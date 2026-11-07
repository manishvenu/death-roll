"""Verify mom6_forge map_overlap seam/equator masking (finding mom6_forge-a1).

Global 3-deg all-ocean "rof" mesh -> tiny 10x10 deg (2-deg) ocean domain whose west
2 columns are land.  Call gen_rof_maps (nn only, what CrocoDash's RunoffConfigurator
calls first) and list which source cells receive non-zero weight.
"""
import sys, os
from pathlib import Path
import numpy as np, xarray as xr
import mom6_forge
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import mapping

print("mom6_forge from:", mom6_forge.__file__)
out = Path(__file__).parent / "work"
out.mkdir(exist_ok=True)

# source: near-global 3-deg mesh, all unmasked (stand-in for the global JRA/GLOFAS rof mesh)
rg = Grid(lenx=357.0, leny=150.0, resolution=3.0, xstart=-180.0, ystart=-75.0, name="rofsyn")
rt = Topo(rg, min_depth=1.0, git=False); rt.set_flat(100.0)
rof_mesh = out / "rof_mesh.nc"
rt.write_esmf_mesh(rof_mesh)

def domain_mesh(tag, xstart, ystart):
    g = Grid(lenx=10.0, leny=10.0, resolution=2.0, xstart=xstart, ystart=ystart, name=tag)
    t = Topo(g, min_depth=1.0, git=False); t.set_flat(100.0)
    d = t.depth.data.copy(); d[:, :2] = 0.0   # west 2 columns are land -> coastline
    t.depth = d
    p = out / f"ocn_{tag}.nc"
    t.write_esmf_mesh(p)
    return p

src = xr.open_dataset(rof_mesh)
slon = src.centerCoords.values[:, 0]; slat = src.centerCoords.values[:, 1]

cases = [("east",  5.0, 40.0), ("pm", -5.0, 40.0), ("edge0", -10.0, 40.0),
         ("eq",    5.0, -5.0), ("south", 5.0, -50.0)]
for tag, x0, y0 in cases:
    ocn = domain_mesh(tag, x0, y0)
    nodes = xr.open_dataset(ocn).nodeCoords.values
    mapping.gen_rof_maps(rof_mesh_path=rof_mesh, ocn_mesh_path=ocn, output_dir=out,
                         mapping_file_prefix=f"rof_to_{tag}", rmax=None, fold=None)
    nn = xr.open_dataset(mapping.get_nn_map_filepath(f"rof_to_{tag}", out))
    cols = np.unique(nn.col.values[nn.S.values > 0] - 1)
    lo = ((slon[cols] + 180) % 360) - 180
    print(f"RESULT [{tag}] domain lon {nodes[:,0].min():.0f}..{nodes[:,0].max():.0f} "
          f"lat {nodes[:,1].min():.0f}..{nodes[:,1].max():.0f}: "
          f"{cols.size} src cells mapped; their lon {lo.min():.1f}..{lo.max():.1f}, "
          f"lat {slat[cols].min():.1f}..{slat[cols].max():.1f}", flush=True)
