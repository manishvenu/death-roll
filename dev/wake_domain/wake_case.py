"""Island-wake showcase: the sketch's 7-segment / 2-headland domain, forced
by an idealized zonal jet so the headlands shed real von-Karman-style wakes.

Same "one interior segment + topo masking" trick proven by the NCAR case,
generalized to 7 segments of mixed orientation (cardinal + interior,
horizontal + vertical), built in a shuffled (non-perimeter) order, with two
segments' extents deliberately overlapping -- exactly the flexibility the
Segment refactor (regional-mom6 PR #315) was built to support.

Forcing is synthetic, not GLORYS: CrocoDash's GET phase is idempotent by
filename, so generate_idealized_forcing.py plants fake-but-GLORYS-shaped raw
files before process_forcings() runs, and the real REGRID/MERGE/IC pipeline
processes them exactly as it would real data.
"""

from pathlib import Path

import numpy as np
import xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
from regional_mom6.segment import Segment

from mask_design_wake import (
    NX,
    NY,
    ocean,
    SEGMENT_SPECS,
    SALINITY_ANOMALY_PSU,
    JET_SPEED,
    JET_EDGE_TAPER_ROWS,
    _center_row_slice,
    _center_col_slice,
)
from generate_idealized_forcing import build_idealized_dataset, write_raw_file

RESOLUTION = 1.0 / 12.0
XSTART = -45.0
YSTART = 32.0

CESMROOT = Path("~/work/installs/full_regional_cesm").expanduser()
CASEROOT = Path("~/croc_cases/wake_domain").expanduser()
INPUTDIR = Path("/glade/u/home/manishrv/scratch/croc_input/wake_domain")

START_DATE = "2020-06-01 00:00:00"
END_DATE = "2020-06-17 00:00:00"  # 16 days requested, run 15 (edge-case buffer)

grid = Grid(
    lenx=NX * RESOLUTION,
    leny=NY * RESOLUTION + 1e-6,  # avoid float floor-rounding grid.ny down by 1
    resolution=RESOLUTION,
    xstart=XSTART,
    ystart=YSTART,
    name="wake_domain",
)
assert grid.nx == NX and grid.ny == NY, f"grid is {grid.nx}x{grid.ny}, expected {NX}x{NY}"
topo = Topo(grid, min_depth=10.0, git=False)
topo.set_flat(1000.0)
topo.depth = np.where(ocean, 1000.0, 0.0)
# Defensive: remove any one-cell-wide channels/lakes and diagonal-only land
# touches our hand-authored mask might still contain -- MOM6's ESMF mesh vs.
# internal-mask consistency check aborts on exactly this kind of feature.
topo.fill_inland_lakes_and_channels()

vgrid = VGrid.uniform(nk=10, depth=1000.0, name="wake_domain")

case = Case(
    cesmroot=CESMROOT,
    caseroot=CASEROOT,
    inputdir=INPUTDIR,
    compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
    ocn_grid=grid,
    ocn_topo=topo,
    ocn_vgrid=vgrid,
    atm_grid_name="T62",
    machine="derecho",
    project="ncgd0011",
    override=True,
)

hgrid = xr.open_dataset(case.supergrid_path)


def build_segment(name, spec):
    if spec["kind"] == "cardinal":
        ir = spec["index_range"]
        # Center-based (odd-length) slice -- MOM6's BRUSHCUTTER_MODE requires
        # an odd point count along every segment ("on the supergrid"); a
        # corner-based slice(2*lo, 2*hi+2) is even-length and gets rejected
        # with "segment data are not on the supergrid".
        index_range = None if ir is None else slice(2 * ir[0] + 1, 2 * ir[1] + 2)
        return Segment.cardinal(
            hgrid, orientation=spec["orientation"], segment_name=name,
            index_range=index_range, topo=topo,
        )
    if spec["kind"] == "interior_horizontal":
        idx, rng = _center_row_slice(spec["row"], *spec["col_range"])
        return Segment.from_hgrid(
            hgrid, axis="nyp", index=idx, index_range=rng, segment_name=name,
            topo=topo, ocean_side=spec["ocean_side"],
        )
    if spec["kind"] == "interior_vertical":
        if spec["row_range"] is None:
            idx = 2 * spec["col"] + 1
            rng = None
        else:
            idx, rng = _center_col_slice(spec["col"], *spec["row_range"])
        return Segment.from_hgrid(
            hgrid, axis="nxp", index=idx, index_range=rng, segment_name=name,
            topo=topo, ocean_side=spec["ocean_side"],
        )
    raise ValueError(spec["kind"])


boundaries = [build_segment(name, spec) for name, spec in SEGMENT_SPECS.items()]
print("Built segments (shuffled construction order):")
for b in boundaries:
    print(f"  {b.segment_name}: {b.mom6_obc_position_string()}")

case.configure_forcings(
    date_range=[START_DATE, END_DATE],
    boundaries=boundaries,
    function_name="get_glorys_data_from_rda",
)

# --- Plant synthetic raw files so process_forcings() never calls the real
# GLORYS accessor (idempotent-by-filename GET phase; see fetch_raw_chunk). ---
raw_dir = INPUTDIR / "extract_forcings" / "raw_data"
raw_dir.mkdir(parents=True, exist_ok=True)

lon_min, lon_max = XSTART, XSTART + NX * RESOLUTION
lat_min, lat_max = YSTART, YSTART + NY * RESOLUTION
jet_lat_lo = YSTART + JET_EDGE_TAPER_ROWS * RESOLUTION
jet_lat_hi = YSTART + NY * RESOLUTION - JET_EDGE_TAPER_ROWS * RESOLUTION

start_str = START_DATE.split()[0]
end_str = END_DATE.split()[0]

# Each boundary gets its own dataset -- identical jet/temp physics, but with
# a distinct salinity anomaly baked in (see SALINITY_ANOMALY_PSU) so inflow
# from each of the 7 OBCs is traceable in the output salinity field.
for name in SEGMENT_SPECS:
    seg_ds = build_idealized_dataset(
        lon_min, lon_max, lat_min, lat_max,
        start_str, end_str,
        jet_speed=JET_SPEED,
        jet_taper_lat_lo_full=jet_lat_lo,
        jet_taper_lat_hi_full=jet_lat_hi,
        salinity_anomaly=SALINITY_ANOMALY_PSU[name],
    )
    write_raw_file(seg_ds, raw_dir / f"{name}_unprocessed.{start_str}_{end_str}.nc")

import pandas as pd

ic_end = (pd.Timestamp(start_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
ic_ds = build_idealized_dataset(
    lon_min, lon_max, lat_min, lat_max,
    start_str, ic_end,
    jet_speed=JET_SPEED,
    jet_taper_lat_lo_full=jet_lat_lo,
    jet_taper_lat_hi_full=jet_lat_hi,
)
write_raw_file(ic_ds, raw_dir / "ic_unprocessed.nc")

case.process_forcings()

print(f"Case ready: {case.caseroot}")
