"""Shared harness for the ACSAC rebuttal experiments. Reuses the shipped artifact."""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M1B, M2A, M2C, M3B = ROOT/"mission_1b", ROOT/"mission_2a", ROOT/"mission_2c", ROOT/"mission_3b"
for p in (M1B, M2A, M2C, M2C/"baselines", M3B, ROOT):
    sys.path.insert(0, str(p))

from plant import PlantParams, SwatP1P2Plant          # noqa
from mcp_server import MCPServer                       # noqa
import importlib.util as ilu
_s = ilu.spec_from_file_location("_m2a_adm", str(M2A/"admission_layer"/"pgdsl_admission_layer.py"))
_m = ilu.module_from_spec(_s); sys.modules["_m2a_adm"] = _m; _s.loader.exec_module(_m)
PGDSLAdmissionLayer = _m.PGDSLAdmissionLayer

_sv = ilu.spec_from_file_location("_m2a_dtv", str(M2A/"dt_verifier"/"dt_verifier.py"))
_mv = ilu.module_from_spec(_sv); sys.modules["_m2a_dtv"] = _mv; _sv.loader.exec_module(_mv)
verify_tool = _mv.verify_tool

SENSORS = ("LIT101","LIT201","FIT101","FIT201","AIT201","AIT202","AIT203")
READ_TOOLS = {"read_level_T101":"LIT101","read_level_T201":"LIT201",
              "read_flow_FIT101":"FIT101","read_flow_FIT201":"FIT201",
              "read_chemical_AIT201":"AIT201"}

def fresh():
    p = SwatP1P2Plant(PlantParams()); return p, MCPServer(p)

def save(name, obj):
    out = Path(__file__).resolve().parent/"results"/f"{name}.json"
    out.write_text(json.dumps(obj, indent=2, default=str)); print(f"  -> {out.name}")
    return out
