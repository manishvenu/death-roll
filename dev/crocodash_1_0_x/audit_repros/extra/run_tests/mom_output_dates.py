import sys, glob, cftime, pandas as pd, xarray as xr
from CrocoDash.raw_data_access.datasets.cesm_ocean_output import convert_cftime_to_numeric, CESM_MOM_OUTPUT as P
from CrocoDash.raw_data_access.datasets.utils import make_dates_end_inclusive
files = sorted(glob.glob(f"{sys.argv[1]}/*.mom6.h.sfc.*.nc"))
ds = xr.open_mfdataset(files, combine="by_coords")
print("decoded time type:", type(ds.time.values[0]).__name__, "| first", ds.time.values[0], "| last", ds.time.values[-1])
ds2 = convert_cftime_to_numeric(ds, time_var_name="time", calendar=P.calendar)
print("after convert_cftime_to_numeric:", dict(ds2.time.attrs), "first/last", float(ds2.time[0]), float(ds2.time[-1]))
s, e = make_dates_end_inclusive(["2020-01-02", "2020-01-02"]); pdts = pd.to_datetime([s, e])
if "units" in ds2.time.attrs:
    sel = cftime.date2num(pdts.to_pydatetime(), units=ds2.time.attrs["units"], calendar=ds2.time.attrs["calendar"])
else:
    sel = pdts
print("slice bounds for 2020-01-02:", sel, "-> records selected:", ds2.sel(time=slice(sel[0], sel[-1])).sizes["time"])
