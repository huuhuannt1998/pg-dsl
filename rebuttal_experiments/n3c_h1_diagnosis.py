"""N3.1 done properly: the prescribed per-mutant x per-state dump, with a COMPUTED
H1/H2/H3 classification. The earlier n3_command_log.json carried n3_1_all_H1=True as a
hardcoded literal with no classification code behind it; this supersedes that field.

H1 post-state coincidence : the claimed actuator ALREADY sits at the claimed value before
                            the call, so the post-state check cannot distinguish
                            "set it" from "it was already so".
H2 lifter error           : phi does not name the honest tool's actuator.
H3 shared state variable  : the mutated actuator and the claimed actuator are the same name.
"""
import sys, re, json
sys.path.insert(0,'.')
from harness import *
import e11_mutation as E
m2a=sys.modules['_m2a_adm']
AR=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)")
assert AR.findall("actuator(MV101) := open")==[("MV101","open")]
lay=E.PGDSLAdmissionLayer()

def replay(tool, init, spec):
    p,s=fresh()
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    pre={a:p.read(a) for a in p.ACTUATORS}
    log=[]; o=p.set; p.set=lambda n,v:(log.append((n,str(v))),o(n,v))[1]
    s._tools[tool].impl=E.build_impl(spec[0],spec[1],p)
    try: s.call_tool(tool)
    except Exception: pass
    p.set=o
    return pre, {a:p.read(a) for a in p.ACTUATORS}, log

rows=[]; miss=[]
for tool,kind,prm in E.mutants():
    if kind!="M1_actuator_swap": continue
    p,s=fresh(); s._tools[tool].impl=E.build_impl(kind,prm,p); s._tools[tool]._mutant_spec=(kind,prm)
    r=lay.gate_one_tool(tool,s); phi=r.phi
    detected_poststate = not r.admitted
    claims=AR.findall(phi or "")
    per=[]
    for init in m2a.INITIAL_STATES:
        pre,post,log=replay(tool,init,(kind,prm))
        per.append({"state":init.get("name"),"actuator_pre":pre,"actuator_post":post,
                    "command_log":log,"phi":phi})
    # classify only the MISSES
    cls=None; why=None
    if not detected_poststate:
        n,v = claims[0] if claims else (None,None)
        already = all(str(x["actuator_pre"].get(n))==v for x in per)
        h2 = (n is None) or (n not in p.ACTUATORS)
        h3 = (n == prm.get("other"))
        if already and not h2 and not h3: cls,why="H1", f"{n} already == '{v}' at LOW/MID/HIGH before the call"
        elif h2: cls,why="H2", "phi does not name a real actuator"
        elif h3: cls,why="H3", "claimed and mutated actuator are the same name"
        else: cls,why="UNEXPLAINED", "none of H1/H2/H3 holds"
        miss.append({"tool":tool,"phi":phi,"class":cls,"why":why,
                     "claimed":list(claims),"mutated_to":prm.get("other")})
    rows.append({"tool":tool,"phi":phi,"claims":claims,"detected_poststate":detected_poststate,
                 "classification":cls,"why":why,"per_state":per})

print(f"actuator-swap mutants: {len(rows)}   post-state misses: {len(miss)}")
for m in miss: print(f"   {m['tool']:26} {m['class']}  -- {m['why']}")
all_h1 = bool(miss) and all(m["class"]=="H1" for m in miss)
print(f"\nN3.1 (all misses classify as H1): {'CONFIRMED' if all_h1 else 'NOT CONFIRMED'}  [COMPUTED, not asserted]")
save("n3c_h1_diagnosis",{"supersedes":"n3_command_log.json field n3_1_all_H1 (was a hardcoded literal)",
 "n_mutants":len(rows),"n_poststate_misses":len(miss),"misses":miss,
 "n3_1_all_H1_computed":all_h1,"rows":rows})
