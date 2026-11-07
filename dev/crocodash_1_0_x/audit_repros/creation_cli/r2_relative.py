import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
wd = D / "relwd"; wd.mkdir(exist_ok=True); os.chdir(wd)
Path("cases_rel").mkdir(exist_ok=True); Path("inputs_rel").mkdir(exist_ok=True)
case = make_case("cases_rel/audit_ccl_r2", "inputs_rel/audit_ccl_r2", name="ccr2")
st = json.load(open("cases_rel/audit_ccl_r2/_crocodash_state.json"))
print("STATE inputdir:", st["inputdir"], "| supergrid:", st["supergrid_path"])
print([l for l in open("cases_rel/audit_ccl_r2/user_nl_mom") if l.startswith("INPUTDIR")])
q = subprocess.run("./xmlquery OCN_DOMAIN_MESH,MASK_MESH,CASEROOT --non-local", shell=True, cwd="cases_rel/audit_ccl_r2", capture_output=True, text=True)
print("XML:", q.stdout, q.stderr[-500:])
configure(case)
cfg = json.load(open("inputs_rel/audit_ccl_r2/extract_forcings/config.json"))
print("CONFIG caseroot:", cfg["caseroot"])
