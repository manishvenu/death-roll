"""vcg-a6: a real ./case.setup failure inside Case() loses its reason, and the
caseroot (CaseStatus, logs) is deleted afterwards.

The only interference: right before the REAL ./case.setup runs, its caseroot's
LockedFiles/ dir is made read-only (a permissions problem), so CIME itself fails.
The wrapper records what case.setup printed, to compare with what the user sees.
"""
import os, sys, stat, subprocess
from pathlib import Path

S = Path(sys.argv[1])
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

_real_run = subprocess.run
seen = {}

def wrapped_run(cmd, *a, **kw):
    if isinstance(cmd, str) and cmd.startswith("./case.setup"):
        cr = Path(kw["cwd"])
        lf = cr / "LockedFiles"
        lf.mkdir(exist_ok=True)
        os.chmod(lf, 0o555)
        out = _real_run(cmd, *a, **kw)
        seen["cmd"] = cmd
        seen["rc"] = out.returncode
        seen["stdout"] = out.stdout
        seen["stderr"] = out.stderr
        seen["casestatus_exists"] = (cr / "CaseStatus").exists()
        seen["casestatus"] = (cr / "CaseStatus").read_text() if (cr / "CaseStatus").exists() else None
        os.chmod(lf, 0o755)  # so cleanup can remove it
        return out
    return _real_run(cmd, *a, **kw)

subprocess.run = wrapped_run  # case_tools / case_creator call subprocess.run via the module

grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a6")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="a6")
caseroot = S / "cases/audit_vcga6_1"
try:
    Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
         caseroot=caseroot, inputdir=S / "input/audit_vcga6_1",
         compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
         ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
         machine="derecho", project="ncgd0011", override=True)
    print("UNEXPECTED: Case() succeeded")
except Exception as e:
    print("=== what the user gets ===")
    print(f"{type(e).__name__}: {e!r}")
    print("__cause__:", repr(e.__cause__))
    print("__context__:", repr(e.__context__)[:300])
print("=== what case.setup actually reported (captured by subprocess, then dropped) ===")
print("cmd:", seen.get("cmd"), "rc:", seen.get("rc"))
so = seen.get("stdout") or b""
se = seen.get("stderr") or b""
so = so.decode() if isinstance(so, bytes) else so
se = se.decode() if isinstance(se, bytes) else se
print("stdout tail:\n", so[-1500:])
print("stderr tail:\n", se[-1500:])
print("CaseStatus existed after setup failure:", seen.get("casestatus_exists"))
print("CaseStatus content:\n", (seen.get("casestatus") or "")[-1200:])
print("caseroot exists now:", caseroot.exists())
