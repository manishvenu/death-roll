"""Verify mom6_forge-a7: iterative_fill uses land cells (depth 0) as donors.

Part A: iterative_fill directly (own toy case).
Part B: public path Topo.set_from_dataset(depth_method="cressman", mask_method="manual")
        with a synthetic source that is a FLAT 200 m ocean west of -59.5 and land elsewhere.
        Every correct interpolation of a flat 200 m ocean must give 200 m. Anything else is
        contamination.
Part C: same as B with a monkeypatched iterative_fill that excludes land donors.
"""
from pathlib import Path
import numpy as np
import xarray as xr

import mom6_forge.utils as mu
import mom6_forge.topo as mt
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo

here = Path(__file__).resolve().parent
np.set_printoptions(precision=1, suppress=True, linewidth=150)

# ---------------- Part A ----------------
# 3x3; centre cell unfilled ocean; ocean neighbour to the west (200 m), land elsewhere.
depth = np.zeros((3, 3))
depth[1, 0] = 200.0
mask = xr.DataArray(np.array([[0, 0, 0], [1, 1, 0], [0, 0, 0]]))
unfilled = np.zeros((3, 3), bool)
unfilled[1, 1] = True
outA = mu.iterative_fill(depth.copy(), unfilled, mask)
print("PART A centre cell:", outA[1, 1], "(only ocean neighbour is 200 m; 3 land neighbours)")

# ---------------- Part B ----------------
src = here / "src_flat200.nc"
lon = np.arange(-63.0, -51.0, 0.05) + 0.025
lat = np.arange(27.0, 39.0, 0.05) + 0.025
elev = np.where(lon[None, :] < -59.5, -200.0, 50.0) * np.ones((lat.size, 1))
xr.Dataset(
    {"elevation": (("lat", "lon"), elev)}, coords={"lon": lon, "lat": lat}
).to_netcdf(src)

captured = {}
_orig_fill = mt.iterative_fill


def spy_fill(d, unf, m, *a, **k):
    captured["cressman_out"] = np.array(d, copy=True)
    captured["unfilled"] = np.array(unf, copy=True)
    return _orig_fill(d, unf, m, *a, **k)


def run(label):
    g = Grid(lenx=6.0, leny=6.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a7")
    t = Topo(g, min_depth=10.0)
    m = np.ones((g.ny, g.nx), int)
    m[:, 5] = 0  # easternmost column land; columns 0..4 ocean (coastal strip extends into source land)
    m[0, :] = 0  # southern row land
    t.user_mask = m
    t.set_from_dataset(
        src, "lon", "lat", "elevation",
        mask_method="manual", depth_method="cressman",
    )
    print(f"\n==== {label} ====")
    print("user mask (1=ocean):\n", t.tmask.values)
    print("Cressman unfilled ocean cells:\n", captured["unfilled"].astype(int))
    print("Cressman output on land cells (donor value):",
          np.unique(captured["cressman_out"][m == 0]))
    print("raw depth after fill:\n", np.asarray(t.depth))
    print("masked_depth:\n", t.masked_depth.values)
    ocean = m == 1
    print("ocean depths min/max:", float(np.asarray(t.depth)[ocean].min()),
          float(np.asarray(t.depth)[ocean].max()), "(expected exactly 200 everywhere)")
    return t


mt.iterative_fill = spy_fill
run("PART B: shipped iterative_fill")


# ---------------- Part C: proposed fix ----------------
def fixed_iterative_fill(depth, unfilled, mask=None, max_iter=100):
    if unfilled.any():
        if mask is not None:
            mask_2d = mask.values.astype(bool)
            unfilled_2d = unfilled & mask_2d
            donor_ok = mask_2d
        else:
            unfilled_2d = unfilled
            donor_ok = np.ones_like(unfilled, bool)
        for _ in range(max_iter):
            if not unfilled_2d.any():
                break
            filled_f = (~unfilled_2d & donor_ok).astype(float)
            d_pad = np.pad(depth * filled_f, 1, mode="constant", constant_values=0)
            f_pad = np.pad(filled_f, 1, mode="constant", constant_values=0)
            d_nbr = d_pad[:-2, 1:-1] + d_pad[2:, 1:-1] + d_pad[1:-1, :-2] + d_pad[1:-1, 2:]
            f_nbr = f_pad[:-2, 1:-1] + f_pad[2:, 1:-1] + f_pad[1:-1, :-2] + f_pad[1:-1, 2:]
            can_fill = unfilled_2d & (f_nbr > 0)
            depth = np.where(can_fill, d_nbr / np.maximum(f_nbr, 1), depth)
            unfilled_2d = unfilled_2d & ~can_fill
    return depth


print("\nPART C fixed fill on Part A toy:",
      fixed_iterative_fill(depth.copy(), unfilled, mask)[1, 1])
_orig_fill = fixed_iterative_fill
run("PART C: patched iterative_fill (land excluded from donors)")
