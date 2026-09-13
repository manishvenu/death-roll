"""Rewrite a supergrid's longitudes into the 0-360 convention.

Why this matters for a seam-crossing domain
-------------------------------------------
mom6_forge's Grid.get_bounding_boxes derives a domain's longitude window from a
raw min/max, and treats a span wider than 180 degrees as proof the edge crosses
the antimeridian:

    if lon_max - lon_min > 180:
        lon_min, lon_max = -180.0, 179.999

Written in the (-180, 180] convention, both Alaska domains have nodes at both
ends of that interval, so min/max come out as -180/180, a span of 360, and the
bounding box is widened to the entire globe. The bathymetry read then pulls all
86400 GEBCO longitudes instead of a regional window -- which is what produced
the 64 GB OOM, and then a Cressman weights array too large for HDF to write.

In 0-360 the same domains are contiguous (alaska_big 156.8-241.9, alaska_small
171.2-200.8), the span is well under 180, and the widening branch is never
taken. Only `x` is touched: dx, dy, area and angle_dx are computed from node
positions that do not move, so they stay valid.
"""

import shutil
import sys
from pathlib import Path

import numpy as np
import xarray as xr


def normalize(path, backup=True):
    path = Path(path)
    with xr.open_dataset(path) as ds:
        ds = ds.load()
    x = np.asarray(ds.x)
    span_before = float(x.max() - x.min())
    x360 = x % 360.0
    span_after = float(x360.max() - x360.min())

    if span_after >= span_before:
        print(f"{path.name}: already contiguous ({span_before:.2f} deg), left alone")
        return False

    if backup:
        bak = path.with_suffix(".nc.bak_lon180")
        if not bak.exists():
            shutil.copy2(path, bak)
            print(f"  backed up to {bak.name}")

    ds["x"].values = x360
    ds.to_netcdf(path)
    print(f"{path.name}: x [{x.min():.3f}, {x.max():.3f}] span {span_before:.2f} deg"
          f"  ->  [{x360.min():.3f}, {x360.max():.3f}] span {span_after:.2f} deg")
    return True


if __name__ == "__main__":
    for p in sys.argv[1:]:
        normalize(p)
