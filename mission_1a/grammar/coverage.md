# PG-DSL Class-C Grammar — Coverage vs. SWaT P1+P2

**Mission:** mis_01KR2R4Q9Y3WZHZ53473PPZS66 (Mission 1A)
**Grammar file:** `grammar.lark`
**Coverage target (per mission task 2):** SWaT process stages P1 and P2 only. P3+ deferred to Mission 2.

---

## 1. Actuator Vocabulary (`actuator(name) := value`)

| Symbol  | Stage | Type             | Modelled values     | Grammar token | MiniCPS-modelled? |
|---------|-------|------------------|---------------------|---------------|-------------------|
| MV101   | P1    | Motorized valve  | `open`, `closed`    | `mv101`       | yes               |
| P101    | P1    | Pump (raw water) | `on`, `off`         | `p101`        | yes               |
| P102    | P1    | Pump (redundant) | `on`, `off`         | `p102`        | yes               |
| MV201   | P2    | Motorized valve  | `open`, `closed`    | `mv201`       | yes               |
| P201    | P2    | HCl dosing pump  | `on`, `off`         | `p201`        | partial¹          |
| P202    | P2    | HCl dosing pump  | `on`, `off`         | `p202`        | partial¹          |
| P203    | P2    | NaOCl dosing pump| `on`, `off`         | `p203`        | partial¹          |
| P204    | P2    | NaOCl dosing pump| `on`, `off`         | `p204`        | partial¹          |
| P205    | P2    | NaCl dosing pump | `on`, `off`         | `p205`        | partial¹          |
| P206    | P2    | NaCl dosing pump | `on`, `off`         | `p206`        | partial¹          |

¹ MiniCPS models pump on/off and gross flow but does **not** model chemistry kinetics
(pH, conductivity dynamics under dosing). Per `jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX`,
chemistry is out of scope. Tool descriptions that talk about pump-on/off events are
in scope; descriptions that talk about *chemical effects* of dosing fall outside the
in-scope DT and require complementary defences.

**Coverage:** 10/10 P1+P2 actuators tokenised.  Manual enumeration vs. SWaT
documentation:

- P1 actuators (per iTrust SWaT data dictionary): MV101, P101, P102 — **all covered.**
- P2 actuators: MV201, P201, P202, P203, P204, P205, P206 — **all covered.**

## 2. Sensor Vocabulary (`sensor(name) reads value`)

| Symbol  | Stage | Quantity                         | Modelled units / quals  | Grammar token | Added |
|---------|-------|----------------------------------|-------------------------|---------------|-------|
| LIT101  | P1    | Raw-water tank level             | `%`                     | `lit101`      |       |
| LIT201  | P2    | P2 buffer-tank level             | `%`                     | `lit201`      | dec_01KR2YPK31NM987H3KEVK9C2DT |
| FIT101  | P1    | Raw-water inlet flow             | `L_per_s`               | `fit101`      |       |
| FIT201  | P2    | P1→P2 cross-stage flow           | `L_per_s`               | `fit201`      | dec_01KR2YPK31NM987H3KEVK9C2DT |
| AIT201  | P2    | Conductivity                     | `uS_per_cm`             | `ait201`      |       |
| AIT202  | P2    | pH                               | `pH_units`              | `ait202`      |       |
| AIT203  | P2    | ORP (oxidation-reduction)        | `mV`                    | `ait203`      |       |

Qualitative readings `low | nominal | high` are accepted for descriptions that
specify behaviour symbolically (common in NL tool docs).

**Coverage:** 7/7 P1+P2 sensors tokenised after the additive extension authorised by
`dec_01KR2YPK31NM987H3KEVK9C2DT`. All 14 Mission 1B MCP tools now lift cleanly.

## 3. State-Variable Vocabulary (`Δstate(variable) {property+}`)

| State var      | Bound to                                | Used in / Stage  | Added |
|----------------|-----------------------------------------|------------------|-------|
| `L_T101`       | tank-T101 level                         | P1               |       |
| `L_T201`       | tank-T201 level                         | P2               | dec_01KR2YPK31NM987H3KEVK9C2DT |
| `L_T301`       | downstream P3 buffer (boundary refs)    | P2 boundary      |       |
| `Q_in_T101`    | inlet flow into T101                    | P1               |       |
| `Q_out_T101`   | outlet flow from T101                   | P1               |       |
| `Q_in_T201`    | inlet flow into T201                    | P2               | dec_01KR2YPK31NM987H3KEVK9C2DT |
| `Q_out_T201`   | outlet flow from T201                   | P2               | dec_01KR2YPK31NM987H3KEVK9C2DT |
| `C_HCl`        | HCl concentration in P2 pipe            | P2 (chemistry²)  |       |
| `C_NaOCl`      | NaOCl concentration                     | P2 (chemistry²)  |       |
| `C_NaCl`       | NaCl concentration                      | P2 (chemistry²)  |       |
| `pH_P2`        | pH at P2                                | P2 (chemistry²)  |       |
| `ORP_P2`       | ORP at P2                               | P2 (chemistry²)  |       |
| `Cond_P2`      | conductivity at P2                      | P2 (chemistry²)  |       |

