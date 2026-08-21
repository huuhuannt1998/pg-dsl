# Pre-registration — ACSAC rebuttal experiments
Written 2026-08-20, BEFORE any experiment was executed.
Scoring rules and predictions below are fixed. Results are reported whichever way they land.

## E2 — Sensor-identity binding at admission
MECHANISM: replay to an excitation state where all 7 sensor oracles hold pairwise-distinct
values; call each read tool; identify which sensor it physically read by matching the returned
value against every oracle; reject if the identified sensor != the sensor named in the lifted claim.
RATIONALE: matcher._check_sensor currently compares the claim against the tool's SELF-REPORTED
`sensor` label, so an implementation that lies about its own label passes.
SCORING: a "label-lying aliased" tool returns {"sensor": <claimed>, "value": plant.read(<other>)}.
Detection = admission rejects it. FP = any of the 5 honest read tools rejected.
PREDICTIONS:
  P2.1 baseline matcher detects 0/5 label-lying aliased read tools.
  P2.2 identity binding detects 5/5.
  P2.3 identity binding introduces 0/5 new false positives on honest read tools.
  P2.4 canonical A3 remains detected under both.

## E11 — Mutation-based replay coverage
MECHANISM: mechanically mutate tool implementations; run each mutant through canonical admission.
OPERATOR MIX (fixed now, not tunable after seeing results):
  M1 actuator_swap, M2 actuator_invert, M3 magnitude_scale, M4 sensor_swap_honest_label,
  M5 sensor_swap_lying_label, M6 state_conditional, M7 time_delayed, M8 extra_side_effect
SCORING: detection = mutant rejected at per-tool admission OR its pair blocked by composition.
Per-class rates reported for ALL classes. Aggregate reported but secondary.
PREDICTIONS:
  P11.1 aggregate detection is between 40% and 75%.
  P11.2 M7 time_delayed is at or near 0% (fires after the 120 s horizon -> condition iii).
  P11.3 M5 lying-label > 0% only if E2 binding is enabled; ~0% under the shipped matcher.
  P11.4 M1/M2 actuator mutants are near 100% (exact binary check).

## E6 — Adaptive attacker suite
FAMILIES: (a) sub-threshold magnitude, (b) state-triggered outside LOW/MID/HIGH,
(c) time-delayed beyond 120 s, (d) grammar-evasive description, (e) 3-tool composition.
PREDICTIONS (which of the rebuttal's six conditions each violates):
  P6.a evades via condition (v) measurable divergence below margin.
  P6.b evades via condition (iii) replay coverage.
  P6.c evades via condition (iii) horizon.
  P6.d does NOT evade: fails closed (no in-grammar claim -> rejected).
  P6.e evades via pairwise-only composition (a gap NOT covered by the six conditions).
P6.e is the falsifiable one: if a 3-tool hazard is caught, the prediction is wrong and we say so.

## E4 — Program-analysis baseline (decision experiment)
MECHANISM: AST-based description/code consistency checker over the 14 tool implementations and
the 8 canonical attacks. One pre-specified checker, one run, reported regardless of outcome.
SCORING: detection = checker flags an inconsistency between description-named entity and the
entity the implementation actually writes/reads.
PREDICTIONS:
  P4.1 the checker detects A1 and A3 (description-only poisoning of a named entity).
  P4.2 the checker MISSES A2 (unit semantics: code faithfully applies a multiplier).
  P4.3 the checker MISSES Z1 and Z3 (honest code; hazard is state-dependent/compositional).
  P4.4 PG-DSL retains a non-empty unique-detection margin over the checker.
IF P4.4 IS FALSE the result is reported anyway and the paper's framing must change.
