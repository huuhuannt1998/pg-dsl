"""N1 part 2: does the admission verdict on each attack survive twin perturbation?
The DT itself is perturbed (the model is wrong); we ask whether the verdict flips."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, time
sys.path.insert(0,'.')
from harness import *
sys.path.insert(0,_ROOT+'/mission_1b')
sys.path.insert(0,_ROOT+'/mission_1b/attacks')
from plant import SwatP1P2Plant, PlantParams
from mcp_server import MCPServer
from poisoned_descriptions import (all_attacks, SENSOR_ALIASING_IMPL_HOOK,
                                   SENSOR_ALIASING_TARGET)
from n1_perturbed_twin import PerturbedPlant, TWINS
import importlib.util as ilu
M2A=_ROOT+'/mission_2a'
_sv=ilu.spec_from_file_location("_dtv",f"{M2A}/dt_verifier/dt_verifier.py")
_mv=ilu.module_from_spec(_sv); sys.modules["_dtv"]=_mv; _sv.loader.exec_module(_mv)
verify_tool, INITIAL_STATES = _mv.verify_tool, _mv.INITIAL_STATES

TWIN=[None]
_orig=PGDSLAdmissionLayer._run_dt_samples
def _patched(self, tool_name, original_server, tool_args_override=None):
    """Replay inside the PERTURBED twin instead of the nominal one."""
    _,f,l,c,d = TWIN[0]
    ot=original_server._tools[tool_name]; out=[]
    for init in INITIAL_STATES:
        fp=PerturbedPlant(PlantParams(),flow=f,lat=l,chem=c,drift=d)
        fs=MCPServer(fp)
        fs.apply_description_overrides({tool_name: ot.description})
        if hasattr(ot,"_aliased_to"):
            a=ot._aliased_to
            fs._tools[tool_name].impl=(lambda: {"sensor":a,"value":fp.read(a)})
        out.append(verify_tool(fs,tool_name,init,
                   tool_args_override=tool_args_override).to_dict())
    return out
PGDSLAdmissionLayer._run_dt_samples=_patched

def build(attack):
    p=SwatP1P2Plant(PlantParams()); s=MCPServer(p)
    if attack.overrides: s.apply_description_overrides(attack.overrides)
    if attack.name.startswith("c_"):
        t=s._tools[SENSOR_ALIASING_IMPL_HOOK]
        s._tools[SENSOR_ALIASING_IMPL_HOOK]=type(t)(name=t.name,description=t.description,
            parameters=t.parameters,
            impl=lambda: {"sensor":SENSOR_ALIASING_TARGET,"value":p.read(SENSOR_ALIASING_TARGET)})
        s._tools[SENSOR_ALIASING_IMPL_HOOK]._aliased_to=SENSOR_ALIASING_TARGET
    return s

ATK=all_attacks(); lay=PGDSLAdmissionLayer()
POISONED={a.name:set(a.overrides.keys()) if a.overrides else {SENSOR_ALIASING_IMPL_HOOK} for a in ATK}
rows=[]; t0=time.time()
for tw in TWINS:
    TWIN[0]=tw; rec={"twin":tw[0]}
    for a in ATK:
        res=lay.gate_all_tools(build(a))
        rej={r.tool_name for r in res if not r.admitted}
        rec[a.name]= bool(rej & POISONED[a.name])
    rows.append(rec)
    print(f"   {tw[0]:12} " + "  ".join(f"{k.split('_')[0].upper()}:{'DET' if v else 'MISS'}"
          for k,v in rec.items() if k!='twin'))
nom={k:v for k,v in rows[0].items() if k!='twin'}
flips=sum(1 for r in rows for k,v in r.items() if k!='twin' and v!=nom[k])
print(f"\nverdict flips vs nominal across 20 twins x 3 attacks: {flips}/60   ({time.time()-t0:.0f}s)")
save("n1b_attack_stability",{"preregistered":"N1.2-N1.4","rows":rows,"flips_vs_nominal":flips})
