"""IC regrid for a pole-centred Arctic grid from a GLORYS-like lat-lon source
whose last row is exactly lat=90 (GLORYS's layout)."""
import sys, traceback
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge.vgrid import VGrid
from CrocoDash.forcing.mom6 import _regrid_ic
from CrocoDash.raw_data_access.datasets.reference import REFERENCE_OCEAN

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
grid = Grid.from_projection("EPSG:3995", -200e3, 200e3, -200e3, 200e3, 40e3, name="pol")
print("grid lat range", float(grid.tlat.min()), float(grid.tlat.max()), grid.ny, grid.nx)
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
topo.write_topo(out / "topo.nc"); grid.write_supergrid(out / "hgrid.nc")
VGrid.uniform(nk=5, depth=1000.0, name="pol").write(out / "vgrid.nc")
res = 1/12
lat = np.round(np.arange(86.0, 90.0 + 1e-9, res), 6)       # ends exactly at 90.0, like GLORYS
lon = np.round(np.arange(-180.0, 180.0 - 1e-9, res), 6)
depth = np.array([5., 50., 200., 600., 1200.])
time = pd.date_range("2020-01-01 12:00", periods=1)
shape = (1, len(depth), len(lat), len(lon))
ds = xr.Dataset({"temp": (("time","depth","latitude","longitude"), np.full(shape, -1.0)),
                 "salt": (("time","depth","latitude","longitude"), np.full(shape, 34.0)),
                 "u": (("time","depth","latitude","longitude"), np.full(shape, 0.01)),
                 "v": (("time","depth","latitude","longitude"), np.full(shape, 0.0)),
                 "ssh": (("time","latitude","longitude"), np.full((1, len(lat), len(lon)), 0.1))},
                coords={"time": time, "depth": depth, "latitude": lat, "longitude": lon})
ds.to_netcdf(out / "ic_unprocessed.nc")
hgrid = xr.open_dataset(out / "hgrid.nc")
try:
    _regrid_ic(out / "ic_unprocessed.nc", hgrid, "20200101", out, REFERENCE_OCEAN.write_metadata(),
               hgrid_path=out / "hgrid.nc", vgrid_path=out / "vgrid.nc", bathymetry_path=out / "topo.nc")
    t = xr.open_dataset(out / "init_tracers.nc")
    print("IC OK; temp NaNs before fill:", int(np.isnan(t.temp.values).sum()), "of", t.temp.size)
except Exception:
    traceback.print_exc()
