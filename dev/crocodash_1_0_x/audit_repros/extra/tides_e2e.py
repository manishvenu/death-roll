import sys, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1]); T = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="td")
topo = Topo(grid, min_depth=10.0); topo.set_flat(3000.0)
vgrid = VGrid.uniform(nk=10, depth=3000.0, name="td")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_tides", inputdir=S/"input/audit_tides",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data",
                        tidal_constituents=["M2", "S2", "K1", "O1"],
                        tpxo_elevation_filepath=T+"h_tpxo9.v1.nc", tpxo_velocity_filepath=T+"u_tpxo9.v1.nc")
case.process_forcings()
ocn = S/"input/audit_tides/ocn"
nl = (S/"cases/audit_tides/user_nl_mom").read_text()
print("NL:", [l.strip() for l in nl.splitlines() if re.search(r"TIDE|OBC_SEGMENT_001_DATA", l)])
refs = set(re.findall(r"file:([\w.]+)\(", nl)); print("referenced files exist:", {r: (ocn/r).exists() for r in sorted(refs)})
for f in sorted(ocn.glob("tu_*.nc")) + sorted(ocn.glob("tz_*.nc")):
    ds = xr.open_dataset(f, decode_times=False)
    out = []
    for v in ds.data_vars:
        a = ds[v].values.astype(float); a = np.where(np.abs(a) > 1e10, np.nan, a)
        out.append(f"{v}:[{np.nanmin(a):.3g},{np.nanmax(a):.3g}] {ds[v].attrs.get('units','')}")
    print(f.name, dict(ds.sizes), "|", "; ".join(out)); ds.close()
