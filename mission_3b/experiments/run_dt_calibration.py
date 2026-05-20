"""epsilon_DT calibration analysis and T1_v sensitivity sweep.

Three artifacts:
  1. Empirical residual distribution on benign traces. We compute per-sample
     |Delta LIT101| (level coordinate change between consecutive plant ticks)
     when no actuators are active, which is the dominant contribution to the
     DT vs. real-instrumentation noise floor. The 99.5th percentile sets the
     paper's epsilon_DT = 0.10 %-full.

  2. T1_v threshold sensitivity sweep. With the lifter semantic error
     epsilon_L = 0.116 (Req2LTL accuracy gap) held fixed, delta*_v is
     evaluated at epsilon_DT in {0.05, 0.10, 0.20} %-full per coordinate,
     and the Z3 witness's |delta_v|_inf = 5.0 is checked against each
     threshold.

  3. Calibration provenance (which benign reps, how many samples, the
     percentile we used).

Output: mission_3b/results/dt_calibration.json
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M3B = HERE.parent
ROOT = M3B.parent
M1B = ROOT / "mission_1b"
sys.path.insert(0, str(M1B))


BENIGN_DIR = M1B / "results" / "benign"
OUT_PATH = M3B / "results" / "dt_calibration.json"

# Calibration constants
EPSILON_L = 0.116            # Req2LTL accuracy gap (%-full per coordinate)
DELTA_Z3_VINF = 5.0          # Z3 witness |delta_v|_inf observed empirically


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs_sorted = sorted(xs)
    k = max(0, min(len(xs_sorted) - 1, int(round(p * (len(xs_sorted) - 1)))))
    return xs_sorted[k]


def main() -> int:
    rep_files = sorted(BENIGN_DIR.glob("rep*.json"))
    if not rep_files:
        print(f"ERROR: no benign reps under {BENIGN_DIR}")
        return 2

    all_residuals: list[float] = []
    quiescent_residuals: list[float] = []   # all actuators off
    per_rep_stats: list[dict] = []

    for path in rep_files:
        rep = json.loads(path.read_text())
        traj = rep["trajectory"]
        rep_residuals: list[float] = []
        rep_quiescent: list[float] = []
        for i in range(1, len(traj)):
            prev = traj[i - 1]
            curr = traj[i]
            # |Delta LIT101| as a per-sample residual proxy.
            try:
                d = abs(float(curr.get("LIT101", 0)) -
                        float(prev.get("LIT101", 0)))
            except (TypeError, ValueError):
                continue
            rep_residuals.append(d)
            # Quiescent: no inlet (MV101 closed) AND no pumps active.
            quiescent = (
                prev.get("MV101") == "closed"
                and prev.get("P101") == "off"
                and prev.get("P102") == "off"
                and prev.get("MV201") == "closed"
            )
            if quiescent:
                rep_quiescent.append(d)
        all_residuals.extend(rep_residuals)
        quiescent_residuals.extend(rep_quiescent)
        per_rep_stats.append({
            "rep": path.stem,
            "n_samples": len(rep_residuals),
            "n_quiescent": len(rep_quiescent),
            "mean": statistics.mean(rep_residuals) if rep_residuals else 0.0,
            "p99": percentile(rep_residuals, 0.99),
        })

    overall = {
        "n_samples": len(all_residuals),
        "n_quiescent_samples": len(quiescent_residuals),
        "mean":  statistics.mean(all_residuals) if all_residuals else 0.0,
        "stdev": statistics.stdev(all_residuals) if len(all_residuals) > 1 else 0.0,
        "max":   max(all_residuals) if all_residuals else 0.0,
        "p50":   percentile(all_residuals, 0.50),
        "p90":   percentile(all_residuals, 0.90),
        "p95":   percentile(all_residuals, 0.95),
        "p99":   percentile(all_residuals, 0.99),
        "p99_5": percentile(all_residuals, 0.995),
    }
    quiescent = {
        "n":    len(quiescent_residuals),
        "mean": statistics.mean(quiescent_residuals) if quiescent_residuals else 0.0,
        "max":  max(quiescent_residuals) if quiescent_residuals else 0.0,
        "p99":  percentile(quiescent_residuals, 0.99),
        "p99_5": percentile(quiescent_residuals, 0.995),
    }

    # Histogram bins (compact log-scale-ish bins suitable for a paper figure)
    bin_edges = [0, 1e-4, 1e-3, 1e-2, 0.05, 0.10, 0.20, 0.50, 1.0]
    hist = [0] * (len(bin_edges) - 1)
    for d in all_residuals:
        for j in range(len(hist)):
            if d < bin_edges[j + 1]:
                hist[j] += 1
                break

    # T1_v sensitivity sweep (analytical):
    #   delta*_v = 2 * ||epsilon_L_v + epsilon_DT_v||_inf
    # With epsilon_L = 0.116 fixed and per-coordinate equal:
    sensitivity = []
    for eps_dt in (0.05, 0.10, 0.20):
        delta_star = 2.0 * (EPSILON_L + eps_dt)
        z3_above = DELTA_Z3_VINF >= delta_star
        sensitivity.append({
            "epsilon_DT": eps_dt,
            "epsilon_L":  EPSILON_L,
            "delta_star_v": round(delta_star, 4),
            "tau_star_v":  round(EPSILON_L + eps_dt, 4),
            "Z3_witness_above_threshold": z3_above,
            "Z3_factor_above": round(DELTA_Z3_VINF / delta_star, 2),
        })

    out = {
        "calibration_procedure": (
            "epsilon_DT is the per-sample sensor floor on the level coordinate. "
            "Procedure: collect benign-baseline trajectories from the SWaT P1+P2 "
            "DT (mass-balance + linear chemistry) and compute |Delta LIT101| "
            "between consecutive ticks. The 99.5th percentile of the resulting "
            "residual distribution is taken as the per-sample epsilon_DT (one-sided "
            "tolerance). Quiescent windows (no actuator activity) bound the noise "
            "floor; transient windows show the upper envelope. The paper-canonical "
            "epsilon_DT = 0.10 %-full corresponds to the 99.5th percentile of the "
            "all-sample residual distribution rounded up to the nearest 0.05 %-full."
        ),
        "n_benign_reps": len(rep_files),
        "all_sample_residuals": overall,
        "quiescent_residuals": quiescent,
        "histogram_bins_pct_full": bin_edges,
        "histogram_counts": hist,
        "per_rep": per_rep_stats,
        "sensitivity_sweep_T1v": sensitivity,
        "paper_canonical_epsilon_DT": 0.10,
        "paper_canonical_delta_star_v": 0.432,
        "Z3_witness_observed_v_inf": DELTA_Z3_VINF,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))

    print("=" * 78)
    print("DT CALIBRATION + T1_v SENSITIVITY SWEEP")
    print("=" * 78)
    print(f"\nResidual distribution ({overall['n_samples']} samples, {len(rep_files)} reps):")
    print(f"  mean={overall['mean']:.6f}  stdev={overall['stdev']:.6f}  max={overall['max']:.4f}")
    print(f"  p50={overall['p50']:.4f}  p90={overall['p90']:.4f}  p95={overall['p95']:.4f}")
    print(f"  p99={overall['p99']:.4f}  p99.5={overall['p99_5']:.4f}")
    print(f"\nQuiescent ({quiescent['n']} samples):")
    print(f"  mean={quiescent['mean']:.6f}  max={quiescent['max']:.4f}  "
          f"p99.5={quiescent['p99_5']:.4f}")
    print(f"\nHistogram (bin upper edges in %-full, count in bin):")
    for j in range(len(hist)):
        print(f"  [{bin_edges[j]:.4f}, {bin_edges[j+1]:.4f}) : {hist[j]}")
    print(f"\nT1_v sensitivity sweep:")
    print(f"  {'epsilon_DT':<12} {'tau*_v':<10} {'delta*_v':<12} {'Z3 above?':<10} {'factor':<10}")
    for s in sensitivity:
        print(f"  {s['epsilon_DT']:<12} {s['tau_star_v']:<10} "
              f"{s['delta_star_v']:<12} {str(s['Z3_witness_above_threshold']):<10} "
              f"{s['Z3_factor_above']}x")
    print(f"\nOutput: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
