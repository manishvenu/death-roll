# vcg-a5: Case() given an ocn_topo built on a different Grid than ocn_grid.
# usage: repro.py <variant>   variant = res (different resolution) | shift (same shape, moved 2 deg east)
import sys, time, traceback
from pathlib import Path
import xarray as xr, numpy as np
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

variant = sys.argv[1]
D = Path(__file__).resolve().parent
name = f"audit_vcga5_{variant}"
g = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="va5" + variant)  # 8x8
if variant == "res":
    g_old = Grid(lenx=4.0, leny=4.0, resolution=0.25, xstart=-60.0, ystart=30.0, name="va5old")  # 16x16
else:
    g_old = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-58.0, ystart=30.0, name="va5old")   # 8x8, moved
topo = Topo(g_old, min_depth=10.0)
topo.set_flat(1000.0)
vg = VGrid.uniform(nk=10, depth=1000.0, name="va5")
print("ocn_grid ny,nx =", g.ny, g.nx, " topo depth shape =", topo.depth.shape, flush=True)

case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=D / "cases" / name, inputdir=D / "input" / name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=g, ocn_topo=topo, ocn_vgrid=vg, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("Case() returned without error", flush=True)

import subprocess
q = subprocess.run(["grep", "-E", "OCN_NX|OCN_NY", str(case.caseroot / "env_build.xml")], capture_output=True, text=True).stdout
print("env_build.xml:", " | ".join(l.strip() for l in q.splitlines()))
nl = (case.caseroot / "user_nl_mom").read_text().splitlines()
print("user_nl_mom:", [l.strip() for l in nl if l.strip().startswith(("NIGLOBAL", "NJGLOBAL"))])
with xr.open_dataset(case.supergrid_path) as h:
    print("supergrid (from ocn_grid) nx,ny:", h.sizes["nx"], h.sizes["ny"], " x[1,1]=", float(h.x[1, 1]))
with xr.open_dataset(case.topo_path) as t:
    print("topo file depth dims:", dict(t.depth.sizes), " geolon[0,0]=", float(t.geolon[0, 0]) if "geolon" in t else None)
with xr.open_dataset(case.esmf_mesh_path) as m:
    print("ESMF mesh elementCount:", m.sizes["elementCount"], " first centerCoord lon=", float(m.centerCoords[0, 0]))
print("ocn_grid tlon[0,0] =", float(g.tlon[0, 0]))

case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
print("configure_forcings OK", flush=True)
try:
    case.process_forcings()
    print("process_forcings OK", flush=True)
except Exception as e:
    print("process_forcings RAISED:", type(e).__name__, str(e)[:600], flush=True)
