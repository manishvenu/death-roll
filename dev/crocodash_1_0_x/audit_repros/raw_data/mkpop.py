"""Write tiny synthetic CESM-POP-like tseries files (one variable per file)."""
import numpy as np, xarray as xr, cftime
from pathlib import Path

def make(root, year=2000, vars=("SSH","TEMP","SALT","UVEL","VVEL"), angle_deg=30.0, nmon=12):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    nlat, nlon, nz = 12, 16, 3
    lat1 = np.linspace(20, 31, nlat); lon1 = np.linspace(270, 285, nlon)
    TLONG, TLAT = np.meshgrid(lon1, lat1)
    # POP monthly means are stamped at the END of the month (e.g. Feb 1 for January)
    times = [cftime.DatetimeNoLeap(year + (m+1)//12, (m+1)%12+1, 1) for m in range(nmon)]
    z_t = np.array([500., 1500., 2500.])
    for v in vars:
        if v == "SSH":
            data = np.full((nmon, nlat, nlon), 10.0); dims = ("time","nlat","nlon"); units="centimeter"
        elif v == "UVEL":
            data = np.full((nmon, nz, nlat, nlon), 100.0); dims=("time","z_t","nlat","nlon"); units="centimeter/s"
        elif v == "VVEL":
            data = np.zeros((nmon, nz, nlat, nlon)); dims=("time","z_t","nlat","nlon"); units="centimeter/s"
        else:
            data = np.full((nmon, nz, nlat, nlon), 15.0); dims=("time","z_t","nlat","nlon"); units="degC"
        ds = xr.Dataset({v: (dims, data, {"units": units, "long_name": "Velocity in grid-x direction" if v=="UVEL" else v})},
            coords={"time": ("time", times), "z_t": ("z_t", z_t, {"units": "centimeters"}), "z_t_150m": ("z_t_150m", z_t[:2], {"units": "centimeters"}),
                    "TLAT": (("nlat","nlon"), TLAT), "TLONG": (("nlat","nlon"), TLONG),
                    "ULAT": (("nlat","nlon"), TLAT+0.5), "ULONG": (("nlat","nlon"), TLONG+0.5)})
        ds["ANGLE"] = (("nlat","nlon"), np.full((nlat,nlon), np.deg2rad(angle_deg)), {"units": "radians"})
        ds.to_netcdf(root / f"case.pop.h.{v}.{year}01-{year}12.nc")
    return root
