"""vcg-a9: Case(machine=None) -- the documented default -- always raises, although
__init__ has `self.machine = machine or self.cime.machine` (dead fallback)."""
import sys
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
from visualCaseGen.initialize import initialize as initialize_visualCaseGen

D = Path(__file__).resolve().parent
CESMROOT = Path("~/work/installs/CESM_crocodash").expanduser()

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="auda9")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="auda9")

cime = initialize_visualCaseGen(CESMROOT)
print("visualCaseGen detected cime.machine =", repr(cime.machine),
      "| in cime.machines:", cime.machine in cime.machines, flush=True)

kw = dict(cesmroot=CESMROOT, compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
          ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
          project="ncgd0011", override=True)

# 1) machine omitted (documented default None)
try:
    Case(caseroot=D / "cases/audit_vcga9_1", inputdir=D / "input/audit_vcga9_1", **kw)
    print("1) machine omitted: Case created (no bug)")
except Exception as e:
    print("1) machine omitted -> RAISED", type(e).__name__ + ":", e, flush=True)
print("   caseroot created?", (D / "cases/audit_vcga9_1").exists(), flush=True)

if len(sys.argv) > 1 and sys.argv[1] == "fix":
    # 2) monkeypatch the smallest fix: apply the fallback before the check
    orig = Case.init_args_check
    def patched(*, cime, machine, **k):
        return orig(cime=cime, machine=machine or cime.machine, **k)
    Case.init_args_check = staticmethod(patched)
    c = Case(caseroot=D / "cases/audit_vcga9_2", inputdir=D / "input/audit_vcga9_2", **kw)
    print("2) with fix: Case created, case.machine =", repr(c.machine), flush=True)
    import re
    txt = (Path(c.caseroot) / "env_case.xml").read_text()
    print("   env_case.xml:", [l.strip() for l in txt.splitlines() if 'id="MACH"' in l])
