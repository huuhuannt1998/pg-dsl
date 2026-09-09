"""E2 (revision-pass III) - INVARLLM benign false-positive rate on honest admission-style traces.
Pre-registered in PREREGISTRATION_R.md before this run.

INVARLLM is built exactly as run_canonical_t3_partition_qwen3.py builds it (invariants mined
from mission_1b/results/benign/rep*.json). It is then fed honest traces it has never seen:
each of the 14 canonical tools executed once from LOW/MID/HIGH on a fresh plant and stepped
for the 120 s admission horizon (42 traces), plus the 8 actuator tools from the 30 LHS states
of E1 (240 traces). A trace is a false positive iff check() reports >= 1 violation."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, random, re
from pathlib import Path
sys.path.insert(0,_ROOT+'/rebuttal_experiments')
from harness import *
ROOT=_ROOT
for p in (f'{ROOT}/mission_2b', f'{ROOT}/mission_2b/baselines', f'{ROOT}/mission_1b', f'{ROOT}/mission_2a'):
    sys.path.insert(0,p)
from invarllm_runtime import INVARLLMRuntime
M1B=Path(f'{ROOT}/mission_1b')

def build_invarllm():
    traces=[]
    for path in sorted((M1B/"results"/"benign").glob("rep*.json")):
        traj=json.loads(path.read_text())["trajectory"]
        traces.append({s:[x.get(s) for x in traj] for s in ("LIT101","LIT201","FIT101","FIT201","AIT201")}
                      | {"actuator_per_step":[{a:x.get(a) for a in ("MV101","P101","P102","MV201")} for x in traj]})
    return INVARLLMRuntime.extract_from_traces(traces), len(traces)
ids,nb=build_invarllm()
inv_desc=[{"name":i.name,"fields":{k:v for k,v in vars(i).items() if k not in ('name','description')}} for i in ids.invariants]
print(f"INVARLLM: {len(ids.invariants)} invariants mined from {nb} benign reps")
for i in inv_desc: print("   ", i["name"], i["fields"])

CANON=[{"name":"LOW","LIT101":30.0,"LIT201":30.0,"MV101":"closed","P101":"off","MV201":"closed","P201":"off","AIT201":0.30},
       {"name":"MID","LIT101":70.0,"LIT201":60.0,"MV101":"closed","P101":"off","MV201":"closed","P201":"off","AIT201":0.30},
       {"name":"HIGH","LIT101":90.0,"LIT201":90.0,"MV101":"closed","P101":"off","MV201":"closed","P201":"off","AIT201":0.30}]
def lhs2d(K, seed):
    r=random.Random(seed)
    a=[25.0+(i+r.random())*70.0/K for i in range(K)]; b=[20.0+(i+r.random())*75.0/K for i in range(K)]; r.shuffle(b)
    return [{"name":f"LHS{i:02d}","LIT101":round(a[i],3),"LIT201":round(b[i],3),
             "MV101":"closed","P101":"off","MV201":"closed","P201":"off","AIT201":0.30} for i in range(K)]
LHS=lhs2d(30, seed=1030)
ACT_TOOLS=["open_valve_MV101","close_valve_MV101","open_valve_MV201","close_valve_MV201",
           "start_pump_P101","stop_pump_P101","start_dosing_pump_P201","stop_dosing_pump_P201"]
STEPS=120
SENS=("LIT101","LIT201","FIT101","FIT201","AIT201")

def honest_trace(tool, init):
    p,s=fresh()
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    snaps=[]
    def snap():
        d={a:p.read(a) for a in ("MV101","P101","P102","MV201")}
        d.update({x:float(p.read(x)) for x in SENS}); return d
    snaps.append(snap())
    try:
        if tool=="set_dosing_rate": s.call_tool(tool,{"rate":1.0})
        else: s.call_tool(tool)
    except Exception: pass
    for _ in range(STEPS): p.step(); snaps.append(snap())
    return {s_:[x[s_] for x in snaps] for s_ in SENS} | {"actuator_per_step":[{a:x[a] for a in ("MV101","P101","P102","MV201")} for x in snaps]}

STEP_RE=re.compile(r"\[(\d+)\]")
def score(tool, init):
    rep=ids.check(honest_trace(tool, init))
    v=[]
    for x in rep.violations:
        m=STEP_RE.search(x["reason"] or "")
        v.append({"invariant":x["invariant"],"step":int(m.group(1)) if m else None,"reason":x["reason"][:90]})
    return {"tool":tool,"state":init["name"],"LIT101_0":init["LIT101"],"LIT201_0":init["LIT201"],
            "fired":rep.fired,"violations":v}

tools=[t['name'] for t in fresh()[1].list_tools()]
rows42=[score(t,i) for t in tools for i in CANON]
rows240=[score(t,i) for t in ACT_TOOLS for i in LHS]
def summ(rows,label):
    fp=[r for r in rows if r["fired"]]
    by_inv={}; t0=0; mb=0
    for r in fp:
        for v in r["violations"]:
            by_inv[v["invariant"]]=by_inv.get(v["invariant"],0)+1
            if v["step"]==0: t0+=1
            if "mass" in v["invariant"].lower() or "residual" in (v["reason"] or "").lower(): mb+=1
    by_state={}
    for r in fp: by_state[r["state"]]=by_state.get(r["state"],0)+1
    print(f"\n{label}: {len(fp)}/{len(rows)} honest traces fire  | by invariant {by_inv} | violations at t=0: {t0} | mass-balance: {mb}")
    print(f"   firing traces by initial state: {dict(sorted(by_state.items()))}")
    return {"n":len(rows),"fired":len(fp),"by_invariant":by_inv,"violations_at_t0":t0,"mass_balance_violations":mb,"by_state":by_state}
s42=summ(rows42,"[42] 14 tools x LOW/MID/HIGH"); s240=summ(rows240,"[240] 8 actuator tools x 30 LHS")
ex=[r for r in rows42 if r["fired"]][:4]
for r in ex: print("   e.g.", r["tool"], r["state"], r["violations"][:2])
lit201_lo=[r for r in rows42 if r["state"]=="MID" and r["fired"]]
print(f"\nMID-state honest traces that fire: {len(lit201_lo)}/14 (LIT201 starts at the mined floor 60)")
pred={"P5_ge1_all_band_t0_LOW_no_massbalance":
        s42["fired"]>=1 and s42["mass_balance_violations"]==0 and all(k.startswith("band_") for k in s42["by_invariant"]),
      "P5_strict_only_LOW_at_t0": s42["fired"]>=1 and set(s42["by_state"])=={"LOW"} and s42["violations_at_t0"]==sum(s42["by_invariant"].values())}
print("predictions:", pred)
save("r2_invarllm_benign",{"preregistered":"PREREGISTRATION_R.md E2","invariants":inv_desc,"n_benign_reps_fit":nb,
  "horizon_steps":STEPS,"canonical_42":s42,"lhs_240":s240,"rows_42":rows42,"rows_240":rows240,"predictions":pred})
