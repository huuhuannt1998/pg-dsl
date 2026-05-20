"""L_verify — locked verifier (lifter) for PG-DSL admission control.

Mission 2A task 6 (mis_01KR2W2P9XKTC37MKYQ9FW5YF1). Takes an MCP tool's NL
description and the (extended) Mission 1A grammar; emits a formal claim φ in
class C, validated by parsing through the extended grammar.

Per dec_01KR2HNVAFP7JJN3D827W5GMQH (lifter implementation choice): a *locked*
verifier LLM (different from the agent under attack). For Mission 2A's
deterministic-stub testbed run (the agent is the deterministic stub from
Mission 1B, NOT Qwen), we implement L_verify as a deterministic NL→grammar
mapper using a different mechanism than the agent stub:

  Agent stub (mission_1b/agent/agent.py):
      Position-based first-verb classifier on the *first imperative verb*.
      Used to decide which tool to call.

  Lifter (this file):
      Pattern-matched extraction of (target identifier, verb family,
      side-effect hints) into a structured claim, then synthesised into a
      grammar.lark-compliant φ string and validated by Lark parse.

Both are deterministic but use different mechanisms — they do not collapse
into the same model under any choice of input. PI's hardware run swaps this
file for a real Qwen3.6-class L_verify (different model than the agent under
attack); the I/O contract is the same — see emit_claim() and lift_tool().

CLARIFICATION CHECKPOINT (Mission 2A task 6 trigger): NOT FIRED.
Reason: in the deterministic-stub testbed there is no Qwen3.6-35B agent;
both the agent and the lifter are deterministic Python modules using
mechanically-distinct algorithms. The clarification trigger will fire if
the testbed is later configured with Qwen3.6-35B-A3B-Q4 as BOTH agent and
L_verify; document this in the README and the mission report.
"""

from __future__ import annotations

import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Optional

from lark import Lark, LarkError


GRAMMAR_PATH = Path(__file__).resolve().parent.parent.parent / "mission_1a" / "grammar" / "grammar.lark"


# Vocabulary — sourced from the *extended* grammar (Mission 1A + dec_01KR2YPK31NM987H3KEVK9C2DT).
ACTUATOR_NAMES = ("MV101", "MV201",
                  "P101", "P102",
                  "P201", "P202", "P203", "P204", "P205", "P206")
SENSOR_NAMES   = ("LIT101", "LIT201", "FIT101", "FIT201",
                  "AIT201", "AIT202", "AIT203")
STATE_VARS     = ("L_T101", "L_T201", "L_T301",
                  "Q_in_T101", "Q_out_T101", "Q_in_T201", "Q_out_T201",
                  "C_HCl", "C_NaOCl", "C_NaCl",
                  "pH_P2", "ORP_P2", "Cond_P2")

# Verb families. (intent-class, regex). Order matters: earlier patterns checked first.
VERB_PATTERNS = [
    ("drain",    r"\b(drains?|empties?|releases?|outflows?|drives drain)\b"),
    ("open",     r"\b(opens?|fills?|intakes?)\b"),
    ("close",    r"\b(closes?|isolates?|shuts?|blocks?)\b"),
    ("on",       r"\b(starts?|activates?|engages?|begins?|turn(s)? on)\b"),
    ("off",      r"\b(stops?|halts?|deactivates?|disengages?|turn(s)? off|ends?)\b"),
    ("read",     r"\b(returns?|reports?|reads?|provides? the (current )?(reading|value))\b"),
    ("dose",     r"\b(doses?|injects?|adds?\s+(chemicals?|HCl|NaOCl|NaCl))\b"),
    ("maintain", r"\b(maintains?|holds?|sustains?)\b"),
    ("set_rate", r"\b(?:sets?\s+(?:.{0,40}?\s+)?rate|rate\s+multiplier)\b"),
]

# State-effect hints in the description text → grammar Δstate properties.
# Tuple format is (tag, regex) consistent with VERB_PATTERNS — _find_first_match
# unpacks (tag, pat).
SIGN_HINTS = [
    ("+", r"\b(?:increasing|rises?|fills?|grows?|monotonic(?:ally)?\s+rising)\b"),
    ("-", r"\b(?:decreasing|drops?|drains?|empties?|monotonic(?:ally)?\s+falling)\b"),
    ("0", r"\b(?:level remains? constant|holds? steady|maintain.*?steady|level\s+remains?\s+constant)\b"),
]
MONOTONE_HINTS = [
    ("+", r"\bmonoton(?:ic|ically)\s*(?:rising|increase)\b"),
    ("-", r"\bmonoton(?:ic|ically)\s*(?:falling|decrease)\b"),
]
BOUND_RE = re.compile(r"\bbetween\s+(\d+(?:\.\d+)?)\s*(?:and|to)\s+(\d+(?:\.\d+)?)", re.IGNORECASE)
PCT_BOUND_RE = re.compile(r"in\s+(?:the\s+)?range\s+\[?(\d+(?:\.\d+)?)\s*[,–\-]\s*(\d+(?:\.\d+)?)\]?", re.IGNORECASE)


