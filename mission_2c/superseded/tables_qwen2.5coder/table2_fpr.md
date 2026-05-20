# Table 2 — FPR × Defense × Benign Corpus (real-Qwen)

All FPR values reported as point estimate + Wilson 95 % CI. Per resolved CLARIFICATION chk_01KR30S1CV263M4ZXQTPJC7T1G and the dec_01KR3K6P6CX26D00RZ131Y6437 reframe, T2 is parametric in δ_lift; the **empirical δ_lift** measured here replaces the earlier 11.6 % target estimate.

| Defense | Benign corpus | n | k (false reject) | FPR | Wilson 95 % CI |
|---|---|---|---|---|---|
| PG-DSL v1 | canonical 14 tools | 14 | 1 | 7.14 % | [1.27 %, 31.47 %] |
| **PG-DSL v1** | **expanded 42-tool corpus** | 42 | 4 | **9.52 %** | **[3.77 %, 22.07 %]** |
| MCPShield | expanded 42-tool corpus | 42 | 17 | 40.48 % | [27.04 %, 55.51 %] |

**Interpretation.** PG-DSL v1's empirical δ_lift is **9.52 %**, below the original 11.6 % target estimate. MCPShield's 40.48 % FPR (CI [27.04 %, 55.51 %]) is roughly 4× PG-DSL's, driven by the LLM-judge brittleness predicted by the Gaming-the-Judge thesis. The high-FPR and W1-hallucination findings are the same root cause expressed two ways.