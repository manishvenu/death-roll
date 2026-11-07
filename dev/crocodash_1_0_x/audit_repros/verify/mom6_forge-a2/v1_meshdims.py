"""Verify: get_mesh_dimensions swaps nx/ny on rotated from_center grids, and what that does
to grid_from_esmf_mesh / extract_coastline_mask / Grid.from_esmf_mesh / get_avg_resolution_km."""
import os, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np
import xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import utils, mapping

out = Path(__file__).parent / "out"
out.mkdir(exist_ok=True)


def true_coast(mask2d):
    """ocean cell with a land 4-neighbour (no wrap)."""
    m = mask2d.astype(int)
    ny, nx = m.shape
    c = np.zeros_like(m)
    for j in range(ny):
        for i in range(nx):
            if not m[j, i]:
                continue
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                jj, ii = j + dj, i + di
                if 0 <= jj < ny and 0 <= ii < nx and m[jj, ii] == 0:
                    c[j, i] = 1
    return c


for angle in [0, 30, 45, 60, 90, -60, 120]:
    g = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=angle, name=f"a{angle}")
    ny, nx = g.tlon.shape
    t = Topo(g, min_depth=10.0, git=False)
    d = np.full((ny, nx), 1000.0)
    d[:, :3] = 0.0  # land on the first 3 columns (i = 0..2)
    t.depth = d
    tmask = t.tmask.data.astype(int)
    p = out / f"mesh_a{angle}.nc"
    if p.exists():
        p.unlink()
    t.write_esmf_mesh(str(p))
    mesh = xr.open_dataset(p)
    mnx, mny = utils.get_mesh_dimensions(mesh)
    hg = mapping.grid_from_esmf_mesh(mesh)
    cm = mapping.extract_coastline_mask(hg).data
    flat_cm = mapping.flatten_to_mesh(cm).reshape(ny, nx)  # back to true layout
    tc = true_coast(tmask)
    n_flag = int((flat_cm * tmask).sum())
    n_wrong = int(((flat_cm == 1) & (tc == 0) & (tmask == 1)).sum())
    n_missed = int(((flat_cm == 0) & (tc == 1)).sum())
    res_km = utils.get_avg_resolution_km(str(p))
    rt = Grid.from_esmf_mesh(str(p), name="rt")
    rt_ok = rt.tlon.shape == g.tlon.shape and np.allclose(rt.tlon.data, g.tlon.data)
    print(
        f"angle={angle:4d} true(nx,ny)=({nx},{ny}) get_mesh_dimensions=({mnx},{mny}) "
        f"grid_from_esmf_mesh shape={hg['mask'].shape} | coast flagged={n_flag} "
        f"true coast={int(tc.sum())} wrongly flagged={n_wrong} missed={n_missed} | "
        f"avg_res_km={res_km:.2f} | from_esmf_mesh shape={rt.tlon.shape} tlon matches={rt_ok}"
    )
