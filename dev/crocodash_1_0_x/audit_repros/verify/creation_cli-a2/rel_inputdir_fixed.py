"""Verify: a relative inputdir is stored and written into the case as a relative path."""
import json, os, re, subprocess, sys
from pathlib import Path

V = Path(__file__).resolve().parent
WD = V / "wd"                      # cwd the user runs the notebook from
(WD / "rel").mkdir(parents=True, exist_ok=True)   # parent of inputdir must exist (known lead finding)
(V / "cases").mkdir(exist_ok=True)
os.chdir(WD)

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
import functools
_orig = Case.__init__
@functools.wraps(_orig)
def _patched(self, *, cesmroot, caseroot, inputdir, **k):
    # proposed fix: resolve the three paths before anything uses them
    return _orig(self, cesmroot=Path(cesmroot).expanduser().resolve(), caseroot=Path(caseroot).expanduser().resolve(),
                 inputdir=Path(inputdir).expanduser().resolve(), **k)
Case.__init__ = _patched

name = "audit_vca2_2"
caseroot = V / "cases" / name                # absolute
inputdir = f"rel/{name}"                     # relative to cwd

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="vca2")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="vca2")
case = Case(cesmroot=Path(os.environ["CESMROOT"]), caseroot=caseroot, inputdir=inputdir,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("CASE CREATED; case.inputdir =", repr(str(case.inputdir)))

state = json.loads((caseroot / "_crocodash_state.json").read_text())
for k in ("inputdir", "supergrid_path", "topo_path", "vgrid_path"):
    print(f"STATE {k} = {state[k]!r}")

for line in (caseroot / "user_nl_mom").read_text().splitlines():
    if line.strip().startswith("INPUTDIR"):
        print("user_nl_mom:", line.strip())

for xml in sorted(caseroot.glob("env_*.xml")):
    txt = xml.read_text()
    for var in ("OCN_DOMAIN_MESH", "MASK_MESH"):
        m = re.search(rf'<entry id="{var}" value="([^"]*)"', txt)
        if m:
            print(f"{xml.name}: {var} = {m.group(1)!r}")

case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
cfg_path = Path(inputdir) / "extract_forcings" / "config.json"
print("config.json exists (from original cwd):", cfg_path.exists())
cfg = json.loads(cfg_path.read_text())
rel = []
def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, f"{p}[{i}]")
    elif isinstance(o, str) and name in o and not o.startswith("/"):
        rel.append((p, o))
walk(cfg)
print("config.json relative path values:")
for p, o in rel:
    print("  ", p, "=", o)

# What MOM6 would see: INPUTDIR is resolved against RUNDIR at run time.
rundir = Path(os.environ.get("RUNDIR_GUESS", f"/glade/derecho/scratch/manishrv/{name}/run"))
print("INPUTDIR resolved against RUNDIR exists:", (rundir / inputdir / "ocn").exists(), rundir / inputdir / "ocn")

# The documented CLI, run from another cwd (e.g. a PBS job that starts in $HOME).
other = V / "elsewhere"
other.mkdir(exist_ok=True)
crocodash = Path(sys.executable).parent / "crocodash"
r = subprocess.run([str(crocodash), "process", "--caseroot", str(caseroot), "--ic"],
                   cwd=other, capture_output=True, text=True, timeout=300)
print("CLI from other cwd: rc =", r.returncode)
print("CLI stdout/stderr tail:\n", (r.stdout + r.stderr)[-800:])

# The documented CLI, run from inside extract_forcings/ ("Run from inside an extract_forcings/ directory").
efdir = (WD / inputdir / "extract_forcings").resolve()
r = subprocess.run([str(crocodash), "process", "--ic"], cwd=efdir, capture_output=True,
                   text=True, timeout=300)
print("CLI from extract_forcings/: rc =", r.returncode)
print("CLI stdout/stderr tail:\n", (r.stdout + r.stderr)[-1200:])
