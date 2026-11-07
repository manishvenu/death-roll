"""Same as tides_seam.py, with a candidate fix monkeypatched: TPXO transposed to
(constituent, ny, nx) and the tidal regridders built with periodic=True."""
import sys
from pathlib import Path
import numpy as np, xarray as xr
from mom6_forge.grid import Grid
from regional_mom6.regional_mom6 import prepare_tpxo_tidal_forcing
from regional_mom6 import segment as segmod, regridding as rgd
from regional_mom6.segment import Segment

_orig = rgd.create_regridder
def patched(*a, **k):
    k["periodic"] = True
    return _orig(*a, **k)
segmod.rgd.create_regridder = patched

H = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/h_tpxo9.v1.nc"
U = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/u_tpxo9.v1.nc"
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
xstart = float(sys.argv[2])
tpxo_h, tpxo_u, tpxo_v = prepare_tpxo_tidal_forcing(H, U, ["M2"])
tpxo_h = tpxo_h[["lon","lat","hRe","hIm"]].load().transpose("constituent","ny","nx")
tpxo_u = tpxo_u[["lon","lat","uRe","uIm"]].load().transpose("constituent","ny","nx")
tpxo_v = tpxo_v[["lon","lat","vRe","vIm"]].load().transpose("constituent","ny","nx")
grid = Grid(lenx=2.0, leny=2.0, resolution=0.25, xstart=xstart, ystart=-4.0, name="seam")
hgrid = grid.supergrid.to_ds()
for b, n in (("west", 1), ("east", 2), ("south", 3)):
    seg = Segment.cardinal(hgrid, b, f"segment_{n:03d}")
    seg.regrid_tides(tpxo_v, tpxo_u, tpxo_h, None, out, "2020-01-01")
    tu = xr.open_dataset(out / f"tu_segment_{n:03d}.nc"); tz = xr.open_dataset(out / f"tz_segment_{n:03d}.nc")
    print(b, "uamp", np.round(tu[f"uamp_segment_{n:03d}"].values.ravel()[[0,8,16]],5),
          "vamp", np.round(tu[f"vamp_segment_{n:03d}"].values.ravel()[[0,8,16]],5),
          "zamp", np.round(tz[f"zamp_segment_{n:03d}"].values.ravel()[[0,8,16]],4))
