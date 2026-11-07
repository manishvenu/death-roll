import sys, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="sb")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="sb")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_subset", inputdir=S/"input/audit_subset",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data", boundaries=["east", "south"])
case.process_forcings()
ocn = S/"input/audit_subset/ocn"
nl = (S/"cases/audit_subset/user_nl_mom").read_text()
print("NL:", [l.strip()[:90] for l in nl.splitlines() if re.match(r"\s*OBC_(NUMBER|SEGMENT_00\d =)", l)])
print("grid lon", float(grid.qlon.min()), float(grid.qlon.max()), "lat", float(grid.qlat.min()), float(grid.qlat.max()), "shape", grid.tlon.shape)
for f in sorted(ocn.glob("forcing_obc_segment_*.nc")):
    ds = xr.open_dataset(f, decode_times=False); n = f.stem[-3:]
    lo, la = ds[f"lon_segment_{n}"].values, ds[f"lat_segment_{n}"].values
    print(f.name, dict((k, v) for k, v in ds.sizes.items() if "segment" in k and not k.startswith("nz")), "lon", round(float(lo.min()), 2), round(float(lo.max()), 2), "lat", round(float(la.min()), 2), round(float(la.max()), 2)); ds.close()
