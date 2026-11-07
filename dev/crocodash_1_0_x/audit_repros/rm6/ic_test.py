"""IC regrid via CrocoDash's _regrid_ic with analytic source fields: check
staggering, eta, vertical interpolation and fills."""
import sys
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge.vgrid import VGrid
from CrocoDash.forcing.mom6 import _regrid_ic
from CrocoDash.raw_data_access.datasets.reference import REFERENCE_OCEAN

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
grid = Grid(lenx=2.0, leny=2.0, resolution=0.25, xstart=-60.0, ystart=30.0, name="i1")
topo = Topo(grid, min_depth=10.0)
d = np.full((grid.ny, grid.nx), 1000.0); d[:, :3] = 0.0; d[:, 3] = 120.0
topo.depth = d
topo.write_topo(out / "topo.nc"); grid.write_supergrid(out / "hgrid.nc")
vg = VGrid.uniform(nk=10, depth=1000.0, name="i1")
vg.write(out / "vgrid.nc") if hasattr(vg, "write") else vg.write_z_file(out / "vgrid.nc")
print(xr.open_dataset(out / "vgrid.nc"))
lon = np.arange(-61.0, -57.0 + 1e-9, 0.25); lat = np.arange(29.0, 33.0 + 1e-9, 0.25)
depth = np.array([5., 15., 30., 60., 120., 250., 500., 900., 1500., 2500.])
time = pd.date_range("2020-01-01 12:00", periods=1, freq="D")
LON = lon[None, None, None, :]; LAT = lat[None, None, :, None]; Z = depth[None, :, None, None]
shape = (1, len(depth), len(lat), len(lon))
temp = np.broadcast_to(20 + 0.5*(LON+60) + 0.25*(LAT-30) - 0.005*Z, shape).copy()
u = np.broadcast_to(0.1*(LON+60) + 0*Z + 0*LAT, shape).copy()
v = np.broadcast_to(0.2*(LAT-30) + 0*Z + 0*LON, shape).copy()
# GLORYS-like NaN: land west of -59.4 everywhere, and below 300 m east of it until -59.0
landmask = (lon < -59.4)[None, None, None, :] & np.ones(shape, bool)
temp[landmask] = np.nan; u[landmask] = np.nan; v[landmask] = np.nan
ssh = (0.1*(LON+60) + 0*LAT)[0, 0][None].repeat(1, 0).copy(); ssh[0][:, lon < -59.4] = np.nan
ds = xr.Dataset({"temp": (("time","depth","latitude","longitude"), temp),
                 "salt": (("time","depth","latitude","longitude"), np.full(shape, 35.0)),
                 "u": (("time","depth","latitude","longitude"), u),
                 "v": (("time","depth","latitude","longitude"), v),
                 "ssh": (("time","latitude","longitude"), ssh)},
                coords={"time": time, "depth": depth, "latitude": lat, "longitude": lon})
for vn, un in (("temp","degC"),("u","m/s"),("v","m/s"),("ssh","m")): ds[vn].attrs["units"] = un
ds["depth"].attrs["units"] = "m"
ds.to_netcdf(out / "ic_unprocessed.nc")
meta = REFERENCE_OCEAN.write_metadata()
hgrid = xr.open_dataset(out / "hgrid.nc")
_regrid_ic(out / "ic_unprocessed.nc", hgrid, "20200101", out, meta,
           hgrid_path=out / "hgrid.nc", vgrid_path=out / "vgrid.nc", bathymetry_path=out / "topo.nc")
vel = xr.open_dataset(out / "init_vel.nc"); velf = xr.open_dataset(out / "init_vel_filled.nc")
print(vel)
print("xq", vel.xq.values[0] if vel.xq.ndim > 1 else vel.xq.values, vel.xq.attrs, vel.yh.attrs)
print("u row0 lev0", np.round(vel.u.values[0, 0], 4))
print("expected at u-points", np.round(0.1*(grid.ulon.values[0]+60), 4))
print("v col5 lev0", np.round(vel.v.values[0, :, 5], 4))
print("expected at v-points", np.round(0.2*(grid.vlat.values[:, 5]-30), 4))
eta = xr.open_dataset(out / "init_eta.nc"); print("eta row0", np.round(eta.eta_t.values[0], 4))
tr = xr.open_dataset(out / "init_tracers.nc"); print(tr)
print("temp row0 lev0", np.round(tr.temp.values[0, 0], 3))
print("expected", np.round(20 + 0.5*(grid.tlon.values[0]+60) + 0.25*(grid.tlat.values[0]-30) - 0.005*tr.zl.values[0], 3))
print("zl", tr.zl.values)
