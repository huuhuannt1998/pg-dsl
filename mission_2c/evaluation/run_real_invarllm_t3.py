"""Real-Qwen INVARLLM extraction + T3 composition empirical — Mission 2C task 9.

Pipeline:
  1. Real-Qwen extracts physical invariants from Mission 1B benign baseline
     (offline-extraction step of INVARLLM).
  2. The deterministic runtime check (Mission 2B's INVARLLMRuntime) applies
     the extracted invariants to each attack's runtime trajectory.
  3. T3 composition is computed as PG-DSL alone, INVARLLM alone, composed.

KEY VERIFICATION CONDITION (from dec_01KR3N1M8PB5YDXYV7B5DYJQET locked
witnesses): A2 (magnitude poisoning) MUST be missed by INVARLLM at runtime.
A2 is the canonical A_static-only witness — its lane membership in
A_static \\ A_runtime depends on INVARLLM missing it.

If INVARLLM catches A2, fire BLOCKING DECISION (would force another T3
witness reconsideration).

Output: results/real_invarllm_t3.json
        results/invarllm_extraction_real_qwen.json
"""

from __future__ import annotations
import json
import sys
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

from real_invarllm_extractor import extract_invariants_real_qwen
from real_admission_layer import RealLLMAdmissionLayer
from baselines import INVARLLMRuntime
from evaluation.run_t3_composition import SIMULATORS, _telemetry_dict, _actuator_sensor_snapshot


def load_benign_traces() -> list[dict]:
    benign_dir = M1B / "results" / "benign"
    out = []
    for path in sorted(benign_dir.glob("rep*.json")):
        rep = json.loads(path.read_text())
        traj = rep["trajectory"]
        out.append({
            "LIT101":  [s.get("LIT101") for s in traj],
            "LIT201":  [s.get("LIT201") for s in traj],
            "FIT101":  [s.get("FIT101") for s in traj],
            "FIT201":  [s.get("FIT201") for s in traj],
            "AIT201":  [s.get("AIT201") for s in traj],
            "actuator_per_step": [
                {a: s.get(a) for a in ("MV101","P101","P102","MV201")}
                for s in traj
            ],
        })
    return out


def evaluate_pgdsl(server, poisoned_tools: set[str], layer) -> dict:
    results = layer.gate_all_tools(server)
    rejected = [r.tool_name for r in results if not r.admitted and r.tool_name in poisoned_tools]
    if not poisoned_tools:
        return {"detected": False, "reason": "no_poisoned_tool_at_admission_time"}
    return {"detected": bool(rejected), "rejected_poisoned_tools": rejected}


def evaluate_invarllm(telem: dict, ids: INVARLLMRuntime) -> dict:
    rep = ids.check(telem)
    return {"detected": rep.fired, "n_violations": len(rep.violations),
            "first_violation": (rep.violations[0] if rep.violations else None)}


