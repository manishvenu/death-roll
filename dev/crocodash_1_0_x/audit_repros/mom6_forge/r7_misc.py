import numpy as np, xarray as xr, traceback
from mom6_forge.utils import iterative_fill
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo

# 1) iterative_fill: one unfilled ocean cell with 2 land and 2 ocean (100 m) neighbours
depth = np.array([[0., 100., 0.],
                  [0., 0., 100.],
                  [0., 0., 0.]])
mask = xr.DataArray(np.array([[0, 1, 0],
                              [0, 1, 1],
                              [0, 0, 0]]))
unfilled = np.zeros((3, 3), bool); unfilled[1, 1] = True
out = iterative_fill(depth.copy(), unfilled, mask)
print("iterative_fill: filled value", out[1, 1], "(ocean neighbours are both 100)")

# 2) Topo slicing drops the user mask
g = Grid(lenx=6.0, leny=4.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="s")
t = Topo(g, min_depth=10.0)
t.set_flat(500.0)
m = np.ones((g.ny, g.nx), int); m[1, 1] = 0; m[2, 3] = 0
t.user_mask = m
sub = t[0:3, 0:4]
print("parent ocean in [0:3,0:4]:", int(t.tmask.values[0:3, 0:4].sum()), " sliced topo ocean:", int(sub.tmask.sum()))
