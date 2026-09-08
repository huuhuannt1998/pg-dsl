"""N5: initial-state coverage curve for state-conditional mutants. Pre-registered N5.1-N5.4.
Replay from K Latin-hypercube initial states over (LIT101, LIT201); fit detection vs 1-(1-w)^K."""
import sys, json, time, random
sys.path.insert(0,'.')
from harness import *
import e11_mutation as E
m2a=sys.modules['_m2a_adm']; lay=E.PGDSLAdmissionLayer()
BAND1=(25.0,95.0); BAND2=(20.0,95.0)
TRIG_HALF=2.0   # mutants fire when |LIT101 - trigger| < 2.0
W = (2*TRIG_HALF)/(BAND1[1]-BAND1[0])

def lhs(K, seed=42):
    rnd=random.Random(seed)
    a=[BAND1[0]+(i+rnd.random())*(BAND1[1]-BAND1[0])/K for i in range(K)]
    b=[BAND2[0]+(i+rnd.random())*(BAND2[1]-BAND2[0])/K for i in range(K)]
    rnd.shuffle(b)
    return [{"name":f"S{i}","LIT101":round(a[i],2),"LIT201":round(b[i],2)} for i in range(K)]

def detect_at(tool, spec, states):
    """mutant is detected if the claim fails at ANY sampled state"""
    p0,s0=fresh(); s0._tools[tool].impl=E.build_impl(spec[0],spec[1],p0); s0._tools[tool]._mutant_spec=spec
    phi=lay.gate_one_tool(tool,s0).phi
    import re
    AR=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)")
    for st in states:
        p,s=fresh()
        for k,v in st.items():
            if k!="name" and k in p.state: p.state[k]=v
        s._tools[tool].impl=E.build_impl(spec[0],spec[1],p)
        try: s.call_tool(tool)
        except Exception: pass
        for m in AR.finditer(phi or ""):
            if p.read(m.group(1))!=m.group(2): return True
    return False

M6=[(t,k,pm) for t,k,pm in E.mutants() if k=="M6_state_conditional"]
CANON=[t['name'] for t in fresh()[1].list_tools()]
print(f"state-conditional mutants: {len(M6)} | trigger half-width {TRIG_HALF} -> w = {W:.4f}")
rows=[]
for K in (3,10,30,100):
    states = m2a.INITIAL_STATES if K==3 else lhs(K)
    t0=time.time()
    det=sum(detect_at(t,(k,pm),states) for t,k,pm in M6)
    # benign cost at this K
    import re
    AR=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)")
    fp=0
    for tool in CANON:
        p0,s0=fresh(); phi=lay.gate_one_tool(tool,s0).phi
        bad=False
        for st in states:
            p,s=fresh()
            for kk,vv in st.items():
                if kk!="name" and kk in p.state: p.state[kk]=vv
            try: s.call_tool(tool)
            except Exception: pass
            for m in AR.finditer(phi or ""):
                if p.read(m.group(1))!=m.group(2): bad=True
        fp+=bad
    exp=1-(1-W)**K
    el=time.time()-t0
    rows.append({"K":K,"detected":det,"n":len(M6),"rate":det/len(M6),
                 "predicted_1_minus_1_minus_w_K":round(exp,3),"benign_fp":fp,"seconds":round(el,1)})
    print(f"  K={K:4d}  detected {det:2d}/16 ({det/len(M6):5.1%})  model 1-(1-w)^K = {exp:5.1%}  benign FP {fp}/14  ({el:.1f}s)")
save("n5_coverage_curve",{"preregistered":"N5.1-N5.4","trigger_width_w":W,"rows":rows})
