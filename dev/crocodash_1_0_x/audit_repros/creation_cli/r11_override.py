import os, sys, json, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from ProConPy.config_var import cvars
cr, ip = D/"cases9/audit_ccl_r9y", D/"inputs9/audit_ccl_r9y"
print("before: caseroot exists", cr.exists(), "inputdir exists", ip.exists())
(ip/"user_file_keep.txt").write_text("x")
try:
    c = make_case(cr, ip, name="ccr9y", override=True)
    print("OVERRIDE OK; CUSTOM_GRID_PATH =", cvars["CUSTOM_GRID_PATH"].value, "| CASEROOT =", cvars["CASEROOT"].value)
    print("INPUTDIR line:", [l.strip() for l in open(cr/"user_nl_mom") if l.startswith("INPUTDIR")])
except Exception as e:
    print("OVERRIDE FAILED:", type(e).__name__, str(e)[:400]); traceback.print_exc(limit=-4)
# machine=None (documented default: auto-detect)
try:
    g, t, v = objs("ccr11")
    Case(cesmroot=CESMROOT, caseroot=D/"cases9/audit_ccl_r11m", inputdir=D/"inputs9/audit_ccl_r11m", compset=NYF,
         ocn_grid=g, ocn_topo=t, ocn_vgrid=v, atm_grid_name="T62", project="ncgd0011")
    print("machine=None OK")
except Exception as e:
    print("machine=None FAILED:", type(e).__name__, str(e)[:300])
