# Build a tiny NYF case with reference_ocean conditions + TPXO M2 tides, process forcings,
# then show what the tides step left in inputdir and inputdir/ocn.
import sys, os, time
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
D = Path(sys.argv[1])
TPXO = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo"
t0 = time.time()
grid = Grid(lenx=3.0, leny=3.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="va4")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="va4")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=D/"cases/audit_va4_src", inputdir=D/"input/audit_va4_src",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data",
                        tpxo_elevation_filepath=f"{TPXO}/h_tpxo9.v1.nc",
                        tpxo_velocity_filepath=f"{TPXO}/u_tpxo9.v1.nc",
                        tidal_constituents=["M2"])
print("configured", round(time.time()-t0), flush=True)
case.process_forcings()
print("processed", round(time.time()-t0), flush=True)
inp = (D/"input/audit_va4_src").resolve()
for p in sorted(inp.iterdir()) + sorted((inp/"ocn").iterdir()):
    kind = ("SYMLINK -> " + os.readlink(p)) if p.is_symlink() else ("DIR" if p.is_dir() else "file")
    print(f"  {kind:60s} {p.relative_to(inp.parent)}")
print("cycle: realpath(ocn/rundir) == inputdir:", os.path.realpath(inp/"ocn/rundir") == str(inp))
print("cycle: realpath(inputdir/inputdir) == inputdir/ocn:", os.path.realpath(inp/"inputdir") == str(inp/"ocn"))
print("deep path resolves:", (inp/"ocn/rundir/ocn/rundir/ocn/rundir/inputdir/rundir/ocn").is_dir())
