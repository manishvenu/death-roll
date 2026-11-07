import os, sys, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from CrocoDash.shareable import CaseBundle, ForkBundle
for d in ("cases10", "inputs10", "bundles10"): (D/d).mkdir(exist_ok=True)
class _C: pass
C = _C(); C.caseroot = D/"cases10/audit_ccl_r10c"; C.inputdir = D/"inputs10/audit_ccl_r10c"
cfg = json.load(open(C.inputdir/"extract_forcings/config.json"))
mapf = Path(cfg["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"]) if "runoff" in cfg else None
print("map file configured:", mapf)
# stand-ins for what process_forcings would have produced
mapf.parent.mkdir(parents=True, exist_ok=True); mapf.write_text("dummy map")
(C.inputdir/"ice").mkdir(exist_ok=True); (C.inputdir/"ice/cice_forcing.nc").write_text("dummy cice forcing")
for f in ("init_tracers_filled.nc", "forcing_obc_segment_001.nc"): (C.inputdir/"ocn"/f).write_text("dummy")
cb = CaseBundle(C.caseroot)
bdir = cb.bundle(D/"bundles10")
print("BUNDLE contents:", sorted(str(p.relative_to(bdir)) for p in bdir.rglob("*") if p.is_file() and "user_nl" not in p.name))
fb = ForkBundle(bdir)
new = fb.fork(cesmroot=CESMROOT, machine="derecho", project_number="ncgd0011",
              new_caseroot=D/"cases10/audit_ccl_r10f", new_inputdir=D/"inputs10/audit_ccl_r10f", plan={})
ncfg = json.load(open(new.inputdir/"extract_forcings/config.json"))
nmap = Path(ncfg["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"])
print("FORK expects map:", nmap, "exists:", nmap.exists())
print("FORK ice/cice_forcing.nc exists:", (new.inputdir/"ice/cice_forcing.nc").exists())
print("FORK inputdir files:", sorted(str(p.relative_to(new.inputdir)) for p in new.inputdir.rglob("*") if p.is_file() and "extract_forcings" not in str(p)))
