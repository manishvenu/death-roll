"""rectilinear_cartesian cell count vs requested resolution."""
import numpy as np
from mom6_forge.grid import Grid
for lenx, leny, res in [(0.6, 0.6, 0.1), (1.2, 1.0, 0.1), (10.0, 10.0, 1.0), (2.4, 2.0, 0.2), (3.0, 3.0, 0.3), (7.0, 5.0, 0.7)]:
    g = Grid(lenx=lenx, leny=leny, resolution=res, xstart=-60.0, ystart=30.0, type="rectilinear_cartesian", name="r")
    gu = Grid(lenx=lenx, leny=leny, resolution=res, xstart=-60.0, ystart=30.0, name="u")
    dlon = float(np.diff(g.qlon.values[0]).mean())
    print(f"lenx={lenx} res={res}: rect nx={g.nx} (dlon {dlon:.4f}) | uniform nx={gu.nx}; expected nx={round(lenx/res)}; rect ny={g.ny}")
