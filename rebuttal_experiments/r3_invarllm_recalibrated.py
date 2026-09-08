"""E3 - INVARLLM re-mined on grid-spanning benign traffic; runtime column recomputed. Pre-registered."""
import sys, json, random, re, time
from pathlib import Path
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
from harness import *
ROOT='/Users/huanbui/Desktop/PG-DSL'
for p in (ROOT, f'{ROOT}/mission_1b', f'{ROOT}/mission_2a', f'{ROOT}/mission_2b', f'{ROOT}/mission_2b/baselines', f'{ROOT}/mission_3b'):
    sys.path.insert(0,p)
from invarllm_runtime import INVARLLMRuntime
from mission_3b.attacks.z3_simulator import make_z3_simulator
from evaluation.run_t3_composition import SIMULATORS as M2B_SIMULATORS
M1B=Path(f'{ROOT}/mission_1b'); SENS=("LIT101","LIT201","FIT101","FIT201","AIT201"); ACTK=("MV101","P101","P102","MV201")
def rep_traces():
    out=[]
    for path in sorted((M1B/"results"/"benign").glob("rep*.json")):
        traj=json.loads(path.read_text())["trajectory"]
        out.append({s:[x.get(s) for x in traj] for s in SENS} | {"actuator_per_step":[{a:x.get(a) for a in ACTK} for x in traj]})
    return out
CANON=[{"name":"LOW","LIT101":30.0,"LIT201":30.0},{"name":"MID","LIT101":70.0,"LIT201":60.0},{"name":"HIGH","LIT101":90.0,"LIT201":90.0}]
for c in CANON: c.update({"MV101":"closed","P101":"off","MV201":"closed","P201":"off","AIT201":0.30})
def lhs2d(K, seed):
    r=random.Random(seed)
    a=[25.0+(i+r.random())*70.0/K for i in range(K)]; b=[20.0+(i+r.random())*75.0/K for i in range(K)]; r.shuffle(b)
    return [{"name":f"LHS{i:02d}","LIT101":round(a[i],3),"LIT201":round(b[i],3),"MV101":"closed","P101":"off","MV201":"closed","P201":"off","AIT201":0.30} for i in range(K)]
LHS=lhs2d(30,1030); STEPS=120
def honest_trace(tool, init):
    p,s=fresh()
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    snaps=[]
    def snap():
        d={a:p.read(a) for a in ACTK}; d.update({x:float(p.read(x)) for x in SENS}); return d
    snaps.append(snap())
    try:
        s.call_tool(tool,{"rate":1.0}) if tool=="set_dosing_rate" else s.call_tool(tool)
    except Exception: pass
    for _ in range(STEPS): p.step(); snaps.append(snap())
    return {x:[q[x] for q in snaps] for x in SENS} | {"actuator_per_step":[{a:q[a] for a in ACTK} for q in snaps]}
tools=[t['name'] for t in fresh()[1].list_tools()]
ACT_TOOLS=["open_valve_MV101","close_valve_MV101","open_valve_MV201","close_valve_MV201","start_pump_P101","stop_pump_P101","start_dosing_pump_P201","stop_dosing_pump_P201"]
honest42=[honest_trace(t,i) for t in tools for i in CANON]
heldout240=[(t,i["name"],honest_trace(t,i)) for t in ACT_TOOLS for i in LHS]

ids_old=INVARLLMRuntime.extract_from_traces(rep_traces())
ids_new=INVARLLMRuntime.extract_from_traces(rep_traces()+honest42)
def desc(ids): return [{"name":i.name,**{k:(round(v,3) if isinstance(v,float) else v) for k,v in vars(i).items() if k not in ('name','description')}} for i in ids.invariants]
print("re-mined invariants:"); [print("   ",d) for d in desc(ids_new)]

def fp(ids, traces):
    n=0; by={}; mb=0
    for tr in traces:
        r=ids.check(tr)
        if r.fired:
            n+=1
            for v in r.violations:
                by[v["invariant"]]=by.get(v["invariant"],0)+1
                if v["invariant"].startswith("mb"): mb+=1
    return {"fired":n,"n":len(traces),"by_invariant":by,"mass_balance":mb}
