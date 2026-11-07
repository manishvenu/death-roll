"""Version-controlled topo: edit, undo/redo, reload; compare state."""
import os, shutil, numpy as np
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
lib = Path("g5_lib"); shutil.rmtree(lib, ignore_errors=True)
g = Grid(lenx=6.0, leny=5.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="vc")
t = Topo(g, min_depth=10.0, version_control_dir=str(lib), git=True)
t.set_flat(500.0)
t.edit_depth((1, 1), [5.0])            # shallow -> land
m = t.tmask.values.copy(); m[2, 2] = 0
t.user_mask = m                        # mask edit (land at 2,2)
t.edit_depth((3, 3), [800.0])
t.tcm.undo()                           # undo the 800 edit
state = (t.depth.values.copy(), t.tmask.values.copy(), t.masked_depth.values.copy(), t.min_depth)
print("live: depth[3,3]", state[0][3,3], "tmask[1,1],[2,2]", state[1][1,1], state[1][2,2], "min_depth", state[3])
t2 = Topo.from_version_control(t.domain_dir)
print("reload: depth[3,3]", float(t2.depth[3,3]), "tmask[1,1],[2,2]", int(t2.tmask[1,1]), int(t2.tmask[2,2]), "min_depth", t2.min_depth)
print("depth equal", np.array_equal(np.nan_to_num(state[0]), np.nan_to_num(t2.depth.values)),
      "tmask equal", np.array_equal(state[1], t2.tmask.values),
      "masked_depth equal", np.allclose(state[2], t2.masked_depth.values))
# second Topo on the same grid in the same library (new session)
t3 = Topo(g, min_depth=10.0, version_control_dir=str(lib), git=True)
print("fresh Topo on same grid: depth all nan?", bool(np.isnan(t3.depth.values).all()), "has user_mask", t3.user_mask is not None)
print("can undo:", t3.tcm.undo(check_only=True))
t3.tcm.undo()
print("after undo on fresh topo: min_depth", t3.min_depth, "depth[0,0]", float(t3.depth[0,0]))
