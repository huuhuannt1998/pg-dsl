# Pre-registration — revision-pass III (review-driven), fixed 2026-08-25 before any run

Both experiments answer items in `.planning/REVIEW_ai-cyber-paper-reviewer_2026-08-25.md`.
Predictions and scoring rules are fixed here first; results are reported whether or not
they land.

## E1 — headline numbers at the adopted grid (K = 30)

**Concern.** §5.7 shows the published 3-state grid is an attack surface and says "we adopt
K = 30 going forward", yet every headline figure is measured at K = 3.

**Design.** Re-run through the *shipped* admission layer (`PGDSLAdmissionLayer`, deterministic
stub, unchanged matcher) with `_run_dt_samples` iterating 30 Latin-hypercube initial states
over (LIT101, LIT201) instead of LOW/MID/HIGH — the same LHS generator and seed family as
`n5b_coverage_curve.py`. Three workloads: (a) canonical 8 attacks via `PGDSLCanonicalLayer`
as in `n1d_canonical8.py`; (b) 14 honest tools × 30 states = 420 benign per-tool verdicts;
(c) the 134 mutants of `e11_mutation.py`, plus the two hardened rules of n2/n3 if their
harnesses accept the same state override.

**Scoring.** Identical to the K = 3 runs: a tool/mutant is detected iff the shipped layer
rejects it on any state; canonical detection uses `detected_at_admission` (per-tool OR
composition).

**Predictions.**
- P1 canonical: 6/8 unchanged (W1, W2 remain runtime-only). Falsifier: any of A1, A2, A3,
  Z1, Z2, Z3 becomes MISS, or W1/W2 becomes DET.
- P2 benign: 0/420 rejections. Falsifier: ≥ 1 rejection.
- P3 mutants (shipped): state-conditional 0/16 → 16/16; every other class unchanged;
  aggregate 70/134 → 86/134. Falsifier: state-conditional < 16/16, or any other class moves.
- P4 mutants (hardened): 94/134 → 110/134 (the two rules do not touch state-conditional).
  Falsifier: ≠ 110/134.

## E2 — INVARLLM benign false-positive rate

**Concern.** "8/8 covered when composed with INVARLLM" rests on W1 being caught by a
`band_LIT201 [60,100]` violation that also fires for W2 and Z1–Z3, and INVARLLM's invariants
were mined from `mission_1b/results/benign/rep*.json`. No honest trace outside that fit set
has ever been checked.

**Design.** Build INVARLLM exactly as `run_canonical_t3_partition_qwen3.py` does
(`_build_invarllm()`), then feed it the telemetry of honest replays: each of the 14 canonical
tools executed from each of LOW/MID/HIGH on a fresh plant for the same horizon the attack
traces use (42 traces), plus the 30 LHS states of E1 for the 8 actuator tools (240 traces).

**Scoring.** A trace is a false positive iff `ids.check()` reports ≥ 1 violation. Report
count, which invariant fired, and whether the violation is present at t = 0 (initial-state
artifact) or arises during the horizon.

**Predictions.**
- P5: ≥ 1 benign violation on the 42, all on `band_LIT201`, all present at t = 0 for the
  LOW initial state (LIT201 below the mined 60 floor); 0 mass-balance violations.
  Falsifier: 0/42 violations, or any mass-balance violation on an honest trace.
- P6: the W1 "detection" is therefore not W1-specific; whether it survives as evidence
  depends on whether the benign rate is 0 (it does) or > 0 (it does not, and §5.4 must
  say so). Either outcome is reported.

## E1b — the deployed lifter at K = 30 (added after E1; fixed before running)

E1's P1 was mis-specified: it named the deployed (qwen3:14b) baseline of 6/8 while the
pre-registered run used the deterministic stub, whose baseline is 5/8 (Z2 is the stub-only
miss at K = 3). Stub at K = 30 is 5/8 with the same Z2 miss — no verdict moved. E1b runs the
deployed lifter (prompt v1, lifts cached per (tool, description)) with the same 30-state
override, composition grid unchanged.

- P1b: 6/8 — A1, A2, A3, Z1, Z2, Z3 detected; W1, W2 missed. Falsifier: any change.

## E3 — INVARLLM re-mined on benign traffic that spans the admission grid (fixed before running)

**Why.** E2 found the INVARLLM instance used for the T3 partition fires on 42/42 honest
admission-style traces: its bands were mined from ten benign reps that all start at MID
(70/60) under agent control, so any trace starting at LOW or HIGH is out-of-band at t = 0 and
even MID traces trip `band_LIT201` when the tool does not feed T201. Every attack's
"runtime detection" — W1 and W2 included — was a band hit; mass balance fired on nothing.
The only fair runtime column is one whose invariants were mined on benign traffic covering
the states the attack traces start from.

**Design.** Mine INVARLLM (same `extract_from_traces`, same slack/safety factors) on the ten
reps **plus** the 42 honest admission traces (14 tools × LOW/MID/HIGH, 120 s). Hold out the
240 LHS honest traces of E2 as an out-of-sample benign set. Recompute the runtime column for
the 8 canonical attack traces (regenerated from the same deterministic simulators). PG-DSL's
column is unchanged and is taken from `t3_partition_canonical.json`.

**Predictions.**
- P7 honest FPR on the held-out 240: ≤ 12/240 (5 %; the LHS extremes 25/95 and 20/95 sit
  just outside the 30–90 mining range). Falsifier: > 12/240.
- P8 mass balance fires on no honest trace. Falsifier: any.
- P9 A1, W2, Z3 (all overflow T101 past 95) stay runtime-detected via `band_LIT101`.
- P10 A2 stays runtime-missed (AIT201 0.317 is inside a band whose floor is the 0.30 start).
- P11 **W1 becomes runtime-missed**: a 3 %-full drift from a mid-band start stays inside a
  band that now spans the grid. If so, W1 is caught by neither layer and composed coverage is
  7/8, not 8/8; the T3 strict difference survives on W2 alone. Falsifier: W1 detected.
- P12 A3 and Z1 become runtime-missed (physically honest trajectories). Z2 stays detected via
  `band_AIT201` (overdose to 5.0). Falsifiers stated per attack.
