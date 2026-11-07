"""Two CIME_interface objects in one process: does the second see its own CESM tree?"""
import sys
from pathlib import Path
from visualCaseGen.cime_interface import CIME_interface

roots = [Path(p).expanduser() for p in sys.argv[1:]]
for r in roots:
    ci = CIME_interface(cesmroot=r)
    import CIME
    print(f"--- cesmroot={r}")
    print("  ci.cimeroot           =", ci.cimeroot)
    print("  CIME.__file__         =", CIME.__file__)
    print("  CONFIG_CPL_FILE       =", ci._files.get_value("CONFIG_CPL_FILE"))
    print("  MACHINES_SPEC_FILE    =", ci._files.get_value("MACHINES_SPEC_FILE"))
    print("  COMPSETS_SPEC_FILE mom=", ci._files.get_value("COMPSETS_SPEC_FILE", {"component": "mom"}))
    print("  n compsets            =", len(ci.compsets))
    print("  'CR_JRA_GLOFAS' in compsets =", "CR_JRA_GLOFAS" in ci.compsets)
    print("  sys.path tail         =", sys.path[-len(roots):])
