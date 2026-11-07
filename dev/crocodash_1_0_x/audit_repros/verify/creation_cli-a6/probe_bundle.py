import sys, traceback
from pathlib import Path
V = Path(__file__).resolve().parent
from CrocoDash.shareable import CaseBundle
try:
    CaseBundle(V / "cases/audit_a6v_src")
    print("CaseBundle OK")
except Exception:
    traceback.print_exc()
print([p for p in sys.path if "MOM_RPS" in p or "cime" in p.lower()])
