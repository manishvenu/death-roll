"""Synthetic native-MOM6 daily-mean output on a NO_LEAP calendar (time at noon)."""
import sys
from pathlib import Path
import numpy as np, xarray as xr, cftime
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
xh = np.arange(-63.0, -52.9, 0.25); yh = np.arange(27.0, 37.1, 0.25)
xq = xh + 0.125; yq = yh + 0.125
z_l = np.array([5., 50., 150., 300., 600., 900., 1200., 1500.])
# 2020-01-25 .. 2020-03-10 noleap daily means stamped at noon
t0 = cftime.DatetimeNoLeap(2020, 1, 25, 12)
times = [t0 + __import__("datetime").timedelta(days=i) for i in range(45)]
nt, nz = len(times), len(z_l)
def f(shape, v): return np.full(shape, v, dtype="f4")
ds = xr.Dataset(
    {
        "zos": (("time", "yh", "xh"), f((nt, len(yh), len(xh)), 0.1)),
        "thetao": (("time", "z_l", "yh", "xh"), f((nt, nz, len(yh), len(xh)), 10.0)),
        "so": (("time", "z_l", "yh", "xh"), f((nt, nz, len(yh), len(xh)), 35.0)),
        "uo": (("time", "z_l", "yh", "xq"), f((nt, nz, len(yh), len(xq)), 0.05)),
        "vo": (("time", "z_l", "yq", "xh"), f((nt, nz, len(yq), len(xh)), 0.02)),
    },
    coords={"time": times, "xh": xh, "yh": yh, "xq": xq, "yq": yq, "z_l": z_l},
)
ds.time.encoding.update(units="days since 2000-01-01 00:00:00", calendar="noleap")
ds.to_netcdf(out / "parent.ocean_daily.nc", unlimited_dims=["time"])
print(ds.time.values[[0, -1]])
