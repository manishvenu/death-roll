"""Case(cesmroot=B) after Case(cesmroot=A) in the same process.

mode "after_A": create a tiny real case against CESM_crocodash, then ask for
cases against CESM_wu2r05. mode "fresh": only the CESM_wu2r05 requests.
For the B requests, init_args_check is wrapped so that a request that passes
it prints the resolved compset long name and stops (no B case is created).
"""
import sys, time
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

mode = sys.argv[1]
S = Path(__file__).resolve().parent
A = Path("~/work/installs/CESM_crocodash").expanduser()
B = Path("~/work/installs/CESM_wu2r05").expanduser()
(S / "cases").mkdir(exist_ok=True)
(S / "input").mkdir(exist_ok=True)

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="va4")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="va4")

if mode == "after_A":
    t0 = time.time()
    ca = Case(cesmroot=A, caseroot=S / "cases/audit_va4_A", inputdir=S / "input/audit_va4_A",
              compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
              ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
              machine="derecho", project="ncgd0011", override=True)
    print(f"case A created in {time.time()-t0:.0f}s; ca.cime.cimeroot={ca.cime.cimeroot}", flush=True)

class Stop(Exception):
    pass

orig = Case.init_args_check
def wrapped(*args, **kw):
    orig(*args, **kw)
    cime = kw["cime"]
    import CIME
    print(f"   passed init_args_check; cime.cimeroot={cime.cimeroot}; CIME.__file__={CIME.__file__}")
    print(f"   compset_lname used by CrocoDash = {kw['compset_lname']}")
    raise Stop()
Case.init_args_check = staticmethod(wrapped)

for alias in ["CR_JRA_GLOFAS", "CR_JRA"]:
    print(f"== Case(cesmroot={B.name}, compset={alias!r})", flush=True)
    try:
        Case(cesmroot=B, caseroot=S / f"cases/audit_va4_B_{alias}", inputdir=S / f"input/audit_va4_B_{alias}",
             compset=alias, ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="TL319",
             machine="derecho", project="ncgd0011", override=True)
    except Stop:
        pass
    except Exception as e:
        print(f"   {type(e).__name__}: {e}")
