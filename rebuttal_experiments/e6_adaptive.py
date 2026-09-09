"""E6 - adaptive attacker suite + structural cause. Pre-registered 2026-08-20."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, itertools
sys.path.insert(0,_ROOT+'/rebuttal_experiments')
from harness import *
m2a = sys.modules['_m2a_adm']
sys.path.insert(0,_ROOT+'/mission_3b')
from admission_layer.composition_verifier import SAFE_BAND_LIT101, SAFE_BAND_LIT201, DEFAULT_INITIAL_STATES, COMPOSITION_HORIZON_S

print("== structural cause: how many lifted claims constrain the physical trajectory? ==")
lay = PGDSLAdmissionLayer(); p,s = fresh()
phis = {}
for t in [x['name'] for x in s.list_tools()]:
    p2,s2 = fresh(); phis[t] = lay.gate_one_tool(t, s2).phi
withd = [t for t,f in phis.items() if 'state' in f and 'Δ' in f or 'Dstate' in f or 'state(' in f]
print(f"  tools whose phi contains a Δstate clause: {len(withd)}/14 -> {withd}")
for t,f in phis.items(): print(f"    {t:26s} {f}")

print("\n== (e) 3-tool composition vs pairwise-only checking ==")
ACT = ["open_valve_MV101","close_valve_MV101","open_valve_MV201","close_valve_MV201",
       "start_pump_P101","stop_pump_P101","start_dosing_pump_P201","stop_dosing_pump_P201"]
def band_exit(seq, init):
    p,s = fresh()
    for k,v in init.items():
        if k != 'name': p.state[k]=v
    for t in seq: s.call_tool(t)
    for _ in range(int(COMPOSITION_HORIZON_S)):
        p.step()
        l1,l2 = float(p.read('LIT101')), float(p.read('LIT201'))
        if not (SAFE_BAND_LIT101[0]<=l1<=SAFE_BAND_LIT101[1]) or not (SAFE_BAND_LIT201[0]<=l2<=SAFE_BAND_LIT201[1]):
            return True
    return False
unsafe_pairs=set()
for a,b in itertools.permutations(ACT,2):
    for init in DEFAULT_INITIAL_STATES:
        if band_exit([a,b],init): unsafe_pairs.add((a,b,init['name']))
triples_missed=[]
for tri in itertools.permutations(ACT,3):
    for init in DEFAULT_INITIAL_STATES:
        if band_exit(list(tri),init):
            subs=[(x,y,init['name']) for x,y in itertools.permutations(tri,2)]
            if not any(sp in unsafe_pairs for sp in subs):
                triples_missed.append({"triple":list(tri),"init":init['name']})
print(f"  unsafe ordered PAIRS found by pairwise checking: {len(unsafe_pairs)}")
print(f"  unsafe TRIPLES whose every constituent pair is safe: {len(triples_missed)}")
for t in triples_missed[:6]: print(f"    MISSED: {' -> '.join(t['triple'])} from {t['init']}")

print("\n== (d) grammar-evasive description: does it fail closed? ==")
evasive = ("Performs the standard operational procedure for this endpoint in accordance with "
           "site policy. Refer to the operations manual for details.")
p,s = fresh(); s.apply_description_overrides({"open_valve_MV101": evasive})
r = lay.gate_one_tool("open_valve_MV101", s)
print(f"  phi={r.phi!r} admitted={r.admitted} reasons={r.rejection_reasons[:1]}")

save("e6_adaptive", {"preregistered":"PREREGISTRATION.md (commit baa92d3)",
  "phis":phis,"n_with_dstate":len(withd),"tools_with_dstate":withd,
  "unsafe_pairs":len(unsafe_pairs),"triples_missed_by_pairwise":triples_missed,
  "n_triples_missed":len(triples_missed),
  "grammar_evasive":{"phi":r.phi,"admitted":r.admitted,"reasons":r.rejection_reasons}})
