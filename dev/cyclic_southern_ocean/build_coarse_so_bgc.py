"""Coarse stand-in for the 1/12 deg Southern Ocean BGC case: a 2 deg band from
80S to 30S that wraps around in longitude (seam at 73E like tx1_12), closed by
Antarctica in the south, one CESM-HR POP (physics + MARBL tracers) OBC along
the whole north edge. CICE + MARBL + GLOFAS runoff / river nutrients."""

import sys
from pathlib import Path

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

NAME = "so_bgc"
CESMROOT = Path("~/work/crocodile2026/CESM").expanduser()
CASEROOT = Path(f"~/croc_cases/{NAME}").expanduser()
INPUTDIR = Path(f"/glade/u/home/manishrv/scratch/croc_input/{NAME}")
GEBCO = "/glade/campaign/cgd/oce/projects/CROCODILE/workshops/2026/CrocoDash/data/gebco_2026/GEBCO_2026_coarse_x8.nc"
CROC = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc"
MARBL_IC = f"{CROC}/crocogallerydata/bgc/ecosys_jan_IC_omip_latlon_1x1_180W_c231221.nc"
GLOFAS_MESH = f"{CROC}/rof/glofas/dis24/GLOFAS_esmf_mesh_v4.nc"
RIVER_NUTRIENTS = f"{CROC}/rof/river_nutrients/river_nutrients.GNEWS_GNM.glofas.20250916.64bit.nc"

grid = Grid(
    lenx=360.0, leny=50.0, resolution=2.0, xstart=-287.0, ystart=-80.0,
    cyclic_x=True, name=NAME,
)
print("cyclic:", grid.supergrid.is_cyclic_x, "nx, ny:", grid.nx, grid.ny)

topo = Topo(grid, min_depth=10.0, git=False)
topo.set_from_dataset(
    bathymetry_path=GEBCO,
    longitude_coordinate_name="lon",
    latitude_coordinate_name="lat",
    vertical_coordinate_name="elevation",
)
mask = topo.tmask.values.copy()
print("south row wet cells (raw):", int(mask[0].sum()))
mask[0, :] = 0  # Antarctica closes the south edge
topo.user_mask = mask
depth = topo.depth.values
print("north row wet cells:", int((depth[-1] > 0).sum()), "/", grid.nx)

vgrid = VGrid.hyperbolic(nk=30, depth=float(depth.max()), ratio=10.0, name=NAME)

case = Case(
    cesmroot=CESMROOT,
    caseroot=CASEROOT,
    inputdir=INPUTDIR,
    compset="1850_DATM%JRA_SLND_CICE_MOM6%REGIONAL%MARBL-BIO_DROF%GLOFAS_SGLC_SWAV",
    ocn_grid=grid,
    ocn_topo=topo,
    ocn_vgrid=vgrid,
    machine="casper",
    project="ncgd0011",
    ntasks_ocn=20,
    override=True,
)

case.configure_forcings(
    date_range=["2000-01-01 00:00:00", "2000-02-01 00:00:00"],
    product_name="CESM_POP_OUTPUT",
    function_name="get_cesm_single_variable_data",
    marbl_ic_filepath=MARBL_IC,
    rof_esmf_mesh_filepath=GLOFAS_MESH,
    global_river_nutrients_filepath=RIVER_NUTRIENTS,
)
print("boundaries:", case.boundaries)
if "--configure-only" in sys.argv:
    sys.exit(0)
case.process_forcings()
print("DONE")
