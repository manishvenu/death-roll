import os, sys, shutil, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from CrocoDash.shareable import CaseBundle
A = D/"cases4/audit_ccl_r4a"
mode = sys.argv[1]
nl = {"cpl": ("user_nl_cpl", "\norb_iyear = 1990\n"), "kpp": ("user_nl_mom", "\nKPP%\nN_SMOOTH = 2\n%KPP\n")}[mode]
orig = open(A/nl[0]).read()
open(A/nl[0], "a").write(nl[1])
try:
    cb = CaseBundle(A)
    print(mode, "source user_nl modules:", {k: list(v) for k, v in cb.user_nl_objs.items()})
    info = cb.identify_non_standard_case_info(CESMROOT, "derecho", "ncgd0011")
    print(mode, "DIFF OK:", info)
except Exception as e:
    print(mode, "BUNDLE DIFF FAILED:", type(e).__name__, repr(e)[:300])
    traceback.print_exc(limit=-3)
finally:
    open(A/nl[0], "w").write(orig)
