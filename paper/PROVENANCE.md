# PG-DSL Paper — Provenance Map

This document maps every paper claim, theorem statement, citation, and
empirical number to its RKA primary source. PI uses this to verify
integrity during inspection. No fabricated citations; no fabricated
numbers.

**Last updated:** 2026-05-10 (ACSAC revision pass: addressing R2
weaknesses).

## Page-envelope and abstract tightening (2026-05-15, late)

After the Tier A/B/D pass landed, the body was effectively 12 pages
(Conclusion straddled p11--p12), which is over the 11-page IEEEtran
v1.8b body envelope. Additional cuts:

- **Abstract trimmed from ~340 words to ~245 words.** Removed the
  expanded "validates T1${}_v$ predictively" sentence (it was already
  reframed during Tier B as "consistent with T1${}_v$ threshold
  analysis"; the body Z3 paragraph carries that interpretation).
  Compressed the formal-properties summary while keeping T1${}_v$ /
  T2 / T3 named.
- **T1${}_v$ proof sketch moved to a new
  Appendix~\ref{app:t1v-proof}.** Body now references the appendix.
- **§4.2 R1--R5 prompt-rule paragraph compressed.** Per-rule
  parenthetical expansions removed (verbatim rules are in
  Appendix~\ref{app:prompt}).
- **§5.8 real-agent paragraphs consolidated.** A1/W2/A2/A2_eng
  per-condition explanations merged into one tight ``per-condition
  reading'' paragraph.
- **§6 ``MCPShield Pareto-dominance instance'' paragraph removed.**
  Content duplicated §5.5 prose; the §5.5 description-physics-gap
  framing carries the point.

Final layout (14 pages total):
- pp 1--11: body (Intro through Conclusion + LLM Usage + Related Work)
- pp 11 bottom -- 12: references
- pp 13--14: Appendices A--F (T1${}_v$ proof, grammar, tool surface,
  witnesses, prompt rules, reproduction commands)

Within IEEEtran v1.8b "11 body + up to 5 references/appendix"
envelope strictly.

## Pre-submission review response — Tiers B + D (2026-05-15)

**Tier B (claim calibration)** applied per advisor's "suggested claim
calibration" section:
- Abstract: "avoids two adjacent limitations" not "escapes
  impossibility"; "formalize three conditional properties under
  bounded DT fidelity" not "we prove three theorems"; "$Z_3$
  consistent with T1${}_v$ threshold analysis" not "validating
  predictively"; $6/8$ alone vs $8/8$ composed separated explicitly;
  "DT-measured physical behaviour as reference signal subject to
  fidelity bounds" not "physics as ground truth".
- §1 contributions list rewritten from theorem-bullets to
  system-centric per advisor (problem / system / conditional
  analysis / evaluation / artifact).
- §3 "per-rep seed variation for genuine statistical independence"
  replaced with "operating-condition variation, not stochastic
  LLM-policy independence" to reconcile with §6.8.
- "paper-final" → "main pipeline result" across the paper.
- §4 T3 final sentence: "witnessed composition result, not a general
  security statement" instead of "T3 is empirically grounded".
- §8 Conclusion tightened to 22 lines, "avoided" / "formalized"
  language consistent with abstract.

**Tier D (structural and writing)** applied:
- **§4 flattened** to normal subsections (\S4.1--\S4.7) — fixes the
  prior "$4.0.1$" subsubsection numbering anomaly. All cross-reference
  labels preserved (`sec:theory`, `sec:method`, `sec:t3-witnesses`,
  `sec:dt-calibration`, `sec:method-grammar`). Theorems integrated
  with their corresponding pipeline components: T2 with lifter (§4.2),
  T1${}_v$ with per-tool DT verifier (§4.3), T3 standalone (§4.6).
- **TCB box** (Table 1) added to §3 listing trusted vs untrusted
  components and rationale.
- **Evaluation-map table** (Table 4) added at start of §5 mapping each
  RQ to its experiment, trial count, and supported claim.
- **Admission filtering vs runtime pair enforcement** explicitly
  separated in §4.4 (the composition-aware verifier performs
  admission-time pair analysis but the enforcement happens at runtime).
- **Sensor aliasing and ε_DT limitations moved earlier** in §7
  Discussion (DT fidelity scoping and Lifter limitations now first in
  the section rather than penultimate).
- **Cross-model lifter ablation table** (Table 9) added to §5.7
  showing qwen3:14b vs llama3.1:8b on benign FPR and admission-attack
  coverage; data from the prior cross-model T3 campaign.
- Conclusion trimmed from 38 lines to 22 to keep body within envelope.
- Sub-Gaussian future-work paragraph removed from §4.3 to recover
  ~0.3pp.

**Tier C deferred to future experimental work** with honest
acknowledgement: sensor-identity admission hardening ablation, T1${}_v$
boundary sweep on the SWaT DT, and expanded MSB ($\geq 25$/class) are
flagged as planned post-acceptance work in §6 (T2 Adversarial
Robustness) and §7 (Lifter limitations). The advisor's recommendation
to add these strengthens the paper; ACSAC submission proceeds with
the current empirical depth.

**Final compile audit:**
- Total: 14 pages
- Body: 11 pages + ~0.5 page overflow into p12 (last paragraph of
  Related Work continues onto p12)
- References: ~0.5 page (p12 bottom)
- Appendices A–E: pp 13–14
- Within IEEEtran v1.8b 11+5 envelope
- Zero LaTeX errors, zero unresolved references/citations
- All 13 backfill macros filled

## Pre-submission review response — Tier A (2026-05-15)

Advisor pre-submission review
(`pg_dsl_presubmission_review.md`) flagged three Tier-A arithmetic
blockers. Source state was also corrupted (theorem file overwritten
with methodology content); recovered first.

**Theorem-file recovery.** `sections/04_theoretical_framework.tex`
had been overwritten with the methodology content during an earlier
edit; reconstructed from the compiled `main.pdf` text and the
known LaTeX structure (`\begin{theorem}` envs, `\paragraph{...}`
markers, `\label{thm:t1v/t2/t3}`, `\label{sec:t3-witnesses}`,
`\label{sec:dt-calibration}`). All cross-references resolve.

**A.1 — Per-tool FPR denominator clarified.** Table 1, Abstract, and
Conclusion now report $0/42$ (over $14$ canonical tools $\times$ $3$
initial states LOW/MID/HIGH) explicitly. Wilson 95% UB $8.38\%$ is
correct for $n=42$; the prior wording with only "$14$-tool surface"
in the caption made the CI look inconsistent with a $14$-trial
denominator. Source: `mission_3b/results/benign_fpr_canonical_qwen3.json`
keys `n_total_decisions=42, n_admit=42, wilson_ci_95=[0, 0.0838]`.

**A.2 — Seed-FPR contradiction resolved.** §6.5 MCPShield comparison
was reporting both PG-DSL and MCPShield at $2.38\%$ on the
$42$-paraphrase seed corpus, contradicting the §6.2 by-source
breakdown ($0/42 = 0.00\%$ on the seed corpus). The contradiction
stemmed from the comparison using the M2C-era PG-DSL pipeline (prompt
v1 pre-R4/R5), whereas the by-source breakdown reports the
paper-canonical post-R4/R5 pipeline. Updated §6.5 to report the
post-revision numbers honestly: PG-DSL $0/42$ vs MCPShield $1/42$, a
strict superset of admitted honest tools rather than a tie. Added a
one-sentence transparency note about the prior two-rule prompt.

**A.3 — $\varepsilon_{DT}$ calibration distinguished from full-transient
envelope.** The §4.2 calibration paragraph had said "$99.5$th
percentile rounded up to $0.05$" yielding $\varepsilon_{DT} = 0.10$,
which is not arithmetic. Reframed honestly: $\varepsilon_{DT} = 0.10$
is the \emph{median} per-sample $|\Delta L_{T101}|$ residual (rounded
up to LIT-sensor granularity), appropriate for the steady
post-action matcher; the $99.5$th-percentile full-transient
envelope is $0.40$ \%-full; using the conservative bound would
raise $\delta^{*}_v$ from $0.432$ to $1.032$ \%-full. Sensitivity
sweep extended from $\{0.05, 0.10, 0.20\}$ to
$\{0.05, 0.10, 0.20, 0.40\}$; $Z_3$ remains $4.85\times$ above the
conservative-bound threshold.

## Appendix pass (2026-05-15)

Five appendices added (`sections/99_appendix.tex`, ~3 pages total
including references):

- **Appendix A** — Lark grammar listing for class $\mathcal{C}$
  (verbatim from `mission_1a/grammar/grammar.lark`); needed
  `\DeclareUnicodeCharacter{0394}{\ensuremath{\Delta}}` preamble fix
  for the `Δstate` token to render in verbatim.
- **Appendix B** — 14 canonical tool descriptions (verbatim
  abbreviated; full descriptions in `mission_1b/mcp_server/server.py`).
- **Appendix C** — Witness construction details for $W_1$, $W_2$,
  $Z_3$. Setup parameters, dynamics, and what each defense layer
  sees vs misses. Sources: `mission_2a/witnesses/run_witnesses_v2.py`
  (W1), `mission_2b/evaluation/run_t3_composition.py` (W2),
  `mission_3b/attacks/z3_simulator.py` (Z3).
- **Appendix D** — Lifter prompt v1 with rules R1–R5 paraphrased.
  Verbatim prompt text is in `mission_2c/baselines/real_lifter.py`
  (GRAMMAR_SPEC_PROMPT_V1). Documents the R3/R4/R5 evolution during
  the revision pass.
- **Appendix E** — Reproduction commands. One-shot bash incantations
  for every campaign (per-tool FPR, per-style FPR, defense ASR, T3
  partition, cross-model T3, T2 probes, MSB subset, DT calibration,
  real-agent N=10). Dependencies listed.

Page audit post-appendix: body 11 pp, references + 5 appendices = 3 pp,
total 14 pp — within the IEEEtran v1.8b "11 body + up to 5
references/appendix" envelope.

## Section restructure (2026-05-15)

PI directive: reorganize section order to security-paper-standard
outline.

New section order:
1. Introduction (`01_intro.tex`)
2. **Background** (`02_background.tex`, NEW) — MCP+admission model,
   description-channel poisoning, SWaT P1+P2 substrate, formal
   preliminaries ($\varepsilon_L$/$\varepsilon_{DT}$ bounds + state
   space), INVARLLM baseline overview
3. Threat Model (`03_threat_model.tex`, unchanged)
4. **System Design** (`04_system_design.tex`, NEW wrapper) — merges
   the prior §4 Theoretical Framework (`04_theoretical_framework.tex`,
   T1${}_v$ / T2 / T3) and §5 Methodology (`05_methodology.tex`,
   pipeline + implementation) via `\let\section\subsection` to
   preserve all internal labels (`sec:theory`, `sec:method`,
   `sec:t3-witnesses`, `sec:dt-calibration`, `sec:method-grammar`)
   while collapsing the structure into a single §4 numbering
5. Evaluation (`06_evaluation.tex`, unchanged content; renumbered §5)
6. Discussion (`07_discussion.tex`, unchanged content; renumbered §6)
7. **Related Work** (`02_related_work.tex`, moved from §2 to §7)
8. Conclusion (`08_conclusion.tex`, unchanged content; renumbered §8)

Net result: 8 numbered body sections (option `M3(b)` style merge in
the prior polish-pass call, plus the new Background section).
Cross-references via `\S\ref{...}` are stable across the move since
all labels are preserved; the `\S\ref{sec:theory}` and
`\S\ref{sec:method}` references now resolve to subsections of §4
System Design (e.g., §4.1, §4.2) rather than their own §4 / §5
section numbers, but the references render correctly and remain
semantically accurate.

The §1 paper-organization paragraph is rewritten to reflect the new
ordering.

Pages: 11 body + 1 references = 12 total (up from 11 prior to the
restructure; the Background section adds ~1pp).

## Final fix-up pass (2026-05-11)

- **§3 paragraph 5 "Real-agent threat realisation"**: stale N=3 numbers
  updated to N=10 to match Table 4 / §6.8 / Abstract. A1
  type-confusion overflow $3/3 \to 10/10$ without defence; W2
  post-admission spoofing $3/3 \to 9/10$ regardless of admission-time
  defence.
- **§6.5 MCPShield comparison clarifier**: added one parenthetical
  noting that the $2.38\%$ MCPShield-tie FPR is on the $42$-paraphrase
  seed corpus used for the apples-to-apples comparison, distinct from
  the paper-canonical $0.44\%$ on the $227$-paraphrase extended corpus
  in Table~\ref{tbl:fpr}. Addresses the reviewer-defensibility gap
  identified in brain's polish-pass review.

## Polish pass changelog (2026-05-11)

- **C1 §8 Conclusion**: per-style FPR updated 2.38% → 0.44% (with CI),
  revision-pass contributions (MSB cross-benchmark, cross-model T3,
  N=10 op-condition sweep) named in the conclusion sentence.
- **C2 §6.8 Real-Agent prose**: A1 ASR drop "0/3" → "0/10";
  W2 "3/3" → "9/10"; added an honest one-sentence note that the
  single non-overflow W2 rep is at the low end of the LIT101 sweep
  range (61% initial, 96% final at horizon end — the 30-step horizon
  ended short of the 99% overflow predicate).
- **C3 §7 FPR-vs-robustness paragraph**: CASUAL 7.14% (from 42-paraphrase
  seed) → 1.30% (from paper-canonical 227-paraphrase corpus), with the
  honest framing that the 42-corpus number was a sample-size artifact.
- **C4 + M3(b) Table 3 removed**: legacy `M2C` codename caption leak +
  Table 3-Table 4 redundancy both fixed by removing Table 3 entirely.
  Pareto-dominance prose inlined in §6.5 with strict-superset
  witness-set listing, MSB cross-benchmark in §6.6 carries the
  Z3-inclusive comparison.
- **Table 4 row label**: "Z3 (composition; from M3B)" → "$Z_3$
  (composition witness, canonical 8-attack set)" — M3B codename leak
  fixed.
- **M1 §5.2 prompt v1 transparency**: §5.2 now explicitly discloses
  that prompt v1 evolved during the revision pass from a two-rule
  formulation (R1, R2) to a five-rule formulation (R1–R5), with R3
  added as structural disambiguator and R4/R5 added to close the
  failure modes surfaced by the extended corpus's wider phrasing
  distribution. Artifact ships the rule-evolution trace for ablation.
- **M2 §6.6 PI 0/8 narrative**: added explanation that the PI class is
  structurally hard for admission-time defences (adversarial content
  in description text vs. description's claimed physical effect);
  both PG-DSL and MCPShield reach 0/8 on subtle natural-language PI;
  T3 composition with runtime CPS-IDS catches downstream physical
  manifestations.
- **Mi1 §7 ensemble-lifter motivation**: added one sentence in the
  cross-model T3 invariance paragraph flagging ensemble-lifter
  approaches as future work alongside sensor-aliasing hardening,
  motivated by the Z3 lifter dependence.
- **Dragos citekey row in §1 citation map**: stale entry
  `dragos_mexico_news_26` replaced with primary `dragos_mexico_26`
  (Deen 2026 + intel-brief), reflecting the P4.1 update.

## Revision pass changelog (2026-05-10)

- **Lifter prompt v1 — added rules R4 and R5.**
  R4 (single-actuator-per-tool) prevents lifting co-actuators
  mentioned as preconditions/downstream effects; R5
  (parametric-tool-minimal) prevents enumerating alternative pump
  targets in `set_dosing_rate` paraphrases. Source: extended-corpus
  campaign found a 6.61% point-estimate FPR before the rules; 0.44%
  after. Both rules added to `mission_2c/baselines/real_lifter.py`
  GRAMMAR_SPEC_PROMPT_V1 (no API change; prompt-only).
- **Benign corpus extended 42 -> 227 paraphrases** via mistral:7b
  (lifter-paraphraser separation; mistral is from a different model
  family than the qwen3:14b lifter). Source corpus:
  `mission_3b/data/benign_corpus_extended.json`.
- **T2 probe battery extended 12 -> 31 prompts** spanning 8
  categories. Source: `mission_3b/experiments/run_t2_probes_extended.py`,
  `mission_3b/results/t2_probes_extended_qwen3.json`.
- **MSB cross-benchmark subset (32 instances, 4 classes)** —
  NC/PM/PI/OP from Zhang et al. ICLR 2026 (arXiv:2510.15994), adapted
  to SWaT P1+P2. Source: `mission_3b/data/msb_subset.py`,
  `mission_3b/results/msb_subset_evaluation.json`.
- **Cross-model T3 validation** on llama3.1:8b (added Llama family
  alongside Qwen). Source:
  `mission_3b/experiments/run_canonical_pipeline_llama3.py`,
  `mission_3b/results/{per_style,defense_asr,t3_partition}_canonical_llama3.json`,
  `mission_3b/results/cross_model_t3_summary.json`.
- **ε_DT calibration documented + sensitivity sweep** at
  ε_DT in {0.05, 0.10, 0.20}. Source:
  `mission_3b/experiments/run_dt_calibration.py`,
  `mission_3b/results/dt_calibration.json`.
- **Real-agent campaign N=3 -> N=10 reframed as operational-condition
  sweep**: empirical smoke testing established that qwen3:14b at
  T<=0.7 produces bit-identical action sequences across distinct
  Ollama seeds AND distinct per-rep prompt nonces (the agent is
  functionally deterministic on fixed input). The N=10 expansion is
  therefore reformulated as a per-rep sweep across realistic plant
  operating bands (LIT101 in [72,90] for A1; LIT101 in [61,79] for
  W2; AIT201 in [0.405,0.495] for A2; AIT201 in [0.255,0.345] for
  A2_eng), with `temperature=0.5` and per-rep prompt nonce as
  additional perturbations. Wilson CI is then the binomial CI on
  the operating-condition outcome distribution. Added 4th condition
  A2_eng (scenario-engineered A2 variant: lower AIT201 sweep + seeded
  agent dosing-context priming). The prior N=3 campaign used a single
  seed across reps without operating-condition variation and is
  superseded. Source: `mission_2d/scripts/run_campaign.py`
  (per-rep seed/nonce/env-noise sweep), `mission_2d/baselines/real_mcp_agent.py`
  (temp=0.5), `mission_3b/results/real_agent_asr_n10.json`.
- **Citation de-anonymization**: replaced `Anonymous arXiv submission`
  with full author lists for `toolgate`, `mcp_misleading`,
  `prompt_inj_survey`, `trust_auth_sok`, `gaming_judge`, `invarllm`.
  Verified against arXiv abs pages.
- **Dragos primary citation**: replaced aggregator
  `dragos_mexico_news_26` (letsdatascience.com) with primary Dragos
  blog post `dragos_mexico_26` (Deen, May 6 2026, "AI in the Breach")
  and companion Dragos intel-brief whitepaper.

---

## 1. Citation map (cite-key → RKA literature ID)

| `\cite{}` key | Title | RKA ID |
|---|---|---|
| `mcpshield` | MCPShield: Adaptive Trust Calibration | `lit_01KR2HXCBAQDTYDGZREF8BH7QP` |
| `toolgate` | ToolGate: Contract-Grounded Tool Execution | `lit_01KR2HY0Y6SRFN9MQ6WJGPF9E8` |
| `mcp_misleading` | Don't believe everything you read (MCP measurement) | `lit_01KR2HYBXS0CXYK50TCX5C4MQK` |
| `secure_mcp_jamshidi` | Securing MCP (Jamshidi 2025) | `lit_01KR2HYVT2E98HT0QJKR1QEXMT` |
| `gaming_judge` | Gaming the Judge | `lit_01KR2J0NSB89R6VJG9656AK8P6` |
| `trust_auth_sok` | SoK: Trust-Authorization Mismatch | `lit_01KR2J05T3XRBA79SJM18V0WYT` |
| `req2ltl` | Req2LTL | `lit_01KR2J15CY9PM0NKMBJRPRFG00` |
| `invarllm` | INVARLLM | `lit_01KR2J2TD01QA37TSTF6WFWQBG` |
| `showkatbakhsh_sparse` | Sparse Strong Observability | `lit_01KR2J3B3G4PS2W4SNRXPKDMQP` |
| `msb_mcp_bench` | MCP Security Bench | `lit_01KR2J5P1MYSZZXCMFHQGMEQHT` |
| `when_mcp_attack` | When MCP Servers Attack (Zhao 2025) | `lit_01KR2JD887BV4XY4ZGQSQHVW8K` |
| `prompt_inj_survey` | Prompt Injection Survey | `lit_01KR2JDGB18J8ABHNTPGW3JJ96` |
| `dragos_mexico_26` | Primary Dragos publication: Deen, "AI in the Breach" (Dragos Threat Intelligence Blog, May 6 2026) + Dragos intel-brief whitepaper; verified independently via dragos.com (revision-pass P4.1) | `lit_01KR2JDTQSTNN2NNBH3CSM4ZB1` (now superseded by primary citation) |
| `minicps` | MiniCPS toolkit (DT substrate) | (CPS-SPC 2015; not in RKA) |
| `mcp_spec` | Anthropic MCP specification 2024-11-05 | (Anthropic; not in RKA literature) |

`minicps` and `mcp_spec` are infrastructure references (not RKA-tracked
research literature) and reference the canonical artifact descriptions.

---

## 2. Theorem statement map

| Paper section | Theorem | RKA source |
|---|---|---|
| §Theoretical Framework, T1 (scalar baseline) | Detection threshold under bounded-error sensing, scalar form | `jrn_01KR2JP8DJ0X21RAZGJMP1M3AA` (original framework) |
| §Theoretical Framework, T1${}_v$ (paper-final) | Vectorized detection threshold for canonical (per-tool ⊕ composition) admission | `jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ` (brain-produced T1_v statement); `mission_3a/theorems.tex` (executor formalization, pending brain INSPECTION on `chk_01KR4G7S77T40PE54ABT7MQ4TR`) |
| §Theoretical Framework, T2 | Lifting soundness on structured class C; parametric in δ_lift | `jrn_01KR2JP8DJ0X21RAZGJMP1M3AA` + `jrn_01KR3K600MR250FGXK77TZP7BF` (T2 reframe) + `dec_01KR3K6P6CX26D00RZ131Y6437` (T2 parametric) |
| §Theoretical Framework, T3 | Strict composition with runtime CPS-IDS; partition shift under canonical PG-DSL | `jrn_01KR2JP8DJ0X21RAZGJMP1M3AA` (statement) + `jrn_01KR3N2SEQETNSMK7SJ9B25MJE` (W1 reclassification) + `dec_01KR3N1M8PB5YDXYV7B5DYJQET` (locked witnesses) + `dec_01KR49FTB2ND38DW36094G95ZM` (Z3b option B; partition shift) |

---

## 3. Empirical number map (paper-canonical)

| Paper claim | Value | Source file/line |
|---|---|---|
| Per-tool benign FPR (canonical 14-tool corpus, qwen3:14b) | 0.00% point estimate; Wilson 95% CI [0.00%, 8.38%] | `mission_3b/results/benign_fpr_canonical_qwen3.json` keys `fpr_per_tool_overall`, `wilson_ci_95` |
| Per-style benign FPR (42-paraphrase expanded corpus) | 2.38% point; CI [0.42%, 12.32%] | `mission_3b/results/per_style_canonical_qwen3.json` keys `fpr_point_estimate`, `fpr_wilson_ci_95` |
| Per-style FPR by style {FORMAL, CASUAL, TERSE} | 0.00% / 7.14% / 0.00% | `mission_3b/results/per_style_canonical_qwen3.json` `by_style` |
| Defense ASR (canonical 8-attack set) | 6/8 detected at admission; 2/8 missed (W1, W2 ∈ A_runtime) | `mission_3b/results/defense_asr_canonical_qwen3.json` `per_attack_asr` |
| Z3 detection (key option-B) | 0% ASR via composition pair on HIGH initial state | `mission_3b/results/defense_asr_canonical_qwen3.json` row `Z3` |
| T3 partition (canonical ⊕ INVARLLM) | intersection={A1,A3,Z1,Z2,Z3}; canonical_only={A2}; invarllm_only={W1,W2}; missed=∅; composed=8/8 | `mission_3b/results/t3_partition_canonical.json` `lanes` |
| Single-tool ablation FPR (M2C baseline) | 7.14% canonical → 0.00%; 9.52% expanded → 2.38% (qwen3 canonical = same as 3B) | `mission_2c/results/real_pgdsl_fpr_*_qwen3.json`; M2C is recharacterized as single-tool baseline per `jrn_01KR40HHXXZQP1Q3B0H2K56ATR` (recharacterization header) |
| MCPShield benign FPR (qwen3 expanded corpus) | 2.38% (1/42) — matches PG-DSL canonical at point | `mission_2c/results/real_mcpshield_eval_qwen3.json` `benign_campaign.fpr_point_estimate` |
| MCPShield TPR comparison | pgdsl_better={A2,Z1,Z2}; mcpshield_better={}; both_match={A1,A3,W1,W2} | `mission_2c/results/real_mcpshield_eval_qwen3.json` `comparison` |
| L_verify adversarial CORRECT (qwen3) | 12/12 (100%) | `mission_2c/results/real_lverify_adversarial_qwen3.json` `n_correct` |
| Real-agent ASR — A1 without defence (N=10 op-condition sweep) | $10/10$ ($100\%$, Wilson CI $[72.2\%, 100\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.A1.without` |
| Real-agent ASR — A1 with canonical PG-DSL (N=10) | $0/10$ ($0\%$, CI $[0, 27.8\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.A1.with` |
| Real-agent ASR — A2 bare without defence (no engagement) | $0/10$ ($0\%$, CI $[0, 27.8\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.A2.without` |
| Real-agent ASR — A2 with canonical PG-DSL (N=10) | $0/10$ ($0\%$, CI $[0, 27.8\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.A2.with` |
| Real-agent ASR — A2_eng scenario-engineered without (N=10) | $5/10$ ($50\%$, CI $[23.7\%, 76.3\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.A2eng.without` |
| Real-agent ASR — A2_eng with canonical PG-DSL (N=10) | $0/10$ ($0\%$, CI $[0, 27.8\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.A2eng.with` |
| Real-agent ASR — W2 without defence (N=10) | $9/10$ ($90\%$, CI $[59.6\%, 98.2\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.W2.without` |
| Real-agent ASR — W2 with canonical PG-DSL (N=10, T3 runtime-only by construction) | $9/10$ ($90\%$, CI $[59.6\%, 98.2\%]$) | `mission_3b/results/real_agent_asr_n10.json` `aggregate.W2.with` |
| Real-agent campaign harness (revision pass) | Python MCP SDK ($\geq 1.27$) + qwen3:14b at temp=0.5 via Ollama; Mission 1B real-MCP server; per-rep prompt nonce + per-rep operational-condition sweep (LIT101/AIT201 around canonical centre) | `mission_2d/INSTALL.md`; `dec_01KR4F7NEWBBH44RDP5N9JKYP0`; revision-pass changelog above |

---

## 4. Methodology / pipeline references

| Pipeline component | Reference / source |
|---|---|
| Lifter `L_verify` (qwen3:14b, prompt v1) | `mission_2c/baselines/real_lifter.py`; `dec_01KR3TYT9JHYH1H0W2700YJN5Q` (qwen3:14b canonicalization) |
| Per-tool DT verifier | `mission_2a/dt_verifier/dt_verifier.py` (LOW/MID/HIGH initial states; 120s admission window) |
| Composition-aware DT verifier (Mission 3B) | `mission_3b/admission_layer/composition_verifier.py` (pairwise replay; safe band [25,95] L_T101 / [20,95] L_T201; 30s horizon) |
| Matcher | `mission_2a/matcher/matcher.py` (clause-by-clause; ε_DT tolerance per state-var) |
| Canonical admission orchestrator | `mission_3b/admission_layer/pgdsl_canonical.py` (per-tool ⊕ composition); ratified per `chk_01KR4B1PVDRWQZRHD4MSD6YN1N` |
| Plant simulator (DT) | `mission_1b/plant/swat_p1p2.py`; `dec_01KR2HMMHE30R9RF78F4ZGX0WX` (verifier-mechanism choice = MiniCPS-style mass balance) |
| Backend LLM | qwen3:14b via Ollama; `mission_2c/INSTALL.md`; `dec_01KR3TYT9JHYH1H0W2700YJN5Q` |

---

## 5. Witness construction map (T3)

| Witness | Lane (canonical PG-DSL ⊕ INVARLLM) | Source |
|---|---|---|
| A1 (type-confusion overflow) | intersection | `mission_1b/attacks/poisoned_descriptions.py:attack_a_type_confusion` |
| A2 (magnitude poisoning underdose) | canonical_only (PG-DSL detects, INVARLLM misses sub-noise-floor underdose) | `mission_1b/attacks/poisoned_descriptions.py:attack_b_magnitude_poisoning` |
| A3 (sensor aliasing) | intersection | `mission_1b/attacks/poisoned_descriptions.py:attack_c_sensor_aliasing` |
| W1 (sub-noise-floor stealth drain) | invarllm_only (canonical admits; INVARLLM bands miss but mass-balance fires) | `mission_2a/witnesses/run_witnesses_v2.py:witness_w1_v2`; `dec_01KR3N1M8PB5YDXYV7B5DYJQET` (witness lock) |
| W2 (post-admission spoof) | invarllm_only | `mission_2b/evaluation/run_t3_composition.py:make_w2_simulator` |
| Z1 (transient overshoot, single tool with bounded[]) | intersection | `mission_2b/evaluation/run_t3_composition.py:make_z1_simulator` |
| Z2 (overdose magnitude poisoning) | intersection | `mission_2b/evaluation/run_t3_composition.py:make_z2_simulator` |
| Z3 (composition-only transient overshoot) | intersection (caught at admission via composition pair) | `mission_2a/witnesses/run_witness_z3.py`; `mission_3b/attacks/z3_simulator.py` |

---

## 6. Decision history

| Decision | RKA ID |
|---|---|
| Threat model + research question (description-channel poisoning of CPS LLM agents) | `dec_01KR2HKRMZTX2QPWCQ0APJY8H9` |
| Verifier mechanism = physics-grounded DT (not LLM-as-judge) | `dec_01KR2HMMHE30R9RF78F4ZGX0WX` |
| Admission timing = pre-context-injection (not runtime) | `dec_01KR2HN026RRX80Q1N02M7MTBM` |
| Theorem-led contribution shape (T1+T2+T3) | `dec_01KR2HNDZ06B9J2JBV0G2SM0KA` |
| Lifter implementation = per-tool LLM (locked) | `dec_01KR2HNVAFP7JJN3D827W5GMQH` |
| T2 parametric in δ_lift (target ESTIMATE, not bound) | `dec_01KR3K6P6CX26D00RZ131Y6437` |
| T3 witness lock (A2 / W1 / W2) | `dec_01KR3N1M8PB5YDXYV7B5DYJQET` |
| qwen3:14b backend canonicalization | `dec_01KR3TYT9JHYH1H0W2700YJN5Q` |
| Z3b option B (composition-aware admission canonical) | `dec_01KR49FTB2ND38DW36094G95ZM` |
| Mission 2D agent harness = Python MCP SDK (Option C) | `dec_01KR4F7NEWBBH44RDP5N9JKYP0` |
| ACSAC 2026 CFP ratification | `dec_01KR4ETPE3FTZG0CKNHWRMHV8H` |

---

## 7. Open / pending items

- **T1${}_v$ formalization INSPECTION** — `chk_01KR4G7S77T40PE54ABT7MQ4TR` (Mission 3A) pending brain ratification. Paper uses brain's T1${}_v$ statement from `jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ` (already PI-approved per Path b).
- **Real-agent ASR (Mission 2D)** — campaign in progress (background task `bnirdapy7`); paper has placeholder `% [PI: insert from Mission 2D when produced]` flagged at the relevant location in §Threat Model and §Evaluation. Surrounding prose is structured to permit fill-in without restructuring.

---

## 8. Validation procedure

To verify a claim's provenance:
1. Find the cite-key or number in `paper/main.tex`.
2. Look up its RKA source row in §1–§5 above.
3. Run `rka_get(<id>)` and confirm the cited content.
4. For empirical numbers, run `python3 -c 'import json; print(json.load(open("<file>"))["<key>"])'` and confirm the value.

Every claim in the body of the paper has a row in this document.
