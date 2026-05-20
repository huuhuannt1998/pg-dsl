# Mission 2B — Baseline Implementation Design Memo

**Mission:** mis_01KR3FJ9JJP5EKEFQ1AVFPPAZE.
**Purpose:** document the deterministic-stub implementation strategy for the two
baselines BEFORE writing any code, so the "published-prompt faithfulness" question
is on record. This memo is the answer to whether to fire DECISION checkpoints
under tasks 2 and 3.

---

## Deterministic-stub policy (consistent with Missions 1B and 2A)

The Mission 1B agent (deterministic instruction-following stub, not real Qwen)
and Mission 2A L_verify (deterministic NL→grammar synthesiser, not real Qwen)
both used the same pattern: a Python stand-in that faithfully *represents the
concept* of the LLM-component being modelled, while running deterministically
without an actual model invocation.

That same pattern is the only honest implementation choice in this evaluation
session: PI's hardware deployment runs real Qwen3.6 for all four LLM roles
(agent, L_verify, MCPShield judge, INVARLLM extractor). The stubs let the
evaluation campaign run end-to-end here without the ~minutes-per-rep wall-clock
of a real-Qwen sweep.

**Verdict:** stubs are an appropriate substitute. NO DECISION checkpoint fires
for this stand-in pattern. Real-Qwen swap-in is documented in each baseline's
docstring and in the Mission 2B README.

