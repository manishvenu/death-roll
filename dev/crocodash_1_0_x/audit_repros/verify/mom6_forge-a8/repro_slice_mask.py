"""Verify: Topo.__getitem__ drops the user mask and land_fillval."""

import numpy as np
import xarray as xr
import CrocoDash.topo as ct
import mom6_forge.topo as mt
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo

print("mom6_forge.topo from:", mt.__file__)
print("CrocoDash.topo.Topo is mom6_forge Topo:", Topo is mt.Topo)

grid = Grid(lenx=6.0, leny=6.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a8")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(500.0)

# A user mask: land on two cells (e.g. what naturalearth/ocean_frac/TopoEditor gives
# where the regridded depth is still positive).
mask = np.ones((grid.ny, grid.nx), dtype=int)
mask[1, 1] = 0
mask[2, 3] = 0
topo.user_mask = mask
topo.land_fillval = -5.0

js, is_ = slice(0, 4), slice(0, 5)
sub = topo[js, is_]

print("parent tmask in window:\n", topo.tmask.values[js, is_])
print("sliced tmask:\n", sub.tmask.values)
print("parent ocean cells in window:", int(topo.tmask.values[js, is_].sum()))
print("sliced ocean cells:", int(sub.tmask.values.sum()))
print("sub._user_mask is None:", sub._user_mask is None)
print("parent land_fillval:", topo.land_fillval, " sliced land_fillval:", sub.land_fillval)

# What gets written for MOM6
ds_parent = topo.gen_topo_ds()
ds_sub = sub.gen_topo_ds()
print("parent topog depth (window):\n", ds_parent["depth"].values[js, is_])
print("sliced topog depth:\n", ds_sub["depth"].values)
mvars = [v for v in ds_sub.data_vars if "mask" in v.lower()]
print("mask-like vars in topog ds:", mvars)

# fill_inland_lakes_and_channels path: lake cell becomes land via user mask
topo2 = Topo(grid, min_depth=10.0)
topo2.set_flat(500.0)
d = topo2.depth.values.copy()
d[0, :] = 0.0  # land row
d[:, 0] = 0.0  # land column
d[2, 2] = 0.0
d[2, 1] = 0.0  # 1-cell channel / lake-ish feature
topo2.depth = d
before = int(topo2.tmask.values.sum())
topo2.fill_inland_lakes_and_channels()
after = int(topo2.tmask.values.sum())
print("fill_inland: ocean cells before/after:", before, after,
      "user_mask set:", topo2._user_mask is not None)
sub2 = topo2[0:5, 0:5]
print("fill_inland parent window ocean:", int(topo2.tmask.values[0:5, 0:5].sum()),
      " sliced ocean:", int(sub2.tmask.values.sum()))

# Monkeypatched fix check
orig = mt.Topo.__getitem__


def fixed_getitem(self, slices):
    new = orig(self, slices)
    if self._user_mask is not None:
        new._user_mask = self._user_mask[slices].copy()
    new._land_fillval = self._land_fillval
    return new


mt.Topo.__getitem__ = fixed_getitem
subf = topo[js, is_]
print("FIX: sliced ocean cells:", int(subf.tmask.values.sum()),
      " equal to parent window:", bool((subf.tmask.values == topo.tmask.values[js, is_]).all()),
      " depth equal:", bool(np.allclose(subf.gen_topo_ds()["depth"].values,
                                         ds_parent["depth"].values[js, is_])))
mt.Topo.__getitem__ = orig

# Side observation: sliced _depth is a numpy view of the parent's depth
sub3 = topo[js, is_]
print("sub._depth shares memory with parent:", np.shares_memory(sub3._depth.data, topo._depth.data))
sub3.edit_depth([(0, 0)], [1234.0]) if sub3.tcm is not None else sub3.set_flat(777.0)
print("parent depth[0,0] after editing sub (expect 500):", float(topo._depth.values[0, 0]))
