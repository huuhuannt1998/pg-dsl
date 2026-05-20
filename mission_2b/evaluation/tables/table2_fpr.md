# Table 2 — FPR × Defense × Corpus

All FPR values are reported as point estimate + Wilson 95 % CI. T2 δ_lift theoretical bound is 11.6 % (conservative, derived from Req2LTL accuracy gap; per resolved CLARIFICATION chk_01KR30S1CV263M4ZXQTPJC7T1G this is not a target — empirical-below is sound).

| Defense | Corpus | n | k | FPR | Wilson 95 % CI |
|---|---|---|---|---|---|
| PG-DSL | original corpus | 140 | 0 | 0.00% | [0.00%, 2.67%] |
| PG-DSL | expanded corpus | 42 | 2 | 4.76% | [1.32%, 15.79%] |
| PG-DSL | adversarial probe | 12 | 7 | 58.33% | [31.95%, 80.67%] |
| MCPShield | expanded corpus | 42 | 2 | 4.76% | [1.32%, 15.79%] |

**Notes.**
- INVARLLM is a runtime invariant-checker, not a per-description admission filter. Its FPR is measured per benign-trajectory; reported in Table 1 (it fires zero benign violations on Mission 1B benign baseline traces).
- The PG-DSL adversarial-probe FPR-equivalent (58.33%) is the deterministic-stub baseline; real-Qwen L_verify is expected to recover most formal-jargon and grammar-boundary cases. See `results/lverify_adversarial.json` and clarification chk_01KR3GTMBCBB1FX6GN1BP6M99D.