# Step 1: a tiny NYF source case with forcings configured (reference_ocean, no network).
import sys, time
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
t0 = time.time()
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a5")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a5")
case = Case(
    cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
    caseroot=S / "cases/audit_v_a5_src",
    inputdir=S / "inputs/audit_v_a5_src",
    compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
    ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
    machine="derecho", project="ncgd0011", override=True,
)
case.configure_forcings(
    date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
    product_name="reference_ocean", function_name="get_reference_ocean_data",
)
print("source case configured", round(time.time() - t0, 1), "s", flush=True)
