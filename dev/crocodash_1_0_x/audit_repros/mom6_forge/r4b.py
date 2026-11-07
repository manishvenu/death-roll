import numpy as np
from r4_topo_lon import srcdesc, f_elev, Grid, Topo
g = Grid(lenx=10.0, leny=5.0, resolution=0.5, xstart=-60.0, ystart=20.0, name="t")
t = Topo(g, min_depth=10.0)
try:
    t.set_from_dataset(str(srcdesc), "lon", "lat", "elevation", mask_method="dataset", depth_method="xesmf")
    ref = -f_elev(g.tlon.values, g.tlat.values)
    print("[desc] max err", np.nanmax(np.abs(t.depth.values-ref)), "src shape", t.src.depth.shape)
except Exception as e:
    print("[desc] FAILED:", type(e).__name__, str(e)[:300])
