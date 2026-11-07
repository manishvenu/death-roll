import os, sys, json, subprocess, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
print("HOME =", Path.home())
wd = D / "relwd2"; wd.mkdir(exist_ok=True); os.chdir(wd)
ip = D / "inputs_abs/audit_ccl_r2b"; ip.parent.mkdir(exist_ok=True)
for label, cr in [("bare", "audit_ccl_r2b"), ("dot", "./audit_ccl_r2b"), ("tilde", "~/audit_ccl_r2t")]:
    try:
        c = make_case(cr, ip if label != "tilde" else D / "inputs_abs/audit_ccl_r2t", name="ccr2b")
        print(label, "CREATED; self.caseroot =", c.caseroot)
    except Exception as e:
        print(label, "FAILED:", type(e).__name__, str(e)[:400])
    print(label, "cwd-relative exists:", Path(cr).exists(), "| under HOME exists:", (Path.home() / Path(cr).name).exists(),
          "| HOME listing:", sorted(p.name for p in Path.home().iterdir()))
