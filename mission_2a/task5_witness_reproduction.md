# Task 5 — T3 Witness Reproduction on Real Testbed

**Mission:** mis_01KR2W2P9XKTC37MKYQ9FW5YF1 (Mission 2A).
**Embedded condition (Gate 0):** Reproduce both T3 witnesses on the Mission 1B P1+P2
testbed (not just the tractable single-tank model). Failure to generalise fires
DECISION CHECKPOINT.
**Verdict:** **W2 PASS, W1 FAIL → DECISION CHECKPOINT FIRED.**

---

## 1. W2 — post-admission LIT101 spoofing — PASS

| Step | PG-DSL admission | INVARLLM runtime |
|---|---|---|
| Honest READ_LEVEL_T101 description, lifted as `sensor(LIT101) reads x` | δ̂ = 0.000 < τ = 1.116 → **admit** ✓ | n/a (admission phase) |
| Post-admission attacker spoofs LIT101 = 80 (constant) while P101=on, MV101=open | already done at admission | mass-balance residual = 0.5 %/s vs expected 0 → **fires** ✓ |

W2 passes as specified. PG-DSL admits (the description is honest at admission and
the impl is honest at admission); INVARLLM fires at runtime on the FIT101–LIT101
mass-balance violation. The two defenses cleanly separate on this attack.
Trace: `mission_2a/results/w2_trace.json`.

## 2. W1 — slow-drain in-band poisoning — FAIL (saturated-lane collapse)

Mission 1A specified W1 as a 5 %-full drift over a 30 s admission horizon
(drain rate 0.167 %-full/s) under a `MAINTAIN_LEVEL(target=80)` description
that lifts to `Δstate(L_T101) { sign 0 }`.

| Defense | Expected (Mission 1A) | Observed (real testbed) |
|---|---|---|
| PG-DSL admission | fire (δ̂ ≈ 5 ≫ τ = 1.116) | **fire** (δ̂ = 5.010, τ = 1.116) ✓ |
| INVARLLM runtime stand-in | miss (drift below dot-L noise floor) | **fires** (mass-balance residual ≈ 0.167 %/s ≫ noise floor 0.033 %/s) ✗ |

Both defenses fire, so W1 does NOT lie in `A_static \ A_runtime`; the strict-
composition claim is empirically uncorroborated for this witness on the real
testbed. Trace: `mission_2a/results/w1_trace.json`.

### 2.1 Why W1 collapsed

INVARLLM's mass-balance invariant on this testbed has a residual noise floor
≈ 1 %-full / 30 s (≡ 0.033 %/s per-second threshold). This is the natural
calibration: in the Mission 1B benign baseline, LIT101 sits stably at 70 with
no actuator activity, so the benign mass-balance residual is ≈ 0 modulo
ε_DT = 1.0 per-sample sensor noise; an INVARLLM-style invariant calibrated
to "0 false positives on benign" lands at ≈ 1 %-full / 30 s.

Mission 1A's W1 claimed *"drain rate ≈ 5 %/30 s falls below INVARLLM's noise
floor"*. The Mission 1A report's findings field flagged this exact assumption
as the highest-priority brain validation item:
> *"W1 separation from INVARLLM relies on (a) staying inside INVARLLM's level
> band [50,100] and (b) keeping the drain rate below INVARLLM's empirical
> dot-L noise floor (~1%-full per 30s window). 5%-full drift over 30s
> pushes the dot-L envelope; if INVARLLM's noise floor in practice is
> tighter than ~5%-full/30s, W1 collapses..."*

The Mission 1A report's fallback ("80 → 78 over 30s, δ = 2") was also wrong:
δ = 2 < δ* = 2.232 → PG-DSL doesn't fire either.

### 2.2 Feasibility analysis at the spec-specified 30 s window

To pass W1 we need:
1. δ > δ* = 2.232 %-full (PG-DSL fires)
2. drain_rate < INVARLLM noise floor (INVARLLM misses)

At a fixed window T = 30 s, drain_rate = δ/T:
- (1) ⇒ drain_rate > 2.232/30 = 0.0744 %/s
- (2) ⇒ drain_rate < 0.033 %/s (the testbed-realistic noise floor)

These are mutually inconsistent at T = 30 s. The W1 witness is **infeasible on
this testbed at the spec-specified 30 s admission window** under any reasonable
noise-floor calibration of an INVARLLM stand-in.

### 2.3 Feasibility at extended admission window

Solving δ/T > δ* AND δ/T < 0.033:
- δ/T > 0.0744 forces δ > 0.0744·T
- δ/T < 0.033 forces δ < 0.033·T
These are inconsistent unless we relax one side. With T ≥ 67 s and a sub-
threshold drain rate (e.g. 0.025 %/s), the cumulative δ over T satisfies
δ > 2.232 while drain rate < noise floor. So **an extended admission window
makes W1 feasible**.

Concretely, T = 90 s and drain_rate = 0.025 %/s gives:
- δ = 2.25 > δ* (PG-DSL fires)
- drain_rate = 0.025 < 0.033 (INVARLLM noise floor) → INVARLLM misses

This is W1's natural fix and the most surgical change (no theorem rewrite, no
witness rewrite — just the admission window length).

## 3. DECISION CHECKPOINT FIRED

Per task 5 trigger: "If either witness fails to generalize, FIRE DECISION
CHECKPOINT." Pipeline tasks 6–13 already blocked on
`chk_01KR2WK51Y1ZW6SF2K2XWR7ZQ8` (grammar coverage). This adds a second
blocking dependency.

Brain to choose between the four options listed in the checkpoint description
(extend admission window, lower δ* by tightening anchors, redesign W1 as a
non-monotonic perturbation, or accept W1 as theoretical-only).
