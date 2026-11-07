import sys, time
from pathlib import Path
t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="smk")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="smk")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/smoke", inputdir=S/"input/smoke",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("case created", time.time()-t0, flush=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
print("configured", time.time()-t0, flush=True)
case.process_forcings()
print("processed", time.time()-t0, flush=True)
import subprocess
print(subprocess.run(["find", str(S/"input/smoke"), "-maxdepth", "3", "-newer", __file__], capture_output=True, text=True).stdout[-3000:])
