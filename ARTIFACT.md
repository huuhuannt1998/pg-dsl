# PG-DSL — Artifact Evaluation Guide

Artifact for **PG-DSL: Physics-Grounded Admission Checking for MCP-Controlled CPS Tools**
(ACSAC 2026, paper #151). Huan Bui and Chenglong Fu, University of North Carolina at
Charlotte.

Badges requested: **Available**, **Functional**, **Reproduced**.

This file is the evaluator's entry point. `README.md` describes the system; this file maps
artifact components to paper claims and gives a time-boxed evaluation path.

---

## 1. What the artifact contains

All software, all data, no external services.

| Component | Path | What it is |
|---|---|---|
| Plant + MCP server | `mission_1b/` | SWaT P1+P2 digital twin (mass balance + linearised chemistry) and a real JSON-RPC 2.0 stdio MCP server exposing the 14 canonical tools |
| Claim grammar | `mission_1a/grammar/` | Lark grammar for class C |
| Per-tool admission | `mission_2a/` | Lifter, DT verifier, formal matcher, T3 witness constructions |
| Baselines | `mission_2b/`, `mission_2c/` | MCPShield judge, INVARLLM invariant extractor, real-LLM lifter (prompt v1, rules R1–R5) |
| Real-agent harness | `mission_2d/` | Official Python MCP SDK agent + campaign driver, and all 80 released traces |
| Canonical pipeline | `mission_3b/` | Per-tool ⊕ composition admission, campaign scripts, result JSONs |
| T1ᵥ corroboration | `mission_3a/` | Numerical sweep behind Figure 1 |
| Revision-pass experiments | `rebuttal_experiments/` | The 19 experiments added during review, their **pre-registration registers**, and every result JSON |

**No proprietary components, no sensitive data, no special hardware, no network access at
run time.** Everything runs on a single machine against a local [Ollama](https://ollama.com)
server. Total repository size is about 3 MB.

## 2. Requirements

- Python ≥ 3.11 — `python3 -m pip install -r requirements.txt`
  (numpy, matplotlib, ollama, mcp, lark; exact tested pins in that file)
- [Ollama](https://ollama.com) ≥ 0.5 with models pulled:
  - **`qwen3:14b`** — required (lifter, agent, MCPShield judge, INVARLLM extractor); ~9.3 GB
    on disk, ~10 GB resident at 4096 context
  - optional, only for the cross-family experiments: `mistral:7b`, `llama3.1:8b`,
    `gemma2:9b`, `mistral-nemo:12b`, `granite3.1-dense:8b`, `phi4-mini`
- ~25 GB free disk if all seven models are pulled; ~12 GB for the required one alone
- CPU-only is fine. Reference host: Apple M4, 24 GB RAM, macOS. No GPU required.
- **No network access is needed once models are pulled**, and no API keys.

The deterministic-stub configuration needs **no models at all** — see the 5-minute path
below, which exercises the plant, grammar, matcher and composition pass end to end.

## 3. Suggested evaluation path

Full reproduction is about **9 hours**, dominated by the real-agent sweep (~7.5 h). Three
time-boxed options; each is self-contained.

### (a) Kick the tires — 5 minutes, no models required

```bash
python3 -m pip install -r requirements.txt
python3 mission_2a/admission_layer/pgdsl_admission_layer.py    # 14/14 benign tools admitted
(cd mission_3a && python3 t1_v_verify.py --n-trials 200)      # T1v sweep, scaled down
```

Expected: the admission layer admits all 14 honest tools and prints each lifted claim; the
T1ᵥ sweep reproduces the step shape of Figure 1 at reduced trial count, writing
`mission_3a/results/detection_rate_plot_v.png` and `t1_v_witnesses.json`.

`t1_v_verify.py` resolves its `--out-plot` / `--out-witness` defaults relative to the
working directory, which is why the command above `cd`s first; run from the repository root
it would drop a stray `results/` there instead.

### (b) Core claims — about 1 hour, `qwen3:14b` only

```bash
python3 mission_3b/experiments/run_canonical_benign_fpr_qwen3.py    # 0/42        (Table 2)
python3 mission_3b/experiments/run_canonical_defense_asr_qwen3.py   # 6/8         (Table 3)
python3 mission_3b/experiments/run_canonical_t3_partition_qwen3.py  # T3 lanes    (Table 4)
python3 mission_3b/experiments/run_t2_probes_extended.py            # 28/31       (§5.7)
python3 rebuttal_experiments/e11_mutation.py                        # 70/134      (Table 8)
python3 rebuttal_experiments/n5b_coverage_curve.py                  # K sweep     (Table 11)
```

This covers the paper's headline numbers and the two boundary results reviewers cared most
about. Outputs land in `mission_3b/results/` and `rebuttal_experiments/results/`.

### (c) Everything — about 9 hours

Run every command in `README.md` §"Reproduce every paper number", then every runner in
`rebuttal_experiments/*.py`. The real-agent sweep alone is ~7.5 h; it can be shortened with
`--n-reps 2` at the cost of the reported confidence intervals.

## 4. Mapping from artifact to paper claims

Every number in the paper traces to a JSON file. `rebuttal_experiments/verify_ver2.py`
encodes 62 of these as executable assertions (it is author-only — it needs the LaTeX source,
which is not part of this artifact, and exits cleanly with an explanation on a fresh clone).

| Paper claim | Where in paper | Script | Result JSON |
|---|---|---|---|
| 0/42 benign tool-state rejections | Table 2 | `mission_3b/experiments/run_canonical_benign_fpr_qwen3.py` | `mission_3b/results/benign_fpr_canonical_qwen3.json` |
| 1/227 benign paraphrase rejections | Table 2, §4.2 | `run_canonical_per_style_extended.py` | `mission_3b/results/per_style_canonical_extended_qwen3.json` |
| 0/70 held-out, 70/70 entity | §5.2 | `rebuttal_experiments/e1_heldout.py` | `results/e1_heldout_fpr.json` |
| 6 of 8 canonical attacks blocked | Table 3 | `run_canonical_defense_asr_qwen3.py` | `mission_3b/results/defense_asr_canonical_qwen3.json` |
| T3 partition; W1, W2 outside both layers | Table 4, §4.6 | `run_canonical_t3_partition_qwen3.py`, then `rebuttal_experiments/r3_invarllm_recalibrated.py` | `mission_3b/results/t3_partition_canonical.json`, `results/r3_invarllm_recalibrated.json` |
| IDS fires on 42/42 honest traces (why 8/8 was withdrawn) | §5.4 | `rebuttal_experiments/r2_invarllm_benign.py` | `results/r2_invarllm_benign.json` |
| 28/31 adversarial probes | §5.7 | `run_t2_probes_extended.py` | `mission_3b/results/t2_probes_extended_qwen3.json` |
| Identity probe 30/30, shipped 24/30 | §5.8 | `rebuttal_experiments/e2_identity.py` | `results/e2_identity_binding.json` |
| Six lifter families, δ_cov 0/42 … 25/42 | Table 10 | `rebuttal_experiments/e8c_crossmodel_fullpipe.py`, `e8d_deltacov.py` | `results/e8c_crossmodel_fullpipe.json`, `results/e8d_deltacov.json` |
| 134 mutants, 70/134 → 94/134 | Table 8 | `e11_mutation.py`, `n2_closed_world.py`, `n3_command_log.py` | `results/e11_mutation_coverage.json`, `results/n2_closed_world.json`, `results/n3_command_log.json` |
| Probe grid 0/16 → 16/16; 42 % at K=100 | Table 11 | `n5_coverage_curve.py`, `n5b_coverage_curve.py` | `results/n5_coverage_curve.json`, `results/n5b_coverage_curve.json` |
| K=30 headline re-run (86/134, 110/134, 0/420) | Table 8, §5.10 | `rebuttal_experiments/r1_k30_headline.py`, `r1b_k30_qwen3.py` | `results/r1_k30_headline.json`, `results/r1b_k30_qwen3.json` |
| 18-twin perturbation; 144 + 756 verdicts | §5.11 | `n1_perturbed_twin.py`, `n1d_canonical8.py`, `n1e_benign42.py`, `n1f_z3_margin.py` | `results/n1*.json` |
| Static-analysis baseline, 1/14 FP | §5.12 | `e4_proganalysis.py` | `results/e4_static_only.json` |
| Adaptive attacker (1.01 / 0.99; rate 0.3 → 0.599) | Table 12 | `p3_threshold_aware.py` | `results/p3_threshold_aware.json` |
| Composition cost 0.026 ms; pre-filter loses 14/15 | §4.4 | `e7_scale.py`, `n7b_prefilter_variants.py` | `results/e7_scale.json`, `results/n7b_prefilter_variants.json` |
| MSB union 24/33 and its 8 + 25 split | Tables 5, 9 | `run_msb_subset_evaluation.py`, `n4_msb_union.py`, `n4b_mcpshield_union.py` | `mission_3b/results/msb_subset_evaluation.json`, `results/n4_msb_union.json`, `results/n4b_mcpshield_union.json` |
| Second substrate SWaT P3 (1/8, 3/3, 7 of 8) | §5.13 | `p4_second_substrate.py` | `results/p4_second_substrate.json` |
| Real-agent sweep, A1 10/10 → 0/10 | Table 7 | `mission_2d/scripts/run_campaign.py` | `mission_3b/results/real_agent_asr_n10.json` + 80 traces in `mission_2d/agent_traces/` |

## 5. Expected variation

The plant, matcher, grammar and composition pass are **deterministic**: those numbers should
reproduce exactly. Anything routed through an LLM can vary:

- The lifter runs at temperature 0 with a fixed seed and `think=False`, and was
  bit-stable across our runs, but Ollama version or quantisation changes can shift a lift.
  The failure mode is visible, not silent: a changed lift shows up as a changed admission
  verdict, and `δ_cov` is exactly the rate at which lifts go wrong.
- The real-agent campaign samples operating conditions per rep rather than decoding
  randomness (§5.14); reps are per-condition, not i.i.d.
- Wall-clock times assume the reference host.

**Pre-registration.** Predictions and scoring rules were fixed before each campaign ran:
50 in total, 14 falsified, all reported. The registers are in
`rebuttal_experiments/PREREGISTRATION.md`, `PREREGISTRATION_N.md` and `PREREGISTRATION_R.md`.
Falsified predictions are recorded there rather than removed, so an evaluator can check that
what we predicted is what we reported.

## 6. Known limitations of the artifact

- One substrate (SWaT P1+P2, plus a P3 stage). No second CPS domain.
- Attacks and MSB-adapted instances are author-constructed; the paper says so.
- Two scripts (`verify_ver2.py`, `verify_rebuttal.py`) cross-check the manuscript text
  against the JSONs. The LaTeX source is not part of this artifact, so they exit cleanly
  with an explanation rather than running.
- `mission_1b/.claw/` holds one smoke-test transcript from a superseded agent harness. The
  campaign in the paper uses the official Python MCP SDK (`mission_2d/`).

## 7. Public release

The artifact is already public at **https://github.com/huuhuannt1998/pg-dsl** under the MIT
licence. On acceptance of the evaluation we will deposit the evaluated commit in a permanent
archive with a DOI (Zenodo) and cite it in the camera-ready.

## 8. Contact

Huan Bui — hbui11@charlotte.edu. At least one author will be reachable through HotCRP for
the whole evaluation period.
