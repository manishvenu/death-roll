"""Use a Topo reloaded with from_version_control in a tiny CrocoDash Case."""
import shutil, subprocess
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
lib = S / "TopoLibraryCase"
shutil.rmtree(lib, ignore_errors=True)
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a3c")
t0 = Topo(grid, min_depth=10.0, version_control_dir=lib, git=True)
d = np.full((grid.ny, grid.nx), 1000.0); d[0, :] = 5.0
t0.depth = d
topo = Topo.from_version_control(t0.domain_dir)
print("saved min_depth", t0.min_depth, "reloaded min_depth", topo.min_depth)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a3c")
(S / "cases").mkdir(exist_ok=True); (S / "input").mkdir(exist_ok=True)
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases/audit_a3_1", inputdir=S / "input/audit_a3_1",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
for f in sorted((S / "input/audit_a3_1/ocnice").glob("topog*.nc")) + sorted((S / "input/audit_a3_1/ocn").glob("topog*.nc")):
    ds = xr.open_dataset(f)
    print(f.name, "attrs min_depth=", ds.attrs.get("min_depth"), " depth row0=", ds["depth"].values[0][:4].tolist())
    ds.close()
print(subprocess.run(["grep", "-n", "MINIMUM_DEPTH", str(S / "cases/audit_a3_1/user_nl_mom")], capture_output=True, text=True).stdout)
