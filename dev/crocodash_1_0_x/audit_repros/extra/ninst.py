import sys
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="ni")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="ni")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_ninst", inputdir=S/"input/audit_ninst",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True, ninst=2)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
cr = S/"cases/audit_ninst"
for f in sorted(cr.glob("user_nl_mom*")):
    t = f.read_text()
    print(f.name, "lines:", len(t.splitlines()), "| INPUTDIR:", "INPUTDIR" in t, "| OBC_SEGMENT_001:", "OBC_SEGMENT_001" in t, "| TOPO_FILE:", "TOPO_FILE" in t)
import re
x = (cr/"env_mach_pes.xml").read_text()
print("NINST_OCN:", re.findall(r'id="NINST_OCN".*?value="(\d+)"', x, re.S)[:1], re.findall(r'<value compclass="OCN">(\d+)</value>', x)[:3])
