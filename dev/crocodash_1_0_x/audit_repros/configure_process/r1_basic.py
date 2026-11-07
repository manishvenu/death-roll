"""R1: basic flow with partial boundaries, leap-day date range; inspect outputs.
Then reconfigure with a new date range and reprocess; inspect stale handling."""
import sys, time, re, subprocess
from pathlib import Path
import xarray as xr
t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).parent
name = "audit_cp_1"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="acp1")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="acp1")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("case created", time.time()-t0, flush=True)
case.configure_forcings(date_range=["2020-02-27 00:00:00", "2020-03-02 00:00:00"],
                        boundaries=["north", "east"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
print("configured", time.time()-t0, flush=True)

def xml(var):
    for f in (S/"cases"/name).glob("env_*.xml"):
        m = re.search(rf'<entry id="{var}" value="([^"]*)"', f.read_text())
        if m:
            return m.group(1)
for v in ("CALENDAR", "RUN_STARTDATE", "STOP_OPTION", "STOP_N", "START_TOD"):
    print(v, "=", xml(v))
print(open(S/"cases"/name/"user_nl_mom").read())
case.process_forcings()
print("processed", time.time()-t0, flush=True)
ocn = S/"input"/name/"ocn"
for f in sorted(ocn.glob("*.nc")):
    print(f.name)
for f in sorted(ocn.glob("forcing_obc_segment_*.nc")):
    ds = xr.open_dataset(f, decode_times=False)
    print(f.name, dict(ds.sizes), ds.time.values, ds.time.attrs)
    ds.close()
ds = xr.open_dataset(ocn/"init_tracers_filled.nc", decode_times=False)
print("init_tracers", dict(ds.sizes), ds.time.values if "time" in ds else None, ds.time.attrs if "time" in ds else None)
ds.close()
for f in sorted((S/"input"/name/"extract_forcings"/"raw_data").glob("*.nc")):
    print("raw", f.name)
