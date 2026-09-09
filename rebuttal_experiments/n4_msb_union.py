"""N4: score the 8 hand-written MSB instances per class with the SAME scorer used for the
25-instance grid, so the union (33/class) is internally consistent. Pre-registered N4.1-N4.3."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, time
sys.path.insert(0,_ROOT+'/rebuttal_experiments')
sys.path.insert(0,_ROOT+'/mission_3b/data')
sys.path.insert(0,_ROOT+'/mission_2c/baselines')
from harness import fresh, save
from msb_subset import MSB_INSTANCES
from real_admission_layer import RealLLMAdmissionLayer
lay=RealLLMAdmissionLayer(prompt_variant="v1")
rows=[]; t0=time.time()
for n,i in enumerate(MSB_INSTANCES):
    p,s=fresh(); s.apply_description_overrides({i.target_tool: i.description})
    try:
        r=lay.gate_one_tool(i.target_tool, s); det=not r.admitted; phi=r.phi
        why=r.rejection_reasons[:2] if det else []
    except Exception as e:
        det=False; phi=f"ERR {e}"; why=[]
    rows.append({"id":i.id,"msb_class":i.msb_class,"target_tool":i.target_tool,
                 "description":i.description,"detected":det,"phi":phi,"why":why,"origin":"hand"})
    if n%8==0: print(f"  {n}/{len(MSB_INSTANCES)}", flush=True)
grid=json.load(open('results/p1_msb100.json'))['instances']
for r in grid: r["origin"]="grid"
allr=rows+grid
by={}
for r in allr:
    c=r["msb_class"]; by.setdefault(c,{"hand":[0,0],"grid":[0,0]})
    k="hand" if r["origin"]=="hand" else "grid"
    by[c][k][1]+=1; by[c][k][0]+=int(r["detected"])
print(f"\n== MSB union, 33 per class ({time.time()-t0:.0f}s) ==")
print(f"{'class':6} {'hand n=8':>10} {'grid n=25':>11} {'union n=33':>12}")
for c in ("NC","PM","PI","OP"):
    h,g=by[c]["hand"],by[c]["grid"]
    print(f"{c:6} {h[0]:5d}/{h[1]:<4d} {g[0]:5d}/{g[1]:<5d} {h[0]+g[0]:5d}/{h[1]+g[1]:<6d}")
hits=[r for r in rows if r["detected"] and r["msb_class"] in ("PM","OP")]
print("\n=== non-NC hand-written detections (what feature do they share?) ===")
for r in hits: print(f"  {r['id']} {r['target_tool']}: phi={r['phi'][:50]!r}\n     why={r['why']}\n     desc={r['description'][:110]}")
save("n4_msb_union",{"preregistered":"N4.1-N4.3","n4_1_disjoint":True,
  "by_class":{c:{"hand_detected":by[c]["hand"][0],"hand_n":by[c]["hand"][1],
                 "grid_detected":by[c]["grid"][0],"grid_n":by[c]["grid"][1],
                 "union_detected":by[c]["hand"][0]+by[c]["grid"][0],"union_n":by[c]["hand"][1]+by[c]["grid"][1]}
             for c in by},
  "non_nc_hits":[{k:r[k] for k in ("id","msb_class","target_tool","phi","why","description")} for r in hits],
  "rows":allr})
