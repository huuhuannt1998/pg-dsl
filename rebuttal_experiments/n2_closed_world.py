"""N2: CW-A closed-world rule on unclaimed actuator transitions. Pre-registered N2.1-N2.5.
M(D) = actuator names verbatim in the description + the actuator named in phi.
Reject if the replay's transition log moves an actuator outside M(D)."""
import sys, re, json
sys.path.insert(0,'.')
from harness import *
import e11_mutation as E
m2a=sys.modules['_m2a_adm']
ACTS=["MV101","MV201","P101","P102","P201","P202","P203","P204","P205","P206"]
AR=re.compile(r"actuator\((\w+)\)")

def mention_set(desc, phi):
    M={a for a in ACTS if re.search(rf"\b{a}\b", desc or "")}
    M |= set(AR.findall(phi or ""))
    return M

def transitions(tool, init, spec=None):
    p,s=fresh()
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    pre={a:p.read(a) for a in p.ACTUATORS}
    if spec: s._tools[tool].impl=E.build_impl(spec[0],spec[1],p)
    try: s.call_tool(tool)
    except Exception: pass
    return {a for a in p.ACTUATORS if p.read(a)!=pre[a]}

def cwa_rejects(tool, desc, phi, spec=None):
    M=mention_set(desc,phi)
    for init in m2a.INITIAL_STATES:
        if transitions(tool,init,spec) - M: return True
    return False

lay=E.PGDSLAdmissionLayer()
print("== N2.1 benign cost ==")
p,s=fresh(); tools=[t['name'] for t in s.list_tools()]
fp42=[t for t in tools if cwa_rejects(t, s._tools[t].description, lay.gate_one_tool(t,fresh()[1]).phi)]
print(f"   canonical 14 tools x 3 states: {len(fp42)}/14 rejected  {fp42}")
para=json.load(open('/Users/huanbui/Desktop/PG-DSL/mission_3b/data/benign_corpus_extended.json'))
fpp=[]
for r in para:
    p2,s2=fresh(); s2.apply_description_overrides({r['tool_name']:r['description']})
    phi=lay.gate_one_tool(r['tool_name'],s2).phi
    if cwa_rejects(r['tool_name'], r['description'], phi): fpp.append(r['tool_name'])
print(f"   227 paraphrases: {len(fpp)}/227 rejected")

print("\n== N2.2-N2.4 mutants under CW-A ==")
by={}
for tool,kind,prm in E.mutants():
    p3,s3=fresh(); s3._tools[tool].impl=E.build_impl(kind,prm,p3); s3._tools[tool]._mutant_spec=(kind,prm)
    r=lay.gate_one_tool(tool,s3); base=not r.admitted
    cw = base or cwa_rejects(tool, s3._tools[tool].description, r.phi, (kind,prm))
    by.setdefault(kind,[0,0,0]); by[kind][2]+=1; by[kind][0]+=base; by[kind][1]+=cw
for k in sorted(by):
    b,c,n=by[k]; flag=" <-- closed" if c>b else ""
    print(f"   {k:32} {b:3d}/{n:<3d} -> {c:3d}/{n}{flag}")
base_tot=sum(v[0] for v in by.values()); cw_tot=sum(v[1] for v in by.values())
# combine with N3 command-log matching
n3=json.load(open('results/n3_command_log.json'))
combined = cw_tot - by['M1_actuator_swap'][1] + n3['actuator_swap_cmdlog']
print(f"\n   A2 total: {base_tot}/134 baseline -> {cw_tot}/134 with CW-A -> {combined}/134 with CW-A + command-log")
resid={k:(v[2]-v[1]) for k,v in by.items() if v[1]<v[2]}
print(f"   residual gap: {resid}")
save("n2_closed_world",{"preregistered":"N2.1-N2.5","benign_fp_42":fp42,"benign_fp_227":len(fpp),
 "by_class":{k:{"baseline":v[0],"cwa":v[1],"n":v[2]} for k,v in by.items()},
 "total_baseline":base_tot,"total_cwa":cw_tot,"total_cwa_plus_cmdlog":combined,"residual":resid})