² Chemistry-state symbols are *parsed* by the grammar but are flagged out-of-scope
for DT verification (the DT cannot certify their evolution). Lifted claims that
constrain chemistry symbols pass T2 syntactically and are deferred to T3's
composition partner (e.g. INVARLLM) at runtime.

## 4. Property Vocabulary

| Property                | Meaning                                                         |
|-------------------------|-----------------------------------------------------------------|
| `monotone [+|−]`        | state-variable is non-decreasing (`+`) or non-increasing (`−`)  |
| `bounded [a, b]`        | state-variable stays in `[a, b]` over the verification horizon  |
| `sign [+|−|0]`          | sign of the discrete-time increment over the horizon            |

## 5. Worked Examples (each parses against `grammar.lark`)

```
// honest description: "Open inlet to fill tank to 80%"
actuator(MV101) := open;
Δstate(L_T101) { monotone+, bounded[0, 100] };
sensor(LIT101) reads 80 %
```

```
// poisoned description (NL says fill, lifted claim should still match what NL says):
actuator(MV101) := open;
Δstate(L_T101) { sign + }
// — adversary's *implementation* will instead drive MV101 := closed and the
//   actual ΔL will be sign 0 or sign −. PG-DSL flags the mismatch at admission
//   between this lifted claim and the DT-observed trajectory.
```

```
// chemistry claim — parses, but DT cannot verify:
actuator(P201) := on;
Δstate(pH_P2) { monotone-, bounded[6.0, 8.5] }
```

## 6. Coverage Status

- [x] All P1 actuators (MV101, P101, P102) tokenised.
- [x] All P2 actuators (MV201, P201–P206) tokenised.
- [x] LIT101, **LIT201**, FIT101, **FIT201** (P1+P2 level/flow sensors) tokenised.
- [x] AIT201–AIT203 (P2 chemistry sensors) tokenised.
- [x] State-variable vocabulary covers T101 + **T201** mass-balance symbols, and chemistry symbols
      (the latter parsed but explicitly out-of-scope for DT verification).
- [x] Three property forms (`monotone`, `bounded`, `sign`) implemented.
- [x] All 14 Mission 1B MCP tools lift cleanly to grammar productions (see `mission_2a/coverage_check.md`).
- [ ] PI confirmation of vocabulary completeness — pending (acceptance criterion 2).

## 7. Additive extension (added 2026-05-08 per `dec_01KR2YPK31NM987H3KEVK9C2DT`)

Mission 2A's Task 3 grammar-coverage check identified that Mission 1B's MCP server
exposes `read_level_T201` and `read_flow_FIT201` (LIT201, FIT201) which were not in
the original Mission 1A grammar. Brain authorised an additive extension (Option A):

- New sensor terminals: `LIT201`, `FIT201` mirror the LIT101/FIT101 structure.
- New state-variable terminals: `L_T201`, `Q_in_T201`, `Q_out_T201` mirror the T101 set.
- No existing production was modified; T1 statement is unaffected; T2's class C widens
  to cover the full P1+P2 actuator/sensor surface (T2 is strengthened, not weakened);
  T3 statement is unaffected.

Verification (`python3 -c "from lark import Lark; Lark.open(...).parse(...)"`): 8/8
representative claims parse — 5 new productions and 3 pre-existing P1 productions.
See Mission 2A's `coverage_check.md` for the full 14-tool lift table.

## 7. Out of Scope (do not extend in Mission 1A)

- P3 dechlorination actuators/sensors.
- P4 ultra-filtration.
- P5 reverse-osmosis.
- P6 backwash & disposal.
- Network-layer actuators (PLC/HMI commands separate from physical effects).
- Per `jrn_01KR2K0ATN2SMRZ28SMRZ3ADVX`: chemistry kinetics, sensor noise beyond
  bounded-error, hardware aging, side-channel attacks on `L_verify`.
