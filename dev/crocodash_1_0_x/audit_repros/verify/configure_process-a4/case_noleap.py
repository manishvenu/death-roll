"""configure_process-a4: a nested case from noleap MOM6 output (CESM_MOM_OUTPUT.get_mom6_output_data)
over Jan 1 - Mar 5 2020, with CrocoDash's default chunking (get 7 d, regrid 30 d).
REGRID chunk 2 is [2020-01-31, 2020-02-29]."""
import sys, time, shutil, traceback
from pathlib import Path
t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
name = "audit_cpa4_noleap"
(S / "cases").mkdir(exist_ok=True); (S / "input").mkdir(exist_ok=True)
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="cpa4")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="cpa4")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases" / name, inputdir=S / "input" / name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("case created", round(time.time() - t0), flush=True)
case.configure_forcings(
    date_range=["2020-01-01 00:00:00", "2020-03-05 00:00:00"],
    product_name="CESM_MOM_OUTPUT", function_name="get_mom6_output_data",
    function_overrides={"dataset_path": str(S / "parent"), "file_glob": "*.nc"},
)
print("configured", round(time.time() - t0), flush=True)
try:
    case.process_forcings(process_ic=False)
    print("PROCESSED OK", flush=True)
except Exception as e:
    traceback.print_exc()
    print("RAISED", type(e).__name__, e, flush=True)
reg = S / "input" / name / "extract_forcings" / "regridded_data"
raw = S / "input" / name / "extract_forcings" / "raw_data"
print("raw files:", sorted(p.name for p in raw.glob("*.nc")) if raw.exists() else None)
print("regridded files:", sorted(p.name for p in reg.rglob("forcing_obc_segment_*.nc")) if reg.exists() else None)
print("elapsed", round(time.time() - t0))
