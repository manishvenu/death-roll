import numpy as np, xarray as xr, xesmf
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge.mapping import regrid_dataset_via_cressman
import mom6_forge.topo as T
print("xesmf", xesmf.__version__)
HERE = Path(__file__).parent
grid = Grid(lenx=10.0, leny=10.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a7")
src = HERE / "src_a7.nc"
topo = Topo(grid, min_depth=10.0)
print("initial _depth unique:", np.unique(np.asarray(topo._depth))[:5])
m = np.zeros((grid.ny, grid.nx), int); m[:, :8] = 1
topo.user_mask = m
topo.set_src(src, "lon", "lat", "elevation", is_input_positive_below_msl=False)
print("src depth min/max:", float(topo.src.ds.depth.min()), float(topo.src.ds.depth.max()), "nan?", bool(topo.src.ds.depth.isnull().any()))
dst_ds = grid.get_esmf_ready_tracer_ds(); dst_ds["area"] = grid.tarea; dst_ds["mask"] = topo.tmask
dd, unf = regrid_dataset_via_cressman(topo.src.ds, dst_ds)
print("depth_dst row5:", np.round(dd["depth"].values[5], 1))
print("unfilled row5:", unf[5].astype(int))
orig = T.iterative_fill
def spy(depth, unfilled, mask=None, max_iter=100):
    print("spy in  row5:", np.round(depth[5], 1))
    out = orig(depth, unfilled, mask, max_iter)
    print("spy out row5:", np.round(out[5], 1)); print("spy out col7:", np.round(out[:, 7], 1))
    return out
T.iterative_fill = spy
topo.direct_cressman_interp()
print("_depth row5      :", np.round(np.asarray(topo._depth)[5], 1))
print("masked_depth row5:", np.round(topo.masked_depth.values[5], 1))
print("masked_depth col7:", np.round(topo.masked_depth.values[:, 7], 1))
