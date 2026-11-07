import numpy as np, xarray as xr
from pathlib import Path
from scipy.ndimage import binary_dilation
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import mapping
out = Path("r13_out"); out.mkdir(exist_ok=True)
rof = Grid(lenx=4.0, leny=4.0, resolution=0.05, xstart=-62.0, ystart=28.0, name="rofr")
rof.supergrid.to_esmf_mesh(str(out / "rof.nc"), mask="all_unmasked")
for ang in (30.0, 60.0):
    g = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=ang, name="m")
    t = Topo(g, min_depth=10.0)
    d = np.full((g.ny, g.nx), 100.0); d[:, :5] = 0.0
    t.depth = d
    p = out / f"ocn{int(ang)}.nc"; t.write_esmf_mesh(str(p))
    mapping.gen_rof_maps(str(out / "rof.nc"), str(p), str(out), f"m{int(ang)}", rmax=10, fold=20)
    m = xr.open_dataset(out / f"m{int(ang)}_nn.nc")
    rows = np.unique(m.row.values) - 1
    land = t.tmask.values == 0
    coastal = (binary_dilation(land, structure=np.array([[0,1,0],[1,1,1],[0,1,0]])) & ~land).ravel()
    print(f"angle {ang}: nn map sends runoff to {rows.size} ocean cells; {int((~coastal[rows]).sum())} of them are not next to land")
