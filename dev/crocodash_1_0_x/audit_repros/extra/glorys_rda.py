import sys
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1]); xs = float(sys.argv[2]); ys = float(sys.argv[3]); tag = sys.argv[4]
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=xs, ystart=ys, name="gl")
topo = Topo(grid, min_depth=10.0); topo.set_flat(3000.0)
vgrid = VGrid.uniform(nk=10, depth=3000.0, name="gl")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/f"cases/audit_gl_{tag}", inputdir=S/f"input/audit_gl_{tag}",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="GLORYS", function_name="get_glorys_data_from_rda")
case.process_forcings()
inp = S/f"input/audit_gl_{tag}"; ocn = inp/"ocn"
raw = xr.open_dataset(inp/"extract_forcings/raw_data/ic_unprocessed.nc")
print("raw lon", float(raw.longitude.min()), float(raw.longitude.max()), "n", raw.sizes["longitude"], "lat", float(raw.latitude.min()), float(raw.latitude.max()),
      "grid lon", float(grid.qlon.min()), float(grid.qlon.max()))
lon = raw.longitude.values; d = np.diff(lon); print("raw lon monotonic:", bool(np.all(d > 0)), "max step", float(d.max()))
raw.close()
tr = xr.open_dataset(ocn/"init_tracers.nc", decode_times=False); vel = xr.open_dataset(ocn/"init_vel.nc", decode_times=False); eta = xr.open_dataset(ocn/"init_eta.nc", decode_times=False)
T = tr["temp"].values; Sa = tr["salt"].values
print("IC temp surf", np.round(T[0].ravel()[:4], 2), "deep", np.round(T[-1].ravel()[:2], 2), "| salt", float(np.nanmin(Sa)), float(np.nanmax(Sa)),
      "| nan T", float(np.isnan(T).mean()), "| u max", float(np.nanmax(np.abs(vel["u"].values))), "| eta", float(np.nanmin(eta["eta_t"].values)), float(np.nanmax(eta["eta_t"].values)))
col = np.nanmean(T[0], axis=0); print("surface T by column", np.round(col, 2))
for i in (1, 3):
    o = xr.open_dataset(ocn/f"forcing_obc_segment_00{i}.nc", decode_times=False)
    t = o[f"temp_segment_00{i}"].values; t = np.where(np.abs(t) > 1e10, np.nan, t)
    print(f"OBC seg {i} temp range", float(np.nanmin(t)), float(np.nanmax(t)), "nan frac", float(np.isnan(t).mean())); o.close()
