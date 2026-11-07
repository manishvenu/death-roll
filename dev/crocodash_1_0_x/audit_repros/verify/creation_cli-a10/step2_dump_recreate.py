# Process 2 (what `crocodash dump` + `crocodash create`, duplicate, bundle and fork do):
# case_to_yaml(orig) -> create_case_from_yaml(config) at a new caseroot/inputdir.
import sys, traceback
from pathlib import Path
from CrocoDash.recipe import case_to_yaml, create_case_from_yaml

V = Path(__file__).resolve().parent
tag = sys.argv[1]
cfg = case_to_yaml(V / "cases" / f"audit_v10_{tag}_orig")
print("STEP2 dumped case.compset =", cfg["case"]["compset"])
cfg["case"]["caseroot"] = str(V / "cases" / f"audit_v10_{tag}_copy")
cfg["case"]["inputdir"] = str(V / "inputs" / f"audit_v10_{tag}_copy")
try:
    create_case_from_yaml(cfg, override=True, configure_only=True)
    print("STEP2 RESULT: recreated fully")
except Exception as e:
    # No forcings were configured on the original, so a successful Case() is
    # followed by "Cannot recreate a case without a forcings configuration".
    print("STEP2 RESULT:", type(e).__name__, str(e)[:600])
