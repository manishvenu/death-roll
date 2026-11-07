"""Verify creation_cli-a8, part 2: bundle the source case made by a8_fork.py, fork it."""
import io, json, sys, contextlib
from pathlib import Path
# env artifact: CESM_crocodash's MOM_RPS imports a sibling module (accepted, not a bug)
sys.path.insert(0, "/glade/u/home/manishrv/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS")
D = Path(__file__).resolve().parent
CESMROOT = Path("/glade/u/home/manishrv/work/installs/CESM_crocodash")
src_root, src_in = D / "cases/audit_a8v_src", D / "inputs/audit_a8v_src"
cfg = json.load(open(src_in / "extract_forcings/config.json"))
mapf = Path(cfg["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"])
mapf.parent.mkdir(parents=True, exist_ok=True); mapf.write_text("stand-in map")
(src_in / "ice").mkdir(exist_ok=True)
(src_in / "ice/cice_forcing.nc").write_text("stand-in cice forcing")
(src_in / "ocn/init_tracers.nc").write_text("stand-in IC")
print("SRC map:", mapf, mapf.exists())

from CrocoDash.shareable import CaseBundle, ForkBundle
bdir = CaseBundle(src_root).bundle(D / "bundles")
print("BUNDLE files:", sorted(str(p.relative_to(bdir)) for p in bdir.rglob("*")
      if p.is_file() and (p.parent.name in ("ice", "mapping") or p.name.startswith("init"))))

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fk = ForkBundle(bdir).fork(cesmroot=CESMROOT, machine="derecho", project_number="ncgd0011",
                               new_caseroot=D / "cases/audit_a8v_fork",
                               new_inputdir=D / "inputs/audit_a8v_fork", plan={})
print("FORK printed 'not valid yet':", "not valid yet" in buf.getvalue())
ncfg = json.load(open(fk.inputdir / "extract_forcings/config.json"))
nmap = Path(ncfg["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"])
print("FORK ROF2OCN_LIQ_RMAPNAME:", nmap, "exists:", nmap.exists())
print("FORK ice/cice_forcing.nc exists:", (fk.inputdir / "ice/cice_forcing.nc").exists())
print("FORK ocn/init_tracers.nc exists:", (fk.inputdir / "ocn/init_tracers.nc").exists())
print("FORK user_nl_cice ice_ic:", [l.strip() for l in open(fk.caseroot / "user_nl_cice") if "ice_ic" in l])
print("FORK inputdir subdirs:", sorted(p.name for p in fk.inputdir.iterdir() if p.is_dir()))
