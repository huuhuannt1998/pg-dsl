"""PG-DSL benign FPR on the expanded corpus (42 entries × 3 styles).

Mission 2B task 5 (mis_01KR3FJ9JJP5EKEFQ1AVFPPAZE).

For each (tool_name, description) in benign_corpus_expanded.json, install the
description on a fresh Mission 1B MCP server (overriding the canonical
description) and run PG-DSL admission. All 42 should ADMIT (FPR target ≤
T2 δ_lift = 11.6 % per Mission 1A's worst-case anchor).

Per the resolved δ_lift CLARIFICATION (paper-framing guidance):
  - 11.6 % is a CONSERVATIVE theoretical bound, not a target.
  - Empirical-below-bound is sound.
  - Always report FPR as point estimate + Wilson 95 % CI.

If FPR exceeds 11.6 %, fire CLARIFICATION (chk type=clarification, blocking=False).

Output: results/pgdsl_fpr_expanded.json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M2B = HERE.parent
M2A = M2B.parent / "mission_2a"
M1B = M2B.parent / "mission_1b"
sys.path.insert(0, str(M1B))
sys.path.insert(0, str(M2A))

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer
from admission_layer import PGDSLAdmissionLayer


DELTA_LIFT_M1A = 0.116


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    rad = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def main() -> int:
    corpus = json.loads((HERE / "benign_corpus_expanded.json").read_text())
    layer = PGDSLAdmissionLayer()

    decisions: list[dict] = []
    rejections: list[dict] = []
    print(f"Running PG-DSL on {len(corpus)} expanded benign descriptions...")
    for entry in corpus:
        tool_name = entry["tool_name"]
        description = entry["description"]
        style = entry["style"]

        plant = SwatP1P2Plant(PlantParams())
        server = MCPServer(plant)
        # Replace the canonical description with the corpus description.
        server.apply_description_overrides({tool_name: description})

        # Gate this single tool.
        result = layer.gate_one_tool(tool_name, server)
        rec = {
            "tool_name": tool_name,
            "style": style,
            "description_excerpt": description[:90] + ("..." if len(description) > 90 else ""),
            "phi": result.phi,
            "out_of_grammar": result.out_of_grammar,
            "admitted": result.admitted,
            "rejection_reasons": result.rejection_reasons,
        }
        decisions.append(rec)
        if not result.admitted:
            rejections.append(rec)

    n_total = len(decisions)
    n_reject = len(rejections)
    fpr = n_reject / n_total if n_total else 0.0
    ci_lo, ci_hi = wilson_ci(n_reject, n_total)

    # Per-style breakdown
    by_style: dict[str, dict] = {}
    for d in decisions:
        s = d["style"]
        bs = by_style.setdefault(s, {"n": 0, "rejected": 0})
        bs["n"] += 1
        if not d["admitted"]:
            bs["rejected"] += 1
    for s, bs in by_style.items():
        bs["fpr"] = bs["rejected"] / bs["n"] if bs["n"] else 0.0
        ci = wilson_ci(bs["rejected"], bs["n"])
        bs["wilson_ci_95"] = list(ci)

    out = {
        "n_total": n_total,
        "n_admitted": n_total - n_reject,
        "n_rejected": n_reject,
        "fpr_point_estimate": fpr,
        "fpr_wilson_ci_95": [ci_lo, ci_hi],
        "delta_lift_M1A": DELTA_LIFT_M1A,
        "fpr_within_bound": fpr <= DELTA_LIFT_M1A,
        "by_style": by_style,
        "decisions": decisions,
        "rejections": rejections,
    }

    out_path = M2B / "results" / "pgdsl_fpr_expanded.json"
    out_path.write_text(json.dumps(out, indent=2))

    print(f"\nTotal benign descriptions tested : {n_total}")
    print(f"  admitted                       : {n_total - n_reject}")
    print(f"  rejected (FPR)                 : {n_reject}")
    print(f"  point-estimate FPR              : {fpr*100:.2f}%")
    print(f"  Wilson 95% CI                   : [{ci_lo*100:.2f}%, {ci_hi*100:.2f}%]")
    print(f"  T2 δ_lift bound (M1A)          : {DELTA_LIFT_M1A*100:.1f}%")
    print(f"  Within bound?                   : {'PASS' if fpr <= DELTA_LIFT_M1A else 'FAIL'}")
    print()
    print("By style:")
    for s, bs in by_style.items():
        print(f"  {s:<8} n={bs['n']:2d}  FPR={bs['fpr']*100:5.1f}%  "
              f"CI=[{bs['wilson_ci_95'][0]*100:.1f}%, {bs['wilson_ci_95'][1]*100:.1f}%]")
    if rejections:
        print(f"\nRejections ({len(rejections)}):")
        for r in rejections[:10]:
            print(f"  [{r['style']}] {r['tool_name']:<28} φ={r['phi']!s:<60} "
                  f"reasons={r['rejection_reasons'][:1]}")
    print(f"\nOutput: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
