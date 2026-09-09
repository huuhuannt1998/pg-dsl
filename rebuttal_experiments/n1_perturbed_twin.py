"""N1: perturbed-twin verdict stability. Closes RB-B3 and RC's DT-fidelity assumption.
Pre-registered N1.1-N1.6. The frozen plant is subclassed, never edited; the nominal config
must reproduce frozen behaviour exactly before any perturbed result is reported."""
import pathlib as _pl
_ROOT = str(_pl.Path(__file__).resolve().parent.parent)   # repo root; no absolute paths
import sys, json, time, copy
sys.path.insert(0,'.')
from harness import *
sys.path.insert(0,_ROOT+'/mission_1b')
from plant import SwatP1P2Plant, PlantParams

class PerturbedPlant(SwatP1P2Plant):
    """flow gain, first-order actuator latency, chemistry gain, unmodelled drift."""
    def __init__(self, params=None, flow=1.0, lat=0.0, chem=1.0, drift=0.0):
        super().__init__(params)
        self.k_flow, self.lat, self.k_chem, self.drift = flow, lat, chem, drift
        self._pending=[]           # (t_apply, name, value)
        self._eff=dict({a:self.state[a] for a in self.ACTUATORS})
    def set(self, name, value):
        super().set(name,value)                     # commanded state (what the log sees)
        if self.lat<=0: self._eff[name]=value
        else: self._pending.append((self.t+self.lat,name,value))
    def step(self, dt=None):
        dt=dt or self.params.dt
        for tA,n,v in [x for x in self._pending if x[0]<=self.t]:
            self._eff[n]=v; self._pending.remove((tA,n,v))
        cmd={a:self.state[a] for a in self.ACTUATORS}
        for a in self.ACTUATORS: self.state[a]=self._eff[a]      # physics sees effective state
        l0=float(self.state["LIT101"]); c0=float(self.state["AIT201"])
        super().step(dt)
        l1=float(self.state["LIT101"]); c1=float(self.state["AIT201"])
        self.state["LIT101"]=max(0.0,min(100.0, l0 + (l1-l0)*self.k_flow - self.drift*dt))
        self.state["AIT201"]=max(0.0,min(5.0,  c0 + (c1-c0)*self.k_chem))
        for a in self.ACTUATORS: self.state[a]=cmd[a]            # restore commanded view

TWINS=[("nominal",1.0,0.0,1.0,0.0)]
for g in (0.8,0.9,1.1,1.2): TWINS.append((f"flow{g}",g,0.0,1.0,0.0))
for L in (1,2,5,10):        TWINS.append((f"lat{L}s",1.0,float(L),1.0,0.0))
for g in (0.8,0.9,1.1,1.2): TWINS.append((f"chem{g}",1.0,0.0,g,0.0))
for d in (0.005,0.01,0.02): TWINS.append((f"drift{d}",1.0,0.0,1.0,d))
TWINS += [("corner_slow",0.8,10.0,0.8,0.0), ("corner_fast",1.2,10.0,1.2,0.0)]
INIT=[("LOW",30.0,30.0),("MID",70.0,60.0),("HIGH",90.0,90.0)]
TOOLS=None

def traj(tool, init, twin, args=None):
    _,f,l,c,d = twin
    p=PerturbedPlant(PlantParams(),flow=f,lat=l,chem=c,drift=d)
    from mcp_server import MCPServer
    s=MCPServer(p)
    nm,l1,l2=init; p.state["LIT101"]=l1; p.state["LIT201"]=l2
    pre={k:p.read(k) for k in p.SENSORS}
    ret=None
    try: ret=s.call_tool(tool,args)
    except Exception: pass
    series=[]
    for _ in range(120):
        p.step(); series.append(float(p.read("LIT101")))
    return {"actuator_post":{a:p.read(a) for a in p.ACTUATORS},"sensor_pre":pre,
            "ret":ret,"series":series,"final":{k:p.read(k) for k in p.SENSORS}}

# --- regression gate: nominal must match the frozen plant exactly -------------
from mcp_server import MCPServer
ok=True
for tool in ["open_valve_MV101","start_pump_P101","set_dosing_rate"]:
    for init in INIT:
        a=traj(tool,init,TWINS[0])["series"]
        p=SwatP1P2Plant(PlantParams()); s=MCPServer(p)
        nm,l1,l2=init; p.state["LIT101"]=l1; p.state["LIT201"]=l2
        try: s.call_tool(tool)
        except Exception: pass
        b=[ (p.step(), float(p.read("LIT101")))[1] for _ in range(120) ]
        if a!=b: ok=False; print(f"  GATE FAIL {tool} {nm}")
print(f"REGRESSION GATE: nominal reproduces frozen plant exactly: {ok}")
if not ok:
    print("ABORT: nothing from N1 is reportable until the gate passes."); sys.exit(1)
json.dump({"gate_passed":True},open('results/n1_gate.json','w'))
print("gate passed -> proceeding")

# --- benign verdict stability + induced eps_DT --------------------------------
import re, sys as _s
_s.path.insert(0,'.')
import e11_mutation as E
lay=E.PGDSLAdmissionLayer()
AR=re.compile(r"actuator\((\w+)\)\s*:=\s*(\w+)"); SR=re.compile(r"sensor\((\w+)\)")
DR=re.compile(r"state\(\s*(\w+)\s*\)\s*\{([^}]*)\}")
p0,s0=fresh(); TOOLS=[t['name'] for t in s0.list_tools()]
PHI={t: lay.gate_one_tool(t, fresh()[1]).phi for t in TOOLS}

def verdict(tool, twin, args=None):
    phi=PHI[tool] or ""
    for init in INIT:
        r=traj(tool,init,twin,args)
        for m in AR.finditer(phi):
            if r["actuator_post"].get(m.group(1))!=m.group(2): return False
        for m in SR.finditer(phi):
            tr=(r["ret"] or {}); body=tr.get("result",tr) if isinstance(tr,dict) else {}
            nm=body.get("sensor") if isinstance(body,dict) else None
            if nm is not None and nm!=m.group(1): return False
        for m in DR.finditer(phi):
            if "Cond" in m.group(1):
                c=float(r["final"]["AIT201"]); lo,hi=0.40,1.50
                mm=re.search(r"bounded\[([\d.]+),\s*([\d.]+)\]",m.group(2))
                if mm: lo,hi=float(mm.group(1)),float(mm.group(2))
                if not (lo-0.05<=c<=hi+0.05): return False
    return True

print("\n== N1.1 benign verdict stability (14 tools x 3 states per twin) ==")
nom_series={}
for t in TOOLS:
    for init in INIT: nom_series[(t,init[0])]=traj(t,init,TWINS[0])["series"]
res=[]
for tw in TWINS:
    flips=[t for t in TOOLS if not verdict(t,tw)]
    dev=0.0
    for t in TOOLS:
        for init in INIT:
            a=traj(t,init,tw)["series"]; b=nom_series[(t,init[0])]
            dev=max(dev, max(abs(x-y) for x,y in zip(a,b)))
    res.append({"twin":tw[0],"benign_flips":len(flips),"flipped":flips,"eps_DT_emp":round(dev,3)})
    print(f"   {tw[0]:12} benign flips {len(flips):2d}/14   induced eps_DT = {dev:6.2f} %-full")
save("n1_perturbed_twin",{"preregistered":"N1.1-N1.6","gate_passed":True,"twins":res})
