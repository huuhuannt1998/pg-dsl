"""E8d - N6 support: compute delta_cov per lifter family as the plan defines it,
i.e. the WRONG-LIFT RATE = |{rejected} UNION {R2-violating}| over the 42-seed corpus.
E8c stored only rej[:8], so the union was not recoverable; this run records a per-row flag
pair for every one of the 42 descriptions and every family. Scoring fixed before the run:
  rejected   = canonical per-tool admission gate rejects the tool
  r2_violation = lifted phi contains a Delta-state clause on a tool other than set_dosing_rate
  wrong_lift = rejected OR r2_violation      <- this is delta_cov(C, L_verify)"""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, os, json, time
sys.path.insert(0,_ROOT+'/rebuttal_experiments')
CORPUS=_ROOT+'/mission_3b/data/benign_corpus_extended.json'
rows=[r for r in json.load(open(CORPUS)) if r['source']=='seed_M2B']
MODELS=["qwen3:14b","llama3.1:8b","gemma2:9b","mistral-nemo:12b","granite3.1-dense:8b","phi4-mini:latest"]
out=[]
for m in MODELS:
    os.environ["PG_DSL_LIFTER_MODEL"]=m
    for k in [x for x in list(sys.modules) if 'lifter' in x or 'qwen_client' in x
              or 'real_admission' in x or 'harness' in x or '_m2a' in x]: sys.modules.pop(k,None)
    sys.path.insert(0,_ROOT+'/mission_2c/baselines')
    from harness import fresh
    import importlib, qwen_client; importlib.reload(qwen_client)
    import real_lifter; importlib.reload(real_lifter)
    import real_admission_layer; importlib.reload(real_admission_layer)
    lay=real_admission_layer.RealLLMAdmissionLayer(prompt_variant="v1")
    t0=time.time(); per=[]
    for r in rows:
        p,s=fresh(); s.apply_description_overrides({r['tool_name']: r['description']})
        rej=False; r2=False; phi=''
        try:
            res=lay.gate_one_tool(r['tool_name'], s)
            phi=res.phi or ''
            r2 = ('state(' in phi and r['tool_name']!='set_dosing_rate')
            rej = not res.admitted
        except Exception as e:
            rej=True; phi=f"ERROR {str(e)[:80]}"
        per.append({"tool":r['tool_name'],"style":r.get('style'),"phi":phi,
                    "rejected":rej,"r2_violation":r2,"wrong_lift":bool(rej or r2)})
    el=time.time()-t0
    nrej=sum(1 for x in per if x['rejected']); nr2=sum(1 for x in per if x['r2_violation'])
    nun=sum(1 for x in per if x['wrong_lift'])
    rec={"model":m,"n":len(rows),"rejected":nrej,"r2_violations":nr2,
         "delta_cov_union":nun,"seconds":round(el,1),"per_row":per}
    out.append(rec)
    print(f"  {m:24s} rejected {nrej:2d}/42   R2 {nr2:2d}/42   "
          f"delta_cov(union) {nun:2d}/42   ({el:.0f}s)", flush=True)
    json.dump({"purpose":"N6 delta_cov per family = |rejected UNION r2_violating| on the 42-seed corpus",
      "scoring_fixed_before_run":True,"supersedes_for_delta_cov":"e8c (stored only rej[:8])",
      "models":out},
      open(_ROOT+'/rebuttal_experiments/results/e8d_deltacov.json','w'),indent=2)
print("-> e8d_deltacov.json")
