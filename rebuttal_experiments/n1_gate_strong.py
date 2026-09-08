"""Strengthened N1 regression gate, per plan Section 4 N1 and Section 9.
The first gate covered 3 of 14 tools and only LIT101 -- and since LIT101 is
chemistry-invariant (eps_DT_emp = 0.0 on every chem twin), it could not exercise the
chemistry branch of PerturbedPlant.step at all. This gate covers ALL 14 tools x 3 initial
states x ALL 7 sensors x 120 steps, and byte-compares serialised nominal trajectories
against the frozen plant."""
import sys, json, hashlib
sys.path.insert(0,'.')
from harness import *
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/mission_1b')
from plant import SwatP1P2Plant, PlantParams
from mcp_server import MCPServer
from n1_perturbed_twin import PerturbedPlant
m2a=sys.modules['_m2a_adm']
INIT=[("LOW",30.0,30.0),("MID",70.0,60.0),("HIGH",90.0,90.0)]
SENS=("LIT101","LIT201","FIT101","FIT201","AIT201","AIT202","AIT203")

def traj(plant_factory, tool, l1, l2):
    p=plant_factory(); s=MCPServer(p)
    p.state["LIT101"]=l1; p.state["LIT201"]=l2
    try: s.call_tool(tool)
    except Exception: pass
    out=[]
    for _ in range(120):
        p.step(); out.append([float(p.read(k)) for k in SENS])
    return out

p0,s0=fresh(); TOOLS=[t['name'] for t in s0.list_tools()]
rows=[]; div=0
for tool in TOOLS:
    for nm,l1,l2 in INIT:
        a=traj(lambda: PerturbedPlant(PlantParams()), tool, l1, l2)   # nominal perturbed
        b=traj(lambda: SwatP1P2Plant(PlantParams()),  tool, l1, l2)   # frozen
        ja=json.dumps(a,sort_keys=True); jb=json.dumps(b,sort_keys=True)
        same = (ja.encode()==jb.encode())
        if not same:
            div+=1
            worst=max(abs(x-y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))
            print(f"  DIVERGENCE {tool} {nm}  max |delta| = {worst}")
        rows.append({"tool":tool,"state":nm,"byte_identical":same,
                     "sha_nominal":hashlib.sha256(ja.encode()).hexdigest()[:16],
                     "sha_frozen":hashlib.sha256(jb.encode()).hexdigest()[:16]})
n=len(rows)
print(f"\nSTRONG REGRESSION GATE")
print(f"  coverage : {len(TOOLS)} tools x {len(INIT)} states x {len(SENS)} sensors x 120 steps"
      f" = {n} trajectories, {n*len(SENS)*120} scalar comparisons")
print(f"  result   : {n-div}/{n} byte-identical, {div} divergences")
print(f"  verdict  : {'PASS' if div==0 else 'FAIL'}")
digest=hashlib.sha256("".join(r["sha_nominal"] for r in rows).encode()).hexdigest()
print(f"  trajectory-set digest: {digest}")
save("n1_gate_strong",{"coverage":{"tools":len(TOOLS),"states":len(INIT),"sensors":len(SENS),
  "steps":120,"trajectories":n,"scalar_comparisons":n*len(SENS)*120},
  "byte_identical":n-div,"divergences":div,"passed":div==0,
  "trajectory_set_digest":digest,
  "supersedes":"n1_gate.json (3 tools, LIT101 only - could not reach the chemistry branch)",
  "rows":rows})
