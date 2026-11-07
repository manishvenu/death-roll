"""OBC segment regrid through CrocoDash's _regrid_obc_chunk with analytic source
fields and a partially-land, variable-depth topo. Checks orientation, values,
dz, masking, time encoding."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from CrocoDash.forcing.mom6 import _regrid_obc_chunk
from CrocoDash.raw_data_access.datasets.reference import REFERENCE_OCEAN

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
grid = Grid(lenx=2.0, leny=2.0, resolution=0.25, xstart=-60.0, ystart=30.0, name="o1")
topo = Topo(grid, min_depth=10.0)
ny, nx = grid.ny, grid.nx
d = np.full((ny, nx), 1000.0)
d[:, :3] = 0.0          # west 3 columns land
d[:, 3] = 120.0         # shallow column
d[:, 4] = 400.0
topo.depth = d
topo.write_topo(out / "topo.nc")
hgrid = grid.supergrid.to_ds()
grid.write_supergrid(out / "hgrid.nc")

# source: 0.25 deg A-grid around the domain, with NaN below the "source" seafloor
lon = np.arange(-61.0, -57.0 + 1e-9, 0.25); lat = np.arange(29.0, 33.0 + 1e-9, 0.25)
depth = np.array([5., 15., 30., 60., 120., 250., 500., 900., 1500., 2500.])
time = pd.date_range("2020-01-01 12:00", periods=4, freq="D")
LON = lon[None, None, None, :]; LAT = lat[None, None, :, None]; Z = depth[None, :, None, None]
shape = (len(time), len(depth), len(lat), len(lon))
temp = np.broadcast_to(20 + 0.5 * (LON + 60) + 0.25 * (LAT - 30) - 0.005 * Z, shape).copy()
salt = np.broadcast_to(35 + 0.0 * LON + 0 * Z, shape).copy()
u = np.broadcast_to(0.1 * (LON + 60) + 0 * Z + 0 * LAT, shape).copy()
v = np.broadcast_to(0.2 * (LAT - 30) + 0 * Z + 0 * LON, shape).copy()
ssh = np.broadcast_to((0.1 * (LON + 60) + 0 * LAT)[0, 0], (len(time), len(lat), len(lon))).copy()
ds = xr.Dataset({"temp": (("time","depth","latitude","longitude"), temp),
                 "salt": (("time","depth","latitude","longitude"), salt),
                 "u": (("time","depth","latitude","longitude"), u),
                 "v": (("time","depth","latitude","longitude"), v),
                 "ssh": (("time","latitude","longitude"), ssh)},
                coords={"time": time, "depth": depth, "latitude": lat, "longitude": lon})
for vn, un in (("temp","degC"),("u","m/s"),("v","m/s"),("ssh","m")):
    ds[vn].attrs["units"] = un
ds["depth"].attrs["units"] = "m"
meta = REFERENCE_OCEAN.write_metadata()
print("calendar", meta["calendar"], "time_units", meta["time_units"])
for b, n in (("south", 1), ("west", 2), ("north", 3), ("east", 4)):
    _regrid_obc_chunk(ds, hgrid, b, n, out, meta, pd.Timestamp("2020-01-01").to_pydatetime(), None,
                      bathymetry_path=out / "topo.nc")
o = xr.open_dataset(out / "forcing_obc_segment_001.nc", decode_times=False)
print(o)
print("time", o.time.values, o.time.attrs)
print("lon along south", o.lon_segment_001.values)
print("temp surface t0", np.round(o.temp_segment_001.isel(time=0, nz_segment_001_temp=0).values.ravel(), 3))
print("expected temp", np.round(20 + 0.5*(o.lon_segment_001.values+60) + 0.25*(o.lat_segment_001.values-30) - 0.005*5, 3))
print("u surface", np.round(o.u_segment_001.isel(time=0, nz_segment_001_u=0).values.ravel(), 3))
print("v surface", np.round(o.v_segment_001.isel(time=0, nz_segment_001_v=0).values.ravel(), 3))
print("eta", np.round(o.eta_segment_001.isel(time=0).values.ravel(), 3))
dz = o.dz_temp_segment_001.isel(time=0).values.squeeze()
print("dz col sums", np.round(dz.sum(axis=0), 1))
print("dz dims", o.dz_temp_segment_001.dims, "temp dims", o.temp_segment_001.dims)
print("encodings", {k: o[k].attrs.get('_FillValue') for k in o.data_vars})
