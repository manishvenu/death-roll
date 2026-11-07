import sys, cdsapi, zipfile
from pathlib import Path
out = Path(sys.argv[1]) / "glofas_fixed.nc"
req = {"system_version": ["version_4_0"], "hydrological_model": ["lisflood"], "product_type": ["consolidated"],
       "variable": ["average_river_discharge_in_the_last_24_hours"], "year": ["2020"], "month": ["01"], "day": ["15"],
       "data_format": "netcdf", "download_format": "unarchived", "area": [31, -98, 18, -80]}
for attempt in (req, {**req, "timespan": ["time_mean"]}):
    try:
        cdsapi.Client().retrieve("cems-glofas-historical", attempt, str(out)); print("OK with", sorted(attempt)); break
    except Exception as e:
        print("FAILED with", sorted(attempt), "|", str(e)[:300])
if out.exists():
    import xarray as xr
    print("is zip", zipfile.is_zipfile(out)); ds = xr.open_dataset(out); print(ds)
