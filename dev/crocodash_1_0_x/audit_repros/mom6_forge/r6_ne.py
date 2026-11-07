import numpy as np
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
masks = {}
for xs in (-10.0, 350.0, 710.0):
    g = Grid(lenx=20.0, leny=10.0, resolution=0.5, xstart=xs, ystart=0.0, name="ne")
    t = Topo(g, min_depth=10.0)
    try:
        m = t.generate_mask_from_naturalearth(resolution="110")
        masks[xs] = m
        print(xs, "ocean cells", int(m.sum()), "of", m.size)
    except Exception as e:
        print(xs, "FAILED", type(e).__name__, str(e)[:200])
if -10.0 in masks and 350.0 in masks:
    print("same mask -10 vs 350:", np.array_equal(masks[-10.0], masks[350.0]))
