import sys, traceback
from common import *
# 1) inputdir parent missing
cr = D / "cases1/audit_ccl_r1a"; ip = D / "missing_parent_a/sub/audit_ccl_r1a"
cr.parent.mkdir(parents=True, exist_ok=True)
try:
    make_case(cr, ip)
    print("R1a: created OK")
except Exception as e:
    print("R1a FAILED:", type(e).__name__, e)
    traceback.print_exc(limit=-6)
print("caseroot exists?", cr.exists(), "inputdir exists?", ip.exists())
# 2) caseroot parent missing
cr = D / "missing_parent_b/sub/audit_ccl_r1b"; ip = D / "inputs1/audit_ccl_r1b"
ip.parent.mkdir(parents=True, exist_ok=True)
try:
    make_case(cr, ip)
    print("R1b: created OK")
except Exception as e:
    print("R1b FAILED:", type(e).__name__, e)
    traceback.print_exc(limit=-6)
print("caseroot exists?", cr.exists(), "inputdir exists?", ip.exists())
# 3) retry in same process after creating parents
(D / "missing_parent_b/sub").mkdir(parents=True, exist_ok=True)
try:
    c = make_case(cr, ip)
    print("R1c: retry in same process created OK", c.caseroot)
except Exception as e:
    print("R1c FAILED:", type(e).__name__, e)
    traceback.print_exc(limit=-6)
