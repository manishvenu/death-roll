"""Topo.set_from_dataset with different lon conventions vs an analytic bathymetry."""
import sys
import numpy as np
import xarray as xr
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo

out = Path("r4_out"); out.mkdir(exist_ok=True)


def f_elev(lon, lat):
    # elevation (positive up), ocean everywhere, smooth in true geographic lon
    return -(2000.0 + 1000.0 * np.sin(np.deg2rad(lon)) + 10.0 * lat)


def make_src(name, lon0, desc_lat=False, res=0.25):
    lon = lon0 + res / 2 + np.arange(int(360 / res)) * res
    lat = -90 + res / 2 + np.arange(int(180 / res)) * res
    if desc_lat:
        lat = lat[::-1]
    LON, LAT = np.meshgrid(lon, lat)
    ds = xr.Dataset({"elevation": (("lat", "lon"), f_elev(LON, LAT).astype("float32"))},
                    coords={"lon": lon, "lat": lat})
    p = out / f"{name}.nc"
    if not p.exists():
        ds.to_netcdf(p)
    return p


src180 = make_src("src180", -180.0)
src360 = make_src("src360", 0.0)
srcdesc = make_src("srcdesc", -180.0, desc_lat=True)

cases = [
    ("x-5_src360", -5.0, src360),
    ("x355_src180", 355.0, src180),
    ("x170_src180", 170.0, src180),
    ("x-60_src360", -60.0, src360),
    ("x170_src360", 170.0, src360),
]
which = sys.argv[1:] or [c[0] for c in cases]
for tag, xs, src in cases:
    if tag not in which:
        continue
    g = Grid(lenx=10.0, leny=5.0, resolution=0.5, xstart=xs, ystart=20.0, name="t")
    t = Topo(g, min_depth=10.0)
    try:
        t.set_from_dataset(str(src), "lon", "lat", "elevation", mask_method="dataset",
                           depth_method="xesmf")
    except Exception as e:
        print(f"[{tag}] FAILED: {type(e).__name__}: {e}")
        continue
    ref = -f_elev(g.tlon.values, g.tlat.values)
    dep = t.depth.values
    err = np.abs(dep - ref)
    print(f"[{tag}] max abs err {np.nanmax(err):.2f} m, nan count {int(np.isnan(dep).sum())}, "
          f"zero count {int((dep == 0).sum())}, ocean cells {int(t.tmask.sum())}/{dep.size}")
