"""Cut a North Pacific GEBCO subset in 0-360 longitude.

Why
---
Both Alaska domains cross the antimeridian. For a seam-crossing request
mom6_forge's longitude_slicer deliberately returns the *entire* dataset rather
than a sliver either side of the seam, so a regional domain still reads all
86400 GEBCO longitude points. Combined with the latitude window that is
491,616,000 source points, and xESMF's ESMF backend overflows its coordinate
buffer allocating that:

    Source:  lat=5690, lon=86400  (491,616,000 points)
    TypeError: buffer is too small for requested array

Re-expressing the region in 0-360 makes it contiguous -- 130 E to 250 E is one
unbroken span with no seam to cross -- so the slicer can take a real window and
the source drops by roughly 3.6x. Native 15 arcsec resolution is preserved;
only the extent changes.

The output keeps elevation as int16, matching the source, so the file stays
small enough to be cheap to read repeatedly.

Run
---
    python make_np_gebco.py
"""

import os

import numpy as np
import xarray as xr

SRC = "/glade/derecho/scratch/manishrv/ice/croc/gebco/GEBCO_2024.nc"
DST = "/glade/derecho/scratch/manishrv/ice/croc/gebco/GEBCO_2024_north_pacific.nc"

# Generous margin around both domains: alaska_big spans 156.8 E -> 236.2 E
# (123.9 W) and 45.0 -> 67.7 N; alaska_small sits inside that.
LON_MIN, LON_MAX = 130.0, 250.0     # in 0-360
LAT_MIN, LAT_MAX = 38.0, 75.0


def main():
    ds = xr.open_dataset(SRC, chunks={"lat": 2000, "lon": 10800})
    band = ds.sel(lat=slice(LAT_MIN, LAT_MAX))

    # East half keeps its own longitudes; west half is shifted past 180 so the
    # two join into one increasing axis. GEBCO cell centres sit at +-179.99792,
    # so the halves abut without a duplicate at exactly 180.
    east = band.sel(lon=slice(LON_MIN, 180.0))
    west = band.sel(lon=slice(-180.0, LON_MAX - 360.0))
    west = west.assign_coords(lon=west.lon + 360.0)
    out = xr.concat([east, west], dim="lon")

    lon = out.lon.values
    assert np.all(np.diff(lon) > 0), "longitude axis is not strictly increasing"
    print(f"lon {lon[0]:.5f} -> {lon[-1]:.5f}  ({lon.size} points)")
    print(f"lat {float(out.lat[0]):.5f} -> {float(out.lat[-1]):.5f} "
          f"({out.lat.size} points)")
    print(f"total {lon.size * out.lat.size / 1e6:.1f} M points "
          f"(was {86400 * 5690 / 1e6:.0f} M for a seam-crossing read)")

    enc = {"elevation": {"dtype": "int16", "zlib": True, "complevel": 1,
                         "_FillValue": None}}
    out.to_netcdf(DST, encoding=enc)
    print(f"wrote {DST}  ({os.path.getsize(DST) / 1e9:.2f} GB)")


if __name__ == "__main__":
    main()
