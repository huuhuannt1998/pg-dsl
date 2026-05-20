# Sensor Noise-Floor Estimation (Mission 1B Benign Baseline)

**Mission:** mis_01KR2W2P9XKTC37MKYQ9FW5YF1 (Mission 2A).
**Source:** brain unblock directive jrn_01KR2YSJ6M28TPJA93RVT52W99, action 1.
**Decision authorising:** dec_01KR2YQ59841KEVNYNTV6B6TWM (W1 restructure to 120s + sub-noise-floor witness).
**Output consumer:** task 5 W1 v2 INVARLLM stand-in calibration (`witnesses/run_witnesses_v2.py`).

---

## 1. Per-sample sensor statistics (10 benign reps × 1801 samples each)

| Sensor | n | min | max | mean | stdev |
|---|---|---|---|---|---|
| LIT101 | 18 010 | 46.0000 | 82.0000 | 68.0011 | 8.244689 |
| LIT201 | 18 010 | 60.0000 | 100.0000 | 95.5469 | 9.953534 |
| FIT101 | 18 010 |  0.0000 |   0.5000 |  0.3998 | 0.200172 |
| FIT201 | 18 010 |  0.0000 |   0.4000 |  0.3998 | 0.009423 |

The `stdev` numbers above describe the *operating-range excursion* of each sensor as
the agent cycles its actuators to maintain setpoints. They are NOT the per-sample
sensor noise — Mission 1B's plant simulator is fully deterministic (no per-sample
noise model). Use them only for sanity (operating bands).

## 2. INVARLLM-style mass-balance residual (the metric the runtime IDS actually checks)

We compute, for each sample step k of every benign trajectory:

```
residual[k] = | (LIT101[k] − LIT101[k−1]) − expected_dL_from_actuators[k−1] |
```

with `expected_dL = q_in·n_pumps_on·1[MV101=open] − q_out·1[MV201=open]`,
`q_in = 0.5 %-full/s`, `q_out = 0.4 %-full/s`.

| Statistic | Value |
|---|---|
| max benign |residual| | **0.500000 %-full / sample** |
| mean benign |residual| | 0.003278 %-full / sample |
| stdev benign |residual| | 0.040075 %-full / sample |
| p99 benign |residual| | 0.000000 %-full / sample |

**Interpretation.** 99 % of benign samples have residual ≡ 0 (deterministic plant,
mass balance closes exactly). The 0.5 %-full max is a one-step *actuator-transition
lag artifact*: at the step where the agent commands `MV101: closed → open` and
`P101: off → on`, the next-step inflow is `+0.5 %-full/s` while the
`expected_dL_from_actuators[k−1]` evaluation used the previous-step (off, closed)
state. A real INVARLLM trained on real benign data would either smooth across
transitions or set its threshold above this transient.

## 3. Calibration choice for Task 5 W1 v2 INVARLLM stand-in

We pick a per-sample residual threshold that:
- is **above** the steady-state benign residual (≥ 0.05 — comfortably above the
  empirical p99 of 0 with margin for plausible real-sensor noise);
- is **below** the worst-case transient (≤ 0.1 < 0.5 — keeps the bar meaningful
  rather than trivially loose).

**Calibrated threshold:** `INVARLLM_SAMPLE_FLOOR = 0.10 %-full / sample`.

This is the value the W1 v2 witness must come in below to demonstrate runtime-IDS
miss. With this floor:

- Realistic real-world reading: a 1 Hz LIT101 sensor with 0.10 %-full per-sample
  noise floor is consistent with published iTrust sensor specs.
- Sensitivity: an attack drain at 0.10 %-full/s sits exactly at the floor; PG-DSL
  catches anything above 0.0186 %-full/s (= δ*/120s = 2.232/120). The defender's
  separation regime (PG-DSL fires AND INVARLLM misses) is therefore the rate band
  `(0.0186, 0.10) %-full/s` over the 120 s admission window.

## 4. W1 v2 parameter pick

```
admission window T  = 120 s              (per dec_01KR2YQ59841KEVNYNTV6B6TWM)
drain rate         = 0.025 %-full / s    (sub-noise-floor: 0.025 ≪ 0.10)
cumulative drift δ = 0.025 × 120         = 3.0  %-full
PG-DSL margin       = δ − δ*              = 3.0 − 2.232 = 0.768 %-full
INVARLLM headroom   = floor − rate        = 0.10 − 0.025 = 0.075 %-full / sample
```

Both inequalities (`δ > δ*` and `rate < INVARLLM_SAMPLE_FLOOR`) hold by comfortable
margins. Re-validation in the next sub-task.

## 5. Notes for Mission 2B (when it arrives)

- A real-Qwen run of the testbed on PI hardware will introduce floating-point
  noise from quantised inference. That doesn't affect the LIT/FIT noise floor
  (which is plant-side). It may affect `ε_L` measured during the lifter benchmark
  (Task 11 monitoring point).
- A real iTrust SWaT calibration of INVARLLM would replace the `0.10` constant
  here with a per-sensor threshold derived from the real benign trace. The
  stand-in number is for the deterministic testbed only.
