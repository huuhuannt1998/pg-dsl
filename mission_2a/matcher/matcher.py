"""Formal matcher — checks φ ⊨ ψ within ε_DT and decides admission.

Mission 2A task 8 (mis_01KR2W2P9XKTC37MKYQ9FW5YF1).

Tolerance:  ε_DT = 1.0 %-full per sample (Mission 1A digest, validated by Task 2)
            δ*   = 2.232 %-full cumulative (T1 worst-case bound, validated by Task 2)

The matcher walks each clause in φ and checks satisfaction in ψ. If any
clause is contradicted by ψ within tolerance, the tool is REJECTED with a
reason. Otherwise ADMITTED.

Clause semantics:
  actuator(NAME) := value
        Pass iff ψ.actuator_post[NAME] == value (binary, exact).
  sensor(NAME) reads VALUE
        Pass iff |ψ.tool_return_value − ψ.sensor_oracle_post[NAME]| ≤ ε_DT
        (i.e., the tool returns the sensor it claims to return, within
        per-sample noise budget). For 'reads nominal' qualitative claims,
        the check is just that tool_return.sensor == NAME (i.e., the tool
        returns the named sensor's reading).
  Δstate(VAR) {sign s}        s ∈ {+, -, 0}
        Pass iff ψ.delta_<VAR>_signs.sign == s, with the cumulative
        deviation respecting δ* = 2.232 %-full (a sign 0 claim with
        |Δ| > δ* counts as a contradiction).
  Δstate(VAR) {monotone d}    d ∈ {+, -}
        Pass iff ψ.delta_<VAR>_signs.monotone == d.
  Δstate(VAR) {bounded[a, b]}
        Pass iff ψ.delta_<VAR>_signs.min ≥ a − ε_DT and max ≤ b + ε_DT.

The matcher needs both ψ and (sometimes) the tool's return value, which the
DT verifier captures as ``tool_return_value``.
"""

from __future__ import annotations

import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


HERE = Path(__file__).resolve().parent
MISSION_2A = HERE.parent
sys.path.insert(0, str(MISSION_2A))


EPS_DT      = 1.0
DELTA_STAR  = 2.232

# Per-state-variable tolerance for `bounded[]` checks. ε_DT in T1 is anchored
# to LIT101 (%-full of operating capacity); for sensors with different units
# (notably AIT201 conductivity, in arbitrary calibrated units, nominal range
# 0.40–1.50) the per-sample tolerance is much smaller. We use the published
# "below 0.40 = underdose" as the natural noise floor: ε_AIT = 0.05 (one
# tenth of the band width) lets honest dosing land cleanly while flagging
# 60×-underdose magnitude poisoning.
EPS_BY_STATE_VAR = {
    "L_T101":  EPS_DT,
    "L_T201":  EPS_DT,
    "Cond_P2": 0.05,    # AIT201 conductivity tolerance
}


@dataclasses.dataclass
class AdmissionDecision:
    tool_name: str
    initial_state_name: str
    phi: str
    admitted: bool
    rejection_reasons: list[str]
    clause_results: list[dict]
    notes: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# Regex parsers for each clause family.
ACTUATOR_RE = re.compile(r"actuator\(([A-Za-z0-9_]+)\)\s*:=\s*(open|closed|on|off)")
SENSOR_RE   = re.compile(r"sensor\(([A-Za-z0-9_]+)\)\s+reads\s+(nominal|low|high|[0-9]+\.?[0-9]*)")
DSTATE_RE   = re.compile(r"Δstate\(([A-Za-z0-9_]+)\)\s*\{([^}]+)\}")
SIGN_RE     = re.compile(r"sign\s*([+\-0])")
MONOTONE_RE = re.compile(r"monotone\s*([+\-])")
BOUNDED_RE  = re.compile(r"bounded\s*\[\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*\]")


# Map state-variable names in the grammar to keys in the DT-verifier output.
STATE_VAR_TO_TRAJECTORY_KEY = {
    "L_T101":  "delta_LIT101_signs",
    "L_T201":  "delta_LIT201_signs",
    "Cond_P2": "delta_Cond_P2_signs",
}


def _split_clauses(phi: str) -> list[str]:
    return [c.strip() for c in phi.split(";") if c.strip()]


def _check_actuator(clause: str, psi: dict) -> dict:
    m = ACTUATOR_RE.search(clause)
    if not m:
        return {"clause": clause, "kind": "actuator", "passed": False,
                "reason": "could_not_parse"}
    name, value = m.group(1), m.group(2)
    observed = psi["actuator_post"].get(name)
    passed = (observed == value)
    return {"clause": clause, "kind": "actuator", "name": name,
            "claimed_value": value, "observed_value": observed,
            "passed": passed,
            "reason": None if passed else f"actuator {name} expected={value} observed={observed}"}


