# Two-Tank Tractable Model for T1_v Verification

**Mission:** mis_01KR49N65QSX03VYGC9SSSF325 (Mission 3A — T1 vectorization theory)
**Scope:** Two-tank coupled reservoir (n = 2 state coordinates). Multi-stage extension is explicitly out of scope.
**Purpose:** Concrete instantiation of T1_v's vectorized detection bound on a model where every per-coordinate quantity (`δ_v`, `ε_L_v`, `ε_DT_v`, `F_v`) is computable so the bound's non-vacuity can be checked numerically; sufficient to demonstrate the admission-domain expansion (single-tool ∪ ordered-pair) introduced by Z3b option B (dec_01KR49FTB2ND38DW36094G95ZM).

This document parallels `mission_1a/tractable_model.md` (single-tank, n = 1) and extends it to vectorized state with composition-aware admission.

---

## 1. Plant

Two coupled open-top reservoirs `T101` (upstream) and `T201` (downstream).

| Symbol      | Meaning                                                  | Domain            | Unit     |
|-------------|----------------------------------------------------------|-------------------|----------|
| `L_T101`    | True liquid level in T101                                | `[0, 100]`        | %-full   |
| `L_T201`    | True liquid level in T201                                | `[0, 100]`        | %-full   |
| `V_in1`     | Inlet valve to T101 (analogue: SWaT MV101)               | `{open, closed}`  | binary   |
| `P1`        | Raw-water pump feeding T101 (analogue: SWaT P101)        | `{on, off}`       | binary   |
| `V_couple`  | Coupling valve T101 → T201 (analogue: SWaT MV201)        | `{open, closed}`  | binary   |
| `V_out2`    | Outlet valve from T201 (downstream consumption)          | `{open, closed}`  | binary   |
| `L_T101.s`  | DT-side noisy reading of `L_T101`                        | `[0, 100]`        | %-full   |
| `L_T201.s`  | DT-side noisy reading of `L_T201`                        | `[0, 100]`        | %-full   |

Numerical defaults:

| Parameter | Value | Description |
|---|---|---|
| `q_in1`    | 1.0 %-full/s | inflow to T101 when `V_in1 = open ∧ P1 = on` |
| `q_couple` | 0.4 %-full/s | flow T101→T201 when `V_couple = open ∧ L_T101 > 0` |
| `q_out2`   | 0.3 %-full/s | downstream consumption from T201 when `V_out2 = open` |
| `Δt`       | 1.0 s | simulation step |

These parameters preserve the SWaT P1+P2 sense ratios used in Mission 1B's plant (`mission_1b/plant/swat_p1p2.py`) without requiring the full chemistry stack.

## 2. Continuous-Time Dynamics

```
dL_T101/dt = q_in1·𝟙[V_in1=open ∧ P1=on]
           − q_couple·𝟙[V_couple=open ∧ L_T101>0],     L_T101 ∈ [0, 100]

dL_T201/dt = q_couple·𝟙[V_couple=open ∧ L_T101>0]
           − q_out2·𝟙[V_out2=open],                    L_T201 ∈ [0, 100]
```

Discretized at `Δt = 1.0 s`. Both levels are clamped (saturated) to the physical envelope `[0, 100]` per simulation step.

## 3. Sensing Model (DT-Side, Bounded Error per Coordinate)

```
L_T101.s[k] = L_T101[k] + n1[k],  |n1[k]| ≤ ε_DT_v[1]
L_T201.s[k] = L_T201[k] + n2[k],  |n2[k]| ≤ ε_DT_v[2]
```

