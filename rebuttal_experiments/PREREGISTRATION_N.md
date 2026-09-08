# N-series prediction register (N1–N6)

## Provenance — stated plainly

These twenty-two predictions were authored in the advisor experiment plan
`PG-DSL rebuttal experiment plan.pdf`, **before any N-series run**. The evidence:

| artifact | timestamp |
|---|---|
| advisor plan PDF (contains N1.1–N5.4 with reasoning) | 2026-08-22 01:03:46 |
| earliest N-series result JSON (`n3_command_log.json`) | 2026-08-22 01:09:23 |
| latest N-series result JSON (`n1b_attack_stability.json`) | 2026-08-22 01:18:00 |

**This file was added to the repository after those runs**, transcribing the plan. It is
not itself evidence of pre-commitment; the PDF and the timestamps above are. The plan's
Section 7 gate ("commit this register to the artifact repo, Fri 21 Aug evening") was
**not met** — the register existed only as the PDF. Recording that here rather than
back-dating it.

The original seventeen predictions (P2.x, P11.x, P6.x, P4.x) *were* git-committed before
their runs, in `PREREGISTRATION.md` at commit `baa92d3` (2026-08-20 23:43:38).

## N1 — Perturbed-twin verdict stability

- **N1.1** Benign: 0/42 verdict flips on every single-axis twin. → **CONFIRMED** (0 flips, 756 cells)
- **N1.2** A1, A2, A3, Z2, Z3 detected on every twin including corners. → **FALSIFIED on Z2**, which is detected on no twin including nominal (published ASR 1.0)
- **N1.3** Z1 is the first and likely only attack to flip; missed at 0.8 flow and the slow corner. → **FALSIFIED** (Z1 detected on all 18)
- **N1.4** Z2 does not flip. → **CONFIRMED**
- **N1.5** T1v holds empirically: zero counterexamples where ‖δv‖∞ > 2(0.116 + ε_DT^emp) and the attack is missed; report (‖δv‖∞, δ*_v) per attack. → **CONFIRMED** (0 counterexamples; Z3 witness measured per twin in `n1f_z3_margin.json`)
- **N1.6** Drift: 0/42 per-tool flips at every drift level. → **CONFIRMED**

## N2 — Closed-world matcher

- **N2.1** Benign 0/42 and 0/227 CW-A rejections; P3 tools 0/8. → **CONFIRMED** (all three)
- **N2.2** Extra-side-effect ≥ 20/22. → **CONFIRMED** (20/22)
- **N2.3** State-conditional: 0 to 4/16 become visible. → **CONFIRMED** (0/16)
- **N2.4** Canonical attacks unchanged; W1/W2 remain runtime-only. → **CONFIRMED**
- **N2.5** A2 headline 70 → 90–92/134; residual exactly {state-conditional, time-delayed}. → **FALSIFIED in part**: 90/134 with CW-A ✓, but 2 M8 and 6 M5 also survive

## N3 — Actuator-swap diagnosis and command-log matching

- **N3.1** All 4 misses classify as H1 (post-state coincidence). → **CONFIRMED** (computed in `n3c_h1_diagnosis.json`)
- **N3.2** Command-log matching: 8/8 actuator-swap. → **CONFIRMED** (under both literal and value-normalised variants)
- **N3.3** Benign 0/42 and 0/227 unchanged. → **PARTLY FALSIFIED**: 0/42 ✓; 227 is 29/227 literal, 1/227 value-normalised
- **N3.4** Falsified-label sensor-swap stays 24/30. → **CONFIRMED**

## N4 — MSB provenance reconciliation

- **N4.1** The two populations are disjoint. → **CONFIRMED**
- **N4.2** Union: NC 24/33, PM 1/33, PI 0/33, OP 1/33. → **CONFIRMED exactly**
- **N4.3** Both non-NC hits embed an entity mismatch; no grid instance does. → **FALSIFIED** (both come from the Δstate band)

## N5 — Initial-state coverage curve

- **N5.1** 0/16 at K=3; 6–10/16 at K=30; 8–12/16 at K=100. → **FALSIFIED above the range** (0/16, then 16/16)
- **N5.2** Per-mutant detection tracks 1−(1−w)^K. → **FALSIFIED** (stratified sampling beats the model at mid widths)
- **N5.3** Benign 0/14 at K=100. → **CONFIRMED**
- **N5.4** K=30 over 14 tools is seconds; K=100 under a minute. → **CONFIRMED** (sub-second)

## N6 — Analysis item (δ_cov replaces the Req2LTL anchor)

No prediction registered. Outcome: δ_cov measured per family, **0/42 to 25/42**
(`e8d_deltacov.json`). The plan anticipated 0/42 to 24/42.

---

**Ledger: 22 N-predictions, 6 falsified. With the original 17 (5 falsified): 39 total,
11 falsified.**
