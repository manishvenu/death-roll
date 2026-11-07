"""R6: DATM%JRA + DROF%JRA configure: stream years and runoff xml."""
import sys, time, re
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).parent
name = "audit_cp_8"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="acp8")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="v")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset=sys.argv[1] if len(sys.argv) > 1 else "1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
cr = S/"cases"/name
def xml(var):
    for f in cr.glob("env_*.xml"):
        m = re.search(rf'<entry id="{var}" value="([^"]*)"', f.read_text())
        if m:
            return m.group(1)
case.configure_forcings(date_range=["2020-02-01 00:00:00", "2020-03-01 00:00:00"],
                        product_name="CESM_POP_OUTPUT", function_name="get_cesm_single_variable_data")
import json
c = json.load(open(S/"input"/name/"extract_forcings"/"config.json"))
print("conditions dates:", c["conditions"]["inputs"]["start_date"], c["conditions"]["inputs"]["end_date"])
for v in ("CALENDAR", "RUN_STARTDATE", "STOP_N", "DATM_MODE", "DROF_MODE", "ROF2OCN_LIQ_RMAPNAME", "ROF2OCN_ICE_RMAPNAME", "ROF_GRID", "DATM_YR_ALIGN", "DATM_YR_START", "DATM_YR_END"):
    print(v, "=", xml(v))
for f in ("user_nl_datm_streams", "user_nl_drof_streams"):
    p = cr / f
    if p.exists():
        txt = p.read_text()
        print("=====", f)
        for line in txt.splitlines():
            print(line[:300])
