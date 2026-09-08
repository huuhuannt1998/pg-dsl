# SUPERSEDED_BY: n7b_prefilter_variants.py
# WHY_WRONG: models "charitable" by MEASURING each tool's affected-state set from the
#   default initial state. close_*/stop_* tools move nothing from a state where the valve
#   is already closed, so their measured sets come back empty and never intersect anything.
#   The model therefore prunes MORE than the literal reading (15/15 lost) - the opposite of
#   charitable. n7b uses the actuator->tank topology a sign classifier would actually use
#   and reproduces the asserted 4/15 exactly.
# DO_NOT_CITE: the 15/15 figure in this file is an artifact, not a result.
"""N7 - substantiate (or correct) the 'charitable reading' of the Sec 4.4 prefilter.

e7_scale.py measured only the LITERAL reading of the prefilter ("actuator-state
intersection" == same actuator), which loses 14 of 15 unsafe (pair,state) triples.
RESULTS.md and the rebuttal additionally asserted "4 of 15 charitably" with NO
computation behind it. This script computes the charitable reading properly.

Charitable prefilter := keep the ordered pair if the two tools' MEASURED
affected-state sets intersect (not merely the same actuator). The affected-state
set per tool is measured, not hand-coded: replay each tool alone from each
published initial state and record which plant state variables move.

This is the most generous sign-classifier-style prefilter that still prunes
anything: it keeps every pair that could interact through a shared state var.
"""
import sys, itertools, json
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
from harness import *
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/mission_3b')
from admission_layer.composition_verifier import (DEFAULT_INITIAL_STATES, SAFE_BAND_LIT101,
                                  SAFE_BAND_LIT201, COMPOSITION_HORIZON_S)

ACT=["open_valve_MV101","close_valve_MV101","open_valve_MV201","close_valve_MV201",
     "start_pump_P101","stop_pump_P101","start_dosing_pump_P201","stop_dosing_pump_P201"]
ACTOF={"open_valve_MV101":"MV101","close_valve_MV101":"MV101","open_valve_MV201":"MV201",
 "close_valve_MV201":"MV201","start_pump_P101":"P101","stop_pump_P101":"P101",
 "start_dosing_pump_P201":"P201","stop_dosing_pump_P201":"P201"}

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

def affected_states(tool):
    """Measured: which state vars move when this tool runs, vs a no-tool control."""
    moved=set()
    for init in DEFAULT_INITIAL_STATES:
        # control: no tool
        pc,_=fresh()
        for k,v in init.items():
            if k!='name': pc.state[k]=v
        for _ in range(int(COMPOSITION_HORIZON_S)): pc.step()
        # treatment: tool then same horizon
        pt,st=fresh()
        for k,v in init.items():
            if k!='name': pt.state[k]=v
        st.call_tool(tool)
        for _ in range(int(COMPOSITION_HORIZON_S)): pt.step()
        for var in pc.state:
            try:
                a,b=float(pc.state[var]), float(pt.state[var])
            except (TypeError,ValueError):
                if pc.state[var]!=pt.state[var]: moved.add(var)
                continue
            if abs(a-b)>1e-9: moved.add(var)
    return moved

AFF={t:affected_states(t) for t in ACT}
print("== measured affected-state sets ==")
for t in ACT: print(f"  {t:<28} {sorted(AFF[t])}")

truth=set()
for a,b in itertools.permutations(ACT,2):
    for init in DEFAULT_INITIAL_STATES:
        if replay([a,b],init): truth.add((a,b,init['name']))

kept_lit=set(); kept_cha=set()
for a,b in itertools.permutations(ACT,2):
    for init in DEFAULT_INITIAL_STATES:
        if ACTOF[a]==ACTOF[b]: kept_lit.add((a,b,init['name']))
        if AFF[a] & AFF[b]:    kept_cha.add((a,b,init['name']))

lost_lit=truth-kept_lit; lost_cha=truth-kept_cha
n=len(truth)
print(f"\nground-truth unsafe (pair,state) triples : {n}")
print(f"LITERAL   prefilter: kept {len(kept_lit):3d}  lost {len(lost_lit):2d}/{n}")
print(f"CHARITABLE prefilter: kept {len(kept_cha):3d}  lost {len(lost_cha):2d}/{n}")
print(f"\nrebuttal asserted 'lost 4 of 15 charitably' -> "
      f"{'CONFIRMED' if len(lost_cha)==4 and n==15 else 'NOT CONFIRMED'}")
if lost_cha:
    print("charitable losses:")
    for x in sorted(lost_cha): print("   ",x)

save("n7_prefilter_charitable", {
  "purpose":"substantiate or correct the 'charitable reading' asserted in RESULTS.md/rebuttal B4",
  "charitable_definition":"keep ordered pair iff MEASURED affected-state sets intersect",
  "affected_states":{t:sorted(AFF[t]) for t in ACT},
  "ground_truth_unsafe":n,
  "literal":{"kept":len(kept_lit),"lost":len(lost_lit)},
  "charitable":{"kept":len(kept_cha),"lost":len(lost_cha),
                "lost_examples":[list(x) for x in sorted(lost_cha)]},
  "rebuttal_claim_4_of_15_confirmed": bool(len(lost_cha)==4 and n==15)})
