# Table 4 — Per-Style δ_lift Reversal (v0 → v1, expanded corpus)

Configuration (a) is the original v0 prompt; (b) is the v1 restrained prompt with R1/R2/R3 rules from dec_01KR3K6P6CX26D00RZ131Y6437. The headline finding: FORMAL was *worst* (71.4 %) under v0 and is *best* (7.1 %) under v1 — a reversal driven by prompt restraint exploiting explicit description content while suppressing inferred preconditions. Discussion-section material.

| Style | n | v0 FPR | v0 95 % CI | v1 FPR | v1 95 % CI | Δ (pp) |
|---|---|---|---|---|---|---|
| FORMAL | 14 | 57.14 % | [0.00, 0.00] % | 7.14 % | [1.27, 31.47] % | -50.00 |
| CASUAL | 14 | 28.57 % | [0.00, 0.00] % | 14.29 % | [4.01, 39.94] % | -14.29 |
| TERSE | 14 | 7.14 % | [0.00, 0.00] % | 7.14 % | [1.27, 31.47] % | +0.00 |

**Interpretation.** v0's lifter eagerly inferred preconditions from formal descriptions (e.g., 'when pumps are running' → Δstate(Q_in_T101) {sign +}) producing claims the DT verifier couldn't satisfy under unconditioned initial states. v1's explicit-content-only rule suppresses this elaboration, making formal descriptions the *easiest* class to lift correctly. Casual descriptions retain ambiguity not eliminated by restraint, hence v1's 14.29 % > 7.14 %.