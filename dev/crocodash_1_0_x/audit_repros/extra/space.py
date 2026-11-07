import sys, re
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="sp")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="sp")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_space", inputdir=S/"in put/audit_space",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
cr = S/"cases/audit_space"
print("NL:", [l for l in (cr/"user_nl_mom").read_text().splitlines() if "INPUTDIR" in l])
x = (cr/"env_run.xml").read_text() + (cr/"env_build.xml").read_text()
print("XML:", re.findall(r'id="(OCN_DOMAIN_MESH|MASK_MESH)" value="([^"]*)"', x))
