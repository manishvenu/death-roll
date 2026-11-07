"""configure_process-a2: TidesConfigurator hard-codes TIDE_M2 and never writes TIDE_<c>."""
import re, sys
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a2")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a2")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases/audit_cp_a2_1", inputdir=S / "input/audit_cp_a2_1",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)

user_nl = Path(case.caseroot) / "user_nl_mom"
for consts in (["K1", "O1"], ["M2", "S2", "K1", "O1"]):
    case.configure_forcings(
        date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
        product_name="reference_ocean", function_name="get_reference_ocean_data",
        tpxo_elevation_filepath=str(S / "tpxo/h_dummy.nc"),
        tpxo_velocity_filepath=str(S / "tpxo/u_dummy.nc"),
        tidal_constituents=consts,
    )
    txt = user_nl.read_text()
    lines = [l for l in txt.splitlines() if re.match(r"\s*(TIDES|TIDE_[A-Z0-9]+|OBC_TIDE_\w+)\s*=", l)]
    print(f"\n=== tidal_constituents={consts} ===")
    for l in lines:
        print("   ", l)
    body = {m.group(1) for m in re.finditer(r"^\s*TIDE_(M2|S2|N2|K2|K1|O1|P1|Q1|MF|MM)\s*=\s*True", txt, re.M)}
    print("    interior (body) tide constituents MOM6 will force:", sorted(body))
    print("    OBC tide constituents:", consts)
    print("    MISMATCH" if body != set(consts) else "    consistent")
