"""Verify: Case() fails when the parent of caseroot/inputdir is missing (creation_cli-a1).

usage: v_parent.py fail   -> run the failing variants (no case is created)
       v_parent.py fix    -> monkeypatch the proposed fix and create a real case
"""
import os, sys, traceback
from pathlib import Path

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

D = Path(__file__).resolve().parent
CESMROOT = Path(os.environ["CESMROOT"])
COMPSET = "1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV"
(D / "cases").mkdir(exist_ok=True)
(D / "input").mkdir(exist_ok=True)
os.chdir(D)


def objs(name):
    g = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name=name)
    t = Topo(g, min_depth=10.0)
    t.set_flat(1000.0)
    v = VGrid.uniform(nk=5, depth=1000.0, name=name)
    return g, t, v


def attempt(label, caseroot, inputdir, gname):
    g, t, v = objs(gname)
    print(f"\n=== {label}: caseroot={caseroot!s} inputdir={inputdir!s}", flush=True)
    try:
        c = Case(cesmroot=CESMROOT, caseroot=caseroot, inputdir=inputdir,
                 compset=COMPSET, ocn_grid=g, ocn_topo=t, ocn_vgrid=v,
                 atm_grid_name="T62", machine="derecho", project="ncgd0011")
        print(f"RESULT {label}: OK caseroot={c.caseroot} exists={c.caseroot.exists()} "
              f"inputdir={c.inputdir} exists={c.inputdir.exists()}", flush=True)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        inner = e.__cause__
        itb = traceback.extract_tb(inner.__traceback__) if inner else []
        print(f"RESULT {label}: {type(e).__name__}: {e}", flush=True)
        if itb:
            f = itb[-1]
            print(f"   raised at {f.filename}:{f.lineno} in {f.name}", flush=True)
    for p in (caseroot, inputdir):
        print(f"   after: {p!s} exists={Path(p).expanduser().exists()} "
              f"parent exists={Path(p).expanduser().parent.exists()}", flush=True)


mode = sys.argv[1]
if mode == "fail":
    # A: inputdir parent missing (caseroot parent exists)
    attempt("A_missing_inputdir_parent",
            D / "cases" / "audit_cca1_a", D / "newin" / "sub" / "audit_cca1_a", "cca1a")
    # B: caseroot parent missing (inputdir parent exists)
    attempt("B_missing_caseroot_parent",
            D / "newcase" / "sub" / "audit_cca1_b", D / "input" / "audit_cca1_b", "cca1b")
    # C: bare relative caseroot name (cwd = D exists)
    attempt("C_relative_caseroot", "audit_cca1_c", D / "input" / "audit_cca1_c", "cca1c")
    # E: '~' caseroot whose expanded parent exists (the scratch dir under $HOME? use ~ itself)
    attempt("E_tilde_inputdir", D / "cases" / "audit_cca1_e", "~/audit_cca1_e_never_created",
            "cca1e")
elif mode == "fix":
    orig = Case._configure_case

    def patched(self, *a, **k):
        # proposed fix: normalise and create the parents before the vCG widgets see them
        self.caseroot = Path(self.caseroot).expanduser().resolve()
        self.inputdir = Path(self.inputdir).expanduser().resolve()
        self.caseroot.parent.mkdir(parents=True, exist_ok=True)
        self.inputdir.parent.mkdir(parents=True, exist_ok=True)
        return orig(self, *a, **k)

    Case._configure_case = patched
    attempt("FIX_both_parents_missing",
            D / "fixcase" / "sub" / "audit_cca1_fix", D / "fixin" / "sub" / "audit_cca1_fix",
            "cca1fix")
