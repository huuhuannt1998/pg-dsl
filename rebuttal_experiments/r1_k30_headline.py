"""E1 (revision-pass III) - headline numbers at the ADOPTED grid, K=30.
Pre-registered in PREREGISTRATION_R.md before this run.

Mechanism: every loaded copy of the shipped admission layer resolves INITIAL_STATES from its
module globals at call time, so overriding that attribute runs the SHIPPED per-tool verifier
and matcher over 30 Latin-hypercube initial states with no code change. The composition pass
keeps its own published 3-state grid (DEFAULT_INITIAL_STATES) so that the per-tool K effect is
isolated. harness.save is redirected so the K=3 result files are never overwritten."""
import sys, json, random, time, re
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
import harness as H
from harness import *
ROOT='/Users/huanbui/Desktop/PG-DSL'
for p in (ROOT, f'{ROOT}/mission_1b', f'{ROOT}/mission_2a', f'{ROOT}/mission_2b', f'{ROOT}/mission_3b'):
    sys.path.insert(0,p)

K=30
def lhs2d(K, seed):
    r=random.Random(seed)
    a=[25.0+(i+r.random())*70.0/K for i in range(K)]     # LIT101 over its safe band [25,95]
    b=[20.0+(i+r.random())*75.0/K for i in range(K)]     # LIT201 over its safe band [20,95]
    r.shuffle(b)
    return [{"name":f"LHS{i:02d}","LIT101":round(a[i],3),"LIT201":round(b[i],3),
             "MV101":"closed","P101":"off","MV201":"closed","P201":"off","AIT201":0.30}
            for i in range(K)]
STATES=lhs2d(K, seed=1030)

_save=H.save
H.save=lambda name,obj: _save("k30_"+name, obj)          # never clobber the K=3 artifacts

# load the canonical layer FIRST so its private copy of the admission module exists to be overridden
from mission_3b.admission_layer import PGDSLCanonicalLayer, detected_at_admission
from mission_3b.admission_layer.pgdsl_canonical import PGDSLAdmissionLayer as CanonAdm
from mission_3b.attacks.z3_simulator import make_z3_simulator, Z3_TOOL_SEQUENCE
from evaluation.run_t3_composition import SIMULATORS as M2B_SIMULATORS

def override_states():
    hit=[]
    for name,mod in list(sys.modules.items()):
        if mod is None: continue
        try:
            v=getattr(mod,'INITIAL_STATES',None)
            if isinstance(v,list) and v and isinstance(v[0],dict) and 'name' in v[0]:
                setattr(mod,'INITIAL_STATES',STATES); hit.append(name)
        except Exception: pass
    return hit
hit=override_states(); print("INITIAL_STATES overridden in modules:", hit)
assert any('adm' in h or 'dtv' in h or 'admission' in h for h in hit), "override did not reach the admission layer"

t0=time.time()
import e11_mutation as E          # runs the 134-mutant battery NOW, at K=30, via m2a.INITIAL_STATES
shipped_by={k:{"detected":v[0],"n":v[1]} for k,v in E.by.items()}
shipped_tot, shipped_n = E.tot, E.n
print(f"\n[c] shipped matcher at K={K}: {shipped_tot}/{shipped_n}  ({time.time()-t0:.0f}s)")

# ---- (b) benign: 14 honest tools x 30 states through the SHIPPED layer ----
lay=E.PGDSLAdmissionLayer()
p,s=fresh(); cells={}
for r in lay.gate_all_tools(s):
    for d in r.decision_per_initial_state:
        cells[(r.tool_name,d.get("initial_state_name"))]=bool(d.get("admitted"))
rejected=[f"{k[0]}@{k[1]}" for k,v in cells.items() if not v]
print(f"[b] benign: {len(rejected)}/{len(cells)} rejected  {rejected[:6]}")

# ---- (a) canonical 8 through the canonical layer (per-tool at K=30, composition at its 3) ----
TOOL_SEQ={"W1":["close_valve_MV101"],"W2":[],"Z1":["open_valve_MV201"],
          "Z2":["start_dosing_pump_P201","set_dosing_rate"],"Z3":Z3_TOOL_SEQUENCE}
POISONED={"A1":{"open_valve_MV101","close_valve_MV101"},"A2":{"set_dosing_rate"},
          "A3":{"read_level_T101"},"W1":set(),"W2":set(),"Z1":set(),"Z2":{"set_dosing_rate"},"Z3":set()}
IDS=("A1","A2","A3","W1","W2","Z1","Z2","Z3")
def seq_for(aid, sim_factory):
    if aid in TOOL_SEQ: return TOOL_SEQ[aid]
    sf, rt, _ = sim_factory(); calls=[]
    try:
        srv=sf(); orig=srv.call_tool
        def spy(n,a=None,_o=orig,_c=calls): _c.append(n); return _o(n,a)
        srv.call_tool=spy; rt(srv)
    except Exception: pass
    return calls
