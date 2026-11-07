import sys, os, time
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
name = "audit_va6_1"
inputdir = S / "input" / name
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="va6")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="va6")
case = Case(cesmroot=Path(os.environ["CESMROOT"]), caseroot=S / "cases" / name, inputdir=inputdir,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
ARGS = dict(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
            product_name="reference_ocean", function_name="get_reference_ocean_data")
ef = inputdir / "extract_forcings"

def snap(tag):
    files = {str(p.relative_to(inputdir)): p.stat().st_mtime_ns
             for d in (ef, inputdir / "ocn") if d.exists() for p in sorted(d.rglob("*")) if p.is_file()}
    print(f"--- {tag}: {len(files)} files under extract_forcings/ + ocn/")
    for k in files:
        if k.startswith("extract_forcings"):
            print("   ", k)
    return files

case.configure_forcings(**ARGS)
case.process_forcings()
s1 = snap("after configure #1 + process #1")
# stand-in for GLORYS data the user downloaded by hand with get_glorys_data.sh
sentinel = ef / "raw_data" / "user_downloaded_by_script.nc"
sentinel.write_bytes(b"x")
print("case.override =", case.override)

case.configure_forcings(**ARGS)   # identical arguments
s2 = snap("after identical configure #2 (override=True)")
print("sentinel survived:", sentinel.exists())
time.sleep(1.1)
case.process_forcings()
s3 = snap("after process #2")
refetched = [k for k in s1 if k in s3 and s1[k] != s3[k]]
kept = [k for k in s1 if k in s3 and s1[k] == s3[k]]
print("REWRITTEN by process #2:", refetched)
print("UNCHANGED (skipped) by process #2:", kept)

# control: same Case, same args, override flag off (equivalent to deleting case.py:654-655)
sentinel.write_bytes(b"x")
case.override = False
case.configure_forcings(**ARGS)
s4 = snap("CONTROL: identical configure #3 with case.override=False")
print("sentinel survived:", sentinel.exists())
time.sleep(1.1)
case.process_forcings()
s5 = snap("CONTROL: after process #3")
print("REWRITTEN by process #3:", [k for k in s4 if k in s5 and s4[k] != s5[k]])
print("DONE")
