"""Verify: Grid.from_supergrid rejects degree-unit hgrids whose x/y unit strings differ."""
import os
import traceback
from pathlib import Path

import xarray as xr

import mom6_forge
from mom6_forge.grid import Grid
from CrocoDash.recipe import build_grid

HERE = Path(__file__).parent
print("mom6_forge from", mom6_forge.__file__)


def attempt(label, fn):
    try:
        g = fn()
        print(f"[{label}] OK: nx={g.nx} ny={g.ny} tlon.units={g.tlon.units!r} tlat.units={g.tlat.units!r}")
        return g
    except Exception as e:
        print(f"[{label}] {type(e).__name__}: {e}")
        return None


# 1. Synthetic tiny grid, rewritten with FRE make_hgrid-style unit strings
g0 = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a10")
ds = g0.supergrid.to_ds()
print("mom6_forge writes x/y units:", ds.x.attrs.get("units"), ds.y.attrs.get("units"))
fre = ds.copy()
fre["x"].attrs["units"] = "degree_east"
fre["y"].attrs["units"] = "degree_north"
fre_path = HERE / "fre_style_hgrid.nc"
fre.to_netcdf(fre_path)

Grid.check_supergrid(xr.open_dataset(fre_path))
print("check_supergrid accepts degree_east/degree_north: OK")
attempt("FRE-style from_supergrid", lambda: Grid.from_supergrid(str(fre_path)))
attempt("FRE-style CrocoDash recipe build_grid", lambda: build_grid({"supergrid_path": str(fre_path)}))

# 2. Real hgrid shipped in CESM inputdata (POP-derived gx1v6): units 'degrees E' / 'degrees N'
gx1 = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/gx1v6/ocean_hgrid.nc"
with xr.open_dataset(gx1) as d:
    print("gx1v6 x/y units:", repr(d.x.units), repr(d.y.units))
    Grid.check_supergrid(d)
    print("check_supergrid accepts gx1v6: OK")
attempt("gx1v6 from_supergrid", lambda: Grid.from_supergrid(gx1))
attempt("gx1v6 subgrid_from_supergrid",
        lambda: Grid.subgrid_from_supergrid(gx1, llc=(20.0, -80.0), urc=(30.0, -70.0), name="gx1sub"))

# 3. Monkeypatched fix: accept any degree units on both axes, normalise to 'degrees'
_orig = Grid.from_supergrid_ds.__func__


def _patched(cls, ds, name=None):
    xu, yu = ds.x.attrs.get("units", ""), ds.y.attrs.get("units", "")
    assert "degree" in xu and "degree" in yu, "Only degrees units are supported in supergrid files"
    ds = ds.copy()
    ds["x"].attrs["units"] = "degrees"
    ds["y"].attrs["units"] = "degrees"
    return _orig(cls, ds, name)


Grid.from_supergrid_ds = classmethod(_patched)
gf = attempt("FRE-style from_supergrid (patched)", lambda: Grid.from_supergrid(str(fre_path)))
if gf is not None:
    import numpy as np
    print("  tlon/tlat identical to original:",
          bool(np.allclose(gf.tlon, g0.tlon) and np.allclose(gf.tlat, g0.tlat)),
          " tarea identical:", bool(np.allclose(gf.tarea, g0.tarea)))
attempt("gx1v6 subgrid_from_supergrid (patched)",
        lambda: Grid.subgrid_from_supergrid(gx1, llc=(20.0, -80.0), urc=(30.0, -70.0), name="gx1sub"))
