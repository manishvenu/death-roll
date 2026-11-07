# Simulate a failing ./case.setup (it prints its reason on stderr and exits 1) and see what Case() reports.
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
import visualCaseGen.custom_widget_types.case_tools as ct
_real_run = subprocess.run
class _Sub:  # stand-in for the subprocess module inside case_tools only
    def __getattr__(self, k): return getattr(subprocess, k)
    def run(self, cmd, *a, **kw):
        if isinstance(cmd, str) and cmd.startswith("./case.setup"):
            cmd = "echo 'ERROR: (simulated) the real reason case.setup failed' >&2; exit 1"
        return _real_run(cmd, *a, **kw)
ct.subprocess = _Sub()
try:
    make("setupfail")
except BaseException as e:
    print("RAISED:", type(e).__name__, repr(str(e)))
    print("cause:", repr(e.__cause__))
print("caseroot still there for inspection?", (S/"cases/audit_vcg_setupfail").exists())
