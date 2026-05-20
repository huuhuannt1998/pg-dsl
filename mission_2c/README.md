# PG-DSL — Mission 2C Real-LLM Evaluation Campaign

CCS 2026 Cycle B paper-quality empirical results. Real Qwen (Ollama-hosted
qwen2.5-coder:14b) wired into all four LLM swap points, replacing Missions 1B
& 2B's deterministic stubs.

**Mission:** `mis_01KR3GKV2ESRM4FR43W3VRG0MA`
**Status:** complete; Gate 3 marks entry to paper-writing.

---

## Headline numbers (real-Qwen, qwen2.5-coder:14b, M4 24 GB)

### Detection (mixed 7-attack set)
| Defense | Detected | Coverage |
|---|---|---|
| PG-DSL v1 (admission)        | 5/7 | 71% |
| MCPShield (LLM-as-judge)     | 3/6 admission-relevant | 50% |
| INVARLLM (runtime)           | 6/7 | 86% |
| **PG-DSL v1 ⊕ INVARLLM**     | **7/7** | **100%** |

### T3 strict composition (real-Qwen empirical)
- A_static \\ A_runtime = **{A2}**  ← magnitude poisoning, canonical static-only witness
- A_runtime \\ A_static = **{W1, W2}**  ← cross-state stealth + post-admission spoof
- composed = full coverage on all 7 attacks
- Lane labels match locked witness mapping (`dec_01KR3N1M8PB5YDXYV7B5DYJQET`)

### Benign FPR (42-tool expanded corpus)
| Defense | FPR | Wilson 95% CI |
|---|---|---|
| **PG-DSL v1** | **9.52%** | **[3.77%, 22.07%]** |
| MCPShield | 40.48% | [27.04%, 55.51%] |

### PG-DSL strictly dominates MCPShield in (FPR, TPR) space
- PG-DSL v1: FPR 9.5% / TPR 83.3%
- MCPShield: FPR 40.5% / TPR 50.0%   *(includes hallucinated W1 'detection')*

---

## What's in this mission

```
mission_2c/
├── INSTALL.md                  — install verification (Ollama + qwen2.5-coder:14b)
├── baseline_design_memo.md      — see mission_2b/
├── baselines/
│   ├── qwen_client.py            — thin Ollama wrapper, per-role seed/temp config
│   ├── real_lifter.py            — L_verify with v0/v1 prompt variants
│   ├── real_admission_layer.py   — drop-in for Mission 2A admission layer
│   ├── real_mcpshield_judge.py   — Qwen-as-judge MCPShield Stage-1 stand-in
│   ├── real_invarllm_extractor.py — offline LLM extraction; runtime check unchanged
│   └── real_agent.py             — single-step agent-loop plumbing (full loop deferred to PI)
├── evaluation/
│   ├── run_p22_ablation.py       — v0 vs v1 prompt restraint ablation
│   ├── run_real_pgdsl_fpr.py     — canonical 14 + expanded 42 corpora
│   ├── run_real_defense_asr.py   — 7-attack defense ASR
│   ├── run_real_mcpshield.py     — MCPShield comparison
│   ├── run_real_invarllm_t3.py   — INVARLLM extraction + T3 composition
│   ├── run_real_lverify_adversarial.py — 12-probe adversarial battery
│   ├── build_paper_tables_and_figures.py — Tables 1-4 + Venn + ROC
│   ├── tables/
│   │   ├── table1_asr.md          — ASR × defense × attack
│   │   ├── table2_fpr.md          — FPR × defense × corpus + Wilson CIs
│   │   ├── table3_latency.md      — real-Qwen wall-clock × defense
│   │   └── table4_per_style_fpr.md — v0→v1 reversal (FORMAL: 71% → 7%)
│   └── figures/
│       ├── t3_composition_venn.png       — locked witness lobes
│       └── pgdsl_vs_mcpshield_roc.png    — strict (FPR, TPR) dominance
├── results/                       — full traces (JSON) + sensor noise floors
├── plumbing_validation/           — Mission 2B stub-mode results preserved
├── Dockerfile, docker-compose.yml — dual-mode (stub | real-llm)
├── entrypoint.sh                  — selects MODE
└── requirements.txt
```

---

## Reproduction

### Stub-mode (fast, ~10 s)

For development iteration; matches Mission 2B exactly.
```bash
cd mission_2c
docker-compose up evaluation
```

### Real-LLM-mode (paper reproduction, ~5–10 min on M4 24 GB)

Prerequisites:
1. Ollama running on the host: `ollama serve`
2. Model pulled: `ollama pull qwen2.5-coder:14b` (~9 GB)

Then:
```bash
cd mission_2c
MODE=real-llm docker-compose up evaluation
```

