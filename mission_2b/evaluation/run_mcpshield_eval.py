"""MCPShield-style judge comparison campaign.

Mission 2B task 8 (mis_01KR3FJ9JJP5EKEFQ1AVFPPAZE).

Runs the MCPShield-style judge on:
  - The mixed attack set (7 attacks from task 6) for ASR.
  - The expanded benign corpus (42 entries from task 4) for FPR.

For each attack, generate one simulated invocation against a fresh plant and
present (description, [invocation_evidence]) to the judge — the canonical
MCPShield Stage-1 input. For benign corpus, do the same with the honest
description and a clean invocation.

If MCPShield outperforms PG-DSL on any attack class, fire CLARIFICATION
(per Mission 2B checkpoint trigger).

Output: results/mcpshield_eval.json
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
sys.path.insert(0, str(M2B))

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer, Tool
from baselines import MCPShieldJudge

from run_t3_composition import (
    SIMULATORS, _actuator_sensor_snapshot,
)


def make_one_invocation(server: MCPServer, tool_name: str,
                         tool_args: dict | None = None) -> dict:
    """Generate the Stage-1 invocation evidence packet for the judge."""
    plant = server.plant
    pre_act = {n: plant.read(n) for n in plant.ACTUATORS}
    pre_sen = {n: plant.read(n) for n in plant.SENSORS}
    if tool_args:
        result = server.call_tool(tool_name, tool_args)
    else:
        result = server.call_tool(tool_name)
    post_act = {n: plant.read(n) for n in plant.ACTUATORS}
    post_sen = {n: plant.read(n) for n in plant.SENSORS}
    return {
        "tool_name": tool_name,
        "tool_args": tool_args or {},
        "tool_return": result.get("result"),
        "actuator_pre": pre_act, "actuator_post": post_act,
        "sensor_oracle_pre": pre_sen, "sensor_oracle_post": post_sen,
    }


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    rad = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


# Map each attack to (poisoned_tool_name, args_to_invoke).
# This drives invocation generation specifically for the attack-relevant tool.
ATTACK_PROBE = {
    "A1": ("open_valve_MV101", None),
    "A2": ("set_dosing_rate", {"pump": "P201", "rate": 0.0167}),
    "A3": ("read_level_T101", None),
    "W1": ("close_valve_MV101", None),
    "W2": (None, None),  # no poisoned tool — W2 has nothing for the judge to inspect at admission
    "Z1": ("open_valve_MV201", None),
    "Z2": ("set_dosing_rate", {"pump": "P201", "rate": 10.0}),
}


def run_attack_campaign() -> list[dict]:
    judge = MCPShieldJudge()
    manifest = json.loads((HERE / "mixed_attack_set.json").read_text())
    out: list[dict] = []
    print(f"\n=== MCPShield judge on mixed attack set ===")
    print(f"{'ID':<4} {'Attack':<32} {'MCPShield':<10} {'Lane':<14} Notes")
    print("-" * 90)
    for atk_meta in manifest["attacks"]:
        aid = atk_meta["id"]
        probe_tool, probe_args = ATTACK_PROBE[aid]

        if probe_tool is None:
            # W2 has no poisoned admission-time artefact — judge has nothing to evaluate.
            verdict_str = "n/a"
            detected = False  # MCPShield is structurally blind here
            verdict_dict = {"detected": False,
                            "rationale": "no poisoned tool at admission; structural miss"}
            print(f"{aid:<4} {atk_meta['name'][:30]:<32} {verdict_str:<10} "
                  f"{'invarllm_only':<14} (no admission-time evidence)")
            out.append({
                "id": aid, "name": atk_meta["name"],
                "mcpshield_detected": False,
                "verdict": verdict_dict,
            })
            continue

        sim_factory = SIMULATORS[aid]()
        server_factory, _, _ = sim_factory
        server = server_factory()
        invocation = make_one_invocation(server, probe_tool, probe_args)
        description = server._tools[probe_tool].description

        verdict = judge.judge(description, [invocation])
        detected = not verdict.admitted   # detection = judge rejects

        verdict_str = "detect" if detected else "miss"
        notes = verdict.failed_checks[:1] if verdict.failed_checks else verdict.rationale[:60]
        print(f"{aid:<4} {atk_meta['name'][:30]:<32} {verdict_str:<10} "
              f"{atk_meta['lane']:<14} {notes}")
        out.append({
            "id": aid, "name": atk_meta["name"],
            "probe_tool": probe_tool, "probe_args": probe_args,
            "mcpshield_detected": detected,
            "verdict": {
                "admitted": verdict.admitted,
                "rationale": verdict.rationale,
                "failed_checks": verdict.failed_checks,
            },
        })
    return out


def run_benign_campaign() -> dict:
    judge = MCPShieldJudge()
    corpus = json.loads((HERE / "benign_corpus_expanded.json").read_text())
    out: list[dict] = []
    n_admit = 0
    print(f"\n=== MCPShield judge on expanded benign corpus ({len(corpus)} entries) ===")
    for entry in corpus:
        tool_name = entry["tool_name"]
        description = entry["description"]
        plant = SwatP1P2Plant(PlantParams())
        server = MCPServer(plant)
        # Mount the corpus description on this server.
        server.apply_description_overrides({tool_name: description})
        # Default invocation — empty args, except for set_dosing_rate where we use the
        # description's nominal rate (1.0) since this is an honest description.
        if tool_name == "set_dosing_rate":
            invocation = make_one_invocation(server, tool_name, {"pump": "P201", "rate": 1.0})
        else:
            invocation = make_one_invocation(server, tool_name)
        verdict = judge.judge(description, [invocation])
        if verdict.admitted:
            n_admit += 1
        out.append({
            "tool_name": tool_name, "style": entry["style"],
            "description": description[:80] + ("..." if len(description) > 80 else ""),
            "admitted": verdict.admitted,
            "failed_checks": verdict.failed_checks,
        })
    fpr = (len(corpus) - n_admit) / len(corpus) if corpus else 0.0
    ci_lo, ci_hi = wilson_ci(len(corpus) - n_admit, len(corpus))

    print(f"\n  benign admitted        : {n_admit}/{len(corpus)}")
    print(f"  benign rejected (FPR)  : {len(corpus) - n_admit}")
    print(f"  point-estimate FPR     : {fpr*100:.2f}%")
    print(f"  Wilson 95% CI          : [{ci_lo*100:.2f}%, {ci_hi*100:.2f}%]")

    return {
        "n_total": len(corpus),
        "n_admitted": n_admit,
        "n_rejected": len(corpus) - n_admit,
        "fpr_point_estimate": fpr,
        "fpr_wilson_ci_95": [ci_lo, ci_hi],
        "decisions": out,
    }


def main() -> int:
    attack_results = run_attack_campaign()
    benign_results = run_benign_campaign()

    # PG-DSL outperforms-MCPShield comparison: load PG-DSL T3 composition results.
    pgdsl_t3 = json.loads((M2B / "results" / "t3_composition.json").read_text())
    pgdsl_detect_per_atk = {r["id"]: r["pgdsl"]["detected"] for r in pgdsl_t3["results"]}
    mcpshield_detect_per_atk = {r["id"]: r["mcpshield_detected"] for r in attack_results}

    pgdsl_only_better, mcpshield_better, both_match = [], [], []
    for aid in pgdsl_detect_per_atk:
        p, m = pgdsl_detect_per_atk[aid], mcpshield_detect_per_atk[aid]
        if p == m:
            both_match.append(aid)
        elif p and not m:
            pgdsl_only_better.append(aid)
        else:
            mcpshield_better.append(aid)

    print()
    print("Comparison (per-attack detection):")
    print(f"  PG-DSL detects + MCPShield misses : {pgdsl_only_better}")
    print(f"  MCPShield detects + PG-DSL misses : {mcpshield_better}")
    print(f"  Both same                          : {both_match}")
    print()
    if mcpshield_better:
        print("⚠  MCPShield outperformed PG-DSL on at least one attack class.")
        print("    Per Mission 2B trigger: CLARIFICATION CHECKPOINT to brain.")
    else:
        print("PG-DSL ≥ MCPShield on every attack class. No CLARIFICATION fires.")

    out = {
        "attack_campaign": attack_results,
        "benign_campaign": benign_results,
        "comparison": {
            "pgdsl_only_better": pgdsl_only_better,
            "mcpshield_better": mcpshield_better,
            "both_match": both_match,
            "trigger_clarification": bool(mcpshield_better),
        },
    }
    out_path = M2B / "results" / "mcpshield_eval.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
