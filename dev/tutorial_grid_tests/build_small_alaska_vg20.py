"""
Timing experiment: same tutorial domain as `small-alaska`, but with 20 vertical
levels instead of 75 (max depth is only 93 m, so 75 levels is overkill).

Raw + regridded GLORYS data is copied over from the `small-alaska` inputdir so
process_forcings only has to redo the vertically-remapped initial condition.
"""

import shutil
from pathlib import Path

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

CASENAME = "small-alaska-vg20"
CESMROOT = "/glade/u/home/manishrv/work/installs/full_regional_cesm"
INPUTDIR = Path("/glade/u/home/manishrv/scratch/croc_input") / CASENAME
CASEROOT = Path("/glade/u/home/manishrv/croc_cases") / CASENAME

SRC_INPUTDIR = Path("/glade/u/home/manishrv/scratch/croc_input/small-alaska")
BATHY = Path(
    "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/"
    "gebco/GEBCO_2024_coarse_x8.nc"
)

# ---------------------------------------------------------------- domain ----
grid = Grid(
    resolution=1 / 12,
    xstart=184,
    lenx=16.0,
    ystart=62.5,
    leny=5.0,
    name="small_alaska",
)

topo = Topo(grid=grid, min_depth=9.5)
topo.set_from_dataset(
    bathymetry_path=BATHY,
    longitude_coordinate_name="lon",
    latitude_coordinate_name="lat",
    vertical_coordinate_name="elevation",
)

# 20 levels instead of 75 -- this is the change under test
vgrid = VGrid.hyperbolic(nk=20, depth=topo.max_depth, ratio=5.0)
print(f"vgrid: nk={len(vgrid.dz)}  max_depth={topo.max_depth}")

# ------------------------------------------------------------------ case ----
case = Case(
    cesmroot=CESMROOT,
    caseroot=CASEROOT,
    inputdir=INPUTDIR,
    ocn_grid=grid,
    ocn_vgrid=vgrid,
    ocn_topo=topo,
    project="CESM0030",
    override=True,
    machine="derecho",
    compset="GR_JRA",
)

case.configure_forcings(
    date_range=["2018-12-01 00:00:00", "2018-12-31 00:00:00"],
    boundaries=["north", "south", "east", "west"],
    function_name="get_glorys_data_from_rda",
)

# ------------------------------------------------- reuse the fetched data ----
# The horizontal grid is identical, so the raw GLORYS cutouts, the regridded
# OBC segments (which stay on GLORYS' 50 native z-levels) and the regridding
# weights are all reusable. Only the IC is remapped onto the model vgrid.
src = SRC_INPUTDIR / "extract_forcings"
dst = INPUTDIR / "extract_forcings"
for sub in ("raw_data", "regridded_data"):
    if (src / sub).is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src / sub, dst / sub, dirs_exist_ok=True)
        n = len(list((dst / sub).rglob("*.nc")))
        print(f"reused {sub}: {n} netCDF files")

case.process_forcings()

print("Case ready at", CASEROOT)
