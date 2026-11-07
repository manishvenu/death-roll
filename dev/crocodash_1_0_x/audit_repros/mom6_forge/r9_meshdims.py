import numpy as np
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge.utils import get_mesh_dimensions
out = Path("r9_out"); out.mkdir(exist_ok=True)
for ang in (0.0, 30.0, 60.0, 90.0, 120.0):
    g = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=ang, name="m")
    t = Topo(g, min_depth=10.0); t.set_flat(100.0)
    p = out / f"rot{int(ang)}.nc"; t.write_esmf_mesh(str(p))
    nx, ny = get_mesh_dimensions(str(p))
    msg = ""
    try:
        g2 = Grid.from_esmf_mesh(str(p))
        msg = f"from_esmf_mesh shape {g2.tlon.shape}, tlon match {np.allclose(g2.tlon.values, g.tlon.values) if g2.tlon.shape==g.tlon.shape else False}"
    except Exception as e:
        msg = f"from_esmf_mesh FAILED {type(e).__name__}: {str(e)[:120]}"
    print(f"angle {ang:5.1f}: true (nx, ny)=({g.nx}, {g.ny}), get_mesh_dimensions={nx, ny}; {msg}")
