import sys, re, traceback
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(sys.argv[1])
dr = sys.argv[2:4]
name = sys.argv[4]
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a7")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a7")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("date_range =", dr, flush=True)
case.configure_forcings(date_range=dr, product_name="reference_ocean",
                        function_name="get_reference_ocean_data")
print("configure_forcings: accepted", flush=True)
txt = (S/"cases"/name/"env_run.xml").read_text()
for v in ("RUN_STARTDATE", "STOP_OPTION", "STOP_N"):
    m = re.search(r'<entry id="%s" value="([^"]*)"' % v, txt)
    print(f"env_run.xml {v} = {m.group(1) if m else None}", flush=True)
try:
    case.process_forcings()
    print("process_forcings: succeeded", flush=True)
except Exception as e:
    print("process_forcings raised:", type(e).__name__, ":", e, flush=True)
    traceback.print_exc(limit=4)
