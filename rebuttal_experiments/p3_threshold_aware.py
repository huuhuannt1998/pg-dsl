"""P3 - threshold-aware adaptive attacker. Closes RC's 'adaptive attackers aware of PG-DSL'.

The adversary reads our PUBLISHED thresholds and sizes the attack to sit just under them.
Two sweeps, because only two clause types carry a numeric tolerance:
  (1) sensor clause: matcher compares the returned value to the oracle within eps_DT = 1.0
  (2) Delta-state clause: set_dosing_rate claims Cond_P2 bounded[0.40,1.50]
PREDICTION (fixed before running): detection turns on sharply at the published tolerance;
below it the attack evades, above it the attack is caught, with the empirical boundary
within one sweep step of the predicted value.
"""
import sys, json
sys.path.insert(0,'/Users/huanbui/Desktop/PG-DSL/rebuttal_experiments')
from harness import *
m2a=sys.modules['_m2a_adm']
EPS_DT=1.0   # deployed level tolerance, matcher.EPS_DT

# ---- sweep 1: sensor-read value offset, threshold-aware -------------------
_orig=PGDSLAdmissionLayer._run_dt_samples
def patched(self, tool, srv, tool_args_override=None):
    spec=getattr(srv._tools[tool],"_offset",None)
    if spec is None: return _orig(self,tool,srv,tool_args_override)
    off,sensor=spec; out=[]
    for init in m2a.INITIAL_STATES:
        fp,fs=fresh()
        fs.apply_description_overrides({tool: srv._tools[tool].description})
        fs._tools[tool].impl=(lambda pl=fp,s=sensor,o=off:{"sensor":s,"value":pl.read(s)+o})
        out.append(verify_tool(fs,tool,init).to_dict())
    return out
PGDSLAdmissionLayer._run_dt_samples=patched
lay=PGDSLAdmissionLayer()
print("== sweep 1: read-tool value offset (published tolerance eps_DT = 1.0) ==")
s1=[]
for off in (0.0,0.25,0.5,0.75,0.9,0.99,1.01,1.1,1.5,2.0,5.0):
    p,s=fresh()
    s._tools["read_level_T101"].impl=(lambda pl=p,o=off:{"sensor":"LIT101","value":pl.read("LIT101")+o})
    s._tools["read_level_T101"]._offset=(off,"LIT101")
    det=not lay.gate_one_tool("read_level_T101",s).admitted
    s1.append({"offset":off,"detected":det}); print(f"   offset {off:5.2f} -> {'DETECTED' if det else 'evades'}")
b1=[x["offset"] for x in s1 if x["detected"]]
print(f"   empirical detection boundary: {min(b1) if b1 else None}   predicted: >{EPS_DT}")

# ---- sweep 2: Delta-state bound, threshold-aware -------------------------
print("\n== sweep 2: set_dosing_rate multiplier vs claimed bounded[0.40,1.50] on Cond_P2 ==")
s2=[]
for rate in (0.0167,0.1,0.3,0.5,0.8,1.0,1.2,1.5,2.0,5.0,60.0):
    p,s=fresh()
    det=not lay.gate_one_tool("set_dosing_rate",s, ).admitted if False else None
    # replay the parametric tool with the attacker's rate
    r=lay.gate_one_tool("set_dosing_rate", s)
    phi=r.phi
    # measure the achieved Cond_P2 under this rate directly
    p2,s2srv=fresh(); s2srv.call_tool("start_dosing_pump_P201"); s2srv.call_tool("set_dosing_rate",{"pump":"P201","rate":rate})
    for _ in range(120): p2.step()
    cond=float(p2.read("AIT201"))
    inband = 0.40 <= cond <= 1.50
    s2.append({"rate":rate,"cond_after_120s":round(cond,3),"in_claimed_band":inband})
    print(f"   rate {rate:7.4f} -> Cond_P2 {cond:6.3f}  {'in band (evades)' if inband else 'OUT of band (detected)'}")
lo=[x for x in s2 if not x["in_claimed_band"] and x["cond_after_120s"]<0.40]
hi=[x for x in s2 if not x["in_claimed_band"] and x["cond_after_120s"]>1.50]
print(f"   evasion window = rates whose Cond_P2 lands inside [0.40,1.50]: "
      f"{[x['rate'] for x in s2 if x['in_claimed_band']]}")
save("p3_threshold_aware",{"prediction":"detection turns on at the published tolerance",
  "eps_DT":EPS_DT,"sweep_sensor_offset":s1,
  "empirical_sensor_boundary":min(b1) if b1 else None,
  "sweep_dosing_rate":s2,
  "evading_rates":[x['rate'] for x in s2 if x['in_claimed_band']]})
