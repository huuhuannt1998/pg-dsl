# Table 2 — FPR × Defense × Benign Corpus (real-Qwen)

All FPR values reported as point estimate + Wilson 95 % CI. Per resolved CLARIFICATION chk_01KR30S1CV263M4ZXQTPJC7T1G and the dec_01KR3K6P6CX26D00RZ131Y6437 reframe, T2 is parametric in δ_lift; the **empirical δ_lift** measured here replaces the earlier 11.6 % target estimate.

| Defense | Benign corpus | n | k (false reject) | FPR | Wilson 95 % CI |
|---|---|---|---|---|---|
| PG-DSL v1 | canonical 14 tools | 14 | 0 | 0.00 % | [0.00 %, 21.53 %] |
| **PG-DSL v1** | **expanded 42-tool corpus** | 42 | 1 | **2.38 %** | **[0.42 %, 12.32 %]** |
| MCPShield | expanded 42-tool corpus | 42 | 1 | 2.38 % | [0.42 %, 12.32 %] |

**Interpretation.** PG-DSL v1's empirical δ_lift is **2.38 %**, below the original 11.6 % target estimate. MCPShield's 2.38 % FPR (CI [0.42 %, 12.32 %]) under qwen3:14b is comparable to PG-DSL's at this corpus size; on qwen2.5-coder:14b (Phase 1, superseded) MCPShield's FPR was 40.48 % vs PG-DSL's 9.52 %. The TPR side of the trade is what differentiates them: MCPShield catches 33.3 % of admission-relevant attacks vs PG-DSL's 83.3 %, dominated by physics-grounded verification on parametric (A2, Z2) and transient (Z1) attacks where surface-level LLM-judge consistency can't rule against.