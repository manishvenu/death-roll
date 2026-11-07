"""POP-like source: grid-relative UVEL=1, VVEL=0 on a grid whose x-axis is 30 deg
CCW from east (ANGLE=30deg), so the true earth velocity is (cos30, sin30).
Run it through CrocoDash's OBC regrid step with the CESM_POP_OUTPUT metadata on an
unrotated MOM6 grid and print what lands in the segment file."""
import sys
from pathlib import Path
import numpy as np, xarray as xr, cftime
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from CrocoDash.forcing.mom6 import _regrid_obc_chunk
from CrocoDash.raw_data_access.datasets.cesm_ocean_output import CESM_POP_OUTPUT

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-40.0, ystart=50.0, name="pop")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0); topo.write_topo(out / "topo.nc")
hgrid = grid.supergrid.to_ds()
nlat, nlon = 30, 30
TLONG = np.broadcast_to(np.linspace(-42, -36, nlon)[None, :], (nlat, nlon)) % 360
TLAT = np.broadcast_to(np.linspace(48, 54, nlat)[:, None], (nlat, nlon))
z_t = np.array([500., 1500., 5000., 20000., 80000.])  # cm
time = [cftime.DatetimeNoLeap(2000, 1, d, 12) for d in (1, 2)]
shp = (2, len(z_t), nlat, nlon)
ds = xr.Dataset({"UVEL": (("time","z_t","nlat","nlon"), np.full(shp, 100.0), {"units": "centimeter/s"}),
                 "VVEL": (("time","z_t","nlat","nlon"), np.zeros(shp), {"units": "centimeter/s"}),
                 "TEMP": (("time","z_t","nlat","nlon"), np.full(shp, 10.0), {"units": "degC"}),
                 "SALT": (("time","z_t","nlat","nlon"), np.full(shp, 35.0), {"units": "gram/kilogram"}),
                 "SSH": (("time","nlat","nlon"), np.zeros((2, nlat, nlon)), {"units": "centimeter"}),
                 "ANGLE": (("nlat","nlon"), np.full((nlat, nlon), np.radians(30.0)), {"units": "radians"})},
                coords={"time": time, "z_t": ("z_t", z_t, {"units": "centimeters"}), "z_t_150m": ("z_t_150m", z_t[:3], {"units": "centimeters"}),
                        "TLAT": (("nlat","nlon"), TLAT), "TLONG": (("nlat","nlon"), TLONG)})
ds.time.encoding.update({"units": "days since 1850-01-01 00:00:00", "calendar": "noleap"})
meta = CESM_POP_OUTPUT.write_metadata()
_regrid_obc_chunk(ds, hgrid, "south", 1, out, meta, "2000-01-01", None, bathymetry_path=out / "topo.nc")
o = xr.open_dataset(out / "forcing_obc_segment_001.nc", decode_times=False)
print("u at surface:", np.round(o.u_segment_001.isel(time=0, nz_segment_001_u=0).values.ravel()[1:-1], 3))
print("v at surface:", np.round(o.v_segment_001.isel(time=0, nz_segment_001_v=0).values.ravel()[1:-1], 3))
print("expected earth (and, on this unrotated MOM6 grid, model) velocity: u=0.866 v=0.5")
print("time:", o.time.values, o.time.attrs)
