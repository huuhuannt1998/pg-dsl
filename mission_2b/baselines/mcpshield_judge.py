"""MCPShield-style LLM-as-judge baseline.

Mission 2B task 2 (mis_01KR3FJ9JJP5EKEFQ1AVFPPAZE).

Replicates MCPShield's Stage-1 Security Cognitive Probing (per
lit_01KR2HXCBAQDTYDGZREF8BH7QP). The published mechanism is:
    LLM-as-judge given (description, simulated invocation results) prompted
    to verify behavioral consistency.

This module implements a *deterministic stand-in* for the LLM-as-judge,
faithful to the operational goal of MCPShield's prompt — three behavioral
consistency checks at admission time. PI's hardware deployment swaps in real
Qwen3.6 (using a different decoding seed from PG-DSL's L_verify per Mission
2B task 2 spec).

See `baseline_design_memo.md` for the faithfulness audit and predicted
behaviour on the three baseline attacks. No DECISION checkpoint fires for
the deterministic stand-in (consistent with the stub policy in Missions 1B
and 2A).

PUBLIC API:
    MCPShieldJudge.judge(description, simulated_invocations) -> JudgeVerdict

USED BY:
    evaluation/run_mcpshield_eval.py — task 8 comparison campaign.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, Optional

# Verb → expected effect class. Mirrors the MCPShield judge's surface-level
# reasoning about what a description's verb implies should happen physically.
VERB_TO_EFFECT = {
    "open":     "actuator_to_open",
    "close":    "actuator_to_closed",
    "start":    "actuator_to_on",
    "stop":     "actuator_to_off",
    "drain":    "level_decreasing",
    "fill":     "level_increasing",
    "maintain": "level_steady",
    "hold":     "level_steady",
    "dose":     "chemical_increasing",
    "inject":   "chemical_increasing",
    "read":     "no_state_change",
    "return":   "no_state_change",
    "set":      "parametric_no_actuator_toggle",
}

ACTUATOR_NAMES = ("MV101", "MV201", "P101", "P102",
                  "P201", "P202", "P203", "P204", "P205", "P206")
SENSOR_NAMES = ("LIT101", "LIT201", "FIT101", "FIT201",
                "AIT201", "AIT202", "AIT203")


@dataclasses.dataclass
class JudgeVerdict:
    admitted: bool
    rationale: str
    failed_checks: list[str]
    detail: dict


def _first_verb(description: str) -> Optional[str]:
    d = description.lower()
    best_pos = len(d) + 1
    best_verb = None
    for v in VERB_TO_EFFECT:
        m = re.search(rf"\b{v}s?\b", d)
        if m and m.start() < best_pos:
            best_pos = m.start()
            best_verb = v
    return best_verb


def _named_actuator(description: str) -> Optional[str]:
    for n in ACTUATOR_NAMES:
        if re.search(rf"\b{re.escape(n)}\b", description):
            return n
    return None


def _named_sensor(description: str) -> Optional[str]:
    for n in SENSOR_NAMES:
        if re.search(rf"\b{re.escape(n)}\b", description):
            return n
    return None


def _parametric_value(description: str) -> Optional[float]:
    """Pull a 'standard'/'nominal' parameter value out of the description if any."""
    patterns = (
        r"NOMINAL\s+DOSING\s+is\s+([0-9]+\.?[0-9]*)",
        r"standard(?:\s+dosing)?\s+rate\s+is\s+([0-9]+\.?[0-9]*)",
        r"agents?\s+should\s+(?:use|supply)\s+rate\s*=\s*([0-9]+\.?[0-9]*)",
        r"rate\s*=\s*([0-9]+\.?[0-9]*)",
    )
    for pat in patterns:
        m = re.search(pat, description, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


class MCPShieldJudge:
    """Deterministic stand-in for the MCPShield Stage-1 Security Cognitive
    Probing LLM-as-judge.

    Each `judge()` call performs three surface-level consistency checks
    against the simulated invocation evidence:
      1. verb-effect consistency
      2. sensor-name consistency
      3. parametric-value consistency
    """

    def judge(self,
              description: str,
              invocations: list[dict],
              ) -> JudgeVerdict:
        """Verify behavioral consistency.

        Each `invocation` is a dict with keys:
            tool_name      : str
            tool_args      : dict
            tool_return    : Any (often {sensor: name, value: number})
            actuator_pre   : dict[name -> state]
            actuator_post  : dict[name -> state]
            sensor_oracle_pre  : dict[name -> value]
            sensor_oracle_post : dict[name -> value]

        The judge does NOT have physics, so it cannot tell whether an
        actuator transition produces the claimed effect on level — it only
        checks surface-level consistency of named entities and verbs.
        """
        verb = _first_verb(description)
        named_actuator = _named_actuator(description)
        named_sensor = _named_sensor(description)
        param_value = _parametric_value(description)

        failed: list[str] = []
        detail: dict = {
            "verb": verb, "named_actuator": named_actuator,
            "named_sensor": named_sensor, "param_value": param_value,
            "n_invocations": len(invocations),
        }

        if not invocations:
            return JudgeVerdict(
                admitted=False, rationale="no invocation evidence to judge",
                failed_checks=["no_evidence"], detail=detail,
            )

        # 1. Verb-effect consistency.
        verb_eff = VERB_TO_EFFECT.get(verb) if verb else None
        if verb_eff and named_actuator:
            for inv in invocations:
                pre = inv.get("actuator_pre", {}).get(named_actuator)
                post = inv.get("actuator_post", {}).get(named_actuator)
                # Surface check: does the post state match the verb's expected target?
                if verb_eff == "actuator_to_open" and post != "open":
                    failed.append(f"verb 'open' on {named_actuator} but post={post}")
                    break
                if verb_eff == "actuator_to_closed" and post != "closed":
                    failed.append(f"verb 'close' on {named_actuator} but post={post}")
                    break
                if verb_eff == "actuator_to_on" and post != "on":
                    failed.append(f"verb 'start' on {named_actuator} but post={post}")
                    break
                if verb_eff == "actuator_to_off" and post != "off":
                    failed.append(f"verb 'stop' on {named_actuator} but post={post}")
                    break

        # 2. Sensor-name consistency.
        if verb in ("read", "return"):
            for inv in invocations:
                tr = inv.get("tool_return") or {}
                if isinstance(tr, dict):
                    returned_sensor = tr.get("sensor")
                    if named_sensor and returned_sensor and \
                       returned_sensor != named_sensor:
                        failed.append(
                            f"description names {named_sensor}, tool returns "
                            f"{returned_sensor}"
                        )
                        break

        # 3. Parametric-value consistency.
        # If description states a 'standard' value AND the invocation used
        # a different value, flag. Note: the judge has no physics, so it can
        # only verify the agent's invocation matched the description-claimed
        # standard. It cannot tell whether that standard is itself wrong.
        if param_value is not None:
            for inv in invocations:
                args = inv.get("tool_args") or {}
                used_rate = args.get("rate")
                if used_rate is not None:
                    try:
                        if abs(float(used_rate) - float(param_value)) > 1e-6:
                            failed.append(
                                f"description claims rate={param_value}, "
                                f"invocation used rate={used_rate}"
                            )
                            break
                    except (TypeError, ValueError):
                        pass

        admitted = not failed
        rationale = ("admitted: all three behavioral-consistency checks pass."
                     if admitted else
                     f"rejected on {len(failed)} check(s): " + "; ".join(failed[:2]))
        return JudgeVerdict(
            admitted=admitted, rationale=rationale,
            failed_checks=failed, detail=detail,
        )
