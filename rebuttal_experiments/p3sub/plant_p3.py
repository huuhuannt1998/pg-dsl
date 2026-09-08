"""SWaT Stage P3 (ultrafiltration) digital twin — ADDITIVE second substrate.
Deliberately a separate module: mission_1b/plant/swat_p1p2.py is NOT modified, so no
existing paper number can be perturbed by this experiment.

Physics (same mass-balance family as P1+P2):
  T301 UF feed tank, fed from P2 through motorised valve MV301.
  P301 / P302 are redundant UF feed pumps drawing T301 down through the membrane.
  LIT301 level; FIT301 feed flow; DPIT301 trans-membrane differential pressure, which
  rises with cumulative throughput (fouling proxy) and is reset by a backwash.
"""
from __future__ import annotations
import dataclasses
from typing import Dict

@dataclasses.dataclass
class P3Params:
    dt: float = 1.0
    t301_init: float = 60.0
    t301_min: float = 0.0
    t301_max: float = 100.0
    q_in_mv301: float = 0.45      # %-full/s when MV301 open
    q_out_pump: float = 0.35      # %-full/s per UF pump running
    dp_init: float = 20.0         # kPa
    dp_per_unit_flow: float = 0.02
    dp_max: float = 100.0

class SwatP3Plant:
    ACTUATORS = ("MV301", "P301", "P302")
    SENSORS = ("LIT301", "FIT301", "DPIT301")
    INITIAL_ACTUATORS = {"MV301": "closed", "P301": "off", "P302": "off"}

    def __init__(self, params: P3Params | None = None) -> None:
        self.params = params or P3Params()
        self.t = 0.0
        self.state: Dict[str, object] = dict(self.INITIAL_ACTUATORS)
        self.state["LIT301"] = self.params.t301_init
        self.state["FIT301"] = 0.0
        self.state["DPIT301"] = self.params.dp_init

    def read(self, name):
        if name not in self.state: raise KeyError(name)
        return self.state[name]

    def set(self, name, value):
        if name not in self.ACTUATORS: raise KeyError(f"{name!r} is not an actuator")
        if name.startswith("MV") and value not in ("open","closed"): raise ValueError(value)
        if name.startswith("P") and value not in ("on","off"): raise ValueError(value)
        self.state[name] = value

    def snapshot(self):
        s = dict(self.state); s["_t"] = self.t; return s

    def step(self, dt=None):
        dt = dt or self.params.dt
        p = self.params
        q_in = p.q_in_mv301 if self.state["MV301"] == "open" else 0.0
        n_p = sum(1 for k in ("P301","P302") if self.state[k] == "on")
        q_out = p.q_out_pump * n_p
        lvl = float(self.state["LIT301"]) + (q_in - q_out) * dt
        self.state["LIT301"] = max(p.t301_min, min(p.t301_max, lvl))
        self.state["FIT301"] = q_out
        dp = float(self.state["DPIT301"]) + p.dp_per_unit_flow * q_out * dt
        self.state["DPIT301"] = min(p.dp_max, dp)
        self.t += dt

    def is_overflow_t301(self): return float(self.state["LIT301"]) >= 99.0
    def is_dry_run(self):
        return float(self.state["LIT301"]) <= 1.0 and any(
            self.state[k]=="on" for k in ("P301","P302"))
    def violations(self):
        v=[]
        if self.is_overflow_t301(): v.append("OVERFLOW_T301")
        if self.is_dry_run(): v.append("DRY_RUN_UF_PUMP")
        return v
