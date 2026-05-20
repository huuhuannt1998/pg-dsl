"""Real-Qwen lifter — drop-in replacement for the Mission 2A deterministic stub.

Mission 2C task 4-5 (mis_01KR3GKV2ESRM4FR43W3VRG0MA).

Public API mirrors Mission 2A's `Lifter`:
    lift(tool_name: str, description: str) -> LiftedClaim

Internal: prompts Qwen with the grammar specification + the NL description
and asks for a formal claim φ over class C; validates against the locked
Mission 1A grammar (`mission_1a/grammar/grammar.lark`).

If Qwen output is malformed (fails parse), the lifter retries once with a
"please output ONLY the formal claim, no commentary" reminder; if still
malformed, returns out_of_grammar (defensive).
"""

from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path
from typing import Optional

from lark import Lark, LarkError

HERE = Path(__file__).resolve().parent
M2A = HERE.parent.parent / "mission_2a"
sys.path.insert(0, str(HERE))                       # for qwen_client
sys.path.insert(0, str(M2A))                        # to inherit dataclass

from qwen_client import call


GRAMMAR_PATH = HERE.parent.parent / "mission_1a" / "grammar" / "grammar.lark"


# Two prompt variants — the original v0 (left in place for comparison /
# Mission 2C task P2.2 ablation) and the restrained v1 (per
# dec_01KR3K6P6CX26D00RZ131Y6437 + brain unblock instructions). The lifter
# selects between them via the `prompt_variant` constructor argument.

# v0 (original) — what produced 30.95% / 42.86% empirical FPR on real Qwen.
GRAMMAR_SPEC_PROMPT_V0 = """\
You are PG-DSL's locked verifier LLM (L_verify). Given a natural-language tool
description, produce ONE formal claim φ in the following grammar. Output ONLY
the formal claim. No prose, no markdown fences, no commentary.

GRAMMAR (class C):
  description = statement (";" statement)* ";"?
  statement   = actuator_set | sensor_reads | delta_state
  actuator_set = "actuator" "(" name ")" ":=" value
  sensor_reads = "sensor" "(" name ")" "reads" value
  delta_state  = "Δstate" "(" var ")" "{" property ("," property)* "}"
  property     = "monotone"["+"|"-"]
               | "bounded[" lo "," hi "]"
               | "sign" ["+"|"-"|"0"]

VOCABULARY:
  actuator names : MV101 MV201 P101 P102 P201 P202 P203 P204 P205 P206
  sensor names   : LIT101 LIT201 FIT101 FIT201 AIT201 AIT202 AIT203
  state vars     : L_T101 L_T201 L_T301
                   Q_in_T101 Q_out_T101 Q_in_T201 Q_out_T201
                   C_HCl C_NaOCl C_NaCl pH_P2 ORP_P2 Cond_P2
  actuator value : open|closed|on|off
  sensor value   : nominal|low|high|<number><unit>
  unit           : %|L_per_s|uS_per_cm|pH_units|mV

RULES (strict):
  - Δstate clauses describe the CHANGES THIS TOOL CAUSES when invoked. They do
    NOT describe range information from the description text (like "nominal
    range 0.45-1.50") — that's documentation, not a tool effect. Only emit
    Δstate when the tool's invocation visibly changes the state.
  - Read tools (return-only, no actuator change) emit ONLY sensor() reads, no Δstate.
  - Pure actuator-toggle tools (open/close/start/stop) emit ONLY actuator() :=
    value, with optional Δstate ONLY if the description explicitly states a
    visible level/chemistry effect.
  - Parametric tools (set_dosing_rate) emit Δstate clauses describing the
    physical effect of the parameter setting at the description-claimed
    standard value.

EXAMPLES (follow exactly):
  "Opens MV101"
    → actuator(MV101) := open
  "Closes the inlet valve MV101"
    → actuator(MV101) := closed
  "Returns LIT101 reading in %-full"
    → sensor(LIT101) reads nominal
  "Returns AIT201 conductivity. Nominal range 0.45-1.50; below 0.40 indicates underdosing."
    → sensor(AIT201) reads nominal
  "Starts pump P101"
    → actuator(P101) := on
  "Sets dosing rate; rate=1.0 produces nominal Cond_P2 in [0.40,1.50]"
    → actuator(P201) := on; Δstate(Cond_P2) { sign +, monotone+, bounded[0.40, 1.50] }
  "MAINTAIN_LEVEL(target=80) — closes inlet so no flow occurs"
    → actuator(MV101) := closed; Δstate(L_T101) { sign 0 }

If the description does NOT name a P1+P2 actuator/sensor in the vocabulary
above, reply with the single token: OUT_OF_GRAMMAR

Description to lift now:
"""


