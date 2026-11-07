"""Verify: `crocodash duplicate` always runs Case(override=True).

1. Build a tiny source case  V/src_cases/audit_v4a  with inputdir  V/inputs/audit_v4a_in
   (configure_forcings with reference_ocean so the case is a full CrocoDash case).
2. Drop marker files that stand in for processed forcings (in the source inputdir) and
   for model output (in the source case's bld/run dir, CIME_OUTPUT_ROOT/audit_v4a/run).
3. Run the real CLI: crocodash duplicate --source V/src_cases/audit_v4a
       --case V/dst_cases/audit_v4a --inputdir V/inputs
   i.e. duplicate to a new folder, same case name, new inputdir = existing folder that
   holds the source inputdir. No --override exists on the subcommand.
_remove_previous is wrapped: paths inside V are really deleted (real behaviour);
paths outside V (the CIME bld/run dir) are only logged, never deleted (audit rule).
"""
import os, sys, time, shutil
from pathlib import Path

V = Path(__file__).resolve().parent
NAME = "audit_v4b"
CESMROOT = Path("/glade/u/home/manishrv/work/installs/CESM_crocodash")
# Known env artifact (local MOM_interface changes): FType_MOM_params imports a sibling module.
sys.path.insert(0, str(CESMROOT / "components/mom/cime_config/MOM_RPS"))

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
import CrocoDash.case as cmod

src_caseroot = V / "src_b" / NAME
src_inputdir = V / "inputs_b" / f"{NAME}_in"
dst_caseroot = V / "dst_b" / NAME
new_inputdir_arg = V / "inputs_b"
for p in (V / "src_b", V / "inputs_b", V / "dst_b"):
    p.mkdir(parents=True, exist_ok=True)

t0 = time.time()
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="v4b")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="v4b")
case = Case(cesmroot=CESMROOT, caseroot=src_caseroot, inputdir=src_inputdir,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
src_rundir_parent = Path(case.cime.cime_output_root) / NAME
print(f"[{time.time()-t0:.0f}s] source case built; CIME bld/run dir = {src_rundir_parent} exists={src_rundir_parent.exists()}", flush=True)

# Stand-ins for processed forcings and model output
forcing_marker = src_inputdir / "ocn" / "forcing_obc_segment_001_PROCESSED.nc"
forcing_marker.write_text("pretend processed OBC forcing")
(src_rundir_parent / "run").mkdir(parents=True, exist_ok=True)
restart_marker = src_rundir_parent / "run" / f"{NAME}.mom6.r.0001-01-01-00000.nc"
restart_marker.write_text("pretend restart")
print("markers:", forcing_marker.exists(), restart_marker.exists(), flush=True)

orig_remove = cmod._remove_previous
log = []
def guarded_remove(path):
    path = Path(path)
    if "temp_case-" in str(path) or "temp_inputdir" in str(path):
        return orig_remove(path)  # identify_non_standard_case_info's own temp case
    exists = path.exists()
    log.append((str(path), exists))
    if V in path.parents:
        print(f"REMOVE (real, inside scratch): {path} exists={exists}", flush=True)
        orig_remove(path)
    else:
        content = sorted(str(p.relative_to(path)) for p in path.rglob("*"))[:10] if exists else []
        print(f"WOULD REMOVE (outside scratch, skipped): {path} exists={exists} contains={content}", flush=True)
cmod._remove_previous = guarded_remove

from CrocoDash import cli
sys.argv = ["crocodash", "duplicate", "--source", str(src_caseroot),
            "--case", str(dst_caseroot), "--inputdir", str(new_inputdir_arg)]
print("RUN:", " ".join(sys.argv), flush=True)
try:
    cli.main()
except BaseException as e:
    print("duplicate raised:", type(e).__name__, str(e)[:500], flush=True)

print(f"[{time.time()-t0:.0f}s] after duplicate:", flush=True)
print("  source caseroot exists:", src_caseroot.exists())
print("  source inputdir exists:", src_inputdir.exists())
print("  source processed-forcing marker exists:", forcing_marker.exists())
print("  new caseroot exists:", dst_caseroot.exists())
print("  _remove_previous calls for the new case:")
for p, e in log:
    print(f"    {p}  (existed={e})  same_as_source_rundir_parent={Path(p) == src_rundir_parent}")
