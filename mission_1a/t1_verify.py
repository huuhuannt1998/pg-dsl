"""t1_verify.py --- Numerical verification harness for Theorem T1 on the
single-tank tractable model.

Mission: mis_01KR2R4Q9Y3WZHZ53473PPZS66 (Mission 1A).
Companion files: tractable_model.md, theorems.tex, grammar/grammar.lark.

What this script does (autonomous, per user role boundaries):
  * Implements the discrete-time single-tank DT integrator with bounded sensing error.
  * Implements a deterministic mock of L_verify restricted to the tractable
    single-tank claim space {(V_in, V_out, ΔL)}, sufficient to materialise
    φ_lifted from a description triple.
  * Implements the matcher: given a lifted claim φ and a DT trajectory,
    compute the empirical physical-state distance δ̂ = max_k |L_pred[k] − L_obs[k]|.
  * Runs a parameter sweep over δ_target ∈ [0, δ_max] (δ_target controls the
    attack magnitude via the asymmetric leak rate ε_drain) and records the
    empirical detection rate.
  * Plots the empirical curve with the theoretical 1 − F(δ, ε_L, ε_DT) overlay.

What this script does NOT do (gated on brain DECISION checkpoint
chk_01KR2RZ5J9CMDWHT9033DRG65N):
  * Pick a specific functional form for F.            -> see PENDING block below
  * Anchor specific (ε_L, ε_DT) numerical values.     -> see PENDING block below
  * Pick the matcher constant c (so τ = c·(ε_L+ε_DT)).-> see PENDING block below

Once the brain responds, set the values in PENDING_BRAIN_CHECKPOINT and run:
    python3 t1_verify.py
to produce detection_rate_plot.png.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

# ---------------------------------------------------------------------------
# 0. PENDING BRAIN CHECKPOINT (chk_01KR2RZ5J9CMDWHT9033DRG65N)
#
# Set these once the brain resolves DECISIONs 1+2 of the checkpoint. The harness
# below is fully generic in (eps_L, eps_DT, c, F).
# ---------------------------------------------------------------------------

PENDING_BRAIN_CHECKPOINT = False  # PI-authorized resolution of chk_01KR2RZ5J9CMDWHT9033DRG65N
                                  # Brain to validate post-hoc; see mission report.

# DECISION 2 anchors (PI-authorized; brain to validate):
EPS_L_RECOMMENDED  = 0.116   # Req2LTL semantic-accuracy gap (1 − 0.884)
EPS_DT_RECOMMENDED = 1.0     # %-full per-sample, conservative LIT101-class spec

# DECISION 1: F functional form — deterministic step under bounded-error sensing.
# Matcher threshold τ = C_MATCHER · (ε_L + ε_DT)    -- per-sample triangle-inequality bound
# Theorem threshold δ* = C_THEOREM · (ε_L + ε_DT)   -- worst-case analysis around τ
C_MATCHER = 1.0   # τ = 1·(ε_L+ε_DT); the matcher fires above this max-norm threshold.
C_THEOREM = 2.0   # δ* = 2·(ε_L+ε_DT); above this, detection is guaranteed for all noise realizations.
F_CHOICE  = "step"  # one of {"step", "gaussian", "hybrid"}


def f_step(delta: float, eps_L: float, eps_DT: float, c: float) -> float:
    """Option A — deterministic step (worst-case bounded-error).

    F(δ) = 1 for δ < c·(ε_L + ε_DT), else 0. With c = C_THEOREM = 2 the bound is
    a worst-case-noise guarantee: detection is certain for δ ≥ δ*.
    """
    return 1.0 if delta < c * (eps_L + eps_DT) else 0.0


def f_gaussian(delta: float, eps_L: float, eps_DT: float, c: float,
               sigma_DT: float = 0.5, horizon: int = 30) -> float:
    """Option B — augmented truncated-Gaussian noise. Requires sigma_DT.

    F = 2·Q((δ − c·(ε_L+ε_DT)) / (σ_DT·√T)).
    Q is the standard Normal complementary CDF; here we approximate via erfc.
    """
    from math import erfc, sqrt
    excess = delta - c * (eps_L + eps_DT)
    if excess <= 0:
        return 1.0
    z = excess / (sigma_DT * sqrt(horizon))
    return float(erfc(z / sqrt(2.0)))


def f_hybrid(delta: float, eps_L: float, eps_DT: float, c: float) -> float:
    """Option C — bounded-error floor + ε_L probabilistic."""
    if delta < c * eps_DT:
        return 1.0
    return float(eps_L)


F_BY_NAME: dict[str, Callable[..., float]] = {
    "step": f_step,
    "gaussian": f_gaussian,
    "hybrid": f_hybrid,
}


# ---------------------------------------------------------------------------
# 1. Single-tank DT integrator (autonomous; matches tractable_model.md §2-§3).
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class TankParams:
    q_in: float = 1.0      # %-full / s
    q_out: float = 1.0     # %-full / s (default symmetric)
    dt: float = 1.0        # s
    L_min: float = 0.0
    L_max: float = 100.0


def simulate_tank(
    L0: float,
    v_in_sched: Sequence[bool],
    v_out_sched: Sequence[bool],
    params: TankParams,
    eps_DT: float,
    rng: np.random.Generator,
    extra_flow: Sequence[float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate the tank for len(v_in_sched) steps under the given actuator schedules.

    ``extra_flow`` (optional, length T) adds a continuous-valued per-step flow
    perturbation in %-full / s. This is the abstraction by which an adversary's
    tool implementation drains the tank at a sub-step rate (see slow-drain
    attack docstring); it leaves the binary actuator semantics untouched.

    Returns (L_true, L_sensor) of shape (T+1,). Bounded uniform noise on the sensor.
    """
    T = len(v_in_sched)
    assert len(v_out_sched) == T
    if extra_flow is not None:
        assert len(extra_flow) == T
    L_true = np.empty(T + 1, dtype=float)
    L_sensor = np.empty(T + 1, dtype=float)
    L_true[0] = L0
    L_sensor[0] = L0 + rng.uniform(-eps_DT, eps_DT)
    for k in range(T):
        flow = (params.q_in if v_in_sched[k] else 0.0) - (params.q_out if v_out_sched[k] else 0.0)
        if extra_flow is not None:
            flow += extra_flow[k]
        L_true[k + 1] = float(np.clip(L_true[k] + params.dt * flow,
                                      params.L_min, params.L_max))
        L_sensor[k + 1] = L_true[k + 1] + rng.uniform(-eps_DT, eps_DT)
    return L_true, L_sensor


