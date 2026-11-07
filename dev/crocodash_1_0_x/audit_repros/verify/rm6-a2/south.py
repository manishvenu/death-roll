"""pinned code: west segment at lon -0.05 (= 359.95) and a south segment
crossing 0 deg (lon -0.5..0.5, res 0.05). Per-point error vs analytic."""
import warnings, logging
from pathlib import Path
import numpy as np, xarray as xr
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
from mom6_forge.grid import Grid
from regional_mom6.regional_mom6 import prepare_tpxo_tidal_forcing
from regional_mom6.segment import Segment
S = Path(__file__).resolve().parent; T = S / "tpxo_var"
h, u, v = prepare_tpxo_tidal_forcing(T/"h_synth.nc", T/"u_synth.nc", ["M2"])
sel = dict(ny=slice(450, 560))
h = h[["lon","lat","hRe","hIm"]].isel(sel).load(); u = u[["lon","lat","uRe","uIm"]].isel(sel).load(); v = v[["lon","lat","vRe","vIm"]].isel(sel).load()
out = S/"scan/south"; out.mkdir(parents=True, exist_ok=True)
g = Grid(lenx=1.0, leny=0.5, resolution=0.05, xstart=-0.05, ystart=-4.0, name="s")
seg = Segment.cardinal(g.supergrid.to_ds(), "west", "segment_009")
seg.regrid_tides(v, u, h, None, out, "2020-01-01")
tu = xr.open_dataset(out/"tu_segment_009.nc")
print("west lon=-0.05: uamp zeros", int((tu["uamp_segment_009"].values==0).sum()), "/", tu["uamp_segment_009"].size)
g = Grid(lenx=1.0, leny=0.5, resolution=0.05, xstart=-0.5, ystart=-4.0, name="s")
seg = Segment.cardinal(g.supergrid.to_ds(), "south", "segment_010")
seg.regrid_tides(v, u, h, None, out, "2020-01-01")
tz = xr.open_dataset(out/"tz_segment_010.nc"); tu = xr.open_dataset(out/"tu_segment_010.nc")
lon = seg.lon.values % 360
z = tz["zamp_segment_010"].values.ravel(); ua = tu["uamp_segment_010"].values.ravel()
ez = 0.5 + 0.3*np.sin(np.radians(30*lon)); eu = 0.10 + 0.03*np.sin(np.radians(30*lon))
for k in range(len(lon)):
    if abs(z[k]-ez[k]) > 2e-4 or abs(ua[k]-eu[k]) > 2e-4:
        print(f"  south lon {lon[k]:8.3f}: zamp {z[k]:.4f} exp {ez[k]:.4f} | uamp {ua[k]:.4f} exp {eu[k]:.4f}")
print("south points:", len(lon))
