# Default GLORYS CLI-script flow with an inputdir whose path contains a space.
import sys, subprocess, shlex, re
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(sys.argv[1])
caseroot = S / "cases" / "audit_rda6_1"
inputdir = S / "my inputs" / "audit_rda6_1"          # space in the inputdir path
caseroot.parent.mkdir(parents=True, exist_ok=True)
inputdir.parent.mkdir(parents=True, exist_ok=True)

grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="rda6")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="rda6")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=caseroot, inputdir=inputdir,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("case created", flush=True)
# defaults: product_name="GLORYS", function_name="get_glorys_data_script_for_cli"
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"])
print("configured", flush=True)
try:
    case.process_forcings()
except Exception as e:
    print("process_forcings raised (expected, raw file not downloaded yet):", type(e).__name__, str(e)[:300], flush=True)

raw = inputdir / "extract_forcings" / "raw_data"
scripts = sorted(raw.glob("get_glorys_data*"))
print("scripts:", scripts)
script = scripts[0]
txt = script.read_text()
cmd = [l for l in txt.splitlines() if l.startswith("copernicusmarine")][-1]
print("tail of command line:", cmd[cmd.index(" -o "):])

stub = 'copernicusmarine() { shift; while [ $# -gt 0 ]; do case "$1" in -o|-f) echo "$1 = [$2]"; shift 2;; --*) shift 2;; *) echo "stray positional = [$1]"; shift;; esac; done; }'
print("--- bash word-splitting of the generated script (copernicusmarine stubbed) ---")
print(subprocess.run(["bash", "-c", stub + "; source " + shlex.quote(str(script))], capture_output=True, text=True).stdout)

print("--- real copernicusmarine 2.0.1 CLI parse of that line (network blocked via dead proxy) ---")
env = dict(**__import__("os").environ, HTTPS_PROXY="http://127.0.0.1:9", HTTP_PROXY="http://127.0.0.1:9", PATH=str(Path(sys.executable).parent) + ":" + __import__("os").environ["PATH"])
r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=env, timeout=120)
print("exit", r.returncode); print((r.stdout + r.stderr)[-800:])

print("--- same line with shlex.quote on -o / -f (proposed fix) ---")
fixed = re.sub(r" -o (.*) -f (\S+)$", lambda m: f" -o {shlex.quote(m.group(1))} -f {shlex.quote(m.group(2))}", cmd)
print(subprocess.run(["bash", "-c", stub + "; " + fixed], capture_output=True, text=True).stdout)
