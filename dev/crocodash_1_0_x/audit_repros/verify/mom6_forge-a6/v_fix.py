"""Monkeypatched fix: unsigned great-circle neighbour spacing + 1 km floor."""
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, xarray as xr
from mom6_forge import mapping, utils

def avg_res_km_fixed(mesh):
    ds = xr.open_dataset(mesh)
    nx, ny = utils.get_mesh_dimensions(ds)
    c = np.deg2rad(ds["centerCoords"].values.reshape(ny, nx, 2))
    lon, lat = c[..., 0], c[..., 1]
    def gc(l1, p1, l2, p2):
        a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2
        return 2 * 6371.0 * np.arcsin(np.sqrt(a))
    dx = gc(lon[:, :-1], lat[:, :-1], lon[:, 1:], lat[:, 1:])
    dy = gc(lon[:-1], lat[:-1], lon[1:], lat[1:])
    return float(np.mean(np.concatenate([dx.ravel(), dy.ravel()])))

def area_res_km(mesh):
    ds = xr.open_dataset(mesh)
    return float(np.mean(np.sqrt(ds["elementArea"].values)) / 1e3)

orig = mapping.get_suggested_smoothing_params
mapping.get_avg_resolution_km = avg_res_km_fixed
def fixed(p):
    r, f = orig(p)
    return max(r, 1), max(f, 1)
print(f"{'mesh':28s} {'fixed_res':>9s} {'sqrt(area)':>10s} fixed (rmax,fold)")
for d in ["meshes", "meshes_sweep", "meshes_seam"]:
    for p in sorted(Path(d).glob("*.nc")):
        print(f"{d[7:]+'/'+p.stem:28s} {avg_res_km_fixed(str(p)):9.3f} {area_res_km(str(p)):10.3f} {fixed(str(p))}")