Per-coordinate bounded sensing noise. No Gaussian tails. Default
`ε_DT_v = (0.10, 0.10) %-full` (matches the per-sample sensor floor used in
Mission 3B's INVARLLM stand-in and the Z3 simulator).

## 4. Vectorized Lifted-Claim Space

A tool description, lifted by `L_verify`, produces a vectorized formal claim
`φ_v = (φ_actuator, A_φ)` where:

- `φ_actuator` is a set of single-actuator transitions (e.g.,
  `actuator(V_in1) := open`, `actuator(P1) := on`).
- `A_φ : {1, ..., n} → P(ℝ) ∪ {⊤}` is the per-coordinate admissible region:
  for each state coordinate `k ∈ {L_T101, L_T201}`, either an interval
  `[a_k, b_k] ⊆ ℝ` (a `bounded[]` clause), the singleton `{L_0[k]}`
  (a `sign 0` claim), or `⊤` (no claim — coordinate `k` is unconstrained
  by `φ_v`).

Per dec_01KR49FTB2ND38DW36094G95ZM Option B, the admission target `T` is
either:
- A single tool (single-actuator claims; `A_φ` may be `⊤` on every level
  coordinate when the description names no level band — e.g.,
  `start_pump_P101`); or
- An ordered tool pair `(D_i, D_j)` (composition admission). Composition
  admission supplies an EXTERNAL safe operating band per coordinate that
  acts as the effective admissible region `A_eff(k) = [25, 95]` for
  `L_T101`, `[20, 95]` for `L_T201` (matching `mission_3b/admission_layer/composition_verifier.py`'s
  `SAFE_BAND_LIT101 = [25, 95]`, `SAFE_BAND_LIT201 = [20, 95]`).

For T1_v's per-coordinate detection bound, what matters is the **effective**
admissible region `A_eff(k)` used by the matcher, regardless of whether it
came from `φ_v` directly or from the composition layer's safety band.

## 5. Per-Coordinate Discrepancy and Max-Norm

For trajectory `ψ_v: [0, T_horizon] → ℝ²`, define per-coordinate discrepancy

```
δ_v[k] = sup_{t ∈ [0, T_horizon]} d(ψ_v(t)[k], A_eff(k))
       where d(x, [a, b]) = max(0, x − b, a − x)
       and   d(x, ⊤)      = 0  (unconstrained — no contribution)
```

The vectorized discrepancy is `δ_v = (δ_v[L_T101], δ_v[L_T201]) ∈ ℝ²_{≥0}`.

The matcher fires iff `‖δ̂_v‖_∞ > τ*_v` where `δ̂_v` is the
DT-measured discrepancy (using the noisy sensor) and
`τ*_v = ‖ε_L_v + ε_DT_v‖_∞`.

## 6. Threat Model on the Two-Tank Model

The threat class spans both single-tool and composition attacks:

**Single-tool (Mission 1A scope, replicated at n=2):** poisoned description
mismatched to impl on coordinate 1 or coordinate 2 (e.g., `start_pump_P1`
description claims `Δstate(L_T101) sign 0` but impl drives net inflow).

**Composition (Mission 3A new scope):** two individually-admitted tools that,
called in sequence, drive a coordinate out of its safe operating band. The
canonical witness is Z3 (see §8).

## 7. T1_v Plug-Points

T1_v (per `jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ`) is parametric in:

- `‖δ_v‖_∞` — max-norm of the per-coordinate physical-state discrepancy.
- `ε_L_v` — vector of per-coordinate worst-case lifter errors.
- `ε_DT_v` — vector of per-coordinate per-sample DT sensing/modelling errors.

T1_v claims:
```
P(detect | ‖δ_v‖_∞ ≥ τ) ≥ 1 − F_v(τ, ε_L_v, ε_DT_v)
```

**Bounded-error specialization** (used in `t1_v_verify.py`):
```
F_v(τ, ε_L_v, ε_DT_v) = 1   if τ < δ*_v = 2·‖ε_L_v + ε_DT_v‖_∞
                     = 0   if τ ≥ δ*_v
```
which is the worst-case-noise step: detection is guaranteed for every noise
realization above `δ*_v`, vacuous below. (Smooth `F_v` under sub-Gaussian
sensing is future work, flagged in `jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ`.)

Default numerical anchors (matching Mission 3B's calibration):
```
ε_L_v   = (0.116, 0.116)  %-full        (Req2LTL accuracy gap, both coordinates)
ε_DT_v  = (0.10,  0.10)   %-full        (Mission 3B sample floor)
‖ε_v‖_∞ = max_k(ε_L_v[k] + ε_DT_v[k]) = 0.216 %-full
τ*_v    = 0.216 %-full   (matcher threshold)
δ*_v    = 0.432 %-full   (theorem detection-guarantee threshold)
```

The matcher threshold `τ*_v` and theorem threshold `δ*_v` differ by a factor
of `c_t / c_m = 2 / 1 = 2` (per Mission 1A's bounded-error analysis,
preserved per-coordinate under T1_v).

## 8. Z3 Witness on the Two-Tank Model

Z3's canonical attack (per Mission 3B and `mission_2a/witnesses/run_witness_z3.py`)
is the ordered pair `(open V_in1, turn-on P1)` from initial
`L_T101 = 90 %-full, V_couple = closed`.

**Predicted trajectory under `φ_v`:** Lifted `φ_v` from honest descriptions
contains only `actuator(V_in1) := open` and `actuator(P1) := on` clauses;
no `Δstate(L_T101)` claim (descriptions name no level band). At admission:
- Single-tool DT replay of each constituent from the canonical MID initial
  state (`L_T101 = 70`, `V_in1 = closed` or `P1 = off` respectively) shows
  zero level effect → both admit.
- Composition replay (Option B) replays the ordered pair from each of
  {LOW, MID, HIGH}; under `init = HIGH (L_T101 = 90)`, net inflow drives the
  trajectory beyond the safe band `[25, 95]`.

**Per-coordinate discrepancy:**
- `δ_v[L_T101] = max_t d(L_T101(t), [25, 95]) = 99.5 − 95 = 4.5 %-full` (overflow)
- `δ_v[L_T201] = 0` (T201 stays in band; the 30s horizon is too short for
  downstream coupling to push T201 out of band even if `V_couple = open`)
- `‖δ_v‖_∞ = 4.5 %-full`

**Detection verdict under T1_v:**
- `‖δ_v‖_∞ = 4.5 ≥ δ*_v = 0.432 %-full` ✓
- `F_v(4.5, ε_L_v, ε_DT_v) = 0` (in detected region) ✓
- T1_v predicts P(detect) ≥ 1 with probability 1 (worst-case-noise) ✓
- Mission 3B empirical: Z3 caught at admission ✓

Z3 anchors the detected regime of T1_v's `F_v` curve.

## 9. What This Document Does *Not* Decide

- Multi-stage (n > 2) compositions: explicitly out of scope per
  `dec_01KR49FTB2ND38DW36094G95ZM` and Mission 3A scope_boundaries.
  Future work.
- Smooth `F_v` under non-bounded-error noise (Gaussian, sub-Gaussian):
  bounded-error suffices for tractable-model verification; flagged for
  future work in `jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ`.
- T2 reformulation: T2 is per-tool lifting soundness, unaffected by
  admission-domain expansion. Statement unchanged.
- T3 statement: strict-superset claim preserved; only the witness
  partition shifts (Z3 → A_static, W1+W2 → A_runtime per
  dec_01KR49FTB2ND38DW36094G95ZM).

## 10. Cross-References

- T1_v formal statement: `jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ` (brain-produced)
- Z3b option-B canonical decision: `dec_01KR49FTB2ND38DW36094G95ZM`
- Mission 3B canonical pipeline (composition_verifier source-of-truth):
  `mission_3b/admission_layer/composition_verifier.py`
- Z3 simulator (witness source-of-truth):
  `mission_3b/attacks/z3_simulator.py`,
  `mission_2a/witnesses/run_witness_z3.py`
- Original T1 / single-tank tractable model: `mission_1a/tractable_model.md`
- Original T1 statement: `mission_1a/theorems.tex` §T1
