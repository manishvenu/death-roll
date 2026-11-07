"""Create a real CR_JRA case against CESM_wu2r05 after a case against CESM_crocodash
(mode after_A) or in a fresh process (mode fresh), and compare CrocoDash's idea of
the compset with what create_newcase actually wrote."""
import sys, time, subprocess
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

mode = sys.argv[1]
S = Path(__file__).resolve().parent
A = Path("~/work/installs/CESM_crocodash").expanduser()
B = Path("~/work/installs/CESM_wu2r05").expanduser()
(S / "cases").mkdir(exist_ok=True); (S / "input").mkdir(exist_ok=True)
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="va4")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="va4")
if mode == "after_A":
    Case(cesmroot=A, caseroot=S / "cases/audit_va4_A", inputdir=S / "input/audit_va4_A",
         compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
         ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
         machine="derecho", project="ncgd0011", override=True)
    print("#### case A done", flush=True)
grid2 = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="vb4")
topo2 = Topo(grid2, min_depth=10.0); topo2.set_flat(1000.0)
name = f"audit_va4_Bfull_{mode}"
try:
    cb = Case(cesmroot=B, caseroot=S / f"cases/{name}", inputdir=S / f"input/{name}",
              compset="CR_JRA", ocn_grid=grid2, ocn_topo=topo2, ocn_vgrid=vgrid, atm_grid_name="TL319",
              machine="derecho", project="ncgd0011", override=True)
except Exception as e:
    print(f"#### case B failed: {type(e).__name__}: {e}")
    sys.exit(0)
print("#### case B CrocoDash compset_lname =", cb.compset_lname)
print("#### case B runoff_in_compset       =", cb.runoff_in_compset)
env_case = (S / f"cases/{name}/env_case.xml").read_text()
import re
print("#### case B env_case.xml COMPSET    =", re.search(r'id="COMPSET" value="([^"]+)"', env_case).group(1))
print("#### case B env_case.xml CIMEROOT   =", re.search(r'id="CIMEROOT" value="([^"]+)"', env_case).group(1))
