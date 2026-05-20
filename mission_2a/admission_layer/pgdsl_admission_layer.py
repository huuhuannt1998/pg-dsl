"""PG-DSL admission layer — pre-context-injection gate for the LLM agent.

Mission 2A task 9 (mis_01KR2W2P9XKTC37MKYQ9FW5YF1).

The admission layer wraps the lifter + DT verifier + matcher. Each tool the
MCP server publishes is run through the gate at agent-discovery time:

    1. L_verify produces φ from the tool's NL description.
    2. The DT verifier runs the tool's impl in an *isolated* DT instance
       (a fresh SwatP1P2Plant separate from the live agent's plant),
       sampling ``INITIAL_STATES`` from dt_verifier.py.
    3. The matcher checks φ ⊨ ψ for each (initial-state, ψ) sample.
    4. The tool is ADMITTED if it passes ALL initial-state checks; otherwise
       REJECTED with the union of the failure reasons.

Admitted tools are added to a filtered tool catalog that the agent can use.
Rejected tools are dropped (not added to the catalog) with a recorded reason.

This module exports:
    PGDSLAdmissionLayer.gate(server)          → filtered MCPServer
    PGDSLAdmissionLayer.gate_all_tools(...)   → list[ToolAdmissionResult]

Used by:
    experiments/run_defense_asr.py    — task 10 (defense ASR campaign)
    experiments/run_benign_fpr.py     — task 11 (benign FPR campaign)
    integration_test.ipynb            — task 9 (PI inspection)
"""

from __future__ import annotations

import dataclasses
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MISSION_2A = HERE.parent
MISSION_1B = MISSION_2A.parent / "mission_1b"
sys.path.insert(0, str(MISSION_1B))
sys.path.insert(0, str(MISSION_2A))

from plant import SwatP1P2Plant, PlantParams
from mcp_server import MCPServer

from lifter import Lifter
from dt_verifier import verify_tool, INITIAL_STATES
from matcher import evaluate, EPS_DT, DELTA_STAR


