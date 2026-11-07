import sys, re
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
from visualCaseGen.custom_widget_types.case_tools import xmlchange

V = Path(__file__).resolve().parent
A = V / "cases/audit_v7_src"; IA = V / "inputs/audit_v7_src"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="v7")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="v7")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(), caseroot=A, inputdir=IA,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-04 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
# user customisation 1: lower DT in place after a (hypothetical) CFL crash
p = A / "user_nl_mom"; txt = p.read_text()
assert re.search(r"^\s*DT = 1800\.0$", txt, re.M), "expected default DT line"
p.write_text(re.sub(r"^(\s*)DT = 1800\.0$", r"\1DT = 900.0", txt, count=1, flags=re.M))
# user customisation 2: shorter run
xmlchange("STOP_N", "1", caseroot=A, is_non_local=True)
print("SRC DT lines:", [l.strip() for l in open(p) if l.strip().startswith("DT")])
print("SRC replay tail:", [l for l in (A/"replay.sh").read_text().splitlines() if "STOP_N" in l])
