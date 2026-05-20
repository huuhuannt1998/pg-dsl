# Tractable Single-Tank Model for T1 Verification

**Mission:** mis_01KR2R4Q9Y3WZHZ53473PPZS66 (Mission 1A — PG-DSL theorem framework validation)
**Scope:** Single-tank reservoir. Multi-stage SWaT extension is explicitly out of scope (Mission 2).
**Purpose:** Concrete instantiation of T1's detection bound on a model where every quantity (δ, ε_L, ε_DT, F) is computable so the bound's non-vacuity can be checked numerically.

---

## 1. Plant

A single open-top reservoir `T101` with one inlet valve, one outlet valve, and one level sensor.

| Symbol     | Meaning                                | Domain                | Unit     |
|------------|----------------------------------------|-----------------------|----------|
| `L`        | True liquid level in T101              | `[0, 100]`            | %-full   |
| `V_in`     | Inlet valve actuator state             | `{open, closed}`      | binary   |
| `V_out`    | Outlet valve actuator state            | `{open, closed}`      | binary   |
| `q_in`     | Inflow rate when `V_in = open`         | `> 0`                 | %-full/s |
| `q_out`    | Outflow rate when `V_out = open`       | `> 0`                 | %-full/s |
| `L_sensor` | Reading reported by the level sensor   | `[0, 100]`            | %-full   |

For numerical work we fix `q_in = q_out = q = 1.0 %/s`. Asymmetric rates do not change the
qualitative analysis but complicate the witness arithmetic.

## 2. Continuous-Time Dynamics

```
dL/dt = q_in · 1[V_in = open] − q_out · 1[V_out = open],   with L clamped to [0, 100].
```

Discretized at a fixed sampling period `Δt` (default `Δt = 1.0 s`):

```
L[k+1] = clip(L[k] + Δt · (q_in · 1[V_in[k]=open] − q_out · 1[V_out[k]=open]), 0, 100).
```

This is the digital-twin (DT) integrator used to advance the simulated tank under any
candidate actuator schedule.

## 3. Sensing Model (DT-Side, Bounded Error)

