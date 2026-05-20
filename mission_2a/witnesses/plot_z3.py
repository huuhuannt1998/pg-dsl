"""Plot Z3 trajectory — LIT101 vs t with safe-operating band + overflow line.

Output: mission_2a/results/z3_trajectory.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"


def main() -> int:
    z = json.loads((RESULTS / "z3_trace.json").read_text())
    traj = z["runtime_trajectory"]["trajectory_LIT101"]
    band_lo, band_hi = z["calibration"]["safe_band"]
    overflow = z["calibration"]["overflow_threshold"]
    band_exit = z["runtime_trajectory"]["band_exit_step_s"]
    overflow_step = z["runtime_trajectory"]["overflow_step_s"]
    t = list(range(len(traj)))

    fig, ax = plt.subplots(figsize=(7, 4.2))

    # Safe-operating band (INVARLLM runtime)
    ax.add_patch(patches.Rectangle(
        (0, band_lo), len(traj) - 1, band_hi - band_lo,
        linewidth=0, alpha=0.15, color="green", label=f"INVARLLM safe band [{band_lo:g}, {band_hi:g}]",
    ))
    # Overflow predicate line
    ax.axhline(overflow, color="red", linestyle="--", linewidth=1.4,
               label=f"OVERFLOW_T101 (LIT101 ≥ {overflow:g})")

    ax.plot(t, traj, color="C0", linewidth=2.0, label="LIT101 trajectory")

    # Tool-call markers at t=0 and t=0 (both fired together)
    ax.scatter([0], [traj[0]], marker="v", s=80, color="black", zorder=5,
               label="t=0: open_valve_MV101 + start_pump_P101")

    # Band exit marker
    if band_exit is not None:
        ax.scatter([band_exit], [traj[band_exit]], marker="X", s=120,
                   color="darkorange", zorder=5,
                   label=f"band exit @ t={band_exit}s (INVARLLM fires)")
    if overflow_step is not None:
        ax.scatter([overflow_step], [traj[overflow_step]], marker="*", s=160,
                   color="red", zorder=5,
                   label=f"overflow @ t={overflow_step}s")

    ax.set_xlabel("Composition runtime t (s)")
    ax.set_ylabel("LIT101 (% full)")
    ax.set_title("Z3 — Transient Overshoot via Admitted-Tool Composition\n"
                 "PG-DSL admits each tool individually; runtime composition violates band")
    ax.set_xlim(0, len(traj) - 1)
    ax.set_ylim(20, 105)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95)

    out_path = RESULTS / "z3_trajectory.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
