"""raw_data-a5: GLOFAS.get_global_data_with_python request shape + zip-under-.nc.

cdsapi.Client is mocked (no network). The fake server honours the request the
way the ECMWF datastores do: hyear x hmonth x hday is a Cartesian product
(invalid dates dropped), and download_format='zip' returns a zip archive.
"""
import itertools, zipfile, io, sys, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr

import CrocoDash.raw_data_access.datasets.glofas as gl
print("glofas module:", gl.__file__)

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
captured = {}

class FakeClient:
    def retrieve(self, dataset, request, target):
        captured.update(dataset=dataset, request=request, target=str(target))
        days = []
        for y, m, d in itertools.product(request["hyear"], request["hmonth"], request["hday"]):
            try:
                days.append(dt.date(int(y), int(m), int(d)))
            except ValueError:
                pass
        days = sorted(days)
        captured["served_days"] = days
        ds = xr.Dataset({"dis24": ("valid_time", np.zeros(len(days)))},
                        coords={"valid_time": pd.to_datetime(days)})
        nc_bytes = ds.to_netcdf()  # in-memory netCDF3
        if request.get("download_format") == "zip":
            with zipfile.ZipFile(target, "w") as z:
                z.writestr("data_0.nc", nc_bytes)
        else:
            Path(target).write_bytes(nc_bytes)
        return target

gl.cdsapi.Client = FakeClient

for window in (["2019-12-30", "2020-01-02"], ["2020-01-30", "2020-02-02"], ["2020-01-15", "2020-03-15"]):
    captured.clear()
    p = gl.GLOFAS.get_global_data_with_python(dates=window, output_folder=OUT,
                                               output_filename=f"glofas_{window[0]}.nc")
    r = captured["request"]
    want = pd.date_range(*window)
    served = captured["served_days"]
    outside = [d for d in served if not (want[0].date() <= d <= want[-1].date())]
    print(f"\nwindow {window}: returned path {p}")
    print("  hyear", r["hyear"], "hmonth", r["hmonth"], "hday", r["hday"], "download_format", r["download_format"])
    print(f"  requested {len(want)} days, request selects {len(served)} days, {len(outside)} outside window"
          f" (first few outside: {[str(d) for d in outside[:4]]})")
    print("  is zip archive:", zipfile.is_zipfile(p))
    try:
        xr.open_dataset(p).close()
        print("  xr.open_dataset OK")
    except Exception as e:
        print(f"  xr.open_dataset FAILED: {type(e).__name__}: {str(e).splitlines()[0][:200]}")
