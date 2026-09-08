"""E8b - cross-model lifter breadth on the PARAPHRASE corpus (the hard case).
E8a used the canonical descriptions and every family scored ~14/14, which only shows the
canonical surface is easy. The paper's own Table 7 reports llama3.1:8b at 4/42 on the
42-entry seed paraphrase corpus, so that is the discriminating test. Scoring rule fixed
before running: rejection = out-of-grammar OR lifted claim does not name the tool's component."""
import sys, os, json, time
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
CORPUS='/Users/huanbui/Desktop/PG-DSL/mission_3b/data/benign_corpus_extended.json'
rows=[r for r in json.load(open(CORPUS)) if r['source']=='seed_M2B']
print(f"paraphrase seed corpus: n={len(rows)}")
MODELS=["qwen3:14b","llama3.1:8b","gemma2:9b","mistral-nemo:12b","granite3.1-dense:8b","phi4-mini:latest"]
EXP={"open_valve_MV101":"MV101","close_valve_MV101":"MV101","start_pump_P101":"P101",
 "stop_pump_P101":"P101","open_valve_MV201":"MV201","close_valve_MV201":"MV201",
 "start_dosing_pump_P201":"P201","stop_dosing_pump_P201":"P201","set_dosing_rate":"P201",
 "read_level_T101":"LIT101","read_level_T201":"LIT201","read_flow_FIT101":"FIT101",
 "read_flow_FIT201":"FIT201","read_chemical_AIT201":"AIT201"}
out=[]
for m in MODELS:
    os.environ["PG_DSL_LIFTER_MODEL"]=m
    for k in [x for x in list(sys.modules) if 'lifter' in x or 'qwen_client' in x]: sys.modules.pop(k,None)
    sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/mission_2c/baselines')
    import importlib, qwen_client; importlib.reload(qwen_client)
    import real_lifter; importlib.reload(real_lifter)
    lifter=real_lifter.RealLifter(); t0=time.time(); oog=0; wrong=0; bad=[]
    for r in rows:
        ent=EXP[r['tool_name']]
        try:
            lc=lifter.lift(r['tool_name'], r['description'])
            phi=getattr(lc,'phi','') or ''; og=getattr(lc,'out_of_grammar',False)
        except Exception: phi=''; og=True
        if og or not phi: oog+=1; bad.append({**r,"phi":phi,"why":"out_of_grammar"})
        elif ent not in phi: wrong+=1; bad.append({**r,"phi":phi,"why":f"missing {ent}"})
    el=time.time()-t0; rej=oog+wrong
    out.append({"model":m,"n":len(rows),"out_of_grammar":oog,"wrong_entity":wrong,
                "rejected":rej,"rate":rej/len(rows),"seconds":round(el,1),"failures":bad[:6]})
    print(f"  {m:24s} rejected {rej:2d}/{len(rows)}  ({100*rej/len(rows):5.1f}%)  oog={oog} wrong={wrong}  ({el:.0f}s)", flush=True)
json.dump({"corpus":"42-entry seed paraphrase corpus (mission_3b/data/benign_corpus_extended.json, source=seed_M2B)",
  "scoring":"rejection = out-of-grammar OR lifted claim omits the tool's component",
  "note":"E8a on canonical descriptions gave 83/84 correct across the same 6 families; the canonical surface does not discriminate",
  "models":out}, open('/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments/results/e8b_crossmodel_paraphrase.json','w'), indent=2)
print("-> e8b_crossmodel_paraphrase.json")
