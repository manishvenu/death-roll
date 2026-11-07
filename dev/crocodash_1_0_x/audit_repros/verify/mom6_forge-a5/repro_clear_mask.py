"""Verify mom6_forge-a5: replaying a ClearMaskCommand raises TypeError.

Scenarios (each in its own version-control dir, tiny 5x5 grid):
  A  set user_mask, clear_user_mask(), Topo.from_version_control(domain_dir)
  B  set user_mask, clear_user_mask(), undo(), redo()
  C  set_from_dataset-style clear on a topo that never had a user mask (old_mask=None),
     then from_version_control
  D  set user_mask on branch 'b', clear, checkout main then checkout b
  F  same as A with the proposed fix monkeypatched in
"""
import shutil
import sys
import traceback
from pathlib import Path

import numpy as np
import mom6_forge
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import edit_command

print("mom6_forge from", mom6_forge.__file__)
HERE = Path(__file__).resolve().parent


def fresh(tag):
    vc = HERE / f"vc_{tag}"
    if vc.exists():
        shutil.rmtree(vc)
    grid = Grid(lenx=5.0, leny=5.0, resolution=1.0, xstart=-60.0, ystart=30.0, name=f"a5{tag}")
    topo = Topo(grid, min_depth=10.0, version_control_dir=str(vc), git=True)
    topo.set_flat(1000.0)
    return topo


def set_mask(topo):
    m = np.ones((topo._grid.ny, topo._grid.nx), dtype=int)
    m[0, 0] = 0
    topo.user_mask = m


def run(tag, fn):
    print(f"\n=== {tag} ===")
    try:
        fn()
        print(f"[{tag}] OK, no exception")
    except Exception as e:
        print(f"[{tag}] RAISED {type(e).__name__}: {e}")
        tb = traceback.extract_tb(sys.exc_info()[2])
        for fr in tb[-3:]:
            print(f"    {Path(fr.filename).name}:{fr.lineno} in {fr.name}")


def scen_A():
    t = fresh("A")
    set_mask(t)
    print("tmask[0,0] before clear:", int(t.tmask[0, 0]))
    t.clear_user_mask()
    print("clear_user_mask() committed fine; _user_mask is", t._user_mask)
    t2 = Topo.from_version_control(t.domain_dir)
    print("reloaded; _user_mask is", t2._user_mask)


def scen_B():
    t = fresh("B")
    set_mask(t)
    t.clear_user_mask()
    t.tcm.undo()
    print("after undo: _user_mask is None?", t._user_mask is None)
    t.tcm.redo()
    print("after redo: _user_mask is None?", t._user_mask is None)


def scen_C():
    t = fresh("C")
    # what set_from_dataset(mask_method="dataset") does after loading depth
    t.clear_user_mask()
    t2 = Topo.from_version_control(t.domain_dir)
    print("reloaded")


def scen_D():
    t = fresh("D")
    base = t.tcm.get_current_branch()
    t.tcm.create_branch("b")
    t.tcm.checkout("b")
    set_mask(t)
    t.clear_user_mask()
    t.tcm.checkout(base)
    print("on", base)
    t.tcm.checkout("b")
    print("back on b")


run("A from_version_control after clear", scen_A)
run("B undo then redo of clear", scen_B)
run("C clear with no prior mask, then from_version_control", scen_C)
run("D branch checkout replay", scen_D)

# Proposed fix: accept old_mask in __init__
_orig_init = edit_command.ClearMaskCommand.__init__


def _fixed_init(self, topo, old_mask=None, message="Clear Manual Mask"):
    self._topo = topo
    self.old_mask = old_mask if old_mask is not None else topo._user_mask
    self.message = message


edit_command.ClearMaskCommand.__init__ = _fixed_init


def scen_F():
    t = fresh("F")
    set_mask(t)
    t.clear_user_mask()
    t2 = Topo.from_version_control(t.domain_dir)
    print("reloaded with fix; _user_mask is", t2._user_mask, "tmask[0,0] =", int(t2.tmask[0, 0]))
    t2.tcm.undo()
    print("undo after reload: tmask[0,0] =", int(t2.tmask[0, 0]))
    t2.tcm.redo()
    print("redo after reload: _user_mask is", t2._user_mask)


run("F with fix: A + undo/redo", scen_F)
