"""Repro: runoff nn map pulls source cells from the whole globe when the ocean
domain straddles lon 0 or lat 0 (map_overlap normalizes lon AND lat to [0,360))."""
import os, sys
import numpy as np
import xarray as xr
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import mapping

out = Path("r1_out"); out.mkdir(exist_ok=True)

# Synthetic global 2-degree runoff grid (avoid poles), all unmasked
rof = Grid(lenx=360.0, leny=160.0, resolution=2.0, xstart=0.0, ystart=-80.0, cyclic_x=True, name="rof2")
rof_mesh = out / "rof_mesh.nc"
rof.supergrid.to_esmf_mesh(str(rof_mesh), mask="all_unmasked")

def run(tag, xstart, ystart):
    g = Grid(lenx=10.0, leny=10.0, resolution=1.0, xstart=xstart, ystart=ystart, name=f"oc{tag}")
    t = Topo(g, min_depth=10.0)
    d = np.full((g.ny, g.nx), 1000.0)
    d[:, :3] = 0.0  # land strip on the west -> a coastline
    t.depth = d
    ocn_mesh = out / f"ocn_{tag}.nc"
    t.write_esmf_mesh(str(ocn_mesh))
    mapping.gen_rof_maps(str(rof_mesh), str(ocn_mesh), str(out), f"map_{tag}")
    m = xr.open_dataset(out / f"map_{tag}_nn.nc")
    cols = np.unique(m.col.values) - 1
    xc = m.xc_a.values[cols]; yc = m.yc_a.values[cols]
    print(f"[{tag}] domain lon {xstart}..{xstart+10}, lat {ystart}..{ystart+10}: "
          f"{cols.size} source cells mapped; their lon range {xc.min():.0f}..{xc.max():.0f}, "
          f"lat range {yc.min():.0f}..{yc.max():.0f}")

run("east", 5.0, 40.0)     # does not straddle 0 lon / 0 lat
run("pm", -5.0, 40.0)      # straddles the prime meridian
run("eq", 5.0, -5.0)       # straddles the equator
