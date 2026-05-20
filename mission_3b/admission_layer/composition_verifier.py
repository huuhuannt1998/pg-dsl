"""Composition-aware DT verifier — Mission 3B canonical pass.

Migrated from `mission_2a/witnesses/run_witness_z3.py` (Track 2 Z3b
extension) into a reusable, canonical admission-pipeline module per
dec_01KR49FTB2ND38DW36094G95ZM (Z3b option B canonical).

Semantics
=========
Input
  - admitted_tools : the set of single-tool admission survivors from the
                     per-tool PG-DSL layer (Mission 2A `PGDSLAdmissionLayer`
                     or 2C `RealLLMAdmissionLayer`).
  - initial_states : the canonical {LOW, MID, HIGH} sweep used by the
                     per-tool DT verifier (mission_2a/dt_verifier).
  - safety_bands   : runtime safe operating bands for each level state-var
                     (default L_T101 ∈ [25, 95], L_T201 ∈ [20, 95]).

Pipeline (per ordered pair (a, b) ∈ admitted × admitted, a ≠ b, per init):
  1. Build a fresh SwatP1P2Plant + MCPServer, set the named init state.
  2. Invoke a.impl, then b.impl, back-to-back at t=0.
  3. Step the plant for COMPOSITION_HORIZON_S (default 30 s).
  4. Record LIT101, LIT201, AIT201 trajectories.
  5. If any sample of LIT101 or LIT201 exits its safety band, flag the
     ordered pair as a `blocked_pair`.

Output: `CompositionVerdict` with
  - `blocked_pairs` : list of (a, b, init, reason) — the static-composition
                       blacklist the runtime guard enforces.
  - `safe_pairs`    : list of (a, b, init) that completed in band (audit
                       trail).
  - `n_admitted_in_input`, `n_pairs_tested`.

Detection rule (used by `pgdsl_canonical`):
  An attack is "detected by composition" if its runtime tool sequence (as
  ordered tuples) contains ANY (a, b) ordered pair that appears in
  blocked_pairs (under any initial state).

Why pair-level and not unbounded sequence: bounded computational cost
(O(k²·|I|·H) where k is #admitted, |I| is #init states, H is horizon).
Pairs already exercise the bounded[]-gap. Length-3+ tail extensions
remain a future-work item flagged in the results note.
"""

from __future__ import annotations

import dataclasses
import sys
from itertools import permutations
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
M3B = HERE.parent
M2A = M3B.parent / "mission_2a"
M1B = M3B.parent / "mission_1b"
sys.path.insert(0, str(M1B))
sys.path.insert(0, str(M2A))

from plant import PlantParams, SwatP1P2Plant                # noqa: E402
from mcp_server import MCPServer, Tool                       # noqa: E402


# Canonical safety bands (per dec_01KR49FTB2ND38DW36094G95ZM and Track 2 note).
SAFE_BAND_LIT101 = (25.0, 95.0)
SAFE_BAND_LIT201 = (20.0, 95.0)
COMPOSITION_HORIZON_S = 30
DEFAULT_INITIAL_STATES = (
    {"name": "LOW",  "LIT101": 30.0, "LIT201": 30.0,
     "MV101": "closed", "P101": "off", "P102": "off",
     "MV201": "closed",
     "P201": "off", "P202": "off", "P203": "off",
     "P204": "off", "P205": "off", "P206": "off",
     "AIT201": 0.30},
    {"name": "MID",  "LIT101": 70.0, "LIT201": 60.0,
     "MV101": "closed", "P101": "off", "P102": "off",
     "MV201": "closed",
     "P201": "off", "P202": "off", "P203": "off",
     "P204": "off", "P205": "off", "P206": "off",
     "AIT201": 0.30},
    {"name": "HIGH", "LIT101": 90.0, "LIT201": 90.0,
     "MV101": "closed", "P101": "off", "P102": "off",
     "MV201": "closed",
     "P201": "off", "P202": "off", "P203": "off",
     "P204": "off", "P205": "off", "P206": "off",
     "AIT201": 0.30},
)


