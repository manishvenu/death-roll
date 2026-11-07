"""CrocoDash RunoffConfigurator with rmax/fold omitted, real mom6_forge mapping code.

Ocean mesh written the way Case does (topo.write_esmf_mesh). The runoff source mesh
is a tiny 0.5 deg lat-lon mesh standing in for GLOFAS (which is far too big for a
login node). Only xmlchange is stubbed (no CESM case here).
"""
import sys
import shutil
import warnings
import contextlib
import io
from pathlib import Path
from unittest.mock import patch

warnings.filterwarnings("ignore")
import numpy as np
import xarray as xr

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.forcing.base import WorkflowContext
from CrocoDash.forcing.runoff import RunoffConfigurator

HERE = Path(__file__).parent / "e2e"
shutil.rmtree(HERE, ignore_errors=True)
HERE.mkdir()

which = sys.argv[1]
if which == "beaufort":  # Arctic polar-stereographic domain in the Beaufort Sea
    grid = Grid.from_projection("EPSG:3995", -1000e3, -800e3, 1000e3, 1200e3, 10e3, name="beau")
elif which == "estuary150m":  # north-up estuary grid, 150 m cells
    grid = Grid.from_center(30.0, -60.0, 3e3, 3e3, 150.0, angle_deg=0.0, name="est")
elif which == "rot0_5km":  # control
    grid = Grid.from_center(30.0, -60.0, 100e3, 100e3, 5e3, angle_deg=0.0, name="ctl")
else:
    raise SystemExit("usage: beaufort|estuary150m|rot0_5km")

topo = Topo(grid, min_depth=10.0, git=False)
topo.set_flat(1000.0)
d = np.array(topo.depth)
d[:, :4] = 0.0  # land strip on the west edge so there is a coastline to map runoff to
topo.depth = d
ocn_mesh = HERE / "ocn_mesh.nc"
with contextlib.redirect_stdout(io.StringIO()):
    topo.write_esmf_mesh(str(ocn_mesh))

lon = grid.tlon.values
lat = grid.tlat.values
if which == "estuary150m":  # stand-in runoff mesh fine enough to overlap a 3 km box
    rof = Grid(lenx=0.04, leny=0.04, resolution=0.002, xstart=-60.02, ystart=29.98, name="rof")
else:
    x0, y0 = np.floor(lon.min()) - 1, np.floor(lat.min()) - 1
    rof = Grid(
        lenx=float(np.ceil(lon.max()) + 1 - x0), leny=float(min(np.ceil(lat.max()) + 1, 89.0) - y0),
        resolution=0.5, xstart=float(x0), ystart=float(y0), name="rof",
    )
rof_mesh = HERE / "rof_mesh.nc"
with contextlib.redirect_stdout(io.StringIO()):
    rof.supergrid.to_esmf_mesh(str(rof_mesh), mask="all_unmasked")
print(f"ocean grid {which}: {grid.nx}x{grid.ny}, lon [{lon.min():.2f},{lon.max():.2f}] lat [{lat.min():.2f},{lat.max():.2f}]")

cfg = RunoffConfigurator(
    case_grid_name=f"audit_{which}",
    case_session_id="v1",
    case_compset_lname="1850_DATM%JRA-1p5-2023_SLND_CICE_MOM6%REGIONAL_DROF%GLOFAS_SGLC_SWAV",
    case_inputdir=str(HERE),
    case_esmf_mesh_path=str(ocn_mesh),
    rmax=None,
    fold=None,
    rof_grid_name="r05",
    rof_esmf_mesh_filepath=str(rof_mesh),
)

xml = []
with patch("CrocoDash.forcing.base.xmlchange", lambda n, v, **k: xml.append((n, v))):
    cfg.configure()
print("configure(): rmax =", cfg.get_input_param("rmax"), " fold =", cfg.get_input_param("fold"))
for n, v in xml:
    print(f"  xmlchange {n} = {Path(v).name}")

ctx = WorkflowContext(
    inputdir=HERE, supergrid_path=HERE / "g.nc", vgrid_path=HERE / "v.nc", topo_path=HERE / "t.nc",
    raw_data_dir=HERE, regridded_data_dir=HERE, output_path=HERE, config={},
)
try:
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        cfg.process(ctx)
    print("process(): OK")
except Exception as e:
    print(f"process(): {type(e).__name__}: {e}")
print("  files in mapping/:", sorted(p.name for p in (HERE / "mapping").iterdir()))
