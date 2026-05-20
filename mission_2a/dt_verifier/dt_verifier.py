"""DT verifier — executes a candidate tool in the MiniCPS-style DT and
records the actual physical effects ψ_actual.

Mission 2A task 7 (mis_01KR2W2P9XKTC37MKYQ9FW5YF1). Per brain unblock
directive, executor picks a reasonable test-input sampling strategy.

Test-input sampling strategy (documented):
  Each tool is verified by running its implementation against THREE
  representative DT initial states that sweep the operating envelope:
    LOW  : LIT101 = 30 %, LIT201 = 30 %, no actuators active.
    MID  : LIT101 = 70 %, LIT201 = 60 %, no actuators active. (= benign default)
    HIGH : LIT101 = 90 %, LIT201 = 90 %, no actuators active.
  Three samples per tool. Each sample records the full trajectory over the
  admission window (120 s — ratified per dec_01KR2YQ59841KEVNYNTV6B6TWM).

For each (tool, initial_state) sample, the verifier records:
  - actuator pre / post state (transitions caused by the tool call)
  - level / flow / chemistry sensor pre / post values
  - the tool's RETURN VALUE (separate from sensor oracle reads — needed for
    sensor-aliasing detection)
  - the cumulative Δstate sign + monotone + bounded properties of LIT101,
    LIT201, Cond_P2 over the admission window

Output: ``measured_effects.json`` mapping tool_name → list[ψ_sample].
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MISSION_1B = HERE.parent.parent / "mission_1b"
sys.path.insert(0, str(MISSION_1B))

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer


ADMISSION_WINDOW_S = 120     # ratified by dec_01KR2YQ59841KEVNYNTV6B6TWM
PLANT_DT = 1.0


# Three representative initial states — sweep the operating envelope.
INITIAL_STATES = [
    {"name": "LOW",  "LIT101": 30.0, "LIT201": 30.0,
                       "MV101": "closed", "P101": "off",
                       "MV201": "closed", "P201": "off",
                       "AIT201": 0.30},
    {"name": "MID",  "LIT101": 70.0, "LIT201": 60.0,
                       "MV101": "closed", "P101": "off",
                       "MV201": "closed", "P201": "off",
                       "AIT201": 0.30},
    {"name": "HIGH", "LIT101": 90.0, "LIT201": 90.0,
                       "MV101": "closed", "P101": "off",
                       "MV201": "closed", "P201": "off",
                       "AIT201": 0.30},
]


@dataclasses.dataclass
class MeasuredEffect:
    tool_name: str
    initial_state_name: str
    initial_state: dict
    tool_return_value: Any
    actuator_pre: dict
    actuator_post: dict
    sensor_oracle_pre: dict     # what the plant ACTUALLY says (verifier-side oracle read)
    sensor_oracle_post: dict
    trajectory_LIT101: list[float]
    trajectory_LIT201: list[float]
    trajectory_AIT201: list[float]
    delta_LIT101_signs: dict
    delta_LIT201_signs: dict
    delta_Cond_P2_signs: dict
    notes: str = ""

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        return d


def _sign_summary(traj: list[float], eps: float = 1e-6) -> dict:
    """Classify the trajectory's overall direction over the window."""
    if len(traj) < 2:
        return {"sign": "0", "monotone": "0", "min": traj[0], "max": traj[0],
                "first": traj[0], "last": traj[0], "delta": 0.0}
    first, last = traj[0], traj[-1]
    delta = last - first
    if delta > eps:
        sign = "+"
    elif delta < -eps:
        sign = "-"
    else:
        sign = "0"

    # monotone check: strictly non-decreasing / non-increasing
    diffs = [traj[k+1] - traj[k] for k in range(len(traj) - 1)]
    if all(d >= -eps for d in diffs) and any(d > eps for d in diffs):
        monotone = "+"
    elif all(d <=  eps for d in diffs) and any(d < -eps for d in diffs):
        monotone = "-"
    else:
        monotone = "0"

    return {"sign": sign, "monotone": monotone,
            "min": min(traj), "max": max(traj),
            "first": first, "last": last, "delta": delta}


def _snapshot_actuators(plant: SwatP1P2Plant) -> dict:
    return {a: plant.read(a) for a in plant.ACTUATORS}


def _snapshot_sensors(plant: SwatP1P2Plant) -> dict:
    return {s: plant.read(s) for s in plant.SENSORS}


