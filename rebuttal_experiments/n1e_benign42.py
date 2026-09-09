"""N1.1 at the granularity the plan specifies: 42 benign per-tool verdicts per twin
(14 tools x LOW/MID/HIGH), taken from the SHIPPED admission pipeline's
decision_per_initial_state - not from a re-implemented proxy verdict function.
Supersedes the 14-granularity figure in n1_perturbed_twin.json."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, time
sys.path.insert(0,'.')
from harness import *
sys.path.insert(0,_ROOT+'/mission_1b')
from plant import PlantParams
from mcp_server import MCPServer
from n1_perturbed_twin import PerturbedPlant, TWINS
import importlib.util as ilu
M2A=_ROOT+'/mission_2a'
_s=ilu.spec_from_file_location("_dtv2",f"{M2A}/dt_verifier/dt_verifier.py")
_m=ilu.module_from_spec(_s); sys.modules["_dtv2"]=_m; _s.loader.exec_module(_m)
verify_tool, INITIAL_STATES = _m.verify_tool, _m.INITIAL_STATES

TWIN=[None]
_orig=PGDSLAdmissionLayer._run_dt_samples
def _patched(self, tool_name, original_server, tool_args_override=None):
    _,f,l,c,d = TWIN[0]
    ot=original_server._tools[tool_name]; out=[]
    for init in INITIAL_STATES:
        fp=PerturbedPlant(PlantParams(),flow=f,lat=l,chem=c,drift=d)
        fs=MCPServer(fp); fs.apply_description_overrides({tool_name: ot.description})
        if hasattr(ot,"_aliased_to"):
            a=ot._aliased_to; fs._tools[tool_name].impl=(lambda: {"sensor":a,"value":fp.read(a)})
        out.append(verify_tool(fs,tool_name,init,tool_args_override=tool_args_override).to_dict())
    return out
PGDSLAdmissionLayer._run_dt_samples=_patched

lay=PGDSLAdmissionLayer()
rows=[]; nom=None
for tw in TWINS:
    TWIN[0]=tw
    p,s=fresh()
    cells={}
    for r in lay.gate_all_tools(s):
        for d in r.decision_per_initial_state:
            cells[(r.tool_name, d.get("initial_state_name"))] = bool(d.get("admitted"))
    if nom is None: nom=dict(cells)
    flips=[f"{k[0]}@{k[1]}" for k,v in cells.items() if v!=nom[k]]
    rejected=[f"{k[0]}@{k[1]}" for k,v in cells.items() if not v]
    rows.append({"twin":tw[0],"n_cells":len(cells),"rejected_cells":len(rejected),
                 "rejected":rejected,"flips_vs_nominal":len(flips),"flipped":flips})
    print(f"   {tw[0]:12} cells {len(cells):3d}  rejected {len(rejected):2d}/42  "
          f"flips vs nominal {len(flips):2d}", flush=True)
tot=sum(r['flips_vs_nominal'] for r in rows)
print(f"\n42-cell granularity, shipped pipeline: {len(rows)} twins x 42 = {len(rows)*42} benign verdicts")
print(f"nominal rejected cells: {rows[0]['rejected_cells']}/42  {rows[0]['rejected']}")
print(f"TOTAL perturbation-induced benign flips: {tot}")
save("n1e_benign42",{"granularity":"42 per-tool-per-state cells from the shipped pipeline",
 "supersedes":"n1_perturbed_twin.json benign_flips (14-tool granularity, proxy verdict fn)",
 "n_twins":len(rows),"total_benign_verdicts":len(rows)*42,
 "induced_flips":tot,"rows":rows})
