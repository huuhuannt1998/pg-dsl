# PG-DSL

**Physics-Grounded Admission Checking for MCP-Controlled CPS Tools**

Companion artifact to the paper accepted at **ACSAC 2026** (Huan Bui and
Chenglong Fu, University of North Carolina at Charlotte).

> **Artifact evaluators start here:** [`ARTIFACT.md`](ARTIFACT.md) — requirements,
> three time-boxed evaluation paths (5 minutes with no models, ~1 hour, full ~9 hours),
> and a claim-to-script-to-JSON mapping for every number in the paper.

This repository contains the full reproducible implementation of
PG-DSL — an admission-time defence that lifts each MCP tool
description into a formal claim over a CPS-grounded grammar, replays
the tool against a digital twin (DT), and admits only those tools
whose claimed effect matches DT-measured behaviour — together with
the SWaT P1+P2 substrate, the LLM-based lifter, the matcher, the
composition-aware DT verifier, every campaign script, every JSON
output that backs a paper claim.

## What's in the paper

PG-DSL verifies a narrower object than full agent verification
(undecidable) or LLM-as-judge verification (manipulable): the bounded
tool implementation under DT replay, subject to the fidelity bounds
of the modeled CPS dynamics. We formalize three conditional
properties under bounded DT fidelity and a restricted CPS-description
grammar:

- **T1ᵥ** — vectorized detection threshold
  `δ*ᵥ = 2‖εL,v + εDT,v‖∞` above which bounded-error detection is
  deterministic.
- **T2** — lifting-soundness decomposition for tool descriptions drawn
  from a restricted CPS-grounded grammar: `δ_lift ≤ δ_cov + δ_gram`.
  Both terms are measured, not assumed — `δ_gram = 0/227` on the
  paraphrase corpus, and `δ_cov` runs `0/42` (qwen3:14b) to `25/42`
  (phi4-mini) across six lifter families.
- **T3** — admission/runtime visibility witness on a canonical 8-attack
  set: admission sees an attack (A₂) no runtime invariant sees; with the
  runtime IDS calibrated on benign traffic spanning the replay grid, W₁
  and W₂ escape both layers (one-directional separation).

### Headline empirical results

On a SWaT P1+P2 substrate with 14 MCP tools:

| Result | Value |
|---|---|
| Per-tool benign FPR | **0/42** rejections (Wilson 95% CI [0, 8.38]%, over 14 tools × 3 init states) |
| Per-style benign FPR | **0.44%** (1/227, Wilson 95% CI [0.08, 2.45]%) on a mistral-generated 227-paraphrase corpus |
| Canonical attacks blocked | **6/8** — five tools withheld at admission (A₁, A₂, A₃, Z₁, Z₂); the Z₃ pair is identified at admission and blocked at invocation |
| Composed coverage (PG-DSL ⊕ INVARLLM, IDS calibrated on grid-spanning benign traffic) | **6/8** — W₁, W₂ outside both layers |
| T2 adversarial probe battery | 28/31 = 90.3% CORRECT across 8 categories (3 read-tool aliasing prompts regraded under R1; the shipped verifier then rejects all three on the returned sensor name) |
| MSB-adapted union (132 instances, 33 per class) | PG-DSL ≥ MCPShield on every class (NC 24/33 vs 3/33) |
| Cross-model / six lifter families | A₂ static-only and W₁, W₂ outside both layers under qwen3:14b and llama3.1:8b; measured δ_cov 0/42 … 25/42 across six lifter families |
| Real-agent end-to-end (N=10 operational-condition sweep) | A₁ 10/10 → 0/10 with defence; W₂ 9/10 unchanged (admission-invisible by design) |
| Boundary characterisation (revision pass) | 134 mutants 70/134 → 94/134 hardened (86 / 110 at the adopted K=30 grid); 18 perturbed twins lose no nominal detection; probe-grid sweep 0/16 at K=3 → 16/16 at K=30 |

Full provenance — every number above traces to a JSON output in
`mission_3b/results/`, `rebuttal_experiments/results/` (revision-pass
experiments, with their pre-registration registers
`rebuttal_experiments/PREREGISTRATION*.md`) and `mission_2c/results/` (M2C baselines)
and to a campaign script under `mission_*/experiments/`,
`mission_2d/scripts/` or `rebuttal_experiments/`. The
claim-to-script-to-JSON mapping is in [`ARTIFACT.md`](ARTIFACT.md); the
paper's LaTeX source is not part of this repository.

