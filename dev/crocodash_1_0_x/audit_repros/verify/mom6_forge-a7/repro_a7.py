"""Verify mom6_forge-a7: iterative_fill donor set includes land (and still-unfilled) cells.

Pipeline: Topo.set_from_dataset(mask_method="manual", depth_method="cressman") on a 10x10 1-deg grid.
Source (0.05 deg, ratio ~21x): ocean 100 m west of lon -55, land east of it.
User mask: columns 0..7 ocean. Column 7 (lon -52.5) has no source ocean within L -> 'unfilled'.
"""
import numpy as np, xarray as xr
from pathlib import Path
import mom6_forge
from mom6_forge.utils import iterative_fill
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
import mom6_forge.topo as T
print("mom6_forge from", mom6_forge.__file__)
HERE = Path(__file__).parent

# ---- 1. unit level (land = 0): W/E ocean 100 m, N/S land
depth = np.array([[0., 0., 0.], [100., 0., 100.], [0., 0., 0.]])
mask = xr.DataArray(np.array([[0, 0, 0], [1, 1, 1], [0, 0, 0]]))
unf = np.zeros((3, 3), bool); unf[1, 1] = True
print("UNIT (land=0)   centre:", iterative_fill(depth.copy(), unf, mask)[1, 1], "(expected 100)")
depth_nan = depth.copy(); depth_nan[mask.values == 0] = np.nan; depth_nan[1, 1] = np.nan
print("UNIT (land=NaN) centre:", iterative_fill(depth_nan, unf, mask)[1, 1], "(expected 100)")

# ---- 2. public API
grid = Grid(lenx=10.0, leny=10.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a7")
lon = np.arange(-61.0, -49.0 + 1e-9, 0.05); lat = np.arange(29.0, 41.0 + 1e-9, 0.05)
elev = np.where(lon[None, :] < -55.0, -100.0, 100.0) * np.ones((lat.size, 1))
src = HERE / "src_a7.nc"
xr.Dataset({"elevation": (("lat", "lon"), elev)}, coords={"lon": lon, "lat": lat}).to_netcdf(src)

orig = T.iterative_fill
def spy(depth, unfilled, mask=None, max_iter=100):
    print("  Cressman output row 5 :", np.round(depth[5], 1))
    print("  unfilled row 5        :", unfilled[5].astype(int))
    return orig(depth, unfilled, mask, max_iter)

def finder_fix(depth, unfilled, mask=None, max_iter=100):   # filled_f = ~unfilled & mask only
    m2d = mask.values.astype(bool); un = unfilled & m2d
    for _ in range(max_iter):
        if not un.any(): break
        f = ((~un) & m2d).astype(float)
        dp = np.pad(depth, 1, mode="edge"); fp = np.pad(f, 1, mode="constant")
        dn = dp[:-2, 1:-1] + dp[2:, 1:-1] + dp[1:-1, :-2] + dp[1:-1, 2:]
        fn = fp[:-2, 1:-1] + fp[2:, 1:-1] + fp[1:-1, :-2] + fp[1:-1, 2:]
        can = un & (fn > 0); depth = np.where(can, dn / np.maximum(fn, 1), depth); un &= ~can
    return depth

def nan_safe_fix(depth, unfilled, mask=None, max_iter=100):  # donors = filled & ocean & finite; numerator masked
    m2d = mask.values.astype(bool) if mask is not None else np.ones_like(unfilled)
    un = unfilled & m2d
    for _ in range(max_iter):
        if not un.any(): break
        donor = (~un) & m2d & np.isfinite(depth)
        dp = np.pad(np.where(donor, depth, 0.0), 1); fp = np.pad(donor.astype(float), 1)
        dn = dp[:-2, 1:-1] + dp[2:, 1:-1] + dp[1:-1, :-2] + dp[1:-1, 2:]
        fn = fp[:-2, 1:-1] + fp[2:, 1:-1] + fp[1:-1, :-2] + fp[1:-1, 2:]
        can = un & (fn > 0); depth = np.where(can, dn / np.maximum(fn, 1), depth); un &= ~can
    return depth

def run(label, fill):
    T.iterative_fill = fill
    topo = Topo(grid, min_depth=10.0)
    m = np.zeros((grid.ny, grid.nx), int); m[:, :8] = 1
    topo.user_mask = m
    topo.set_from_dataset(src, "lon", "lat", "elevation", is_input_positive_below_msl=False,
                          mask_method="manual", depth_method="cressman")
    out = HERE / f"topo_{label}.nc"; topo.write_topo(out)
    ds = xr.open_dataset(out); dvar = [v for v in ds.data_vars if "depth" in v.lower()][0]
    print(f"[{label}] raw _depth   col 7:", np.round(np.asarray(topo._depth)[:, 7], 1))
    print(f"[{label}] masked_depth row 5:", np.round(topo.masked_depth.values[5], 1))
    print(f"[{label}] topo file {dvar} col 7:", np.round(ds[dvar].values[:, 7], 1))
    ds.close()

print("lon centres row 5:", np.round(np.asarray(grid.tlon)[5], 1))
run("shipped", spy)
run("finder_fix", finder_fix)
run("nan_safe_fix", nan_safe_fix)
