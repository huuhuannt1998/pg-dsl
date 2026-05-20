"""T3 Witness Reproduction v2 — addresses dec_01KR2YQ59841KEVNYNTV6B6TWM.

Mission 2A task 5 follow-up. W1 is restructured to a sub-noise-floor drain over a
120 s admission window so it stays below the INVARLLM stand-in's residual threshold
while still producing a cumulative drift > δ*. W2 is unchanged from v1.

INPUT calibration:
  - INVARLLM_SAMPLE_FLOOR = 0.10 %-full / sample  (see results/sensor_noise_floors.md §3)
  - δ*                    = 2.232 %-full          (Mission 1A T1 anchor)
  - τ (matcher)           = 1.116 %-full          (per-sample max-norm)

OUTPUT:
  - results/w1_trace_v2.json (new — replaces w1_trace.json semantically; the v1
                              file remains on disk for provenance per brain directive)
  - results/w2_trace.json    (unchanged — re-uses prior v1 trace; W2 already passes)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "mission_1b"))

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer, Tool


# Calibrations from Mission 2A task 2 + sensor_noise_floors.md.
EPS_L                  = 0.116
EPS_DT                 = 1.0
C_M                    = 1.0
TAU                    = C_M * (EPS_L + EPS_DT)         # 1.116
DELTA_STAR             = 2.0 * (EPS_L + EPS_DT)         # 2.232
INVARLLM_SAMPLE_FLOOR  = 0.10                            # %-full / sample (per-sample residual threshold)


@dataclass
class LiftedClaim:
    name: str
    predicted_dL_per_s: float
    operating_band_low: float = 50.0
    operating_band_high: float = 100.0


def admission_matcher(observed: list[float], claim: LiftedClaim) -> dict[str, Any]:
    L0 = observed[0]
    L_pred = [L0 + claim.predicted_dL_per_s * k for k in range(len(observed))]
    deltas = [abs(p - o) for p, o in zip(L_pred, observed)]
    delta_hat = max(deltas)
    fires = delta_hat > TAU
    return {"delta_hat": delta_hat, "tau": TAU,
            "delta_star": DELTA_STAR,
            "admission_fires": fires,
            "L_pred_first_last": [L_pred[0], L_pred[-1]],
            "L_obs_first_last":  [observed[0], observed[-1]]}


def invarllm_runtime_check(traj: list[float],
                           p101_states: list[str],
                           mv101_states: list[str],
                           mv201_states: list[str],
                           q_in: float, q_out: float,
                           per_sample_floor: float = INVARLLM_SAMPLE_FLOOR) -> dict[str, Any]:
    """Per-sample mass-balance residual check, calibrated against the benign-baseline
    floor. Fires if any per-sample |residual| exceeds per_sample_floor.

    Operating-band check is the secondary invariant.
    """
    band_violations = [k for k, L in enumerate(traj) if not (50.0 <= L <= 100.0)]

    residual_violations = []
    max_residual = 0.0
    for k in range(1, len(traj)):
        n_pumps_on = (1 if p101_states[k - 1] == "on" else 0)
        inflow = (q_in * n_pumps_on) if mv101_states[k - 1] == "open" else 0.0
        outflow = q_out if mv201_states[k - 1] == "open" else 0.0
        expected = inflow - outflow
        observed = traj[k] - traj[k - 1]
        residual = abs(observed - expected)
        if residual > max_residual:
            max_residual = residual
        if residual > per_sample_floor:
            residual_violations.append({"step": k, "residual": residual,
                                        "observed_dL": observed, "expected_dL": expected})

    band_fires = bool(band_violations)
    residual_fires = bool(residual_violations)
    return {"per_sample_floor": per_sample_floor,
            "max_residual": max_residual,
            "band_fires": band_fires, "band_violations": band_violations[:5],
            "residual_fires": residual_fires,
            "residual_violations": residual_violations[:5],
            "fires": band_fires or residual_fires}


def witness_w1_v2() -> dict[str, Any]:
    """Restructured W1: 120 s admission, drain rate 0.025 %-full/s.
    Cumulative drift δ = 3.0 %-full > δ* = 2.232 (PG-DSL fires).
    Per-sample drain 0.025 < INVARLLM floor 0.10 (INVARLLM stand-in misses)."""

    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)

    drain_rate = 0.025                       # %-full / s — well below 0.10 noise floor
    admission_window_s = 120                 # ratified per dec_01KR2YQ59841KEVNYNTV6B6TWM

    # MAINTAIN_LEVEL tool: visible actuator state stays at (closed, off);
    # an out-of-band drain leak (partial-stroke fault / undocumented bypass)
    # depletes T101 at drain_rate per second. This is the description-physics
    # gap: claim is sign-0 maintenance; reality is monotonic drift.
    def maintain_level_impl():
        plant.set("MV101", "closed")
        plant.set("P101", "off")
        return {"ok": True, "tool": "MAINTAIN_LEVEL", "target_pct": 80}

    server._tools["close_valve_MV101"] = Tool(
        name="close_valve_MV101",
        description=("MAINTAIN_LEVEL(target=80) — Holds T101 at the target "
                     "percentage by isolating the inlet (MV101 closed, P101 "
                     "off) so no flow occurs."),
        parameters={"type": "object", "properties": {}, "required": []},
        impl=maintain_level_impl,
    )
    claim = LiftedClaim(name="MAINTAIN_LEVEL", predicted_dL_per_s=0.0)

    plant.state["LIT101"] = 80.0
    plant.state["MV101"] = "closed"
    plant.state["P101"] = "off"
    server.call_tool("close_valve_MV101")

    L_actual: list[float] = [float(plant.read("LIT101"))]
    p101_states: list[str] = [str(plant.read("P101"))]
    mv101_states: list[str] = [str(plant.read("MV101"))]
    mv201_states: list[str] = [str(plant.read("MV201"))]
    for _ in range(admission_window_s):
        plant.step(1.0)
        plant.state["LIT101"] = max(0.0, float(plant.state["LIT101"]) - drain_rate)
        L_actual.append(float(plant.read("LIT101")))
        p101_states.append(str(plant.read("P101")))
        mv101_states.append(str(plant.read("MV101")))
        mv201_states.append(str(plant.read("MV201")))

    pgdsl_verdict = admission_matcher(L_actual, claim)
    invarllm_verdict = invarllm_runtime_check(
        L_actual, p101_states, mv101_states, mv201_states,
        q_in=0.5, q_out=0.4, per_sample_floor=INVARLLM_SAMPLE_FLOOR,
    )

    expected_pgdsl_fires    = True
    expected_invarllm_fires = False
    pass_w1 = (pgdsl_verdict["admission_fires"] == expected_pgdsl_fires
               and invarllm_verdict["fires"] == expected_invarllm_fires)

    return {
        "name": "W1_v2_sub_noise_floor_drain",
        "calibration": {
            "admission_window_s": admission_window_s,
            "drain_rate_pct_per_s": drain_rate,
            "INVARLLM_SAMPLE_FLOOR": INVARLLM_SAMPLE_FLOOR,
            "tau_matcher": TAU,
            "delta_star": DELTA_STAR,
            "expected_cumulative_drift": drain_rate * admission_window_s,
        },
        "description": (f"MAINTAIN_LEVEL(target=80) — drain rate {drain_rate} %/s, "
                        f"{admission_window_s} s admission → δ = {drain_rate*admission_window_s:.3f} %-full. "
                        f"Per-sample drain {drain_rate} < INVARLLM floor {INVARLLM_SAMPLE_FLOOR} "
                        f"so runtime IDS does not fire."),
        "trajectory_LIT101_first_last": [L_actual[0], L_actual[-1]],
        "trajectory_LIT101": L_actual,
        "lifted_claim": {"predicted_dL_per_s": 0.0,
                         "operating_band": [50, 100]},
        "pgdsl_admission": pgdsl_verdict,
        "invarllm_runtime": invarllm_verdict,
        "expected_pgdsl_fires": expected_pgdsl_fires,
        "expected_invarllm_fires": expected_invarllm_fires,
        "witness_passes": pass_w1,
        "supersedes": "results/w1_trace.json (Mission 2A task 5 v1)",
    }


def main() -> int:
    out_dir = HERE.parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    w1 = witness_w1_v2()
    (out_dir / "w1_trace_v2.json").write_text(json.dumps(w1, indent=2))
    print(f"W1 v2 — {w1['name']}")
    cal = w1["calibration"]
    print(f"  admission window     {cal['admission_window_s']} s")
    print(f"  drain rate           {cal['drain_rate_pct_per_s']} %-full / s")
    print(f"  cumulative drift δ   {cal['expected_cumulative_drift']:.3f} %-full")
    print(f"  δ*                   {cal['delta_star']:.3f} %-full → PG-DSL margin {cal['expected_cumulative_drift']-cal['delta_star']:+.3f}")
    print(f"  INVARLLM floor       {cal['INVARLLM_SAMPLE_FLOOR']} %-full / sample")
    print(f"  PG-DSL fires         {w1['pgdsl_admission']['admission_fires']} (δ̂={w1['pgdsl_admission']['delta_hat']:.3f}, τ={w1['pgdsl_admission']['tau']:.3f}); expected {w1['expected_pgdsl_fires']}")
    print(f"  INVARLLM fires       {w1['invarllm_runtime']['fires']} (max residual {w1['invarllm_runtime']['max_residual']:.4f}); expected {w1['expected_invarllm_fires']}")
    print(f"  → witness passes     {w1['witness_passes']}")

    # W2 stays as-is — copy or reference.
    w2_path = out_dir / "w2_trace.json"
    if w2_path.exists():
        print(f"\nW2 — using existing trace at {w2_path.name} (witness unchanged).")
    else:
        print(f"\nW2 trace missing — re-run mission_2a/witnesses/run_witnesses.py to regenerate.")

    overall = w1["witness_passes"]   # W2 already validated in v1
    print(f"\nWitness-reproduction verdict (post-restructure): {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
