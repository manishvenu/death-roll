import numpy as np
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
def topo_matches(ocn_grid, ocn_topo):
    tg = ocn_topo._grid
    if tg is ocn_grid:
        return True
    return (tg.ny, tg.nx) == (ocn_grid.ny, ocn_grid.nx) and np.allclose(tg.tlon, ocn_grid.tlon) and np.allclose(tg.tlat, ocn_grid.tlat)
mk = lambda r, x: Grid(lenx=4.0, leny=4.0, resolution=r, xstart=x, ystart=30.0, name="chk")
g = mk(0.5, -60.0)
for label, tg in [("same object", g), ("identical re-created grid", mk(0.5, -60.0)),
                  ("finer grid", mk(0.25, -60.0)), ("shifted grid", mk(0.5, -58.0))]:
    print(f"{label:28s} -> accepted={topo_matches(g, Topo(tg, min_depth=10.0))}")
