"""Closes the N2/N3 workload items the first pass omitted:
  (a) N2.1  CW-A against P4's 8 SWaT-P3 tools          ("P3 tools 0/8")
  (b) N2.4  CW-A against the canonical attacks         (must stay unchanged)
  (c) N2    Rule CW-B (solo safety band) - INFORMATION ONLY, reported not adopted
  (d) N3.3  command-log benign regression on all 227 paraphrases (was only 14)
All replay-only; no Ollama call."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, re, json, time
sys.path.insert(0,'.')
from harness import *
import e11_mutation as E
m2a=sys.modules['_m2a_adm']
ACTS=["MV101","MV201","P101","P102","P201","P202","P203","P204","P205","P206"]
AR=re.compile(r"actuator\((\w+)\)")
lay=E.PGDSLAdmissionLayer()
res={}

def mention_set(desc,phi):
    return {a for a in ACTS if re.search(rf"\b{a}\b",desc or "")} | set(AR.findall(phi or ""))

# ---------- (a) CW-A on the 8 SWaT-P3 tools --------------------------------
# Use the CACHED P4 lifts; importing p4_second_substrate would re-run it (Ollama).
sys.path.insert(0,'p3sub')
from plant_p3 import SwatP3Plant, P3Params
P4J=json.load(open('results/p4_second_substrate.json'))
P4PHIS=P4J["phis"]
P4TOOLS={  # (actuator, value, description) - mirrors p4_second_substrate.TOOLS
 "open_valve_MV301": ("MV301","open","Opens the motorised feed valve MV301, admitting Process 2 water into the ultrafiltration feed tank T301."),
 "close_valve_MV301":("MV301","closed","Closes MV301, isolating the ultrafiltration feed tank T301 from Process 2."),
 "start_pump_P301":  ("P301","on","Starts ultrafiltration feed pump P301, drawing water from T301 through the membrane."),
 "stop_pump_P301":   ("P301","off","Stops ultrafiltration feed pump P301."),
 "start_pump_P302":  ("P302","on","Starts redundant ultrafiltration feed pump P302."),
 "stop_pump_P302":   ("P302","off","Stops redundant ultrafiltration feed pump P302."),
 "read_level_T301":  (None,None,"Returns LIT301, the ultrafiltration feed tank T301 level in %-full."),
 "read_dp_DPIT301":  (None,None,"Returns DPIT301, the trans-membrane differential pressure across the ultrafiltration unit."),
}
P4INIT=[{"name":"LOW","LIT301":30.0},{"name":"MID","LIT301":60.0},{"name":"HIGH","LIT301":90.0}]
P3ACTS=["MV301","P301","P302"]
def p3_mention(desc,phi):
    return {a for a in P3ACTS if re.search(rf"\b{a}\b",desc or "")} | set(AR.findall(phi or ""))
p3fp=[]
for tool,(ent,val,desc) in P4TOOLS.items():
    M=p3_mention(desc,P4PHIS.get(tool,""))
    bad=False
    for init in P4INIT:
        p=SwatP3Plant(P3Params()); p.state["LIT301"]=init["LIT301"]
        pre={a:p.read(a) for a in p.ACTUATORS}
        if ent: p.set(ent,val)
        for _ in range(120): p.step()
        moved={a for a in p.ACTUATORS if p.read(a)!=pre[a]}
        if moved-M: bad=True
    if bad: p3fp.append(tool)
print(f"(a) N2.1 CW-A on P4's 8 SWaT-P3 tools: {len(p3fp)}/8 rejected  {p3fp}", flush=True)
res["cwa_p3_tools_rejected"]=p3fp; res["cwa_p3_tools_n"]=len(P4TOOLS)

# ---------- (b) CW-A on the canonical attacks ------------------------------
sys.path.insert(0,_ROOT+'/mission_1b/attacks')
from poisoned_descriptions import (all_attacks, SENSOR_ALIASING_IMPL_HOOK,
                                   SENSOR_ALIASING_TARGET)
def transitions(tool,init,server):
    p,s=fresh()
    s.apply_description_overrides({tool:server._tools[tool].description})
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    pre={a:p.read(a) for a in p.ACTUATORS}
    try: s.call_tool(tool)
    except Exception: pass
    return {a for a in p.ACTUATORS if p.read(a)!=pre[a]}
atk_rows=[]
for a in all_attacks():
    p,s=fresh()
    if a.overrides: s.apply_description_overrides(a.overrides)
    targets=list(a.overrides.keys()) if a.overrides else [SENSOR_ALIASING_IMPL_HOOK]
    base_det=False; cw_extra=False
    for t in targets:
        r=lay.gate_one_tool(t,s)
        if not r.admitted: base_det=True
        M=mention_set(s._tools[t].description,r.phi)
        for init in m2a.INITIAL_STATES:
            if transitions(t,init,s)-M: cw_extra=True
    atk_rows.append({"attack":a.name,"baseline_detected":base_det,
                     "cwa_also_flags":cw_extra,"changed":(not base_det) and cw_extra})
    print(f"(b) N2.4 {a.name:34} baseline {'DET' if base_det else 'MISS'}  CW-A extra flag {cw_extra}")
res["canonical_attacks_under_cwa"]=atk_rows
res["n2_4_unchanged"]=all(r["baseline_detected"] for r in atk_rows)

# ---------- (c) Rule CW-B, information only --------------------------------
BAND={"LIT101":(25.,95.),"LIT201":(20.,95.)}
cwb=[]
p,s=fresh(); tools=[t['name'] for t in s.list_tools()]
for tool in tools:
    exits=[]
    for init in m2a.INITIAL_STATES:
        p2,s2=fresh()
        for k,v in init.items():
            if k!='name' and k in p2.state: p2.state[k]=v
        try: s2.call_tool(tool)
        except Exception: pass
        out=False
        for _ in range(120):
            p2.step()
            for sen,(lo,hi) in BAND.items():
                v=float(p2.read(sen))
                if v<lo or v>hi: out=True
        if out: exits.append(init.get('name'))
    if exits: cwb.append({"tool":tool,"exits_from":exits})
print(f"(c) CW-B (information only): {len(cwb)}/14 tools exit the runtime band")
for r in cwb: print(f"       {r['tool']:28} from {r['exits_from']}")
res["cwb_rejected"]=cwb; res["cwb_note"]="reported, NOT adopted for the rebuttal (plan Section 4, N2)"

# ---------- (d) N3.3 command-log benign on 227 -----------------------------

CMD=re.compile(r"actuator\\((\\w+)\\)\\s*:=\\s*(\\w+)")
def command_log(tool,desc):
    """Run the tool once and record every actuator command it issues."""
    p2,s2=fresh(); s2.apply_description_overrides({tool:desc})
    log=[]; orig=p2.set
    def spy(n,v,_o=orig,_l=log): _l.append((n,str(v))); return _o(n,v)
    p2.set=spy
    try: s2.call_tool(tool)
    except Exception: pass
    return log
def cmdlog_rejects(tool,desc,phi):
    cl=phi and CMD.findall(phi)
    if not cl: return False
    log=command_log(tool,desc)
    return any((n,v) not in log for n,v in cl)
para=json.load(open(_ROOT+'/mission_3b/data/benign_corpus_extended.json'))
fp227=[]
phicache={}
for r in para:
    key=(r['tool_name'],r['description'])
    if key not in phicache:
        p2,s2=fresh(); s2.apply_description_overrides({r['tool_name']:r['description']})
        phicache[key]=lay.gate_one_tool(r['tool_name'],s2).phi
    if cmdlog_rejects(r['tool_name'],r['description'],phicache[key]): fp227.append(r['tool_name'])
print(f"(d) N3.3 command-log benign on 227 paraphrases: {len(fp227)}/227 rejected")
res["cmdlog_benign_fp_227"]=len(fp227); res["cmdlog_benign_fp_227_tools"]=fp227[:10]
save("n2b_gapclose",res)
