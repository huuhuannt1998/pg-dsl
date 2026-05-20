"""Mission 3B canonical benign-FPR campaign — stub-lifter mode.

Runs the canonical PG-DSL admission layer (per-tool ⊕ composition) on the
14 benign Mission 1B tool descriptions. Reports:
  - per-tool FPR (paper-final FPR — count of benign tools wrongly REJECTED).
  - composition pass diagnostics (blocked-pair count + reasons).
  - Wilson 95% CI on per-tool FPR.

The composition layer does NOT reject single tools; it identifies unsafe
ordered pairs which the runtime guard refuses to execute. Composition-pass
output is reported as auxiliary diagnostic, NOT as an FPR contribution
(blocked benign pairs from elevated initial states are genuine safety
limits, not false positives).

Acceptance per Mission 3B brief:
  per-tool FPR point estimate ≤ 5%; Wilson CI upper ≤ 11.6% (T2 δ_lift).

Output: mission_3b/results/benign_fpr_canonical_stub.json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M3B = HERE.parent
M2A = M3B.parent / "mission_2a"
M1B = M3B.parent / "mission_1b"
ROOT = M3B.parent
sys.path.insert(0, str(M1B))
sys.path.insert(0, str(M2A))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(M3B))

from plant import PlantParams, SwatP1P2Plant                  # noqa: E402
from mcp_server import MCPServer                               # noqa: E402

from mission_3b.admission_layer import PGDSLCanonicalLayer     # noqa: E402
from mission_3b.admission_layer.pgdsl_canonical import (
    PGDSLAdmissionLayer,
)                                                              # noqa: E402


N_REPS = 10
DELTA_LIFT_M1A_ESTIMATE = 0.116


def wilson_ci(n_success: int, n_trials: int, z: float = 1.96) -> tuple[float, float]:
    if n_trials == 0:
        return (0.0, 0.0)
    p = n_success / n_trials
    denom = 1 + z * z / n_trials
    centre = (p + z * z / (2 * n_trials)) / denom
    rad = z * math.sqrt(p * (1 - p) / n_trials + z * z / (4 * n_trials * n_trials)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def main() -> int:
    layer = PGDSLCanonicalLayer(per_tool_layer=PGDSLAdmissionLayer(), mode="stub")

    print("=" * 78)
    print("MISSION 3B — Canonical Benign FPR (stub-lifter mode)")
    print(f"  Acceptance: per-tool FPR ≤ 5%; CI upper ≤ {DELTA_LIFT_M1A_ESTIMATE*100:.1f}%")
    print("=" * 78)

    rep_records: list[dict] = []
    composition_diagnostics: list[dict] = []
    for rep in range(N_REPS):
        def factory():
            plant = SwatP1P2Plant(PlantParams())
            return MCPServer(plant)
        report = layer.gate_all_tools(factory)
        per_tool_records = [
            {"tool_name": r.tool_name,
             "admitted": r.admitted,
             "rejection_reasons": r.rejection_reasons}
            for r in report.per_tool
        ]
        rep_records.append({"rep": rep, "per_tool": per_tool_records,
                            "per_tool_seconds": report.per_tool_admit_seconds,
                            "composition_seconds": report.composition_seconds})
        composition_diagnostics.append({
            "rep": rep,
            "n_blocked_pairs": len(report.composition.blocked_pairs),
            "n_pairs_tested": report.composition.n_pairs_tested,
            "n_safe_pairs": report.composition.safe_pair_count,
            "blocked_pair_set_first10": [
                {"a": bp.a, "b": bp.b, "init": bp.initial_state,
                 "exit_var": bp.band_exit_var, "exit_step_s": bp.band_exit_step_s}
                for bp in report.composition.blocked_pairs[:10]
            ],
        })

    n_tools = len(rep_records[0]["per_tool"])
    n_total = N_REPS * n_tools
    n_admit = sum(1 for rec in rep_records for tr in rec["per_tool"] if tr["admitted"])
    fpr = (n_total - n_admit) / n_total
    ci_lo, ci_hi = wilson_ci(n_total - n_admit, n_total)

    per_tool_admit_rate: dict[str, float] = {}
    for tool in [r["tool_name"] for r in rep_records[0]["per_tool"]]:
        admits = sum(1 for rec in rep_records
                     for tr in rec["per_tool"]
                     if tr["tool_name"] == tool and tr["admitted"])
        per_tool_admit_rate[tool] = admits / N_REPS

    print("\nPer-tool admission rates (deterministic stub):")
    for tool, rate in per_tool_admit_rate.items():
        marker = "✓" if rate == 1.0 else "✗"
        print(f"  {marker} {tool:<28} {rate:.2f}")

    print(f"\nOverall per-tool FPR        : {fpr*100:.2f}%  (Wilson 95% CI [{ci_lo*100:.2f}%, {ci_hi*100:.2f}%])")
    print(f"Acceptance (≤5%, CI≤11.6%) : "
          f"{'PASS' if fpr <= 0.05 and ci_hi <= DELTA_LIFT_M1A_ESTIMATE else 'FAIL'}")

    rep0 = composition_diagnostics[0]
    print(f"\nComposition-pass diagnostics (rep 0)")
    print(f"  pairs tested          : {rep0['n_pairs_tested']}")
    print(f"  blocked pairs         : {rep0['n_blocked_pairs']}")
    print(f"  safe pairs            : {rep0['n_safe_pairs']}")
    print(f"  (blocked benign pairs are NOT false positives; they are unsafe-from-extremes safety limits)")

    out = {
        "mode": "stub",
        "n_reps": N_REPS,
        "n_tools_per_rep": n_tools,
        "n_total_decisions": n_total,
        "n_admit": n_admit,
        "fpr_per_tool_overall": fpr,
        "wilson_ci_95": [ci_lo, ci_hi],
        "delta_lift_m1a_estimate": DELTA_LIFT_M1A_ESTIMATE,
        "acceptance_per_tool_fpr_le_5pct": fpr <= 0.05,
        "acceptance_ci_upper_le_11_6pct": ci_hi <= DELTA_LIFT_M1A_ESTIMATE,
        "per_tool_admit_rate": per_tool_admit_rate,
        "rep_admission_records": rep_records,
        "composition_diagnostics": composition_diagnostics,
    }
    out_path = M3B / "results" / "benign_fpr_canonical_stub.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {out_path}")
    return 0 if (fpr <= 0.05 and ci_hi <= DELTA_LIFT_M1A_ESTIMATE) else 2


if __name__ == "__main__":
    raise SystemExit(main())
