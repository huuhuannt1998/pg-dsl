"""N7b - is the 'charitable reading' of the Sec 4.4 prefilter really 15/15 lost?

n7 measured each tool's affected-state set by replaying it alone from the default
state. That penalises close_*/stop_* tools: closing an already-closed valve moves
nothing, so their measured set is empty and they never intersect anything. That is
a MEASUREMENT ARTIFACT, not a charitable reading.

This script tries three progressively more generous readings, including the one a
"monotone sign-classifier on actuator semantics" would actually use: a static
actuator -> touched-tank topology, which is charitable because it ignores direction
and state and keeps any pair that could interact through shared plant topology.
"""
import sys, itertools, json
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
from harness import *
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/mission_3b')
from admission_layer.composition_verifier import (DEFAULT_INITIAL_STATES,
    SAFE_BAND_LIT101, SAFE_BAND_LIT201, COMPOSITION_HORIZON_S)

ACT=["open_valve_MV101","close_valve_MV101","open_valve_MV201","close_valve_MV201",
     "start_pump_P101","stop_pump_P101","start_dosing_pump_P201","stop_dosing_pump_P201"]
ACTOF={"open_valve_MV101":"MV101","close_valve_MV101":"MV101","open_valve_MV201":"MV201",
 "close_valve_MV201":"MV201","start_pump_P101":"P101","stop_pump_P101":"P101",
 "start_dosing_pump_P201":"P201","stop_dosing_pump_P201":"P201"}
# SWaT P1+P2 topology: which tanks/state each actuator physically touches.
TOPO={"MV101":{"T101"}, "P101":{"T101","T201"}, "MV201":{"T201"}, "P201":{"T201"}}

def fresh():
    p=SwatP1P2Plant(PlantParams()); return p, MCPServer(p)

def replay(seq, init):
    p,s=fresh()
    for k,v in init.items():
        if k!='name': p.state[k]=v
    for t in seq: s.call_tool(t)
    for _ in range(int(COMPOSITION_HORIZON_S)):
        p.step()
        l1,l2=float(p.read('LIT101')),float(p.read('LIT201'))
        if not(SAFE_BAND_LIT101[0]<=l1<=SAFE_BAND_LIT101[1]) or not(SAFE_BAND_LIT201[0]<=l2<=SAFE_BAND_LIT201[1]):
            return True
    return False

truth=set()
for a,b in itertools.permutations(ACT,2):
    for init in DEFAULT_INITIAL_STATES:
        if replay([a,b],init): truth.add((a,b,init['name']))
n=len(truth)

READINGS={
 "literal_same_actuator":      lambda a,b: ACTOF[a]==ACTOF[b],
 "charitable_shared_tank":     lambda a,b: bool(TOPO[ACTOF[a]] & TOPO[ACTOF[b]]),
 "maximally_charitable_any_actuator_pair": lambda a,b: True,
}
out={}
print(f"ground-truth unsafe (pair,state) triples: {n}\n")
for name,rule in READINGS.items():
    kept=set()
    for a,b in itertools.permutations(ACT,2):
        for init in DEFAULT_INITIAL_STATES:
            if rule(a,b): kept.add((a,b,init['name']))
    lost=truth-kept
    frac_pruned = 1 - len(kept)/(len(ACT)*(len(ACT)-1)*len(DEFAULT_INITIAL_STATES))
    out[name]={"kept":len(kept),"lost":len(lost),
               "fraction_of_budget_pruned":round(frac_pruned,3),
               "lost_examples":[list(x) for x in sorted(lost)[:6]]}
    print(f"{name:42} kept {len(kept):3d}  LOST {len(lost):2d}/{n}   prunes {frac_pruned*100:4.1f}% of budget")

print("\n-> does ANY reading prune anything AND lose 0?",
      any(v['lost']==0 and v['fraction_of_budget_pruned']>0 for v in out.values()))
print("-> was the withdrawn 'without coverage loss' claim ever true? ",
      any(v['lost']==0 and v['fraction_of_budget_pruned']>0 for v in out.values()))
print("-> does any reading give the asserted 4/15?",
      any(v['lost']==4 for v in out.values()))

save("n7b_prefilter_variants",{
 "purpose":"test whether the asserted '4 of 15 charitable' survives ANY reasonable reading",
 "ground_truth_unsafe":n,"readings":out,
 "n7_artifact_note":"n7's measured-effect model gave empty sets for close_*/stop_* tools (closing an already-closed valve moves nothing); superseded by the topology reading here",
 "any_reading_yields_4": any(v['lost']==4 for v in out.values()),
 "any_reading_prunes_without_loss": any(v['lost']==0 and v['fraction_of_budget_pruned']>0 for v in out.values())})
