"""rm6-level: prepare_tpxo_tidal_forcing + Segment.regrid_tides (pinned code)
on west segments at several longitudes, under 3 variants:
  pinned            -- code as shipped
  periodic_only     -- create_regridder(periodic=True), TPXO left (nx, ny)
  transpose+periodic-- TPXO transposed to (constituent, ny, nx) + periodic=True
Data: synthetic TPXO9.v1 geometry, smooth lon-varying amplitudes."""
import sys, warnings, logging
from pathlib import Path
import numpy as np, xarray as xr
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
from mom6_forge.grid import Grid
from regional_mom6.regional_mom6 import prepare_tpxo_tidal_forcing
from regional_mom6 import regridding as rgd
from regional_mom6.segment import Segment

S = Path(__file__).resolve().parent
T = S / "tpxo_var"
_orig = rgd.create_regridder
def exp(lon):
    lon = np.asarray(lon) % 360
    return (0.5 + 0.3*np.sin(np.radians(30*lon)), 0.10 + 0.03*np.sin(np.radians(30*lon)), 0.06 + 0.02*np.cos(np.radians(30*lon)))

def load(transpose):
    h, u, v = prepare_tpxo_tidal_forcing(T/"h_synth.nc", T/"u_synth.nc", ["M2"])
    # lat-band subset for speed only (full 0..360 lon range kept, so the seam gap is unchanged)
    sel = dict(ny=slice(450, 560))   # lat ~ -15 .. +3
    h = h[["lon","lat","hRe","hIm"]].isel(sel).load()
    u = u[["lon","lat","uRe","uIm"]].isel(sel).load()
    v = v[["lon","lat","vRe","vIm"]].isel(sel).load()
    if transpose:
        h, u, v = (d.transpose("constituent", "ny", "nx") for d in (h, u, v))
    return h, u, v

variants = {"pinned": (False, False), "periodic_only": (False, True), "transpose+periodic": (True, True)}
xs = [float(a) for a in sys.argv[1:]] or [-0.1, 0.0, 0.05, 0.1, 0.15, 1.0]
for name, (tr, per) in variants.items():
    def patched(*a, **k):
        if per: k["periodic"] = True
        return _orig(*a, **k)
    rgd.create_regridder = patched
    h, u, v = load(tr)
    print(f"== {name}", flush=True)
    for x in xs:
        out = S / f"scan/{name}/x{x}"; out.mkdir(parents=True, exist_ok=True)
        g = Grid(lenx=1.0, leny=1.0, resolution=0.1, xstart=x, ystart=-4.0, name="scan")
        hg = g.supergrid.to_ds()
        seg = Segment.cardinal(hg, "west", "segment_001")
        try:
            seg.regrid_tides(v, u, h, None, out, "2020-01-01")
        except Exception as e:
            print(f"  west lon={x:6.2f}: ERROR {type(e).__name__}: {str(e)[:150]}", flush=True); continue
        tu = xr.open_dataset(out/"tu_segment_001.nc"); tz = xr.open_dataset(out/"tz_segment_001.nc")
        z = tz["zamp_segment_001"].values; ua = tu["uamp_segment_001"].values; va = tu["vamp_segment_001"].values
        ez, eu, ev = exp(x)
        print(f"  west lon={x:6.2f}: zamp {z.mean():.4f} (exp {ez:.4f}, zeros {(z==0).sum()}/{z.size}) | "
              f"uamp {ua.mean():.4f} (exp {eu:.4f}, zeros {(ua==0).sum()}/{ua.size}) | "
              f"vamp {va.mean():.4f} (exp {ev:.4f}, zeros {(va==0).sum()}/{va.size})", flush=True)
    rgd.create_regridder = _orig
