"""Monkeypatched guard: refuse a second cimeroot once CIME is imported from another."""
import sys
from pathlib import Path
from visualCaseGen import cime_interface as m

orig = m.CIME_interface._set_cimeroot
def guarded(self, cesmroot=None):
    orig(self, cesmroot)
    mod = sys.modules.get("CIME")
    if mod is not None:
        loaded = Path(mod.__file__).resolve().parent.parent
        if loaded != self.cimeroot.resolve():
            raise RuntimeError(f"CIME is already loaded from {loaded} in this Python process; "
                               f"cannot switch to {self.cimeroot}. Restart the kernel/process to use another CESM.")
m.CIME_interface._set_cimeroot = guarded

A = Path("~/work/installs/CESM_crocodash").expanduser()
B = Path("~/work/installs/CESM_wu2r05").expanduser()
m.CIME_interface(cesmroot=A); print("A ok")
m.CIME_interface(cesmroot=A); print("A again ok")
try:
    m.CIME_interface(cesmroot=B)
except RuntimeError as e:
    print("B refused:", e)
