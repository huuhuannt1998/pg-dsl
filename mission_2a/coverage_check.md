# Task 3 — Grammar Coverage Check vs Mission 1B's 14 MCP Tools

**Mission:** mis_01KR2W2P9XKTC37MKYQ9FW5YF1 (Mission 2A).
**Embedded condition (Gate 0):** Enumerate grammar coverage against the P1+P2 MCP tools.
**Verdict:** **FAIL — DECISION CHECKPOINT FIRED** (2 sensor terminals missing from grammar).

---

## 1. Authoritative tool list (Mission 1B `mcp_server.make_tools`)

```
 1. open_valve_MV101              8. stop_dosing_pump_P201
 2. close_valve_MV101             9. set_dosing_rate
 3. start_pump_P101              10. read_level_T101
 4. stop_pump_P101                11. read_level_T201          ← reads LIT201
 5. open_valve_MV201              12. read_flow_FIT101
 6. close_valve_MV201              13. read_flow_FIT201          ← reads FIT201
 7. start_dosing_pump_P201        14. read_chemical_AIT201
```

(The mission text says "13 tools" in task 3 but enumerates 14; the count text is a minor
copy-paste error in the mission spec. The authoritative list above is from
`make_tools()` in `mission_1b/mcp_server/server.py` and contains 14 entries.)

## 2. Grammar terminals (Mission 1A `grammar/grammar.lark`)

### Actuator names (10 — complete coverage)

```
MV101, MV201, P101, P102, P201, P202, P203, P204, P205, P206
```

All 10 P1+P2 actuators are tokenised. Tools 1–9 lift cleanly:

| # | Tool | Honest lifted claim | Parse |
|---|---|---|---|
| 1 | open_valve_MV101 | `actuator(MV101) := open` | ✓ |
| 2 | close_valve_MV101 | `actuator(MV101) := closed` | ✓ |
| 3 | start_pump_P101 | `actuator(P101) := on` | ✓ |
| 4 | stop_pump_P101 | `actuator(P101) := off` | ✓ |
| 5 | open_valve_MV201 | `actuator(MV201) := open` | ✓ |
| 6 | close_valve_MV201 | `actuator(MV201) := closed` | ✓ |
| 7 | start_dosing_pump_P201 | `actuator(P201) := on; Δstate(Cond_P2) { sign + }` | ✓ |
| 8 | stop_dosing_pump_P201 | `actuator(P201) := off` | ✓ |
| 9 | set_dosing_rate | `actuator(P201) := on; Δstate(Cond_P2) { sign +, monotone+ }` | ✓ |

### Sensor names (5 — INCOMPLETE)

```
LIT101, FIT101, AIT201, AIT202, AIT203
```

Two sensors are MISSING:

- **`LIT201`** — used by `read_level_T201` (tool 11)
- **`FIT201`** — used by `read_flow_FIT201` (tool 13)

These are referenced by Mission 1B's tool surface but cannot be expressed as grammar
sensor terminals. Any honest description of `read_level_T201` or `read_flow_FIT201` will
fail to lift to a faithful claim — the lifter would have to either reject the tool as
out-of-grammar or substitute a wrong sensor, both of which are wrong outcomes for an
honest tool.

| # | Tool | Faithful claim required | Status |
|---|---|---|---|
| 11 | read_level_T201 | `sensor(LIT201) reads nominal` | ✗ — LIT201 not in grammar |
| 13 | read_flow_FIT201 | `sensor(FIT201) reads nominal` | ✗ — FIT201 not in grammar |
| 10, 12, 14 | read_level_T101, read_flow_FIT101, read_chemical_AIT201 | `sensor(LIT101|FIT101|AIT201) reads nominal` | ✓ |

### State variables (relevant subset)

The grammar's `state_var` production includes `L_T101`, `L_T301`, `Q_in_T101`,
`Q_out_T101`, but **omits** `L_T201`, `Q_in_T201`, `Q_out_T201`. This becomes relevant
when lifting Δstate-bearing claims about the P2 buffer tank (e.g., a maintenance tool
description that specifies T201 mass-balance). For the present 14-tool surface this
matters less because the 14-tool surface only needs sensor names directly; the
state-variable gap is a secondary concern that compounds the sensor gap.

## 3. Why this surfaces in Mission 2A and not Mission 1A

Mission 1A's `coverage.md` declared "5/5 sensors mentioned in the mission spec are
tokenised. Other P2 sensors (FIT201) exist in SWaT but are not part of the mission's
enumerated target vocabulary." That was correct for Mission 1A's task scope (P1+P2
*minimum* vocabulary).

Mission 1B then enlarged the tool surface to include `read_level_T201` (LIT201) and
`read_flow_FIT201` (FIT201) for plant-control completeness, but the grammar was not
updated to track. The two artifacts diverged silently. Gate 0's coverage check is the
intended gate to catch exactly this divergence.

## 4. Required Brain Decision

Two acceptable resolutions, in order of executor preference:

- **Option A (recommended).** Extend the locked grammar by adding `LIT201` and `FIT201`
  as sensor terminals (and `L_T201`, `Q_in_T201`, `Q_out_T201` as state variables).
  This is a minimal, additive change that does not affect any existing claim in
  Mission 1A, does not change theorem statements, and lets all 14 tools lift cleanly.

- **Option B.** Drop `read_level_T201` and `read_flow_FIT201` from Mission 2A's tool
  surface. Both are admitted-by-default as out-of-grammar (intended behaviour per
  scope boundary) and report `out_of_grammar` rejection on every benign rep. FPR for
  these two tools is then 100% by design, which is acceptable per the scope boundary's
  text but pushes FPR ≤ δ_lift for the *other* 12 tools.

Executor recommendation: **Option A**. The grammar extension is purely additive (new
terminals), preserves all Mission 1A theorems and witnesses, and matches the scope
boundary's spirit (FPR target should reflect lifter performance, not vocabulary gaps).

## 5. Pipeline blocking status

Per Mission 2A scope: "Do NOT proceed past first-task phase if any of the 4 embedded
conditions fires a DECISION checkpoint — wait for brain resolution."

Pipeline tasks 6–13 (lifter, DT verifier, matcher, integration, ASR/FPR campaigns,
packaging) are blocked until brain resolves Option A vs Option B.