sims=dict(M2B_SIMULATORS); sims["Z3"]=make_z3_simulator
layer=PGDSLCanonicalLayer(per_tool_layer=CanonAdm(), mode="stub")
canon={}
for aid in IDS:
    sf, rt, pois = sims[aid]()
    rep=layer.gate_all_tools(sf)
    det=detected_at_admission(rep, pois or POISONED[aid], seq_for(aid, sims[aid]))
    canon[aid]={"detected":det["detected"],"via":det["via"],
                "n_states_per_tool":len(rep.per_tool[0].decision_per_initial_state) if rep.per_tool else None}
print("[a] canonical:", {a:('DET' if canon[a]['detected'] else 'MISS') for a in IDS},
      "| states/tool:", canon['A1']['n_states_per_tool'])

# ---- (d) the two hardened rules at K=30 (inline copies of n3/n2, iterating the overridden states) ----
AR_CMD=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)"); AR_ACT=re.compile(r"actuator\((\w+)\)")
ACTS=["MV101","MV201","P101","P102","P201","P202","P203","P204","P205","P206"]
def replay_with_log(tool, init, spec=None):
    p,s=fresh()
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    log=[]; orig=p.set
    p.set=lambda n,v: (log.append((n,v)), orig(n,v))[1]
    pre={a:p.read(a) for a in p.ACTUATORS}
    if spec: s._tools[tool].impl=E.build_impl(spec[0],spec[1],p)
    try: s.call_tool(tool)
    except Exception: pass
    p.set=orig
    return log, {a for a in p.ACTUATORS if p.read(a)!=pre[a]}
def cmdlog_rejects(tool, phi, spec=None):
    for init in STATES:
        log,_=replay_with_log(tool,init,spec)
        for m in AR_CMD.finditer(phi or ""):
            if (m.group(1),m.group(2)) not in log: return True
    return False
def cwa_rejects(tool, desc, phi, spec=None):
    M={a for a in ACTS if re.search(rf"\b{a}\b", desc or "")} | set(AR_ACT.findall(phi or ""))
    for init in STATES:
        _,moved=replay_with_log(tool,init,spec)
        if moved-M: return True
    return False
hard_by={}
for row,(tool,kind,prm) in zip(E.rows, E.mutants()):
    assert row["tool"]==tool and row["class"]==kind
    p3,s3=fresh(); s3._tools[tool].impl=E.build_impl(kind,prm,p3); s3._tools[tool]._mutant_spec=(kind,prm)
    phi=lay.gate_one_tool(tool,s3).phi; desc=s3._tools[tool].description
    base=row["detected"]
    hard = base or cmdlog_rejects(tool,phi,(kind,prm)) or cwa_rejects(tool,desc,phi,(kind,prm))
    hard_by.setdefault(kind,[0,0,0]); hard_by[kind][2]+=1; hard_by[kind][0]+=base; hard_by[kind][1]+=hard
hard_tot=sum(v[1] for v in hard_by.values())
# benign cost of the hardened rules at K=30
hfp=[]
for tool in [t['name'] for t in fresh()[1].list_tools()]:
    p4,s4=fresh(); phi=lay.gate_one_tool(tool,s4).phi
    if cmdlog_rejects(tool,phi) or cwa_rejects(tool,s4._tools[tool].description,phi): hfp.append(tool)
print(f"[d] hardened at K={K}: {hard_tot}/{shipped_n}   benign cost {len(hfp)}/14 {hfp}")
print("    per class (shipped -> hardened):")
for k in sorted(hard_by): b,h,n=hard_by[k]; print(f"      {k:32} {b:3d} -> {h:3d} / {n}")

k3=json.load(open('results/e11_mutation_coverage.json'))['by_class']
pred={"P1_canonical_6of8": sum(canon[a]['detected'] for a in IDS)==6 and not canon['W1']['detected'] and not canon['W2']['detected'],
      "P2_benign_0": len(rejected)==0,
      "P3_shipped_86": shipped_tot==86 and shipped_by['M6_state_conditional']['detected']==16
                        and all(shipped_by[c]['detected']==k3[c]['detected'] for c in k3 if c!='M6_state_conditional'),
      "P4_hardened_110": hard_tot==110}
print("\npredictions:", pred, f"  ({time.time()-t0:.0f}s total)")
_save("r1_k30_headline",{"preregistered":"PREREGISTRATION_R.md E1","K":K,"lhs_seed":1030,"states":STATES,
  "composition_grid":"published 3 states (unchanged)",
  "canonical":canon,"benign":{"n_cells":len(cells),"rejected":rejected},
  "shipped":{"total":shipped_tot,"n":shipped_n,"by_class":shipped_by},
  "hardened":{"total":hard_tot,"by_class":{k:{"shipped":v[0],"hardened":v[1],"n":v[2]} for k,v in hard_by.items()},
              "benign_fp_14":hfp},
  "k3_reference":{"shipped":70,"hardened":94,"by_class":k3},
  "predictions":pred,"seconds":time.time()-t0})
