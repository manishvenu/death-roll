import sys, time, os, subprocess
from pathlib import Path
t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
H = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/h_tpxo9.v1.nc"
U = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/u_tpxo9.v1.nc"
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=1.0, ystart=-4.0, name="atide")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="atide")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_rm6_tide1", inputdir=S/"input/audit_rm6_tide1",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("case created", time.time()-t0, flush=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data",
                        tpxo_elevation_filepath=H, tpxo_velocity_filepath=U, tidal_constituents=["M2"])
print("configured", time.time()-t0, flush=True)
case.process_forcings()
print("processed", time.time()-t0, flush=True)
inp = S/"input/audit_rm6_tide1"
for p in sorted(inp.iterdir()) + sorted((inp/"ocn").iterdir()):
    print(("L " + os.readlink(p)) if p.is_symlink() else ("D" if p.is_dir() else "F"), p)
