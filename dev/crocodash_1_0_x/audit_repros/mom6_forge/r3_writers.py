"""Write every grid file for a small grid and cross-check them."""
import numpy as np
import xarray as xr
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge.vgrid import VGrid
from mom6_forge._supergrid import haversine

out = Path("r3_out"); out.mkdir(exist_ok=True)
g = Grid(lenx=8.0, leny=6.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="w")
t = Topo(g, min_depth=10.0)
d = np.full((g.ny, g.nx), 500.0)
d[0, :2] = 0.0
d[3, 4] = 5.0  # shallower than min_depth
t.depth = d

g.write_supergrid(str(out / "hgrid.nc"))
t.write_topo(str(out / "topog.nc"))
t.write_scrip_grid(str(out / "scrip.nc"))
t.write_esmf_mesh(str(out / "mesh.nc"))
t.write_cice_grid(str(out / "cice.nc"))
t.write_ww3_input(str(out / "wav"), grid_alias="w")

hg = xr.open_dataset(out / "hgrid.nc")
tp = xr.open_dataset(out / "topog.nc")
sc = xr.open_dataset(out / "scrip.nc")
me = xr.open_dataset(out / "mesh.nc")
ci = xr.open_dataset(out / "cice.nc")

print("hgrid vars:", list(hg.data_vars), "angle_dx units", hg.angle_dx.attrs)
print("angle_dx range", float(hg.angle_dx.min()), float(hg.angle_dx.max()))
print("topog mask sum", int(tp.mask.sum()), "depth min ocean", float(tp.depth.where(tp.mask == 1).min()))
print("scrip imask sum", int(sc.grid_imask.sum()), "mesh mask sum", int(me.elementMask.sum()))
print("cice kmt sum", float(ci.kmt.sum()), ci.kmt.dims)
print("cice tlat units:", ci.tlat.attrs.get("units"), "value range", float(ci.tlat.min()), float(ci.tlat.max()))
print("cice ulat units:", ci.ulat.attrs.get("units"), float(ci.ulat.min()), float(ci.ulat.max()))
# htn should equal the north-edge length of each T cell (between NW and NE corners)
ql, qa = g.qlon.values, g.qlat.values
R = g.supergrid._R
htn_ref = R * np.cos(np.deg2rad(qa[1:, 1:])) * np.deg2rad(ql[1:, 1:] - ql[1:, :-1]) * 100
hte_ref = R * np.deg2rad(qa[1:, 1:] - qa[:-1, 1:]) * 100
print("htn max rel err", float(np.max(np.abs(ci.htn.values / htn_ref - 1))))
print("hte max rel err", float(np.max(np.abs(ci.hte.values / hte_ref - 1))))
# SCRIP area vs supergrid area
sg_area = g.supergrid.area.reshape(g.ny, 2, g.nx, 2).sum(axis=(1, 3)).ravel() / R**2
print("scrip grid_area vs supergrid area max rel err", float(np.max(np.abs(sc.grid_area.values / sg_area - 1))))
print("mesh elementArea vs supergrid", float(np.max(np.abs(me.elementArea.values / (sg_area * R**2) - 1))))
print("Grid.tarea vs supergrid block sum", float(np.max(np.abs(g.tarea.values.ravel() / (sg_area * R**2) - 1))))

# vgrid
v = VGrid.hyperbolic(10, 1000.0, 20.0, name="v")
v.write(str(out / "vgrid.nc"))
vv = xr.open_dataset(out / "vgrid.nc")
print("vgrid sum dz", float(vv.dz.sum()), "top/bottom", float(vv.dz[0]), float(vv.dz[-1]), "dz>0", bool((vv.dz > 0).all()))
v2 = VGrid.from_file(str(out / "vgrid.nc"))
print("vgrid round trip equal", np.allclose(v2.dz, v.dz))
# from cell centers / interfaces
vv2 = xr.Dataset({"zl": ("z", v.zl), "zi": ("zi", v.zi)})
vv2.to_netcdf(out / "vz.nc")
a = VGrid.from_file(str(out / "vz.nc"), "zl", "cell_center")
b = VGrid.from_file(str(out / "vz.nc"), "zi", "cell_interface")
print("from centers ok", np.allclose(a.dz, v.dz), "from interfaces ok", np.allclose(b.dz, v.dz))

# round trip hgrid
g2 = Grid.from_supergrid(str(out / "hgrid.nc"))
print("roundtrip tlon eq", np.array_equal(g2.tlon.values, g.tlon.values), "tarea eq", np.allclose(g2.tarea, g.tarea))
g3 = Grid.from_esmf_mesh(str(out / "mesh.nc"))
print("mesh roundtrip tlon eq", np.allclose(g3.tlon.values, g.tlon.values), np.allclose(g3.qlat.values, g.qlat.values))
for f in ["w_mapsta.inp", "w_bottom.inp"]:
    print(f, open(out / "wav" / f).read().splitlines()[0][:80])
