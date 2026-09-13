"""
Build a WW3 points.list file of candidate boundary-spectra output locations,
covering the wgx3v7 global wave grid's active sea points.

Why: CESM's WW3 component supports native point/spectral output
(namelist_definition_ww3.xml's output_type_nml -> type%point%file, default
'points.list') -- the same mechanism NOAA's own global hindcast uses to feed
regional nests. But nothing in cime_config/buildnml copies a points.list into
$RUNDIR automatically (confirmed by reading buildnml directly -- it only
stages wav_in/mod_def.ww3), so this has to be built and placed by hand.

Reads the wgx3v7 grid's own curvilinear coordinate + status-map files
(grid_inp.wgx3v7.260527/g37_{x,y,mapsta}.inp -- plain whitespace-separated
ASCII, one row per line, shape confirmed (116, 100) by inspection) rather than
guessing at an independent land/sea mask, so every point selected is actually
a WW3-active sea point on the exact grid the model will run on.

mapsta convention (WW3 model manual): 0 = excluded/land, 1 = active sea point,
2 = active boundary point, 3 = excluded sea point. Selecting mapsta==1 only
(not >=1) intentionally excludes points 2/3 -- boundary/excluded-sea points
are edge cases not worth the ambiguity for a first-pass candidate list.

Usage:
    python generate_points_list.py --stride 2 --out points.list
"""

import argparse
from pathlib import Path

import numpy as np

GRID_INP_DIR = Path(
    "/glade/campaign/cesm/cesmdata/inputdata/wav/ww3/grid_inp.wgx3v7.260527"
)
NY, NX = 116, 100  # confirmed via `awk 'NR==1{print NF}'` / `wc -l` on g37_x.inp


def load_grid():
    x = np.loadtxt(GRID_INP_DIR / "g37_x.inp").reshape(NY, NX)
    y = np.loadtxt(GRID_INP_DIR / "g37_y.inp").reshape(NY, NX)
    mapsta = np.loadtxt(GRID_INP_DIR / "g37_mapsta.inp").reshape(NY, NX)
    return x, y, mapsta


def build_points(stride=1):
    """Returns (lon, lat, name) for every mapsta==1 point on a stride*stride
    subsample of the grid. stride=1 keeps every active sea point; increase it
    to cut point-output volume (and ww3_ounp postprocessing time) at the cost
    of coarser candidate-point coverage for future regional boundaries.
    """
    x, y, mapsta = load_grid()
    j_idx, i_idx = np.meshgrid(
        np.arange(0, NY, stride), np.arange(0, NX, stride), indexing="ij"
    )
    sea = mapsta[j_idx, i_idx] == 1
    lons = x[j_idx, i_idx][sea]
    lats = y[j_idx, i_idx][sea]
    names = [f"p{j}_{i}" for j, i in zip(j_idx[sea], i_idx[sea])]
    return lons, lats, names


def write_points_list(lons, lats, names, out_path):
    """WW3 points.list format confirmed against real regtest examples
    (regtests/ww3_ta1/input_UPD2_O/points.list, .../mww3_test_08/.../points.list):
    one point per line, 'lon lat 'name'', no header/terminator line needed --
    WW3 reads to EOF.
    """
    with open(out_path, "w") as f:
        for lon, lat, name in zip(lons, lats, names):
            f.write(f"{lon:.4f} {lat:.4f} '{name}'\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--stride",
        type=int,
        default=2,
        help="Subsample every Nth grid row/column of active sea points (default 2).",
    )
    ap.add_argument("--out", type=Path, default=Path("points.list"))
    args = ap.parse_args()

    lons, lats, names = build_points(stride=args.stride)
    write_points_list(lons, lats, names, args.out)
    print(f"Wrote {len(names)} points to {args.out} (stride={args.stride})")
