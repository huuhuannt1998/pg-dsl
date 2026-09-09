"""Q3, corrected: combined benign cost on the 227 corpus under CACHED qwen3 lifts,
with the command log captured over the SAME replay the admission layer performs
(dt_verifier.verify_tool), including its set_dosing_rate pre-condition call.

Supersedes n6_combined_benign227.py, whose direct call_tool() replay omitted the
pre-condition and therefore reported a spurious 19/227."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, re, json
sys.path.insert(0,'.')
from harness import *
import importlib.util as ilu
m2a=sys.modules['_m2a_adm']
sp=ilu.spec_from_file_location("_dtv4",_ROOT+"/mission_2a/dt_verifier/dt_verifier.py")
mv=ilu.module_from_spec(sp); sys.modules["_dtv4"]=mv; sp.loader.exec_module(mv)
verify_tool, INIT = mv.verify_tool, mv.INITIAL_STATES

dec=json.load(open(_ROOT+'/mission_3b/results/per_style_canonical_extended_qwen3.json'))['decisions']
corpus=json.load(open(_ROOT+'/mission_3b/data/benign_corpus_extended.json'))
def full_desc(d):
    pre=d['description_excerpt'].rstrip('.').rstrip('…')[:60]
    for c in corpus:
        if c['tool_name']==d['tool_name'] and c['description'].startswith(pre[:40]):
            return c['description']
    return None

ACTS=["MV101","MV201","P101","P102","P201","P202","P203","P204","P205","P206"]
AR=re.compile(r"actuator\((\w+)\)"); CMD=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)")
assert CMD.findall("actuator(P201) := on")==[("P201","on")]
SYN={"on":"open","open":"open","off":"closed","closed":"closed"}
norm=lambda v: SYN.get(str(v).lower(),str(v).lower())

def replay_like_admission(tool, desc, init):
    """Exactly the admission layer's replay, with plant.set instrumented."""
    p,s=fresh(); s.apply_description_overrides({tool:desc})
    log=[]; orig=p.set
    p.set=lambda n,v:(log.append((n,str(v))), orig(n,v))[1]
    pre={a:p.read(a) for a in p.ACTUATORS}
    args={"rate":1.0} if tool=="set_dosing_rate" else None
    try: verify_tool(s, tool, init, tool_args_override=args)
    except Exception: pass
    p.set=orig
    moved={a for a in p.ACTUATORS if p.read(a)!=pre[a]}
    return log, moved

rows=[]
for d in dec:
    desc=full_desc(d)
    if desc is None: continue
    phi=d.get('phi') or ''
    shipped=not d.get('admitted',True)
    M={a for a in ACTS if re.search(rf"\b{a}\b",desc)} | set(AR.findall(phi))
    claims=CMD.findall(phi)
    cwa=False; clog=False
    for init in INIT:
        log,moved=replay_like_admission(d['tool_name'],desc,init)
        if moved-M: cwa=True
        ln=[(a,norm(b)) for a,b in log]
        for n,v in claims:
            if (n,norm(v)) not in ln: clog=True
    rows.append({"tool":d['tool_name'],"style":d.get('style'),"phi":phi,
                 "shipped":shipped,"cwa":cwa,"cmdlog":clog,
                 "union":bool(shipped or cwa or clog)})
S=sum(r['shipped'] for r in rows); A=sum(r['cwa'] for r in rows)
C=sum(r['cmdlog'] for r in rows); U=sum(r['union'] for r in rows)
print(f"joined {len(rows)}/227   (command log captured over verify_tool's full replay)")
print(f"\n  shipped (cached qwen3)       : {S}/227")
print(f"  CW-A alone                   : {A}/227")
print(f"  command-log alone            : {C}/227")
print(f"  UNION (shipped + both rules) : {U}/227")
print(f"  rules ADD                    : {U-S} beyond shipped")
for r in rows:
    if r['union']:
        print(f"    {r['tool']:22} {str(r['style']):7} by={[k for k in ('shipped','cwa','cmdlog') if r[k]]}")
save("n6b_combined_benign227",{"question":"advisor Q3 (corrected replay path)",
 "supersedes":"n6_combined_benign227.json (direct call_tool omitted the set_dosing_rate pre-condition)",
 "lifter":"cached qwen3:14b lifts; replay via dt_verifier.verify_tool",
 "shipped":S,"cwa_alone":A,"cmdlog_alone":C,"union":U,"added_by_rules":U-S,
 "rows":[r for r in rows if r['union']]})
