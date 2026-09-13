"""Create alaska_big_flat: alaska_big with its bathymetry capped, vgrid rebuilt.

Why
---
alaska_big blew up on model day 3. All 1462 velocity truncations landed on j=0 --
the southern open boundary itself -- clustered in ~5 cells near 159.9 E, 50.84 N,
where the domain crosses the Kuril-Kamchatka Trench. Velocities reached 7.6 m/s,
driven by the pressure-gradient term.

The reason is a mismatch between the domain and its forcing product:

    GLORYS depth levels : 50, deepest 5727.9 m
    alaska_big topog    : max 7888.0 m, 2512 cells deeper than 5500 m

1968 model cells sat below any GLORYS data, so those layers were filled by
extrapolation -- and an open boundary was laid straight across the deepest part
of it, with a 2400 m depth change over ~35 km. alaska_small never hit this: its
max depth is 92 m, entirely inside GLORYS's range.

Capping MAXIMUM_DEPTH in user_nl_mom does NOT work; it is fatal:

    FATAL: MOM_ALE, initialize_regridding: MAXIMUM_DEPTH was too shallow to
           adjust bottom layer of DZ!

because the 75-level vgrid was generated from topo.max_depth and its layers sum
to exactly 7888 m. Depth and vgrid are locked together, so the cap has to be
applied to the bathymetry and the vgrid regenerated from it.

What this does
--------------
Same horizontal grid (the supergrid is untouched -- the geometry was never the
problem), bathymetry read back from the existing topog file rather than
re-regridded from GEBCO, then clipped to DEPTH_CAP, then a fresh vgrid built from
the capped maximum. Forcings are configured but NOT processed: the boundary files
are reused (see the companion copy step) because they live on GLORYS's 50
z-levels and are independent of the model vgrid. The initial conditions are not
reusable -- they are on the 75 model levels -- but cost only ~145 s to redo.

A new caseroot and inputdir are used deliberately, so the existing alaska_big
case and its 2.7 hours of downloaded boundary data stay intact.
"""

import os
from pathlib import Path

import numpy as np

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

HERE = Path("/glade/u/home/manishrv/documents/croc/dev/tutorial_grid_tests")
SUPERGRID = HERE / "alaska_grids" / "alaska_big" / "ocean_hgrid.nc"
OLD_INPUT = Path("/glade/u/home/manishrv/scratch/croc_input/alaska_big")
OLD_TOPOG = OLD_INPUT / "ocnice" / "ocean_topog_alaska_big_ad9099.nc"

CASEROOT = Path("/glade/u/home/manishrv/croc_cases/alaska_big_flat")
INPUTDIR = Path("/glade/u/home/manishrv/scratch/croc_input/alaska_big_flat")
CESMROOT = Path("/glade/u/home/manishrv/work/installs/full_regional_cesm")

# Comfortably inside GLORYS's deepest level (5727.9 m), so no model cell sits
# below where boundary data exists.
DEPTH_CAP = 5500.0
MIN_DEPTH = 9.5
NK = 75


def main():
    grid = Grid.from_supergrid(str(SUPERGRID), name="alaska_big_flat")
    print(f"grid: {grid.nx} x {grid.ny}")

    topo = Topo(grid, min_depth=MIN_DEPTH, git=False)
    # Read the bathymetry back rather than re-running the GEBCO regrid: the
    # horizontal field is fine, only its deep tail is the problem.
    topo.set_depth_via_topog_file(str(OLD_TOPOG), varname="depth")
    d = np.asarray(topo.depth)
    deep = int((d > DEPTH_CAP).sum())
    print(f"depth before cap: max {np.nanmax(d):.1f} m, {deep} cells > {DEPTH_CAP:.0f} m")

    topo.depth = np.minimum(d, DEPTH_CAP)
    d2 = np.asarray(topo.depth)
    print(f"depth after  cap: max {np.nanmax(d2):.1f} m, "
          f"{int((d2 > DEPTH_CAP + 0.1).sum())} cells still above the cap")
    assert topo.max_depth <= DEPTH_CAP + 0.1, "cap did not take"

    # Built from the capped maximum, so vgrid and bathymetry agree and MOM_ALE
    # has a bottom layer it can adjust.
    vgrid = VGrid.hyperbolic(nk=NK, depth=topo.max_depth, ratio=20.0)
    print(f"vgrid: {NK} levels summing to {float(np.sum(vgrid.dz)):.1f} m")

    case = Case(
        cesmroot=CESMROOT,
        caseroot=CASEROOT,
        inputdir=INPUTDIR,
        ocn_grid=grid,
        ocn_topo=topo,
        ocn_vgrid=vgrid,
        compset="GR_JRA",
        machine="derecho",
        project="ncgd0011",
        atm_grid_name="TL319",
        override=False,
    )
    case.configure_forcings(
        date_range=["2018-06-01 00:00:00", "2018-08-15 00:00:00"],
        boundaries=["north", "south", "east", "west"],
        product_name="glorys",
        function_name="get_glorys_data_from_rda",
    )
    print("configure_forcings done -- process_forcings deliberately NOT run")
    print(f"caseroot: {CASEROOT}")
    print(f"inputdir: {INPUTDIR}")


if __name__ == "__main__":
    main()
