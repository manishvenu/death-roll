"""Verify: Topo.from_version_control loses the saved min_depth."""
import shutil, sys
from pathlib import Path
import numpy as np
import xarray as xr
import mom6_forge
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo

print("mom6_forge from:", mom6_forge.__file__)
here = Path(__file__).resolve().parent
lib = here / "TopoLibrary"
shutil.rmtree(lib, ignore_errors=True)

grid = Grid(lenx=4.0, leny=3.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a3")
topo = Topo(grid, min_depth=10.0, version_control_dir=lib, git=True)
d = np.full((grid.ny, grid.nx), 500.0)
d[0, :] = 5.0  # shallower than min_depth -> land
topo.depth = d
print("ORIGINAL : min_depth=", topo.min_depth, " ocean cells=", int(topo.tmask.sum()),
      " masked_depth row0=", topo.masked_depth.values[0].tolist())
n_commits_before = len(list(topo.repo.iter_commits()))

re = Topo.from_version_control(topo.domain_dir)
print("RELOADED : min_depth=", re.min_depth, " ocean cells=", int(re.tmask.sum()),
      " masked_depth row0=", re.masked_depth.values[0].tolist())
print("raw depth equal:", bool(np.array_equal(re.depth.values, topo.depth.values)))
n_commits_after = len(list(re.repo.iter_commits()))
print("git commits before/after reload:", n_commits_before, n_commits_after)
for c in list(re.repo.iter_commits())[:3]:
    print("   ", c.message.strip()[:60])

# what MOM6 would read
out = here / "reloaded_topog.nc"
re.write_topo(out)
ds = xr.open_dataset(out)
print("written topog depth row0:", ds["depth"].values[0].tolist())
ds.close()

# reload a second time: still wrong (and more commits)
re2 = Topo.from_version_control(topo.domain_dir)
print("RELOAD#2 : min_depth=", re2.min_depth, " commits=", len(list(re2.repo.iter_commits())))

# Proposed fix: remember the replayed min_depth across the undo
from mom6_forge import topo as topo_mod
def fixed(cls, folder_path, channel_widths=None):
    folder_path = Path(folder_path)
    g = Grid.from_supergrid(folder_path / "grid.nc")
    t = Topo(g, 0.0, version_control_dir=folder_path.parent, channel_widths=channel_widths, git=True)
    t.tcm.undo()  # undo the bootstrap command first, so replay ends on the saved state
    t.tcm.reapply_changes()
    return t
Topo.from_version_control = classmethod(fixed)
re3 = Topo.from_version_control(topo.domain_dir)
print("FIX(undo-then-replay): min_depth=", re3.min_depth, " ocean cells=", int(re3.tmask.sum()))
