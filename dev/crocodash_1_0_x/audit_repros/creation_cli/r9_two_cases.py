import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
(D/"cases9").mkdir(exist_ok=True); (D/"inputs9").mkdir(exist_ok=True)
def ntasks(cr):
    t = open(cr/"env_mach_pes.xml").read()
    m = re.search(r'id="NTASKS".*?<value compclass="OCN">(\d+)</value>', t, re.S); return m.group(1)
def files(ip): return sorted(str(p.relative_to(ip)) for p in ip.rglob("*") if p.is_file())
X = make_case(D/"cases9/audit_ccl_r9x", D/"inputs9/audit_ccl_r9x", name="ccr9x", compset="GWR_JRA", atm="TL319")
print("X pecount ->", X._compute_pecount(), "NTASKS_OCN", ntasks(X.caseroot), "ocean pts", int(X.ocn_topo.tmask.sum()))
Case._compute_pecount = lambda self: None   # what the docstring says a small domain should get
Y = make_case(D/"cases9/audit_ccl_r9y", D/"inputs9/audit_ccl_r9y", name="ccr9y")
print("Y (pecount None) NTASKS_OCN", ntasks(Y.caseroot))
print("Y files:", files(Y.inputdir)); print("Y user_nl:", sorted(p.name for p in Y.caseroot.glob("user_nl_*")))
print("Y replay create:", [l for l in open(Y.caseroot/"replay.sh") if "create_newcase" in l][0][-140:])
print("X _cime_case caseroot:", X._cime_case.get_value("CASEROOT"))
