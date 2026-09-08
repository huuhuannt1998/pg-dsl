"""N3.2/N3.3: command-log matching. actuator(N):=v passes iff the replay's command log
contains a command to N with value v (post-state retained as secondary). Pre-registered."""
import sys, re, json
sys.path.insert(0,'.')
from harness import *
import e11_mutation as E
m2a=sys.modules['_m2a_adm']
AR=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)")

def replay_with_log(tool, init, spec=None):
    p,s=fresh()
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    log=[]
    orig=p.set
    p.set=lambda n,v: (log.append((n,v)), orig(n,v))[1]
    if spec: s._tools[tool].impl=E.build_impl(spec[0],spec[1],p)
    try: s.call_tool(tool)
    except Exception: pass
    p.set=orig
    return log, {a:p.read(a) for a in p.ACTUATORS}

def admits_cmdlog(tool, phi, spec=None):
    """reject if any claimed actuator command is absent from the log"""
    for init in m2a.INITIAL_STATES:
        log,post=replay_with_log(tool,init,spec)
        for m in AR.finditer(phi or ""):
            n,v=m.group(1),m.group(2)
            if (n,v) not in log: return False
    return True

lay=E.PGDSLAdmissionLayer()
print("== N3.2: actuator-swap under command-log matching ==")
det=0; rows=[]
for tool,kind,prm in E.mutants():
    if kind!="M1_actuator_swap": continue
    p,s=fresh(); s._tools[tool].impl=E.build_impl(kind,prm,p); s._tools[tool]._mutant_spec=(kind,prm)
    phi=lay.gate_one_tool(tool,s).phi
    caught = not admits_cmdlog(tool,phi,(kind,prm)); det+=caught
    rows.append({"tool":tool,"phi":phi,"detected_cmdlog":caught})
    print(f"   {tool:24} {'DETECTED' if caught else 'missed'}")
print(f"   command-log matching: {det}/8   (post-state was 4/8)")

print("\n== N3.3: benign regression, 14 canonical tools ==")
fp=[]
for tool in [t['name'] for t in fresh()[1].list_tools()]:
    p,s=fresh(); phi=lay.gate_one_tool(tool,s).phi
    if not admits_cmdlog(tool,phi): fp.append(tool)
print(f"   benign false positives: {len(fp)}/14  {fp}")

print("\n== N3.4: other E11 classes unchanged? ==")
other={}
for tool,kind,prm in E.mutants():
    if kind=="M1_actuator_swap": continue
    p,s=fresh(); s._tools[tool].impl=E.build_impl(kind,prm,p); s._tools[tool]._mutant_spec=(kind,prm)
    r=lay.gate_one_tool(tool,s)
    base=not r.admitted
    cl = base or (not admits_cmdlog(tool,r.phi,(kind,prm)))
    other.setdefault(kind,[0,0,0]); other[kind][2]+=1
    other[kind][0]+=base; other[kind][1]+=cl
for k in sorted(other):
    b,c,n=other[k]; print(f"   {k:32} baseline {b:3d}/{n:<3d} -> with cmd-log {c:3d}/{n}")
new_total=det+sum(v[1] for v in other.values())
print(f"\n   A2 total: 70/134 -> {new_total}/134 with command-log matching alone")
save("n3_command_log",{"preregistered":"N3.1-N3.4","n3_1_all_H1":True,
  "actuator_swap_postState":4,"actuator_swap_cmdlog":det,"benign_fp":fp,
  "by_class_baseline_vs_cmdlog":{k:{"baseline":v[0],"cmdlog":v[1],"n":v[2]} for k,v in other.items()},
  "new_total":new_total,"rows":rows})
