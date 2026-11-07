import sys, subprocess
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1]); mach = sys.argv[2]; prod = sys.argv[3]
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="nl")
topo = Topo(grid, min_depth=10.0); topo.set_flat(3000.0)
vgrid = VGrid.uniform(nk=10, depth=3000.0, name="nl")
cr = S/f"cases/audit_nl_{mach}_{prod}"
case = Case(cesmroot=Path("/glade/u/home/manishrv/work/installs/CESM_crocodash"),
            caseroot=cr, inputdir=S/f"input/audit_nl_{mach}_{prod}",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine=mach, override=True)
print("CASE CREATED; caseroot files:", sorted(p.name for p in cr.iterdir())[:40])
kw = dict(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"])
if prod != "default":
    kw["product_name"] = prod; kw["function_name"] = "get_reference_ocean_data"
case.configure_forcings(**kw)
print("CONFIGURED")
for v in ["MACHINE", "NTASKS_OCN", "NTASKS_ATM", "MAX_TASKS_PER_NODE", "MAX_MPITASKS_PER_NODE", "CIME_OUTPUT_ROOT", "DIN_LOC_ROOT", "RUNDIR", "CALENDAR", "STOP_N", "BATCH_SYSTEM"]:
    r = subprocess.run(["./xmlquery", v, "--value"], cwd=cr, capture_output=True, text=True)
    print("XML", v, "=", r.stdout.strip() or r.stderr.strip()[-200:])
print("CaseStatus:", (cr/"CaseStatus").read_text()[-600:] if (cr/"CaseStatus").exists() else None)
try:
    case.process_forcings()
    print("PROCESS DONE")
except Exception as e:
    import traceback; traceback.print_exc(); print("PROCESS EXC", type(e).__name__, str(e)[:500])
