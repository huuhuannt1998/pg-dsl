"""Backfill macro \newcommand definitions in paper/main.tex from the JSON
campaign outputs.

Reads campaign outputs from mission_3b/results/ and rewrites the
[PEND] placeholders in main.tex with formatted LaTeX values
(e.g., "$15/227 = 6.61\\%$ $[4.04, 10.62]$").

Idempotent: safely re-runnable. If a JSON output is missing the
corresponding macro is left as [PEND].
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
M3B = ROOT / "mission_3b" / "results"
PAPER_MAIN = ROOT / "paper" / "main.tex"


def fmt_count_with_ci(k: int, n: int, ci_low: float, ci_high: float) -> str:
    """Return e.g. '$15/227 = 6.61\\%$ $[4.04, 10.62]$' as LaTeX-safe string."""
    pct = 100 * k / n if n else 0.0
    return rf"${k}/{n} = {pct:.2f}\%$ $[{ci_low*100:.2f}, {ci_high*100:.2f}]$"


def fmt_count_short(k: int, n: int, ci_low: float, ci_high: float) -> str:
    """Compact: '$15/227\,(6.61\\%)$'"""
    pct = 100 * k / n if n else 0.0
    return rf"${k}/{n}\,({pct:.1f}\%)$"


def load_json(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    macros: dict[str, str] = {}

    # --- Per-style FPR on extended corpus ---
    ps = load_json(M3B / "per_style_canonical_extended_qwen3.json")
    if ps:
        n = ps["n_total"]
        k = ps["n_rejected"]
        ci = ps["fpr_wilson_ci_95"]
        macros["extPerStyleN"] = str(n)
        macros["extPerStyleFPR"] = rf"${k}/{n} = {100*k/n:.2f}\%$"
        macros["extPerStyleCI"] = rf"$[{ci[0]*100:.2f}, {ci[1]*100:.2f}]$"
        bs = ps.get("by_style", {})
        for style_key, macro_key in (("FORMAL", "perStyleFormal"),
                                       ("CASUAL", "perStyleCasual"),
                                       ("TERSE",  "perStyleTerse")):
            if style_key in bs:
                v = bs[style_key]
                macros[macro_key] = rf"{v['rejected']}/{v['n']} ({100*v['fpr']:.2f}\%, CI $[{v['ci'][0]*100:.2f}, {v['ci'][1]*100:.2f}]$)"
        # By-source summary
        bsrc = ps.get("by_source", {})
        if "seed_M2B" in bsrc:
            v = bsrc["seed_M2B"]
            macros["perStyleSeed"] = rf"{v['rejected']}/{v['n']} ({100*v['fpr']:.2f}\%)"
        # Aggregate mistral paraphrase rejects
        m_n = sum(v["n"] for k_, v in bsrc.items() if k_ != "seed_M2B")
        m_rej = sum(v["rejected"] for k_, v in bsrc.items() if k_ != "seed_M2B")
        if m_n:
            macros["perStyleMistral"] = rf"{m_rej}/{m_n} ({100*m_rej/m_n:.2f}\%)"

    # --- T2 probes extended ---
    t2 = load_json(M3B / "t2_probes_extended_qwen3.json")
    if t2:
        macros["tTwoN"] = str(t2["n_probes"])
        macros["tTwoCorrect"] = f"{t2['n_correct']}/{t2['n_probes']}"
        macros["tTwoCorrectPct"] = f"{100*t2['correct_rate']:.1f}"

    # --- MSB subset ---
    msb = load_json(M3B / "msb_subset_evaluation.json")
    if msb:
        bc = msb.get("by_class", {})
        for cls in ("NC", "PM", "PI", "OP"):
            if cls in bc:
                v = bc[cls]
                macros[f"msb{cls}pgdsl"] = (
                    rf"{v['pgdsl_detected']}/{v['n']} ({100*v['pgdsl_rate']:.0f}\%, "
                    rf"CI [{v['pgdsl_ci'][0]*100:.0f}, {v['pgdsl_ci'][1]*100:.0f}])"
                )
                macros[f"msb{cls}mcpshield"] = (
                    rf"{v['mcpshield_detected']}/{v['n']} ({100*v['mcpshield_rate']:.0f}\%, "
                    rf"CI [{v['mcpshield_ci'][0]*100:.0f}, {v['mcpshield_ci'][1]*100:.0f}])"
                )
        z3 = msb.get("z3_comparison", {})
        if "pgdsl" in z3 and z3["pgdsl"].get("detected") is not None:
            macros["msbZthreepgdsl"] = "1/1 (100\\%)" if z3["pgdsl"].get("detected") else "0/1 (0\\%)"
        if "mcpshield" in z3 and z3["mcpshield"].get("detected") is not None:
            macros["msbZthreemcpshield"] = "1/1 (100\\%)" if z3["mcpshield"].get("detected") else "0/1 (0\\%)"

    # --- Real-agent N=10 ---
    ra = load_json(M3B / "real_agent_asr_n10.json")
    if ra:
        agg = ra.get("aggregate", {})
        for atk_id, macro_prefix in (("A1", "realAgentAone"),
                                       ("A2", "realAgentAtwo"),
                                       ("W2", "realAgentWtwo"),
                                       ("A2eng", "realAgentAtwoeng")):
            if atk_id not in agg:
                continue
            for mode_key, macro_suffix in (("without", "without"), ("with", "with")):
                if mode_key not in agg[atk_id]:
                    continue
                v = agg[atk_id][mode_key]
                ci = v.get("wilson_ci_95", [0, 0])
                macros[f"{macro_prefix}{macro_suffix}"] = (
                    rf"${v['n_succeeded']}/{v['n_reps']} = {100*v['asr']:.0f}\%$ $[{ci[0]*100:.1f}, {ci[1]*100:.1f}]$"
                )

    # Apply substitutions
    text = PAPER_MAIN.read_text()
    n_changed = 0
    for name, value in macros.items():
        # Replace lines like "\newcommand{\NAME}{[PEND]}" with "\newcommand{\NAME}{<value>}"
        pattern = re.compile(
            r"(\\newcommand\{\\" + re.escape(name) + r"\}\{)([^}]*)(\})"
        )
        new_text, n = pattern.subn(rf"\g<1>{value}\g<3>", text)
        if n:
            text = new_text
            n_changed += 1
            print(f"  {name} -> {value[:60]}{'...' if len(value) > 60 else ''}")

    PAPER_MAIN.write_text(text)
    print(f"\nBackfilled {n_changed} macros into {PAPER_MAIN}")

    # Report any still-PEND
    still_pend = re.findall(r"\\newcommand\{\\(\w+)\}\{\[PEND\]\}", text)
    if still_pend:
        print(f"\nStill [PEND]:")
        for name in still_pend:
            print(f"  \\{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