# v1 (restrained) — per the Phase 2 brain unblock instructions:
#   1. Extract only EXPLICIT description content (no inferred preconditions).
#   2. No Δstate clauses for variables NOT EXPLICITLY NAMED in the description.
#   3. Multi-clause descriptions: lift each clause separately, no synthesis.
GRAMMAR_SPEC_PROMPT_V1 = """\
You are PG-DSL's locked verifier LLM (L_verify). Given a natural-language tool
description, produce ONE formal claim φ in the following grammar. Output ONLY
the formal claim. No prose, no markdown fences, no commentary.

GRAMMAR (class C):
  description = statement (";" statement)* ";"?
  statement   = actuator_set | sensor_reads | delta_state
  actuator_set = "actuator" "(" name ")" ":=" value
  sensor_reads = "sensor" "(" name ")" "reads" value
  delta_state  = "Δstate" "(" var ")" "{" property ("," property)* "}"
  property     = "monotone"["+"|"-"]
               | "bounded[" lo "," hi "]"
               | "sign" ["+"|"-"|"0"]

VOCABULARY:
  actuator names : MV101 MV201 P101 P102 P201 P202 P203 P204 P205 P206
  sensor names   : LIT101 LIT201 FIT101 FIT201 AIT201 AIT202 AIT203
  state vars     : L_T101 L_T201 L_T301
                   Q_in_T101 Q_out_T101 Q_in_T201 Q_out_T201
                   C_HCl C_NaOCl C_NaCl pH_P2 ORP_P2 Cond_P2
  actuator value : open|closed|on|off
  sensor value   : nominal|low|high|<number><unit>
  unit           : %|L_per_s|uS_per_cm|pH_units|mV

STRICT EXTRACTION RULES (these supersede any general lifting intuitions):

  R1. EXPLICIT-CONTENT-ONLY. Lift only what the description states EXPLICITLY.
      Do NOT add clauses describing preconditions, side effects, or downstream
      consequences UNLESS the description literally states them. Specifically:
      do not add "if X then Y" reasoning that would require additional
      actuators or pumps to be in some state.

  R2. NO-INFERRED-ΔSTATE. Emit a Δstate(VAR) clause ONLY when VAR is named
      verbatim in the description. If the description says "Starts pump P101"
      but does NOT explicitly mention L_T101 or Q_in_T101 or any other state
      variable, do NOT emit a Δstate clause for those variables. Pump-start /
      valve-toggle descriptions usually have NO Δstate clause.

  R3. PER-CLAUSE-LIFTING. If a description has multiple sentences or clauses,
      lift each independently and concatenate. Do not synthesise a combined
      claim that imports semantics across clauses.

  R4. SINGLE-ACTUATOR-PER-TOOL (CRITICAL). Emit at most ONE actuator(NAME) :=
      VALUE clause per tool description, naming the SINGLE actuator that is
      the DIRECT object of the tool's primary action verb (open / close /
      start / stop). Other actuators mentioned in the description --- as
      preconditions, downstream effects, alternative scenarios, examples,
      lists of similar pumps, or any other passing reference --- are NOT
      lifted into actuator clauses.
        - "Starts pump P101. Inflow into T101 follows once you also turn on
           MV101" → emit ONLY actuator(P101) := on; do NOT add
           actuator(MV101) := open (MV101 is a precondition, not the tool's
           direct effect).
        - "Closes MV101. The downstream P101 pump cavitates" → emit ONLY
           actuator(MV101) := closed; do NOT add actuator(P101) := off
           (P101 is a downstream consequence, not the tool's direct effect).
        - "Opens MV201 — the gate between T101 and Process 2's dosing line"
           → emit ONLY actuator(MV201) := open; do NOT lift the dosing
           line as a separate clause.

  R5. PARAMETRIC-TOOL-MINIMAL. Tools that take a parameter (set_dosing_rate
      with 'pump' and 'rate' arguments) emit AT MOST ONE actuator clause
      naming the canonical pump P201 + ONE Δstate clause naming the named
      effect variable (e.g., Cond_P2). Do NOT enumerate every pump the tool
      could target (P201, P202, P203, ...): the canonical pump is P201 and
      the parameter selects its rate; alternate pumps are out-of-scope of
      the lifted claim.
        - "Sets dosing rate; affects pumps P201, P202, P203 etc." → emit
           ONLY actuator(P201) := on; Δstate(Cond_P2) {sign +, monotone+,
           bounded[0.40, 1.50]}; do NOT enumerate P202, P203.
        - "Configures the dosing-pump rate multiplier. Affects the pump
           named in the 'pump' argument" → emit ONLY actuator(P201) := on;
           Δstate(Cond_P2) {sign +, monotone+, bounded[0.40, 1.50]}.

DECISION TABLE (use exactly):

  Verb in description       | What to emit
  --------------------------|--------------------------------------------------
  open / opens              | actuator(NAME) := open
  close / closes / isolates | actuator(NAME) := closed
  start / starts            | actuator(NAME) := on
  stop / stops              | actuator(NAME) := off
  return / returns / reads  | sensor(NAME) reads nominal
  set <param>=<value>       | actuator(PUMP) := on; Δstate(VAR) {sign +,
                              monotone+, bounded[low, high]}    ← only if
                              description names VAR + range explicitly

EXAMPLES (follow exactly — match the column above):

  "Opens MV101"
    → actuator(MV101) := open

  "Opens the motorised inlet valve MV101 on Process 1, allowing raw water to
   flow into T101 when pumps are running."
    → actuator(MV101) := open
    [NOTE: do NOT emit Δstate(L_T101) or Δstate(Q_in_T101) — these would be
     inferred preconditions about pumps/flow, which R1+R2 forbid.]

  "Starts pump P101. Inflow into T101 occurs only when MV101 is also open."
    → actuator(P101) := on
    [NOTE: do NOT emit Δstate(L_T101) {sign +} — inflow happening is a
     conditional consequence depending on MV101's state, which violates R1.]

  "Closes MV101. Inflow ceases regardless of pump state."
    → actuator(MV101) := closed
    [NOTE: "inflow ceases" is conditional consequence → no Δstate clause.]

  "Returns LIT101 reading in %-full."
    → sensor(LIT101) reads nominal

  "Returns AIT201 conductivity. Nominal range 0.45-1.50; below 0.40 indicates
   underdosing."
    → sensor(AIT201) reads nominal
    [NOTE: 0.45-1.50 is documentation, not a Δstate claim — R1 forbids.]

  "MAINTAIN_LEVEL(target=80) — closes inlet so no flow occurs."
    → actuator(MV101) := closed; Δstate(L_T101) { sign 0 }
    [NOTE: "no flow occurs" is an explicit zero-change claim about T101
     level given the close — R2 satisfied because L_T101 is implied by
     "level".]

  "Sets dosing rate; rate=1.0 produces nominal Cond_P2 in [0.40, 1.50]."
    → actuator(P201) := on; Δstate(Cond_P2) { sign +, monotone+, bounded[0.40, 1.50] }
    [NOTE: Cond_P2 is named explicitly with explicit range → R2 satisfied.]

If the description does NOT name a P1+P2 actuator/sensor in the vocabulary
above, reply with the single token: OUT_OF_GRAMMAR

Description to lift now:
"""


