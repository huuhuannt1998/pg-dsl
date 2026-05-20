# PG-DSL

**Physics-Grounded Description Lifting for Admission-Time Defence of
LLM-Controlled Industrial Cyber-Physical Systems**

Companion artifact to the ACSAC 2026 submission of the same title.

This repository contains the full reproducible implementation of
PG-DSL — an admission-time defence that lifts each MCP tool
description into a formal claim over a CPS-grounded grammar, replays
the tool against a digital twin (DT), and admits only those tools
whose claimed effect matches DT-measured behaviour — together with
the SWaT P1+P2 substrate, the LLM-based lifter, the matcher, the
composition-aware DT verifier, every campaign script, every JSON
output that backs a paper claim, and the LaTeX source of the paper.

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
- **T2** — lifting-soundness decomposition for tool descriptions
  drawn from a restricted CPS-grounded grammar; empirically
  `δ_lift = 0.44%` on a 227-paraphrase out-of-family corpus.
- **T3** — strict-composition witness on a canonical 8-attack set,
  showing admission-time and runtime defences cover complementary
  visibility surfaces.

### Headline empirical results

On a SWaT P1+P2 substrate with 14 MCP tools:

| Result | Value |
|---|---|
| Per-tool benign FPR | **0/42** rejections (Wilson 95% CI [0, 8.38]%, over 14 tools × 3 init states) |
| Per-style benign FPR | **0.44%** (1/227, Wilson 95% CI [0.08, 2.45]%) on a mistral-generated 227-paraphrase corpus |
| Canonical attacks blocked at admission | **6/8** (A₁, A₂, A₃, Z₁, Z₂, Z₃) |
| Composed coverage (PG-DSL ⊕ INVARLLM) | **8/8** |
| T2 adversarial probe battery | 25/31 = 80.6% CORRECT across 8 categories |
| MSB cross-benchmark (32 instances, 4 classes) | PG-DSL ≥ MCPShield on every class |
| Cross-model T3 validation | Locked partition {A₂, W₁, W₂} invariant across qwen3:14b and llama3.1:8b |
| Real-agent end-to-end (N=10 operational-condition sweep) | A₁ 10/10 → 0/10 with defence; W₂ 9/10 unchanged (T3 runtime-only by design) |

Full provenance — every number above traces to a JSON output and a
campaign script — is in [`paper/PROVENANCE.md`](paper/PROVENANCE.md).

## Repository layout

```
paper/                           # LaTeX source + compiled PDF + PROVENANCE
├── main.tex                     # 11pp body + refs + 6 appendices
├── sections/                    # per-section .tex
├── refs.bib                     # bibliography (all citations de-anonymized)
├── PROVENANCE.md                # paper-claim → JSON / source-file map
└── scripts/backfill_macros.py   # JSON → \newcommand backfill driver

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
```

## Quick start

### Dependencies

- Python ≥ 3.11
- [Ollama](https://ollama.com) ≥ 0.5, with the following models pulled:
  - `qwen3:14b` (lifter, agent, MCPShield judge, INVARLLM extractor)
  - `mistral:7b` (out-of-family paraphraser for the extended corpus)
  - `llama3.1:8b` (cross-model T3 lifter ablation)
- Python packages: `ollama`, `mcp` (≥ 1.27), `lark`, plus stdlib;
  the artifact pins versions in `requirements.txt` (per-mission).

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

# RQ5/RQ6 — MSB-adapted cross-benchmark (32 instances, 4 classes)
python3 mission_3b/experiments/run_msb_subset_evaluation.py

# εDT calibration + T1ᵥ sensitivity sweep
python3 mission_3b/experiments/run_dt_calibration.py

# RQ7 — Real-agent N=10 operational-condition sweep (~7.5 h on M4)
python3 mission_2d/scripts/run_campaign.py \
    --attacks A1 A2 W2 A2eng \
    --n-reps 10 --start-rep 1 \
    --out-aggregate mission_3b/results/real_agent_asr_n10.json
```

All campaign outputs land in `mission_3b/results/*.json`. Then:

```bash
python3 paper/scripts/backfill_macros.py
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

builds `paper/main.pdf` with every empirical number filled from the
JSON outputs.

### Reproduce the paper PDF only

```bash
cd paper
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

The current `paper/main.tex` ships with macro values backfilled from
the JSON outputs already in `mission_3b/results/`, so it compiles
without re-running any campaign.

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
- **Complementary**: a runtime CPS-IDS (INVARLLM here) catches
  runtime-only attacks (W₁ sub-noise-floor stealth, W₂ post-admission
  spoof) outside admission-time visibility by construction; T3
  formalizes the composition.

## Citation

When the paper is published, please cite:

```bibtex
@inproceedings{pgdsl_acsac26,
  title     = {{PG-DSL}: Physics-Grounded Description Lifting for
               Admission-Time Defence of {LLM}-Controlled Industrial
               Cyber-Physical Systems},
  author    = {[Anonymous Submission, ACSAC 2026]},
  booktitle = {ACSAC},
  year      = {2026}
}
```

## License

Code: MIT. Paper LaTeX source: CC BY-NC-SA 4.0. See `LICENSE`.

## Acknowledgements

The MSB cross-benchmark adapts attack-class definitions from Zhang
et al., *MCP Security Bench* (ICLR 2026, arXiv:2510.15994, MIT
license); the SWaT testbed model follows MiniCPS (CPS-SPC 2015); the
runtime CPS-IDS composition partner is INVARLLM
(arXiv:2411.10918).
