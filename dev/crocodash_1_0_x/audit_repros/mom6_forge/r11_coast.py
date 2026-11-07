import numpy as np, xarray as xr
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import mapping
out = Path("r11_out"); out.mkdir(exist_ok=True)
g = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=60.0, name="m")
t = Topo(g, min_depth=10.0)
d = np.full((g.ny, g.nx), 100.0); d[:, :5] = 0.0  # land in the first 5 columns
t.depth = d
p = out / "rot60.nc"; t.write_esmf_mesh(str(p))
grid = mapping.grid_from_esmf_mesh(str(p))
print("grid_from_esmf_mesh mask shape", grid["mask"].shape, "true (ny,nx)", (g.ny, g.nx))
cm_used = mapping.flatten_to_mesh(mapping.extract_coastline_mask(grid))
true_grid = xr.Dataset({"mask": (("nlat","nlon"), t.tmask.values)})
cm_true = mapping.flatten_to_mesh(mapping.extract_coastline_mask(true_grid))
ocean = t.tmask.values.ravel() == 1
print("coastline cells used:", int(cm_used.sum()), " correct (with wrap artefacts):", int(cm_true.sum()),
      " used cells that are not next to land in the real grid:", int(((cm_used==1)&(cm_true==0)&ocean).sum()))
# the honest coastline: ocean cells in column 5
print("real coast = column i=5 cells:", g.ny)