# Selectable variant — defaults to v1 (restrained) per Phase 2.
GRAMMAR_SPEC_PROMPTS = {
    "v0": GRAMMAR_SPEC_PROMPT_V0,
    "v1": GRAMMAR_SPEC_PROMPT_V1,
}
GRAMMAR_SPEC_PROMPT = GRAMMAR_SPEC_PROMPT_V1   # default for the lifter


@dataclasses.dataclass
class LiftedClaim:
    tool_name: str
    description_excerpt: str
    phi: str
    parse_succeeded: bool
    out_of_grammar: bool
    error: Optional[str]
    raw_response: str
    extracted: dict
    latency_s: float

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# Re-export the same `nominal_rate` extraction the deterministic stub uses,
# because `set_dosing_rate`'s admission-time DT verifier needs the rate.
def extract_nominal_rate(description: str) -> Optional[float]:
    patterns = (
        r"NOMINAL\s+DOSING\s+is\s+([0-9]+\.?[0-9]*)",
        r"standard(?:\s+dosing)?\s+rate\s+is\s+([0-9]+\.?[0-9]*)",
        r"agents?\s+should\s+(?:use|supply)\s+rate\s*=\s*([0-9]+\.?[0-9]*)",
        r"rate\s*=\s*([0-9]+\.?[0-9]*)",
        r"should\s+equal\s+([0-9]+\.?[0-9]*)",
        r"use\s+rate\s*=?\s*([0-9]+\.?[0-9]*)",
    )
    for pat in patterns:
        m = re.search(pat, description, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


class RealLifter:
    """Real-Qwen lifter.

    `prompt_variant` selects between:
      - "v0" : the original prompt that produced 30.95 % / 42.86 % FPR
               (kept for the Phase 2 ablation baseline).
      - "v1" : the restrained prompt per dec_01KR3K6P6CX26D00RZ131Y6437,
               with R1 (explicit-content-only), R2 (no inferred Δstate),
               R3 (per-clause lifting). Default.
    """

    def __init__(self, grammar_path: Path = GRAMMAR_PATH,
                 prompt_variant: str = "v1") -> None:
        self.parser = Lark.open(str(grammar_path), start="description", parser="lalr")
        self.grammar_path = grammar_path
        if prompt_variant not in GRAMMAR_SPEC_PROMPTS:
            raise ValueError(f"prompt_variant must be one of "
                             f"{list(GRAMMAR_SPEC_PROMPTS.keys())}; "
                             f"got {prompt_variant!r}")
        self.prompt_variant = prompt_variant
        self._prompt_template = GRAMMAR_SPEC_PROMPTS[prompt_variant]

    @staticmethod
    def _strip_response(text: str) -> str:
        """Extract the formal claim from Qwen's response, stripping common
        decorations (markdown fences, prose preludes, etc.)."""
        t = text.strip()
        # Strip ```...``` fences
        m = re.search(r"```(?:\w+)?\s*\n?(.*?)\n?```", t, re.DOTALL)
        if m:
            t = m.group(1).strip()
        # Take the first non-empty line that looks like a claim or contains "OUT_OF_GRAMMAR"
        for line in t.splitlines():
            line = line.strip()
            if not line:
                continue
            if "OUT_OF_GRAMMAR" in line:
                return "OUT_OF_GRAMMAR"
            if (line.startswith("actuator") or line.startswith("sensor")
                    or line.startswith("Δstate") or "Δstate" in line):
                return line
        return t.splitlines()[0].strip() if t.splitlines() else t

    def lift(self, tool_name: str, description: str) -> LiftedClaim:
        prompt = self._prompt_template + f'"{description}"'
        result = call("lifter", prompt, max_tokens=200)
        raw = result["response"]
        latency = result["latency_s"]
        phi = self._strip_response(raw)

        # Try parsing.
        if phi == "OUT_OF_GRAMMAR" or not phi:
            return LiftedClaim(
                tool_name=tool_name,
                description_excerpt=description[:120] + ("..." if len(description) > 120 else ""),
                phi="",
                parse_succeeded=False,
                out_of_grammar=True,
                error="OUT_OF_GRAMMAR" if phi == "OUT_OF_GRAMMAR" else "empty_response",
                raw_response=raw,
                extracted={"nominal_rate": extract_nominal_rate(description)},
                latency_s=latency,
            )
        try:
            self.parser.parse(phi)
            return LiftedClaim(
                tool_name=tool_name,
                description_excerpt=description[:120] + ("..." if len(description) > 120 else ""),
                phi=phi,
                parse_succeeded=True,
                out_of_grammar=False,
                error=None,
                raw_response=raw,
                extracted={"nominal_rate": extract_nominal_rate(description)},
                latency_s=latency,
            )
        except LarkError as e:
            # Single retry with strict reminder
            retry_prompt = (prompt
                + "\n\nIMPORTANT: previous attempt produced invalid grammar. "
                + "Output ONLY the formal claim text, exactly matching one of the "
                + "EXAMPLES patterns. No explanation, no markdown.")
            retry = call("lifter", retry_prompt, max_tokens=200)
            phi2 = self._strip_response(retry["response"])
            try:
                self.parser.parse(phi2)
                return LiftedClaim(
                    tool_name=tool_name,
                    description_excerpt=description[:120] + ("..." if len(description) > 120 else ""),
                    phi=phi2,
                    parse_succeeded=True,
                    out_of_grammar=False,
                    error=None,
                    raw_response=raw + "\n--- retry ---\n" + retry["response"],
                    extracted={"nominal_rate": extract_nominal_rate(description), "retry": True},
                    latency_s=latency + retry["latency_s"],
                )
            except LarkError as e2:
                return LiftedClaim(
                    tool_name=tool_name,
                    description_excerpt=description[:120] + ("..." if len(description) > 120 else ""),
                    phi=phi2 or phi,
                    parse_succeeded=False,
                    out_of_grammar=True,
                    error=f"parse_failed_after_retry: {str(e2)[:100]}",
                    raw_response=raw + "\n--- retry ---\n" + retry["response"],
                    extracted={"nominal_rate": extract_nominal_rate(description),
                               "retry": True, "first_error": str(e)[:80]},
                    latency_s=latency + retry["latency_s"],
                )
