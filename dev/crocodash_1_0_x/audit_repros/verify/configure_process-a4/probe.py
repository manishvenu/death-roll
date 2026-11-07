import cftime, xarray as xr, numpy as np, pandas as pd, datetime as dt
print("xarray", xr.__version__, "cftime", cftime.__version__, "pandas", pd.__version__)
t = xr.date_range("2020-01-01", "2020-03-10", freq="D", calendar="noleap", use_cftime=True)
ds = xr.Dataset({"a": ("time", np.arange(len(t)))}, coords={"time": t})
for a, b in [("2020-01-31", "2020-02-29"), ("2020-02-29", "2020-03-05"), ("2020-01-31", "2020-02-28")]:
    try:
        print(a, b, ds.sel(time=slice(a, b)).time.size)
    except Exception as e:
        print(a, b, "RAISED", type(e).__name__, e)
try:
    print(cftime.date2num([dt.datetime(2020,2,29,23,59,59)], units="days since 1850-01-01 00:00:00", calendar="noleap"))
except Exception as e:
    print("date2num RAISED", type(e).__name__, e)
try:
    print(cftime.date2num([dt.datetime(2020,3,1)], units="days since 1850-01-01 00:00:00", calendar="noleap"), cftime.date2num([dt.datetime(2020,2,28)], units="days since 1850-01-01 00:00:00", calendar="noleap"))
except Exception as e:
    print("date2num RAISED", type(e).__name__, e)
