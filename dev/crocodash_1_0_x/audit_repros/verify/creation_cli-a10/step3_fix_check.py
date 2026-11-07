# Fix check: same dump, but emit the alias the case was made with (what the proposed fix stores).
from pathlib import Path
from CrocoDash.recipe import case_to_yaml, create_case_from_yaml
V = Path(__file__).resolve().parent
cfg = case_to_yaml(V / "cases" / "audit_v10_marbl_orig")
cfg["case"]["compset"] = "CR1850MARBL_JRA"
cfg["case"]["caseroot"] = str(V / "cases" / "audit_v10_marblfix_copy")
cfg["case"]["inputdir"] = str(V / "inputs" / "audit_v10_marblfix_copy")
try:
    create_case_from_yaml(cfg, override=True, configure_only=True)
    print("STEP3 RESULT: recreated fully")
except Exception as e:
    print("STEP3 RESULT:", type(e).__name__, str(e)[:400])
