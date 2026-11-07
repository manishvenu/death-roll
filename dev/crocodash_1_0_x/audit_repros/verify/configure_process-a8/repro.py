import sys, re
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="cpa8")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="cpa8")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_cpa8_1", inputdir=S/"input/audit_cpa8_1",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)

def tide_lines():
    txt = (S/"cases/audit_cpa8_1/user_nl_mom").read_text()
    return [l for l in txt.splitlines() if l.startswith("OBC_TIDE_")]

for tc in ["M2", ["M2"]]:
    print(f"\n=== configure_forcings(tidal_constituents={tc!r}) ===", flush=True)
    try:
        case.configure_forcings(
            date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
            product_name="reference_ocean", function_name="get_reference_ocean_data",
            tidal_constituents=tc,
            tpxo_elevation_filepath=str(S/"tpxo/h_tpxo_dummy.nc"),
            tpxo_velocity_filepath=str(S/"tpxo/u_tpxo_dummy.nc"),
        )
        print("configure_forcings returned without error")
    except Exception as e:
        print("RAISED:", type(e).__name__, e)
    print("tides active:", case.fcr.is_active("tides"))
    print("stored input:", repr(case.fcr["tides"].get_input_param("tidal_constituents")))
    for l in tide_lines():
        print("user_nl_mom:", l)

# What process_tides would hand regional-mom6 (it indexes TPXO with this):
from regional_mom6.regional_mom6 import convert_to_tpxo_tidal_constituents
print("\n=== process-time lookup with the stored string ===")
try:
    print(convert_to_tpxo_tidal_constituents("M2"))
except Exception as e:
    print("RAISED:", type(e).__name__, e)
