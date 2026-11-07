import numpy as np
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
g = Grid(lenx=6.0, leny=4.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a8b")
t = Topo(g, min_depth=10.0); t.set_flat(500.0)
sub = t[0:3, 0:4]
sub.edit_depth([(0, 0)], [123.0])
print("parent depth[0,0] after editing the SLICED topo:", float(t.depth.values[0, 0]))
print("shares memory:", np.shares_memory(sub.depth.values, t.depth.values))
