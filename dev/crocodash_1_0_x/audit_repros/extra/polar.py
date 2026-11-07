import sys, json
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1]); tag = sys.argv[2]; crs = sys.argv[3]
EXT = [float(v) for v in sys.argv[4:8]] if len(sys.argv) > 4 else [-1_000_000, 1_000_000, -1_000_000, 1_000_000]
GEBCO = "/glade/campaign/cgd/oce/projects/CROCODILE/workshops/2026/CrocoDash/data/gebco_2026/GEBCO_2026_coarse_x8.nc"
grid = Grid.from_projection(crs=crs, x_min=EXT[0], x_max=EXT[1], y_min=EXT[2], y_max=EXT[3],
                            resolution_m=50_000, name=f"pol{tag}")
print("grid", grid.nx, grid.ny, "lat", float(grid.tlat.min()), float(grid.tlat.max()))
topo = Topo(grid=grid, min_depth=9.5)
topo.set_from_dataset(bathymetry_path=GEBCO, longitude_coordinate_name="lon",
                      latitude_coordinate_name="lat", vertical_coordinate_name="elevation")
d = topo.depth.values
print("topo ocean frac", float((d > 0).mean()), "max", float(np.nanmax(d)), "nan", int(np.isnan(d).sum()))
vgrid = VGrid.hyperbolic(nk=30, depth=topo.max_depth, ratio=20.0)
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/f"cases/audit_pol_{tag}", inputdir=S/f"input/audit_pol_{tag}",
            compset="GR_JRA", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(
    date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
    function_name="get_glorys_data_from_rda", restore_ice=True,
    cice_product_name="cice_restart", cice_function_name="get_cice_restart_subset",
    cice_function_args={"restart_path": "/glade/u/home/dbailey/b.e30_alpha09b.B1850C_MTso.ne30_t233_wgx3.360.cice.r.0201-01-01-00000.nc",
                        "grid_path": "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/tx2_3v3/cice_grid_tx2_3v3_260305_cdf5.nc"})
case.process_forcings()
print("PROCESS DONE")
