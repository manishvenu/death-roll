"""Nesting a child inside a GREGORIAN parent MOM6 run (e.g. a CrocoDash GLORYS case):
CESM_MOM_OUTPUT declares calendar=NOLEAP whatever the parent ran."""
import sys, shutil
from datetime import datetime
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr, dask
dask.config.set(scheduler="synchronous")
from CrocoDash.grid import Grid
from CrocoDash.forcing import utils
from CrocoDash.forcing.mom6 import _regrid_obc_chunk, build_forcing_request
from CrocoDash.raw_data_access.registry import ProductRegistry
ProductRegistry.load()
S = Path(sys.argv[1]); shutil.rmtree(S, ignore_errors=True); (S/"parent").mkdir(parents=True)
# parent output: daily means, gregorian calendar, across 2020-02-29
t = pd.date_range("2020-02-27 12:00", "2020-03-02 12:00", freq="D")
xh = np.arange(270.0, 285.0, 0.5); yh = np.arange(20.0, 31.0, 0.5)
xq = xh + 0.25; yq = yh + 0.25; zl = np.array([5.0, 15.0, 30.0])
nt = len(t)
ds = xr.Dataset({
    "zos": (("time","yh","xh"), np.zeros((nt, yh.size, xh.size))),
    "thetao": (("time","z_l","yh","xh"), np.full((nt, 3, yh.size, xh.size), 15.0)),
    "so": (("time","z_l","yh","xh"), np.full((nt, 3, yh.size, xh.size), 35.0)),
    "uo": (("time","z_l","yh","xq"), np.full((nt, 3, yh.size, xq.size), 0.1)),
    "vo": (("time","z_l","yq","xh"), np.zeros((nt, 3, yq.size, xh.size))),
}, coords={"time": t, "xh": xh, "yh": yh, "xq": xq, "yq": yq, "z_l": ("z_l", zl, {"units": "meter"})})
ds.to_netcdf(S/"parent"/"parent.ocean_daily.nc", encoding={"time": {"units": "days since 0001-01-01", "calendar": "gregorian"}})
prod = ProductRegistry.get_product("cesm_mom_output")
print("product calendar:", prod.calendar)
info = prod.write_metadata()
variables, extra = build_forcing_request(info, {"dataset_path": str(S/"parent")})
grid = Grid(lenx=2.0, leny=1.0, resolution=0.25, xstart=275.5, ystart=24.5, name="nest")
hgrid = grid._supergrid.to_ds()
box = Grid.get_bounding_boxes(hgrid)["south"]
fn = utils.get_data_access_function("CESM_MOM_OUTPUT", "get_mom6_output_data")
raw = utils.fetch_raw_chunk(fn, ["2020-02-27","2020-03-02"], box, S/"raw", "south_unprocessed.2020-02-27_2020-03-02.nc", variables, extra, name="south")
rds = xr.open_dataset(raw)
print("raw times:", [str(x) for x in rds.time.values])
(S/"out").mkdir()
try:
    _regrid_obc_chunk(rds, hgrid, "south", 1, S/"out", info, datetime(2020,2,27), None)
    out = xr.open_dataset(S/"out"/"forcing_obc_segment_001.nc", decode_times=False)
    print("OBC time values:", out.time.values, out.time.attrs)
except Exception as e:
    print("OBC regrid failed:", type(e).__name__, str(e)[:300])
