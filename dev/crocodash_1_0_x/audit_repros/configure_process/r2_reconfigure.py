"""R2: reconfigure flows on one case (override=True vs not)."""
import sys, time, re, json
from pathlib import Path
import xarray as xr
t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).parent
override = sys.argv[1] == "override"
name = "audit_cp_2o" if override else "audit_cp_2n"
for d in (S/"cases"/name, S/"input"/name):
    if d.exists():
        import shutil; shutil.rmtree(d)
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name=name.replace("audit_", "a"))
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="v")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=override)
inp = S/"input"/name
def listing(tag):
    files = sorted(str(p.relative_to(inp)) for p in inp.rglob("*") if p.is_file() and ("extract_forcings" in str(p.relative_to(inp)) or (p.parent.name == "ocn" and ("obc" in p.name or "init_" in p.name))))
    print(f"--- {tag}:", files, flush=True)

kw = dict(product_name="reference_ocean", function_name="get_reference_ocean_data")
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"], **kw)
case.process_forcings()
listing("after first process")
raw = inp/"extract_forcings"/"raw_data"/"north_unprocessed.2020-01-01_2020-01-03.nc"
m0 = raw.stat().st_mtime if raw.exists() else None
# Re-run configure with the SAME arguments (e.g. a re-run notebook cell)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"], **kw)
listing("after identical reconfigure")
print("raw north file still there:", raw.exists(), flush=True)
case.process_forcings()
listing("after second process")
print("raw re-fetched:", raw.exists() and raw.stat().st_mtime != m0, flush=True)