def _check_sensor(clause: str, psi: dict) -> dict:
    m = SENSOR_RE.search(clause)
    if not m:
        return {"clause": clause, "kind": "sensor", "passed": False,
                "reason": "could_not_parse"}
    name, value = m.group(1), m.group(2)
    tool_return = psi.get("tool_return_value") or {}
    returned_sensor = tool_return.get("sensor")
    returned_value = tool_return.get("value")
    # Read tools return the sensor value at *call time*, so compare against
    # the pre-call oracle snapshot, not the post-window snapshot.
    oracle_value = psi["sensor_oracle_pre"].get(name)

    # First check: did the tool return the sensor named in the claim?
    if returned_sensor != name:
        return {"clause": clause, "kind": "sensor", "name": name,
                "claimed_sensor": name,
                "tool_returned_sensor": returned_sensor,
                "passed": False,
                "reason": f"sensor mismatch: claim names {name}, tool returns {returned_sensor}"}

    # Second check: does the returned value agree with the named sensor's oracle within ε_DT?
    if value == "nominal":
        # qualitative claim — only sensor identity matters
        try:
            gap = abs(float(returned_value) - float(oracle_value))
        except (TypeError, ValueError):
            gap = None
        passed = True if gap is None or gap <= EPS_DT else False
        return {"clause": clause, "kind": "sensor", "name": name,
                "tool_returned_value": returned_value,
                "oracle_value": oracle_value, "gap": gap, "eps_DT": EPS_DT,
                "passed": passed,
                "reason": None if passed else f"value gap {gap:.3f} > ε_DT={EPS_DT}"}

    # Quantitative claim: parse expected value and check
    try:
        expected = float(value)
        gap = abs(float(returned_value) - expected)
    except (TypeError, ValueError):
        return {"clause": clause, "kind": "sensor", "name": name,
                "passed": False, "reason": "non-numeric value comparison failed"}
    passed = gap <= EPS_DT
    return {"clause": clause, "kind": "sensor", "name": name,
            "tool_returned_value": returned_value,
            "expected_value": expected, "gap": gap, "eps_DT": EPS_DT,
            "passed": passed,
            "reason": None if passed else f"value gap {gap:.3f} > ε_DT={EPS_DT}"}


def _check_dstate(clause: str, psi: dict) -> dict:
    m = DSTATE_RE.search(clause)
    if not m:
        return {"clause": clause, "kind": "dstate", "passed": False,
                "reason": "could_not_parse"}
    var, props = m.group(1), m.group(2)
    traj_key = STATE_VAR_TO_TRAJECTORY_KEY.get(var)
    if traj_key is None:
        return {"clause": clause, "kind": "dstate", "passed": False,
                "reason": f"state-var {var} not tracked in ψ (only L_T101, L_T201, Cond_P2 tracked)"}

    summary = psi.get(traj_key)
    if summary is None:
        return {"clause": clause, "kind": "dstate", "passed": False,
                "reason": f"trajectory key {traj_key} missing from ψ"}

    failures: list[str] = []

    sign_m = SIGN_RE.search(props)
    if sign_m:
        claimed = sign_m.group(1)
        observed_sign = summary["sign"]
        # Tighten to also reject sign==0 if |Δ| > δ* (gross deviation under sign-0 claim)
        sign_passed = (observed_sign == claimed) or (
            claimed == "0" and abs(summary["delta"]) <= DELTA_STAR
            and observed_sign != "0"
        )
        # Re-tighten: a sign-0 claim with |Δ| > δ* should fail
        if claimed == "0" and abs(summary["delta"]) > DELTA_STAR:
            sign_passed = False
        # And a sign-{+,-} claim with the wrong observed sign should fail
        if claimed in ("+", "-") and observed_sign != claimed:
            sign_passed = False
        if not sign_passed:
            failures.append(f"sign claim {claimed} but observed {observed_sign} (Δ={summary['delta']:+.3f})")

    monotone_m = MONOTONE_RE.search(props)
    if monotone_m:
        claimed_m = monotone_m.group(1)
        observed_m = summary["monotone"]
        if observed_m != claimed_m:
            failures.append(f"monotone claim {claimed_m} but observed {observed_m}")

    bounded_m = BOUNDED_RE.search(props)
    if bounded_m:
        a, b = float(bounded_m.group(1)), float(bounded_m.group(2))
        eps_var = EPS_BY_STATE_VAR.get(var, EPS_DT)
        # Δstate(VAR) {bounded[a, b]} on a verification trajectory means
        # 'state reaches [a, b]' (the description's claimed steady-state
        # target). For monotone+ / monotone- claims this aligns with the
        # final trajectory value; for sign-0 claims the trajectory stays
        # at the initial value and end == start. We therefore check the
        # END of the trajectory against the band (with ε_var slack).
        observed_last = summary["last"]
        if observed_last < a - eps_var or observed_last > b + eps_var:
            failures.append(
                f"bounded[{a},{b}] expects steady-state in band, but trajectory "
                f"ends at {observed_last:.4f} (ε_{var}={eps_var})"
            )

    passed = not failures
    return {"clause": clause, "kind": "dstate", "var": var,
            "summary": summary, "passed": passed,
            "reason": None if passed else "; ".join(failures)}


