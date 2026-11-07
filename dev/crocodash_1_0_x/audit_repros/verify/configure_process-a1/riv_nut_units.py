"""Minimal repro: BGCRiverNutrientsConfigurator.process unit conversion.
No mocks: real xesmf bilinear regridder from a coarse synthetic global source
(shaped like river_nutrients.GNEWS_GNM.glofas.*.nc) onto a tiny mom6_forge grid.
Every *_riv_flux in the source is 1.0 nmol/cm^2/s, so every output should be
0.01 mmol/m^2/s."""
from pathlib import Path
import numpy as np, xarray as xr, cftime

from CrocoDash.grid import Grid
from CrocoDash.forcing.base import WorkflowContext
from CrocoDash.forcing.bgc import BGCRiverNutrientsConfigurator
from CrocoDash.raw_data_access.base import NOLEAP

here = Path(__file__).resolve().parent / "work"
here.mkdir(exist_ok=True)
for f in here.glob("*.nc"):
    f.unlink()

# --- synthetic source, same variable names/units as the GLADE file ---
lat = np.arange(-88.0, 89.0, 4.0)
lon = np.arange(-178.0, 179.0, 4.0)
LON2, LAT2 = np.meshgrid(lon, lat)
time = [cftime.DatetimeNoLeap(2000, 1, 1), cftime.DatetimeNoLeap(2001, 1, 1)]
FLUXES = ["din", "don", "dip", "dop", "dsi", "dfe", "dic", "alk", "doc"]
ds = xr.Dataset(coords={"lat": lat, "lon": lon, "time": time})
for n in FLUXES:
    v = f"{n}_riv_flux"
    ds[v] = (("time", "lat", "lon"), np.ones((2, lat.size, lon.size)))
    ds[v].attrs["units"] = "nmol/cm^2/s"
ds["LAT"] = (("lat", "lon"), LAT2)
ds["LON"] = (("lat", "lon"), LON2)
for v in ["xc", "yc", "area"]:
    ds[v] = (("lat", "lon"), np.zeros_like(LAT2))
for v in ["xv", "yv"]:
    ds[v] = (("lat", "lon", "nv"), np.zeros(LAT2.shape + (4,)))
src = here / "src_river_nutrients.nc"
ds.to_netcdf(src, encoding={"time": {"units": "days since 0001-01-01 00:00:00", "calendar": "noleap"}})

# --- tiny target grid (4x4 tracer cells) ---
grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=300.0, ystart=30.0, name="a1")

cfg = BGCRiverNutrientsConfigurator(
    global_river_nutrients_filepath=str(src),
    case_session_id="a1", case_grid_name="a1", calendar=NOLEAP,
)
cfg.set_output_param("RIV_FLUX_FILE", "river_nutrients_a1_nnsm.nc")  # what configure() sets (it also writes user_nl, which needs a CASEROOT)
ctx = WorkflowContext(
    inputdir=here, supergrid_path=here / "g.nc", vgrid_path=here / "v.nc",
    topo_path=here / "t.nc", raw_data_dir=here, regridded_data_dir=here,
    output_path=here,
    config={"runoff": {"outputs": {"ROF2OCN_LIQ_RMAPNAME": str(here / "weights_a1.nc")}}},
)
ctx.grid = grid

# Stand-in for the runoff mapping file the real flow passes as weights: build
# bilinear weights between the same two grids process() builds, and save them.
import xesmf as xe
srcg = xr.Dataset({"lon": ("lon", np.sort((lon + 360) % 360), {"units": "degrees"}),
                   "lat": ("lat", lat, {"units": "degrees"})})
dstg = xr.Dataset({"lon": grid.tlon, "lat": grid.tlat})
xe.Regridder(srcg, dstg, method="bilinear").to_netcdf(str(here / "weights_a1.nc"))

cfg.process(ctx)

out = xr.open_dataset(here / cfg.get_output_param("RIV_FLUX_FILE"))
print("output file:", here / cfg.get_output_param("RIV_FLUX_FILE"))
print("expected every flux = 0.01 mmol/m^2/s (1 nmol/cm^2/s * 0.01)")
for n in FLUXES:
    v = f"{n}_riv_flux"
    vals = np.unique(np.round(out[v].values, 10))
    print(f"  {v:14s} values={vals}  units attr={out[v].attrs.get('units')!r}")
