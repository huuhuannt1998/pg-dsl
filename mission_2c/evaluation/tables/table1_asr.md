# Table 1 — ASR × Defense × Attack (real-Qwen, qwen3:14b)

Detection results on the 7-attack mixed set, real-Qwen (qwen3:14b paper-canonical model) lifter and MCPShield judge. `✓` = detected. `✗` = missed. `n/a` = no admission-time evidence for that defense (W2 is post-admission by design).

| ID | Attack | PG-DSL v1 | MCPShield | INVARLLM | PG-DSL ⊕ INVARLLM | Note |
|---|---|---|---|---|---|---|
| A1 | a_type_confusion_overflow | ✓ | ✓ | ✓ | ✓ |  |
| A2 | b_magnitude_poisoning_underdose | ✓ | ✗ | ✗ | ✓ |  |
| A3 | c_sensor_aliasing_violation | ✓ | ✓ | ✓ | ✓ |  |
| W1 | w1_sub_noise_floor_stealth | ✗ | ✗ | ✓ | ✓ |  |
| W2 | w2_post_admission_spoof | ✗ | n/a | ✓ | ✓ | post-admission attack; no admission-time evidence available to either admission defense. |
| Z1 | z1_transient_overshoot_level | ✓ | ✗ | ✓ | ✓ |  |
| Z2 | z2_magnitude_overdose | ✓ | ✗ | ✓ | ✓ |  |

| Defense | Attacks detected | Coverage |
|---|---|---|
| PG-DSL v1            | 5/7 | 71.4% |
| MCPShield            | 2/6 (excl W2) | 33.3% |
| INVARLLM (real-Qwen) | 6/7 | 85.7% |
| PG-DSL ⊕ INVARLLM    | 7/7 | 100.0% |

**T3 witness map (locked via dec_01KR3N1M8PB5YDXYV7B5DYJQET):**
- A_static \ A_runtime = {A2} ← canonical static-only witness (magnitude poisoning, real CPS attack class)
- A_runtime \ A_static = {W1, W2} ← cross-state stealth + post-admission spoof
- composed = full coverage of the 7-attack mixed set