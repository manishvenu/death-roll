import sys, time, traceback
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
from CrocoDash.raw_data_access.registry import ProductRegistry

S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a7")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a7")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_rd_a7_1", inputdir=S/"input/audit_rd_a7_1",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("case created", flush=True)

DR = ["2020-01-01 00:00:00", "2020-01-05 00:00:00"]
trials = [
    ("misspelled product", dict(product_name="glorys12", function_name="get_glorys_data_from_rda")),
    ("non-forcing product gebco", dict(product_name="gebco", function_name="get_gebco_data_script")),
    ("misspelled access method", dict(product_name="GLORYS", function_name="get_glorys_data_from_rdaa")),
    ("reference_ocean, default function_name", dict(product_name="reference_ocean")),
    ("WW3 product as conditions product", dict(product_name="reference_waves", function_name="get_reference_wave_spectra")),
]
for label, kw in trials:
    print(f"\n=== {label}: {kw}")
    try:
        case.configure_forcings(date_range=DR, **kw)
        print("NO ERROR")
    except Exception as e:
        print(f"{type(e).__name__}: {e}")
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"  raised at {Path(tb.filename).name}:{tb.lineno}")

print("\nknown products:", sorted(ProductRegistry.products))
print("glorys methods:", ProductRegistry.list_access_methods("glorys"))
print("reference_waves methods:", ProductRegistry.list_access_methods("reference_waves"))

# sanity: a valid call still works afterwards
case.configure_forcings(date_range=DR, product_name="reference_ocean", function_name="get_reference_ocean_data")
print("\nvalid configure_forcings OK", flush=True)