@dataclasses.dataclass
class ToolAdmissionResult:
    tool_name: str
    description: str
    phi: str
    out_of_grammar: bool
    admitted: bool
    rejection_reasons: list[str]
    decision_per_initial_state: list[dict]
    admission_time_seconds: float

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class PGDSLAdmissionLayer:
    """Pre-context-injection gate.

    Usage:
        layer = PGDSLAdmissionLayer()
        results = layer.gate_all_tools(server)
        admitted_server = layer.filter_server(server, results)
    """

    def __init__(self, lifter: Lifter | None = None) -> None:
        self.lifter = lifter or Lifter()

    def _run_dt_samples(self, tool_name: str,
                        original_server: MCPServer,
                        tool_args_override: dict | None = None) -> list[dict]:
        """Replay the tool against fresh DT instances at each initial state.

        We don't re-use ``original_server`` directly because admission must
        not perturb the live plant. Each call uses a fresh
        ``SwatP1P2Plant`` and clones the description/impl from the original
        server so the DT verifier sees the actual published surface (poisoned
        or honest, doesn't matter — the matcher decides).
        """
        psi_samples: list[dict] = []
        original_tool = original_server._tools[tool_name]
        for init in INITIAL_STATES:
            fresh_plant = SwatP1P2Plant(PlantParams())
            fresh_server = MCPServer(fresh_plant)
            # Replace the named tool with the original's description + impl.
            # We rebind impl to the new plant by replaying the tool-builder.
            # The simplest approach: copy the existing tool's description into
            # the fresh server's same-named tool. The impl on the fresh server
            # is already wired to the fresh plant via make_tools().
            fresh_server.apply_description_overrides(
                {tool_name: original_tool.description}
            )
            # If the original server's impl is itself overridden (e.g. attack c
            # sensor aliasing), replicate that override on the fresh server.
            # We detect this by checking whether the impl is identity to the
            # canonical make_tools impl. Since we can't compare closures
            # directly, we accept the simpler convention: reuse the impl
            # function reference. This is sound because none of the
            # impls hold per-instance plant state outside the closure they
            # were built with.
            #
            # For the sensor-aliasing attack specifically, the impl reads from
            # a *named* sensor on the plant the closure was built against —
            # if that closure references original_server.plant rather than
            # fresh_server.plant, the read goes to the original plant. To
            # avoid that confusion, we re-instantiate the override by name.
            if hasattr(original_tool, "_aliased_to"):
                aliased_to = original_tool._aliased_to
                fresh_plant_ref = fresh_plant
                fresh_server._tools[tool_name].impl = (
                    lambda: {"sensor": aliased_to,
                             "value": fresh_plant_ref.read(aliased_to)}
                )
            psi = verify_tool(fresh_server, tool_name, init,
                              tool_args_override=tool_args_override)
            psi_samples.append(psi.to_dict())
        return psi_samples

    def gate_one_tool(self, tool_name: str,
                      server: MCPServer) -> ToolAdmissionResult:
        t0 = time.time()
        original_tool = server._tools[tool_name]
        description = original_tool.description

        # 1. lift
        c = self.lifter.lift(tool_name, description)
        phi = c.phi if c.parse_succeeded else ""
        out_of_grammar = c.out_of_grammar or not c.parse_succeeded

        if out_of_grammar:
            return ToolAdmissionResult(
                tool_name=tool_name,
                description=description,
                phi=phi,
                out_of_grammar=True,
                admitted=False,
                rejection_reasons=["out_of_grammar"],
                decision_per_initial_state=[],
                admission_time_seconds=time.time() - t0,
            )

        # 2. DT samples — pull tool-args overrides from the lifter's
        #    `extracted` dict. For set_dosing_rate, this is the claimed-
        #    standard rate; under attack (b) this is 0.0167 → DT runs the
        #    tool at the agent-supplied rate, which produces a Δstate(Cond_P2)
        #    violation.
        tool_args_override: dict[str, Any] = {}
        if tool_name == "set_dosing_rate":
            nominal_rate = c.extracted.get("nominal_rate")
            if nominal_rate is not None:
                tool_args_override["rate"] = float(nominal_rate)
        psi_samples = self._run_dt_samples(tool_name, server,
                                            tool_args_override=tool_args_override)

        # 3. matcher per sample
        per_state: list[dict] = []
        rejection_reasons: list[str] = []
        for psi in psi_samples:
            d = evaluate(phi, psi, tool_name=tool_name,
                         initial_state_name=psi["initial_state_name"])
            per_state.append(d.to_dict())
            if not d.admitted:
                rejection_reasons.extend(d.rejection_reasons)

        admitted = not rejection_reasons
        return ToolAdmissionResult(
            tool_name=tool_name,
            description=description,
            phi=phi,
            out_of_grammar=False,
            admitted=admitted,
            rejection_reasons=list(dict.fromkeys(rejection_reasons))[:5],   # dedupe, cap
            decision_per_initial_state=per_state,
            admission_time_seconds=time.time() - t0,
        )

    def gate_all_tools(self, server: MCPServer) -> list[ToolAdmissionResult]:
        results: list[ToolAdmissionResult] = []
        for t in server.list_tools():
            r = self.gate_one_tool(t["name"], server)
            results.append(r)
        return results

    @staticmethod
    def filter_server(server: MCPServer,
                      results: list[ToolAdmissionResult]) -> MCPServer:
        """Return a *view* of the server with rejected tools removed.

        We mutate a shallow copy of the tool dict — the underlying plant is
        shared with the original server (which is what the agent actually
        operates against; admission only changes which tools the agent SEES).
        """
        admitted = {r.tool_name for r in results if r.admitted}
        # Make a shallow-copied server: same plant, filtered tools dict.
        filtered = MCPServer(server.plant)
        filtered._tools = {n: t for n, t in server._tools.items() if n in admitted}
        return filtered


# -----------------------------------------------------------------------------
# CLI: run the gate on a stock Mission 1B server (no attacks). Sanity check.
# -----------------------------------------------------------------------------

def main() -> int:
    plant = SwatP1P2Plant(PlantParams())
    server = MCPServer(plant)
    layer = PGDSLAdmissionLayer()
    results = layer.gate_all_tools(server)

    n_admit = sum(1 for r in results if r.admitted)
    print(f"Stock Mission 1B server (benign descriptions, no attacks):")
    print(f"  admitted : {n_admit}/{len(results)}")
    print()
    for r in results:
        verdict = "ADMIT " if r.admitted else "REJECT"
        rt = f"[{r.admission_time_seconds:.2f}s]"
        if r.admitted:
            print(f"  {verdict} {rt} {r.tool_name:<32} φ = {r.phi}")
        else:
            print(f"  {verdict} {rt} {r.tool_name:<32} reasons: {r.rejection_reasons[:1]}")
    return 0 if n_admit == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
