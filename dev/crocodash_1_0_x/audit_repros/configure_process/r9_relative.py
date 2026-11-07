"""R9: relative caseroot/inputdir."""
import os, re, json
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
os.chdir(Path(__file__).parent)
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="acp9")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="v")
try:
    case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
                caseroot="cases/audit_cp_9", inputdir="input/audit_cp_9",
                compset="1850_DATM%JRA_SLND_SICE_MOM6%REGIONAL_DROF%JRA_SGLC_SWAV",
                ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="TL319",
                machine="derecho", project="ncgd0011", override=True)
except Exception as e:
    print("CREATE RAISED", type(e).__name__, e); raise SystemExit
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
print([l.strip() for l in open("cases/audit_cp_9/user_nl_mom") if l.strip().startswith("INPUTDIR")])
for f in Path("cases/audit_cp_9").glob("env_*.xml"):
    for m in re.finditer(r'<entry id="(ROF2OCN_LIQ_RMAPNAME|OCN_DOMAIN_MESH)" value="([^"]*)"', f.read_text()):
        print(m.group(1), "=", m.group(2))
print("config caseroot:", json.load(open("input/audit_cp_9/extract_forcings/config.json"))["caseroot"])