in_sample=fp(ids_new,honest42); heldout=fp(ids_new,[t for _,_,t in heldout240]); heldout_old=fp(ids_old,[t for _,_,t in heldout240])
print(f"\nhonest FPR  old-INVARLLM held-out 240: {heldout_old['fired']}/240 | re-mined in-sample 42: {in_sample['fired']}/42 | re-mined held-out 240: {heldout['fired']}/240 {heldout['by_invariant']} mb={heldout['mass_balance']}")

sims=dict(M2B_SIMULATORS); sims["Z3"]=make_z3_simulator
IDS=("A1","A2","A3","W1","W2","Z1","Z2","Z3")
old_part=json.load(open(f'{ROOT}/mission_3b/results/t3_partition_canonical.json'))
pg={r["id"]:r["canonical_pgdsl"]["detected"] for r in old_part["results"]}
old_rt={r["id"]:r["invarllm"]["detected"] for r in old_part["results"]}
rows={}
for aid in IDS:
    sf, rt, _ = sims[aid]()
    tel=rt(sf())
    ro=ids_old.check(tel); rn=ids_new.check(tel)
    rows[aid]={"pgdsl":pg[aid],"runtime_old_reproduced":ro.fired,"runtime_old_logged":old_rt[aid],
               "runtime_new":rn.fired,"new_violations":[{"invariant":v["invariant"],"reason":v["reason"][:80]} for v in rn.violations[:3]]}
    print(f"  {aid}: PG-DSL {'DET' if pg[aid] else 'miss':4}  INVARLLM old {'DET' if ro.fired else 'miss':4} (logged {'DET' if old_rt[aid] else 'miss'})  re-mined {'DET' if rn.fired else 'miss':4}  {[v['invariant'] for v in rn.violations[:2]]}")
A_s={a for a in IDS if rows[a]["pgdsl"]}; A_r={a for a in IDS if rows[a]["runtime_new"]}
lanes={"A_static":sorted(A_s),"A_runtime_new":sorted(A_r),"static_only":sorted(A_s-A_r),"runtime_only":sorted(A_r-A_s),
       "intersection":sorted(A_s&A_r),"missed_by_both":sorted(set(IDS)-A_s-A_r),"composed":sorted(A_s|A_r),
       "t3_strict":bool(A_s-A_r) and bool(A_r-A_s)}
print("\nlanes (re-mined runtime column):", lanes)
assert all(rows[a]["runtime_old_reproduced"]==rows[a]["runtime_old_logged"] for a in IDS), "could not reproduce the logged runtime column"
pred={"P7_heldout_le_12": heldout["fired"]<=12, "P8_no_mb_on_honest": heldout["mass_balance"]==0 and in_sample["mass_balance"]==0,
      "P9_A1_W2_Z3_det": all(rows[a]["runtime_new"] for a in ("A1","W2","Z3")), "P10_A2_miss": not rows["A2"]["runtime_new"],
      "P11_W1_miss": not rows["W1"]["runtime_new"], "P12_A3_Z1_miss_Z2_det": (not rows["A3"]["runtime_new"]) and (not rows["Z1"]["runtime_new"]) and rows["Z2"]["runtime_new"]}
print("predictions:", pred)
save("r3_invarllm_recalibrated",{"preregistered":"PREREGISTRATION_R.md E3","mining_set":"10 benign reps + 42 honest admission traces (14 tools x LOW/MID/HIGH, 120 s)",
  "heldout_set":"240 honest traces: 8 actuator tools x 30 LHS states (never mined)","invariants_old":desc(ids_old),"invariants_new":desc(ids_new),
  "honest_fpr":{"old_invarllm_heldout_240":heldout_old,"new_in_sample_42":in_sample,"new_heldout_240":heldout},
  "attacks":rows,"lanes_new":lanes,"lanes_old":old_part["lanes"],"predictions":pred})
