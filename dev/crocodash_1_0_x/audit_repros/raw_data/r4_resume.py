# The resume path: fetch_raw_chunk sees the file, checks its 4 magic bytes, and skips the fetch.
import sys
from pathlib import Path
import xarray as xr
from CrocoDash.raw_data_access.datasets.reference import REFERENCE_OCEAN
from CrocoDash.forcing import utils
out = Path(sys.argv[1]); f = out / "north_unprocessed.2020-01-01_2020-01-30.nc"
print("partial file size:", f.stat().st_size, "is_valid_netcdf:", utils.is_valid_netcdf(f))
p = utils.fetch_raw_chunk(REFERENCE_OCEAN._access_methods["get_reference_ocean_data"].__func__,
    ["2020-01-01", "2020-01-30"], dict(lat_min=20.0, lat_max=30.0, lon_min=-60.0, lon_max=-50.0),
    out, f.name, ["u","v","ssh","temp","salt"], {"resolution_deg": 0.04}, name="north")
print("fetch_raw_chunk returned without refetching:", p)
try:
    with xr.open_mfdataset([str(p)], combine="nested", concat_dim="time") as ds:   # what _regrid_one_chunk does
        print("opened:", dict(ds.sizes)); print("temp mean", float(ds.temp.mean()))
except Exception as e:
    print("REGRID-side open failed:", type(e).__name__, str(e)[:300])