# Tools that are pure reads or rate-set: composition with reads cannot
# perturb the plant, so we exclude reads from composition replay to keep
# cost down. set_dosing_rate is a parametric tool — composition replay on
# it requires a rate argument, which we skip (single-tool layer already
# checks magnitude poisoning per Mission 2A).
NON_COMPOSITION_TOOLS = frozenset({
    "read_level_T101", "read_level_T201",
    "read_flow_FIT101", "read_flow_FIT201",
    "read_chemical_AIT201",
    "set_dosing_rate",
})


@dataclasses.dataclass
class BlockedPair:
    a: str
    b: str
    initial_state: str
    max_LIT101: float
    min_LIT101: float
    max_LIT201: float
    min_LIT201: float
    band_exit_step_s: int | None
    band_exit_var: str | None
    reason: str


@dataclasses.dataclass
class CompositionVerdict:
    n_admitted_in_input: int
    n_composition_eligible: int
    n_pairs_tested: int
    horizon_s: int
    safe_band_LIT101: tuple[float, float]
    safe_band_LIT201: tuple[float, float]
    blocked_pairs: list[BlockedPair]
    safe_pair_count: int

    def is_blocked(self, tool_a: str, tool_b: str) -> bool:
        """True iff (tool_a, tool_b) appears as a blocked ordered pair under
        any initial state."""
        return any(bp.a == tool_a and bp.b == tool_b for bp in self.blocked_pairs)

    def blocked_pair_set(self) -> set[tuple[str, str]]:
        return {(bp.a, bp.b) for bp in self.blocked_pairs}

    def to_dict(self) -> dict:
        return {
            "n_admitted_in_input": self.n_admitted_in_input,
            "n_composition_eligible": self.n_composition_eligible,
            "n_pairs_tested": self.n_pairs_tested,
            "horizon_s": self.horizon_s,
            "safe_band_LIT101": list(self.safe_band_LIT101),
            "safe_band_LIT201": list(self.safe_band_LIT201),
            "blocked_pairs": [dataclasses.asdict(bp) for bp in self.blocked_pairs],
            "blocked_pair_count": len(self.blocked_pairs),
            "safe_pair_count": self.safe_pair_count,
        }


def _apply_init(plant: SwatP1P2Plant, init: dict[str, Any]) -> None:
    for k, v in init.items():
        if k == "name":
            continue
        plant.state[k] = v
    plant.t = 0.0


def _replay_pair(server: MCPServer,
                 init: dict[str, Any],
                 tool_a: str,
                 tool_b: str,
                 horizon_s: int) -> dict[str, Any]:
    """Replay (tool_a, tool_b) at t=0 then step the plant horizon_s seconds."""
    _apply_init(server.plant, init)

    # Issue the composition back-to-back.
    server.call_tool(tool_a)
    server.call_tool(tool_b)

    L101 = [float(server.plant.read("LIT101"))]
    L201 = [float(server.plant.read("LIT201"))]
    for _ in range(horizon_s):
        server.plant.step(1.0)
        L101.append(float(server.plant.read("LIT101")))
        L201.append(float(server.plant.read("LIT201")))
    return {"L101": L101, "L201": L201}


def _band_exit(traj: list[float], band: tuple[float, float]) -> int | None:
    lo, hi = band
    for k, v in enumerate(traj):
        if v < lo or v > hi:
            return k
    return None


