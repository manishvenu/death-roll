import sys, numpy as np, xarray as xr
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
import importlib
rm6_chl = importlib.import_module("regional_mom6.chlorophyll") if importlib.util.find_spec("regional_mom6.chlorophyll") else None
from CrocoDash.forcing import chl as cdchl
S = Path(sys.argv[1]); out = S/"chl_out"; out.mkdir(exist_ok=True)
SEA = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/chl/data/SeaWIFS.L3m.MC.CHL.chlor_a.0.25deg.nc"
hg = next((S/"input/audit_pol_arc/ocn").glob("ocean_hgrid_*.nc")); tp = next((S/"input/audit_pol_arc/ocn").glob("ocean_topog_*.nc"))
grid = Grid.from_supergrid(str(hg))
topo = Topo.from_topo_file(grid, str(tp), min_depth=9.5)
if len(sys.argv) > 2: type(grid).is_rectangular = lambda self, atol=1e-3: True
cdchl.rm6_chl.interpolate_and_fill_seawifs(grid, topo, SEA, out/"chl_arc.nc", calendar="noleap")
ds = xr.open_dataset(out/"chl_arc.nc", decode_times=False)
wet = topo.depth.values > 0
for v in ds.data_vars:
    a = ds[v].values
    if a.dtype.kind == "f" and a.ndim == 3:
        for m in range(a.shape[0]):
            x = a[m][wet]
            print(v, "month", m+1, "nan frac (wet)", round(float(np.isnan(x).mean()), 3), "min", None if np.isnan(x).all() else round(float(np.nanmin(x)), 4), "max", None if np.isnan(x).all() else round(float(np.nanmax(x)), 4), "zeros", int((x == 0).sum()))
src = xr.open_dataset(SEA)
print("source vars", list(src.data_vars), dict(src.sizes))
