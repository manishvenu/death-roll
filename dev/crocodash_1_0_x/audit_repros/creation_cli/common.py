import os, sys, time
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

D = Path(__file__).resolve().parent
CESMROOT = Path("/glade/u/home/manishrv/work/installs/CESM_crocodash")
NYF = "1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV"

def objs(name="ccl", x0=-60.0, lenx=4.0, leny=4.0, res=0.5, y0=30.0):
    grid = Grid(lenx=lenx, leny=leny, resolution=res, xstart=x0, ystart=y0, name=name)
    topo = Topo(grid, min_depth=10.0)
    topo.set_flat(1000.0)
    vgrid = VGrid.uniform(nk=5, depth=1000.0, name=name)
    return grid, topo, vgrid

def make_case(caseroot, inputdir, name="ccl", compset=NYF, override=True, atm="T62", **kw):
    grid, topo, vgrid = objs(name)
    return Case(cesmroot=CESMROOT, caseroot=caseroot, inputdir=inputdir, compset=compset,
                ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name=atm,
                machine="derecho", project="ncgd0011", override=override, **kw)

def configure(case, days=3):
    case.configure_forcings(date_range=["2020-01-01 00:00:00", f"2020-01-0{1+days} 00:00:00"],
                            product_name="reference_ocean", function_name="get_reference_ocean_data")
