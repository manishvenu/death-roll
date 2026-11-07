# Relative caseroot where $HOME/<same relative parent> exists (HOME pointed at a scratch dir).
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
os.chdir(S)
print("Path.home() =", Path.home())
try:
    case = make("relcase2", caseroot=Path("cases/audit_vcg_relcase2"))
    show(case.caseroot)
except Exception as e:
    print("RAISED:", type(e).__name__, str(e)[:600])
print("cwd case exists:", (S/"cases/audit_vcg_relcase2").exists(), " HOME case exists:", (Path.home()/"cases/audit_vcg_relcase2").exists())
