import traceback, numpy as np
import mom6_forge, CrocoDash.grid as cg
from mom6_forge.grid import Grid
from mom6_forge._supergrid import ProjectedSupergrid, SupergridBase
print("mom6_forge from", mom6_forge.__file__)
print("CrocoDash.grid.Grid is mom6_forge Grid:", cg.Grid is Grid)

def try_grid(lat, lon, w, h, res, ang):
    try:
        g = Grid.from_center(lat, lon, w, h, res, angle_deg=ang)
        return f"OK  cyclic_x={g.cyclic_x} nx={g.nx} ny={g.ny}"
    except AssertionError as e:
        return f"AssertionError: {e}"

# 1. the minimal crash
print("\n== Grid.from_center(30, -60, 100 km, 60 km, 5 km, angle_deg=90) ==")
try:
    Grid.from_center(30, -60, 100e3, 60e3, 5e3, angle_deg=90)
except AssertionError:
    traceback.print_exc(limit=-2)

# 2. why: first/last supergrid columns
sg = ProjectedSupergrid.from_center(30, -60, 100e3, 60e3, 5e3, 90)
x, y = np.asarray(sg.x), np.asarray(sg.y)
print("\ncol 0  lon %.4f..%.4f  lat %.4f..%.4f" % (x[:,0].min(), x[:,0].max(), y[:,0].min(), y[:,0].max()))
print("col -1 lon %.4f..%.4f  lat %.4f..%.4f" % (x[:,-1].min(), x[:,-1].max(), y[:,-1].min(), y[:,-1].max()))
print("max |lon0-lon-1| = %.2e deg; max |lat0-lat-1| = %.3f deg" % (np.abs(x[:,0]-x[:,-1]).max(), np.abs(y[:,0]-y[:,-1]).max()))
print("SupergridBase.is_cyclic_x ->", sg.is_cyclic_x, "; Grid.is_cyclic_x ->", Grid.is_cyclic_x(sg))
print("lenx (deg) =", float(x.max()-x.min()))

# 3. sweep
print("\n== sweep (lat, lon, w, h, res, angle) ==")
cases = [
    (30,-60,100e3,60e3,5e3,90), (30,-60,100e3,60e3,5e3,-90), (30,-60,100e3,60e3,5e3,270),
    (30,-60,100e3,60e3,5e3,89), (30,-60,100e3,60e3,5e3,89.9), (30,-60,100e3,60e3,5e3,0),
    (0,-150,100e3,100e3,5e3,90), (45,-70,200e3,100e3,10e3,90), (60,10,300e3,150e3,15e3,90),
    (-35,150,100e3,60e3,5e3,90), (30,-60,100e3,60e3,5e3,180),
]
for c in cases:
    print(c, "->", try_grid(*c))

# 4. a transposed lat/lon supergrid file (i runs north) via Grid.from_supergrid_ds
import xarray as xr
g0 = Grid(lenx=4.0, leny=2.0, resolution=0.5, xstart=300.0, ystart=20.0, name="t")
ds = g0.supergrid.to_ds() if hasattr(g0.supergrid, "to_ds") else None
dsT = ds.transpose("nxp","nyp", ...).rename({"nxp":"nyp_","nyp":"nxp_"}) if ds is not None else None
