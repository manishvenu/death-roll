import os, sys, traceback
from pathlib import Path
D = Path(sys.argv[1])
name = sys.argv[2]
print("HOME =", os.environ["HOME"], "| Path.home() =", Path.home(), "| cwd =", os.getcwd(), flush=True)
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="v3a")
topo = Topo(grid, min_depth=10.0); topo.set_flat(500.0)
vgrid = VGrid.uniform(nk=5, depth=500.0, name="v3a")
caseroot = f"rel_cases/{name}"          # relative, with a folder part
inputdir = D / "inputs" / name          # absolute, parent exists
try:
    Case(cesmroot=os.environ["CESMROOT"], caseroot=caseroot, inputdir=inputdir,
         compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
         ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
         machine="derecho", project="ncgd0011", override=True)
    print("CASE CREATED OK")
except BaseException as e:
    print("EXCEPTION:", type(e).__name__, str(e)[:500])
print("cwd case exists        :", (Path.cwd() / caseroot).exists())
print("home case exists       :", (Path.home() / caseroot).exists(),
      sorted(p.name for p in (Path.home() / caseroot).iterdir())[:8] if (Path.home()/caseroot).exists() else "")
print("inputdir exists        :", inputdir.exists())
