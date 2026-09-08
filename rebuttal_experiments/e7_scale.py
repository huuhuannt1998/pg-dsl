"""E7 - composition-pass scale curve. Answers RC '14 tools' and RB 'O(n^2) scalability'.
Measures real wall-clock of the pairwise replay budget at synthetic catalog sizes, and
tests the paper's claim that a monotone sign-classifier prefilter prunes 'without coverage loss'."""
import sys, time, itertools, json
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
from harness import *
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/mission_3b')
from admission_layer.composition_verifier import (SAFE_BAND_LIT101, SAFE_BAND_LIT201,
    DEFAULT_INITIAL_STATES, COMPOSITION_HORIZON_S)

ACT=["open_valve_MV101","close_valve_MV101","open_valve_MV201","close_valve_MV201",
     "start_pump_P101","stop_pump_P101","start_dosing_pump_P201","stop_dosing_pump_P201"]

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

# measured per-replay cost
t0=time.time(); N=200
for i in range(N): replay([ACT[i%8],ACT[(i+1)%8]], DEFAULT_INITIAL_STATES[1])
per=(time.time()-t0)/N
print(f"measured per-replay cost: {1000*per:.3f} ms  (n={N})")

print("\n== projected composition budget by catalog size ==")
rows=[]
for n_tools in (14,50,100,200,500,1000):
    k=max(0,int(n_tools*8/14))            # actuator tools scale with catalog
    replays=k*(k-1)*len(DEFAULT_INITIAL_STATES)
    rows.append({"catalog":n_tools,"actuator_tools":k,"replays":replays,
                 "projected_seconds":round(replays*per,2)})
    print(f"  {n_tools:5d} tools -> k={k:4d}  {replays:9,d} replays  {replays*per:9.2f} s")

print("\n== does the sign-classifier prefilter prune 'without coverage loss'? ==")
truth=set()
for a,b in itertools.permutations(ACT,2):
    for init in DEFAULT_INITIAL_STATES:
        if replay([a,b],init): truth.add((a,b,init['name']))
ACTOF={"open_valve_MV101":"MV101","close_valve_MV101":"MV101","open_valve_MV201":"MV201",
 "close_valve_MV201":"MV201","start_pump_P101":"P101","stop_pump_P101":"P101",
 "start_dosing_pump_P201":"P201","stop_dosing_pump_P201":"P201"}
kept=set()
for a,b in itertools.permutations(ACT,2):
    if ACTOF[a]==ACTOF[b]:                       # "actuator-state intersection"
        for init in DEFAULT_INITIAL_STATES: kept.add((a,b,init['name']))
lost=truth-kept
print(f"  ground-truth unsafe ordered (pair,state): {len(truth)}")
print(f"  pairs surviving the prefilter          : {len(kept)}")
print(f"  unsafe pairs LOST by the prefilter     : {len(lost)}")
for x in sorted(lost)[:6]: print(f"    LOST: {x[0]} -> {x[1]} from {x[2]}")
save("e7_scale",{"per_replay_ms":1000*per,"projection":rows,
  "prefilter":{"ground_truth_unsafe":len(truth),"kept":len(kept),"lost":len(lost),
               "coverage_loss": len(lost)>0,
               "lost_examples":[list(x) for x in sorted(lost)[:10]]}})