## Repository layout

```
mission_1a/grammar/              # Lark grammar for class C
mission_1b/                      # SWaT P1+P2 plant simulator + MCP server
├── plant/                       # mass-balance + linearised chemistry DT
├── mcp_server/                  # real JSON-RPC 2.0 stdio MCP server
└── attacks/                     # canonical poisoned-description definitions

mission_2a/                      # Per-tool DT verifier + matcher + witnesses
mission_2b/evaluation/           # 42-paraphrase benign corpus + initial MCPShield baseline
mission_2c/baselines/            # Real-LLM lifter (qwen3:14b prompt v1 R1–R5),
                                 # MCPShield judge, INVARLLM extractor, qwen_client
mission_2d/                      # Real-agent campaign harness (Python MCP SDK + qwen3:14b)
├── baselines/real_mcp_agent.py  # agent harness
└── scripts/run_campaign.py      # campaign driver

mission_3a/                      # T1ᵥ numerical corroboration on two-tank tractable model
mission_3b/                      # Canonical pipeline (per-tool ⊕ composition admission)
├── admission_layer/             # PGDSLCanonicalLayer + composition verifier
├── attacks/z3_simulator.py      # Z3 composition witness construction
├── data/                        # extended 227-paraphrase corpus, MSB subset
├── experiments/                 # campaign scripts (one per RQ in the paper)
└── results/                     # JSON outputs (one per campaign)

rebuttal_experiments/            # Revision-pass experiments (19 campaigns)
├── PREREGISTRATION*.md          # predictions + scoring rules, fixed before each run
├── e*.py n*.py p*.py r*.py      # one runner per experiment
└── results/                     # 42 JSON outputs
```

## Quick start

### Dependencies

