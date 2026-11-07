"""End-to-end through CrocoDash: rotated from_center grid + DROF%JRA compset -> runoff configure
(rmax/fold suggestion) and process_forcings(runoff only) -> where does runoff land?"""
import sys, time, re, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np
import xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

angle = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
S = Path(__file__).parent
name = f"audit_vma2_{int(abs(angle))}{'m' if angle < 0 else ''}"
(S / "cases").mkdir(exist_ok=True)
(S / "input").mkdir(exist_ok=True)
t0 = time.time()
grid = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=angle, name="vma2")
ny, nx = grid.tlon.shape
topo = Topo(grid, min_depth=10.0)
d = np.full((ny, nx), 1000.0)
d[:, :3] = 0.0  # land strip on columns i=0..2; the real coast is column i=3
topo.depth = d
tmask = topo.tmask.data.astype(int)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="v")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases" / name, inputdir=S / "input" / name,
            compset="1850_DATM%JRA_SLND_SICE_MOM6%REGIONAL_DROF%JRA_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="TL319",
            machine="derecho", project="ncgd0011", override=True)
print(f"case created {time.time()-t0:.0f}s", flush=True)
case.configure_forcings(date_range=["2000-01-01 00:00:00", "2000-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
cr = S / "cases" / name
def xml(var):
    for f in cr.glob("env_*.xml"):
        m = re.search(rf'<entry id="{var}" value="([^"]*)"', f.read_text())
        if m:
            return m.group(1)
print("ROF2OCN_LIQ_RMAPNAME =", xml("ROF2OCN_LIQ_RMAPNAME"), flush=True)
case.process_forcings(process_ic=False, process_bc=False)
print(f"processed {time.time()-t0:.0f}s", flush=True)

mapdir = S / "input" / name / "mapping"
for f in sorted(mapdir.glob("*.nc")):
    m = xr.open_dataset(f)
    rows = np.unique(m.row.values[m.S.values != 0] - 1)
    recv = np.zeros(ny * nx, int)
    recv[rows] = 1
    recv = recv.reshape(ny, nx)
    adj = np.zeros_like(tmask)
    adj[:, 3] = 1  # true coast (ocean cells with a land neighbour)
    print(f"{f.name}: nj_b,ni_b={m.sizes['nj_b']},{m.sizes['ni_b']} (true ny,nx={ny},{nx}); "
          f"ocean cells receiving runoff={recv.sum()}, of which next to land={int((recv*adj).sum())}; "
          f"per true column: {recv.sum(axis=0).tolist()}")
