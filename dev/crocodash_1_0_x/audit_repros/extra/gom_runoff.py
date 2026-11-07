import sys, time
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1]); t0 = time.time()
GEBCO = "/glade/campaign/cgd/oce/projects/CROCODILE/workshops/2026/CrocoDash/data/gebco_2026/GEBCO_2026_coarse_x8.nc"
grid = Grid(lenx=18.0, leny=13.0, resolution=0.25, xstart=-98.0, ystart=18.0, name="gom")
topo = Topo(grid, min_depth=9.5)
topo.set_from_dataset(bathymetry_path=GEBCO, longitude_coordinate_name="lon", latitude_coordinate_name="lat", vertical_coordinate_name="elevation")
vgrid = VGrid.hyperbolic(nk=20, depth=topo.max_depth, ratio=20.0)
case = Case(cesmroot=Path("/glade/u/home/manishrv/work/installs/CESM_crocodash"), caseroot=S/"cases/audit_gom", inputdir=S/"input/audit_gom",
            compset="CR_JRA", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"], product_name="reference_ocean", function_name="get_reference_ocean_data")
case.process_forcings(process_ic=False, process_bc=False)
print("PROCESS DONE", round(time.time() - t0, 1), "s")
