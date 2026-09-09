"""Q3 (advisor): combined benign cost of BOTH verifier fixes on the 227-paraphrase
corpus, replayed against the CACHED qwen3 lifts so the denominator matches the paper's
headline 1/227 (which is the qwen3 pipeline, not the stub).

Reports, per rule and as a UNION with the shipped rejection:
  shipped        : cached canonical qwen3 admission verdict
  CW-A           : reject if the replay moves an actuator outside M(D)
  command-log    : reject if a claimed actuator command is absent from the replay log
Scoring fixed before the run. Replay-only; no Ollama call."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, re, json
sys.path.insert(0,'.')
from harness import *
m2a=sys.modules['_m2a_adm']

CACHE=_ROOT+'/mission_3b/results/per_style_canonical_extended_qwen3.json'
CORPUS=_ROOT+'/mission_3b/data/benign_corpus_extended.json'
dec=json.load(open(CACHE))['decisions']
corpus=json.load(open(CORPUS))
assert len(dec)==227 and len(corpus)==227, (len(dec),len(corpus))

# join cached decision -> full description via the excerpt prefix
by_prefix={}
for c in corpus:
    by_prefix[(c['tool_name'], c['description'][:60])]=c['description']
def full_desc(d):
    pre=d['description_excerpt'].rstrip('.').rstrip('…')[:60]
    k=(d['tool_name'], pre)
    if k in by_prefix: return by_prefix[k]
    for c in corpus:
        if c['tool_name']==d['tool_name'] and c['description'].startswith(pre[:40]):
            return c['description']
    return None

ACTS=["MV101","MV201","P101","P102","P201","P202","P203","P204","P205","P206"]
AR=re.compile(r"actuator\((\w+)\)")
CMD=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)")
assert CMD.findall("actuator(MV101) := open")==[("MV101","open")]
SYN={"on":"open","open":"open","off":"closed","closed":"closed"}
norm=lambda v: SYN.get(str(v).lower(), str(v).lower())

def replay(tool, desc, init):
    p,s=fresh(); s.apply_description_overrides({tool:desc})
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    pre={a:p.read(a) for a in p.ACTUATORS}
    log=[]; o=p.set
    p.set=lambda n,v:(log.append((n,str(v))),o(n,v))[1]
    try: s.call_tool(tool)
    except Exception: pass
    p.set=o
    moved={a for a in p.ACTUATORS if p.read(a)!=pre[a]}
    return log, moved

rows=[]; unmatched=0
for d in dec:
    desc=full_desc(d)
    if desc is None: unmatched+=1; continue
    phi=d.get('phi') or ''
    shipped = not d.get('admitted', True)
    M={a for a in ACTS if re.search(rf"\b{a}\b", desc)} | set(AR.findall(phi))
    claims=CMD.findall(phi)
    cwa=False; clog=False
    for init in m2a.INITIAL_STATES:
        log,moved=replay(d['tool_name'], desc, init)
        if moved - M: cwa=True
        for n,v in claims:
            if (n,norm(v)) not in [(a,norm(b)) for a,b in log]: clog=True
    rows.append({"tool":d['tool_name'],"style":d.get('style'),"source":d.get('source'),
                 "phi":phi,"shipped":shipped,"cwa":cwa,"cmdlog":clog,
                 "union":bool(shipped or cwa or clog)})
print(f"joined {len(rows)}/227 (unmatched {unmatched})")
S=sum(r['shipped'] for r in rows); A=sum(r['cwa'] for r in rows); C=sum(r['cmdlog'] for r in rows)
U=sum(r['union'] for r in rows)
print(f"\n  shipped (cached qwen3)      : {S}/227")
print(f"  CW-A alone                  : {A}/227")
print(f"  command-log alone           : {C}/227")
print(f"  UNION (shipped + both rules): {U}/227")
print(f"\n  rules ADD {U-S} rejection(s) beyond the shipped baseline")
for r in rows:
    if r['union']:
        who=[k for k in ('shipped','cwa','cmdlog') if r[k]]
        print(f"    {r['tool']:24} {str(r['style']):7} by={who}  phi={r['phi'][:58]!r}")
save("n6_combined_benign227",{"question":"advisor Q3: combined benign cost on 227 under cached qwen3 lifts",
 "lifter":"cached qwen3:14b lifts from per_style_canonical_extended_qwen3.json (replay-only)",
 "joined":len(rows),"shipped":S,"cwa_alone":A,"cmdlog_alone":C,"union":U,"added_by_rules":U-S,
 "rows":[r for r in rows if r['union']]})
