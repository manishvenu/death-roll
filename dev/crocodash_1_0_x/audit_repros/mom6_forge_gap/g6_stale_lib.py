"""from_topo_file(git=True) replays an older session's history for the same grid."""
import shutil, numpy as np, subprocess, sys
from pathlib import Path
lib = Path("g6_lib").resolve()
step = sys.argv[1]
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
g = Grid(lenx=6.0, leny=5.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="st")
if step == "1":
    shutil.rmtree(lib, ignore_errors=True)
    t = Topo(g, min_depth=10.0, version_control_dir=str(lib), git=True)
    t.set_flat(500.0)
    m = np.ones((g.ny, g.nx), int); m[:, :3] = 0      # west half land
    t.user_mask = m
    print("session1 ocean cells:", int(t.tmask.sum()))
    # an unrelated, all-ocean topog file the user wants to load next time
    t2 = Topo(g, min_depth=10.0); t2.set_flat(2000.0); t2.write_topo("g6_allocean_topog.nc")
else:
    t = Topo.from_topo_file(g, "g6_allocean_topog.nc", min_depth=10.0, version_control_dir=str(lib), git=True)
    print("session2 from_topo_file(all-ocean file): ocean cells", int(t.tmask.sum()), "of", g.nx*g.ny,
          "| user_mask set:", t.user_mask is not None, "| depth[0,0]", float(t.depth[0,0]))
    t3 = Topo.from_topo_file(g, "g6_allocean_topog.nc", min_depth=10.0)
    print("same call with git=False: ocean cells", int(t3.tmask.sum()))
