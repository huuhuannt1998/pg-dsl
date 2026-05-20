# ACSAC 2026 — CFP Verification (Phase 0 deliverable)

**Mission:** mis_01KR43PJT245AQMERYB2NYZK1M.
**Source URL:** https://www.acsac.org/2026/submissions/papers/ (fetched 2026-05-08).
**Sources also consulted:** https://www.acsac.org/2026/submissions/, sec-deadlines.github.io, wikicfp.com/cfp/program?id=45.

---

## Material differences vs mission assumptions

| # | Mission assumption | CFP reality | Material? |
|---|---|---|---|
| 1 | Deadline early-to-mid June 2026 | **May 26, 2026 (23:59 AoE), firm** | YES — 18 days from today (2026-05-08); deadline is sooner than assumed |
| 2 | acmart conference template, ~12 pages body + appendices | **IEEEtran v1.8b, `\documentclass[conference,compsoc]{IEEEtran}`, US letter, double-column. 11 body pages + 5 appendix pages, 16 total max.** | YES — different template class entirely; affects every section's LaTeX |
| 3 | Double-blind | **Confirmed double-blind.** Authors anonymous in PDF; cite own prior work in third person. | NO — matches assumption |

→ **Phase 0 BLOCKING DECISION trigger fires** per mission spec ("BLOCKING DECISION if ACSAC CFP details materially differ from brain's assumptions"). Filing immediately; no Phase 2/3 setup until brain ratifies the IEEEtran template + 11-body-page envelope.

## Verbatim CFP requirements

### Submission deadline
- Papers: **May 26, 2026 (23:59 AoE) — firm**.
- Today (2026-05-08) → **18 days runway.**

### Page limits
- Main body: ≤ **11** double-column pages, excluding well-marked references.
- Appendices: ≤ **5** pages.
- Total document: ≤ **16** pages.
- Note from CFP: "PC members are not required to read the appendices."

### Template
- LaTeX: **IEEEtran.cls v1.8b**, `\documentclass[conference,compsoc]{IEEEtran}`.
- Paper size: **US letter** (not A4).
- "Modifying margins, line spacing, or font size is not allowed."

### Double-blind
- PDF must be anonymized (no author names, affiliations).
- Authors may cite prior work but in **third person**.

### Artifact evaluation
- Optional URL to artifact repo at submission time (must also be anonymous).
- Formal artifact evaluation expected post-acceptance.

### Conflicts of interest
- Specify COIs with PC members at submission. Six categories defined.

### Other required sections (conditional)
- **LLM Usage Statement** — required separately if LLMs were used in research/writing. Not counted toward page limit.
- **Ethical Considerations** — required if paper raises ethical concerns; must address procedures and responsible disclosure.

### Important dates (post-deadline)
- Early Rejection Notification: July 13
- Authors Response Period: August 18 – 25
- Acceptance Notification: September 8
- Minor Revision Period: September 8 – October 8
- Camera Ready: October 22
- Conference: December 7 – 11, 2026, Los Angeles, CA

## Implications for the paper

1. **Switch template.** All planned acmart structure must reanchor to IEEEtran. Different sectioning conventions (no `\maketitle{}` ACM-style; uses `\IEEEauthorblockN{}`/`\IEEEauthorblockA{}` even in anonymized form). Reference style switches from `acmart` to `IEEEtran`-compatible (`IEEEtranN.bst` or similar).

2. **Tighten body to 11 pages.** Mission's planned section list (Abstract, Intro, Related Work, Threat Model, Theoretical Framework, Methodology, Evaluation, Discussion, Conclusion) must fit in 11 double-column IEEE pages. With T1/T2/T3 statements + sketches + ROC + Venn + 4 tables, this is feasible but tight. Targeted budget per section in the post-resolution plan.

3. **Use the appendix slot.** Up to 5 pages of appendices for: full theorem proofs, the Lark grammar listing, the 14-tool MCP surface, the 42-tool benign corpus, additional adversarial probe traces, the Mission 1B → 2C → (2D placeholder) raw-data references. PC may skip but reviewers can verify.

4. **Anonymization.** Strip references to "PI" / "executor" / specific names from any retained design memos cited in the paper. RKA decisions are project-internal; cite results, not the org chart.

5. **Mission 2D placeholder.** Real-agent ASR section will use a `% [PI: insert from Mission 2D when produced]` block — this is honest given Mission 2D is on PI hardware and not yet delivered. The placeholder must be structurally complete so the fill-in doesn't re-flow surrounding pages.

6. **18-day runway.** Tight but achievable with focused execution. Phase 1 read (≤ 1 day) + Phase 3 drafting (≤ 8 days) + Phase 4 compile/polish (≤ 2 days) + INSPECTION + revisions (≤ 4 days) leaves 3 days slack.

7. **LLM Usage Statement.** This entire project used LLMs heavily (Qwen3:14b for L_verify, MCPShield judge, INVARLLM extractor, plus deterministic-stub agents). The statement must be honest about scope.

8. **Artifact-evaluation readiness.** mission_2c/results/ + mission_2c/superseded/ + Dockerfile + entrypoint + INSTALL.md are already structured for artifact evaluation. The submission repo URL would point at a sanitized GitHub repo when ready.

## Phase 0 verdict

CFP retrieved successfully; assumptions 1 and 2 are materially different from mission spec. Filing BLOCKING DECISION via `rka_submit_checkpoint`. No code/prose work proceeds until brain ratifies the IEEEtran-and-11-pages plan or supplies an alternate template/budget.
