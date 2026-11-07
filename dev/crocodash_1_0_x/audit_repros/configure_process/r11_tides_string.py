"""R3: configure-only checks on one case."""
import sys, time, re, traceback
from pathlib import Path
t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).parent
name = "audit_cp_11"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="acp11")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="v")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
cr = S/"cases"/name
def xml(var):
    for f in cr.glob("env_*.xml"):
        m = re.search(rf'<entry id="{var}" value="([^"]*)"', f.read_text())
        if m:
            return m.group(1)
def nl(pattern):
    return [l.rstrip() for l in open(cr/"user_nl_mom") if re.match(pattern, l)]
kw = dict(product_name="reference_ocean", function_name="get_reference_ocean_data")

def step(title, **args):
    print(f"\n===== {title}", flush=True)
    try:
        case.configure_forcings(**args)
        print("OK", {v: xml(v) for v in ("RUN_STARTDATE", "STOP_OPTION", "STOP_N", "START_TOD")})
        return True
    except Exception as e:
        print("RAISED", type(e).__name__, e)
        return False


step("tides as a string", date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
     tidal_constituents="M2", tpxo_elevation_filepath="/nonexistent/h.nc",
     tpxo_velocity_filepath="/nonexistent/u.nc", **kw)
print(nl(r"(OBC_)?TIDE"))
print(nl(r"OBC_SEGMENT_001_DATA"))
