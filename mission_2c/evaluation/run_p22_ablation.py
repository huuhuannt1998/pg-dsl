"""Phase 2 prompt-restraint ablation (Mission 2C P2.2).

Runs the real-Qwen lifter over the canonical 14-tool + expanded 42-tool
corpora under TWO prompt configurations:
  (a) v0 — the original prompt (already produced 30.95% / 42.86% FPR;
           we re-load saved results rather than re-run to save wall-clock)
  (b) v1 — the restrained prompt per dec_01KR3K6P6CX26D00RZ131Y6437

Per-style breakdown reported (TERSE / CASUAL / FORMAL).

Acceptance for unblocking Mission 2C tasks 7-13 (per Phase 2 spec):
  v1 expanded FPR < 20% across all styles, FORMAL FPR < 25%.

If v1 fails the threshold, P2.3 will add the canonical-claim post-processor
(config c) or fall back to Option B per the unblocking conditions.

Output:
  results/p22_ablation.json — per-config per-style FPR + Wilson 95% CIs
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
M2C = HERE.parent
M2A = M2C.parent / "mission_2a"
M2B = M2C.parent / "mission_2b"
M1B = M2C.parent / "mission_1b"
sys.path.insert(0, str(M1B))
sys.path.insert(0, str(M2A))
sys.path.insert(0, str(M2B))
sys.path.insert(0, str(M2C))
sys.path.insert(0, str(M2C / "baselines"))

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer
from real_admission_layer import RealLLMAdmissionLayer
from real_lifter import RealLifter


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    rad = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def evaluate_corpus(layer: RealLLMAdmissionLayer, corpus: list[dict],
                     label: str) -> dict:
    decisions: list[dict] = []
    rejections: list[dict] = []
    t0 = time.time()
    for entry in corpus:
        plant = SwatP1P2Plant(PlantParams())
        server = MCPServer(plant)
        # If this is the canonical 14-tool corpus, the description is already
        # the canonical one on the server; for the expanded corpus we must
        # override.
        if "style" in entry:
            server.apply_description_overrides({entry["tool_name"]: entry["description"]})
            description = entry["description"]
            style = entry["style"]
        else:
            description = server._tools[entry["tool_name"]].description
            style = "CANONICAL"
        r = layer.gate_one_tool(entry["tool_name"], server)
        rec = {
            "tool_name": entry["tool_name"],
            "style": style,
            "description_excerpt": description[:90] + ("..." if len(description) > 90 else ""),
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
        print(f"  [{r.admission_time_seconds:5.1f}s] [{style:<9}] {marker:<6} "
              f"{entry['tool_name']:<28} φ = {r.phi[:60]}")
    elapsed = time.time() - t0

    n_total = len(decisions); n_rej = len(rejections)
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

    print(f"  {label}: FPR = {n_rej}/{n_total} = {fpr*100:.2f}%, "
          f"CI = [{ci[0]*100:.2f}%, {ci[1]*100:.2f}%]   wall {elapsed:.1f}s")
    return {
        "label": label,
        "n_total": n_total, "n_rejected": n_rej,
        "fpr_point_estimate": fpr, "fpr_wilson_ci_95": list(ci),
        "by_style": by_style,
        "elapsed_s": elapsed,
        "decisions": decisions, "rejections": rejections,
    }


def main() -> int:
    canonical_descriptions = []
    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)
    for t in server.list_tools():
        canonical_descriptions.append({"tool_name": t["name"]})

    expanded = json.loads((M2B / "evaluation" / "benign_corpus_expanded.json").read_text())

    out_dir = M2C / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("PHASE 2 PROMPT-RESTRAINT ABLATION — config (b) v1 restrained")
    print("=" * 78)
    layer_v1 = RealLLMAdmissionLayer(prompt_variant="v1")

    print("\n— Canonical 14 tools, v1 —")
    canonical_v1 = evaluate_corpus(layer_v1, canonical_descriptions,
                                    "canonical-v1")
    print("\n— Expanded 42 tools, v1 —")
    expanded_v1 = evaluate_corpus(layer_v1, expanded, "expanded-v1")

    # Load v0 results for comparison
    canonical_v0 = json.loads((out_dir / "real_pgdsl_fpr_canonical_v0.json").read_text())
    expanded_v0 = json.loads((out_dir / "real_pgdsl_fpr_expanded_v0.json").read_text())

    out = {
        "configs": {
            "v0_original": {
                "canonical": {
                    "fpr": canonical_v0["fpr_point_estimate"],
                    "ci": canonical_v0["fpr_wilson_ci_95"],
                    "n_total": canonical_v0["n_total"],
                },
                "expanded": {
                    "fpr": expanded_v0["fpr_point_estimate"],
                    "ci": expanded_v0["fpr_wilson_ci_95"],
                    "by_style": expanded_v0.get("by_style", {}),
                    "n_total": expanded_v0["n_total"],
                },
            },
            "v1_restrained": {
                "canonical": {
                    "fpr": canonical_v1["fpr_point_estimate"],
                    "ci": canonical_v1["fpr_wilson_ci_95"],
                    "n_total": canonical_v1["n_total"],
                },
                "expanded": {
                    "fpr": expanded_v1["fpr_point_estimate"],
                    "ci": expanded_v1["fpr_wilson_ci_95"],
                    "by_style": expanded_v1["by_style"],
                    "n_total": expanded_v1["n_total"],
                },
            },
        },
        "raw": {
            "canonical_v1": canonical_v1,
            "expanded_v1": expanded_v1,
        },
    }
    (out_dir / "p22_ablation.json").write_text(json.dumps(out, indent=2, default=str))
    (out_dir / "real_pgdsl_fpr_canonical_v1.json").write_text(json.dumps(canonical_v1, indent=2, default=str))
    (out_dir / "real_pgdsl_fpr_expanded_v1.json").write_text(json.dumps(expanded_v1, indent=2, default=str))

    # Acceptance check
    overall_v1 = expanded_v1["fpr_point_estimate"]
    formal_v1 = expanded_v1["by_style"].get("FORMAL", {}).get("fpr", 1.0)
    casual_v1 = expanded_v1["by_style"].get("CASUAL", {}).get("fpr", 1.0)
    terse_v1 = expanded_v1["by_style"].get("TERSE", {}).get("fpr", 1.0)
    threshold_overall = 0.20
    threshold_formal = 0.25
    pass_overall = (overall_v1 < threshold_overall and formal_v1 < threshold_formal
                    and casual_v1 < threshold_overall and terse_v1 < threshold_overall)

    print()
    print("=" * 78)
    print("P2.2 ABLATION SUMMARY")
    print("=" * 78)
    print(f"v0 (original)    canonical: {canonical_v0['fpr_point_estimate']*100:5.2f}%   "
          f"expanded: {expanded_v0['fpr_point_estimate']*100:5.2f}%")
    print(f"v1 (restrained)  canonical: {canonical_v1['fpr_point_estimate']*100:5.2f}%   "
          f"expanded: {expanded_v1['fpr_point_estimate']*100:5.2f}%")
    print()
    print(f"v1 per-style on expanded corpus:")
    for s, b in expanded_v1["by_style"].items():
        print(f"  {s:<10} n={b['n']:2d}  FPR={b['fpr']*100:5.1f}%  "
              f"CI=[{b['ci'][0]*100:5.2f}%, {b['ci'][1]*100:5.2f}%]")
    print()
    print(f"Phase 2 acceptance threshold:")
    print(f"  expanded FPR < {threshold_overall*100:.0f}%  : {overall_v1 < threshold_overall}  (got {overall_v1*100:.2f}%)")
    print(f"  FORMAL  FPR < {threshold_formal*100:.0f}%  : {formal_v1 < threshold_formal}  (got {formal_v1*100:.2f}%)")
    print(f"  CASUAL  FPR < {threshold_overall*100:.0f}%  : {casual_v1 < threshold_overall}  (got {casual_v1*100:.2f}%)")
    print(f"  TERSE   FPR < {threshold_overall*100:.0f}%  : {terse_v1 < threshold_overall}  (got {terse_v1*100:.2f}%)")
    print()
    if pass_overall:
        print("→ ACCEPTANCE: PASS — config (b) v1 restrained meets thresholds.")
        print("  Phase 2 unblock: proceed with tasks 7-13 using v1 as canonical config.")
        return 0
    else:
        print("→ ACCEPTANCE: FAIL — v1 alone insufficient.")
        print("  Next step: add config (c) canonical-claim post-processor before tasks 7-13.")
        print("  If post-processor still insufficient, fire DECISION (fall back to Option B).")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
