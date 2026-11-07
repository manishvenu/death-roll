import sys, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=40.0, name="gw")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="gw")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_gwr", inputdir=S/"input/audit_gwr", compset="GWR_JRA",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="TL319",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data",
                        restore_ice=True, cice_product_name="reference_ice", cice_function_name="get_reference_ice_data",
                        ww3_obc_product_name="reference_waves", ww3_obc_function_name="get_reference_wave_spectra")
case.process_forcings()
inp = S/"input/audit_gwr"; cr = S/"cases/audit_gwr"
for sub in ["ice", "wav"]:
    for f in sorted((inp/sub).glob("*")):
        line = f"{sub}/{f.name} {f.stat().st_size}B"
        if f.suffix == ".nc":
            ds = xr.open_dataset(f, decode_times=False)
            bad = [v for v in ds.data_vars if ds[v].dtype.kind == "f" and ds[v].size and np.isnan(ds[v].values).all()]
            line += f" vars={list(ds.data_vars)[:8]} all-NaN={bad} dims={dict(ds.sizes)}"
            ds.close()
        print(line)
for nl in ["user_nl_cice", "user_nl_ww3"]:
    t = (cr/nl).read_text()
    paths = re.findall(r"['\"](/[^'\"]+)['\"]", t)
    print(nl, "paths:", [(p.split("/")[-1], Path(p).exists()) for p in paths])