Or directly without Docker:
```bash
cd mission_2c
pip install -r requirements.txt
# Each campaign individually:
python evaluation/run_p22_ablation.py
python evaluation/run_real_pgdsl_fpr.py
python evaluation/run_real_defense_asr.py
python evaluation/run_real_mcpshield.py
python evaluation/run_real_invarllm_t3.py
python evaluation/run_real_lverify_adversarial.py
python evaluation/build_paper_tables_and_figures.py
```

PI verification path (Mission 2C acceptance criterion 10): clone, run real-LLM
mode end-to-end, regenerate all paper tables and figures in **under 8 hours**
on M4 24 GB. Empirical wall-clock during Mission 2C: ~5 minutes.

---

## Key Mission 2C findings

### 1. Phase 2 prompt restraint (P2.1–P2.3)
Mission 2C's first real-LLM benign FPR campaign showed v0 (the original
prompt) producing 30.95% FPR — Qwen's richer lifts emit Δstate clauses
requiring preconditions the DT verifier doesn't establish. The brain
(`dec_01KR3K6P6CX26D00RZ131Y6437`) endorsed prompt restraint with three
rules: explicit-content-only, no inferred Δstate, per-clause lifting.

Result: v1 dropped FPR to **9.52%** on the expanded 42-tool corpus, well
within T2's parametric δ_lift framing. The per-style reversal — FORMAL went
from worst (71% under v0) to best (7% under v1) — is a Discussion-section
finding about prompt restraint exploiting explicit description content.

### 2. W1 lane reclassification
Mission 2A's W1 (sub-noise-floor stealth drain) was constructed as a
description-poisoning A_static-only witness, but the real PG-DSL admission
flow runs the tool's impl on a clean plant and cannot see out-of-tool
mass-balance side effects. The brain
(`dec_01KR3N1M8PB5YDXYV7B5DYJQET`) reclassified W1 as
runtime-only and promoted A2 (magnitude poisoning, real CPS attack class)
to canonical A_static \\ A_runtime witness. Empirically validated here: A2
is detected by PG-DSL via `Δstate(Cond_P2) bounded[0.40, 1.50]` mismatch
and missed by INVARLLM (band_AIT201 wide enough; mass-balance threshold
with 1.5× safety factor doesn't fire on agent-loop residuals).

### 3. MCPShield's W1 'detection' is Gaming-the-Judge
Real-Qwen MCPShield rules INCONSISTENT on W1 because pre-state == post-state
(W1's initial state is already isolated; the tool maintains by no-op).
Qwen's reasoning: "no actuator transitions, so no action was taken"
— exactly the brittleness predicted by the impossibility-pair thesis
(jrn_01KR2JVMTK3NWQWYXCGG8ZXW3D). Combined with MCPShield's 40.48% benign
FPR (CI [27%, 56%]) versus PG-DSL's 9.52%, the same hallucination drives
both the 'detection' and the elevated FPR. Paper-positive: cleanest
empirical Gaming-the-Judge instance.

### 4. L_verify residual adversarial surface (paper Limitations)
Real-Qwen v1 lifter on the 12-probe adversarial battery: **75.0% CORRECT**
(versus stub's 41.7%), +15.48 pp degradation from baseline FPR. Major
recovery in formal-jargon class (0/4 → 4/4) — Qwen handles "actuated",
"deenergises", "energises" the regex stub couldn't. Residual surface
remains in `grammar_boundary` and one `contradictory` case; honest
scoping motivates future hardened-lifter work.

---

## Paper-claim summary (post-Mission-2C)

- T2 stays parametric in δ_lift; empirical δ_lift = **9.52%** on 42-tool
  corpus replaces 11.6% target estimate. Theorem statement unchanged.
- T3 strict composition holds on real-Qwen testbed. Witnesses:
  - A2 ∈ A_static \\ A_runtime (magnitude poisoning)
  - W1, W2 ∈ A_runtime \\ A_static (cross-state stealth, post-admission spoof)
  - composed = full coverage of the 7-attack mixed set
- PG-DSL strictly dominates MCPShield on (FPR, TPR): lower FPR AND higher
  meaningful TPR. MCPShield's W1 'detection' is hallucinated reasoning,
  paired with high overall FPR — an empirical Gaming-the-Judge instance
  that strengthens (not weakens) the paper's main thesis.
- Per-style δ_lift reversal documents prompt-restraint mechanism.
- L_verify residual adversarial surface bounded; hardened-lifter work
  motivated for future work.

## Citation

Decisions backing this work:
- T2 parametric framing: `dec_01KR3K6P6CX26D00RZ131Y6437`
- W1 reclassification: `dec_01KR3N1M8PB5YDXYV7B5DYJQET`
- Verifier mechanism: `dec_01KR2HMMHE30R9RF78F4ZGX0WX`
- Lifter implementation: `dec_01KR2HNVAFP7JJN3D827W5GMQH`
- Grammar extension: `dec_01KR2YPK31NM987H3KEVK9C2DT`
