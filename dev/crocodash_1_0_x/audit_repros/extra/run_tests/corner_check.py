"""Corner-cell check for the -1e20 / +1e20 OBC fill-value lead.

usage: corner_check.py <rundir>
The OBC segment files fill the two segment end points (the domain corners) with -1e20 while the
encoding declares _FillValue = +1e20. If MOM6 used those values, the corner cells would blow up
or drift far from their neighbours. Compare hourly tos/SSH at the four corner cells with the
cells one step inward along the diagonal, and with the interior.
"""
import sys, glob
import numpy as np, xarray as xr

rundir = sys.argv[1]
ds = xr.open_mfdataset(sorted(glob.glob(f"{rundir}/*.mom6.h.sfc*.nc")), decode_times=False)
for v in ("tos", "zos"):
    a = ds[v].values  # (time, y, x)
    ny, nx = a.shape[1:]
    print(f"{v}: records {a.shape[0]}, finite everywhere: {bool(np.isfinite(a).all())}, "
          f"range {np.nanmin(a):.4g}..{np.nanmax(a):.4g}")
    corners = {"SW": (0, 0), "SE": (0, nx - 1), "NW": (ny - 1, 0), "NE": (ny - 1, nx - 1)}
    inward = {"SW": (1, 1), "SE": (1, nx - 2), "NW": (ny - 2, 1), "NE": (ny - 2, nx - 2)}
    for k, (j, i) in corners.items():
        jj, ii = inward[k]
        d = np.abs(a[:, j, i] - a[:, jj, ii])
        print(f"   {k} corner: final {a[-1, j, i]:.4g} vs inward {a[-1, jj, ii]:.4g}; max |diff| over run {d.max():.3g}")
    interior = np.abs(np.diff(a[:, 1:-1, 1:-1], axis=-1)).max()
    print(f"   max |neighbour diff| among interior cells: {interior:.3g}")
