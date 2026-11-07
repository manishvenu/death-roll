"""Topo slicing: does the sub-topo share memory with the parent?"""
import numpy as np
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
g = Grid(lenx=6.0, leny=6.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a")
t = Topo(g, min_depth=10.0)
t.set_flat(500.0)
sub = t[0:3, 0:3]
print("shares memory:", np.shares_memory(sub.depth.data, t.depth.data))
sub.set_flat(50.0)
print("parent depth[0,0] after sub.set_flat(50):", float(t.depth[0, 0]), "(expected 500)")
sub.edit_depth((1, 1), [5.0])
print("parent depth[1,1] after sub.edit_depth:", float(t.depth[1, 1]))
print("parent tmask[1,1]:", int(t.tmask[1, 1]))