def main() -> int:
    # Step 1: real-Qwen extraction.
    print("=" * 78)
    print("Step 1 — Real-Qwen INVARLLM extraction on Mission 1B benign baseline")
    print("=" * 78)
    benign_traces = load_benign_traces()
    print(f"Loaded {len(benign_traces)} benign trajectories.")
    ids, extraction_record = extract_invariants_real_qwen(benign_traces)
    print(f"Real-Qwen returned {extraction_record['n_invariants']} invariants "
          f"in {extraction_record['latency_s']:.1f}s.")
    if extraction_record["parse_error"]:
        print(f"WARNING: extraction parse_error = {extraction_record['parse_error']}")
    for inv in ids.invariants:
        print(f"  {inv.name}: {inv.description}")

    (M2C / "results" / "invarllm_extraction_real_qwen.json").write_text(
        json.dumps(extraction_record, indent=2, default=str))

    # Step 2: apply to mixed-set attacks
    print()
    print("=" * 78)
    print("Step 2 — Apply runtime IDS to mixed attack set")
    print("=" * 78)
    pgdsl_layer = RealLLMAdmissionLayer(prompt_variant="v1")
    manifest = json.loads((M2B / "evaluation" / "mixed_attack_set.json").read_text())

    # locked lane mapping per dec_01KR3N1M8PB5YDXYV7B5DYJQET
    locked_lanes = {
        "A1": "intersection",
        "A2": "pgdsl_only",        # canonical A_static \ A_runtime
        "A3": "intersection",
        "W1": "invarllm_only",      # reclassified per Mission 2C
        "W2": "invarllm_only",      # always was
        "Z1": "intersection",
        "Z2": "intersection",
    }

    results = []
    print(f"\n{'ID':<4} {'Attack':<32} {'PG-DSL':<8} {'INVARLLM':<10} {'Composed':<10} Lane (locked)")
    print("-" * 95)
    for atk_meta in manifest["attacks"]:
        aid = atk_meta["id"]
        sim_factory = SIMULATORS[aid]()
        server_factory, runtime_executor, poisoned_tools = sim_factory

        # PG-DSL admission alone
        s_pg = server_factory()
        pg_verdict = evaluate_pgdsl(s_pg, poisoned_tools, pgdsl_layer)

        # INVARLLM runtime
        s_iv = server_factory()
        telem = runtime_executor(s_iv)
        iv_verdict = evaluate_invarllm(telem, ids)

        composed = pg_verdict["detected"] or iv_verdict["detected"]

        observed_lane = (
            "intersection" if pg_verdict["detected"] and iv_verdict["detected"]
            else "pgdsl_only" if pg_verdict["detected"]
            else "invarllm_only" if iv_verdict["detected"]
            else "missed"
        )
        marker = "✓" if observed_lane == locked_lanes[aid] else "✗"
        print(f"{aid:<4} {atk_meta['name'][:30]:<32} "
              f"{('detect' if pg_verdict['detected'] else 'miss'):<8} "
              f"{('detect' if iv_verdict['detected'] else 'miss'):<10} "
              f"{('detect' if composed else 'miss'):<10} "
              f"{observed_lane:<14} {marker}")
        results.append({
            "id": aid, "name": atk_meta["name"],
            "locked_lane": locked_lanes[aid],
            "observed_lane": observed_lane,
            "lane_matches_locked": observed_lane == locked_lanes[aid],
            "pgdsl": pg_verdict,
            "invarllm": iv_verdict,
            "composed_detected": composed,
        })

    # Lane-set summary
    A_static = {r["id"] for r in results if r["pgdsl"]["detected"]}
    A_runtime = {r["id"] for r in results if r["invarllm"]["detected"]}
    A_composed = {r["id"] for r in results if r["composed_detected"]}
    pgdsl_only = A_static - A_runtime
    invarllm_only = A_runtime - A_static

    strict_dominance = (A_composed == A_static | A_runtime
                        and len(pgdsl_only) > 0
                        and len(invarllm_only) > 0
                        and (A_composed > A_static)
                        and (A_composed > A_runtime))

    print()
    print("=" * 78)
    print("Step 3 — Lane membership and T3 strict-superset check")
    print("=" * 78)
    print(f"  A_static (PG-DSL detects)            : {sorted(A_static)}")
    print(f"  A_runtime (INVARLLM detects)         : {sorted(A_runtime)}")
    print(f"  A_static \\ A_runtime (PG-DSL only)   : {sorted(pgdsl_only)}")
    print(f"  A_runtime \\ A_static (INVARLLM only) : {sorted(invarllm_only)}")
    print(f"  composed                              : {sorted(A_composed)}")
    print()
    print(f"  Locked witnesses:")
    print(f"    A_static \\ A_runtime expected = {{A2}}")
    print(f"    A_runtime \\ A_static expected = {{W1, W2}}")
    print()

    # KEY witness verification: A2 must be in A_static \ A_runtime
    a2_pgdsl = next(r for r in results if r["id"] == "A2")
    a2_witness_holds = (a2_pgdsl["pgdsl"]["detected"]
                        and not a2_pgdsl["invarllm"]["detected"])
    print(f"  A2 PG-DSL detect       : {a2_pgdsl['pgdsl']['detected']}")
    print(f"  A2 INVARLLM detect     : {a2_pgdsl['invarllm']['detected']}")
    print(f"  A2 in A_static \\ A_runtime : {'PASS' if a2_witness_holds else 'FAIL — BLOCKING'}")

    print()
    print(f"T3 strict-superset prediction: "
          f"{'PASS' if strict_dominance else 'FAIL'}")

    out = {
        "n_attacks": len(results),
        "results": results,
        "lanes": {
            "A_static": sorted(A_static),
            "A_runtime": sorted(A_runtime),
            "pgdsl_only": sorted(pgdsl_only),
            "invarllm_only": sorted(invarllm_only),
            "composed": sorted(A_composed),
        },
        "locked_witnesses": {
            "A_static_only_expected": ["A2"],
            "A_runtime_only_expected": ["W1", "W2"],
        },
        "a2_witness_holds": a2_witness_holds,
        "t3_strict_dominance": strict_dominance,
        "extraction_record": extraction_record,
        "extracted_invariants": ids.to_summary(),
    }
    out_path = M2C / "results" / "real_invarllm_t3.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {out_path}")

    # Trigger conditions:
    if not a2_witness_holds:
        print("\n⚠  A2 is NOT in A_static \\ A_runtime — locked witness mapping invalid.")
        print("    BLOCKING DECISION CHECKPOINT to brain (witness reconsideration).")
        return 2
    if not strict_dominance:
        print("\n⚠  T3 strict-superset failed empirically.")
        print("    BLOCKING DECISION CHECKPOINT to brain.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
