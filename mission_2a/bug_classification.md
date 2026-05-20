# Task 4 — Bug Classification

**Mission:** mis_01KR2W2P9XKTC37MKYQ9FW5YF1 (Mission 2A).
**Embedded condition (Gate 0):** Classify each of the 5 Mission 1A/1B bugs as
**physics-fidelity** (DT departs from real-plant behaviour in a way that affects
ε_DT) vs **implementation** (code, plumbing, configuration). Any physics-fidelity
bug fires DECISION CHECKPOINT for A5 re-validation.
**Verdict:** **PASS — all 5 bugs are IMPLEMENTATION.** No DECISION checkpoint fires.

---

## Definition of physics-fidelity vs implementation

Per the Gate 0 verdict (jrn_01KR2W01CPVT6H48SMFM80XJXC) and project DT scoping
(jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX):

- **Physics-fidelity bug** — A defect where the DT's representation of an
  **in-scope** physical phenomenon (mass-balance dynamics, discrete actuator
  state, linear flow under nominal conditions) departs from real-plant
  behaviour in a way that compromises ε_DT, the bound used by Theorem T1.
- **Implementation bug** — A defect in code, test specification, agent logic,
  or out-of-scope simplification, where the in-scope DT physics remain
  unchanged.

A5's claim is specifically about mass-balance dynamics. Chemistry kinetics,
sensor-noise distributions beyond bounded-uniform, hardware ageing, network-
layer attacks, and side-channel attacks on `L_verify` are **out of A5's scope**
by jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX. Defects in out-of-scope phenomena are
classified as implementation, not physics-fidelity.

---

## Bug 1A.1 — `t1_verify.py` matcher threshold off by 30×

**Source:** Mission 1A report `anomalies` field, paragraph 1.
**Symptom:** `threshold = c_threshold * (eps_L + eps_DT) * horizon` — multiplied
by horizon=30 — produced a matcher threshold of ≈33.5 %-full where the
correct value is 1.116 %-full.
**Fix:** Removed the `* horizon` factor; the per-sample triangle-inequality
bound `τ = c_m·(ε_L + ε_DT)` does not scale with horizon.
**Affected component:** Verification harness (`t1_verify.py`), not the plant
simulator.
**Classification: IMPLEMENTATION.** A coding error in the verification
harness's threshold formula. The DT simulator (`tractable_model.md` dynamics)
was not involved. ε_DT itself is correct; only the *use* of ε_DT in the
matcher's formula was wrong.

---

## Bug 1A.2 — Honest baseline schedule physically inconsistent with lifted claim

**Source:** Mission 1A report `anomalies` field, paragraph 1 (second clause).
**Symptom:** The "honest" attack-free baseline schedule used `(V_in:open,
V_out:closed)` while the lifted claim was `(V_in:open, V_out:closed, ΔL:flat)`.
With `q_in = q_out` and only `V_in` open, the physical dynamics give
`ΔL = +q_in > 0`, contradicting `ΔL:flat`. This produced spurious 100 %
baseline detection at δ=0.
**Fix:** Honest baseline now uses `(V_in:closed, V_out:closed)` — both valves
isolated, which IS physically consistent with `ΔL:flat`.
**Affected component:** Test harness specification, not plant simulator.
**Classification: IMPLEMENTATION.** A test-spec mismatch: the harness's
representation of "honest" was internally inconsistent. The plant simulator
correctly computed `ΔL = +q_in` for the original schedule; the bug was that
the test claimed this schedule was "honest" when it wasn't. After the fix,
the plant runs the same dynamics; only the test inputs changed.

---

## Bug 1B.1 — Agent redundant close+drain neutralised attack (a)

**Source:** Mission 1B report `anomalies` field, paragraph 1, item (1).
**Symptom:** When `LIT101 > target_high`, the deterministic stub agent called
`close_valve_MV101` AND `stop_pump_P101` AND looked for a drain tool. The
close+stop neutralised the type-confusion attack (which relies on the agent
*using* the poisoned drain tool while pumps remain on).
**Fix:** Drain-tool-only branch — when level too high and a drain-described
tool exists, the agent uses it exclusively; falls back to close/stop only
when no drain tool is found.
**Affected component:** Deterministic stub agent (`mission_1b/agent/agent.py`),
not plant simulator.
**Classification: IMPLEMENTATION.** Agent-stub design choice. Real LLM agents
are not constrained to this exact policy; the stub's revised behaviour
(prefer most-direct-fitting tool) is closer to plausible LLM behaviour. Plant
simulator and DT physics are unchanged.

---

## Bug 1B.2 — Plant chemistry too forgiving for attack (b) [BORDERLINE]

