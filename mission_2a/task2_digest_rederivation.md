# Task 2 — Digest Re-Derivation

**Mission:** mis_01KR2W2P9XKTC37MKYQ9FW5YF1 (Mission 2A).
**Embedded condition (Gate 0, jrn_01KR2W01CPVT6H48SMFM80XJXC):** Re-derive δ* from
F + (ε_L, ε_DT) using Mission 1A's actual artifacts. Tolerance: |δ*_rederived − 2.232| ≤ 0.01.
**Verdict:** **PASS** (δ* = 2.232 exactly; deviation = 0.0).

---

## 1. Source extraction

From `mission_1a/t1_verify.py`:

| Symbol | Value | Source line |
|---|---|---|
| `EPS_L_RECOMMENDED`  | `0.116` | t1_verify.py:51 (Req2LTL accuracy gap = 1 − 0.884) |
| `EPS_DT_RECOMMENDED` | `1.0`   | t1_verify.py:52 (LIT101-class spec) |
| `C_MATCHER`          | `1.0`   | t1_verify.py:57 (matcher threshold constant) |
| `C_THEOREM`          | `2.0`   | t1_verify.py:58 (theorem threshold constant) |
| `F_CHOICE`           | `"step"` | t1_verify.py:59 (deterministic step) |

From `mission_1a/theorems.tex`:

- T1 statement (line 230): `δ* = c_t (ε_L + ε_DT)` with `c_t = c_m + 1`.
- F definition (lines 226–228): `F = 1` for `δ < δ*`, else `0` (deterministic step).
- Triangle-inequality result (line 259): `|δ̂ − δ| ≤ ε_L + ε_DT`.
- ε_L anchor (lines 140–141): `1 − 0.884 = 0.116` (Req2LTL).

## 2. Analytical re-derivation

The triangle inequality on the matcher's empirical distance gives

```
|δ̂ − δ| ≤ ε_L + ε_DT.
```

The matcher fires when `δ̂ > τ = c_m·(ε_L + ε_DT)`. Guaranteed-detection requires
`δ̂ > τ` for **every** noise realisation, i.e.

```
δ − (ε_L + ε_DT) > τ   ⇔   δ > (c_m + 1)·(ε_L + ε_DT).
```

Setting `c_t = c_m + 1` and computing:

```
δ* = c_t · (ε_L + ε_DT) = 2.0 · (0.116 + 1.0) = 2.0 · 1.116 = 2.232.
```

## 3. Numerical re-derivation

Importing `mission_1a/t1_verify.py` directly and computing
`m.C_THEOREM * (m.EPS_L_RECOMMENDED + m.EPS_DT_RECOMMENDED)` returns `2.232`.

`f_step(δ, ε_L, ε_DT, c_t)` evaluated at three points:

| δ | f_step | expected | result |
|---|---|---|---|
| 2.231 | 1.0 | 1.0 (below threshold, F=1) | ✓ |
| 2.232 | 0.0 | 0.0 (at/above threshold, F=0) | ✓ |
| 2.233 | 0.0 | 0.0 (above threshold, F=0) | ✓ |

The step function lands exactly at δ* = 2.232.

## 4. Tolerance check

| Quantity | Value |
|---|---|
| Expected (Gate 0) | 2.232 |
| Analytical | 2.232 |
| Numerical (module-loaded) | 2.232 |
| Deviation | 0.000 |
| Tolerance | 0.01 |

**Verdict: PASS.** No DECISION checkpoint fires.

## 5. Implications for Mission 2A pipeline

- The matcher tolerance ε in `matcher.py` (Task 8) shall be `ε_DT = 1.0 %-full` per-sample.
- The lifted-claim "deviation budget" before rejection shall be `δ* = 2.232 %-full` cumulative
  (or equivalently τ = 1.116 %-full per-sample max-norm if the matcher uses the per-sample
  test rather than the worst-case theorem threshold).
- ε_L = 0.116 enters Mission 2A only via T2's δ_lift bound, used for the FPR target in Task 11.
