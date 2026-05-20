"""Real-Qwen MCPShield comparison — Mission 2C task 8.

Runs RealMCPShieldJudge across:
  - 7 mixed-set attacks (probe with one simulated invocation per attack)
  - Mission 2B's 42-tool benign expanded corpus (probe with one invocation each)

If MCPShield outperforms PG-DSL on any attack, fire BLOCKING DECISION.

Output: results/real_mcpshield_eval.json
"""

from __future__ import annotations

import json
import math
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

from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer
from real_mcpshield_judge import RealMCPShieldJudge
from evaluation.run_t3_composition import SIMULATORS

ATTACK_PROBE = {
    "A1": ("open_valve_MV101", None),
    "A2": ("set_dosing_rate", {"pump": "P201", "rate": 0.0167}),
    "A3": ("read_level_T101", None),
    "W1": ("close_valve_MV101", None),
    "W2": (None, None),
    "Z1": ("open_valve_MV201", None),
    "Z2": ("set_dosing_rate", {"pump": "P201", "rate": 10.0}),
}


def make_invocation(server: MCPServer, tool_name: str, args=None) -> dict:
    plant = server.plant
    pre_act = {n: plant.read(n) for n in plant.ACTUATORS}
    pre_sen = {n: plant.read(n) for n in plant.SENSORS}
    if args:
        result = server.call_tool(tool_name, args)
    else:
        result = server.call_tool(tool_name)
    post_act = {n: plant.read(n) for n in plant.ACTUATORS}
    post_sen = {n: plant.read(n) for n in plant.SENSORS}
    return {"tool_name": tool_name, "tool_args": args or {},
            "tool_return": result.get("result"),
            "actuator_pre": pre_act, "actuator_post": post_act,
            "sensor_oracle_pre": pre_sen, "sensor_oracle_post": post_sen}


def wilson_ci(k: int, n: int, z: float = 1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n; denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    rad = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0.0, centre - rad), min(1.0, centre + rad))


def run_attack_campaign(judge: RealMCPShieldJudge) -> list[dict]:
    manifest = json.loads((M2B / "evaluation" / "mixed_attack_set.json").read_text())
    out = []
    print(f"\n=== Real-Qwen MCPShield judge on mixed attack set ===")
    print(f"{'ID':<4} {'Attack':<32} {'Verdict':<10}  Rationale")
    print("-" * 100)
    for atk_meta in manifest["attacks"]:
        aid = atk_meta["id"]
        probe_tool, probe_args = ATTACK_PROBE[aid]
        if probe_tool is None:
            out.append({"id": aid, "name": atk_meta["name"],
                        "mcpshield_detected": False,
                        "rationale": "no admission-time evidence (W2 designed runtime-only)",
                        "raw": ""})
            print(f"{aid:<4} {atk_meta['name'][:30]:<32} {'n/a':<10}  no admission evidence (W2)")
            continue

        sim_factory = SIMULATORS[aid]()
        server_factory, _, _ = sim_factory
        server = server_factory()
        invocation = make_invocation(server, probe_tool, probe_args)
        description = server._tools[probe_tool].description

        verdict = judge.judge(description, [invocation])
        detected = not verdict.admitted
        verdict_str = "detect" if detected else "miss"
        print(f"{aid:<4} {atk_meta['name'][:30]:<32} {verdict_str:<10}  {verdict.rationale[:60]}")
        out.append({
            "id": aid, "name": atk_meta["name"],
            "probe_tool": probe_tool, "probe_args": probe_args,
            "mcpshield_detected": detected,
            "rationale": verdict.rationale,
            "raw_response": verdict.raw_response,
            "latency_s": verdict.latency_s,
        })
    return out


def run_benign_campaign(judge: RealMCPShieldJudge) -> dict:
    corpus = json.loads((M2B / "evaluation" / "benign_corpus_expanded.json").read_text())
    decisions = []
    n_admit = 0
    print(f"\n=== Real-Qwen MCPShield judge on expanded benign corpus ({len(corpus)}) ===")
    for entry in corpus:
        plant = SwatP1P2Plant(PlantParams())
        server = MCPServer(plant)
        server.apply_description_overrides({entry["tool_name"]: entry["description"]})
        if entry["tool_name"] == "set_dosing_rate":
            inv = make_invocation(server, entry["tool_name"], {"pump": "P201", "rate": 1.0})
        else:
            inv = make_invocation(server, entry["tool_name"])
        verdict = judge.judge(entry["description"], [inv])
        if verdict.admitted:
            n_admit += 1
        decisions.append({
            "tool_name": entry["tool_name"], "style": entry["style"],
            "admitted": verdict.admitted, "rationale": verdict.rationale,
        })
    fpr = (len(corpus) - n_admit) / len(corpus)
    ci = wilson_ci(len(corpus) - n_admit, len(corpus))
    print(f"\n  benign FPR: {len(corpus)-n_admit}/{len(corpus)} = {fpr*100:.2f}%, CI=[{ci[0]*100:.2f}%, {ci[1]*100:.2f}%]")
    return {"n_total": len(corpus), "n_admit": n_admit,
            "fpr_point_estimate": fpr, "fpr_wilson_ci_95": list(ci),
            "decisions": decisions}


def main() -> int:
    judge = RealMCPShieldJudge()

    attack_results = run_attack_campaign(judge)
    benign_results = run_benign_campaign(judge)

    # Compare against PG-DSL real-LLM defense ASR.
    pgdsl_results = json.loads((M2C / "results" / "real_defense_asr.json").read_text())
    pgdsl_per_atk = {r["id"]: r["pgdsl_real_detected"] for r in pgdsl_results["results"]}
    mcps_per_atk = {r["id"]: r["mcpshield_detected"] for r in attack_results}

    pgdsl_better, mcps_better, both_match = [], [], []
    for aid in pgdsl_per_atk:
        p = pgdsl_per_atk[aid]
        m = mcps_per_atk.get(aid, False)
        if p == m: both_match.append(aid)
        elif p and not m: pgdsl_better.append(aid)
        else: mcps_better.append(aid)

    print()
    print("Comparison (PG-DSL vs MCPShield, per-attack):")
    print(f"  PG-DSL detect + MCPShield miss : {pgdsl_better}")
    print(f"  MCPShield detect + PG-DSL miss : {mcps_better}")
    print(f"  Both same                       : {both_match}")
    if mcps_better:
        print("⚠  MCPShield outperformed PG-DSL on at least one attack — BLOCKING DECISION trigger.")
    else:
        print("PG-DSL ≥ MCPShield on every attack. No blocker.")

    out = {
        "attack_campaign": attack_results,
        "benign_campaign": benign_results,
        "comparison": {
            "pgdsl_better": pgdsl_better,
            "mcpshield_better": mcps_better,
            "both_match": both_match,
            "trigger_blocking_decision": bool(mcps_better),
        },
    }
    out_path = M2C / "results" / "real_mcpshield_eval.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nOutput: {out_path}")
    return 0 if not mcps_better else 2


if __name__ == "__main__":
    raise SystemExit(main())
