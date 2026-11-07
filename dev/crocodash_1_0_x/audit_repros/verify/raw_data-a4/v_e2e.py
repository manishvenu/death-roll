"""raw_data-a4 verify: CESM-POP tseries reader with (a) date window outside archive,
(b) archive missing SSH, run through Case -> configure_forcings -> process_forcings."""
import sys, shutil, traceback
from pathlib import Path
import numpy as np, xarray as xr, cftime

S = Path(__file__).parent / "run"
shutil.rmtree(S, ignore_errors=True)
(S / "cases").mkdir(parents=True); (S / "input").mkdir(parents=True)

# --- synthetic POP tseries archive covering 2000 (one var per file) ---
def make_archive(root, vars_):
    root.mkdir(parents=True, exist_ok=True)
    nlat, nlon, nz = 16, 16, 3
    lat1 = np.linspace(26, 38, nlat); lon1 = np.linspace(296, 308, nlon)   # -64..-52
    TLONG, TLAT = np.meshgrid(lon1, lat1)
    times = [cftime.DatetimeNoLeap(2000 + (m + 1) // 12, (m + 1) % 12 + 1, 1) for m in range(12)]
    z_t = np.array([500.0, 50000.0, 100000.0])
    for v in vars_:
        if v == "SSH":
            data, dims = np.full((12, nlat, nlon), 10.0), ("time", "nlat", "nlon")
        else:
            data, dims = np.full((12, nz, nlat, nlon), 5.0), ("time", "z_t", "nlat", "nlon")
        ds = xr.Dataset({v: (dims, data)},
            coords={"time": ("time", times), "z_t": ("z_t", z_t, {"units": "centimeters"}),
                    "TLAT": (("nlat", "nlon"), TLAT), "TLONG": (("nlat", "nlon"), TLONG)})
        ds.to_netcdf(root / f"g.e22.test.pop.h.{v}.200001-200012.nc")
    return root

full = make_archive(S / "arch_full", ["SSH", "TEMP", "SALT", "UVEL", "VVEL"])
nossh = make_archive(S / "arch_nossh", ["TEMP", "SALT", "UVEL", "VVEL"])

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a4")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a4")

def run(tag, archive, dates, components):
    print(f"\n===== scenario {tag}: archive={archive.name} dates={dates} =====", flush=True)
    case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
                caseroot=S / f"cases/audit_a4v_{tag}", inputdir=S / f"input/audit_a4v_{tag}",
                compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
                ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
                machine="derecho", project="ncgd0011", override=True)
    case.configure_forcings(date_range=dates, product_name="CESM_POP_OUTPUT",
                            function_name="get_cesm_single_variable_data",
                            function_overrides={"dataset_path": str(archive)})
    try:
        case.process_forcings(**components)
        print("process_forcings returned normally")
    except Exception as e:
        print("RAISED:", type(e).__name__, ":", str(e)[:600])
        tb = traceback.extract_tb(e.__traceback__)
        for fr in tb[-4:]:
            print("   at", fr.filename.replace(str(Path.cwd()), "."), fr.lineno, fr.name)
    raw = S / f"input/audit_a4v_{tag}"
    for f in sorted(raw.rglob("*unprocessed*.nc")) + sorted(raw.rglob("*_subset_*.nc")):
        ds = xr.open_dataset(f, decode_times=False)
        print("  file", f.relative_to(S), "vars:", sorted(ds.data_vars)); ds.close()

which = sys.argv[1] if len(sys.argv) > 1 else "all"
if which in ("a", "all"):
    run("a", full, ["2005-01-01 00:00:00", "2005-01-03 00:00:00"], {})
if which in ("b", "all"):
    run("b", nossh, ["2000-03-01 00:00:00", "2000-03-03 00:00:00"], {})
