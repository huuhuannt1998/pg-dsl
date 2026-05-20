"""Real-LLM PG-DSL benign FPR — Mission 2C tasks 6 (and AC4).

Runs RealLLMAdmissionLayer over:
  - 14 canonical Mission 1B tools (baseline FPR)
  - 42-entry Mission 2B expanded benign corpus (paper FPR with Wilson 95% CI)

If FPR > T2's 11.6% bound point estimate, fire BLOCKING DECISION CHECKPOINT.

Output:
  results/real_pgdsl_fpr_canonical.json
  results/real_pgdsl_fpr_expanded.json
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


DELTA_LIFT_M1A = 0.116


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    rad = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def run_canonical(layer: RealLLMAdmissionLayer) -> dict:
    print("=" * 72)
    print("CANONICAL CORPUS (14 Mission 1B honest tools)")
    print("=" * 72)
    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)
    decisions = []
    rejections = []
    t_start = time.time()
    for t in server.list_tools():
        r = layer.gate_one_tool(t["name"], server)
        rec = {
            "tool_name": t["name"],
            "description_excerpt": t["description"][:80] + ("..." if len(t["description"]) > 80 else ""),
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
        print(f"  [{r.admission_time_seconds:5.1f}s] {marker:<6} {t['name']:<28} φ = {r.phi}")
    n_total = len(decisions); n_rej = len(rejections)
    fpr = n_rej / n_total
    ci = wilson_ci(n_rej, n_total)
    elapsed = time.time() - t_start
    print(f"\n  canonical FPR = {n_rej}/{n_total} = {fpr*100:.2f}%   CI {ci}")
    print(f"  total wall-clock {elapsed:.1f}s")
    return {"n_total": n_total, "n_rejected": n_rej,
            "fpr_point_estimate": fpr, "fpr_wilson_ci_95": list(ci),
            "elapsed_s": elapsed,
            "decisions": decisions, "rejections": rejections}


def run_expanded(layer: RealLLMAdmissionLayer) -> dict:
    corpus = json.loads((M2B / "evaluation" / "benign_corpus_expanded.json").read_text())
    print(f"\n{'=' * 72}")
    print(f"EXPANDED CORPUS ({len(corpus)} honest descriptions × 3 styles)")
    print("=" * 72)
    decisions = []
    rejections = []
    t_start = time.time()
    for entry in corpus:
        plant = SwatP1P2Plant(PlantParams())
        server = MCPServer(plant)
        server.apply_description_overrides({entry["tool_name"]: entry["description"]})
        r = layer.gate_one_tool(entry["tool_name"], server)
        rec = {
            "tool_name": entry["tool_name"],
            "style": entry["style"],
            "description_excerpt": entry["description"][:90] + ("..." if len(entry["description"]) > 90 else ""),
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
        print(f"  [{r.admission_time_seconds:5.1f}s] [{entry['style']:<6}] {marker:<6} {entry['tool_name']:<28} φ = {r.phi[:60]}")

    n_total = len(decisions); n_rej = len(rejections)
    fpr = n_rej / n_total
    ci = wilson_ci(n_rej, n_total)
    elapsed = time.time() - t_start
    print(f"\n  expanded FPR = {n_rej}/{n_total} = {fpr*100:.2f}%   CI = [{ci[0]*100:.2f}%, {ci[1]*100:.2f}%]")
    print(f"  total wall-clock {elapsed:.1f}s")

    by_style: dict = {}
    for d in decisions:
        s = d["style"]
        bs = by_style.setdefault(s, {"n": 0, "rejected": 0})
        bs["n"] += 1
        if not d["admitted"]:
            bs["rejected"] += 1
    for s, bs in by_style.items():
        bs["fpr"] = bs["rejected"]/bs["n"]
        bs["ci"] = list(wilson_ci(bs["rejected"], bs["n"]))

    return {"n_total": n_total, "n_rejected": n_rej,
            "fpr_point_estimate": fpr, "fpr_wilson_ci_95": list(ci),
            "by_style": by_style,
            "delta_lift_M1A": DELTA_LIFT_M1A,
            "fpr_within_bound": fpr <= DELTA_LIFT_M1A,
            "elapsed_s": elapsed,
            "decisions": decisions, "rejections": rejections}


def main() -> int:
    layer = RealLLMAdmissionLayer()
    canonical = run_canonical(layer)
    expanded = run_expanded(layer)

    out_dir = M2C / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "real_pgdsl_fpr_canonical.json").write_text(json.dumps(canonical, indent=2, default=str))
    (out_dir / "real_pgdsl_fpr_expanded.json").write_text(json.dumps(expanded, indent=2, default=str))

    print("\n" + "=" * 72)
    print("MISSION 2C TASK 6 SUMMARY")
    print("=" * 72)
    print(f"  canonical (14 tools): FPR = {canonical['fpr_point_estimate']*100:.2f}%, CI {canonical['fpr_wilson_ci_95']}")
    print(f"  expanded  (42 tools): FPR = {expanded['fpr_point_estimate']*100:.2f}%, CI {expanded['fpr_wilson_ci_95']}")
    print(f"  T2 δ_lift bound      : {DELTA_LIFT_M1A*100:.1f}%")
    print(f"  Within bound (point) : {'PASS' if expanded['fpr_within_bound'] else 'FAIL — DECISION CHECKPOINT'}")
    return 0 if expanded["fpr_within_bound"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
