"""Write a tiny synthetic parent MOM6 history file (noleap, daily, 2020-01-01..2020-03-10),
like a CESM MOM6 run's ocean_daily output, for CESM_MOM_OUTPUT.get_mom6_output_data."""
import sys
from pathlib import Path
import numpy as np, xarray as xr

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
t = xr.date_range("2020-01-01 12:00", "2020-03-10 12:00", freq="D", calendar="noleap", use_cftime=True)
xh = np.arange(-64.875, -53.0, 0.25); yh = np.arange(26.125, 38.0, 0.25)
xq = xh + 0.125; yq = yh + 0.125
z_l = np.array([5.0, 50.0, 200.0, 500.0, 900.0])
nt, nz = len(t), len(z_l)
rng = np.random.default_rng(0)
def f(shape, base): return (base + rng.random(shape)).astype("f4")
ds = xr.Dataset(
    {
        "thetao": (("time", "z_l", "yh", "xh"), f((nt, nz, len(yh), len(xh)), 15.0)),
        "so": (("time", "z_l", "yh", "xh"), f((nt, nz, len(yh), len(xh)), 35.0)),
        "uo": (("time", "z_l", "yh", "xq"), f((nt, nz, len(yh), len(xq)), 0.0) * 0.1),
        "vo": (("time", "z_l", "yq", "xh"), f((nt, nz, len(yq), len(xh)), 0.0) * 0.1),
        "zos": (("time", "yh", "xh"), f((nt, len(yh), len(xh)), 0.0) * 0.1),
    },
    coords={"time": t, "xh": xh, "yh": yh, "xq": xq, "yq": yq, "z_l": z_l},
)
ds.time.encoding.update(units="days since 2000-01-01 00:00:00", calendar="noleap")
ds.to_netcdf(out / "parent.mom6.h.ocean_daily.2020.nc")
print("wrote", out, nt, "records; calendar noleap; first", t[0], "last", t[-1])
