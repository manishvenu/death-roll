"""Verify mom6_forge get_suggested_smoothing_params on grids mom6_forge itself builds.

Part 1: suggestion per grid (mesh written exactly as Case does: topo.write_esmf_mesh).
Part 2: compute_smoothing_weights with that suggestion.
"""
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
import xarray as xr

import mom6_forge
from mom6_forge import mapping
from mom6_forge.utils import get_avg_resolution_km
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo

print("mom6_forge from", mom6_forge.__file__)
OUT = Path(__file__).parent / "meshes"
OUT.mkdir(exist_ok=True)


def mesh_for(name, grid):
    topo = Topo(grid, min_depth=10.0, git=False)
    topo.set_flat(1000.0)
    p = OUT / f"{name}.nc"
    topo.write_esmf_mesh(str(p))
    return p


def true_res_km(p):
    """Median haversine distance between centers of i- and j-neighbours."""
    ds = xr.open_dataset(p)
    from mom6_forge.utils import get_mesh_dimensions

    c = ds["centerCoords"].values
    return c


grids = {
    "latlon_0.25deg": Grid(lenx=4.0, leny=4.0, resolution=0.25, xstart=-60.0, ystart=30.0, name="a"),
    "center_5km_rot0": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=0.0, name="b"),
    "center_5km_rot45": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=45.0, name="c"),
    "center_5km_rot90": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=90.0, name="d"),
    "center_5km_rot180": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=180.0, name="e"),
    "center_150m_rot0": Grid.from_center(30.0, -60.0, 3e3, 3e3, 150.0, angle_deg=0.0, name="f"),
    "center_10km_lon180": Grid.from_center(55.0, 180.0, 200e3, 200e3, 10e3, angle_deg=0.0, name="g"),
    "polar_3995_10km": Grid.from_projection("EPSG:3995", -100e3, 100e3, -100e3, 100e3, 10e3, name="h"),
}

print(f"{'grid':22s} {'nx x ny':>8s} {'avg_res_km':>11s} {'(rmax, fold)':>14s}  compute_smoothing_weights")
for name, g in grids.items():
    p = mesh_for(name, g)
    res = get_avg_resolution_km(str(p))
    rmax, fold = mapping.get_suggested_smoothing_params(str(p))
    try:
        w = mapping.compute_smoothing_weights(
            xr.open_dataset(p), rmax=rmax, fold=fold, coastline_masking=True
        )
        outcome = f"ok, nnz={w.nnz}"
    except Exception as e:
        outcome = f"{type(e).__name__}: {e}"
    print(f"{name:22s} {g.nx:>3d}x{g.ny:<4d} {res:11.3f} {str((rmax, fold)):>14s}  {outcome}")
