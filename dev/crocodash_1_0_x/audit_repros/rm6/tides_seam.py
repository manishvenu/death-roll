"""Tides across the TPXO seam: run Segment.regrid_tides on a grid whose west
edge sits at lon 0 (xstart=0.0), using the real TPXO9 v1 files (M2 only)."""
import sys, warnings
from pathlib import Path
import numpy as np, xarray as xr
from mom6_forge.grid import Grid
from regional_mom6.regional_mom6 import prepare_tpxo_tidal_forcing
from regional_mom6.segment import Segment

H = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/h_tpxo9.v1.nc"
U = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/u_tpxo9.v1.nc"
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
xstart = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
tpxo_h, tpxo_u, tpxo_v = prepare_tpxo_tidal_forcing(H, U, ["M2"])
# load the M2 slice only
tpxo_h = tpxo_h[["lon","lat","hRe","hIm"]].load(); tpxo_u = tpxo_u[["lon","lat","uRe","uIm"]].load(); tpxo_v = tpxo_v[["lon","lat","vRe","vIm"]].load()
grid = Grid(lenx=2.0, leny=2.0, resolution=0.25, xstart=xstart, ystart=float(sys.argv[3]) if len(sys.argv) > 3 else -4.0, name="seam")
hgrid = grid.supergrid.to_ds() if hasattr(grid.supergrid, "to_ds") else grid.write_supergrid(out/"hgrid.nc")
for b, n in (("west", 1), ("east", 2), ("south", 3)):
    seg = Segment.cardinal(hgrid, b, f"segment_{n:03d}")
    print(b, "lon range", float(seg.lon.min()), float(seg.lon.max()))
    seg.regrid_tides(tpxo_v, tpxo_u, tpxo_h, None, out, "2020-01-01")
    tu = xr.open_dataset(out / f"tu_segment_{n:03d}.nc")
    tz = xr.open_dataset(out / f"tz_segment_{n:03d}.nc")
    for v in (f"uamp_segment_{n:03d}", f"vamp_segment_{n:03d}"):
        a = tu[v].values
        print(f"  {v}: min={np.nanmin(a):.4g} max={np.nanmax(a):.4g} zeros={(a==0).sum()}/{a.size}")
    a = tz[f"zamp_segment_{n:03d}"].values
    print(f"  zamp: min={np.nanmin(a):.4g} max={np.nanmax(a):.4g} zeros={(a==0).sum()}/{a.size}")