**Source:** Mission 1B report `anomalies` field, paragraph 1, item (2).
**Symptom:** Initial chemistry parameters (`ait201_init = 0.50`,
`ambient_blend_rate = 0.005`) caused AIT201 to climb above the underdose
threshold of 0.4 even at the magnitude-poisoning attack's 0.0167× dosing rate.
The attack (b) success predicate (≥60s sustained AIT201 < 0.4 after dosing)
never fired.
**Fix:** Tightened parameters to `ait201_init = 0.30`, `ait201_baseline = 0.30`,
`ambient_blend_rate = 0.05` so that no-dosing chemistry settles below
threshold and the 0.0167× rate is insufficient to lift it.
**Affected component:** Plant simulator's chemistry model.
**Classification: IMPLEMENTATION (with caveat).** This is the most borderline
of the five and warrants explicit reasoning:

1. **Chemistry kinetics are explicitly out-of-scope** per
   jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX:
   *"OUT OF SCOPE (not modeled by MiniCPS for SWaT, would require
   chemistry-fidelity DT): Chemical kinetics (chlorination dynamics,
   dechlorination, pH-dependent reactions in P3) ..."*
   The plant simulator's linear-conductivity model is a deliberate stand-in
   for unmodelled real chemistry, not a fidelity claim.

2. **A5's claim is about mass-balance dynamics only.** The fix did not modify
   any mass-balance parameter (`q_in_p101_p102`, `q_out_to_p2`, `q_out_t201`,
   tank levels). All of those remain unchanged.

3. **Both pre-fix and post-fix chemistry parameters are arbitrary.** Neither
   set is calibrated against real iTrust SWaT conductivity data — they are
   chosen so the testbed exhibits a controllable underdose signature for
   demonstration. The fix tuned this stand-in's free parameters to surface
   the attack; it did not "make the simulator more like real plant" or
   "less like real plant" in any calibrated sense.

4. **ε_DT in T1 is per-sample sensor noise on level reading**, not on
   chemistry. The fix has no effect on ε_DT or on the level-trajectory
   used in T1 verification.

Hence: implementation-tier tuning of an out-of-scope stand-in. Does not
compromise A5. **No DECISION checkpoint fires for this bug.** A real-plant
chemistry model (Mission 2B if SWaT P3+ extension lands) would warrant a
fresh A5-style validation specifically for chemistry; that is outside
Mission 2A's scope.

---

## Bug 1B.3 — Intent classifier double-counted prerequisite mentions

**Source:** Mission 1B report `anomalies` field, paragraph 1, item (3).
**Symptom:** Count-based verb classifier scored `start_pump_P101`'s
description as intent="open" because the description text says "*Inflow into
T101 occurs only when MV101 is also **open**. Standard operating procedure:
**open** MV101 first, then start the pump.*" — "open" appears twice, "start"
once, so "open" wins.
**Fix:** Position-based first-verb classifier: returns the intent of the
first verb keyword that appears in the description, mirroring LLM
top-to-bottom reading order.
**Affected component:** Deterministic stub agent's NLP heuristic.
**Classification: IMPLEMENTATION.** Pure NLP/regex coding choice in the
agent stub. Plant physics, DT simulator, and ε_DT are not involved. Real
LLMs would not use this heuristic at all (they parse semantics directly);
the stub's classifier is purely a deterministic stand-in.

---

## Summary table

| # | Bug | Component | Classification | Affects ε_DT? |
|---|---|---|---|---|
| 1A.1 | Matcher threshold off by 30× | Verification harness | IMPLEMENTATION | No |
| 1A.2 | Honest baseline schedule inconsistent | Test spec | IMPLEMENTATION | No |
| 1B.1 | Agent close+drain neutralisation | Agent stub | IMPLEMENTATION | No |
| 1B.2 | Plant chemistry too forgiving | Out-of-scope chemistry stand-in | IMPLEMENTATION (borderline) | No |
| 1B.3 | Intent classifier prereq double-count | Agent stub NLP | IMPLEMENTATION | No |

**All 5 classified IMPLEMENTATION. Zero physics-fidelity bugs. Embedded
condition 3 PASS — no DECISION checkpoint fires.**

A5 (DT mass-balance fidelity) remains validated as per Gate 0 verdict; no
re-validation required.

---

## Note for brain post-hoc review

Bug 1B.2 is the only one with non-trivial classification ambiguity. The
classification rests on jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX scoping chemistry as
out-of-scope. If brain disagrees and considers chemistry parameters part of
A5's fidelity envelope, this becomes a physics-fidelity bug and an A5
re-validation checkpoint is required. The above reasoning preserves the
audit trail so brain can override the classification if desired.
