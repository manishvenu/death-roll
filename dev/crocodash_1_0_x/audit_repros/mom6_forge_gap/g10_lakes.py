"""fill_inland_lakes_and_channels on an enclosed-basin domain."""
import numpy as np
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
g = Grid(lenx=10.0, leny=8.0, resolution=1.0, xstart=-90.0, ystart=40.0, name="lk")
t = Topo(g, min_depth=1.0)
d = np.full((g.ny, g.nx), 100.0); d[0, :] = d[-1, :] = d[:, 0] = d[:, -1] = 0.0   # basin walled by a 1-cell land rim
t.depth = d
print("before: ocean cells", int(t.tmask.sum()))
t.fill_inland_lakes_and_channels()
print("after fill_inland_lakes_and_channels: ocean cells", int(t.tmask.sum()))
