import sys, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="ch")
print("grid shape", grid.tlon.shape)
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="ch")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_chl", inputdir=S/"input/audit_chl",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True,
            )
x = (S/"cases/audit_chl/env_batch.xml").read_text()
for job in ["case.run", "case.st_archive"]:
    blk = x.split(f'<job name="{job}">')[1].split("</job>")[0] if f'<job name="{job}">' in x else ""
    print(job, "QUEUE", re.findall(r'id="JOB_QUEUE"[^>]*value="([^"]*)"', blk), "WALL", re.findall(r'id="JOB_WALLCLOCK_TIME"[^>]*value="([^"]*)"', blk))
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data", chl_processed_filepath="/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/chl/data/SeaWIFS.L3m.MC.CHL.chlor_a.0.25deg.nc")
case.process_forcings()
ocn = S/"input/audit_chl/ocn"
for f in sorted(ocn.glob("forcing_obc_segment_*.nc")) + [ocn/"init_tracers_filled.nc"]:
    ds = xr.open_dataset(f, decode_times=False)
    print(f.name, {k: v for k, v in ds.sizes.items()}, "allnan:", [v for v in ds.data_vars if ds[v].dtype.kind=="f" and np.isnan(ds[v].values).all()])
    ds.close()
f = sorted(ocn.glob("seawifs*.nc"))
print("chl files", [x.name for x in f])
for x in f:
    ds = xr.open_dataset(x, decode_times=False)
    for v in ds.data_vars:
        a = ds[v].values
        if a.dtype.kind == "f": print(" ", v, a.shape, "nan frac", float(np.isnan(a).mean()), "min", float(np.nanmin(a)), "max", float(np.nanmax(a)), ds[v].attrs.get("units"))
    print("  time", ds["time"].values[:3] if "time" in ds else None, ds["time"].attrs if "time" in ds else None)
nl = (S/"cases/audit_chl/user_nl_mom").read_text()
print([l for l in nl.splitlines() if "CHL" in l])
