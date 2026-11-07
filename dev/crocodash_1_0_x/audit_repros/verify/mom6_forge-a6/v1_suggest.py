"""Verify mom6_forge-a6: get_suggested_smoothing_params on rotated / fine / seam / polar grids."""
import sys, warnings
from pathlib import Path
import numpy as np, xarray as xr
warnings.filterwarnings("ignore")
import mom6_forge
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import mapping
from mom6_forge.utils import get_avg_resolution_km
print("mom6_forge from", mom6_forge.__file__)
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)

def true_spacing_km(mesh_path):
    """mean great-circle distance between i- and j-neighbour centres"""
    from mom6_forge.utils import get_mesh_dimensions
    m = xr.open_dataset(mesh_path)
    nx, ny = get_mesh_dimensions(m)
    c = m["centerCoords"].values.reshape(ny, nx, 2)
    lon, lat = np.deg2rad(c[..., 0]), np.deg2rad(c[..., 1])
    def hav(lo1, la1, lo2, la2):
        a = np.sin((la2-la1)/2)**2 + np.cos(la1)*np.cos(la2)*np.sin((lo2-lo1)/2)**2
        return 2*6371.0*np.arcsin(np.sqrt(a))
    d = np.concatenate([hav(lon[:, :-1], lat[:, :-1], lon[:, 1:], lat[:, 1:]).ravel(),
                        hav(lon[:-1], lat[:-1], lon[1:], lat[1:]).ravel()])
    return d.mean()

cases = {
  "uniform_0.25deg": lambda: Grid(lenx=4.0, leny=4.0, resolution=0.25, xstart=-60.0, ystart=30.0, name="u"),
  "center_5km_rot0":   lambda: Grid.from_center(40.0, -70.0, 100e3, 100e3, 5e3, angle_deg=0, name="c0"),
  "center_5km_rot45":  lambda: Grid.from_center(40.0, -70.0, 100e3, 100e3, 5e3, angle_deg=45, name="c45"),
  "center_5km_rot90":  lambda: Grid.from_center(40.0, -70.0, 100e3, 100e3, 5e3, angle_deg=90, name="c90"),
  "center_5km_rot-90": lambda: Grid.from_center(40.0, -70.0, 100e3, 100e3, 5e3, angle_deg=-90, name="cm90"),
  "center_5km_rot180": lambda: Grid.from_center(40.0, -70.0, 100e3, 100e3, 5e3, angle_deg=180, name="c180"),
  "center_150m_rot0":  lambda: Grid.from_center(40.0, -70.0, 3e3, 3e3, 150.0, angle_deg=0, name="c150"),
  "center_5km_on_antimeridian": lambda: Grid.from_center(55.0, 180.0, 100e3, 100e3, 5e3, angle_deg=0, name="cam"),
  "polar_3995_100km_over_pole": lambda: Grid.from_projection("EPSG:3995", -1e6, 1e6, -1e6, 1e6, 100e3, name="pol"),
}
for name, mk in cases.items():
    g = mk()
    t = Topo(g, min_depth=10.0); t.set_flat(1000.0)
    p = OUT / f"mesh_{name}.nc"
    t.write_esmf_mesh(str(p))
    avg = get_avg_resolution_km(str(p))
    tru = true_spacing_km(p)
    rmax, fold = mapping.get_suggested_smoothing_params(str(p))
    try:
        sw = mapping.compute_smoothing_weights(xr.open_dataset(p), rmax=rmax, fold=fold, coastline_masking=True)
        res = f"ok nnz={sw.nnz}"
    except Exception as e:
        res = f"{type(e).__name__}: {e}"
    print(f"{name:30s} nx,ny={g.nx},{g.ny}  avg_res_km={avg:9.3f}  true_spacing_km={tru:7.3f}  suggested(rmax,fold)=({rmax},{fold})  compute_smoothing_weights -> {res}", flush=True)
