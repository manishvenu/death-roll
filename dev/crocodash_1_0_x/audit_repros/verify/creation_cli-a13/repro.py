import sys, time, glob, os, subprocess
# env artifact workaround (local uncommitted MOM_interface change): make param_file_reader importable
sys.path.insert(0, os.path.expanduser("~/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS"))
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
from CrocoDash.shareable import CaseBundle

S = Path(__file__).resolve().parent
OUT = Path("/glade/derecho/scratch/manishrv")
CESMROOT = Path("~/work/installs/CESM_crocodash").expanduser()
name = "audit_v_a13_1"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a13")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="a13")
if not (S/"cases"/name/"replay.sh").exists():
  case = Case(cesmroot=CESMROOT, caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
  case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
print("CIME_OUTPUT_ROOT of source case:", subprocess.run("grep -h \"id=.CIME_OUTPUT_ROOT\\|id=.EXEROOT\\|id=.RUNDIR\" env_build.xml env_run.xml", shell=True, cwd=S/"cases"/name, capture_output=True, text=True).stdout, flush=True)

before = set(glob.glob(str(OUT / "temp_case-*")))
import tempfile
print("tempfile.gettempdir():", tempfile.gettempdir(), flush=True)

# Record the TemporaryDirectory used, by wrapping tempfile.TemporaryDirectory
import CrocoDash.shareable as sh
seen = []
_orig_td = tempfile.TemporaryDirectory
class _TD(_orig_td):
    def __enter__(self):
        p = super().__enter__(); seen.append(p); return p
sh.tempfile.TemporaryDirectory = _TD

b = CaseBundle(S/"cases"/name)
info = b.identify_non_standard_case_info(CESMROOT, "derecho", "ncgd0011")
sh.tempfile.TemporaryDirectory = _orig_td
print("non_standard_case_info:", info, flush=True)

after = set(glob.glob(str(OUT / "temp_case-*")))
new = sorted(after - before)
print("TemporaryDirectory used:", seen, "exists after call:", [os.path.exists(p) for p in seen])
print("NEW leftover dirs under CIME_OUTPUT_ROOT:", new)
for d in new:
    print(d, sorted(os.listdir(d)), subprocess.run(["du","-sh",d],capture_output=True,text=True).stdout.split()[0])
    for sub in ("bld","run"):
        print("  ", sub, sorted(os.listdir(os.path.join(d,sub)))[:10])
