"""Regional lat-lon grid touching the North Pole: mesh collapse + readers."""
import numpy as np, xarray as xr
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import utils, mapping
out = Path("g4_out"); out.mkdir(exist_ok=True)
for name, g in {"np": Grid(lenx=20.0, leny=10.0, resolution=1.0, xstart=0.0, ystart=80.0, name="np"),
                "sp": Grid(lenx=20.0, leny=10.0, resolution=1.0, xstart=0.0, ystart=-90.0, name="sp")}.items():
    t = Topo(g, min_depth=10.0); t.set_flat(1000.0)
    m = out / f"{name}_mesh.nc"
    t.write_esmf_mesh(str(m))
    me = xr.open_dataset(m)
    print(name, "nodes", me.sizes["nodeCount"], "elements", me.sizes["elementCount"])
    try:
        print("  get_mesh_dimensions:", utils.get_mesh_dimensions(me), "expected", (g.nx, g.ny))
    except Exception as e:
        print("  get_mesh_dimensions ERR", type(e).__name__, e)
    try:
        print("  avg res km", utils.get_avg_resolution_km(str(m)))
        print("  suggested", mapping.get_suggested_smoothing_params(str(m)))
    except Exception as e:
        print("  avg res ERR", type(e).__name__, e)
    try:
        g2 = Grid.from_esmf_mesh(str(m))
        print("  from_esmf_mesh: tlon eq", np.allclose(g2.tlon, g.tlon), "qlat eq", np.allclose(g2.qlat, g.qlat), "tarea rel", float(np.max(np.abs(g2.tarea/g.tarea-1))))
    except Exception as e:
        print("  from_esmf_mesh ERR", type(e).__name__, e)
    bb = Grid.get_bounding_boxes(g)
    print("  ic box", bb["ic"])
    print("  north box", bb["north"])
    t.write_cice_grid(str(out / f"{name}_cice.nc"))
    t.write_scrip_grid(str(out / f"{name}_scrip.nc"))
    sc = xr.open_dataset(out / f"{name}_scrip.nc")
    sga = g.supergrid.area.reshape(g.ny, 2, g.nx, 2).sum(axis=(1, 3)).ravel() / g.supergrid._R**2
    print("  scrip area vs supergrid", float(np.max(np.abs(sc.grid_area.values / sga - 1))))
    try:
        dt = t.ww3_timesteps(1800.0); print("  ww3 dt", dt)
    except Exception as e:
        print("  ww3 ERR", e)
