import sys, warnings
from pathlib import Path
import numpy as np, xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge.vgrid import VGrid
D = Path(sys.argv[1])
print("== 6: lenx not a multiple of resolution")
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    g = Grid(lenx=4.3, leny=3.7, resolution=0.5, xstart=-60.0, ystart=30.0, name="odd")
    print("  shape", g.tlon.shape, "qlon span", float(g.qlon.max()-g.qlon.min()), "qlat span", float(g.qlat.max()-g.qlat.min()),
          "dlon", float(g.qlon[0,1]-g.qlon[0,0]), "warnings:", [str(x.message)[:80] for x in w])
print("== 7: VGrid dz sums and file round trip")
for name, vg in [("uniform", VGrid.uniform(nk=10, depth=1000.0, name="u")), ("hyperbolic", VGrid.hyperbolic(nk=20, depth=4000.0, ratio=10.0, name="h"))]:
    dz = np.asarray(vg.dz); print(f"  {name}: sum={dz.sum():.6f} min={dz.min():.3f} max={dz.max():.3f} monotonic={bool(np.all(np.diff(dz)>=0))}")
    f = D/"mf"/f"vg_{name}.nc"
    try:
        vg.write(f) if hasattr(vg, "write") else vg.write_z_file(f)
    except Exception as e:
        print("   write:", type(e).__name__, str(e)[:100]); continue
    ds = xr.open_dataset(f); print("   file vars", {v: float(ds[v].sum()) for v in ds.data_vars}); ds.close()
    try:
        vg2 = VGrid.from_file(f); print("   reread dz equal:", np.allclose(np.asarray(vg2.dz), dz))
    except Exception as e:
        print("   from_file:", type(e).__name__, str(e)[:120])
print("== 8: set_from_dataset with a 0..360 source on a negative-longitude domain")
lon = np.arange(280.0, 320.0, 0.05); lat = np.arange(20.0, 40.0, 0.05)
elev = -(1000.0 + (lon[None, :] - 280.0) * 50.0 + 0.0 * lat[:, None])  # depth grows eastward: 2000 m at 300E (-60)
src = xr.Dataset({"elevation": (("lat", "lon"), elev)}, coords={"lon": lon, "lat": lat})
src.to_netcdf(D/"mf"/"bathy360.nc")
g = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="b360")
t = Topo(g, min_depth=10.0)
t.set_from_dataset(bathymetry_path=str(D/"mf"/"bathy360.nc"), longitude_coordinate_name="lon", latitude_coordinate_name="lat",
                   vertical_coordinate_name="elevation", output_dir=D/"mf")
exp = 1000.0 + ((np.asarray(g.tlon) % 360) - 280.0) * 50.0
got = np.asarray(t.depth)
print("  expected west/east", exp[0, 0], exp[0, -1], "got", got[0, 0], got[0, -1], "max abs err", float(np.nanmax(np.abs(got - exp))))
