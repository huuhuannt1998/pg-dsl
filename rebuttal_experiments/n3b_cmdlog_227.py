"""HONEST re-measurement of N3.3's 227-paraphrase denominator.

The earlier figure in n2b_gapclose.json ("cmdlog_benign_fp_227": 0) is VACUOUS: that script's
CMD regex was written with doubled backslashes, so it matched nothing and every row passed
trivially. This script reuses n3_command_log.py's own (correct) AR regex and its exact
matching semantics, and reports BOTH:
  (1) LITERAL matching, exactly as the plan specifies
  (2) VALUE-NORMALISED matching (open==on, closed==off), disclosed as a rule change
"""
import sys, re, json
sys.path.insert(0,'.')
from harness import *
import e11_mutation as E
m2a=sys.modules['_m2a_adm']
AR=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)")
assert AR.findall("actuator(MV101) := open")==[("MV101","open")], "regex sanity check failed"
SYN={"on":"open","open":"open","off":"closed","closed":"closed"}
def norm(v): return SYN.get(str(v).lower(), str(v).lower())

def replay_with_log(tool, desc, init):
    p,s=fresh(); s.apply_description_overrides({tool:desc})
    for k,v in init.items():
        if k!='name' and k in p.state: p.state[k]=v
    log=[]; orig=p.set
    p.set=lambda n,v: (log.append((n,v)), orig(n,v))[1]
    try: s.call_tool(tool)
    except Exception: pass
    p.set=orig
    return log

def rejects(tool, desc, phi, normalise):
    for init in m2a.INITIAL_STATES:
        log=replay_with_log(tool,desc,init)
        for m in AR.finditer(phi or ""):
            n,v=m.group(1),m.group(2)
            hit = ((n,norm(v)) in [(a,norm(b)) for a,b in log]) if normalise else ((n,v) in log)
            if not hit: return True
    return False

lay=E.PGDSLAdmissionLayer()
para=json.load(open('/Users/huanbui/Desktop/PG-DSL/mission_3b/data/benign_corpus_extended.json'))
print(f"corpus: {len(para)} paraphrases")
phis={}
out={}
for mode in (False, True):
    fp=[]
    for r in para:
        key=(r['tool_name'],r['description'])
        if key not in phis:
            p2,s2=fresh(); s2.apply_description_overrides({r['tool_name']:r['description']})
            phis[key]=lay.gate_one_tool(r['tool_name'],s2).phi
        if rejects(r['tool_name'], r['description'], phis[key], mode):
            fp.append({"tool":r['tool_name'],"style":r.get('style'),"phi":phis[key]})
    label="normalised" if mode else "literal"
    tools=sorted({x['tool'] for x in fp})
    print(f"  {label:11} command-log benign rejections: {len(fp)}/227   tools={tools}")
    out[label]={"rejections":len(fp),"n":len(para),"tools":tools,"examples":fp[:6]}

# also re-confirm the 42-canonical figure with the same code path
p,s=fresh(); canon=[t['name'] for t in s.list_tools()]
for mode in (False,True):
    fp=[t for t in canon if rejects(t, s._tools[t].description,
        lay.gate_one_tool(t,fresh()[1]).phi, mode)]
    print(f"  {'normalised' if mode else 'literal':11} canonical 14 tools: {len(fp)}/14  {fp}")
    out[("normalised" if mode else "literal")]["canonical_14"]=len(fp)
save("n3b_cmdlog_227",{"supersedes":"n2b_gapclose.cmdlog_benign_fp_227 (VACUOUS: over-escaped regex matched nothing)",
  "regex_sanity_checked":True,"results":out})
