import sys, subprocess
from pathlib import Path
from unittest import mock
import numpy as np, xarray as xr
from CrocoDash.raw_data_access.registry import ProductRegistry
ProductRegistry.load()
from CrocoDash.raw_data_access.datasets.glorys import GLORYS
from CrocoDash.raw_data_access.datasets import era5, glofas, reference
S = Path(sys.argv[1])
sp = S / "with space"
print("=== (a) GLORYS CLI script in a folder with a space ===")
p = GLORYS.get_glorys_data_script_for_cli(dates=["2020-01-01","2020-01-07"], lat_min=10, lat_max=11, lon_min=280, lon_max=281,
        output_folder=sp, output_filename="north_unprocessed.2020-01-01_2020-01-07.nc", variables=["uo"])
txt = Path(p).read_text(); print(txt.strip().splitlines()[-1][-200:])
print("bash -n parse; args after -o:", subprocess.run(["bash","-c", "set -- " + txt.strip().splitlines()[-1].split(" -o ")[1] + "; echo \"$1 | $2 | $3\""], capture_output=True, text=True).stdout)
print("=== (b) unknown function name ===")
try:
    ProductRegistry.get_function_default_args("glorys", "get_glorys_data_from_rdaa")
except Exception as e:
    print(type(e).__name__, repr(e))
print("=== (d) ERA5 request boxes ===")
for box in [(-5.0, 5.0), (170.0, 180.0), (-180.0, 180.0), (355.0, 365.0)]:
    try:
        r = era5.build_era5_spectra_request(["2020-01-01","2020-01-02"], 50, 51, *box)
        print(box, "area", r["area"])
    except Exception as e:
        print(box, type(e).__name__, e)
print("=== (e) reference_ocean polar box ===")
po = reference.REFERENCE_OCEAN._access_methods["get_reference_ocean_data"].__func__(
    dates=["2020-01-01","2020-01-01"], lat_min=88.0, lat_max=89.9, lon_min=-180.0, lon_max=180.0, output_folder=S, output_filename="ref_polar.nc", variables=["temp"])
ds = xr.open_dataset(po); print("lat max", float(ds.latitude.max()), "lon range", float(ds.longitude.min()), float(ds.longitude.max()), "n lon", ds.sizes["longitude"]); ds.close()
print("=== (h) GLOFAS request (cdsapi mocked) ===")
class FakeClient:
    def retrieve(self, dataset, request, target):
        print("request hyear", request["hyear"], "hmonth", request["hmonth"], "hday", request["hday"], "download_format", request["download_format"], "target", target)
with mock.patch.object(glofas.cdsapi, "Client", FakeClient):
    glofas.GLOFAS.get_global_data_with_python(dates=["2019-12-30","2020-01-02"], output_folder=S, output_filename="glofas_data.nc")
