"""Real-LLM admission layer — Mission 2A's PGDSLAdmissionLayer with the
deterministic-stub Lifter swapped for real Qwen RealLifter.

Mission 2C task 5 (mis_01KR3GKV2ESRM4FR43W3VRG0MA).

Mirrors Mission 2A's `PGDSLAdmissionLayer.gate_one_tool` interface so it can
be used by every existing campaign script.
"""

from __future__ import annotations

import dataclasses
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
M2C = HERE.parent
M2A = M2C.parent / "mission_2a"
M1B = M2C.parent / "mission_1b"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(M1B))
sys.path.insert(0, str(M2A))

from mcp_server import MCPServer, Tool                              # noqa
from plant import PlantParams, SwatP1P2Plant                         # noqa
from dt_verifier import verify_tool, INITIAL_STATES                  # noqa
from matcher import evaluate                                         # noqa
from admission_layer import ToolAdmissionResult                      # noqa
from real_lifter import RealLifter                                   # noqa


class RealLLMAdmissionLayer:
    """Drop-in replacement for `PGDSLAdmissionLayer` using `RealLifter`.

    `prompt_variant` selects the lifter prompt (v0 or v1); used by the
    Mission 2C P2.2 ablation comparing original vs restrained prompts.
    """

    def __init__(self, lifter: RealLifter | None = None,
                 prompt_variant: str = "v1") -> None:
        self.lifter = lifter or RealLifter(prompt_variant=prompt_variant)

    def _run_dt_samples(self, tool_name: str,
                        original_server: MCPServer,
                        tool_args_override: dict | None = None) -> list[dict]:
        psi_samples: list[dict] = []
        original_tool = original_server._tools[tool_name]
        for init in INITIAL_STATES:
            fresh_plant = SwatP1P2Plant(PlantParams())
            fresh_server = MCPServer(fresh_plant)
            fresh_server.apply_description_overrides(
                {tool_name: original_tool.description}
            )
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

        # Pull rate from the real-lifter's extracted dict (same plumbing as 2A stub).
        tool_args_override: dict[str, Any] = {}
        if tool_name == "set_dosing_rate":
            nominal_rate = c.extracted.get("nominal_rate")
            if nominal_rate is not None:
                tool_args_override["rate"] = float(nominal_rate)
        psi_samples = self._run_dt_samples(tool_name, server,
                                           tool_args_override=tool_args_override)

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
            rejection_reasons=list(dict.fromkeys(rejection_reasons))[:5],
            decision_per_initial_state=per_state,
            admission_time_seconds=time.time() - t0,
        )

    def gate_all_tools(self, server: MCPServer) -> list[ToolAdmissionResult]:
        results: list[ToolAdmissionResult] = []
        for t in server.list_tools():
            results.append(self.gate_one_tool(t["name"], server))
        return results
