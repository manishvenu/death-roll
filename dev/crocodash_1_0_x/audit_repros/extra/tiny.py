import sys, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="ty")
print("grid shape", grid.tlon.shape)
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="ty")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_tiny", inputdir=S/"input/audit_tiny",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True,
            job_queue="develop", job_wallclock_time="00:20:00")
x = (S/"cases/audit_tiny/env_batch.xml").read_text()
for job in ["case.run", "case.st_archive"]:
    blk = x.split(f'<job name="{job}">')[1].split("</job>")[0] if f'<job name="{job}">' in x else ""
    print(job, "QUEUE", re.findall(r'id="JOB_QUEUE"[^>]*value="([^"]*)"', blk), "WALL", re.findall(r'id="JOB_WALLCLOCK_TIME"[^>]*value="([^"]*)"', blk))
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
case.process_forcings()
ocn = S/"input/audit_tiny/ocn"
for f in sorted(ocn.glob("forcing_obc_segment_*.nc")) + [ocn/"init_tracers_filled.nc"]:
    ds = xr.open_dataset(f, decode_times=False)
    print(f.name, {k: v for k, v in ds.sizes.items()}, "allnan:", [v for v in ds.data_vars if ds[v].dtype.kind=="f" and np.isnan(ds[v].values).all()])
    ds.close()
