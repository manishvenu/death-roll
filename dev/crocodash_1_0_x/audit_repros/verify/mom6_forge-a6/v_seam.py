"""Antimeridian-straddling domains: raw lon range in the mesh and the suggestion."""
import warnings, contextlib, io
from pathlib import Path
warnings.filterwarnings("ignore")
import xarray as xr
from mom6_forge import mapping
from mom6_forge.utils import get_avg_resolution_km
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo

OUT = Path(__file__).parent / "meshes_seam"; OUT.mkdir(exist_ok=True)
def sugg(name, g):
    t = Topo(g, min_depth=10.0, git=False); t.set_flat(1000.0)
    p = OUT / f"{name}.nc"
    with contextlib.redirect_stdout(io.StringIO()):
        t.write_esmf_mesh(str(p))
    lon = xr.open_dataset(p)["centerCoords"].values[:, 0]
    return lon.min(), lon.max(), get_avg_resolution_km(str(p)), mapping.get_suggested_smoothing_params(str(p))

cases = {
  "latlon_xstart170": Grid(lenx=20.0, leny=5.0, resolution=0.5, xstart=170.0, ystart=50.0, name="a"),
  "center_lon180": Grid.from_center(55.0, 180.0, 200e3, 200e3, 10e3, name="b"),
  "center_lon179.9": Grid.from_center(55.0, 179.9, 200e3, 200e3, 10e3, name="c"),
  "center_lon-179.9": Grid.from_center(55.0, -179.9, 200e3, 200e3, 10e3, name="d"),
  "3995_bering": Grid.from_projection("EPSG:3995", -100e3, 100e3, 1500e3, 1700e3, 10e3, name="e"),
  "3995_beaufort": Grid.from_projection("EPSG:3995", -1000e3, -800e3, 1000e3, 1200e3, 10e3, name="f"),
}
for k, g in cases.items():
    lo, hi, r, s = sugg(k, g)
    print(f"{k:18s} lon [{lo:8.2f},{hi:8.2f}] avg_res_km {r:9.3f} -> {s}")
