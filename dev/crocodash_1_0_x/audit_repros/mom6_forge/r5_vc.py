"""Topo version-control replay: from_version_control after typical edits."""
import shutil
import numpy as np
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo

base = Path("r5_out").resolve()
if base.exists():
    shutil.rmtree(base)
base.mkdir()


def make(tag, clear_mask):
    lib = base / f"lib_{tag}"
    g = Grid(lenx=6.0, leny=4.0, resolution=1.0, xstart=-60.0 - len(tag), ystart=30.0, name="vc")
    t = Topo(g, min_depth=10.0, version_control_dir=str(lib), git=True)
    d = np.full((g.ny, g.nx), 500.0)
    d[0, :] = 5.0  # shallower than min_depth -> land
    t.depth = d
    t.edit_depth([(1, 1)], [123.0])
    if clear_mask:
        m = t.tmask.values.copy(); m[2, 2] = 0
        t.user_mask = m
        t.clear_user_mask()
    print(f"[{tag}] original: min_depth={t.min_depth}, ocean cells={int(t.tmask.sum())}, depth[1,1]={float(t.depth[1,1])}")
    try:
        t2 = Topo.from_version_control(t.domain_dir)
        print(f"[{tag}] reloaded: min_depth={t2.min_depth}, ocean cells={int(t2.tmask.sum())}, depth[1,1]={float(t2.depth[1,1])}")
    except Exception as e:
        print(f"[{tag}] reload FAILED: {type(e).__name__}: {e}")


make("plain", clear_mask=False)
make("clr", clear_mask=True)
