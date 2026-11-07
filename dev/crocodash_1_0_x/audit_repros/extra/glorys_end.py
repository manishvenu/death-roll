import sys
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="ge")
topo = Topo(grid, min_depth=10.0); topo.set_flat(3000.0)
vgrid = VGrid.uniform(nk=10, depth=3000.0, name="ge")
case = Case(cesmroot=Path("/glade/u/home/manishrv/work/installs/CESM_crocodash"), caseroot=S/"cases/audit_gend", inputdir=S/"input/audit_gend",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
            atm_grid_name="T62", machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2026-09-18 00:00:00", "2026-09-26 00:00:00"], product_name="GLORYS", function_name="get_glorys_data_from_rda")
try:
    case.process_forcings()
    print("PROCESS DONE (unexpected)")
except BaseException as e:
    print("USER SEES:", type(e).__name__, "|", str(e)[:600])
import os
raw = S/"input/audit_gend/extract_forcings/raw_data"
print("raw files left:", sorted(p.name for p in raw.iterdir()) if raw.exists() else None)
