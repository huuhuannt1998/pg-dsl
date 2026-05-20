"""Mission 3B canonical T3 partition — qwen3:14b real-lifter mode.

Empirically partitions the 8 canonical attacks {A1..Z3} into detection
lanes under the canonical pipeline:

  Canonical ⊕ INVARLLM:
    intersection      both detect
    canonical_only    only canonical PG-DSL (per-tool ⊕ composition)
    invarllm_only     only INVARLLM runtime IDS
    missed            neither

Compared with Mission 2B's per-tool-only partition, the canonical column
should expand A_static by Z3 (and possibly other composition catches),
preserve A_runtime as the runtime-IDS-only lane, and verify that
A_static \\ A_runtime is non-empty (per T3 strict-superset prediction).

Output: mission_3b/results/t3_partition_canonical.json
"""

from __future__ import annotations

import json
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

from real_admission_layer import RealLLMAdmissionLayer       # noqa: E402

from mission_3b.admission_layer import (
    PGDSLCanonicalLayer,
    detected_at_admission,
)                                                             # noqa: E402
from mission_3b.attacks.z3_simulator import (
    make_z3_simulator,
    Z3_TOOL_SEQUENCE,
    Z3_MANIFEST,
)                                                             # noqa: E402

from evaluation.run_t3_composition import SIMULATORS as M2B_SIMULATORS  # noqa: E402
from baselines import INVARLLMRuntime                          # noqa: E402

from mission_3b.experiments.run_canonical_defense_asr_stub import (
    _tool_sequence_for as _tool_sequence_for_attack,
)                                                              # noqa: E402


class _CachedRealLifter:
    def __init__(self, real_lifter) -> None:
        self._inner = real_lifter
        self._cache: dict[tuple[str, str], object] = {}

    def lift(self, name: str, description: str):
        key = (name, description)
        if key not in self._cache:
            self._cache[key] = self._inner.lift(name, description)
        return self._cache[key]


def _build_invarllm():
    benign_dir = M1B / "results" / "benign"
    benign_traces = []
    for path in sorted(benign_dir.glob("rep*.json")):
        rep = json.loads(path.read_text())
        traj = rep["trajectory"]
        benign_traces.append({
            "LIT101":  [s.get("LIT101") for s in traj],
            "LIT201":  [s.get("LIT201") for s in traj],
            "FIT101":  [s.get("FIT101") for s in traj],
            "FIT201":  [s.get("FIT201") for s in traj],
            "AIT201":  [s.get("AIT201") for s in traj],
            "actuator_per_step": [
                {a: s.get(a) for a in ("MV101", "P101", "P102", "MV201")}
                for s in traj
            ],
        })
    return INVARLLMRuntime.extract_from_traces(benign_traces), len(benign_traces)


def main() -> int:
    real_layer = RealLLMAdmissionLayer(prompt_variant="v1")
    real_layer.lifter = _CachedRealLifter(real_layer.lifter)
    canonical = PGDSLCanonicalLayer(per_tool_layer=real_layer, mode="qwen3")

    ids, n_benign = _build_invarllm()
    print(f"INVARLLM extracted {len(ids.invariants)} invariants from {n_benign} benign traces.")

    sims = dict(M2B_SIMULATORS)
    sims["Z3"] = make_z3_simulator
    aids = ("A1", "A2", "A3", "W1", "W2", "Z1", "Z2", "Z3")

    print("=" * 90)
    print("MISSION 3B — Canonical T3 Partition (qwen3:14b)")
    print(f"{'ID':<4} {'Canonical':<11} {'INVARLLM':<10} {'Lane':<18} ")
    print("-" * 90)

    results: list[dict] = []
    t_start = time.time()
    for aid in aids:
        sim_factory = sims[aid]
        server_factory, runtime_executor, poisoned_tools = sim_factory()

        # Canonical PG-DSL admission
        report = canonical.gate_all_tools(server_factory)
        tool_seq = _tool_sequence_for_attack(aid)
        canonical_verdict = detected_at_admission(report, set(poisoned_tools), tool_seq)

        # INVARLLM runtime
        server = server_factory()
        telemetry = runtime_executor(server)
        invarllm_report = ids.check(telemetry)

        canon = canonical_verdict["detected"]
        invar = invarllm_report.fired
        lane = (
            "intersection"   if canon and invar
            else "canonical_only" if canon and not invar
            else "invarllm_only"  if invar and not canon
            else "missed"
        )
        print(f"{aid:<4} "
              f"{('detect' if canon else 'miss'):<11} "
              f"{('detect' if invar else 'miss'):<10} "
              f"{lane:<18} via={canonical_verdict['via']}")

        results.append({
            "id": aid,
            "tool_sequence": tool_seq,
            "poisoned_tools": list(poisoned_tools),
            "canonical_pgdsl": {
                "detected": canon,
                "via": canonical_verdict["via"],
                "per_tool_detected": canonical_verdict["per_tool_detected"],
                "composition_detected": canonical_verdict["composition_detected"],
                "rejected_poisoned_tools": canonical_verdict["rejected_poisoned_tools"],
                "composition_hits": canonical_verdict["composition_hits"],
            },
            "invarllm": {
                "detected": invar,
                "violations": invarllm_report.violations[:3],
                "n_invariants_evaluated": invarllm_report.invariants_evaluated,
            },
            "lane": lane,
        })

    A_canonical = {r["id"] for r in results if r["canonical_pgdsl"]["detected"]}
    A_runtime   = {r["id"] for r in results if r["invarllm"]["detected"]}
    A_composed  = A_canonical | A_runtime
    canonical_only = A_canonical - A_runtime
    runtime_only   = A_runtime - A_canonical
    intersection   = A_canonical & A_runtime
    missed         = set(aids) - A_composed

    print()
    print("Lane sets")
    print(f"  A_canonical         : {sorted(A_canonical)}")
    print(f"  A_runtime           : {sorted(A_runtime)}")
    print(f"  intersection        : {sorted(intersection)}")
    print(f"  canonical_only      : {sorted(canonical_only)}")
    print(f"  invarllm_only       : {sorted(runtime_only)}")
    print(f"  missed (neither)    : {sorted(missed)}")
    print(f"  composed            : {sorted(A_composed)}")
    print()
    strict_superset = (
        A_composed > A_canonical and A_composed > A_runtime
        and len(canonical_only) > 0 and len(runtime_only) > 0
    )
    print(f"T3 strict-superset (canonical ⊕ INVARLLM): {'PASS' if strict_superset else 'FAIL'}")

    out = {
        "mode": "qwen3",
        "model": "qwen3:14b",
        "n_attacks": len(aids),
        "results": results,
        "lanes": {
            "A_canonical": sorted(A_canonical),
            "A_runtime": sorted(A_runtime),
            "intersection": sorted(intersection),
            "canonical_only": sorted(canonical_only),
            "invarllm_only": sorted(runtime_only),
            "missed": sorted(missed),
            "composed": sorted(A_composed),
        },
        "t3_strict_superset_canonical_invarllm": strict_superset,
        "wall_clock_s_total": time.time() - t_start,
    }
    out_path = M3B / "results" / "t3_partition_canonical.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {out_path}")
    return 0 if strict_superset else 2


if __name__ == "__main__":
    raise SystemExit(main())
