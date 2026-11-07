"""Verify mom6_forge-a9: descending-latitude source bathymetry.

Builds a synthetic global 0.5-degree bathymetry (depth = 1000 + 10*lat, ocean
everywhere) and writes it twice: lat ascending and lat descending (same data,
reversed). Runs Topo.set_from_dataset on a tiny regional grid with each file.
"""

import sys, traceback
from pathlib import Path
import numpy as np
import xarray as xr

import mom6_forge
print("mom6_forge from", mom6_forge.__file__)
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo

here = Path(__file__).parent
lon = np.arange(-179.75, 180.0, 0.5)
lat = np.arange(-89.75, 90.0, 0.5)
LON, LAT = np.meshgrid(lon, lat)
elev = -(1000.0 + 10.0 * LAT)  # elevation, negative = ocean
asc = xr.Dataset({"elevation": (("lat", "lon"), elev)}, coords={"lon": lon, "lat": lat})
desc = asc.isel(lat=slice(None, None, -1))
assert np.all(np.diff(desc.lat.values) < 0)
asc.to_netcdf(here / "src_asc.nc")
desc.to_netcdf(here / "src_desc.nc")


def run(path, label):
    grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a9")
    topo = Topo(grid, min_depth=10.0)
    print(f"\n===== {label}: {path.name} =====")
    try:
        topo.set_from_dataset(
            bathymetry_path=path,
            longitude_coordinate_name="lon",
            latitude_coordinate_name="lat",
            vertical_coordinate_name="elevation",
            mask_method="dataset",
            depth_method="xesmf",
        )
        d = topo.depth.values
        print(f"OK depth min/max = {np.nanmin(d):.2f} / {np.nanmax(d):.2f}")
        expected = 1000.0 + 10.0 * grid.tlat.values
        print(f"max |depth - expected| = {np.nanmax(np.abs(d - expected)):.4f}")
    except Exception as e:
        print("EXCEPTION:", type(e).__name__, e)
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"  raised at {tb.filename}:{tb.lineno}  `{tb.line}`")
        if topo.src is not None:
            print("  src.ds sizes after slicing:", dict(topo.src.ds.sizes))


run(here / "src_asc.nc", "ascending lat")
run(here / "src_desc.nc", "descending lat")

# Monkeypatched fix: sort lat before slicing.
from mom6_forge import _source_bathy

_orig = _source_bathy.SourceBathy._slice_to_domain


def _patched(self, topo, buf=0.5):
    self._ds = self._ds.sortby(self.lat_name)
    return _orig(self, topo, buf=buf)


_source_bathy.SourceBathy._slice_to_domain = _patched
run(here / "src_desc.nc", "descending lat + sortby patch")
