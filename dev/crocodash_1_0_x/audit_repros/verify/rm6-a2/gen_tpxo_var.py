"""Synthetic TPXO9.v1-shaped files whose amplitudes vary smoothly in lon
(period 12 deg, continuous across 0/360) so seam interpolation is testable:
  ha = 0.5 + 0.3 sin(30*lon) m, ua = 10 + 3 sin(30*lon) cm/s, va = 6 + 2 cos(30*lon) cm/s."""
import sys
from pathlib import Path
import numpy as np, xarray as xr
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
nx, ny = 2160, 1081
i = np.arange(nx)[:, None] * np.ones((1, ny)); j = np.ones((nx, 1)) * np.arange(ny)[None, :]
lon_z = (i + 1) / 6.0; lat_z = -90.0 + j / 6.0
lon_u = (i + 0.5) / 6.0; lat_u = lat_z
lon_v = lon_z; lat_v = -90.0 - 1 / 12 + j / 6.0
s = lambda lon: np.sin(np.radians(30 * lon)); c = lambda lon: np.cos(np.radians(30 * lon))
F = lambda a: (("nc", "nx", "ny"), a[None].astype("f8"))
xr.Dataset({"ha": F(0.5 + 0.3 * s(lon_z)), "hp": F(np.full((nx, ny), 40.0))},
           coords={"lon_z": (("nx", "ny"), lon_z), "lat_z": (("nx", "ny"), lat_z)}).to_netcdf(out / "h_synth.nc")
xr.Dataset({"ua": F(10 + 3 * s(lon_u)), "up": F(np.full((nx, ny), 20.0)),
            "va": F(6 + 2 * c(lon_v)), "vp": F(np.full((nx, ny), 110.0))},
           coords={"lon_u": (("nx", "ny"), lon_u), "lat_u": (("nx", "ny"), lat_u),
                   "lon_v": (("nx", "ny"), lon_v), "lat_v": (("nx", "ny"), lat_v)}).to_netcdf(out / "u_synth.nc")
