"""E8 - cross-model lifter breadth. Answers RC 'broader agent/model/tool configurations'
and RA 'a specific lifter prompt/model setup'. Scoring rule fixed before running:
FPR = fraction of the 14 honest canonical descriptions rejected; entity-correctness =
fraction whose lifted claim names the component the tool actually controls."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, os, json, time
sys.path.insert(0,_ROOT+'/rebuttal_experiments')
MODELS = ["qwen3:14b","llama3.1:8b","gemma2:9b","mistral-nemo:12b","granite3.1-dense:8b","phi4-mini:latest"]
EXP={"open_valve_MV101":"MV101","close_valve_MV101":"MV101","start_pump_P101":"P101",
 "stop_pump_P101":"P101","open_valve_MV201":"MV201","close_valve_MV201":"MV201",
 "start_dosing_pump_P201":"P201","stop_dosing_pump_P201":"P201","set_dosing_rate":"P201",
 "read_level_T101":"LIT101","read_level_T201":"LIT201","read_flow_FIT101":"FIT101",
 "read_flow_FIT201":"FIT201","read_chemical_AIT201":"AIT201"}
out=[]
for m in MODELS:
    os.environ["PG_DSL_LIFTER_MODEL"]=m
    for mod in [k for k in list(sys.modules) if 'lifter' in k or 'qwen_client' in k or 'harness' in k
                or 'real_admission' in k or '_m2a' in k]:
        sys.modules.pop(mod,None)
    try:
        from harness import fresh
        sys.path.insert(0,_ROOT+'/mission_2c/baselines')
        import importlib, qwen_client; importlib.reload(qwen_client)
        import real_lifter; importlib.reload(real_lifter)
        lifter = real_lifter.RealLifter()
        actual = qwen_client.ROLE_CONFIG['lifter']['model']
    except Exception as e:
        out.append({"model":m,"error":str(e)[:200]}); print(f"{m}: SETUP FAIL {e}"); continue
    t0=time.time(); rows=[]; oog=0; wrong=0
    p,s = fresh()
    for tool,ent in EXP.items():
        desc = s._tools[tool].description
        try:
            lc = lifter.lift(tool, desc)
            phi = getattr(lc,'phi','') or ''
            bad = getattr(lc,'out_of_grammar', False)
        except Exception as e:
            phi=''; bad=True
        if bad or not phi: oog+=1
        elif ent not in phi: wrong+=1
        rows.append({"tool":tool,"phi":phi,"oog":bool(bad),"entity_ok":(ent in phi) and not bad})
    el=time.time()-t0
    rec={"model":m,"resolved_model":actual,"n":14,"out_of_grammar":oog,"wrong_entity":wrong,
         "entity_correct":14-oog-wrong,"seconds":round(el,1),"rows":rows}
    out.append(rec)
    print(f"{m:26s} resolved={actual:22s} in-grammar={14-oog}/14  entity-correct={14-oog-wrong}/14  ({el:.0f}s)", flush=True)
json.dump({"preregistered":"scoring rule fixed pre-run; all models reported including failures",
           "models":out}, open(_ROOT+'/rebuttal_experiments/results/e8_crossmodel.json','w'), indent=2)
print("-> e8_crossmodel.json")
