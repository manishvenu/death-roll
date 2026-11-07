import sys
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
which = sys.argv[1]; B = Path("/glade/derecho/scratch/manishrv/ar")
T = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name=f"r{which}")
topo = Topo(grid, min_depth=10.0); topo.set_flat(3000.0)
vgrid = VGrid.uniform(nk=10, depth=3000.0, name=f"r{which}")
case = Case(cesmroot=Path("/glade/u/home/manishrv/work/installs/CESM_crocodash"), caseroot=B/f"c/audit_r{which}", inputdir=B/f"i/r{which}",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
            atm_grid_name="T62", machine="derecho", project="ncgd0011", override=True)
kw = dict(product_name="reference_ocean", function_name="get_reference_ocean_data")
if which == "D":
    kw.update(date_range=["2020-01-01 00:00:00", "2020-01-04 00:00:00"], tidal_constituents=["M2"],
              tpxo_elevation_filepath=T + "h_tpxo9.v1.nc", tpxo_velocity_filepath=T + "u_tpxo9.v1.nc")
else:
    kw.update(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"])
case.configure_forcings(**kw)
case.process_forcings()
nl = B/f"c/audit_r{which}/user_nl_mom"
extra = ["diag_table%h.hourly%module = ocean_model", "diag_table%h.hourly%fields = SSH, tos",
         "diag_table%h.hourly%output_freq = 1", "diag_table%h.hourly%output_freq_units = hours"]
nl.write_text(nl.read_text() + "\n" + "\n".join(extra) + "\n")
print("READY", which)
