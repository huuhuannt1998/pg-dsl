# Table 1 — ASR × Defense × Attack

Each cell shows whether the named defense detected (`✓`) or missed (`✗`) the attack.

| ID | Attack | MCPShield | INVARLLM | PG-DSL | PG-DSL ⊕ INVARLLM |
|---|---|---|---|---|---|
| A1 | a_type_confusion_overflow | ✗ | ✓ | ✓ | ✓ |
| A2 | b_magnitude_poisoning_underdose | ✗ | ✗ | ✓ | ✓ |
| A3 | c_sensor_aliasing_violation | ✓ | ✓ | ✓ | ✓ |
| W1 | w1_sub_noise_floor_stealth | ✗ | ✓ | ✗ | ✓ |
| W2 | w2_post_admission_spoof | ✗ | ✓ | ✗ | ✓ |
| Z1 | z1_transient_overshoot_level | ✗ | ✓ | ✓ | ✓ |
| Z2 | z2_magnitude_overdose | ✗ | ✓ | ✗ | ✓ |

| Defense | Attacks detected | Coverage |
|---|---|---|
| MCPShield | 1/7 | 14.3% |
| INVARLLM | 6/7 | 85.7% |
| PG-DSL | 4/7 | 57.1% |
| PG-DSL ⊕ INVARLLM | 7/7 | 100.0% |