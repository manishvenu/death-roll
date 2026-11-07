"""Sweep rotation angle and polar placement; suggestion only (no weights)."""
import warnings
import contextlib, io
from pathlib import Path

warnings.filterwarnings("ignore")
from mom6_forge import mapping
from mom6_forge.utils import get_avg_resolution_km
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo

OUT = Path(__file__).parent / "meshes_sweep"
OUT.mkdir(exist_ok=True)


def sugg(name, g):
    topo = Topo(g, min_depth=10.0, git=False)
    topo.set_flat(1000.0)
    p = OUT / f"{name}.nc"
    with contextlib.redirect_stdout(io.StringIO()):
        topo.write_esmf_mesh(str(p))
    return get_avg_resolution_km(str(p)), mapping.get_suggested_smoothing_params(str(p))


print("from_center 5 km, 20x20 (expected ~5 km -> (20, 40))")
for a in []:
    r, s = sugg(f"rot{a}", Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=a, name="x"))
    print(f"  angle {a:5d}: avg_res_km {r:8.3f} -> {s}")

print("from_center 5 km, 20x10 non-square")
for a in [0, 180]:  # 90 deg non-square raises cyclic_x AssertionError in Grid (separate bug)
    r, s = sugg(f"ns{a}", Grid.from_center(30.0, -60.0, 100e3, 50e3, 5e3, angle_deg=a, name="x"))
    print(f"  angle {a:5d}: avg_res_km {r:8.3f} -> {s}")

print("from_center fine resolution, rot 0")
for res in [500.0, 250.0, 199.0, 100.0]:
    r, s = sugg(f"fine{int(res)}", Grid.from_center(30.0, -60.0, 20 * res, 20 * res, res, name="x"))
    print(f"  {res:6.0f} m: avg_res_km {r:8.3f} -> {s}")

print("from_projection polar, 10 km, 20x20 (expected ~10 km -> (50, 100))")
for crs, x0, y0 in [("EPSG:3995", -100e3, -100e3), ("EPSG:3995", 0, 0), ("EPSG:3995", -200e3, 0),
                    ("EPSG:3031", -100e3, -100e3), ("EPSG:3031", 0, -200e3), ("EPSG:3031", -200e3, 0)]:
    r, s = sugg(f"pol{crs[-4:]}_{int(x0)}_{int(y0)}",
                Grid.from_projection(crs, x0, x0 + 200e3, y0, y0 + 200e3, 10e3, name="x"))
    print(f"  {crs} x0={x0:9.0f} y0={y0:9.0f}: avg_res_km {r:8.3f} -> {s}")
