import traceback, numpy as np
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
g = Grid(lenx=10.0, leny=5.0, resolution=0.5, xstart=-60.0, ystart=20.0, name="t")
t = Topo(g, min_depth=10.0)
try:
    t.set_from_dataset("r4_out/srcdesc.nc", "lon", "lat", "elevation", mask_method="dataset", depth_method="xesmf")
except Exception:
    traceback.print_exc()
