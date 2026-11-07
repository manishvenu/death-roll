import sys, numpy as np, xarray as xr
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
g = Grid(lenx=6.0, leny=4.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a8")
t = Topo(g, min_depth=10.0)
t.set_flat(500.0)
t.edit_depth([(0, 0)], [5.0])            # one shallow cell (<= min_depth)
m = np.ones((g.ny, g.nx), int)
m[1, 1] = 0; m[2, 3] = 0                 # user says: land, although raw depth is 500 m
t.user_mask = m                          # (0,0) stays ocean in the user mask
t.land_fillval = 2.0

sl = (slice(0, 3), slice(0, 4))
sub = t[sl]
print("parent user_mask set:", t.user_mask is not None, " sliced user_mask:", sub.user_mask)
print("land_fillval parent/sliced:", t.land_fillval, sub.land_fillval)
print("parent tmask[0:3,0:4]:\n", t.tmask.values[sl])
print("sliced tmask:\n", sub.tmask.values)
print("parent masked_depth[0:3,0:4]:\n", t.masked_depth.values[sl])
print("sliced masked_depth:\n", sub.masked_depth.values)
print("ocean cells parent window / sliced:", int(t.tmask.values[sl].sum()), int(sub.tmask.values.sum()))

# what lands on disk
t.write_topo(out / "topog_parent.nc")
sub.write_topo(out / "topog_sliced.nc")
sub.write_esmf_mesh(out / "mesh_sliced.nc")
dp = xr.open_dataset(out / "topog_parent.nc")["depth"].values[sl]
ds = xr.open_dataset(out / "topog_sliced.nc")["depth"].values
print("topog depth differs at (j,i):", list(zip(*np.where(dp != ds))))
mm = xr.open_dataset(out / "mesh_sliced.nc")["elementMask"].values
print("sliced ESMF mesh elementMask:", mm.reshape(3, 4).tolist())

# monkeypatched fix
orig = Topo.__getitem__
def fixed(self, slices):
    nt = orig(self, slices)
    if self._user_mask is not None:
        nt._user_mask = self._user_mask[slices].copy()
    nt._land_fillval = self._land_fillval
    return nt
Topo.__getitem__ = fixed
sub2 = t[sl]
print("with fix: tmask equal:", bool((sub2.tmask.values == t.tmask.values[sl]).all()),
      " masked_depth equal:", bool((sub2.masked_depth.values == t.masked_depth.values[sl]).all()))
