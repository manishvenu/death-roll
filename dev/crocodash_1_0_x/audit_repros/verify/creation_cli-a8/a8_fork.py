"""Verify creation_cli-a8: fork/duplicate drop mapping/ (and fork drops ice/); validate_case is vacuous."""
import io, json, sys, contextlib
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

D = Path(__file__).resolve().parent
CESMROOT = Path("/glade/u/home/manishrv/work/installs/CESM_crocodash")
for d in ("cases", "inputs", "bundles"):
    (D / d).mkdir(exist_ok=True)

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a8v")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="a8v")
src = Case(cesmroot=CESMROOT, caseroot=D / "cases/audit_a8v_src", inputdir=D / "inputs/audit_a8v_src",
           compset="GR_JRA", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
           atm_grid_name="TL319", machine="derecho", project="ncgd0011", override=True)
src.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                       product_name="reference_ocean", function_name="get_reference_ocean_data")

print("ACTIVE:", sorted(src.fcr.active_configurators))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    src.validate_case()
print("SRC validate_case before any processing ->", repr(buf.getvalue()))
for n, c in src.fcr.active_configurators.items():
    print(f"  {n}: get_output_filepaths={c.get_output_filepaths(src.inputdir/'ocn')} validate={c.validate_output_filepaths(src.inputdir/'ocn')}")

cfg = json.load(open(src.inputdir / "extract_forcings/config.json"))
mapf = Path(cfg["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"])
print("SRC map:", mapf)
# stand-ins for what process_forcings writes (map needs a ~200 GB PBS job for real GLOFAS)
mapf.parent.mkdir(parents=True, exist_ok=True); mapf.write_text("stand-in map")
(src.inputdir / "ice").mkdir(exist_ok=True)
(src.inputdir / "ice/cice_forcing.nc").write_text("stand-in cice forcing")
(src.inputdir / "ocn/init_tracers.nc").write_text("stand-in IC")

from CrocoDash.shareable import CaseBundle, ForkBundle
bdir = CaseBundle(src.caseroot).bundle(D / "bundles")
print("BUNDLE files:", sorted(str(p.relative_to(bdir)) for p in bdir.rglob("*") if p.is_file() and (p.parent.name in ("ice", "mapping") or p.name.startswith("init"))))

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fk = ForkBundle(bdir).fork(cesmroot=CESMROOT, machine="derecho", project_number="ncgd0011",
                               new_caseroot=D / "cases/audit_a8v_fork", new_inputdir=D / "inputs/audit_a8v_fork", plan={})
out = buf.getvalue()
print("FORK printed 'not valid yet':", "not valid yet" in out)
ncfg = json.load(open(fk.inputdir / "extract_forcings/config.json"))
nmap = Path(ncfg["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"])
print("FORK ROF2OCN_LIQ_RMAPNAME:", nmap, "exists:", nmap.exists())
print("FORK ice/cice_forcing.nc exists:", (fk.inputdir / "ice/cice_forcing.nc").exists())
print("FORK ocn/init_tracers.nc exists:", (fk.inputdir / "ocn/init_tracers.nc").exists())
cice = fk.fcr.active_configurators.get("cice") or fk.fcr.active_configurators.get("CICE")
print("FORK user_nl_cice ice_ic line:", [l for l in open(fk.caseroot/"user_nl_cice") if "ice_ic" in l])
