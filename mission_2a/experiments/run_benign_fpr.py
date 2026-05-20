"""Benign FPR campaign — Mission 2A task 11.

Run the 14 honest Mission 1B tool descriptions through the PG-DSL admission
layer. Each must be ADMITTED. Compute FPR = #incorrectly_rejected / #honest_tools
with a Wilson 95 % CI.

Acceptance criterion (Mission 2A): FPR ≤ T2's δ_lift bound from Mission 1A.
T2's δ_lift estimate from Mission 1A's Req2LTL anchor: δ_lift ≤ 0.116
(11.6 %).

Brain monitoring point (per jrn_01KR2YSJ6M28TPJA93RVT52W99): if measured FPR
on the extended grammar deviates >5 % from this estimate, fire CLARIFICATION
to brain. Otherwise proceed.

Output: results/benign_fpr.json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MISSION_2A = HERE.parent
MISSION_1B = MISSION_2A.parent / "mission_1b"
sys.path.insert(0, str(MISSION_1B))
sys.path.insert(0, str(MISSION_2A))

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer
from admission_layer import PGDSLAdmissionLayer


N_REPS = 10                        # reps per tool — admission decisions are deterministic
DELTA_LIFT_M1A_ESTIMATE = 0.116    # Req2LTL accuracy gap = 1 - 0.884
DEVIATION_TRIGGER = 0.05           # CLARIFICATION trigger if |measured - estimate| > 5%


def wilson_ci(n_success: int, n_trials: int, z: float = 1.96) -> tuple[float, float]:
    if n_trials == 0:
        return (0.0, 0.0)
    p = n_success / n_trials
    denom = 1 + z*z/n_trials
    centre = (p + z*z/(2*n_trials)) / denom
    rad = z * math.sqrt(p*(1-p)/n_trials + z*z/(4*n_trials*n_trials)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def main() -> int:
    layer = PGDSLAdmissionLayer()
    out: dict = {"reps_per_tool": N_REPS, "by_tool": {}, "rep_admission_records": []}

    print("=" * 70)
    print("BENIGN FPR CAMPAIGN — Mission 2A task 11")
    print(f"Acceptance criterion: FPR ≤ T2 δ_lift estimate {DELTA_LIFT_M1A_ESTIMATE} = "
          f"{DELTA_LIFT_M1A_ESTIMATE*100:.1f}%")
    print(f"Clarification trigger: deviation > {DEVIATION_TRIGGER*100:.0f}% from estimate")
    print("=" * 70)

    rep_records: list[dict] = []
    for rep in range(N_REPS):
        plant = SwatP1P2Plant(PlantParams())
        server = MCPServer(plant)   # stock benign — no overrides applied
        results = layer.gate_all_tools(server)
        rep_records.append({
            "rep": rep,
            "per_tool": [
                {"tool_name": r.tool_name,
                 "admitted": r.admitted,
                 "rejection_reasons": r.rejection_reasons}
                for r in results
            ],
        })

    # Aggregate per-tool admission rates
    per_tool_admit_rate: dict[str, float] = {}
    for tool in [r["tool_name"] for r in rep_records[0]["per_tool"]]:
        admits = sum(1 for rec in rep_records
                     for tr in rec["per_tool"]
                     if tr["tool_name"] == tool and tr["admitted"])
        per_tool_admit_rate[tool] = admits / N_REPS

    # FPR per rep = fraction of HONEST tools wrongly rejected
    rep_fprs: list[float] = []
    for rec in rep_records:
        n_honest = len(rec["per_tool"])
        n_wrong_reject = sum(1 for tr in rec["per_tool"] if not tr["admitted"])
        rep_fprs.append(n_wrong_reject / n_honest if n_honest else 0.0)

    n_total = sum(len(r["per_tool"]) for r in rep_records)
    n_admit = sum(1 for r in rep_records for t in r["per_tool"] if t["admitted"])
    fpr_overall = (n_total - n_admit) / n_total
    ci_lo, ci_hi = wilson_ci(n_total - n_admit, n_total)

    print("\nPer-tool admission rates (10 reps, deterministic — should be 1.0 each):")
    for tool, rate in per_tool_admit_rate.items():
        marker = "✓" if rate == 1.0 else "✗"
        print(f"  {marker} {tool:<32} admit_rate = {rate:.2f}")

    print(f"\nOverall:")
    print(f"  total honest decisions       : {n_total}")
    print(f"  correctly admitted           : {n_admit}")
    print(f"  incorrectly rejected (FPR)   : {n_total - n_admit}")
    print(f"  FPR (overall)                : {fpr_overall*100:.2f}%")
    print(f"  95% Wilson CI                : [{ci_lo*100:.2f}%, {ci_hi*100:.2f}%]")
    print(f"  T2 δ_lift estimate (M1A)     : {DELTA_LIFT_M1A_ESTIMATE*100:.1f}%")
    deviation = abs(fpr_overall - DELTA_LIFT_M1A_ESTIMATE)
    print(f"  |measured − estimate|        : {deviation*100:.2f}% "
          f"({'within' if deviation <= DEVIATION_TRIGGER else 'EXCEEDS'} "
          f"{DEVIATION_TRIGGER*100:.0f}% trigger)")
    print(f"  acceptance criterion         : {'PASS' if fpr_overall <= DELTA_LIFT_M1A_ESTIMATE else 'FAIL'} "
          f"(FPR ≤ δ_lift)")

    out.update({
        "n_total_decisions": n_total,
        "n_admit": n_admit,
        "fpr_overall": fpr_overall,
        "wilson_ci_95": [ci_lo, ci_hi],
        "delta_lift_m1a_estimate": DELTA_LIFT_M1A_ESTIMATE,
        "deviation_from_estimate": deviation,
        "deviation_trigger": DEVIATION_TRIGGER,
        "deviation_within_trigger": deviation <= DEVIATION_TRIGGER,
        "acceptance_pass": fpr_overall <= DELTA_LIFT_M1A_ESTIMATE,
        "per_tool_admit_rate": per_tool_admit_rate,
        "rep_fprs": rep_fprs,
        "rep_admission_records": rep_records,
    })
    out_path = MISSION_2A / "results" / "benign_fpr.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nFull traces: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
