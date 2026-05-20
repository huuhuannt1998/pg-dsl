"""t1_v_verify.py --- Numerical verification harness for Theorem T1_v on the
two-tank tractable model (Mission 3A).

Mission: mis_01KR49N65QSX03VYGC9SSSF325.
Companion files: tractable_model_v.md, theorems.tex, results/.

What this script does (autonomous; T1_v statement comes from
jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ):
  * Implements the discrete-time two-tank DT integrator with per-coordinate
    bounded sensing error.
  * Implements a deterministic lifter mock for composition admission: each
    constituent tool lifts to a single-actuator clause; the effective
    admissible region per coordinate is supplied by the composition layer's
    safe operating band (A_eff(L_T101) = [25, 95], A_eff(L_T201) = [20, 95]).
  * Implements the vectorized matcher: per-coordinate δ̂_v[k] from the noisy
    trajectory, max-norm aggregation, fires iff ‖δ̂_v‖_∞ > τ*_v.
  * Runs a parameter sweep over ‖δ_v‖_∞ ∈ [0, δ_max] using a parametric
    overshoot injection on coordinate L_T101 (Z3-style composition attack
    family); records empirical detection rate.
  * Plots empirical curve vs. theoretical 1 - F_v(τ, ε_L_v, ε_DT_v) under
    bounded-error sensing (deterministic step at δ*_v = 2·τ*_v).
  * Writes the Z3 witness instance into the detected region of the curve.

CLI:
    python3 t1_v_verify.py
        --eps-L-v 0.116 0.116
        --eps-DT-v 0.10 0.10
        --c-matcher 1.0
        --c-theorem 2.0
        --horizon 30
        --n-trials 1000
        --out-plot results/detection_rate_plot_v.png
        --out-witness results/t1_v_witnesses.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Sequence

import numpy as np


# ---------------------------------------------------------------------------
# T1_v hyperparameters (per jrn_01KR4F6V8RD7YJJ55Z13JBMQXZ + Mission 3B)
# ---------------------------------------------------------------------------

EPS_L_V_DEFAULT  = (0.116, 0.116)   # Req2LTL accuracy gap, both coordinates
EPS_DT_V_DEFAULT = (0.10,  0.10)    # Mission 3B per-sample sensor floor
C_MATCHER        = 1.0              # τ*_v = c_m · ‖ε_v‖_∞
C_THEOREM        = 2.0              # δ*_v = c_t · ‖ε_v‖_∞ (= 2·τ*_v)

# Two-tank plant defaults (matching mission_3a/tractable_model_v.md §1)
Q_IN1     = 1.0      # %-full/s when V_in1=open ∧ P1=on
Q_COUPLE  = 0.4      # %-full/s when V_couple=open
Q_OUT2    = 0.3      # %-full/s when V_out2=open
DT        = 1.0      # s

SAFE_BAND_LIT101 = (25.0, 95.0)
SAFE_BAND_LIT201 = (20.0, 95.0)


# ---------------------------------------------------------------------------
# 1. Two-tank plant simulator (matches tractable_model_v.md §2-§3).
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class TwoTankParams:
    q_in1:    float = Q_IN1
    q_couple: float = Q_COUPLE
    q_out2:   float = Q_OUT2
    dt:       float = DT
    L_min:    float = 0.0
    L_max:    float = 100.0


def simulate_two_tank(L0: tuple[float, float],
                      v_in1: Sequence[bool],
                      p1:    Sequence[bool],
                      v_couple: Sequence[bool],
                      v_out2:   Sequence[bool],
                      params: TwoTankParams,
                      eps_DT_v: tuple[float, float],
                      rng: np.random.Generator,
                      extra_flow_t101: Sequence[float] | None = None,
                      ) -> tuple[np.ndarray, np.ndarray]:
    """Simulate the two-tank model.
    Returns (L_true: shape (T+1, 2), L_sensor: shape (T+1, 2)).

    `extra_flow_t101` (length T) is an injected continuous net flow on T101
    used to parameterize the attack magnitude. The Z3-family composition attack
    is a special case where v_in1 and p1 are forced True over the horizon and
    extra_flow is zero (pure visible composition).
    """
    T = len(v_in1)
    assert len(p1) == T == len(v_couple) == len(v_out2)
    if extra_flow_t101 is not None:
        assert len(extra_flow_t101) == T

    L_true = np.empty((T + 1, 2), dtype=float)
    L_sensor = np.empty((T + 1, 2), dtype=float)
    L_true[0]    = np.asarray(L0, dtype=float)
    L_sensor[0]  = L_true[0] + rng.uniform(
        [-eps_DT_v[0], -eps_DT_v[1]],
        [+eps_DT_v[0], +eps_DT_v[1]],
    )

    for k in range(T):
        # T101 dynamics
        in_t101 = (params.q_in1 if (v_in1[k] and p1[k]) else 0.0)
        out_t101 = (params.q_couple if (v_couple[k] and L_true[k, 0] > 0) else 0.0)
        flow_t101 = in_t101 - out_t101
        if extra_flow_t101 is not None:
            flow_t101 += extra_flow_t101[k]
        L_true[k + 1, 0] = float(np.clip(
            L_true[k, 0] + params.dt * flow_t101, params.L_min, params.L_max))

        # T201 dynamics
        in_t201 = (params.q_couple if (v_couple[k] and L_true[k, 0] > 0) else 0.0)
        out_t201 = (params.q_out2 if v_out2[k] else 0.0)
        flow_t201 = in_t201 - out_t201
        L_true[k + 1, 1] = float(np.clip(
            L_true[k, 1] + params.dt * flow_t201, params.L_min, params.L_max))

        L_sensor[k + 1] = L_true[k + 1] + rng.uniform(
            [-eps_DT_v[0], -eps_DT_v[1]],
            [+eps_DT_v[0], +eps_DT_v[1]],
        )

    return L_true, L_sensor


# ---------------------------------------------------------------------------
# 2. Vectorized matcher: per-coordinate δ̂_v from trajectory + safe bands.
# ---------------------------------------------------------------------------

def per_coord_distance(x: float, region: tuple[float, float] | None) -> float:
    """d(x, [a, b]) = max(0, x - b, a - x); d(x, ⊤) = 0."""
    if region is None:
        return 0.0
    a, b = region
    return max(0.0, x - b, a - x)


def vector_matcher(L_sensor: np.ndarray,
                   L_pred_pad: np.ndarray | None,
                   A_eff: tuple[tuple[float, float] | None,
                                tuple[float, float] | None],
                   eps_L_v: tuple[float, float],
                   tau_star_v: float,
                   rng: np.random.Generator) -> tuple[bool, np.ndarray]:
    """Compute per-coordinate δ̂_v from L_sensor and the effective admissible
    regions, then fire iff max-norm > τ*_v.

    L_pred_pad is a per-trajectory bias added to L_sensor to inject the lifter
    error ε_L_v (worst-case adversarial sign chosen via uniform sample). For
    the composition admission case the lifter contributes no level constraint
    directly; only the safe band A_eff matters. We still inject the per-coord
    ε_L_v noise to honor the bound's geometry (the lifter could in principle
    influence A_eff via a description that names a band).
    """
    T_plus = L_sensor.shape[0]
    L_eff = L_sensor.copy()
    if L_pred_pad is not None:
        L_eff = L_eff + L_pred_pad   # inject lifter bias (signed bounded)

    delta_v = np.zeros(2, dtype=float)
    for k_coord in range(2):
        for t in range(T_plus):
            d = per_coord_distance(float(L_eff[t, k_coord]), A_eff[k_coord])
            if d > delta_v[k_coord]:
                delta_v[k_coord] = d
    fired = float(delta_v.max()) > tau_star_v
    return fired, delta_v


# ---------------------------------------------------------------------------
# 3. Composition attack family — parametric ‖δ_v‖_∞ on T101.
#
# The attack: at t=0 the agent issues the ordered pair (open V_in1, on P1)
# producing visible inflow rate q_in1 = 1.0 %-full/s. To parametrize the
# eventual peak overshoot beyond the safe band [25, 95], we modulate via
# (a) the initial level L_T101_init and (b) an additional injected
# inflow rate that scales linearly with the desired peak overshoot. This
# lets us sweep ‖δ_v‖_∞ continuously from 0 to ~6 %-full while preserving
# the composition-attack character (both V_in1 and P1 visibly open during
# admission).
# ---------------------------------------------------------------------------

def composition_attack_schedule(horizon: int, params: TwoTankParams,
                                L0: tuple[float, float],
                                target_peak_t101: float,
                                v_couple_open: bool = False,
                                v_out2_open: bool = False
                                ) -> tuple[list[bool], list[bool], list[bool], list[bool], np.ndarray]:
    """Build the attack schedule + extra_flow s.t. T101 peak ≈ target_peak_t101.

    Both V_in1 and P1 are open over the entire horizon (the composed admitted
    pair). V_couple is closed (no T101→T201 outflow). V_out2 is open (T201
    drains so it cannot saturate; this preserves the per-coord behavior on T201
    in band).

    Net visible inflow on T101: q_in1 = 1.0 %-full/s (with V_couple closed).
    Without extra flow, T101 saturates at 100 in (100 - L0) seconds.

    To target a precise peak below 100, we inject a negative extra flow that
    cancels the visible inflow once L_T101 reaches the target peak. The
    decision is made off the *true* level (so the schedule is deterministic
    in the true plant; the observer's noisy reading does not affect the
    schedule).
    """
    v_in1   = [True] * horizon
    p1      = [True] * horizon
    v_couple = [v_couple_open] * horizon
    v_out2   = [v_out2_open] * horizon

    # Pre-compute the saturation profile if no extra flow.
    L = float(L0[0])
    extra = np.zeros(horizon, dtype=float)
    for k in range(horizon):
        if L >= target_peak_t101:
            # Once at peak, cancel the visible inflow (extra_flow = -q_in1)
            extra[k] = -params.q_in1
            L = L     # held at peak
        else:
            L = min(target_peak_t101, L + params.dt * params.q_in1)
    return v_in1, p1, v_couple, v_out2, extra


# ---------------------------------------------------------------------------
# 4. Detection-rate sweep.
# ---------------------------------------------------------------------------

def detection_rate_curve(target_peaks: np.ndarray,
                         L0: tuple[float, float],
                         horizon: int,
                         params: TwoTankParams,
                         eps_L_v: tuple[float, float],
                         eps_DT_v: tuple[float, float],
                         tau_star_v: float,
                         n_trials: int,
                         rng_seed: int) -> tuple[np.ndarray, np.ndarray]:
    """For each target_peak, run n_trials and return:
        - detection_rate per peak
        - achieved_norm_inf per peak (mean over trials)
    """
    rng = np.random.default_rng(rng_seed)
    rates = np.empty_like(target_peaks, dtype=float)
    norms = np.empty_like(target_peaks, dtype=float)

    A_eff = (SAFE_BAND_LIT101, SAFE_BAND_LIT201)

    for i, peak in enumerate(target_peaks):
        v_in1, p1, v_couple, v_out2, extra = composition_attack_schedule(
            horizon=horizon, params=params, L0=L0,
            target_peak_t101=float(peak),
            v_couple_open=False, v_out2_open=False,
        )
        fires = 0
        norm_acc = 0.0
        for _ in range(n_trials):
            _, L_sensor = simulate_two_tank(
                L0=L0, v_in1=v_in1, p1=p1,
                v_couple=v_couple, v_out2=v_out2,
                params=params, eps_DT_v=eps_DT_v, rng=rng,
                extra_flow_t101=extra,
            )
            # Lifter bias: per-coord uniform within ε_L_v[k] applied to
            # the noisy sensor read (worst-case adversarial sign chosen at
            # random, as per Mission 1A's t1_verify lifter-error injection).
            T_plus = L_sensor.shape[0]
            lifter_bias = rng.uniform(
                low=[-eps_L_v[0], -eps_L_v[1]],
                high=[+eps_L_v[0], +eps_L_v[1]],
                size=(T_plus, 2),
            )
            fired, delta_v = vector_matcher(
                L_sensor=L_sensor, L_pred_pad=lifter_bias,
                A_eff=A_eff, eps_L_v=eps_L_v,
                tau_star_v=tau_star_v, rng=rng,
            )
            fires += int(fired)
            norm_acc += float(delta_v.max())
        rates[i] = fires / n_trials
        norms[i] = norm_acc / n_trials

    return rates, norms


# ---------------------------------------------------------------------------
# 5. Plot & witness export.
# ---------------------------------------------------------------------------

def f_v_step_bounded_error(tau: float, eps_L_v: Sequence[float],
                            eps_DT_v: Sequence[float],
                            c_theorem: float = C_THEOREM) -> float:
    eps_v = max(eps_L_v[k] + eps_DT_v[k] for k in range(len(eps_L_v)))
    delta_star_v = c_theorem * eps_v
    return 1.0 if tau < delta_star_v else 0.0


def plot_curve(achieved_norms: np.ndarray, empirical: np.ndarray,
               eps_L_v: tuple[float, float], eps_DT_v: tuple[float, float],
               tau_star_v: float, delta_star_v: float, out_path: Path,
               z3_witness: dict | None = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Theoretical curve over the same x-grid
    theoretical = np.array([
        1.0 - f_v_step_bounded_error(d, eps_L_v, eps_DT_v) for d in achieved_norms
    ])

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(achieved_norms, empirical, marker="o", linestyle="-",
            color="#1f77b4",
            label=r"Empirical (two-tank DT, composition attack)")
    ax.plot(achieved_norms, theoretical, linestyle="--", color="#d62728",
            label=r"Theoretical $1 - F_v$ (bounded-error step)")
    ax.axvline(tau_star_v, color="#888", linestyle=":", alpha=0.7,
               label=rf"matcher $\tau^*_v = \|\varepsilon_v\|_\infty = {tau_star_v:.3f}$")
    ax.axvline(delta_star_v, color="#d62728", linestyle=":", alpha=0.7,
               label=rf"theorem $\delta^*_v = 2\tau^*_v = {delta_star_v:.3f}$")
    if z3_witness is not None:
        z3_x = z3_witness["norm_inf_actual_saturation"]
        ax.scatter([z3_x], [1.0], marker="*", s=220, color="green", zorder=5,
                   label=fr"Z3 witness: $\|\delta_v\|_\infty = {z3_x:.2f}$ (detected)")
    ax.set_xlabel(r"Vectorized attack magnitude $\|\delta_v\|_\infty$ (\%-full)")
    ax.set_ylabel(r"Detection probability $\Pr(\mathrm{detect})$")
    ax.set_title(
        r"PG-DSL T1$_v$ detection rate on the two-tank tractable model"
        "\n"
        rf"$\varepsilon_{{L,v}}={eps_L_v}$, $\varepsilon_{{DT,v}}={eps_DT_v}$, "
        rf"$\tau^*_v={tau_star_v:.3f}$, $\delta^*_v={delta_star_v:.3f}$"
    )
    ax.set_ylim(-0.02, 1.05)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", framealpha=0.95, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def z3_witness_run(L0_z3: tuple[float, float],
                   horizon_z3: int,
                   params: TwoTankParams,
                   eps_L_v: tuple[float, float],
                   eps_DT_v: tuple[float, float],
                   tau_star_v: float,
                   n_trials: int,
                   rng_seed: int) -> dict:
    """Run the canonical Z3 witness: composition pair (V_in1=open, P1=on) from
    LIT101=90 with V_couple=closed, V_out2=closed. Horizon 30s. No extra
    flow injection (pure composition). Record empirical detection rate +
    achieved ‖δ_v‖_∞ + per-coord δ_v.
    """
    rng = np.random.default_rng(rng_seed)
    A_eff = (SAFE_BAND_LIT101, SAFE_BAND_LIT201)
    v_in1   = [True] * horizon_z3
    p1      = [True] * horizon_z3
    v_couple = [False] * horizon_z3
    v_out2   = [False] * horizon_z3

    fires = 0
    delta_acc = np.zeros(2, dtype=float)
    norm_inf_acc = 0.0
    for _ in range(n_trials):
        L_true, L_sensor = simulate_two_tank(
            L0=L0_z3, v_in1=v_in1, p1=p1,
            v_couple=v_couple, v_out2=v_out2,
            params=params, eps_DT_v=eps_DT_v, rng=rng,
            extra_flow_t101=None,
        )
        T_plus = L_sensor.shape[0]
        lifter_bias = rng.uniform(
            low=[-eps_L_v[0], -eps_L_v[1]],
            high=[+eps_L_v[0], +eps_L_v[1]],
            size=(T_plus, 2),
        )
        fired, delta_v = vector_matcher(
            L_sensor=L_sensor, L_pred_pad=lifter_bias,
            A_eff=A_eff, eps_L_v=eps_L_v,
            tau_star_v=tau_star_v, rng=rng,
        )
        fires += int(fired)
        delta_acc += delta_v
        norm_inf_acc += float(delta_v.max())

    detection_rate = fires / n_trials
    delta_v_mean = (delta_acc / n_trials).tolist()
    norm_inf_mean = norm_inf_acc / n_trials

    # The TRUE-plant peak overshoot under the canonical Z3 trajectory:
    # from L0 = 90 with q_in1 = 1.0 over horizon=30, L_true reaches
    # min(100, 90 + 30) = 100 (saturated) — δ_true = 100 - 95 = 5.0
    # %-full. Mission 3B reports 4.5 (using overflow-edge predicate
    # 99.5); we use saturation here. We report both.
    L_true_peak = max(min(100.0, L0_z3[0] + horizon_z3 * Q_IN1), L0_z3[0])
    delta_true_t101 = max(0.0, L_true_peak - SAFE_BAND_LIT101[1])

    return {
        "L0": list(L0_z3),
        "horizon_s": horizon_z3,
        "tool_pair": ["open_valve_MV101", "start_pump_P101"],
        "v_couple": "closed",
        "v_out2": "closed",
        "n_trials": n_trials,
        "detection_rate_empirical": detection_rate,
        "delta_v_mean_per_coord": delta_v_mean,
        "norm_inf_mean": norm_inf_mean,
        "delta_v_actual_t101_saturation": delta_true_t101,
        "delta_v_actual_t201": 0.0,
        "norm_inf_actual_saturation": delta_true_t101,
        "tau_star_v": tau_star_v,
        "delta_star_v_threshold": 2.0 * tau_star_v,
        "in_detected_region_under_T1_v": delta_true_t101 >= 2.0 * tau_star_v,
        "ratio_delta_to_threshold": delta_true_t101 / (2.0 * tau_star_v) if tau_star_v > 0 else float("inf"),
    }


def witness_pairs(eps_L_v: tuple[float, float],
                  eps_DT_v: tuple[float, float],
                  c_theorem: float = C_THEOREM) -> list[dict]:
    """Two analytic witness instances:
      - F_v < 1: τ above δ*_v (provably detectable)
      - F_v ≡ 1: τ below δ*_v (provably undetectable)
    """
    delta_star_v = c_theorem * max(eps_L_v[k] + eps_DT_v[k] for k in range(2))
    detectable_tau   = 5 * delta_star_v
    undetectable_tau = 0.5 * delta_star_v
    return [
        {
            "label": "F_v=0 (provably detectable)",
            "tau": detectable_tau,
            "eps_L_v": list(eps_L_v),
            "eps_DT_v": list(eps_DT_v),
            "tau_star_v": delta_star_v / c_theorem,
            "delta_star_v": delta_star_v,
            "F_v_value": f_v_step_bounded_error(detectable_tau, eps_L_v, eps_DT_v, c_theorem),
            "interpretation": "tau >= delta*_v; F_v=0; Pr(detect) >= 1 under any bounded-error noise",
        },
        {
            "label": "F_v=1 (provably undetectable / impossibility region)",
            "tau": undetectable_tau,
            "eps_L_v": list(eps_L_v),
            "eps_DT_v": list(eps_DT_v),
            "tau_star_v": delta_star_v / c_theorem,
            "delta_star_v": delta_star_v,
            "F_v_value": f_v_step_bounded_error(undetectable_tau, eps_L_v, eps_DT_v, c_theorem),
            "interpretation": "tau < delta*_v; F_v=1; theorem provides no detection guarantee",
        },
    ]


# ---------------------------------------------------------------------------
# 6. CLI.
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--eps-L-v", type=float, nargs=2,
                        default=list(EPS_L_V_DEFAULT),
                        help="Per-coordinate worst-case lifter error vector")
    parser.add_argument("--eps-DT-v", type=float, nargs=2,
                        default=list(EPS_DT_V_DEFAULT),
                        help="Per-coordinate per-sample DT fidelity error vector")
    parser.add_argument("--c-matcher", type=float, default=C_MATCHER)
    parser.add_argument("--c-theorem", type=float, default=C_THEOREM)
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--L0", type=float, nargs=2, default=[90.0, 60.0],
                        help="Initial (L_T101, L_T201) for the sweep family")
    parser.add_argument("--n-trials", type=int, default=500)
    parser.add_argument("--n-peaks", type=int, default=40,
                        help="Number of target_peak values (sweep resolution)")
    parser.add_argument("--peak-min", type=float, default=92.0)
    parser.add_argument("--peak-max", type=float, default=99.5)
    parser.add_argument("--rng-seed", type=int, default=42)
    parser.add_argument("--out-plot", type=Path,
                        default=Path("results/detection_rate_plot_v.png"))
    parser.add_argument("--out-witness", type=Path,
                        default=Path("results/t1_v_witnesses.json"))
    args = parser.parse_args()

    eps_L_v = tuple(args.eps_L_v)
    eps_DT_v = tuple(args.eps_DT_v)
    eps_v_inf = max(eps_L_v[k] + eps_DT_v[k] for k in range(2))
    tau_star_v = args.c_matcher * eps_v_inf
    delta_star_v = args.c_theorem * eps_v_inf

    params = TwoTankParams()
    target_peaks = np.linspace(args.peak_min, args.peak_max, args.n_peaks)

    rates, norms = detection_rate_curve(
        target_peaks=target_peaks,
        L0=tuple(args.L0),
        horizon=args.horizon,
        params=params,
        eps_L_v=eps_L_v, eps_DT_v=eps_DT_v,
        tau_star_v=tau_star_v,
        n_trials=args.n_trials,
        rng_seed=args.rng_seed,
    )

    z3 = z3_witness_run(
        L0_z3=(90.0, 60.0), horizon_z3=30, params=params,
        eps_L_v=eps_L_v, eps_DT_v=eps_DT_v,
        tau_star_v=tau_star_v,
        n_trials=args.n_trials,
        rng_seed=args.rng_seed,
    )

    args.out_plot.parent.mkdir(parents=True, exist_ok=True)
    plot_curve(
        achieved_norms=norms, empirical=rates,
        eps_L_v=eps_L_v, eps_DT_v=eps_DT_v,
        tau_star_v=tau_star_v, delta_star_v=delta_star_v,
        out_path=args.out_plot,
        z3_witness=z3,
    )

    pairs = witness_pairs(eps_L_v, eps_DT_v, args.c_theorem)
    args.out_witness.parent.mkdir(parents=True, exist_ok=True)
    args.out_witness.write_text(json.dumps({
        "eps_L_v": list(eps_L_v),
        "eps_DT_v": list(eps_DT_v),
        "c_matcher": args.c_matcher,
        "c_theorem": args.c_theorem,
        "tau_star_v": tau_star_v,
        "delta_star_v": delta_star_v,
        "z3_witness_run": z3,
        "analytic_witness_pairs": pairs,
        "sweep": {
            "target_peaks": target_peaks.tolist(),
            "achieved_norms_inf_mean": norms.tolist(),
            "empirical_detection_rates": rates.tolist(),
        },
    }, indent=2))

    print(f"τ*_v = {tau_star_v:.4f}, δ*_v = {delta_star_v:.4f}")
    print(f"Z3: ‖δ_v‖_∞_actual_saturation = {z3['norm_inf_actual_saturation']:.3f}, "
          f"detection_rate_empirical = {z3['detection_rate_empirical']:.3f}, "
          f"in_detected_region = {z3['in_detected_region_under_T1_v']}")
    print(f"sweep min/max norm_inf = [{norms.min():.3f}, {norms.max():.3f}]")
    print(f"sweep min/max rate     = [{rates.min():.3f}, {rates.max():.3f}]")
    print(f"plot   -> {args.out_plot}")
    print(f"witnesses -> {args.out_witness}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
