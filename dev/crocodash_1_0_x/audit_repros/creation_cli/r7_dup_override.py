import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import CrocoDash.case as cmod
from CrocoDash.shareable import duplicate_case
calls = []
class Stop(Exception): pass
def dry_remove(path):
    calls.append(path)
    print("WOULD rmtree (override=True):", path, "exists:", path.exists())
    if "temp_case-" not in str(path) and "temp_inputdir" not in str(path):
        if len([c for c in calls if "temp_" not in str(c)]) >= 3:
            raise Stop()
cmod._remove_previous = dry_remove
A = D/"cases4/audit_ccl_r4a"
# duplicate to a different folder but the same case name, with the new inputdir = the folder holding A's inputdir
newB = D/"cases7/audit_ccl_r4a"; newB.parent.mkdir(exist_ok=True)
try:
    duplicate_case(A, newB, D/"inputs4")
except Stop:
    print("stopped before deleting")
