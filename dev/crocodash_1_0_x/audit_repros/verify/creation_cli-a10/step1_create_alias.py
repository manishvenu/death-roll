# Process 1: create a case from a standard MARBL alias, as the gallery marbl.ipynb does.
import sys, json
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

V = Path(__file__).resolve().parent
alias, tag = sys.argv[1], sys.argv[2]
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="v10" + tag)
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="v10" + tag)
cr = V / "cases" / f"audit_v10_{tag}_orig"
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=cr, inputdir=V / "inputs" / f"audit_v10_{tag}_orig",
            compset=alias, ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
            atm_grid_name="TL319", machine="derecho", project="ncgd0011", override=True)
st = json.load(open(cr / "_crocodash_state.json"))
print("STEP1 CREATED from", alias, "| case.compset_alias =", case.compset_alias)
print("STEP1 state keys with 'compset':", {k: v for k, v in st.items() if "compset" in k})
