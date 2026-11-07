"""Undoing the first mask edit leaves a frozen user mask behind."""
import shutil, numpy as np
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
lib = Path("g8_lib").resolve(); shutil.rmtree(lib, ignore_errors=True)
g = Grid(lenx=6.0, leny=5.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="um")
for git in (True, False):
    t = Topo(g, min_depth=10.0, version_control_dir=str(lib), git=git)
    t.set_flat(500.0)
    if git:
        m = np.ones((g.ny, g.nx), int); m[:, :3] = 0
        t.user_mask = m
        t.tcm.undo()                      # back to "no mask edits"
    print(f"git={git}: user_mask is None? {t.user_mask is None}")
    t.edit_depth((0, 0), [5.0])           # shallower than min_depth -> should be land
    print(f"   cell (0,0): depth {float(t.depth[0,0])}, tmask {int(t.tmask[0,0])}, written depth {float(t.masked_depth[0,0])}")
    shutil.rmtree(lib, ignore_errors=True)
