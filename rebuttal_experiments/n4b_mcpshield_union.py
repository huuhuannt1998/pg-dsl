"""N4 completion: rescore MCPShield on the 100 grid-enumerated MSB instances so the
union table (33 per class) carries the SAME denominator for both defences.
The plan flagged this as 'MCPShield rescore on the union if needed: about 100 judge
calls'. It is needed: the manuscript's MSB table otherwise mixes n=8 MCPShield numbers
with n=33 PG-DSL numbers.
Scoring is unchanged from mission_3b/experiments/run_msb_subset_evaluation.py:
detection = the Stage-1 judge returns INCONSISTENT (verdict.admitted == False)."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, time
ROOT=_ROOT
for p in (ROOT, f'{ROOT}/mission_1b', f'{ROOT}/mission_2c', f'{ROOT}/mission_2c/baselines',
          f'{ROOT}/mission_3b'):
    sys.path.insert(0,p)
from plant import PlantParams, SwatP1P2Plant
from mcp_server import MCPServer
from real_mcpshield_judge import RealMCPShieldJudge
from mission_3b.experiments.run_msb_subset_evaluation import make_one_invocation

grid=json.load(open('results/p1_msb100.json'))['instances']
judge=RealMCPShieldJudge()
def args_for(tool):
    return {"pump":"P201","rate":1.0} if tool=="set_dosing_rate" else None

rows=[]; t0=time.time()
for i,inst in enumerate(grid):
    p=SwatP1P2Plant(PlantParams()); s=MCPServer(p)
    s.apply_description_overrides({inst['target_tool']: inst['description']})
    try:
        inv=make_one_invocation(s, inst['target_tool'], args_for(inst['target_tool']))
        v=judge.judge(inst['description'], [inv])
        det=not v.admitted; rat=v.rationale
    except Exception as e:
        det=False; rat=f"ERROR {str(e)[:100]}"
    rows.append({**{k:inst[k] for k in ('id','msb_class','target_tool')},
                 "mcpshield_detected":det,"rationale":str(rat)[:160]})
    if (i+1)%10==0:
        print(f"   {i+1}/100  ({time.time()-t0:.0f}s)", flush=True)

by={}
for r in rows:
    c=r['msb_class']; by.setdefault(c,[0,0]); by[c][1]+=1; by[c][0]+=r['mcpshield_detected']
print("\nMCPShield on the 100 grid instances:")
for c in ('NC','PM','PI','OP'):
    d,n=by.get(c,[0,0]); print(f"   {c}: {d}/{n}")
# union with the hand-written n=8 set
hand=json.load(open(f'{ROOT}/mission_3b/results/msb_subset_evaluation.json'))['instances']
hb={}
for r in hand:
    c=r['msb_class']; m=r['mcpshield']
    det=m.get('detected') if isinstance(m,dict) else None
    hb.setdefault(c,[0,0]); hb[c][1]+=1; hb[c][0]+= bool(det)
print("\nUNION (8 hand-written + 25 grid = 33 per class), MCPShield:")
union={}
for c in ('NC','PM','PI','OP'):
    d=hb.get(c,[0,0])[0]+by.get(c,[0,0])[0]; n=hb.get(c,[0,0])[1]+by.get(c,[0,0])[1]
    union[c]={"hand":hb.get(c,[0,0]),"grid":by.get(c,[0,0]),"union_detected":d,"union_n":n}
    print(f"   {c}: hand {hb.get(c,[0,0])[0]}/{hb.get(c,[0,0])[1]}  grid {by.get(c,[0,0])[0]}/{by.get(c,[0,0])[1]}  UNION {d}/{n}")
json.dump({"scoring":"detection = MCPShield Stage-1 judge returns INCONSISTENT (unchanged)",
  "judge":"qwen3:14b RealMCPShieldJudge","n_grid":len(rows),"by_class_grid":by,
  "union":union,"seconds":round(time.time()-t0,1),"rows":rows},
  open('results/n4b_mcpshield_union.json','w'),indent=2)
print("-> n4b_mcpshield_union.json")
