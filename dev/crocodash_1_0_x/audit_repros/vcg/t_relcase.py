# Relative caseroot: CrocoDash keeps it cwd-relative, vCG's create_case re-roots it under $HOME.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
os.chdir(S)
print("HOME/cases exists?", (Path.home()/"cases").exists())
try:
    case = make("relcase", caseroot=Path("cases/audit_vcg_relcase"))
    show(case.caseroot)
except Exception as e:
    import traceback; traceback.print_exc()
print("cwd case exists:", (S/"cases/audit_vcg_relcase").exists(), " home case exists:", (Path.home()/"cases/audit_vcg_relcase").exists())
