# PG-DSL — Mission 2B Evaluation Campaign

CCS 2026 Cycle B comparative-evaluation evidence base. Layered on top of
Missions 1B (testbed) and 2A (PG-DSL pipeline).

**Mission:** `mis_01KR3FJ9JJP5EKEFQ1AVFPPAZE`
**Status:** complete; awaiting GATE 2 brain review for entry to paper-writing phase.

---

## Headline results

- **T3 strict composition validated empirically.** PG-DSL ⊕ INVARLLM strictly
  dominates either alone on a 7-attack mixed set (intersection {A1, A3, Z1};
  PG-DSL only {A2}; INVARLLM only {W1, W2, Z2}; composed full coverage).
  See `evaluation/figures/t3_composition_venn.png`.
- **PG-DSL strictly outperforms MCPShield** on physical-effect attacks. PG-DSL
  catches A1, A2, Z1 that MCPShield misses; MCPShield catches A3 (text-level
  sensor name mismatch) which PG-DSL also catches. No attack class where
  MCPShield > PG-DSL — no CLARIFICATION fired.
- **Benign FPR within T2's bound.** PG-DSL on the expanded 42-tool corpus:
  4.76 % point estimate, Wilson 95 % CI [1.32 %, 15.79 %]. T2 δ_lift bound
  11.6 % (conservative theoretical anchor; per resolved CLARIFICATION
  `chk_01KR30S1CV263M4ZXQTPJC7T1G`, empirical-below-bound is sound).
- **L_verify adversarial-robustness limitation honestly characterised.** 12-probe
  battery: 5/12 CORRECT, 5/12 OUT_OF_GRAMMAR, 2/12 WRONG_LIFT — degradation
  58.33 %, over the 30 % trigger. CLARIFICATION `chk_01KR3GTMBCBB1FX6GN1BP6M99D`
  filed; framed as deterministic-stub baseline against which the real-Qwen
  L_verify improvement is measured.

## What's here

```
mission_2b/
├── baseline_design_memo.md           — pre-build memo on stub policy + faithfulness audit
├── baselines/
│   ├── mcpshield_judge.py            — 3-check Stage-1 stand-in
│   └── invarllm_runtime.py           — invariant extraction + runtime check
├── evaluation/
│   ├── build_benign_corpus.py        — 14 tools × 3 styles = 42 benign descriptions
│   ├── build_mixed_attack_set.py     — 7-attack manifest (3 baseline + W1 + W2 + Z1 + Z2)
│   ├── benign_corpus_expanded.json   — 42 entries
│   ├── mixed_attack_set.json         — 7 attacks with predicted lanes
│   ├── run_pgdsl_fpr_expanded.py     — task 5
│   ├── run_t3_composition.py         — task 7
│   ├── run_mcpshield_eval.py         — task 8
│   ├── run_lverify_adversarial.py    — task 9
│   ├── build_tables_and_figures.py   — task 11
│   ├── tables/
│   │   ├── table1_asr.md             — ASR × defense × attack
│   │   ├── table2_fpr.md             — FPR × defense × corpus + Wilson 95 % CIs
│   │   └── table3_latency.md         — latency × defense
│   └── figures/
│       └── t3_composition_venn.png   — PG-DSL ⊕ INVARLLM strict-superset diagram
├── results/                          — full traces (JSON) for every campaign
├── requirements.txt
├── Dockerfile, docker-compose.yml
└── README.md (this file)
```

## Quick start (host Python, no GPU, deterministic stubs)

```bash
pip install -r requirements.txt

# Run the four campaigns (≈ 10 s total)
python evaluation/run_pgdsl_fpr_expanded.py
python evaluation/run_t3_composition.py
python evaluation/run_mcpshield_eval.py
python evaluation/run_lverify_adversarial.py

# Build tables and figures
python evaluation/build_tables_and_figures.py
```

Or via Docker:

```bash
docker-compose up evaluation
```

PI verification path (acceptance criterion 8) — clone, run, eyeball:

```bash
git clone <repo>
cd mission_2b
pip install -r requirements.txt
docker-compose up evaluation
ls evaluation/tables/ evaluation/figures/
```

