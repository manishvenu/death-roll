"""TopoCommandManager.checkout keeps the other branch's user mask."""
import shutil, numpy as np
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
lib = Path("g7_lib").resolve(); shutil.rmtree(lib, ignore_errors=True)
g = Grid(lenx=6.0, leny=5.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="br")
t = Topo(g, min_depth=10.0, version_control_dir=str(lib), git=True)
t.set_flat(500.0)
start = t.tcm.get_current_branch()
t.tcm.create_branch("plain")
m = np.ones((g.ny, g.nx), int); m[:, :3] = 0
t.user_mask = m                                  # only on the starting branch
print(f"on {start}: ocean cells", int(t.tmask.sum()))
t.tcm.checkout("plain")
print("after checkout('plain') (no mask edits in its history): ocean cells", int(t.tmask.sum()),
      "expected", g.nx * g.ny, "| user_mask still set:", t.user_mask is not None)
t.tcm.checkout(start)
print(f"back on {start}: ocean cells", int(t.tmask.sum()))
