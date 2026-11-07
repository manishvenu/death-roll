import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
import mom6_forge; print("mom6_forge from", mom6_forge.__file__)

# 1) Rotated grid via the public API, written exactly as Case() writes it
g = Grid.from_center(center_lat=32.0, center_lon=-60.0, width_m=200e3, height_m=200e3,
                     resolution_m=20e3, angle_deg=30.0, name="a12")
g.write_supergrid("hgrid.nc")
h = xr.open_dataset("hgrid.nc")
a = h.angle_dx
print("hgrid angle_dx attrs:", dict(a.attrs))
print("hgrid angle_dx min/max:", float(a.min()), float(a.max()))
print("Grid.angle (same values, mom6_forge's own label):", dict(g.angle.attrs), float(g.angle.min()), float(g.angle.max()))

# 2) CICE grid file, exactly as Case() writes it when CICE is in the compset
g2 = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a12b")
t = Topo(g2, min_depth=10.0)
t.set_flat(1000.0)
t.write_cice_grid("cice_grid.nc")
c = xr.open_dataset("cice_grid.nc", decode_cf=False)
for v in ["ulat", "ulon", "tlat", "tlon", "angle", "anglet"]:
    print(f"cice {v}: units={c[v].attrs.get('units')!r} min={float(c[v].min()):.4f} max={float(c[v].max()):.4f}")
print("source g2.tlat (deg) min/max:", float(g2.tlat.min()), float(g2.tlat.max()))

# 3) Units-aware consumer: cf_xarray / metpy-style detection of lat/lon by units
try:
    import cf_xarray  # noqa
    cc = xr.open_dataset("cice_grid.nc")
    print("cf_xarray latitude candidates:", cc.cf.coordinates.get("latitude"), "longitude:", cc.cf.coordinates.get("longitude"))
except Exception as e:
    print("cf_xarray not usable:", type(e).__name__, e)
