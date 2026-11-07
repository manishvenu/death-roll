"""Does the swap also hit projected (from_projection) grids whose rows are not zonal?"""
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np
import xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import utils

out = Path(__file__).parent / "out3"
out.mkdir(exist_ok=True)
cases = {
    "arctic_centered": ("EPSG:3995", -500e3, 500e3, -300e3, 300e3, 50e3),
    "arctic_offset_x+": ("EPSG:3995", 1500e3, 2500e3, -300e3, 300e3, 50e3),
    "arctic_offset_x-": ("EPSG:3995", -2500e3, -1500e3, -300e3, 300e3, 50e3),
    "arctic_offset_y+": ("EPSG:3995", -500e3, 500e3, 1500e3, 2100e3, 50e3),
    "arctic_offset_y-": ("EPSG:3995", -500e3, 500e3, -2100e3, -1500e3, 50e3),
    "antarctic_offset_x+": ("EPSG:3031", 1500e3, 2500e3, -300e3, 300e3, 50e3),
    "antarctic_offset_x-": ("EPSG:3031", -2500e3, -1500e3, -300e3, 300e3, 50e3),
}
for name, (crs, x0, x1, y0, y1, r) in cases.items():
    try:
        g = Grid.from_projection(crs, x0, x1, y0, y1, r, name=name.replace("_","").replace("+","p").replace("-","m"))
        ny, nx = g.tlon.shape
        t = Topo(g, min_depth=10.0, git=False)
        t.set_flat(1000.0)
        p = out / f"{name}.nc"
        if p.exists():
            p.unlink()
        t.write_esmf_mesh(str(p))
        m = utils.get_mesh_dimensions(str(p))
        print(f"{name:22s} true (nx,ny)=({nx},{ny}) get_mesh_dimensions={m} {'SWAPPED' if m != (nx, ny) else 'ok'}")
    except Exception as e:
        print(f"{name}: {type(e).__name__}: {e}")
