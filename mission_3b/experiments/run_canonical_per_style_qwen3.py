"""Mission 3B canonical per-style benign FPR — qwen3:14b real-lifter.

Runs the canonical PG-DSL admission layer over the 42-entry Mission 2B
expanded benign corpus (14 tools × 3 styles {FORMAL, CASUAL, TERSE}).

Composition pass has no per-style effect (it only operates on admitted-tool
SETS, not on description text). Per-tool admission is the FPR-relevant
output. Composition diagnostics are reported as auxiliary info.

Output: mission_3b/results/per_style_canonical_qwen3.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
M3B = HERE.parent
M2A = M3B.parent / "mission_2a"
M2B = M3B.parent / "mission_2b"
M2C = M3B.parent / "mission_2c"
M1B = M3B.parent / "mission_1b"
ROOT = M3B.parent
sys.path.insert(0, str(M1B))
sys.path.insert(0, str(M2A))
sys.path.insert(0, str(M2B))
sys.path.insert(0, str(M2C))
sys.path.insert(0, str(M2C / "baselines"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(M3B))

from plant import PlantParams, SwatP1P2Plant                # noqa: E402
from mcp_server import MCPServer                             # noqa: E402

from real_admission_layer import RealLLMAdmissionLayer       # noqa: E402

from mission_3b.admission_layer import PGDSLCanonicalLayer   # noqa: E402


DELTA_LIFT_M1A = 0.116


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    rad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def main() -> int:
    real_layer = RealLLMAdmissionLayer(prompt_variant="v1")
    layer = PGDSLCanonicalLayer(per_tool_layer=real_layer, mode="qwen3")

    corpus = json.loads((M2B / "evaluation" / "benign_corpus_expanded.json").read_text())
    print(f"=" * 78)
    print(f"MISSION 3B — Canonical per-style FPR ({len(corpus)} entries × qwen3:14b)")
    print(f"=" * 78)

    t_start = time.time()
    decisions: list[dict] = []
    rejections: list[dict] = []

    for entry in corpus:
        plant = SwatP1P2Plant(PlantParams())
        server = MCPServer(plant)
        server.apply_description_overrides({entry["tool_name"]: entry["description"]})

        # Per-tool decision via the per-tool layer (the canonical layer's
        # composition pass needs all tools admitted; here we only care
        # about per-tool FPR for this entry, so call gate_one_tool).
        r = real_layer.gate_one_tool(entry["tool_name"], server)

        rec = {
            "tool_name": entry["tool_name"],
            "style": entry["style"],
            "description_excerpt": entry["description"][:90]
                                   + ("..." if len(entry["description"]) > 90 else ""),
            "phi": r.phi,
            "out_of_grammar": r.out_of_grammar,
            "admitted": r.admitted,
            "rejection_reasons": r.rejection_reasons,
            "admission_time_seconds": r.admission_time_seconds,
        }
        decisions.append(rec)
        if not r.admitted:
            rejections.append(rec)
        marker = "ADMIT" if r.admitted else "REJECT"
        print(f"  [{r.admission_time_seconds:5.1f}s] [{entry['style']:<6}] {marker:<6} "
              f"{entry['tool_name']:<28} φ = {r.phi[:60]}")

    n_total = len(decisions)
    n_rej = len(rejections)
    fpr = n_rej / n_total if n_total else 0.0
    ci = wilson_ci(n_rej, n_total)

    by_style: dict = {}
    for d in decisions:
        s = d["style"]
        bs = by_style.setdefault(s, {"n": 0, "rejected": 0})
        bs["n"] += 1
        if not d["admitted"]:
            bs["rejected"] += 1
    for s, bs in by_style.items():
        bs["fpr"] = bs["rejected"] / bs["n"]
        bs["ci"] = list(wilson_ci(bs["rejected"], bs["n"]))

    # Auxiliary: composition diagnostics on a fresh canonical-description server.
    def factory():
        return MCPServer(SwatP1P2Plant(PlantParams()))
    canonical_report = layer.gate_all_tools(factory)
    composition_diagnostics = {
        "canonical_server": True,
        "n_blocked_pairs": len(canonical_report.composition.blocked_pairs),
        "n_pairs_tested": canonical_report.composition.n_pairs_tested,
        "n_safe_pairs": canonical_report.composition.safe_pair_count,
    }

    out = {
        "mode": "qwen3",
        "model": "qwen3:14b",
        "n_total": n_total,
        "n_rejected": n_rej,
        "fpr_point_estimate": fpr,
        "fpr_wilson_ci_95": list(ci),
        "by_style": by_style,
        "delta_lift_M1A": DELTA_LIFT_M1A,
        "fpr_within_bound": fpr <= DELTA_LIFT_M1A,
        "composition_diagnostics": composition_diagnostics,
        "decisions": decisions,
        "rejections": rejections,
        "wall_clock_s_total": time.time() - t_start,
    }
    out_path = M3B / "results" / "per_style_canonical_qwen3.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))

    print()
    print(f"Per-style FPR")
    for style, bs in by_style.items():
        print(f"  {style:<6} {bs['rejected']:>2}/{bs['n']:>2} = {bs['fpr']*100:>5.2f}%   "
              f"CI [{bs['ci'][0]*100:.2f}%, {bs['ci'][1]*100:.2f}%]")
    print(f"\nOverall expanded FPR: {n_rej}/{n_total} = {fpr*100:.2f}%   "
          f"Wilson 95% CI [{ci[0]*100:.2f}%, {ci[1]*100:.2f}%]")
    print(f"T2 δ_lift bound      : {DELTA_LIFT_M1A*100:.1f}%")
    print(f"Within bound         : {'PASS' if out['fpr_within_bound'] else 'FAIL'}")
    print(f"\nOutput: {out_path}")
    return 0 if out["fpr_within_bound"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