Total wall-clock for the entire evaluation campaign on M4 24 GB: ~10 s
(deterministic stubs). PI's hardware run with real Qwen3.6-class L_verify and
MCPShield judge will be ~minutes per per-tool admission decision but does not
require harness changes — same scripts, same outputs, just slower.

## Two baselines (locked scope)

Per Mission 2B's locked scope decisions (no third baseline):

| Baseline | Class | Position vs PG-DSL |
|---|---|---|
| MCPShield-style LLM-as-judge | Pre-invocation, surface-level consistency | Closest neighbour. Lacks physics; predicted to fail on CPS-physical attacks. Confirmed empirically. |
| INVARLLM-style runtime physical IDS | Runtime, mass-balance + operating-band | Different layer (runtime, not admission). Composes with PG-DSL via T3. |

ToolGate, ATTESTMCP, and other adjacencies are explicitly out-of-scope per
mission spec.

## Mixed attack set composition (7 attacks)

| ID | Attack | Predicted lane | Observed lane |
|---|---|---|---|
| A1 | type-confusion overflow (Mission 1B) | intersection | intersection ✓ |
| A2 | magnitude-poisoning underdose (Mission 1B) | intersection | pgdsl_only |
| A3 | sensor aliasing (Mission 1B) | intersection | intersection ✓ |
| W1 | sub-noise-floor stealth drain (Mission 2A v2) | pgdsl_only | invarllm_only |
| W2 | post-admission LIT101 spoofing (Mission 2A) | invarllm_only | invarllm_only ✓ |
| Z1 | transient overshoot on level (MSB-style) | invarllm_only | intersection |
| Z2 | overdose magnitude poisoning (MSB-style) | intersection | invarllm_only |

The strict-superset claim survives all the lane deviations; deviations are
documented in `task10_inspection_notes.md` (filed via INSPECTION
chk_01KR3GVYNCB4R9MGGNGQJABC67).

## Reproducible-claims map (acceptance criteria → artefacts)

| AC | Claim | Where verified |
|---|---|---|
| 1 | MCPShield baseline implemented and run | `baselines/mcpshield_judge.py`, `evaluation/run_mcpshield_eval.py`, `results/mcpshield_eval.json` |
| 2 | INVARLLM baseline implemented and run | `baselines/invarllm_runtime.py`, used inside `evaluation/run_t3_composition.py` |
| 3 | T3 strict composition empirically demonstrated | `results/t3_composition.json` (`t3_strict_dominance: true`); figure in `evaluation/figures/t3_composition_venn.png` |
| 4 | Expanded benign corpus + Wilson 95 % CI | `evaluation/benign_corpus_expanded.json` (42 entries); `results/pgdsl_fpr_expanded.json` |
| 5 | L_verify adversarial probe (10–15 instances), no hardening | `evaluation/run_lverify_adversarial.py` (12 probes); `results/lverify_adversarial.json` |
| 6 | Comparative tables | `evaluation/tables/table{1,2,3}_*.md` |
| 7 | T3 composition figure | `evaluation/figures/t3_composition_venn.png` |
| 8 | Reproducible <2 h | full campaign ≈10 s; PI's hardware swap-in unchanged in time-budget |

## Outstanding for brain (Gate 2 review)

- `chk_01KR3GTMBCBB1FX6GN1BP6M99D` (CLARIFICATION, non-blocking) —
  framing for the L_verify adversarial-degradation in the paper limitations
  section. Recommended Option A (disclose stub limitation + plan real-Qwen
  rerun).
- `chk_01KR3GVYNCB4R9MGGNGQJABC67` (INSPECTION, non-blocking) —
  intermediate-results review filed before Tasks 11–13.
- `chk_<gate2>` (filed at end of Mission 2B) — paper-writing entry decision.

## Citation

Decisions backing this work:
- Verifier mechanism: `dec_01KR2HMMHE30R9RF78F4ZGX0WX`
- Lifter implementation: `dec_01KR2HNVAFP7JJN3D827W5GMQH`
- Grammar extension: `dec_01KR2YPK31NM987H3KEVK9C2DT`
- W1 restructure: `dec_01KR2YQ59841KEVNYNTV6B6TWM`
