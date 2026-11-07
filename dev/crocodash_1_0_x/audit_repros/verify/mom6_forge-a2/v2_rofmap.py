"""Verify the user-visible effect: runoff nn map (gen_rof_maps, the call CrocoDash's runoff
forcing makes in process_forcings) on a rotated from_center grid, with and without a
monkeypatched get_mesh_dimensions that trusts the connectivity-derived nx."""
import sys, warnings, shutil
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np
import xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
from mom6_forge import utils, mapping, _supergrid

out = Path(__file__).parent / "out2"
if out.exists():
    shutil.rmtree(out)
out.mkdir()

ORIG = utils.get_mesh_dimensions


def fixed_get_mesh_dimensions(mesh):
    """Same connectivity walk, but no lon/lat swap heuristic for mom6_forge meshes."""
    if not isinstance(mesh, xr.Dataset):
        mesh = xr.open_dataset(mesh)
    if "grid_topology" not in mesh.attrs:
        return ORIG(mesh)
    econn = mesh["elementConn"].values
    e0 = econn[0]
    for i in range(2, len(econn)):
        if len(np.intersect1d(econn[i], e0)) == 2:
            nx = i + 1 if (i < len(econn) - 1 and len(np.intersect1d(econn[i + 1], e0)) == 2) else i
            break
    return nx, len(mesh["centerCoords"]) // nx


def patch(fn):
    for mod in (utils, mapping, _supergrid):
        mod.get_mesh_dimensions = fn


def true_coast(m):
    ny, nx = m.shape
    c = np.zeros_like(m)
    for j in range(ny):
        for i in range(nx):
            if m[j, i] and any(
                0 <= j + dj < ny and 0 <= i + di < nx and m[j + dj, i + di] == 0
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                c[j, i] = 1
    return c


angle = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
g = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=angle, name="rot")
ny, nx = g.tlon.shape
t = Topo(g, min_depth=10.0, git=False)
d = np.full((ny, nx), 1000.0)
d[:, :3] = 0.0  # land strip on columns i=0..2 -> real coast is column i=3
t.depth = d
tmask = t.tmask.data.astype(int)
tc = true_coast(tmask)
ocn_mesh = out / "ocn_mesh.nc"
t.write_esmf_mesh(str(ocn_mesh))

# Small synthetic lat-lon runoff mesh covering the ocean domain (all cells active)
lo0, lo1 = float(g.qlon.min()) - 0.5, float(g.qlon.max()) + 0.5
la0, la1 = float(g.qlat.min()) - 0.5, float(g.qlat.max()) + 0.5
rg = Grid(lenx=lo1 - lo0, leny=la1 - la0, resolution=0.1, xstart=lo0, ystart=la0, name="rof")
rt = Topo(rg, min_depth=0.0, git=False)
rt.set_flat(10.0)
rof_mesh = out / "rof_mesh.nc"
rt.write_esmf_mesh(str(rof_mesh))

print(f"angle={angle} ocean grid (ny,nx)=({ny},{nx}); ocean cells={tmask.sum()}; true coast cells={tc.sum()}")
print(f"suggested (rmax, fold) km = {mapping.get_suggested_smoothing_params(str(ocn_mesh))}")
print(f"get_mesh_dimensions(ocn) = {utils.get_mesh_dimensions(str(ocn_mesh))}")
for label, fn in (("AS-IS", ORIG), ("PATCHED", fixed_get_mesh_dimensions)):
    patch(fn)
    od = out / label
    mapping.gen_rof_maps(str(rof_mesh), str(ocn_mesh), od, "rof_to_ocn", rmax=None, fold=None)
    nn = xr.open_dataset(mapping.get_nn_map_filepath("rof_to_ocn", od))
    rows = np.unique(nn.row.values[nn.S.values != 0] - 1)
    recv = np.zeros(ny * nx, int)
    recv[rows] = 1
    recv = recv.reshape(ny, nx)
    not_coast = int(((recv == 1) & (tc == 0)).sum())
    print(
        f"[{label}] nn map: ocean cells receiving runoff={recv.sum()} "
        f"(not adjacent to land: {not_coast}); nj_b,ni_b in file = {nn.sizes['nj_b']},{nn.sizes['ni_b']}; "
        f"suggested (rmax,fold)={mapping.get_suggested_smoothing_params(str(ocn_mesh))}"
    )
    # columns that receive runoff (true layout)
    print(f"[{label}] receiving cells per true column i: {recv.sum(axis=0).tolist()}")
patch(ORIG)