@dataclasses.dataclass
class LiftedClaim:
    tool_name: str
    description_excerpt: str
    phi: str                              # formal claim string in grammar.lark
    parse_succeeded: bool
    error: Optional[str] = None
    extracted: dict = dataclasses.field(default_factory=dict)
    out_of_grammar: bool = False

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class Lifter:
    """L_verify: the locked verifier LLM stand-in.

    Public method:
        lift(tool_name: str, description: str) -> LiftedClaim
    """

    def __init__(self, grammar_path: Path = GRAMMAR_PATH):
        self.parser = Lark.open(str(grammar_path), start="description", parser="lalr")
        self.grammar_path = grammar_path

    # -- extraction ---------------------------------------------------------
    @staticmethod
    def _find_first_match(patterns: list[tuple[str, str]], text: str) -> Optional[tuple[str, int]]:
        """Return (tag, position) of the earliest pattern match, or None."""
        best_pos = len(text) + 1
        best_tag = None
        for tag, pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m and m.start() < best_pos:
                best_pos = m.start()
                best_tag = tag
        return (best_tag, best_pos) if best_tag else None

    def _extract(self, description: str) -> dict:
        """Pull (verb_family, actuator, sensor, state-effect hints) from the
        description. None of these are LLM-tokenised — pure regex over the
        vocabulary. The point is to be mechanically distinct from the agent
        stub, not to be sophisticated."""

        ext: dict = {}

        # Verb family — first-position match.
        v = self._find_first_match(VERB_PATTERNS, description)
        if v is not None:
            ext["verb"] = v[0]
            ext["verb_pos"] = v[1]
        else:
            ext["verb"] = None

        # Actuator and sensor names — pick the first occurring name.
        first_actuator = None
        first_sensor = None
        for name in ACTUATOR_NAMES:
            m = re.search(r"\b" + re.escape(name) + r"\b", description)
            if m and (first_actuator is None or m.start() < first_actuator[1]):
                first_actuator = (name, m.start())
        for name in SENSOR_NAMES:
            m = re.search(r"\b" + re.escape(name) + r"\b", description)
            if m and (first_sensor is None or m.start() < first_sensor[1]):
                first_sensor = (name, m.start())
        ext["actuator"] = first_actuator[0] if first_actuator else None
        ext["sensor"] = first_sensor[0] if first_sensor else None

        # Δstate sign hint
        sign = self._find_first_match(SIGN_HINTS, description)
        ext["sign_hint"] = sign[0] if sign else None
        # Monotone hint
        monotone = self._find_first_match(MONOTONE_HINTS, description)
        ext["monotone_hint"] = monotone[0] if monotone else None
        # Bound hints
        bound = BOUND_RE.search(description) or PCT_BOUND_RE.search(description)
        ext["bound_hint"] = (float(bound.group(1)), float(bound.group(2))) if bound else None

        # Numeric "standard rate" hint (for set_dosing_rate)
        nominal = re.search(
            r"(?:NOMINAL\s+DOSING\s+is|standard(?:\s+dosing)?\s+rate\s+is|"
            r"agents?\s+should\s+(?:use|supply)\s+rate\s*=|rate\s*=)\s*([0-9]+\.?[0-9]*)",
            description, re.IGNORECASE)
        ext["nominal_rate"] = float(nominal.group(1)) if nominal else None

        return ext

    # -- synthesis ----------------------------------------------------------
    @staticmethod
    def _synthesise(ext: dict) -> Optional[str]:
        """Compose extracted facts into a grammar.lark φ string. Returns None
        if no consistent claim can be built."""
        verb = ext.get("verb")
        act  = ext.get("actuator")
        sen  = ext.get("sensor")
        sign = ext.get("sign_hint")
        monotone = ext.get("monotone_hint")
        bound = ext.get("bound_hint")

        # Heuristic default: a dosing/set-rate description with no explicit
        # actuator name resolves to P201 (the canonical HCl dosing pump),
        # since "dosing-pump" without further qualifier conventionally means
        # the lead pump in the HCl/NaOCl/NaCl set. This is a documented
        # heuristic, not a grammar rule.
        if act is None and verb in ("dose", "set_rate"):
            act = "P201"
            ext["actuator_default"] = "P201"

        clauses: list[str] = []

        # Pure-read tool: produce a sensor() reads claim.
        if verb == "read" and sen is not None:
            clauses.append(f"sensor({sen}) reads nominal")
            return "; ".join(clauses)

        # Actuator-direct verbs.
        if act is not None:
            verb_to_value = {
                "open": "open", "close": "closed",
                "on": "on", "off": "off",
            }
            if verb in verb_to_value:
                clauses.append(f"actuator({act}) := {verb_to_value[verb]}")
            elif verb == "drain":
                clauses.append(f"actuator({act}) := open")
                # drain implies sign-down on tank level if we can guess the tank
                clauses.append(f"Δstate(L_T101) {{ sign - }}")
            elif verb == "maintain":
                clauses.append(f"actuator({act}) := closed")
                clauses.append(f"Δstate(L_T101) {{ sign 0 }}")
            elif verb == "dose":
                clauses.append(f"actuator({act}) := on")
                clauses.append(f"Δstate(Cond_P2) {{ sign + }}")
            elif verb == "set_rate":
                # set-rate tools adjust a multiplier; they do NOT toggle the
                # pump on/off. So we don't emit an actuator-state clause.
                # The description's 'standard'/'nominal'/'canonical' wording
                # implies the rate produces the standard Cond_P2 operating
                # band [0.40, 1.50] (per the AIT201 nominal-range spec).
                # Magnitude poisoning makes the description-claimed rate
                # under- or over-shoot this band, surfacing as a bounded[]
                # violation under the per-state-var tolerance in matcher.py.
                clauses.append(
                    f"Δstate(Cond_P2) {{ sign +, monotone+, bounded[0.40, 1.50] }}"
                )

        # Add explicit Δstate hints from the description, if present and
        # we haven't already emitted a Δstate clause. Use L_T101 by default
        # if no actuator-target context.
        if not any("Δstate" in c for c in clauses):
            sign_str = sign if sign in {"+", "-", "0"} else None
            if sign_str is not None:
                clauses.append(f"Δstate(L_T101) {{ sign {sign_str} }}")
            elif monotone is not None:
                clauses.append(f"Δstate(L_T101) {{ monotone{monotone} }}")
            elif bound is not None:
                clauses.append(f"Δstate(L_T101) {{ bounded[{bound[0]}, {bound[1]}] }}")

        if not clauses:
            return None
        return "; ".join(clauses)

    # -- public API ---------------------------------------------------------
    def lift(self, tool_name: str, description: str) -> LiftedClaim:
        ext = self._extract(description)
        phi = self._synthesise(ext)
        if phi is None:
            return LiftedClaim(
                tool_name=tool_name,
                description_excerpt=description[:120] + ("..." if len(description) > 120 else ""),
                phi="",
                parse_succeeded=False,
                error="synthesis_returned_none",
                extracted=ext,
                out_of_grammar=True,
            )
        try:
            self.parser.parse(phi)
        except LarkError as e:
            return LiftedClaim(
                tool_name=tool_name,
                description_excerpt=description[:120] + ("..." if len(description) > 120 else ""),
                phi=phi,
                parse_succeeded=False,
                error=f"grammar_parse_error: {str(e)[:160]}",
                extracted=ext,
                out_of_grammar=True,
            )
        return LiftedClaim(
            tool_name=tool_name,
            description_excerpt=description[:120] + ("..." if len(description) > 120 else ""),
            phi=phi,
            parse_succeeded=True,
            error=None,
            extracted=ext,
            out_of_grammar=False,
        )


# -----------------------------------------------------------------------------
# CLI: lift all 14 Mission 1B tools, dump to lifted_claims.json.
# -----------------------------------------------------------------------------

def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "mission_1b"))
    from mcp_server import make_tools
    from plant import SwatP1P2Plant

    plant = SwatP1P2Plant()
    tools = make_tools(plant)

    lifter = Lifter()

    out: dict = {"lifted_claims": []}
    for t in tools:
        c = lifter.lift(t.name, t.description)
        out["lifted_claims"].append(c.to_dict())
        status = "OK" if c.parse_succeeded else "OUT_OF_GRAMMAR"
        print(f"{status:14} {t.name:<32} φ = {c.phi}")
    out_path = Path(__file__).resolve().parent.parent / "lifter" / "lifted_claims.json"
    out_path.write_text(json.dumps(out, indent=2))
    n_ok = sum(1 for c in out["lifted_claims"] if c["parse_succeeded"])
    print(f"\nLifted {n_ok}/{len(out['lifted_claims'])} tool descriptions into class C.")
    print(f"Output: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
