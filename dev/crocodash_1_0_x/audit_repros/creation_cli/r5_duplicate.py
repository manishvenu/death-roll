import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from visualCaseGen.custom_widget_types.case_tools import xmlchange
from CrocoDash.shareable import duplicate_case, CaseBundle
A = D/"cases4/audit_ccl_r4a"
# user customisations on the source case
txt = open(A/"user_nl_mom").read()
if "DT = 900.0" not in txt:
    txt = txt.replace("DT = 1800.0\n", "DT = 900.0\n", 1)
    open(A/"user_nl_mom", "w").write(txt)
xmlchange("DOUT_S", "FALSE", caseroot=A, is_non_local=True)
xmlchange("STOP_N", "1", caseroot=A, is_non_local=True)
print("A replay tail:", open(A/"replay.sh").read().strip().splitlines()[-3:])
B = D/"cases5/audit_ccl_r5b"; IB = D/"inputs5/audit_ccl_r5b"; B.parent.mkdir(exist_ok=True); IB.parent.mkdir(exist_ok=True)
nb = duplicate_case(A, B, IB)
print("B DT lines:", [l.strip() for l in open(B/"user_nl_mom") if l.startswith("DT")])
def xml(case, var):
    for fn in Path(case).glob("env_*.xml"):
        m = re.search(rf'<entry id="{var}"[^>]*>\s*<type>[^<]*</type>\s*(?:<valid_values>[^<]*</valid_values>\s*)?<desc>.*?</desc>|<entry id="{var}" value="([^"]*)"', open(fn).read(), re.S)
        if m and m.group(1) is not None: return m.group(1)
    return None
for v in ("DOUT_S", "STOP_N"):
    print("XML", v, "A=", xml(A, v), "B=", xml(B, v))
print("B replay tail:", open(B/"replay.sh").read().strip().splitlines()[-4:])
import glob; print("leaked temp run dirs:", glob.glob("/glade/derecho/scratch/manishrv/temp_case-*"))
