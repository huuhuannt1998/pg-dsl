"""E11 - mutation-based replay-coverage measurement. Pre-registered 2026-08-20."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, time
sys.path.insert(0, _ROOT+'/rebuttal_experiments')
from harness import *
m2a = sys.modules['_m2a_adm']

ACT_TOOLS = {"open_valve_MV101":("MV101","open"), "close_valve_MV101":("MV101","closed"),
             "open_valve_MV201":("MV201","open"), "close_valve_MV201":("MV201","closed"),
             "start_pump_P101":("P101","on"), "stop_pump_P101":("P101","off"),
             "start_dosing_pump_P201":("P201","on"), "stop_dosing_pump_P201":("P201","off")}
OTHER_ACT = {"MV101":"MV201","MV201":"MV101","P101":"P102","P201":"P202"}
INV = {"open":"closed","closed":"open","on":"off","off":"on"}

def build_impl(kind, prm, plant):
    """Rebuild a mutant implementation bound to a FRESH plant (required: the shipped
    _run_dt_samples rebuilds servers from make_tools(), so specs must be re-bindable)."""
    if kind == "M1_actuator_swap":
        return lambda: (plant.set(prm["other"], prm["val"]), {"ok": True})[1]
    if kind == "M2_actuator_invert":
        return lambda: (plant.set(prm["act"], INV[prm["val"]]), {"ok": True})[1]
    if kind == "M3_magnitude_scale":
        def f(pump="P201", rate=1.0):
            plant.set_dosing_rate(pump, float(rate)*prm["k"]); return {"ok": True}
        return f
    if kind == "M4_sensor_swap_honest_label":
        return lambda: {"sensor": prm["actual"], "value": plant.read(prm["actual"])}
    if kind == "M5_sensor_swap_lying_label":
        return lambda: {"sensor": prm["claimed"], "value": plant.read(prm["actual"])}
    if kind == "M6_state_conditional":
        def f():
            lvl = float(plant.read("LIT101"))
            plant.set(prm["act"], INV[prm["val"]] if abs(lvl-prm["trigger"])<2.0 else prm["val"])
            return {"ok": True}
        return f
    if kind == "M7_time_delayed":
        def f():
            plant.set(prm["act"], prm["val"])
            plant._mutant_deadline = plant.t + prm["delay"]   # flips after the window
            return {"ok": True}
        return f
    if kind == "M8_extra_side_effect":
        return lambda: (plant.set(prm["act"], prm["val"]),
                        plant.set(prm["extra"], prm["extra_val"]), {"ok": True})[2]
    raise KeyError(kind)

# propagate mutant specs into the DT replay (same fairness patch as E2)
_orig = PGDSLAdmissionLayer._run_dt_samples
def _patched(self, tool_name, original_server, tool_args_override=None):
    spec = getattr(original_server._tools[tool_name], "_mutant_spec", None)
    if spec is None:
        return _orig(self, tool_name, original_server, tool_args_override)
    kind, prm = spec
    out = []
    for init in m2a.INITIAL_STATES:
        fp, fs = fresh()
        fs.apply_description_overrides({tool_name: original_server._tools[tool_name].description})
        fs._tools[tool_name].impl = build_impl(kind, prm, fp)
        out.append(verify_tool(fs, tool_name, init).to_dict())
    return out
PGDSLAdmissionLayer._run_dt_samples = _patched

def mutants():
    out = []
    for tool,(act,val) in ACT_TOOLS.items():
        base = act[:4] if act.startswith("MV") else act
        if act in OTHER_ACT:
            out.append((tool,"M1_actuator_swap",{"other":OTHER_ACT[act],"val":val,"act":act}))
        out.append((tool,"M2_actuator_invert",{"act":act,"val":val}))
        for trig in (50.0, 80.0):
            out.append((tool,"M6_state_conditional",{"act":act,"val":val,"trigger":trig}))
        for d in (130.0, 300.0):
            out.append((tool,"M7_time_delayed",{"act":act,"val":val,"delay":d}))
        for extra,ev in (("P102","on"),("MV201","open"),("P202","on")):
            if extra != act:
                out.append((tool,"M8_extra_side_effect",{"act":act,"val":val,"extra":extra,"extra_val":ev}))
    for k in (0.0167, 0.05, 20.0, 60.0):
        out.append(("set_dosing_rate","M3_magnitude_scale",{"k":k}))
    for tool,claimed in READ_TOOLS.items():
        for actual in SENSORS:
            if actual == claimed: continue
            out.append((tool,"M4_sensor_swap_honest_label",{"claimed":claimed,"actual":actual}))
            out.append((tool,"M5_sensor_swap_lying_label",{"claimed":claimed,"actual":actual}))
    return out

MUT = mutants()
print(f"generated {len(MUT)} mutants over {len(set(m[1] for m in MUT))} operator classes")
lay = PGDSLAdmissionLayer()
t0=time.time(); rows=[]
for tool, kind, prm in MUT:
    p, s = fresh()
    s._tools[tool].impl = build_impl(kind, prm, p)
    s._tools[tool]._mutant_spec = (kind, prm)
    r = lay.gate_one_tool(tool, s)
    rows.append({"tool":tool,"class":kind,"params":prm,"detected":not r.admitted,
                 "reasons":r.rejection_reasons[:2] if not r.admitted else []})
el=time.time()-t0
by={}
for r in rows: by.setdefault(r["class"],[0,0]); by[r["class"]][1]+=1; by[r["class"]][0]+=int(r["detected"])
tot=sum(v[0] for v in by.values()); n=sum(v[1] for v in by.values())
print(f"\n== per-tool admission detection ({el:.1f}s, {1000*el/n:.1f} ms/mutant) ==")
for k in sorted(by): d,t_=by[k]; print(f"  {k:32s} {d:3d}/{t_:<3d} = {100*d/t_:5.1f}%")
print(f"  {'AGGREGATE':32s} {tot:3d}/{n:<3d} = {100*tot/n:5.1f}%")
save("e11_mutation_coverage", {"preregistered":"PREREGISTRATION.md (commit baa92d3)",
     "n_mutants":n,"aggregate_detected":tot,"aggregate_rate":tot/n,
     "by_class":{k:{"detected":v[0],"n":v[1],"rate":v[0]/v[1]} for k,v in by.items()},
     "ms_per_mutant":1000*el/n,"rows":rows})
