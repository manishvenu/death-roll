import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
wd = D / "relwd"; wd.mkdir(exist_ok=True); os.chdir(wd)
Path("inputs_rel").mkdir(exist_ok=True)
cr = D / "cases_abs/audit_ccl_r2a"; cr.parent.mkdir(exist_ok=True)
case = make_case(cr, "inputs_rel/audit_ccl_r2a", name="ccr2a")
st = json.load(open(cr / "_crocodash_state.json"))
print("STATE inputdir:", st["inputdir"], "| supergrid:", st["supergrid_path"])
print("USERNL", [l.strip() for l in open(cr / "user_nl_mom") if l.startswith("INPUTDIR")])
q = subprocess.run("./xmlquery OCN_DOMAIN_MESH,MASK_MESH --non-local", shell=True, cwd=cr, capture_output=True, text=True)
print("XML:", q.stdout, q.stderr[-500:])
configure(case)
cfg = json.load(open("inputs_rel/audit_ccl_r2a/extract_forcings/config.json"))
print("CONFIG caseroot:", cfg["caseroot"])
os.chdir(D)  # user moves to another dir (e.g. new notebook cell cd's) 
try:
    case.process_forcings()
    print("PROCESS OK")
except Exception as e:
    print("PROCESS FAILED after chdir:", type(e).__name__, str(e)[:300])
