"""Verify creation_cli-a6: duplicate_case replays './xmlchange VAR=VAL --non-local'
from replay.sh with '--non-local' glued onto the value."""
import os, re, sys, shlex, traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
from visualCaseGen.custom_widget_types.case_tools import xmlchange

V = Path(__file__).resolve().parent
A = V / "cases/audit_a6v_src"; IA = V / "inputs/audit_a6v_src"
B = V / "cases/audit_a6v_dup"; IB = V / "inputs/audit_a6v_dup"
CESMROOT = Path("/glade/u/home/manishrv/work/installs/CESM_crocodash")

def env_val(case, var):
    for fn in sorted(Path(case).glob("env_*.xml")):
        for e in ET.parse(fn).getroot().iter("entry"):
            if e.get("id") == var and e.get("value") is not None:
                return e.get("value")
    return None

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a6v")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="a6v")
case = Case(cesmroot=CESMROOT, caseroot=A, inputdir=IA,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("source is_non_local:", case.is_non_local, flush=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")

# A Casper user editing a derecho case: plain ./xmlchange is refused by CIME ...
try:
    xmlchange("DOUT_S", "FALSE", caseroot=A, is_non_local=False)
    print("plain xmlchange (no --non-local): OK")
except RuntimeError as e:
    print("plain xmlchange (no --non-local) refused:", str(e).strip().splitlines()[-1])
# ... so the user's own changes carry --non-local
archive = str(V / "archive_A")
xmlchange("DOUT_S_ROOT", archive, caseroot=A, is_non_local=True)
xmlchange("DOUT_S", "FALSE", caseroot=A, is_non_local=True)
print("A DOUT_S_ROOT =", env_val(A, "DOUT_S_ROOT"))
print("A DOUT_S      =", env_val(A, "DOUT_S"))
print("A replay.sh tail:", [l for l in (A / "replay.sh").read_text().splitlines() if l.strip()][-2:], flush=True)

from CrocoDash.shareable import duplicate_case
try:
    duplicate_case(A, B, IB)
    print("duplicate_case: returned normally")
except Exception as e:
    print("duplicate_case RAISED", type(e).__name__)
    print("   ", str(e).strip().splitlines()[0][:200])
    print("   ", str(e).strip().splitlines()[-1][:300])
print("B exists:", B.exists(), "| B has env_run.xml:", (B / "env_run.xml").exists(),
      "| B user_nl_mom:", (B / "user_nl_mom").exists())
print("B DOUT_S_ROOT =", repr(env_val(B, "DOUT_S_ROOT")))
print("B DOUT_S      =", repr(env_val(B, "DOUT_S")))

# Smallest-fix check: CIME-style parsing of the same replay lines
def parse(line):
    toks = shlex.split(line)[1:]
    out = {}
    for t in toks:
        if t.startswith("-") or "=" not in t:
            continue
        for kv in t.split(","):
            k, v = kv.split("=", 1)
            out[k] = v
    return out
print("shlex parse of A's last two xmlchange lines:",
      [parse(l) for l in (A / "replay.sh").read_text().splitlines() if l.startswith("./xmlchange")][-2:])
