"""Write synthetic TPXO9.v1-shaped files (same (nx, ny) layout and 1/6 deg
staggered lon/lat as the real h_tpxo9.v1.nc / u_tpxo9.v1.nc) with UNIFORM
M2 fields, so the correct regridded answer is known at every point:
  zamp = 0.5 m, uamp = 0.10 m/s, vamp = 0.06 m/s (grid angle 0)."""
import sys
from pathlib import Path
import numpy as np, xarray as xr

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
nx, ny = 2160, 1081
i = np.arange(nx)[:, None] * np.ones((1, ny))
j = np.ones((nx, 1)) * np.arange(ny)[None, :]
lon_z = (i + 1) / 6.0            # 0.1667 .. 360.0  (as in real h file)
lat_z = -90.0 + j / 6.0          # -90 .. 90
lon_u = (i + 0.5) / 6.0          # 0.0833 .. 359.9167 (as in real u file)
lat_u = lat_z
lon_v = lon_z                    # 0.1667 .. 360.0
lat_v = -90.0 - 1 / 12 + j / 6.0  # -90.083 .. 89.917

def f(val):
    return (("nc", "nx", "ny"), np.full((1, nx, ny), val, dtype="f4"))

h = xr.Dataset(
    {"ha": f(0.5), "hp": f(40.0)},
    coords={"lon_z": (("nx", "ny"), lon_z), "lat_z": (("nx", "ny"), lat_z)},
)
h.to_netcdf(out / "h_synth.nc")
u = xr.Dataset(
    {"ua": f(10.0), "up": f(20.0), "va": f(6.0), "vp": f(110.0)},  # cm/s, deg
    coords={
        "lon_u": (("nx", "ny"), lon_u), "lat_u": (("nx", "ny"), lat_u),
        "lon_v": (("nx", "ny"), lon_v), "lat_v": (("nx", "ny"), lat_v),
    },
)
u.to_netcdf(out / "u_synth.nc")
print("lon_z", lon_z.min(), lon_z.max(), "lon_u", lon_u.min(), lon_u.max())
