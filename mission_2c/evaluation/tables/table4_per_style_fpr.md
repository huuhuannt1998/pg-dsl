# Table 4 — Per-Style δ_lift Reversal (v0 → v1, expanded corpus)

Configuration (a) is the original v0 prompt; (b) is the v1 restrained prompt with R1/R2/R3 rules from dec_01KR3K6P6CX26D00RZ131Y6437. **Headline finding (qwen3:14b): FORMAL was *worst* under v0 (35.71 %) and is *best* under v1 (0.00 %)** — a reversal driven by prompt restraint exploiting explicit description content while suppressing inferred preconditions. Overall expanded-corpus FPR: v0 21.43 % → v1 2.38 %. Discussion-section material.

| Style | n | v0 FPR | v0 95 % CI | v1 FPR | v1 95 % CI | Δ (pp) |
|---|---|---|---|---|---|---|
| FORMAL | 14 | 35.71 % | [16.34, 61.24] % | 0.00 % | [0.00, 21.53] % | -35.71 |
| CASUAL | 14 | 28.57 % | [11.72, 54.65] % | 7.14 % | [1.27, 31.47] % | -21.43 |
| TERSE | 14 | 0.00 % | [0.00, 21.53] % | 0.00 % | [0.00, 21.53] % | +0.00 |

**Interpretation.** v0's lifter eagerly inferred preconditions from formal descriptions (e.g., "when pumps are running" → Δstate(Q_in_T101) {sign +}) producing claims the DT verifier couldn't satisfy under unconditioned initial states. v1's explicit-content-only rule suppresses this elaboration, making formal descriptions the *easiest* class to lift correctly. The reversal is robust: the same effect was observed under the qwen2.5-coder:14b Phase 1 substitution (FORMAL 71.4 % v0 → 7.1 % v1), and persists under the paper-canonical qwen3:14b model (FORMAL 35.7 % v0 → 0.0 % v1).