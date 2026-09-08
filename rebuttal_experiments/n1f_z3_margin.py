"""N1.5: measure ||delta_v||_inf for the Z3 composition witness in EVERY twin, instead of
carrying the nominal constant DELTA_Z3_VINF = 5.0 across all 18 rows.

delta_v is the per-coordinate max excursion outside the safe band, exactly as
mission_3a/t1_v_verify.py vector_matcher computes it:
  A_eff = [25,95] on LIT101 and [20,95] on LIT201, horizon 30 s, ordered pair from HIGH.
Then compare ||delta_v||_inf against delta*_v = 2(eps_L + eps_DT^emp) per twin."""
import sys, json
sys.path.insert(0,'.')
from harness import *
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/mission_1b')
from plant import PlantParams
from mcp_server import MCPServer
from n1_perturbed_twin import PerturbedPlant, TWINS
SEQ=["open_valve_MV101","start_pump_P101"]
BAND={"LIT101":(25.0,95.0),"LIT201":(20.0,95.0)}
HORIZON=30; EPS_L=0.116
HIGH={"LIT101":90.0,"LIT201":90.0}

def dist(v, lo, hi): return max(0.0, lo-v, v-hi)

def z3_delta_v(twin):
    _,f,l,c,d = twin
    p=PerturbedPlant(PlantParams(),flow=f,lat=l,chem=c,drift=d); s=MCPServer(p)
    for k,v in HIGH.items(): p.state[k]=v
    for tn in SEQ:
        try: s.call_tool(tn)
        except Exception: pass
    dv={k:0.0 for k in BAND}
    for _ in range(HORIZON):
        p.step()
        for k,(lo,hi) in BAND.items():
            dv[k]=max(dv[k], dist(float(p.read(k)), lo, hi))
    return dv, max(dv.values())

nom=json.load(open('results/n1_perturbed_twin.json'))['twins']
eps={t['twin']:t['eps_DT_emp'] for t in nom}
rows=[]
print(f"{'twin':12} {'||dv||_inf':>11} {'delta*_v':>10} {'margin':>8}  T1v holds?")
for tw in TWINS:
    dv, inf = z3_delta_v(tw)
    e=eps[tw[0]]; ds=2*(EPS_L+e)
    holds = (inf > ds)   # detection required when the excursion exceeds the threshold
    rows.append({"twin":tw[0],"delta_v":dv,"dv_inf":round(inf,3),
                 "eps_DT_emp":e,"delta_star_v":round(ds,3),
                 "exceeds_threshold":holds,"margin_ratio":round(inf/ds,2) if ds else None})
    print(f"{tw[0]:12} {inf:11.3f} {ds:10.3f} {inf/ds:7.2f}x  {'yes' if holds else 'NO'}")
nomdv=rows[0]['dv_inf']
print(f"\nnominal ||delta_v||_inf = {nomdv}   (paper's DELTA_Z3_VINF = 5.0)")
print(f"twin-invariant? {len({r['dv_inf'] for r in rows})==1}")
n_below=sum(1 for r in rows if not r['exceeds_threshold'])
print(f"twins where the Z3 excursion no longer exceeds delta*_v: {n_below}/{len(rows)}")
save("n1f_z3_margin",{"purpose":"N1.5 - measured ||delta_v||_inf per twin for the Z3 witness",
 "supersedes":"n1c_margins.json use of the fixed nominal constant 5.0 in all rows",
 "paper_nominal_constant":5.0,"measured_nominal":nomdv,
 "twins_below_threshold":n_below,"rows":rows})
