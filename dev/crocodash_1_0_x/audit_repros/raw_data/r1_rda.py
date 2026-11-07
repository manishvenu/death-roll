import sys, time
from pathlib import Path
import xarray as xr, numpy as np
import dask
dask.config.set(scheduler="synchronous")
from CrocoDash.raw_data_access.datasets.glorys import GLORYS
out = Path(sys.argv[1])
cases = {
  "pm_0_360": dict(lon_min=280.0, lon_max=280.5, lat_min=25.0, lat_max=25.5),
  "greenwich": dict(lon_min=-0.3, lon_max=0.3, lat_min=40.0, lat_max=40.3),
}
for name, box in cases.items():
    t=time.time()
    p = GLORYS.get_glorys_data_from_rda(dates=["2020-01-01","2020-01-02"], output_folder=out, output_filename=f"{name}.nc",
        variables=["zos","thetao"], **box)
    ds = xr.open_dataset(p, decode_times=False)
    lon = ds.longitude.values
    print(name, "lon", lon.min(), lon.max(), "n", lon.size, "mono", np.all(np.diff(lon)>0), "requested", box["lon_min"]-1, box["lon_max"]+1)
    print("  lat", ds.latitude.values.min(), ds.latitude.values.max())
    print("  time", ds.time.values, ds.time.attrs)
    print("  lon attrs", ds.longitude.attrs)
    print("  took", time.time()-t)
    ds.close()
