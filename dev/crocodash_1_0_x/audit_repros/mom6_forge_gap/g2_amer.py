"""Antimeridian / rotated grids: writers + bounding boxes."""
import numpy as np, xarray as xr
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
out = Path("g2_out"); out.mkdir(exist_ok=True)
cases = {
 "us_170": Grid(lenx=20.0, leny=6.0, resolution=1.0, xstart=170.0, ystart=30.0, name="us"),
 "us_m190": Grid(lenx=20.0, leny=6.0, resolution=1.0, xstart=-190.0, ystart=30.0, name="usm"),
 "fc_180": Grid.from_center(40.0, 180.0, 1.0e6, 6e5, 1.0e5, angle_deg=30.0, name="fc"),
 "fc_m179": Grid.from_center(40.0, -179.5, 1.0e6, 6e5, 1.0e5, angle_deg=0.0, name="fcm"),
}
for k, g in cases.items():
    x = g.supergrid.x
    print(f"== {k}: x range {x.min():.2f}..{x.max():.2f}  nx,ny={g.nx},{g.ny} cyclic={g.cyclic_x}")
    bb = Grid.get_bounding_boxes(g)
    for e in ["ic", "east", "west", "north", "south"]:
        b = bb[e]
        print(f"   {e:5s} lon {b['lon_min']:8.2f}..{b['lon_max']:8.2f} lat {b['lat_min']:6.2f}..{b['lat_max']:6.2f} cross={b['crosses_antimeridian']}")
    t = Topo(g, min_depth=10.0); t.set_flat(1000.0)
    d = out / k; d.mkdir(exist_ok=True)
    g.write_supergrid(str(d / "hgrid.nc"))
    t.write_esmf_mesh(str(d / "mesh.nc"))
    t.write_scrip_grid(str(d / "scrip.nc"))
    t.write_ww3_input(str(d / "wav"), grid_alias=k.replace("_", ""))
    t.write_cice_grid(str(d / "cice.nc"))
    sc = xr.open_dataset(d / "scrip.nc")
    print("   scrip area sum / tarea sum:", float(sc.grid_area.sum() * g.supergrid._R**2 / g.tarea.sum()))
    g2 = Grid.from_supergrid(str(d / "hgrid.nc"))
    print("   reload tlon eq", np.array_equal(g2.tlon.values, g.tlon.values), "cyclic", g2.cyclic_x)
    print("   dxt min/max", float(g.dxt.min()), float(g.dxt.max()), "dyt min/max", float(g.dyt.min()), float(g.dyt.max()))
