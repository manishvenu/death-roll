"""vcg-a7: a failed second Case() breaks the CASEROOT guard in configure_forcings of an earlier case."""
import sys, traceback
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
from ProConPy.config_var import cvars

S = Path(__file__).resolve().parent
CESMROOT = Path("~/work/installs/CESM_crocodash").expanduser()
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a7")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="a7")
common = dict(compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
              ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
              machine="derecho", project="ncgd0011", override=True)
CF = dict(product_name="reference_ocean", function_name="get_reference_ocean_data")

def state():
    return ("CASEROOT" in cvars, cvars["CASEROOT"].value if "CASEROOT" in cvars else "<missing>")

A = Case(cesmroot=CESMROOT, caseroot=S/"cases/audit_va7_A", inputdir=S/"input/audit_va7_A",
         atm_grid_name="T62", **common)
print("A created; cvars CASEROOT:", state(), flush=True)
A.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"], **CF)
print("A.configure_forcings #1 OK", flush=True)

# --- step 2: a second Case() with a typo in atm_grid_name
try:
    Case(cesmroot=CESMROOT, caseroot=S/"cases/audit_va7_B", inputdir=S/"input/audit_va7_B",
         atm_grid_name="T63x", **common)
except Exception as e:
    print("second Case() (bad atm_grid_name) raised:", type(e).__name__, str(e)[:200], flush=True)
print("cvars CASEROOT after failed B:", state(), flush=True)
try:
    A.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-04 00:00:00"], **CF)
    print("A.configure_forcings #2 OK (unexpected)")
except Exception as e:
    print("A.configure_forcings #2 raised:", type(e).__name__, repr(e)[:300], flush=True)
    traceback.print_exc(limit=-4)

# --- step 3: a second Case() with a mistyped cesmroot
try:
    Case(cesmroot=S/"no_such_cesm", caseroot=S/"cases/audit_va7_C", inputdir=S/"input/audit_va7_C",
         atm_grid_name="T62", **common)
except BaseException as e:
    print("second Case() (missing cesmroot) raised:", type(e).__name__, str(e)[:200], flush=True)
print("cvars CASEROOT after failed C:", state(), flush=True)
try:
    A.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-04 00:00:00"], **CF)
    print("A.configure_forcings #3 OK (unexpected)")
except Exception as e:
    print("A.configure_forcings #3 raised:", type(e).__name__, repr(e)[:300], flush=True)
    traceback.print_exc(limit=-4)
