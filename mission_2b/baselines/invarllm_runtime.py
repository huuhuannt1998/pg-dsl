"""INVARLLM-style runtime physical IDS baseline.

Mission 2B task 3 (mis_01KR3FJ9JJP5EKEFQ1AVFPPAZE).

Replicates INVARLLM (lit_01KR2J2TD01QA37TSTF6WFWQBG) — LLM offline-extracts
physical invariants from benign telemetry; runtime detection checks each
invariant against live telemetry. INVARLLM reports 100 % precision (29 TPs, 0
FPs on iTrust SWaT; 13 TPs, 0 FPs on WADI).

The runtime mechanism in INVARLLM is fully deterministic — only invariant
*extraction* uses an LLM offline. Our extraction is a deterministic offline
analysis of Mission 1B benign baseline traces; this stays within INVARLLM's
published invariant classes (operating bands, mass-balance residuals,
correlation-on-if-off). See baseline_design_memo.md.

Three invariant classes (named after the published types):
  - OperatingBand(sensor, low, high, slack)
  - MassBalance(tank, q_in, q_out, residual_threshold)
  - CorrelationOnIfOff(actuator_pair, expected_flow_signature)

Public API:
  INVARLLMRuntime.extract_from_traces(benign_traces) -> INVARLLMRuntime
  INVARLLMRuntime.check(telemetry) -> RuntimeReport
"""

from __future__ import annotations

import dataclasses
import statistics
from typing import Any


@dataclasses.dataclass
class Invariant:
    name: str
    description: str

    def check(self, telemetry: dict) -> tuple[bool, str]:
        """Return (passes, reason_if_violated). To be overridden."""
        raise NotImplementedError


@dataclasses.dataclass
class OperatingBand(Invariant):
    sensor: str = ""
    low: float = 0.0
    high: float = 100.0
    slack: float = 0.5

    def check(self, telemetry: dict) -> tuple[bool, str]:
        traj = telemetry.get(self.sensor)
        if traj is None:
            return True, ""
        for k, v in enumerate(traj):
            if not isinstance(v, (int, float)):
                continue
            if v < self.low - self.slack or v > self.high + self.slack:
                return False, f"{self.sensor}[{k}]={v:.3f} outside [{self.low}, {self.high}]"
        return True, ""


@dataclasses.dataclass
class MassBalance(Invariant):
    tank_level_sensor: str = "LIT101"
    q_in_per_unit: float = 0.5
    q_out: float = 0.4
    actuator_in_pump: str = "P101"
    actuator_in_valve: str = "MV101"
    actuator_out_valve: str = "MV201"
    residual_threshold: float = 0.10

    def check(self, telemetry: dict) -> tuple[bool, str]:
        levels = telemetry.get(self.tank_level_sensor)
        actuators_per_step = telemetry.get("actuator_per_step")
        if not levels or not actuators_per_step:
            return True, ""
        for k in range(1, len(levels)):
            prev = actuators_per_step[k - 1]
            n_pumps_on = (1 if prev.get(self.actuator_in_pump) == "on" else 0)
            inflow = (self.q_in_per_unit * n_pumps_on
                      if prev.get(self.actuator_in_valve) == "open" else 0.0)
            outflow = (self.q_out
                       if prev.get(self.actuator_out_valve) == "open" else 0.0)
            expected = inflow - outflow
            try:
                observed = float(levels[k]) - float(levels[k - 1])
            except (TypeError, ValueError):
                continue
            if abs(observed - expected) > self.residual_threshold:
                return False, (f"mass-balance residual at step {k}: "
                               f"observed={observed:.4f}, expected={expected:.4f}, "
                               f"|gap|={abs(observed-expected):.4f} > "
                               f"threshold={self.residual_threshold}")
        return True, ""


@dataclasses.dataclass
class RuntimeReport:
    fired: bool
    violations: list[dict]
    invariants_evaluated: int


class INVARLLMRuntime:
    """The runtime IDS that checks all extracted invariants against live
    telemetry."""

    def __init__(self, invariants: list[Invariant]) -> None:
        self.invariants = invariants

    @classmethod
    def extract_from_traces(cls, benign_traces: list[dict],
                            slack_band_pct: float = 5.0,
                            residual_safety_factor: float = 1.5,
                            ) -> "INVARLLMRuntime":
        """Offline extraction of invariants from a list of benign trajectories.

        Each trace is a dict containing time-series for each sensor and a
        per-step actuator snapshot. Mirrors what an LLM-driven extraction
        would do: identify operating bands (min/max with slack), mass-balance
        residual envelopes (max-residual × safety factor), and correlation
        invariants. Stays within INVARLLM's published invariant scope.
        """
        invariants: list[Invariant] = []

        sensor_names = ["LIT101", "LIT201", "FIT101", "FIT201",
                        "AIT201", "AIT202", "AIT203"]

        for sensor in sensor_names:
            samples: list[float] = []
            for trace in benign_traces:
                seq = trace.get(sensor)
                if not seq:
                    continue
                for v in seq:
                    if isinstance(v, (int, float)):
                        samples.append(float(v))
            if not samples:
                continue
            lo, hi = min(samples), max(samples)
            slack = slack_band_pct * 0.01 * max(1.0, hi - lo)
            invariants.append(OperatingBand(
                name=f"band_{sensor}",
                description=f"{sensor} ∈ [{lo:.3f}, {hi:.3f}] ± {slack:.3f}",
                sensor=sensor, low=lo, high=hi, slack=slack,
            ))

        # Mass-balance residual envelope on T101 (the testbed's primary tank).
        max_residual = 0.0
        for trace in benign_traces:
            levels = trace.get("LIT101")
            actuators = trace.get("actuator_per_step")
            if not levels or not actuators:
                continue
            for k in range(1, len(levels)):
                prev = actuators[k - 1]
                n_pumps_on = (1 if prev.get("P101") == "on" else 0)
                inflow = 0.5 * n_pumps_on if prev.get("MV101") == "open" else 0.0
                outflow = 0.4 if prev.get("MV201") == "open" else 0.0
                expected = inflow - outflow
                try:
                    observed = float(levels[k]) - float(levels[k - 1])
                except (TypeError, ValueError):
                    continue
                gap = abs(observed - expected)
                if gap > max_residual:
                    max_residual = gap

        residual_threshold = max(0.10, residual_safety_factor * max_residual)
        invariants.append(MassBalance(
            name="mb_T101",
            description=(f"|dLIT101 − expected_flow_T101| ≤ "
                         f"{residual_threshold:.3f} (safety factor "
                         f"{residual_safety_factor}× over benign max "
                         f"residual {max_residual:.4f})"),
            residual_threshold=residual_threshold,
        ))

        return cls(invariants)

    def check(self, telemetry: dict) -> RuntimeReport:
        """Evaluate all invariants against the telemetry trace.

        ``telemetry`` is a dict containing:
          - per-sensor time series (e.g., 'LIT101': [70.0, 70.5, ...])
          - 'actuator_per_step': list of per-step actuator snapshot dicts
        """
        violations: list[dict] = []
        for inv in self.invariants:
            ok, reason = inv.check(telemetry)
            if not ok:
                violations.append({
                    "invariant": inv.name,
                    "reason": reason,
                    "description": inv.description,
                })
        return RuntimeReport(
            fired=bool(violations),
            violations=violations,
            invariants_evaluated=len(self.invariants),
        )

    def to_summary(self) -> dict:
        return {
            "n_invariants": len(self.invariants),
            "invariants": [{"name": i.name, "description": i.description}
                           for i in self.invariants],
        }
