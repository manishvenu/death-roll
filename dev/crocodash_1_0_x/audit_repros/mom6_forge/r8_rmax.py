import numpy as np
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import mapping
from mom6_forge.utils import get_avg_resolution_km
out = Path("r8_out"); out.mkdir(exist_ok=True)
cases = {
  "uniform_0.25deg": Grid(lenx=4.0, leny=4.0, resolution=0.25, xstart=-60.0, ystart=30.0, name="a"),
  "center_5km_rot0": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=0.0, name="b"),
  "center_5km_rot45": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=45.0, name="c"),
  "center_5km_rot90": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=90.0, name="d"),
  "center_5km_rot180": Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=180.0, name="e"),
  "center_150m_rot0": Grid.from_center(30.0, -60.0, 3e3, 3e3, 150.0, angle_deg=0.0, name="f"),
}
for k, g in cases.items():
    t = Topo(g, min_depth=10.0); t.set_flat(100.0)
    p = out / f"{k}.nc"; t.write_esmf_mesh(str(p))
    try:
        r = mapping.get_suggested_smoothing_params(str(p))
    except Exception as e:
        r = f"{type(e).__name__}: {e}"
    print(f"{k:20s} avg_res_km={get_avg_resolution_km(str(p)):9.3f}  suggested (rmax, fold)={r}")
