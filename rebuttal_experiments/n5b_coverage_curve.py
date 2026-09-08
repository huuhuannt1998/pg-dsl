"""N5 (revised): the first design used 16 mutants sharing only 2 trigger locations, so
detection was a step, not a curve, and could not estimate coverage. Revised design sweeps
trigger WIDTH and randomises trigger LOCATION so K-vs-coverage is measurable.
Scoring rule fixed before this run; the first design's result is reported too."""
import sys, json, random, time
sys.path.insert(0,'.')
from harness import *
import e11_mutation as E
m2a=sys.modules['_m2a_adm']; lay=E.PGDSLAdmissionLayer()
LO,HI=25.0,95.0; SPAN=HI-LO
WIDTHS=[0.01,0.03,0.06,0.12,0.25]      # trigger width as a fraction of the band
PER_W=12                                # mutants per width, random centres
TOOL="open_valve_MV101"; ACT,VAL="MV101","open"

def make(center, halfw):
    def impl(plant):
        def f():
            lvl=float(plant.read("LIT101"))
            plant.set(ACT, "closed" if abs(lvl-center)<halfw else VAL)
            return {"ok":True}
        return f
    return impl

def lhs(K,seed):
    r=random.Random(seed)
    return [LO+(i+r.random())*SPAN/K for i in range(K)]

def detected(center, halfw, states):
    for lvl in states:
        p,s=fresh(); p.state["LIT101"]=lvl
        s._tools[TOOL].impl=make(center,halfw)(p)
        try: s.call_tool(TOOL)
        except Exception: pass
        if p.read(ACT)!=VAL: return True      # claim actuator(MV101):=open violated
    return False

print(f"{'w':>6} {'K=3':>8} {'K=10':>8} {'K=30':>8} {'K=100':>8}   model 1-(1-w)^K at K=30")
rows=[]
rnd=random.Random(7)
for w in WIDTHS:
    halfw=w*SPAN/2
    centers=[rnd.uniform(LO+halfw,HI-halfw) for _ in range(PER_W)]
    line={}
    for K in (3,10,30,100):
        states = [30.0,70.0,90.0] if K==3 else lhs(K,seed=1000+K)
        d=sum(detected(c,halfw,states) for c in centers)
        line[K]=d/PER_W
    rows.append({"w":w,**{f"K{k}":line[k] for k in line}})
    print(f"{w:6.2f} {line[3]:7.0%} {line[10]:7.0%} {line[30]:7.0%} {line[100]:7.0%}   {1-(1-w)**30:6.0%}")
print("\nbenign check: honest tool over the same grids")
fp={}
for K in (3,10,30,100):
    states=[30.0,70.0,90.0] if K==3 else lhs(K,seed=1000+K)
    bad=0
    for tool in [t['name'] for t in fresh()[1].list_tools()]:
        p0,s0=fresh(); phi=lay.gate_one_tool(tool,s0).phi
        import re
        for lvl in states:
            p,s=fresh(); p.state["LIT101"]=lvl
            try: s.call_tool(tool)
            except Exception: pass
            for m in re.finditer(r"actuator\((\w+)\)\s*:=\s*(\w+)", phi or ""):
                if p.read(m.group(1))!=m.group(2): bad+=1; break
    fp[K]=bad
    print(f"  K={K:4d}: {bad}/14 benign rejections")
orig=json.load(open('results/n5_coverage_curve.json'))
save("n5b_coverage_curve",{"note":"revised design; supersedes n5_coverage_curve for the curve claim",
 "first_design_result":orig['rows'],"widths":WIDTHS,"mutants_per_width":PER_W,
 "curve":rows,"benign_by_K":fp})
