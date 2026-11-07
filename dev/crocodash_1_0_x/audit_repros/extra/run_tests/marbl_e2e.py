import sys, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(sys.argv[1]); comp = sys.argv[2]
MARBL_IC = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/bgc/ecosys_jan_IC_omip_latlon_1x1_180W_c231221.nc"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="mb")
topo = Topo(grid, min_depth=10.0); topo.set_flat(3000.0)
d = topo.depth.copy(); d[:, :2] = 0.0; topo.depth = d  # land on the west edge so runoff has a coast
vgrid = VGrid.uniform(nk=10, depth=3000.0, name="mb")
cr = S / "cases/audit_marbl"; inp = S / "input/audit_marbl"
case = Case(cesmroot=Path("/glade/u/home/manishrv/work/installs/CESM_crocodash"), caseroot=cr, inputdir=inp,
            compset=comp, ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, machine="derecho", project="ncgd0011", override=True)
print("CREATED", comp, flush=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data",
                        marbl_ic_filepath=MARBL_IC)
print("CONFIGURED", flush=True)
case.process_forcings()
print("PROCESS DONE", flush=True)

nl = (cr / "user_nl_mom").read_text()
refs = sorted(set(re.findall(r"([\w./-]+\.nc)", nl)))
print("user_nl_mom .nc refs:")
for p in refs:
    q = Path(p) if p.startswith("/") else inp / "ocn" / p
    print("  ", p, "exists:", q.exists())
for f in sorted((inp / "ocn").glob("*.nc")):
    if f.name.startswith(("ESMF", "ocean_h", "scrip")):
        continue
    ds = xr.open_dataset(f, decode_times=False)
    fl = [v for v in ds.data_vars if ds[v].dtype.kind == "f" and ds[v].size]
    allnan = [v for v in fl if np.isnan(ds[v].values).all()]
    print(f.name, dict(ds.sizes), "nvars", len(ds.data_vars), "all-NaN:", allnan[:8])
    ds.close()
