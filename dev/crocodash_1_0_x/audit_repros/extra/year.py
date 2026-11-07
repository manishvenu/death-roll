import sys, time, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1]); t0 = time.time()
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="yr")
topo = Topo(grid, min_depth=10.0); topo.set_flat(3000.0)
vgrid = VGrid.uniform(nk=10, depth=3000.0, name="yr")
case = Case(cesmroot=Path("/glade/u/home/manishrv/work/installs/CESM_crocodash"), caseroot=S/"cases/audit_year", inputdir=S/"input/audit_year",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
            atm_grid_name="T62", machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2021-01-01 00:00:00"], product_name="reference_ocean", function_name="get_reference_ocean_data")
case.process_forcings()
ocn = S/"input/audit_year/ocn"
env = (S/"cases/audit_year/env_run.xml").read_text()
print("STOP_N", re.findall(r'id="STOP_N"[^>]*value="([^"]*)"', env), "STOP_OPTION", re.findall(r'id="STOP_OPTION"[^>]*value="([^"]*)"', env))
for f in sorted(ocn.glob("forcing_obc_segment_*.nc")):
    ds = xr.open_dataset(f, decode_times=False); t = ds.time.values
    d = np.diff(t)
    print(f.name, "ntime", len(t), "first", t[0], "last", t[-1], ds.time.attrs.get("units"), "| steps", sorted(set(np.round(d, 6).tolist()))[:5], "| dupes", int((d == 0).sum()), "| monotonic", bool((d > 0).all()))
    ds.close()
print("elapsed", round(time.time() - t0, 1), "s")
