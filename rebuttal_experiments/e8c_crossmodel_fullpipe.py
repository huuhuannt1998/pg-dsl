"""E8c - cross-model breadth through the FULL admission pipeline (lift + DT replay + matcher).
Supersedes E8b, whose scorer only checked component identity and never ran the matcher, so it
scored llama3.1 at 0/42 where the paper's Table 7 reports 4/42. Spot-checking showed llama3.1
emits inferred Delta-state clauses (forbidden by rule R2) that only fail at the matcher.
SCORING (fixed pre-run): rejection = the canonical per-tool admission gate rejects the tool.
This is the same quantity as the paper's Table 7 FPR. All models reported, failures included."""
import sys, os, json, time
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
CORPUS='/Users/huanbui/Desktop/PG-DSL/mission_3b/data/benign_corpus_extended.json'
rows=[r for r in json.load(open(CORPUS)) if r['source']=='seed_M2B']
MODELS=["qwen3:14b","llama3.1:8b","gemma2:9b","mistral-nemo:12b","granite3.1-dense:8b","phi4-mini:latest"]
out=[]
for m in MODELS:
    os.environ["PG_DSL_LIFTER_MODEL"]=m
    for k in [x for x in list(sys.modules) if 'lifter' in x or 'qwen_client' in x
              or 'real_admission' in x or 'harness' in x or '_m2a' in x]: sys.modules.pop(k,None)
    sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/mission_2c/baselines')
    from harness import fresh
    import importlib, qwen_client; importlib.reload(qwen_client)
    import real_lifter; importlib.reload(real_lifter)
    import real_admission_layer; importlib.reload(real_admission_layer)
    lay=real_admission_layer.RealLLMAdmissionLayer(prompt_variant="v1")
    t0=time.time(); rej=[]; dstate=0
    for r in rows:
        p,s=fresh(); s.apply_description_overrides({r['tool_name']: r['description']})
        try:
            res=lay.gate_one_tool(r['tool_name'], s)
            phi=res.phi or ''
            if 'state(' in phi and r['tool_name']!='set_dosing_rate': dstate+=1
            if not res.admitted:
                rej.append({"tool":r['tool_name'],"style":r.get('style'),"phi":phi,
                            "reasons":res.rejection_reasons[:2]})
        except Exception as e:
            rej.append({"tool":r['tool_name'],"error":str(e)[:120]})
    el=time.time()-t0
    rec={"model":m,"n":len(rows),"rejected":len(rej),"fpr":len(rej)/len(rows),
         "inferred_dstate_lifts":dstate,"seconds":round(el,1),"rejections":rej[:8]}
    out.append(rec)
    print(f"  {m:24s} FPR {len(rej):2d}/{len(rows)} = {100*len(rej)/len(rows):5.1f}%   "
          f"inferred-Dstate lifts (R2 violations) {dstate:2d}/{len(rows)}   ({el:.0f}s)", flush=True)
    json.dump({"scoring":"rejection by canonical per-tool admission; same quantity as paper Table 7 FPR",
      "supersedes":"e8b (component-identity only, not comparable to Table 7)",
      "corpus":"42-entry seed paraphrase corpus","models":out},
      open('/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments/results/e8c_crossmodel_fullpipe.json','w'),indent=2)
print("-> e8c_crossmodel_fullpipe.json")
