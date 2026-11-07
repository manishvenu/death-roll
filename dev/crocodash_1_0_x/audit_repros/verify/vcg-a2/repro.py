"""vcg-a2: Case(override=True) rmtree's <CIME_OUTPUT_ROOT>/<case name> wholesale,
not just the EXEROOT/RUNDIR (bld/, run/) that CIME's create_newcase checks."""
import sys, os
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
NAME = "audit_vvcga2_1"
ROOT = Path("/glade/derecho/scratch/manishrv")   # Derecho CIME_OUTPUT_ROOT ($SCRATCH)
D = ROOT / NAME

# Stand-in for a directory under CIME_OUTPUT_ROOT that shares the case's name but
# holds more than the old case's bld/run (e.g. <root>/archive with every case's
# short-term archive, or <root>/tmp).
for p, txt in [(D / "bld" / "old_build.o", "old exe"),
               (D / "run" / "old_run.nc", "old run"),
               (D / "othercase" / "hist" / "othercase.mom6.h.0001.nc", "another case's archive"),
               (D / "keep.txt", "unrelated user data")]:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)

def tree(d):
    return sorted(str(p.relative_to(d)) for p in d.rglob("*")) if d.exists() else "MISSING"

print("BEFORE:", tree(D), flush=True)

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="vga2")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="vga2")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases" / NAME, inputdir=S / "input" / NAME,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("cime_output_root =", case.cime.cime_output_root)
print("AFTER: ", tree(D))
for f in ["othercase/hist/othercase.mom6.h.0001.nc", "keep.txt"]:
    print(f"  {f}: {'survived' if (D / f).exists() else 'DELETED'}")