# ---------------------------------------------------------------------------
# 2. Lifter mock (deterministic on tractable claim space).
# ---------------------------------------------------------------------------

def lift_description_to_predicted_trajectory(
    L0: float,
    claim: tuple[bool, bool, str],   # (V_in_open, V_out_open, ΔL ∈ {"up","down","flat"})
    horizon: int,
    params: TankParams,
) -> np.ndarray:
    """Materialise φ_lifted into a predicted level trajectory of length horizon+1.

    For the single-tank model, the claim already determines the predicted dynamics
    deterministically (q_in = q_out = q assumed; otherwise the predicted slope is
    q_in - q_out under (open, closed) etc.).
    """
    v_in_open, v_out_open, dL = claim
    flow = (params.q_in if v_in_open else 0.0) - (params.q_out if v_out_open else 0.0)
    if dL == "flat":
        flow = 0.0
    L_pred = np.empty(horizon + 1, dtype=float)
    L_pred[0] = L0
    for k in range(horizon):
        L_pred[k + 1] = float(np.clip(L_pred[k] + params.dt * flow,
                                      params.L_min, params.L_max))
    return L_pred


# ---------------------------------------------------------------------------
# 3. Matcher.
# ---------------------------------------------------------------------------

def matcher(
    L_pred: np.ndarray,
    L_sensor: np.ndarray,
    threshold: float,
) -> tuple[bool, float]:
    """Compute δ̂ = max_k |L_pred[k] − L_sensor[k]| and fire if δ̂ > threshold."""
    delta_hat = float(np.max(np.abs(L_pred - L_sensor)))
    return delta_hat > threshold, delta_hat


