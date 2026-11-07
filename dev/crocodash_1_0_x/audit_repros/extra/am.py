import sys
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1]); xs = float(sys.argv[2]); tag = sys.argv[3]
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=xs, ystart=30.0, name="am")
print("grid lon range", float(grid.tlon.min()), float(grid.tlon.max()))
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="am")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/f"cases/audit_am_{tag}", inputdir=S/f"input/audit_am_{tag}",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
case.process_forcings()
ocn = S/f"input/audit_am_{tag}/ocn"
for f in ["init_tracers.nc", "init_vel.nc", "init_eta.nc"] + [f"forcing_obc_segment_00{i}.nc" for i in range(1, 5)]:
    ds = xr.open_dataset(ocn/f, decode_times=False)
    rep = []
    for v in ds.data_vars:
        a = ds[v].values
        if a.dtype.kind == "f" and a.size:
            rep.append(f"{v}: nan={np.isnan(a).mean():.2f} min={np.nanmin(a):.3g} max={np.nanmax(a):.3g}")
    lonv = [c for c in ds.coords if "lon" in c]
    lr = [f"{c}=[{float(ds[c].min()):.2f},{float(ds[c].max()):.2f}]" for c in lonv]
    print(f, "|", "; ".join(rep[:6]), "|", " ".join(lr))
    ds.close()