def verify_compositions(admitted_tools: Iterable[str],
                        server_factory,
                        initial_states: Iterable[dict[str, Any]] | None = None,
                        horizon_s: int = COMPOSITION_HORIZON_S,
                        safe_band_LIT101: tuple[float, float] = SAFE_BAND_LIT101,
                        safe_band_LIT201: tuple[float, float] = SAFE_BAND_LIT201,
                        ) -> CompositionVerdict:
    """Run composition replay over the admitted tools.

    `server_factory` must return a fresh `MCPServer` whose `_tools` map
    contains the originals (used to clone impls for replay). The verifier
    creates a new SwatP1P2Plant per replay so the admission pass does not
    perturb the live agent's plant.
    """
    admitted = [t for t in admitted_tools if t not in NON_COMPOSITION_TOOLS]
    initial_states = tuple(initial_states or DEFAULT_INITIAL_STATES)

    blocked: list[BlockedPair] = []
    safe_count = 0
    n_pairs_tested = 0

    for a, b in permutations(admitted, 2):
        for init in initial_states:
            n_pairs_tested += 1
            # Build a fresh server *cloned from the original surface*. The
            # caller's server_factory is responsible for setting up the
            # canonical (or attacked) tool surface. We do NOT use the live
            # admission server because composition replay must not
            # perturb runtime state.
            server = server_factory()
            traj = _replay_pair(server, init, a, b, horizon_s)
            exit_101 = _band_exit(traj["L101"], safe_band_LIT101)
            exit_201 = _band_exit(traj["L201"], safe_band_LIT201)

            band_exit_step: int | None
            band_exit_var: str | None
            if exit_101 is not None and (exit_201 is None or exit_101 <= exit_201):
                band_exit_step = exit_101
                band_exit_var = "LIT101"
            elif exit_201 is not None:
                band_exit_step = exit_201
                band_exit_var = "LIT201"
            else:
                band_exit_step = None
                band_exit_var = None

            if band_exit_step is None:
                safe_count += 1
                continue

            blocked.append(BlockedPair(
                a=a, b=b,
                initial_state=str(init.get("name", "")),
                max_LIT101=max(traj["L101"]),
                min_LIT101=min(traj["L101"]),
                max_LIT201=max(traj["L201"]),
                min_LIT201=min(traj["L201"]),
                band_exit_step_s=band_exit_step,
                band_exit_var=band_exit_var,
                reason=(f"composition exits safe band on {band_exit_var} at "
                        f"t={band_exit_step}s under init={init['name']}"),
            ))

    return CompositionVerdict(
        n_admitted_in_input=len(list(admitted_tools)),
        n_composition_eligible=len(admitted),
        n_pairs_tested=n_pairs_tested,
        horizon_s=horizon_s,
        safe_band_LIT101=safe_band_LIT101,
        safe_band_LIT201=safe_band_LIT201,
        blocked_pairs=blocked,
        safe_pair_count=safe_count,
    )


def attack_runtime_pair_window(tool_sequence: list[str]) -> list[tuple[str, str]]:
    """Extract all ordered (a, b) adjacent and non-adjacent pairs from a
    tool sequence. Composition-detection fires if ANY of these is in the
    blocked set.

    For two-call attacks, this is just (s[0], s[1]).
    For longer sequences, every (s[i], s[j]) with i < j is checked.
    """
    out: list[tuple[str, str]] = []
    for i in range(len(tool_sequence)):
        for j in range(i + 1, len(tool_sequence)):
            out.append((tool_sequence[i], tool_sequence[j]))
    return out


def composition_detects(tool_sequence: list[str],
                        verdict: CompositionVerdict) -> dict[str, Any]:
    """Decision: did composition admission catch this attack?

    Returns a dict {detected, hits, blocked_pair_set_size}. `hits` is the
    list of (a, b) pairs from `tool_sequence` that match `verdict.blocked_pair_set`.
    """
    if not tool_sequence:
        return {"detected": False, "hits": [], "blocked_pair_set_size": len(verdict.blocked_pairs)}
    blocked = verdict.blocked_pair_set()
    hits = [p for p in attack_runtime_pair_window(tool_sequence) if p in blocked]
    return {"detected": bool(hits), "hits": hits,
            "blocked_pair_set_size": len(verdict.blocked_pairs)}