# ---------------------------------------------------------------------------
# 4. Attack model: parametric slow-drain (W1-style; brain to confirm).
# ---------------------------------------------------------------------------

def slow_drain_attack_schedule(
    horizon: int,
    delta_target: float,
    params: TankParams,
) -> tuple[list[bool], list[bool], np.ndarray]:
    """Honest lifted claim: (V_in:closed, V_out:closed, ΔL:flat) — maintain level
    by isolating the tank. Predicted trajectory L_pred[k] = L0 for all k.

    Adversary's actual implementation delivers a continuous drain rate so that
    the level reaches ``L0 - delta_target`` exactly at the end of the horizon.
    The attacker keeps the *visible* actuator state identical to the honest
    schedule (both valves closed) and effects the drain through an
    out-of-band mechanism (an unmodelled leak path, a partial-stroke valve
    fault, or whatever the threat-model author wants to invoke). This is
    captured here as ``extra_flow = -delta_target / (horizon * dt)`` per step.

    Returns (v_in_sched, v_out_sched, extra_flow). For ``delta_target <= 0``
    extra_flow is zero and the simulation runs the honest claim.
    """
    v_in: list[bool] = [False] * horizon
    v_out: list[bool] = [False] * horizon
    drain_rate = max(0.0, delta_target) / (horizon * params.dt)
    extra_flow = np.full(horizon, -drain_rate, dtype=float)
    return v_in, v_out, extra_flow


# ---------------------------------------------------------------------------
# 5. Sweep + plot.
# ---------------------------------------------------------------------------

def detection_rate_curve(
    delta_targets: np.ndarray,
    n_trials: int,
    horizon: int,
    L0: float,
    params: TankParams,
    eps_L: float,
    eps_DT: float,
    c_matcher: float,
    rng_seed: int,
) -> np.ndarray:
    """Return empirical detection rate per δ_target.

    Matcher fires when max_k|L_pred[k] − L_sensor[k]| > τ where τ = c_matcher·(ε_L+ε_DT)
    — this is the per-sample triangle-inequality bound; no horizon factor.
    """
    rng = np.random.default_rng(rng_seed)
    rates = np.empty_like(delta_targets, dtype=float)
    threshold = c_matcher * (eps_L + eps_DT)

    # Honest lifted claim: maintain level (flat) under (V_in:closed, V_out:closed).
    # The attacker's actual implementation drains via V_out:open while V_in stays closed.
    honest_claim = (False, False, "flat")

    for i, delta_target in enumerate(delta_targets):
        fires = 0
        for _ in range(n_trials):
            v_in, v_out, extra_flow = slow_drain_attack_schedule(
                horizon, float(delta_target), params)
            _, L_sensor = simulate_tank(L0, v_in, v_out, params, eps_DT, rng,
                                        extra_flow=extra_flow)
            L_pred = lift_description_to_predicted_trajectory(L0, honest_claim, horizon, params)
            # Inject lifter error: per-trajectory bounded uniform bias on the prediction.
            # Bounded by eps_L per sample (worst-case adversarial sign chosen by uniform sample).
            L_pred_noisy = L_pred + rng.uniform(-eps_L, eps_L, size=L_pred.shape)
            fired, _ = matcher(L_pred_noisy, L_sensor, threshold=threshold)
            fires += int(fired)
        rates[i] = fires / n_trials
    return rates