The CLARIFICATION trigger ("MCPShield baseline outperforms PG-DSL on any
attack class") fires on RESULTS, not on the stub-vs-real-LLM choice — so it
remains the right gate.

## Baseline 1 — MCPShield-style LLM-as-judge

### Faithfulness target

Per `jrn_01KR2JTAH6H6T758XZ9CYSM5VX` (Mission 1A adjacency analysis) and
`lit_01KR2HXCBAQDTYDGZREF8BH7QP` (the MCPShield paper itself):

> **MCPShield Stage-1 (Security Cognitive Probing):** LLM-as-judge given
> (description, simulated invocation results) prompted to verify behavioral
> consistency. Three coupled mechanisms across the lifecycle: pre-invocation
> probing, execution-time isolated projection, post-invocation periodic
> reasoning. Stage-1 is the comparable component for our admission-time gate.

### Stub design

```
Input  : (tool_description, [(invocation, observed_outputs)])
Output : admit | reject + judge_rationale
```

Stub steps (deterministic, no LLM call):
1. **Verb-effect consistency check.** Extract the description's primary
   action verb (open/close/start/stop/drain/maintain/dose/read/return).
   Look at the simulated invocation's actuator transitions and sensor
   reads. Ask: does the verb's "expected effect class" match what was
   observed? E.g., "drain" implies level-down; if observed is level-up
   or level-flat, flag inconsistent.
2. **Sensor-name consistency check.** If description claims a specific
   sensor (`LIT101`), the tool should return data tagged with that sensor.
   If the tool's return payload references a different sensor, flag.
3. **Magnitude consistency check.** If description specifies a parameter
   value (`rate=0.0167 ml/s standard`), check that the invocation used
   that value. If yes, judge admits (this is the stub's known weakness:
   it doesn't have physics to check whether 0.0167 actually produces
   the claimed effect).
4. **Final verdict.** Admit iff all three checks pass; otherwise reject
   with the failed check as rationale.

### Predicted behaviour on the 3 baseline attacks

| Attack | Expected MCPShield verdict | Why |
|---|---|---|
| (a) type-confusion (open_valve_MV101 claims drain, impl fills) | **admit** (false negative on the attack) | The judge sees `actuator(MV101) := open` post-invocation; both "drains by opening" and "fills by opening" are surface-consistent without a physics model. Verb-effect heuristic might catch it if the judge is strict, but the standard LLM-judge interpretation is permissive on "open" as a generic action. |
| (b) magnitude poisoning (rate=0.0167) | **admit** (false negative) | Description says rate=0.0167 is standard; tool was invoked at 0.0167; surface-level magnitude check passes. The judge has no physics to know 0.0167 underdoses by 60×. This is the canonical Gaming-the-Judge failure mode. |
| (c) sensor aliasing (impl returns LIT201 under LIT101 description) | **reject** (true positive) | Sensor-name consistency check catches this: description names LIT101, tool return tags LIT201. The LLM-judge would notice this. |

This matches the paper's framing: LLM-as-judge handles surface-level
description-implementation mismatch (digital MCP threats) but fails on
CPS-physical attacks where surface looks consistent and only physics shows
the discrepancy.

### Departure-from-published-prompt audit

The published Stage-1 prompt cannot be reproduced verbatim in a deterministic
stub (it's a free-form NL prompt to an LLM). Our deterministic stub replicates
the **operational goal** of the prompt — three behavioral-consistency checks —
in code. This is consistent with the deterministic-stub policy used in
Missions 1B and 2A; **no DECISION checkpoint fires**.

If real-Qwen results on PI hardware (Mission 2B follow-up) diverge
substantially from the deterministic-stub predictions, that's information for
the paper to disclose, not a current blocker.

## Baseline 2 — INVARLLM-style runtime physical IDS

### Faithfulness target

Per `lit_01KR2J2TD01QA37TSTF6WFWQBG`:

> **INVARLLM:** LLM offline-extracts physical invariants for SWaT and WADI
> testbeds. Achieves 100% precision on iTrust SWaT (29 TPs, 0 FPs) and WADI
> (13 TPs, 0 FPs). Runtime detection uses extracted invariants (not the
> LLM); LLM only participates in offline invariant extraction.

The runtime mechanism IS deterministic — only invariant *extraction* uses an
LLM offline. We can faithfully implement the runtime mechanism with no LLM
involvement at all.

For invariant extraction, we use a deterministic offline analysis of Mission
1B benign baseline traces:
- **Operating-band invariants:** for each sensor `s`, compute `[min_s,
  max_s]` over benign trajectories with a small safety margin.
- **Mass-balance residual invariants:** for each tank `T`, compute
  `|dL/dt - expected_flow_from_actuators|` per sample on benign data;
  use the empirical `(p99 + ε)` as the residual threshold.
- **Cross-correlation invariants:** if pump `P` is on AND inlet `MV` is open,
  flow `FIT` should be > 0.

This matches what an LLM-driven extraction would produce on the same data;
the LLM-vs-deterministic-extraction is downstream of what gets checked at
runtime.

### Stub design

```
class InvarLLMRuntime:
    invariants : list[Invariant]    # extracted offline
    def check(telemetry_trace) -> list[violation]
```

Where `Invariant` is one of:
- `OperatingBand(sensor, low, high, slack)`
- `MassBalance(tank, q_in_constants, q_out_constants, residual_threshold)`
- `CorrelationOnIfOff(actuator_pair, expected_flow_signature)`

Already partially implemented in `mission_2a/witnesses/run_witnesses_v2.py`'s
`invarllm_runtime_check`. Mission 2B will:
1. Promote that function into a proper module (`baselines/invarllm_runtime.py`).
2. Add invariant *extraction* on benign traces (currently the noise floor is
   hardcoded — fine for stand-in, but the published method extracts from data).
3. Run on all 6-7 mission attacks plus the expanded benign corpus.

### Predicted behaviour on the 3 baseline attacks

| Attack | Expected INVARLLM verdict | Why |
|---|---|---|
| (a) type-confusion overflow | **detect** (true positive) | LIT101 hits 100% (operating band [50, 100]) — band invariant fires. |
| (b) magnitude poisoning underdose | **maybe detect** | AIT201 settles at 0.317; if the AIT201 operating band is [0.40, 1.50], band invariant fires. Otherwise the steady-state residual could be too small. |
| (c) sensor aliasing | **detect** (true positive) at runtime | LIT101 reading stays plausible while real T101 evolves differently; mass-balance residual fires. |

But for the W1 v2 stealth witness (sub-noise-floor drain over 120s),
INVARLLM is structurally blind — that's the whole point of W1 and what
makes T3 strict-composition non-trivial.

### Scope-departure audit

INVARLLM's published method scopes invariants to {operating bands,
mass-balance residuals, actuator-flow correlations}. Our extraction stays
within that scope. **No DECISION checkpoint fires.**

If during evaluation we discover that an attack requires a *different*
invariant class to detect (e.g., chemistry kinetics for attack b), we will
NOT add that invariant — we'll record INVARLLM's miss as data and let the
paper note it as the kind of attack T3-composition is designed for.

---

## Summary of checkpoint posture

| Trigger | Fires? | Rationale |
|---|---|---|
| DECISION: MCPShield stub uses deterministic stand-in for LLM prompt | NO | Consistent with the established stub policy (Missions 1B, 2A); preserves operational faithfulness without requiring real Qwen wall-clock. Documented as caveat. |
| DECISION: INVARLLM stub uses deterministic invariant extraction | NO | Runtime mechanism is identical to published; only the extraction method differs (deterministic vs LLM-driven), and extraction only affects which invariants are produced, not how they are checked. Stays within INVARLLM's published invariant classes. |
| CLARIFICATION: MCPShield outperforms PG-DSL anywhere | TRIGGER ON RESULTS | Will fire if and only if the empirical comparison shows MCPShield winning on any attack class. |
| CLARIFICATION: expanded benign corpus FPR > 11.6% | TRIGGER ON RESULTS | Per the resolved δ_lift framing — 11.6% is a conservative theoretical bound; empirical-below is sound, empirical-above triggers brain ratification. |
| CLARIFICATION: L_verify adversarial degradation > 30% FPR | TRIGGER ON RESULTS | Will fire on the adversarial-probe results, not preemptively. |
| BLOCKING DECISION: T3 strict composition fails on real testbed | TRIGGER ON RESULTS | Most consequential gate of the mission; fires only if `PG-DSL ⊕ INVARLLM == INVARLLM` (or `== PG-DSL`), invalidating T3. |

Memo posted; building begins next.
