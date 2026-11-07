"""raw_data-a4 verify part 2: (c) OBC with dates outside archive (process_ic=False);
(d) SSH missing -> fix the archive -> rerun process_forcings on the same case."""
import sys, shutil, traceback
from pathlib import Path
import xarray as xr
sys.path.insert(0, str(Path(__file__).parent))
S = Path(__file__).parent / "run2"
shutil.rmtree(S, ignore_errors=True)
(S / "cases").mkdir(parents=True); (S / "input").mkdir(parents=True)
import importlib.util
src = (Path(__file__).parent / "v_e2e.py").read_text()
# reuse make_archive from v_e2e.py without running its scenarios
ns = {}
exec(src.split("full = make_archive")[0].replace('S = Path(__file__).parent / "run"', f'S = Path("{S}")').replace("shutil.rmtree(S, ignore_errors=True)", "").replace('(S / "cases").mkdir(parents=True); (S / "input").mkdir(parents=True)', ""), ns)
make_archive = ns["make_archive"]
full = make_archive(S / "arch_full", ["SSH", "TEMP", "SALT", "UVEL", "VVEL"])
nossh = make_archive(S / "arch_nossh", ["TEMP", "SALT", "UVEL", "VVEL"])

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a4")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a4")

def mk(tag, archive, dates):
    case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
                caseroot=S / f"cases/audit_a4v_{tag}", inputdir=S / f"input/audit_a4v_{tag}",
                compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
                ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
                machine="derecho", project="ncgd0011", override=True)
    case.configure_forcings(date_range=dates, product_name="CESM_POP_OUTPUT",
                            function_name="get_cesm_single_variable_data",
                            function_overrides={"dataset_path": str(archive)})
    return case

def go(case, label, **kw):
    print(f"--- {label}", flush=True)
    try:
        case.process_forcings(**kw); print("process_forcings returned normally")
    except Exception as e:
        print("RAISED:", type(e).__name__, ":", str(e)[:500])
        for fr in traceback.extract_tb(e.__traceback__)[-3:]:
            print("   at", fr.filename, fr.lineno, fr.name)

which = sys.argv[1]
if which == "c":
    case = mk("c", full, ["2005-01-01 00:00:00", "2005-01-03 00:00:00"])
    go(case, "(c) OBC only, dates outside the archive", process_ic=False)
    for f in sorted((S / "input/audit_a4v_c").rglob("*.nc")):
        print("  file", f.relative_to(S))
if which == "d":
    case = mk("d", nossh, ["2000-03-01 00:00:00", "2000-03-03 00:00:00"])
    go(case, "(d1) IC, SSH missing in archive", process_bc=False)
    # user fixes the archive (adds the SSH file series) and reruns
    shutil.copy(full / "g.e22.test.pop.h.SSH.200001-200012.nc", nossh)
    print("archive now holds:", sorted(p.name for p in nossh.iterdir()))
    go(case, "(d2) IC rerun after SSH added to the archive", process_bc=False)
    raw = S / "input/audit_a4v_d/extract_forcings/raw_data/ic_unprocessed.nc"
    ds = xr.open_dataset(raw, decode_times=False); print("  ic_unprocessed.nc vars:", sorted(ds.data_vars)); ds.close()
