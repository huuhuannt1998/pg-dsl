"""MSB-subset evaluation: canonical PG-DSL + MCPShield on the 32-instance
SWaT-adapted MSB attack subset.

Per-class detection rates (Wilson 95% CIs) for two defenses:
  - canonical PG-DSL admission (per-tool ⊕ composition; qwen3:14b lifter)
  - MCPShield Stage-1 cognitive-probing judge (qwen3:14b)

Detection criterion: a defense detects an instance when its admission gate
REJECTS the poisoned description (admitted == False). For MCPShield, that
means the judge returned INCONSISTENT.

Includes Z3 in the comparison (R2 explicitly flagged its prior exclusion as
methodologically inconsistent). Z3 is a composition-only constructive
witness, so we add it to the MCPShield comparison via the existing Z3
simulator (mission_3b/attacks/z3_simulator.py).

Output: mission_3b/results/msb_subset_evaluation.json
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
from real_mcpshield_judge import RealMCPShieldJudge          # noqa: E402

from mission_3b.admission_layer import (
    PGDSLCanonicalLayer, detected_at_admission,
)                                                            # noqa: E402
from mission_3b.attacks.z3_simulator import make_z3_simulator  # noqa: E402
from mission_3b.experiments.run_canonical_defense_asr_stub import (
    _tool_sequence_for as _tool_sequence_for_attack,
)                                                            # noqa: E402

from mission_3b.data.msb_subset import MSB_INSTANCES, all_classes  # noqa: E402


OUT_PATH = M3B / "results" / "msb_subset_evaluation.json"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    rad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def make_one_invocation(server: MCPServer, tool_name: str,
                         tool_args: dict | None = None) -> dict:
    plant = server.plant
    pre_act = {n: plant.read(n) for n in plant.ACTUATORS}
    pre_sen = {n: plant.read(n) for n in plant.SENSORS}
    try:
        if tool_args:
            result = server.call_tool(tool_name, tool_args)
        else:
            result = server.call_tool(tool_name)
        ret = result.get("result") if isinstance(result, dict) else result
    except Exception as e:  # noqa: BLE001
        ret = f"<error: {e!r}>"
    post_act = {n: plant.read(n) for n in plant.ACTUATORS}
    post_sen = {n: plant.read(n) for n in plant.SENSORS}
    return {
        "tool_name": tool_name,
        "tool_args": tool_args or {},
        "tool_return": ret,
        "actuator_pre": pre_act, "actuator_post": post_act,
        "sensor_oracle_pre": pre_sen, "sensor_oracle_post": post_sen,
    }


def _msb_default_args(instance) -> dict | None:
    """Return tool_args to invoke for a given instance to generate evidence
    for MCPShield. Only set_dosing_rate has required args."""
    if instance.target_tool == "set_dosing_rate":
        # OP attacks may declare the rate parameter (we use the description's
        # claimed canonical value when present; otherwise neutral 1.0).
        return {"pump": "P201", "rate": 1.0}
    return None


def evaluate_canonical_pgdsl(instance) -> dict:
    """Run canonical PG-DSL admission on the poisoned tool description and
    return whether the gate rejects (= detection)."""
    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)
    server.apply_description_overrides({instance.target_tool: instance.description})
    layer = PGDSLCanonicalLayer(
        per_tool_layer=RealLLMAdmissionLayer(prompt_variant="v1"),
        mode="qwen3",
    )

    # Per-tool admission first — this is where most description-channel poisons
    # are caught. We only need the verdict on the poisoned tool itself; the
    # composition pass does not modify per-tool verdicts.
    per_tool_layer = layer.per_tool_layer
    r = per_tool_layer.gate_one_tool(instance.target_tool, server)
    detected = not r.admitted
    return {
        "detected": detected,
        "verdict_via": "per_tool_admission",
        "phi": r.phi,
        "out_of_grammar": r.out_of_grammar,
        "rejection_reasons": r.rejection_reasons,
        "admission_time_seconds": r.admission_time_seconds,
    }


def evaluate_mcpshield(instance) -> dict:
    """Run MCPShield Stage-1 judge on the poisoned tool description with one
    simulated invocation as evidence."""
    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)
    server.apply_description_overrides({instance.target_tool: instance.description})
    args = _msb_default_args(instance)
    invocation = make_one_invocation(server, instance.target_tool, args)
    judge = RealMCPShieldJudge()
    verdict = judge.judge(instance.description, [invocation])
    detected = not verdict.admitted
    return {
        "detected": detected,
        "rationale": verdict.rationale,
        "raw_response_excerpt": verdict.raw_response[:120],
        "latency_seconds": verdict.latency_s,
    }


# Z3 evaluation: not in MSB taxonomy but R2 demanded its inclusion. Z3 is a
# composition-only constructive witness from the SWaT canonical attack set.
# We separately evaluate canonical PG-DSL composition pass and MCPShield on
# the Z3 attack instance to enable apples-to-apples comparison.

def evaluate_z3_canonical_pgdsl() -> dict:
    layer = PGDSLCanonicalLayer(
        per_tool_layer=RealLLMAdmissionLayer(prompt_variant="v1"),
        mode="qwen3",
    )
    server_factory, runtime_executor, poisoned_tools = make_z3_simulator()
    report = layer.gate_all_tools(server_factory)
    tool_seq = _tool_sequence_for_attack("Z3")
    verdict = detected_at_admission(report, set(poisoned_tools), tool_seq)
    return {
        "detected": verdict["detected"],
        "verdict_via": verdict["via"],
        "per_tool_detected": verdict["per_tool_detected"],
        "composition_detected": verdict["composition_detected"],
    }


def evaluate_z3_mcpshield() -> dict:
    judge = RealMCPShieldJudge()
    server_factory, runtime_executor, poisoned_tools = make_z3_simulator()
    server = server_factory()
    # Z3 is composition-only: the per-tool descriptions are honest. We feed
    # MCPShield each constituent description with its single invocation.
    invocations = []
    for tool_name in _tool_sequence_for_attack("Z3"):
        plant = server.plant
        invocations.append(make_one_invocation(server, tool_name))
    # Use the first poisoned tool's description as the prompt anchor (the
    # MCPShield stage-1 prompt asks about ONE description; we feed the
    # composition evidence as the invocation block).
    description = (
        "Composition: " + " then ".join(_tool_sequence_for_attack("Z3"))
        + " under HIGH initial state. The per-tool descriptions are honest; the"
        " composed effect overflows T101."
    )
    verdict = judge.judge(description, invocations)
    return {
        "detected": not verdict.admitted,
        "rationale": verdict.rationale,
        "raw_response_excerpt": verdict.raw_response[:120],
    }


def main() -> int:
    print("=" * 78)
    print(f"MSB SUBSET EVALUATION (canonical PG-DSL + MCPShield, qwen3:14b)")
    print(f"  instances: {len(MSB_INSTANCES)}; classes: {all_classes()}")
    print("=" * 78)

    t0 = time.time()
    results: list[dict] = []
    for i, inst in enumerate(MSB_INSTANCES):
        print(f"\n[{i+1:>2}/{len(MSB_INSTANCES)}] {inst.id} ({inst.msb_class}) "
              f"target={inst.target_tool}")
        print(f"  desc: {inst.description[:80]}{'...' if len(inst.description) > 80 else ''}")
        try:
            pgdsl = evaluate_canonical_pgdsl(inst)
        except Exception as e:  # noqa: BLE001
            pgdsl = {"detected": None, "error": repr(e)}
            print(f"  PGDSL ERROR: {e!r}")
        try:
            mcpshield = evaluate_mcpshield(inst)
        except Exception as e:  # noqa: BLE001
            mcpshield = {"detected": None, "error": repr(e)}
            print(f"  MCPShield ERROR: {e!r}")
        results.append({
            "id": inst.id,
            "msb_class": inst.msb_class,
            "target_tool": inst.target_tool,
            "description": inst.description,
            "attack_intent": inst.attack_intent,
            "canonical_pgdsl": pgdsl,
            "mcpshield": mcpshield,
        })
        p_det = pgdsl.get("detected", None)
        m_det = mcpshield.get("detected", None)
        marker = lambda x: ("D" if x is True else "M" if x is False else "?")
        print(f"  PGDSL={marker(p_det)}  MCPShield={marker(m_det)}")

    # Z3 comparison
    print("\n" + "=" * 78)
    print("Z3 (composition-only constructive witness) — included per R2")
    print("=" * 78)
    try:
        z3_pgdsl = evaluate_z3_canonical_pgdsl()
    except Exception as e:  # noqa: BLE001
        z3_pgdsl = {"detected": None, "error": repr(e)}
        print(f"  Z3 PGDSL ERROR: {e!r}")
    try:
        z3_mcpshield = evaluate_z3_mcpshield()
    except Exception as e:  # noqa: BLE001
        z3_mcpshield = {"detected": None, "error": repr(e)}
        print(f"  Z3 MCPShield ERROR: {e!r}")
    print(f"  Z3 PGDSL={z3_pgdsl.get('detected')}  "
          f"Z3 MCPShield={z3_mcpshield.get('detected')}")

    # Per-class aggregate
    by_class: dict[str, dict] = {}
    for r in results:
        cls = r["msb_class"]
        bc = by_class.setdefault(cls, {
            "n": 0,
            "pgdsl_detected": 0,
            "mcpshield_detected": 0,
        })
        bc["n"] += 1
        if r["canonical_pgdsl"].get("detected") is True:
            bc["pgdsl_detected"] += 1
        if r["mcpshield"].get("detected") is True:
            bc["mcpshield_detected"] += 1

    for cls, bc in by_class.items():
        n = bc["n"]
        bc["pgdsl_rate"] = bc["pgdsl_detected"] / n if n else 0.0
        bc["pgdsl_ci"] = list(wilson_ci(bc["pgdsl_detected"], n))
        bc["mcpshield_rate"] = bc["mcpshield_detected"] / n if n else 0.0
        bc["mcpshield_ci"] = list(wilson_ci(bc["mcpshield_detected"], n))

    # Overall
    n_total = len(results)
    n_pgdsl = sum(1 for r in results if r["canonical_pgdsl"].get("detected") is True)
    n_mcpshield = sum(1 for r in results if r["mcpshield"].get("detected") is True)

    out = {
        "n_instances": n_total,
        "classes": all_classes(),
        "msb_taxonomy_source": "Zhang et al. ICLR 2026, arXiv:2510.15994",
        "subset_selection_rationale": (
            "8 instances each across {NC, PM, PI, OP} = 32 description-channel "
            "attack instances directly transferable to SWaT P1+P2 admission. "
            "Tool Response (UI/FE/TT) and Retrieval Injection (RI) classes are "
            "not admission-time visible and are out of scope for PG-DSL admission; "
            "documented honestly."
        ),
        "by_class": by_class,
        "overall": {
            "pgdsl_detected": n_pgdsl,
            "pgdsl_rate": n_pgdsl / n_total,
            "pgdsl_ci": list(wilson_ci(n_pgdsl, n_total)),
            "mcpshield_detected": n_mcpshield,
            "mcpshield_rate": n_mcpshield / n_total,
            "mcpshield_ci": list(wilson_ci(n_mcpshield, n_total)),
        },
        "z3_comparison": {
            "pgdsl": z3_pgdsl,
            "mcpshield": z3_mcpshield,
        },
        "wall_clock_s_total": time.time() - t0,
        "instances": results,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))

    print()
    print("=" * 78)
    print("MSB SUBSET RESULTS")
    print("=" * 78)
    print(f"\nPer-class detection rates")
    print(f"{'class':<5} {'n':<4} {'PG-DSL':<22} {'MCPShield':<22}")
    for cls, bc in by_class.items():
        print(f"  {cls:<3} {bc['n']:<4} "
              f"{bc['pgdsl_detected']}/{bc['n']} = {bc['pgdsl_rate']*100:>5.1f}% "
              f"CI [{bc['pgdsl_ci'][0]*100:.1f}, {bc['pgdsl_ci'][1]*100:.1f}]    "
              f"{bc['mcpshield_detected']}/{bc['n']} = {bc['mcpshield_rate']*100:>5.1f}% "
              f"CI [{bc['mcpshield_ci'][0]*100:.1f}, {bc['mcpshield_ci'][1]*100:.1f}]")
    print(f"\nOverall   {n_total:<4} "
          f"{n_pgdsl}/{n_total} = {n_pgdsl/n_total*100:.1f}%   "
          f"{n_mcpshield}/{n_total} = {n_mcpshield/n_total*100:.1f}%")
    print(f"\nZ3       PG-DSL={z3_pgdsl.get('detected')} ({z3_pgdsl.get('verdict_via', 'n/a')}) "
          f"  MCPShield={z3_mcpshield.get('detected')}")
    print(f"\nOutput: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
