"""End-to-end through CrocoDash: DROF compset, rotated (90 deg) Grid.from_center grid, no rmax/fold.
The runoff source mesh is swapped for a tiny synthetic one (monkeypatch) so the NN map is cheap."""
import sys, time, json, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
t0 = time.time()
S = Path(sys.argv[1]).resolve(); ANG = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
tag = f"audit_a6_r{int(ANG)}".replace("-", "m")
(S / "cases").mkdir(parents=True, exist_ok=True); (S / "input").mkdir(parents=True, exist_ok=True)
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

grid = Grid.from_center(40.0, -70.0, 100e3, 100e3, 5e3, angle_deg=ANG, name=tag.replace("audit_", ""))
topo = Topo(grid, min_depth=10.0)
d = np.full((grid.ny, grid.nx), 1000.0); d[:, :3] = 0.0   # land strip so there is a coastline
topo.depth = d
vgrid = VGrid.uniform(nk=10, depth=1000.0, name=tag.replace("audit_", ""))
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases" / tag, inputdir=S / "input" / tag,
            compset="1850_DATM%JRA_SLND_SICE_MOM6%REGIONAL_DROF%JRA_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="TL319",
            machine="derecho", project="ncgd0011", override=True)
print("case created", round(time.time() - t0), flush=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
cfg = json.loads((S / "input" / tag / "extract_forcings" / "config.json").read_text())
ro = cfg["runoff"]
print("config.json runoff inputs: rmax =", ro["inputs"]["rmax"], " fold =", ro["inputs"]["fold"],
      " rof_grid =", ro["inputs"]["rof_grid_name"], flush=True)
print("config.json ROF2OCN_LIQ_RMAPNAME =", ro["outputs"]["ROF2OCN_LIQ_RMAPNAME"], flush=True)

# tiny synthetic runoff source mesh around the domain (stand-in for the 1440x720 JRA025 mesh)
rg = Grid(lenx=2.0, leny=2.0, resolution=0.25, xstart=-71.0, ystart=39.0, name="tinyrof")
rt = Topo(rg, min_depth=10.0); rt.set_flat(100.0)
tiny = S / "tiny_rof_mesh.nc"; rt.write_esmf_mesh(str(tiny))
from CrocoDash.forcing.runoff import RunoffConfigurator
_orig = RunoffConfigurator.get_input_param
def _patched(self, name):
    return str(tiny) if name == "rof_esmf_mesh_filepath" else _orig(self, name)
RunoffConfigurator.get_input_param = _patched

try:
    case.process_forcings(process_ic=False, process_bc=False)
    print("process_forcings returned normally", flush=True)
except Exception as e:
    import traceback; traceback.print_exc()
    print("process_forcings raised:", type(e).__name__, e, flush=True)
print("mapping dir:", sorted(p.name for p in (S / "input" / tag / "mapping").glob("*")), flush=True)
print("elapsed", round(time.time() - t0), flush=True)