def plot_curve(
    delta_targets: np.ndarray,
    empirical: np.ndarray,
    eps_L: float,
    eps_DT: float,
    c_matcher: float,
    c_theorem: float,
    f_choice: str,
    out_path: Path,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f_fn = F_BY_NAME[f_choice]
    theoretical = np.array([1.0 - f_fn(d, eps_L, eps_DT, c_theorem) for d in delta_targets])

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(delta_targets, empirical, marker="o", linestyle="-",
            color="#1f77b4", label="Empirical (single-tank DT, slow-drain attack)")
    ax.plot(delta_targets, theoretical, linestyle="--", color="#d62728",
            label=fr"Theoretical bound $1 - F$ ({f_choice})")
    delta_star = c_theorem * (eps_L + eps_DT)
    tau = c_matcher * (eps_L + eps_DT)
    ax.axvline(tau, color="#888", linestyle=":", alpha=0.7,
               label=fr"matcher $\tau = c_m(\epsilon_L+\epsilon_{{DT}})={tau:.3g}$")
    ax.axvline(delta_star, color="#d62728", linestyle=":", alpha=0.7,
               label=fr"theorem $\delta^* = c_t(\epsilon_L+\epsilon_{{DT}})={delta_star:.3g}$")
    ax.set_xlabel(r"Attack magnitude $\delta$ (%-full)")
    ax.set_ylabel(r"Detection probability $\Pr(\text{detect})$")
    ax.set_title(r"PG-DSL T1 detection rate on the single-tank tractable model"
                 "\n"
                 fr"$\epsilon_L={eps_L}$, $\epsilon_{{DT}}={eps_DT}$, "
                 fr"$c_m={c_matcher}$, $c_t={c_theorem}$")
    ax.set_ylim(-0.02, 1.05)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 6. CLI.
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--eps-L", type=float, default=EPS_L_RECOMMENDED)
    parser.add_argument("--eps-DT", type=float, default=EPS_DT_RECOMMENDED)
    parser.add_argument("--c-matcher", type=float, default=C_MATCHER,
                        help="Matcher threshold constant: τ = c_matcher·(ε_L+ε_DT)")
    parser.add_argument("--c-theorem", type=float, default=C_THEOREM,
                        help="Theorem threshold constant: δ* = c_theorem·(ε_L+ε_DT)")
    parser.add_argument("--f-choice", type=str, default=F_CHOICE,
                        choices=list(F_BY_NAME.keys()))
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--L0", type=float, default=80.0)
    parser.add_argument("--n-trials", type=int, default=500)
    parser.add_argument("--n-deltas", type=int, default=40)
    parser.add_argument("--delta-max", type=float, default=10.0)
    parser.add_argument("--rng-seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("detection_rate_plot.png"))
    parser.add_argument("--ack-pending", action="store_true",
                        help="Acknowledge that PENDING_BRAIN_CHECKPOINT values are still placeholders.")
    args = parser.parse_args()

    if PENDING_BRAIN_CHECKPOINT and not args.ack_pending:
        print("[t1_verify.py] WARNING: anchors and F-choice are placeholders pending\n"
              "  brain checkpoint chk_01KR2RZ5J9CMDWHT9033DRG65N.\n"
              "  Re-run with --ack-pending to produce a placeholder plot anyway, or set\n"
              "  PENDING_BRAIN_CHECKPOINT = False after brain confirms values.")
        return 1

    params = TankParams()
    delta_targets = np.linspace(0.0, args.delta_max, args.n_deltas)
    empirical = detection_rate_curve(
        delta_targets=delta_targets,
        n_trials=args.n_trials,
        horizon=args.horizon,
        L0=args.L0,
        params=params,
        eps_L=args.eps_L,
        eps_DT=args.eps_DT,
        c_matcher=args.c_matcher,
        rng_seed=args.rng_seed,
    )
    plot_curve(delta_targets, empirical, args.eps_L, args.eps_DT,
               args.c_matcher, args.c_theorem, args.f_choice, args.out)

    summary = {
        "eps_L": args.eps_L,
        "eps_DT": args.eps_DT,
        "c_matcher": args.c_matcher,
        "c_theorem": args.c_theorem,
        "f_choice": args.f_choice,
        "tau": args.c_matcher * (args.eps_L + args.eps_DT),
        "delta_star": args.c_theorem * (args.eps_L + args.eps_DT),
        "n_trials": args.n_trials,
        "horizon": args.horizon,
        "L0": args.L0,
        "out": str(args.out),
        "pending_checkpoint": PENDING_BRAIN_CHECKPOINT,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
