import sys
from pathlib import Path
import xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="rd")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="rd")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_redate", inputdir=S/"input/audit_redate",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
ocn = S/"input/audit_redate/ocn"
def show(tag):
    ds = xr.open_dataset(ocn/"forcing_obc_segment_001.nc", use_cftime=True)
    t = ds["time"].values; print(tag, "OBC time", str(t[0])[:19], "->", str(t[-1])[:19], "n", len(t)); ds.close()
    for f in ["init_tracers.nc", "init_eta.nc"]:
        d = xr.open_dataset(ocn/f, decode_times=False)
        tv = [c for c in d.coords if "time" in c]
        print("  ", f, {c: (str(d[c].values.ravel()[:1]), d[c].attrs.get("units")) for c in tv}); d.close()
    nl = (S/"cases/audit_redate/user_nl_mom").read_text()
    print("  ", [l for l in nl.splitlines() if "TIDE_REF" in l or "RESTART" in l][:2])
for dr in (["2020-01-01 00:00:00", "2020-01-05 00:00:00"], ["2020-03-10 00:00:00", "2020-03-15 00:00:00"]):
    case.configure_forcings(date_range=dr, product_name="reference_ocean", function_name="get_reference_ocean_data")
    case.process_forcings()
    show(dr[0][:10])
    import re
    x = (S/"cases/audit_redate/env_run.xml").read_text()
    print("   RUN_STARTDATE", re.findall(r'id="RUN_STARTDATE" value="([^"]+)"', x), "STOP_N", re.findall(r'id="STOP_N" value="([^"]+)"', x))
