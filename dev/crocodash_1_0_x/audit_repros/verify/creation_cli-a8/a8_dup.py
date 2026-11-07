"""Verify creation_cli-a8 (duplicate half): duplicate_case drops mapping/."""
import sys; sys.path.insert(0, "/glade/u/home/manishrv/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS")
import io, json, contextlib
from pathlib import Path
from CrocoDash.shareable import duplicate_case
D = Path(__file__).resolve().parent
src_root = D / "cases/audit_a8v_src"
src_in = D / "inputs/audit_a8v_src"
print("SRC mapping/:", sorted(p.name for p in (src_in / "mapping").iterdir()))
print("SRC ice/:", sorted(p.name for p in (src_in / "ice").iterdir()))
new = duplicate_case(src_root, D / "cases/audit_a8v_dup", D / "inputs/audit_a8v_dup")
ncfg = json.load(open(new.inputdir / "extract_forcings/config.json"))
nmap = Path(ncfg["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"])
print("DUP ROF2OCN_LIQ_RMAPNAME:", nmap, "exists:", nmap.exists())
print("DUP ice/cice_forcing.nc exists:", (new.inputdir / "ice/cice_forcing.nc").exists())
print("DUP ocn/init_tracers.nc exists:", (new.inputdir / "ocn/init_tracers.nc").exists())
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    new.validate_case()
print("DUP validate_case output:", repr(buf.getvalue()))