- Python ≥ 3.11
- [Ollama](https://ollama.com) ≥ 0.5, with the following models pulled:
  - `qwen3:14b` (lifter, agent, MCPShield judge, INVARLLM extractor)
  - `mistral:7b` (out-of-family paraphraser for the extended corpus)
  - `llama3.1:8b` (cross-model T3 lifter ablation)
  - `gemma2:9b`, `mistral-nemo:12b`, `granite3.1-dense:8b`, `phi4-mini`
    (six-lifter-family sweep and the held-out benign corpus)
- Python packages: `python3 -m pip install -r requirements.txt`
  (numpy, matplotlib, ollama, mcp ≥ 1.27, lark), pinned to the versions
  the reported results were produced with.

### Reproduce every paper number

Run from the repository root. Wall-clock times are for an Apple M4
24 GB host.

```bash
# RQ1 — Per-tool benign FPR (canonical 14-tool surface)
python3 mission_3b/experiments/run_canonical_benign_fpr_qwen3.py

# RQ1 — Per-style benign FPR on extended 227-paraphrase corpus
python3 mission_3b/data/build_extended_corpus.py            # ~10 min via mistral:7b
python3 mission_3b/experiments/run_canonical_per_style_extended.py  # ~7 min via qwen3:14b

# RQ2 — Canonical defense ASR on the 8-attack set
python3 mission_3b/experiments/run_canonical_defense_asr_qwen3.py

# RQ3 — T3 partition under canonical PG-DSL ⊕ INVARLLM
python3 mission_3b/experiments/run_canonical_t3_partition_qwen3.py

# RQ3 (cross-model) — T3 partition under llama3.1:8b lifter
python3 mission_3b/experiments/run_canonical_pipeline_llama3.py

# RQ4 — T2 adversarial probe battery (31 prompts)
python3 mission_3b/experiments/run_t2_probes_extended.py

# RQ5/RQ6 — MSB-adapted union (132 instances, 33 per class, both defences)
python3 mission_3b/experiments/run_msb_subset_evaluation.py   # hand-written subset
python3 rebuttal_experiments/n4_msb_union.py                  # PG-DSL union
python3 rebuttal_experiments/n4b_mcpshield_union.py           # MCPShield union

# εDT calibration + T1ᵥ sensitivity sweep
python3 mission_3b/experiments/run_dt_calibration.py
python3 mission_3a/t1_v_verify.py --n-trials 1000      # Fig. 1 (script default is 500)

# Revision-pass experiments (mutation battery, probe-grid sweep, perturbed twins,
# six lifter families, held-out corpus, identity probe, static baseline, K=30 re-runs,
# INVARLLM calibration): one runner per experiment, predictions fixed beforehand in
# rebuttal_experiments/PREREGISTRATION*.md; results land in rebuttal_experiments/results/
ls rebuttal_experiments/*.py

# RQ7 — Real-agent N=10 operational-condition sweep (~7.5 h on M4)
python3 mission_2d/scripts/run_campaign.py \
    --attacks A1 A2 W2 A2eng \
    --n-reps 10 --start-rep 1 \
    --out-aggregate mission_3b/results/real_agent_asr_n10.json
```

Campaign outputs land in `mission_3b/results/*.json` and
`rebuttal_experiments/results/*.json`. These JSON outputs are the
canonical record of every paper claim.

### Smoke test

```bash
# Verify Ollama + lifter wiring with one tool
python3 mission_2d/scripts/smoke_test.py
```

## Lifter prompt v1 (R1–R5)

The paper-canonical lifter prompt enforces five restraint rules:

- **R1 (explicit-content-only)** — lift only what the description
  states explicitly; no inferred preconditions or downstream effects.
- **R2 (no-inferred-Δstate)** — emit `Δstate(VAR)` only when `VAR` is
  named verbatim.
- **R3 (per-clause-lifting)** — lift each clause independently;
  no cross-clause synthesis.
- **R4 (single-actuator-per-tool)** — emit at most one
  `actuator(NAME) := value` clause naming the tool's primary
  actuator; co-actuators mentioned as preconditions or downstream
  consequences are not lifted.
- **R5 (parametric-tool-minimal)** — parametric tools emit one
  canonical actuator + one `Δstate` clause; do not enumerate
  alternative pump targets.

R3–R5 were added during the revision pass to close systematic failure
modes (co-actuator inference, multi-pump enumeration) surfaced by the
extended out-of-family paraphrase corpus. The verbatim prompt text
is in [`mission_2c/baselines/real_lifter.py`](mission_2c/baselines/real_lifter.py)
(`GRAMMAR_SPEC_PROMPT_V1`), and the paper Appendix E reproduces them.

## Threat model recap

- **Trusted**: digital twin, formal matcher, lifter prompt (bounded
  semantic error εL on class C), grammar.
- **Untrusted**: MCP tool description (the channel), tool
  implementation (may be poisoned), runtime telemetry (may be
  spoofed).
- **Admission-invisible**: W₁ (sub-noise-floor stealth drift) and W₂
  (post-admission spoof) are outside admission-time visibility by
  construction. T3 formalizes the separation, and it is
  one-directional: admission sees an attack (A₂) no runtime invariant
  sees, while a runtime CPS-IDS calibrated on benign traffic spanning
  our replay grid misses W₁ and W₂ as well — composed coverage is 6/8,
  not 8/8. The residual names what a telemetry-independent check must
  catch. See `rebuttal_experiments/results/r2_invarllm_benign.json`
  and `r3_invarllm_recalibrated.json`.

## Citation

Accepted at ACSAC 42 — the 42nd IEEE Annual Computer Security
Applications Conference, 7–11 December 2026, Los Angeles, CA, USA.
Please cite:

```bibtex
@inproceedings{pgdsl_acsac26,
  title     = {{PG-DSL}: Physics-Grounded Admission Checking for
               {MCP}-Controlled {CPS} Tools},
  author    = {Bui, Huan and Fu, Chenglong},
  booktitle = {Proceedings of the 42nd Annual Computer Security
               Applications Conference (ACSAC)},
  address   = {Los Angeles, CA, USA},
  month     = dec,
  year      = {2026}
}
```

Page numbers and the DOI will be added once the proceedings appear.

## License

MIT — see [`LICENSE`](LICENSE). The paper's LaTeX source is not part of
this artifact repository.

## Acknowledgements

The MSB cross-benchmark adapts attack-class definitions from Zhang
et al., *MCP Security Bench* (ICLR 2026, arXiv:2510.15994, MIT
license); the SWaT testbed model follows MiniCPS (CPS-SPC 2015); the
runtime CPS-IDS composition partner is INVARLLM
(arXiv:2411.10918).