The DT exposes a noisy level estimator with **bounded** error (no Gaussian tails — bounded
error is what makes T1's worst-case bound a hard threshold rather than a tail probability):

```
L_sensor[k] = L[k] + n[k],     with |n[k]| ≤ ε_DT.
```

`ε_DT` aggregates two sources:
1. **Sensing noise** — bounded ADC quantisation + manufacturer-spec accuracy on LIT101.
2. **Modelling error** — gap between MiniCPS mass-balance integrator and the iTrust
   physical plant on in-scope phenomena (mass balance / flow only; chemistry is out of
   scope per `jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX`).

`ε_DT` bounds the **per-sample** error.  Trajectory error grows under integration; that
amplification is part of what `F(δ, ε_L, ε_DT)` must capture (see §6 / Task 4 checkpoint).

## 4. Lifted-Claim Space

A tool description, after lifting by `L_verify`, produces a formal claim `φ` over the
grammar in `grammar/grammar.lark`. Restricted to the single-tank model, `φ` is a triple

```
φ = (V_in_claim, V_out_claim, ΔL_claim) ∈ {open, closed} × {open, closed} × {↑, ↓, ≈0}.
```

The **physically consistent** triples (those a sound lifter `L_verify` should ever emit
on an honest description, given `q_in = q_out`) are:

| `V_in`   | `V_out`  | `ΔL`  | Why                                              |
|----------|----------|-------|--------------------------------------------------|
| `open`   | `closed` | `↑`   | net inflow                                        |
| `closed` | `open`   | `↓`   | net outflow                                       |
| `closed` | `closed` | `≈0`  | isolated                                          |
| `open`   | `open`   | `≈0`  | flows cancel (since `q_in = q_out`)              |

Any other triple is a **lifting error** and falls under T2's soundness analysis. T1
assumes the triple is consistent and asks whether the *physical effect claimed* matches
the *physical effect observed in the DT*.

## 5. Threat Model on the Tractable Model

A description-poisoning adversary supplies an MCP tool description whose natural-language
text reads as "Open inlet to maintain level" (so `L_verify` lifts to `φ_lifted = (V_in:
open, V_out: closed, ΔL: ↑)`) but whose underlying tool implementation, when run in the
DT, drives `(V_in: closed, V_out: open)`, i.e. `ψ_actual = (V_in: closed, V_out: open,
ΔL: ↓)`.

The defender's admission-time check runs the tool against the DT for `T_horizon` seconds
starting from a baseline level `L_0`, observes `L_sensor[0..T_horizon/Δt]`, computes the
empirical level trajectory, and compares it against `φ_lifted` via a matcher.

Define the **physical-state distance**

```
δ = | L_lifted(T_horizon) − L_actual(T_horizon) |
```

where `L_lifted(T_horizon)` is the level the lifted claim *predicts* after `T_horizon`
seconds (e.g., `L_0 + q · T_horizon` for `ΔL: ↑`) and `L_actual(T_horizon)` is what the
DT actually produces under the tool. `δ ≥ 0`.

## 6. Plug Points for T1

T1 is parameterised by:

- `δ`     — physical-state distance between lifted and actual.
- `ε_L`   — worst-case lifter error on class C. Concretely on this model, the maximum
  deviation between `φ_lifted` and the "true" lifted intent of the description (e.g.,
  bounded by lifter-LLM benchmark accuracy on the grammar).
- `ε_DT`  — per-sample DT sensing/modelling error bound.

T1 claims:

```
P( detect | δ ≥ δ_thr ) ≥ 1 − F(δ, ε_L, ε_DT),
```

with `δ_thr = δ*(ε_L, ε_DT) = O(ε_L + ε_DT)`.

The functional form of `F` and concrete numerical anchors `(ε_L, ε_DT)` are **not** set
in this document. They require a DECISION checkpoint to the brain (see mission instructions
on autonomy boundaries).  Section 7 records the structural shape of `F` that the witness
construction (Task 5) and verification script (Task 7) must respect.

## 7. Structural Constraints `F` Must Satisfy

Any candidate `F` proposed by the brain must satisfy, at minimum:

1. `F(δ, ε_L, ε_DT) → 0` as `δ → ∞` (large attacks always detected).
2. `F(δ, ε_L, ε_DT) → 1` as `δ → 0` (vanishing attacks indistinguishable from noise).
3. `F(δ, 0, 0) = 0` for all `δ > 0` (perfect lifter + perfect DT detect any deviation).
4. There exists `δ* = c · (ε_L + ε_DT)` with `c = O(1)` such that `F(δ, ε_L, ε_DT) ≡ 1`
   for `δ < δ*` (formalises the impossibility region).
5. `F` should be derivable from the bounded-error sensing model in §3 — no Gaussian or
   sub-Gaussian assumptions.

## 8. What This Document Does *Not* Decide

- Specific functional form for `F` (Task 4 checkpoint).
- Numerical anchors `ε_L = ?`, `ε_DT = ?` (Task 5 checkpoint).
- T3 witness attacks (Task 6 checkpoint).
- Lean/Coq formalisation (out of scope for Mission 1A).
- Multi-stage extension to P2/P3/.../P6 (Mission 2).

## 9. Cross-References

- Theorem statements and class C: `jrn_01KR2JP8DJ0X21RAZGJMP1M3AA`
- Impossibility-pair justifying physics-grounded verification: `jrn_01KR2JVMTK3NWQWYXCGG8ZXW3D`
- DT scoping (in/out of scope): `jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX`
- Verifier-mechanism choice: `dec_01KR2HMMHE30R9RF78F4ZGX0WX`
- Lifter-implementation choice: `dec_01KR2HNVAFP7JJN3D827W5GMQH`
- Grammar productions: `grammar/grammar.lark`, `grammar/coverage.md`
