"""Polar-stereographic regional grids off the pole: sign of i/j lon/lat deltas."""
import sys, warnings
from pathlib import Path
import numpy as np, xarray as xr
warnings.filterwarnings("ignore")
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import mapping
from mom6_forge.utils import get_avg_resolution_km
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
cases = {
  # EPSG:3995, +y half of the map = around lon 180 (Chukchi/Bering side)
  "3995_chukchi_lon180_10km": lambda: Grid.from_projection("EPSG:3995", -1e5, 1e5, 1.8e6, 2.0e6, 10e3, name="chk"),
  # EPSG:3031, -y half = around lon 180 (Ross Sea)
  "3031_ross_lon180_10km":    lambda: Grid.from_projection("EPSG:3031", -1e5, 1e5, -1.4e6, -1.2e6, 10e3, name="ross"),
  # EPSG:3031, +y half = around lon 0 (Weddell side)
  "3031_lon0_10km":           lambda: Grid.from_projection("EPSG:3031", -1e5, 1e5, 1.8e6, 2.0e6, 10e3, name="wed"),
}
for name, mk in cases.items():
    g = mk()
    t = Topo(g, min_depth=10.0); t.set_flat(1000.0)
    p = OUT / f"mesh_{name}.nc"; t.write_esmf_mesh(str(p))
    m = xr.open_dataset(p); c = m["centerCoords"].values.reshape(g.ny, g.nx, 2)
    avg = get_avg_resolution_km(str(p))
    rmax, fold = mapping.get_suggested_smoothing_params(str(p))
    print(f"{name:28s} lon[0,0..2]={np.round(c[0,:3,0],2)} lat[0..2,0]={np.round(c[:3,0,1],2)} avg_res_km={avg:8.3f} suggested=({rmax},{fold})", flush=True)
