import numpy as np, xarray as xr
from mom6_forge.grid import Grid
from mom6_forge._supergrid import SupergridBase
from mom6_forge.utils import normalize_deg

def attempt(*a, **k):
    try:
        g = Grid.from_center(*a, **k); return f"OK cyclic_x={g.cyclic_x}"
    except AssertionError as e:
        return f"FAIL ({e})"

print("== realistic estuary-aligned domains, angle_deg=90 ==")
for lab, args in [
    ("Chesapeake mouth 37N -76, 40x20 km @2 km", (37.0, -76.0, 40e3, 20e3, 2e3)),
    ("Delaware 39N -75, 30x20 km @1.5 km",       (39.0, -75.0, 30e3, 20e3, 1.5e3)),
    ("Amazon 0N -50, 200x100 km @10 km",          (0.0, -50.0, 200e3, 100e3, 10e3)),
    ("Rio de la Plata -35 -57, 40x20 km @2 km",   (-35.0, -57.0, 40e3, 20e3, 2e3)),
    ("Ganges 21N 89E, 40x20 km @2 km",            (21.0, 89.0, 40e3, 20e3, 2e3)),
    ("Gulf of Guinea 4N 5E, 100x60 km @5km",     (4.0, 5.0, 100e3, 60e3, 5e3)),
    ("Red Sea 20N 39E, 200x100 km @10km",         (20.0, 39.0, 200e3, 100e3, 10e3)),
]:
    print(f"  {lab:45s} ang=90 -> {attempt(*args, angle_deg=90)} | ang=0 -> {attempt(*args, angle_deg=0)}")

print("\n== height sweep (width=2*height, 20 cells wide), angle 90, lon -60 ==")
for lat in (0, 15, 30, 45):
    row = []
    for h in (10e3, 30e3, 60e3, 100e3, 200e3):
        r = attempt(lat, -60.0, 2*h, h, h/10, angle_deg=90)
        row.append(f"h={int(h/1e3)}km:{'FAIL' if r.startswith('FAIL') else 'ok'}")
    print(f"  lat={lat:3d}: " + "  ".join(row))

print("\n== same but lon +10 (tolerance rtol*lon is ~30x smaller) ==")
for lat in (0, 15, 30, 45):
    row = []
    for h in (10e3, 30e3, 60e3, 100e3, 200e3):
        r = attempt(lat, 10.0, 2*h, h, h/10, angle_deg=90)
        row.append(f"h={int(h/1e3)}km:{'FAIL' if r.startswith('FAIL') else 'ok'}")
    print(f"  lat={lat:3d}: " + "  ".join(row))

# ---- proposed fix, monkeypatched ----
def _cyc(sg, atol=1e-6):
    x0, x1 = np.asarray(sg.x)[:, 0], np.asarray(sg.x)[:, -1]
    y0, y1 = np.asarray(sg.y)[:, 0], np.asarray(sg.y)[:, -1]
    dlon = (x0 - x1 + 180.0) % 360.0 - 180.0
    return bool(np.all(np.abs(dlon) < atol) and np.allclose(y0, y1, rtol=0, atol=atol))

orig = Grid.is_cyclic_x
Grid.is_cyclic_x = staticmethod(_cyc)
SupergridBase.is_cyclic_x = property(lambda self: _cyc(self))
print("\n== with patched is_cyclic_x ==")
print("  from_center(30,-60,100km,60km,5km,90) ->", attempt(30, -60, 100e3, 60e3, 5e3, angle_deg=90))
print("  from_center(0,-150,100km,100km,5km,-90) ->", attempt(0, -150, 100e3, 100e3, 5e3, angle_deg=-90))
gg = Grid(lenx=360.0, leny=160.0, resolution=10.0, cyclic_x=True, name="glob")
ds = gg.supergrid.to_ds()
g2 = Grid.from_supergrid_ds(ds, name="glob2")
print("  global 360 grid round-trip: cyclic_x =", g2.cyclic_x, "; supergrid.is_cyclic_x =", g2.supergrid.is_cyclic_x)
gr = Grid(lenx=4.0, leny=2.0, resolution=0.5, xstart=300.0, ystart=20.0, name="r")
print("  regional 4x2 deg grid: patched", _cyc(gr.supergrid), "orig", orig(gr.supergrid))
