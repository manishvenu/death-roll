"""POP UVEL/VVEL are grid-x/grid-y components; CrocoDash hands them to rm6 as east/north.
Synthetic POP archive: ANGLE=30 deg everywhere, UVEL=100 cm/s (grid-x), VVEL=0.
True earth-relative flow: u_east = cos30 = 0.866 m/s, v_north = sin30 = 0.5 m/s.
Target: a plain lat-lon MOM6 grid (angle 0), so rm6 should write u=0.866, v=0.5."""
import sys, shutil
from datetime import datetime
from pathlib import Path
import numpy as np, xarray as xr, dask
dask.config.set(scheduler="synchronous")
sys.path.insert(0, str(Path(__file__).parent))
from mkpop import make
from CrocoDash.grid import Grid
from CrocoDash.forcing import utils
from CrocoDash.forcing.mom6 import _regrid_obc_chunk, build_forcing_request
from CrocoDash.raw_data_access.registry import ProductRegistry
ProductRegistry.load()
S = Path(sys.argv[1]); shutil.rmtree(S, ignore_errors=True); S.mkdir(parents=True)
src = make(S/"src", angle_deg=30.0)
prod = ProductRegistry.get_product("cesm_pop_output")
info = prod.write_metadata()
variables, extra = build_forcing_request(info, {"dataset_path": str(src)})
print("variables requested:", variables)
grid = Grid(lenx=2.0, leny=1.0, resolution=0.25, xstart=275.5, ystart=24.5, name="rot")
hgrid = grid.supergrid.to_ds() if hasattr(grid.supergrid, "to_ds") else grid._supergrid.to_ds()
box = Grid.get_bounding_boxes(hgrid)["south"]
fn = utils.get_data_access_function("CESM_POP_OUTPUT", "get_cesm_single_variable_data")
raw = utils.fetch_raw_chunk(fn, ["2000-03-01","2000-03-31"], box, S/"raw", "south_unprocessed.2000-03-01_2000-03-31.nc", variables, extra, name="south")
ds = xr.open_dataset(raw)
print("raw UVEL (cm/s):", float(ds.UVEL.isel(time=0, z_t=0).mean()), " raw VVEL:", float(ds.VVEL.isel(time=0, z_t=0).mean()), " ANGLE in raw file (deg):", float(np.rad2deg(ds.ANGLE).mean()))
(S/"out").mkdir()
_regrid_obc_chunk(ds, hgrid, "south", 1, S/"out", info, datetime(2000,3,1), None)
out = xr.open_dataset(S/"out"/"forcing_obc_segment_001.nc")
u = out["u_segment_001"].isel(time=0).values; v = out["v_segment_001"].isel(time=0).values
print("MOM6 OBC u (m/s): mean", np.nanmean(u).round(4), " v (m/s): mean", np.nanmean(v).round(4))
print("expected earth-relative (and grid-relative on this lat-lon grid): u=0.866 v=0.5")
