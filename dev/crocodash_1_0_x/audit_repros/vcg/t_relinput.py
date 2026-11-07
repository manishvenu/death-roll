# Relative inputdir: what lands in user_nl_mom INPUTDIR and OCN_DOMAIN_MESH?
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
os.chdir(S)
case = make("relin", inputdir=Path("input/audit_vcg_relin"))
show(case.caseroot)
txt = (case.caseroot/"user_nl_mom").read_text()
print([l for l in txt.splitlines() if l.startswith("INPUTDIR")])
