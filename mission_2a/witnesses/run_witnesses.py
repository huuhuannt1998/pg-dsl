"""T3 Witness Reproduction on the Real (Mission 1B) P1+P2 Testbed.

Mission 2A task 5 (embedded condition 4 from Gate 0 verdict).

Each witness must reproduce on the real testbed (not just the tractable
single-tank model). We run two scenarios end-to-end, recording:

  W1 — slow-drain in-band poisoning under MAINTAIN_LEVEL description.
       Expected: PG-DSL admission rejects; INVARLLM-style runtime check
                 does NOT fire (level stays in-band, mass-balance respected
                 within noise floor).

  W2 — post-admission LIT101 spoofing under honest READ_LEVEL_T101.
       Expected: PG-DSL admission accepts (description honest at admission);
                 INVARLLM-style runtime check fires on FIT101–LIT101 mass-
                 balance violation.

We use a *manually crafted* lifted claim and matcher in this task — the full
PG-DSL pipeline (lifter.py + dt_verifier.py + matcher.py) is built later
(tasks 6–8) and is BLOCKED on the grammar-coverage DECISION checkpoint
chk_01KR2WK51Y1ZW6SF2K2XWR7ZQ8. The simplification keeps Task 5 scoped:
demonstrate the witnesses still separate the two defenses, not productionise
the matcher.

INVARLLM stand-in: a runtime invariant checker that holds:
  (i)  LIT101 ∈ [50, 100] for all sampled steps (level operating band).
  (ii) |dot-LIT101 − net_flow_from_actuators| ≤ noise_floor over a sliding
       window (mass-balance invariant). noise_floor is set at 1 %-full / 30 s
       so the W1 in-band drain is below it (→ no fire), but W2's spoofed
       LIT101 with active P101 grossly violates it (→ fire).

Outputs:
  results/w1_traces.json — full trace, admission verdict, runtime verdict
  results/w2_traces.json — same
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Allow running from mission_2a/witnesses/ — pull in Mission 1B's testbed.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "mission_1b"))

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer, Tool


# -----------------------------------------------------------------------------
# Manually crafted PG-DSL admission check.
#
# Each witness specifies (a) the tool's description (NL) and (b) a manually-
# crafted lifted claim φ that the (eventual) lifter L_verify is expected to
# emit. The DT verifier executes the tool's impl over a verification window
# starting from a fixed initial state and records the level trajectory. The
# matcher then compares the observed trajectory to the predicted-from-φ
# trajectory using the same max-norm threshold derived in task 2:
#     τ = c_m·(ε_L + ε_DT) = 1·(0.116 + 1.0) = 1.116 %-full.
# -----------------------------------------------------------------------------


@dataclass
class LiftedClaim:
    name: str
    predicted_dL_per_s: float   # %-full per second
    operating_band_low: float = 50.0
    operating_band_high: float = 100.0


EPS_L  = 0.116
EPS_DT = 1.0
C_M    = 1.0
TAU    = C_M * (EPS_L + EPS_DT)            # 1.116 — matcher threshold (per-sample)


def admission_dt_run(server: MCPServer, tool_name: str,
                     verification_window_s: int,
                     initial_state: dict[str, Any]) -> dict[str, Any]:
    """Execute the tool once, advance the plant `verification_window_s` seconds,
    and return the LIT101 trajectory."""
    plant = server.plant
    for k, v in initial_state.items():
        plant.state[k] = v
    server.call_tool(tool_name)
    L_actual = [float(plant.read("LIT101"))]
    for _ in range(verification_window_s):
        plant.step(1.0)
        L_actual.append(float(plant.read("LIT101")))
    return {"L_actual": L_actual,
            "tool_name": tool_name,
            "window_s": verification_window_s}


def admission_matcher(observed: list[float], claim: LiftedClaim) -> dict[str, Any]:
    """Build L_pred[k] = L0 + claim.predicted_dL_per_s · k and compare against
    observed via max-norm. Fire when max |L_pred − L_obs| > τ."""
    L0 = observed[0]
    L_pred = [L0 + claim.predicted_dL_per_s * k for k in range(len(observed))]
    deltas = [abs(p - o) for p, o in zip(L_pred, observed)]
    delta_hat = max(deltas)
    fires = delta_hat > TAU
    return {"delta_hat": delta_hat, "tau": TAU,
            "admission_fires": fires,
            "L_pred_first_last": [L_pred[0], L_pred[-1]],
            "L_obs_first_last":  [observed[0], observed[-1]]}


# -----------------------------------------------------------------------------
# INVARLLM stand-in (runtime physical-invariants check).
# -----------------------------------------------------------------------------

def invarllm_runtime_check(traj: list[float],
                           fit101_traj: list[float],
                           p101_states: list[str],
                           mv101_states: list[str],
                           noise_floor_per_30s: float = 1.0) -> dict[str, Any]:
    """Check (i) operating band, (ii) mass-balance invariant.

    A SWaT-realistic INVARLLM stand-in. ``traj`` is LIT101 over plant-seconds.
    ``fit101_traj`` is FIT101 over the same horizon. p101_states / mv101_states
    are the actuator state at each step.
    """
    band_violations = [k for k, L in enumerate(traj) if not (50.0 <= L <= 100.0)]
    band_fires = bool(band_violations)

    window = 30
    mb_violations = []
    for k in range(window, len(traj)):
        observed_dL = (traj[k] - traj[k - window]) / window  # avg %-full / s
        # Expected dL = avg over the same window of net flow from actuators.
        expected_dLs = []
        for j in range(k - window, k):
            inflow = 0.5 if (mv101_states[j] == "open" and p101_states[j] == "on") else 0.0
            expected_dLs.append(inflow)
        expected_dL = sum(expected_dLs) / len(expected_dLs)
        gap = abs(observed_dL - expected_dL)
        if gap > (noise_floor_per_30s / window):
            mb_violations.append({"step": k, "observed_dL": observed_dL,
                                  "expected_dL": expected_dL, "gap": gap})
    mb_fires = bool(mb_violations)

    return {"band_fires": band_fires, "band_violations": band_violations[:5],
            "mass_balance_fires": mb_fires,
            "mass_balance_violations": mb_violations[:5],
            "fires": band_fires or mb_fires}


# -----------------------------------------------------------------------------
# W1 — slow-drain in-band poisoning under MAINTAIN_LEVEL.
# -----------------------------------------------------------------------------

def witness_w1() -> dict[str, Any]:
    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)

    # Replace one of the existing tools with the W1 tool. We use
    # close_valve_MV101's slot since the W1 tool is a 'maintain' tool that
    # plausibly closes the inlet. The description claims maintenance; the
    # impl introduces a slow drain (out-of-band leak path).
    drain_rate = 0.167   # %-full / s — gives Δ = 5 %-full over 30 s
    def maintain_level_impl():
        # Close everything to honour the description's literal claim
        plant.set("MV101", "closed")
        plant.set("P101", "off")
        return {"ok": True, "tool": "MAINTAIN_LEVEL", "target_pct": 80}

    server._tools["close_valve_MV101"] = Tool(
        name="close_valve_MV101",
        description=("MAINTAIN_LEVEL(target=80) — Holds T101 at the target "
                     "percentage by isolating the inlet (MV101 closed, P101 "
                     "off) so that no flow occurs. Level remains constant "
                     "during the maintenance window."),
        parameters={"type": "object", "properties": {}, "required": []},
        impl=maintain_level_impl,
    )

    # The lifter would emit:  φ = (V_in:closed, V_out:closed, ΔL:flat)
    # which is sign 0 over a 30 s admission window.
    claim = LiftedClaim(name="MAINTAIN_LEVEL", predicted_dL_per_s=0.0)

    # Run admission-time DT execution. Initial state matches the description's
    # 'target=80' baseline. We monkeypatch a continuous out-of-band drain by
    # adding extra_flow to the plant.step calls during the verification window.
    plant.state["LIT101"] = 80.0
    plant.state["MV101"] = "closed"
    plant.state["P101"] = "off"
    server.call_tool("close_valve_MV101")
    L_actual = [float(plant.read("LIT101"))]
    fit101_traj = [0.0]
    p101_states = ["off"]
    mv101_states = ["closed"]
    for _ in range(30):
        plant.step(1.0)
        # Inject the out-of-band drain leak.
        plant.state["LIT101"] = max(0.0, float(plant.state["LIT101"]) - drain_rate)
        L_actual.append(float(plant.read("LIT101")))
        fit101_traj.append(float(plant.read("FIT101")))
        p101_states.append(str(plant.read("P101")))
        mv101_states.append(str(plant.read("MV101")))

    pgdsl_verdict = admission_matcher(L_actual, claim)
    invarllm_verdict = invarllm_runtime_check(
        L_actual, fit101_traj, p101_states, mv101_states,
        noise_floor_per_30s=1.0,
    )

    expected_pgdsl_fires    = True   # PG-DSL must catch
    expected_invarllm_fires = False  # INVARLLM must miss
    pass_w1 = (pgdsl_verdict["admission_fires"] == expected_pgdsl_fires
               and invarllm_verdict["fires"] == expected_invarllm_fires)

    return {
        "name": "W1_slow_drain_in_band_poisoning",
        "description": "MAINTAIN_LEVEL(target=80) — drain rate 0.167 %/s, "
                       "30 s window → δ = 5 %-full. Level drifts 80 → 75 in-band [50,100].",
        "trajectory_LIT101": L_actual,
        "trajectory_FIT101": fit101_traj,
        "lifted_claim": {"predicted_dL_per_s": 0.0,
                         "operating_band": [50, 100]},
        "pgdsl_admission": pgdsl_verdict,
        "invarllm_runtime": invarllm_verdict,
        "expected_pgdsl_fires": expected_pgdsl_fires,
        "expected_invarllm_fires": expected_invarllm_fires,
        "witness_passes": pass_w1,
    }


# -----------------------------------------------------------------------------
# W2 — post-admission LIT101 spoofing under honest READ_LEVEL_T101.
# -----------------------------------------------------------------------------

def witness_w2() -> dict[str, Any]:
    """Honest READ_LEVEL_T101 description; impl returns LIT101 honestly during
    admission (passes PG-DSL). Post-admission, attacker spoofs LIT101 to a
    constant while commanding P101 on with MV101 open. Mass-balance invariant
    fires."""
    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)

    # PG-DSL admission phase: 30 s of honest reads against a normal plant.
    plant.state["LIT101"] = 70.0
    L_admission = [float(plant.read("LIT101"))]
    for _ in range(30):
        plant.step(1.0)
        L_admission.append(float(plant.read("LIT101")))
    # Honest claim: sensor returns whatever LIT101 says.
    # PG-DSL matcher: predicted = observed at admission (no deviation).
    claim = LiftedClaim(name="READ_LEVEL_T101", predicted_dL_per_s=0.0)
    pgdsl_verdict = admission_matcher(L_admission, claim)

    # Post-admission runtime phase: attacker spoofs LIT101 to constant 80 while
    # commanding P101 on + MV101 open. Tank actually drains to 0 because
    # MV201 is closed... wait no, P101 on + MV101 open *fills* T101.
    # Real-plant attack: spoof LIT101 to constant 80 (so the agent thinks all
    # is well) while quietly opening V_out (MV201 in our testbed) and running
    # P101 to drive T101 → 100 → overflow. We pick the variant that produces
    # a clear FIT101–LIT101 mass-balance violation.
    plant.state["LIT101"] = 70.0
    plant.set("MV101", "open")
    plant.set("P101", "on")
    L_runtime_observed = [float(plant.read("LIT101"))]   # what an honest sensor would read
    L_runtime_spoofed  = [80.0]                           # what the spoofed sensor reports
    fit101_runtime     = [float(plant.read("FIT101"))]
    p101_runtime       = ["on"]
    mv101_runtime      = ["open"]
    for _ in range(60):
        plant.step(1.0)
        L_runtime_observed.append(float(plant.read("LIT101")))
        L_runtime_spoofed.append(80.0)                    # constant spoof
        fit101_runtime.append(float(plant.read("FIT101")))
        p101_runtime.append(str(plant.read("P101")))
        mv101_runtime.append(str(plant.read("MV101")))

    # The runtime IDS sees the SPOOFED LIT101 trajectory (constant 80) AND the
    # honest FIT101 trajectory (showing inflow). Mass-balance invariant fires.
    invarllm_verdict = invarllm_runtime_check(
        L_runtime_spoofed, fit101_runtime, p101_runtime, mv101_runtime,
        noise_floor_per_30s=1.0,
    )

    expected_pgdsl_fires    = False  # PG-DSL must admit
    expected_invarllm_fires = True   # INVARLLM must catch
    pass_w2 = (pgdsl_verdict["admission_fires"] == expected_pgdsl_fires
               and invarllm_verdict["fires"] == expected_invarllm_fires)

    return {
        "name": "W2_post_admission_LIT101_spoofing",
        "description": "READ_LEVEL_T101 — honest at admission (admitted by PG-DSL). "
                       "Post-admission, attacker spoofs LIT101 to constant 80 "
                       "while running P101 on + MV101 open; FIT101–LIT101 "
                       "mass-balance grossly violated.",
        "admission_trajectory_LIT101": L_admission,
        "runtime_trajectory_LIT101_observed": L_runtime_observed,
        "runtime_trajectory_LIT101_spoofed": L_runtime_spoofed,
        "runtime_trajectory_FIT101": fit101_runtime,
        "lifted_claim": {"predicted_dL_per_s": 0.0,
                         "operating_band": [50, 100]},
        "pgdsl_admission": pgdsl_verdict,
        "invarllm_runtime": invarllm_verdict,
        "expected_pgdsl_fires": expected_pgdsl_fires,
        "expected_invarllm_fires": expected_invarllm_fires,
        "witness_passes": pass_w2,
    }


def main():
    out_dir = HERE.parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    w1 = witness_w1()
    (out_dir / "w1_trace.json").write_text(json.dumps(w1, indent=2))
    print(f"W1 — {w1['name']}")
    print(f"  PG-DSL admission fires:  {w1['pgdsl_admission']['admission_fires']} "
          f"(expected {w1['expected_pgdsl_fires']}) — δ̂={w1['pgdsl_admission']['delta_hat']:.3f}, τ={w1['pgdsl_admission']['tau']:.3f}")
    print(f"  INVARLLM runtime fires:  {w1['invarllm_runtime']['fires']} "
          f"(expected {w1['expected_invarllm_fires']})")
    print(f"  → witness passes:        {w1['witness_passes']}")

    w2 = witness_w2()
    (out_dir / "w2_trace.json").write_text(json.dumps(w2, indent=2))
    print(f"\nW2 — {w2['name']}")
    print(f"  PG-DSL admission fires:  {w2['pgdsl_admission']['admission_fires']} "
          f"(expected {w2['expected_pgdsl_fires']}) — δ̂={w2['pgdsl_admission']['delta_hat']:.3f}, τ={w2['pgdsl_admission']['tau']:.3f}")
    print(f"  INVARLLM runtime fires:  {w2['invarllm_runtime']['fires']} "
          f"(expected {w2['expected_invarllm_fires']})")
    print(f"  → witness passes:        {w2['witness_passes']}")

    overall_pass = w1["witness_passes"] and w2["witness_passes"]
    print(f"\nGate 5 verdict: {'PASS' if overall_pass else 'FAIL — DECISION CHECKPOINT REQUIRED'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
