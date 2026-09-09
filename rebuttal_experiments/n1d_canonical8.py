"""N1 completion: the FULL canonical 8-attack set (A1,A2,A3,W1,W2,Z1,Z2,Z3) re-adjudicated
inside every perturbed twin, per plan Section 4 N1 'PER TWIN REQUIRED WORKLOAD'.
Z3 goes through the 168-replay composition pass. W1/W2 are logged for completeness and are
known runtime-only misses by design. Closes N1.2, N1.3, N1.4."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, time
sys.path.insert(0,'.')
from harness import *
ROOT=_ROOT
for p in (ROOT, f'{ROOT}/mission_1b', f'{ROOT}/mission_2a', f'{ROOT}/mission_2b', f'{ROOT}/mission_3b'):
    sys.path.insert(0,p)
from plant import PlantParams
from n1_perturbed_twin import PerturbedPlant, TWINS

from mission_3b.admission_layer import PGDSLCanonicalLayer, detected_at_admission
from mission_3b.admission_layer.pgdsl_canonical import PGDSLAdmissionLayer
from mission_3b.attacks.z3_simulator import make_z3_simulator, Z3_TOOL_SEQUENCE
from evaluation.run_t3_composition import SIMULATORS as M2B_SIMULATORS

TOOL_SEQ={"W1":["close_valve_MV101"],"W2":[],"Z1":["open_valve_MV201"],
          "Z2":["start_dosing_pump_P201","set_dosing_rate"],"Z3":Z3_TOOL_SEQUENCE}
POISONED={"A1":{"open_valve_MV101","close_valve_MV101"},"A2":{"set_dosing_rate"},
          "A3":{"read_level_T101"},"W1":set(),"W2":set(),"Z1":set(),
          "Z2":{"set_dosing_rate"},"Z3":set()}
IDS=("A1","A2","A3","W1","W2","Z1","Z2","Z3")

import plant as plant_mod
BASE=plant_mod.SwatP1P2Plant

def install(twin):
    """Swap the plant class everywhere so BOTH the per-tool and composition passes
    replay inside this twin."""
    _,f,l,c,d = twin
    class TwinPlant(PerturbedPlant):
        def __init__(self, params=None): super().__init__(params, flow=f, lat=l, chem=c, drift=d)
    TwinPlant.__name__='SwatP1P2Plant'
    n=0
    for mod in list(sys.modules.values()):
        if mod is None: continue
        try:
            if getattr(mod,'SwatP1P2Plant',None) is not None:
                setattr(mod,'SwatP1P2Plant',TwinPlant); n+=1
        except Exception: pass
    return n

def restore():
    for mod in list(sys.modules.values()):
        if mod is None: continue
        try:
            if getattr(mod,'SwatP1P2Plant',None) is not None:
                setattr(mod,'SwatP1P2Plant',BASE)
        except Exception: pass

def seq_for(aid, sim_factory):
    if aid in TOOL_SEQ: return TOOL_SEQ[aid]
    sf, rt, _ = sim_factory()
    calls=[]
    try:
        srv=sf()
        orig=srv.call_tool
        def spy(n,a=None,_o=orig,_c=calls): _c.append(n); return _o(n,a)
        srv.call_tool=spy
        rt(srv)
    except Exception: pass
    return calls

rows=[]; t0=time.time()
for tw in TWINS:
    n=install(tw)
    sims=dict(M2B_SIMULATORS); sims["Z3"]=make_z3_simulator
    layer=PGDSLCanonicalLayer(per_tool_layer=PGDSLAdmissionLayer(), mode="stub")
    rec={"twin":tw[0]}
    for aid in IDS:
        try:
            sf, rt, pois = sims[aid]()
            rep=layer.gate_all_tools(sf)
            s=seq_for(aid, sims[aid])
            det=detected_at_admission(rep, pois or POISONED[aid], s)
            rec[aid]={"detected":det["detected"],"via":det["via"]}
        except Exception as e:
            rec[aid]={"detected":None,"error":str(e)[:90]}
    rows.append(rec)
    print("  {:12} ".format(tw[0]) + "  ".join(
        f"{a}:{'DET' if rec[a].get('detected') else ('ERR' if rec[a].get('detected') is None else 'MISS')}"
        for a in IDS), flush=True)
    restore()

nom={a:rows[0][a].get('detected') for a in IDS}
flips=[(r['twin'],a) for r in rows for a in IDS if r[a].get('detected')!=nom[a]]
print(f"\nnominal baseline: {nom}")
print(f"attack-verdict flips vs nominal: {len(flips)}/{len(rows)*len(IDS)}  {flips}")
print(f"({time.time()-t0:.0f}s)")
save("n1d_canonical8",{"preregistered":"N1.2-N1.4 (full 8-attack set)","attacks":list(IDS),
  "n_twins":len(rows),"nominal":nom,"rows":rows,"flips":flips,
  "note":"W1/W2 are runtime-only by design and are logged, not scored as admission misses"})
