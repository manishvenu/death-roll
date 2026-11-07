"""Minimal check of Case._compute_pecount + MOM_interface config_pes.xml tiers.

No create_newcase: a stub Case carries only what _compute_pecount reads, and CIME's
own Pes lookup resolves each tier to NTASKS/ROOTPE.
"""
import os, sys, math
from pathlib import Path
import numpy as np

CESMROOT = Path(os.environ["CESMROOT"])
from CrocoDash.case import Case
from visualCaseGen.cime_interface import CIME_interface


cime = CIME_interface(str(CESMROOT))
from CIME.XML.pes import Pes  # importable once CIME_interface put cime on sys.path
pes = Pes(infile=str(CESMROOT / "components/mom/cime_config/config_pes.xml"))
NYF = "1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV"
GRID = "a%T62_l%null_oi%audit_custom_r%null_g%null_w%null_z%null_m%audit_custom"

class Topo:  # only tmask is read
    def __init__(self, n_ocean):
        self.tmask = np.ones(n_ocean)

def stub(n_ocean, compset=NYF):
    c = Case.__new__(Case)
    c.cime, c.machine, c.compset_lname = cime, "derecho", compset
    c.ocn_topo = Topo(n_ocean)
    return c

def layout(pesize):
    nt, nth, root, *_ = pes.find_pes_layout(GRID, NYF, "derecho", pesize_opts=pesize)
    return nt.get("NTASKS_OCN"), root.get("ROOTPE_OCN"), nt.get("NTASKS_ATM"), nt.get("NTASKS_CPL")

print("MAX_TASKS_PER_NODE(derecho) =", stub(1)._max_tasks_per_node())
for n in [0, 1, 64, 100, 400, 21760, 21761, 65280, 65281]:
    print(f"ocean_pts={n:6d} -> pecount {stub(n)._compute_pecount()!r}")

print("\nCIME/MOM_interface layout per pecount (NTASKS_OCN, ROOTPE_OCN, NTASKS_ATM, NTASKS_CPL):")
for p in ["XS", "S", "M", "L"]:
    print(f"  --pecount {p:2s}: {layout(p)}")
print("  no --pecount   : CIME create_newcase default is 'M' ->", layout("M"))
