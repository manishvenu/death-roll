import os, sys, json, subprocess, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
print("HOME =", Path.home())
wd = D / "relwd3"; wd.mkdir(exist_ok=True); os.chdir(wd)
Path("cases_rel").mkdir(exist_ok=True); (Path.home() / "cases_rel").mkdir(exist_ok=True)
ip = D / "inputs_abs/audit_ccl_r2d"; ip.parent.mkdir(exist_ok=True)
cr = "cases_rel/audit_ccl_r2d"
try:
    c = make_case(cr, ip, name="ccr2d")
    print("CREATED; self.caseroot =", c.caseroot, "abs:", c.caseroot.resolve())
except Exception as e:
    print("FAILED:", type(e).__name__, str(e)[:400])
print("cwd-relative caseroot exists:", Path(cr).exists())
print("HOME caseroot exists:", (Path.home() / cr).exists(), sorted(p.name for p in (Path.home()/"cases_rel").iterdir()))
if (Path.home() / cr).exists(): print("HOME case files:", sorted(p.name for p in (Path.home()/cr).iterdir())[:8])
