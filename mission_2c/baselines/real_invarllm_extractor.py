"""Real-Qwen INVARLLM extractor — drop-in replacement for the Mission 2B
deterministic stub.

Mission 2C task 5/9 (mis_01KR3GKV2ESRM4FR43W3VRG0MA).

INVARLLM (lit_01KR2J2TD01QA37TSTF6WFWQBG) uses an LLM offline to extract
physical invariants from benign telemetry. Runtime detection then uses those
extracted invariants — no LLM in the runtime path.

This module replicates the LLM-extraction step using Qwen on Mission 1B
benign-baseline telemetry summaries, then re-uses Mission 2B's
INVARLLMRuntime class (deterministic runtime check) with the
LLM-extracted invariants. Faithfulness target: stay within INVARLLM's
published invariant scope (operating bands, mass-balance residuals,
correlation-on-if-off).
"""

from __future__ import annotations

import json
import re
import sys
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
M2B = HERE.parent.parent / "mission_2b"
M1B = HERE.parent.parent / "mission_1b"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(M2B))

from qwen_client import call
from baselines import INVARLLMRuntime, OperatingBand, MassBalance, Invariant


EXTRACTION_PROMPT_TEMPLATE = """\
You are INVARLLM, an offline invariant-extraction agent for the SWaT P1+P2
testbed. Given the BENIGN-OPERATION TELEMETRY SUMMARY below, identify the
physical invariants that hold during nominal operation. Output ONLY in the
following JSON schema, no commentary or markdown:

{{
  "operating_bands": [
    {{"sensor": "<name>", "low": <float>, "high": <float>}}
  ],
  "mass_balance": [
    {{"tank": "<name>", "residual_threshold_per_step_pct_full": <float>}}
  ]
}}

INVARIANT TYPES:
  - operating_bands: each sensor's nominal value range across benign trajectories.
  - mass_balance: per-tank max benign residual between observed dL and the
    expected flow from actuator state, used as the runtime threshold.

VOCABULARY:
  sensors  : LIT101, LIT201, FIT101, FIT201, AIT201
  tanks    : T101 (level sensed by LIT101)

TELEMETRY SUMMARY:
{telemetry_block}

JSON output:"""


def _summarise_traces(benign_traces: list[dict]) -> str:
    """Build a compact telemetry summary block to feed Qwen."""
    sensor_stats: dict[str, dict] = {}
    for sensor in ("LIT101", "LIT201", "FIT101", "FIT201", "AIT201"):
        all_vals: list[float] = []
        for tr in benign_traces:
            seq = tr.get(sensor) or []
            for v in seq:
                if isinstance(v, (int, float)):
                    all_vals.append(float(v))
        if not all_vals:
            continue
        sensor_stats[sensor] = {
            "n_samples": len(all_vals),
            "min": min(all_vals),
            "max": max(all_vals),
            "mean": sum(all_vals) / len(all_vals),
            "stdev": statistics.stdev(all_vals) if len(all_vals) > 1 else 0.0,
        }

    # Per-tank mass-balance residual stats (T101).
    residuals = []
    for tr in benign_traces:
        levels = tr.get("LIT101") or []
        actuators = tr.get("actuator_per_step") or []
        if len(levels) < 2 or not actuators:
            continue
        for k in range(1, len(levels)):
            prev = actuators[k - 1] if k - 1 < len(actuators) else {}
            n_pumps_on = (1 if prev.get("P101") == "on" else 0)
            inflow = 0.5 * n_pumps_on if prev.get("MV101") == "open" else 0.0
            outflow = 0.4 if prev.get("MV201") == "open" else 0.0
            expected = inflow - outflow
            try:
                observed = float(levels[k]) - float(levels[k - 1])
            except (TypeError, ValueError):
                continue
            residuals.append(abs(observed - expected))
    if residuals:
        max_resid = max(residuals)
        p99_resid = sorted(residuals)[int(len(residuals) * 0.99)]
        mb_stats = {"n_samples": len(residuals), "max_residual": max_resid,
                    "p99_residual": p99_resid}
    else:
        mb_stats = {}

    # Render summary as text Qwen can read.
    lines = [f"Number of benign trajectories analysed: {len(benign_traces)}"]
    lines.append("Per-sensor statistics:")
    for s, st in sensor_stats.items():
        lines.append(f"  {s}: n={st['n_samples']}, min={st['min']:.3f}, "
                     f"max={st['max']:.3f}, mean={st['mean']:.3f}, "
                     f"stdev={st['stdev']:.3f}")
    if mb_stats:
        lines.append(f"T101 mass-balance residual (|observed dL - expected flow|): "
                     f"n={mb_stats['n_samples']}, "
                     f"max={mb_stats['max_residual']:.4f}, "
                     f"p99={mb_stats['p99_residual']:.4f}")
    return "\n".join(lines)


def extract_invariants_real_qwen(benign_traces: list[dict]) -> tuple[INVARLLMRuntime, dict]:
    """Run real-Qwen extraction on benign telemetry; return an INVARLLMRuntime
    populated with the LLM-extracted invariants and the raw response trace."""
    summary = _summarise_traces(benign_traces)
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(telemetry_block=summary)
    result = call("invarllm", prompt, max_tokens=600)
    raw = result["response"].strip()
    latency = result["latency_s"]

    # Strip markdown fences if present.
    text = raw
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    # Find the first JSON object.
    obj_match = re.search(r"\{.*\}", text, re.DOTALL)
    if obj_match:
        text = obj_match.group(0)

    invariants: list[Invariant] = []
    parsed: dict = {}
    parse_error = None
    # Safety factor applied to LLM-returned thresholds. INVARLLM's published
    # iTrust SWaT result uses an empirically-calibrated safety margin to
    # achieve 0% false-positive on benign data; we replicate that practice
    # post-processing the LLM's raw extraction.
    SAFETY_FACTOR = 1.5
    try:
        parsed = json.loads(text)
        for band in parsed.get("operating_bands", []):
            sensor = band.get("sensor")
            low = float(band.get("low"))
            high = float(band.get("high"))
            band_width = abs(high - low)
            # Slack scaled to band width with safety factor; minimum 0.5
            # absolute floor to avoid hyper-tight bands on near-constant sensors.
            slack = max(SAFETY_FACTOR * 0.05 * band_width, 0.5)
            invariants.append(OperatingBand(
                name=f"band_{sensor}",
                description=f"{sensor} ∈ [{low:.3f}, {high:.3f}] ± {slack:.3f} "
                            f"(real-Qwen × {SAFETY_FACTOR}× safety)",
                sensor=sensor, low=low, high=high, slack=slack,
            ))
        for mb in parsed.get("mass_balance", []):
            if mb.get("tank") == "T101":
                raw_threshold = float(mb.get("residual_threshold_per_step_pct_full"))
                threshold = SAFETY_FACTOR * raw_threshold
                invariants.append(MassBalance(
                    name="mb_T101",
                    description=(f"|dLIT101 - expected_flow| ≤ {threshold:.4f} "
                                 f"(real-Qwen raw {raw_threshold:.4f} × {SAFETY_FACTOR}× safety)"),
                    residual_threshold=threshold,
                ))
    except (ValueError, TypeError) as e:
        parse_error = repr(e)

    extraction_record = {
        "raw_response": raw,
        "parsed_response": parsed,
        "parse_error": parse_error,
        "n_invariants": len(invariants),
        "latency_s": latency,
    }
    return INVARLLMRuntime(invariants), extraction_record