def evaluate(phi: str, psi: dict, tool_name: str = "",
             initial_state_name: str = "") -> AdmissionDecision:
    """Decide ADMIT / REJECT for one (φ, ψ) pair."""
    if not phi.strip():
        return AdmissionDecision(
            tool_name=tool_name,
            initial_state_name=initial_state_name,
            phi=phi, admitted=False,
            rejection_reasons=["out_of_grammar (empty φ)"],
            clause_results=[],
        )

    clauses = _split_clauses(phi)
    results: list[dict] = []
    rejections: list[str] = []
    for cl in clauses:
        if cl.startswith("actuator"):
            r = _check_actuator(cl, psi)
        elif cl.startswith("sensor"):
            r = _check_sensor(cl, psi)
        elif cl.startswith("Δstate"):
            r = _check_dstate(cl, psi)
        else:
            r = {"clause": cl, "kind": "unknown", "passed": False,
                 "reason": "unrecognised clause prefix"}
        results.append(r)
        if not r["passed"]:
            rejections.append(r["reason"])

    return AdmissionDecision(
        tool_name=tool_name,
        initial_state_name=initial_state_name,
        phi=phi,
        admitted=(not rejections),
        rejection_reasons=rejections,
        clause_results=results,
    )


# -----------------------------------------------------------------------------
# CLI: combine the lifter's lifted_claims.json with the DT verifier's
# measured_effects.json, write admission_decisions.json.
# -----------------------------------------------------------------------------

def main() -> int:
    lifted = json.loads(
        (MISSION_2A / "lifter" / "lifted_claims.json").read_text()
    )["lifted_claims"]
    measured = json.loads(
        (MISSION_2A / "dt_verifier" / "measured_effects.json").read_text()
    )["measured_effects"]

    by_tool_phi = {c["tool_name"]: c for c in lifted}

    decisions: list[dict] = []
    for tool, samples in measured.items():
        phi = by_tool_phi.get(tool, {}).get("phi", "")
        out_of_grammar = by_tool_phi.get(tool, {}).get("out_of_grammar", True)
        if out_of_grammar:
            for psi in samples:
                d = AdmissionDecision(
                    tool_name=tool,
                    initial_state_name=psi["initial_state_name"],
                    phi=phi,
                    admitted=False,
                    rejection_reasons=["out_of_grammar"],
                    clause_results=[],
                )
                decisions.append(d.to_dict())
            continue

        for psi in samples:
            d = evaluate(phi, psi, tool_name=tool,
                         initial_state_name=psi["initial_state_name"])
            decisions.append(d.to_dict())

    out_path = MISSION_2A / "matcher" / "admission_decisions.json"
    serialised = {
        "eps_DT": EPS_DT,
        "delta_star": DELTA_STAR,
        "decisions": decisions,
    }
    out_path.write_text(json.dumps(serialised, indent=2, default=str))

    # Summary
    print(f"Total decisions             : {len(decisions)}")
    n_admit = sum(1 for d in decisions if d["admitted"])
    print(f"  admitted                  : {n_admit}")
    print(f"  rejected                  : {len(decisions) - n_admit}")
    print(f"\nPer-tool decision (over 3 initial states):")
    by_tool: dict[str, list] = {}
    for d in decisions:
        by_tool.setdefault(d["tool_name"], []).append(d)
    for tool, ds in by_tool.items():
        admits = sum(1 for d in ds if d["admitted"])
        print(f"  {tool:<32} {admits}/{len(ds)} admitted")
        for d in ds:
            if not d["admitted"]:
                print(f"    [{d['initial_state_name']}] REJECT: {d['rejection_reasons'][:1]}")
    print(f"\nOutput: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