def verify_tool(server: MCPServer, tool_name: str,
                init_overrides: dict[str, Any],
                tool_args_override: dict | None = None) -> MeasuredEffect:
    """Run a single tool against the DT from one initial state, record ψ.

    ``tool_args_override`` lets the admission layer feed the DT verifier
    parameters extracted from the description (e.g., the claimed-standard
    dosing rate). For set_dosing_rate this is critical: the admission layer
    invokes the tool at the description-claimed-standard rate so that any
    magnitude poisoning shows up as a Δstate(Cond_P2) violation.
    """
    plant = server.plant
    # Reset to the desired initial state
    for k, v in init_overrides.items():
        if k == "name":
            continue
        plant.state[k] = v
    plant.t = 0.0

    actuator_pre = _snapshot_actuators(plant)
    sensor_oracle_pre = _snapshot_sensors(plant)

    if tool_name == "set_dosing_rate":
        # Pre-condition: P201 must be on for the rate to have any effect.
        server.call_tool("start_dosing_pump_P201")
        actuator_pre = _snapshot_actuators(plant)
        # Use the claimed-standard rate if the lifter extracted one; else 1.0
        # (canonical honest reference invocation).
        rate = 1.0
        if tool_args_override and "rate" in tool_args_override:
            rate = float(tool_args_override["rate"])
        result = server.call_tool(tool_name, {"pump": "P201", "rate": rate})
    else:
        args = tool_args_override or {}
        result = server.call_tool(tool_name, args) if args else server.call_tool(tool_name)
    tool_return = result.get("result")

    actuator_post = _snapshot_actuators(plant)

    # Run the plant for the admission window, recording trajectories.
    LIT101_traj = [float(plant.read("LIT101"))]
    LIT201_traj = [float(plant.read("LIT201"))]
    AIT201_traj = [float(plant.read("AIT201"))]
    for _ in range(ADMISSION_WINDOW_S):
        plant.step(PLANT_DT)
        LIT101_traj.append(float(plant.read("LIT101")))
        LIT201_traj.append(float(plant.read("LIT201")))
        AIT201_traj.append(float(plant.read("AIT201")))

    sensor_oracle_post = _snapshot_sensors(plant)

    return MeasuredEffect(
        tool_name=tool_name,
        initial_state_name=init_overrides["name"],
        initial_state={k: v for k, v in init_overrides.items() if k != "name"},
        tool_return_value=tool_return,
        actuator_pre=actuator_pre,
        actuator_post=actuator_post,
        sensor_oracle_pre=sensor_oracle_pre,
        sensor_oracle_post=sensor_oracle_post,
        trajectory_LIT101=LIT101_traj,
        trajectory_LIT201=LIT201_traj,
        trajectory_AIT201=AIT201_traj,
        delta_LIT101_signs=_sign_summary(LIT101_traj),
        delta_LIT201_signs=_sign_summary(LIT201_traj),
        delta_Cond_P2_signs=_sign_summary(AIT201_traj),
    )


def measure_all_tools(server_factory) -> dict[str, list[MeasuredEffect]]:
    """Return ψ for every tool × every initial state."""
    out: dict[str, list[MeasuredEffect]] = {}
    server = server_factory()
    for t in server.list_tools():
        tool_name = t["name"]
        out[tool_name] = []
        for init in INITIAL_STATES:
            # fresh plant per (tool, init) to avoid state contamination
            server = server_factory()
            psi = verify_tool(server, tool_name, init)
            out[tool_name].append(psi)
    return out


def main() -> int:
    def factory():
        return MCPServer(SwatP1P2Plant(PlantParams()))

    measured = measure_all_tools(factory)

    out_path = Path(__file__).resolve().parent.parent / "dt_verifier" / "measured_effects.json"
    serialised = {
        "admission_window_s": ADMISSION_WINDOW_S,
        "plant_dt": PLANT_DT,
        "initial_states": INITIAL_STATES,
        "measured_effects": {
            tool: [m.to_dict() for m in samples]
            for tool, samples in measured.items()
        },
    }
    out_path.write_text(json.dumps(serialised, indent=2, default=str))
    print(f"Tools verified                  : {len(measured)}")
    print(f"Initial states per tool         : {len(INITIAL_STATES)}")
    print(f"Total ψ samples                  : {sum(len(s) for s in measured.values())}")
    print(f"Admission window                : {ADMISSION_WINDOW_S} s × {PLANT_DT} s/step")
    print(f"Output                          : {out_path}")
    # Tiny sanity print: per-tool LIT101 sign over the MID initial state
    print("\nPer-tool LIT101 sign over MID initial state (sanity):")
    for tool, samples in measured.items():
        mid = next(s for s in samples if s.initial_state_name == "MID")
        print(f"  {tool:<32} sign={mid.delta_LIT101_signs['sign']}, "
              f"Δ={mid.delta_LIT101_signs['delta']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
