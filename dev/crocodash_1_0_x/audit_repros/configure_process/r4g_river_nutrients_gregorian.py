"""R4: BGCRiverNutrients unit conversion. Every source flux = 1.0 nmol/cm^2/s;
expected 0.01 mmol/m^2/s for every flux MOM6's MARBL_tracers.F90 reads."""
from pathlib import Path
from types import SimpleNamespace
import numpy as np, xarray as xr, cftime
from unittest.mock import MagicMock
import CrocoDash.forcing.bgc as bgc
from CrocoDash.forcing.bgc import BGCRiverNutrientsConfigurator
from CrocoDash.raw_data_access.base import Calendar
import dataclasses

S = Path(__file__).parent / "r4g"
S.mkdir(exist_ok=True)
ny, nx = 3, 4
lat = np.linspace(20, 25, ny); lon = np.linspace(-10, 10, nx)
time = [cftime.DatetimeNoLeap(1950 + i, 1, 1) for i in range(2)]
# names MOM6 reads (MARBL_tracers.F90 init_external_field) + extras in the real file
flux_vars = ["din", "dip", "don", "dop", "dsi", "dfe", "dic", "alk", "doc"]
dv = {f"{v}_riv_flux": (("time", "lat", "lon"), np.ones((2, ny, nx))) for v in flux_vars}
for v in ("LAT", "LON", "xc", "xv", "yc", "yv", "area"):
    dv[v] = (("lat", "lon"), np.zeros((ny, nx)))
src = xr.Dataset(dv, coords={"lat": lat, "lon": lon, "time": time})
src.to_netcdf(S / "src.nc")

# identity "regridder": same values, on the model's (ny, nx) dims
def fake_regrid(ds):
    out = {}
    for v in ds.data_vars:
        d = ds[v]
        out[v] = (("time", "ny", "nx") if "time" in d.dims else ("ny", "nx"), d.values)
    return xr.Dataset(out, coords={"time": ds.time.values})
bgc.xe.Regridder = MagicMock(return_value=fake_regrid)

grid = SimpleNamespace(
    tlon=xr.DataArray(np.broadcast_to(lon, (ny, nx)).copy(), dims=("ny", "nx")),
    tlat=xr.DataArray(np.broadcast_to(lat[:, None], (ny, nx)).copy(), dims=("ny", "nx")),
)
from CrocoDash.raw_data_access.base import GREGORIAN as NOLEAP
cal = dataclasses.asdict(NOLEAP)
conf = BGCRiverNutrientsConfigurator(global_river_nutrients_filepath=str(S / "src.nc"),
                                     case_session_id="x", case_grid_name="g", calendar=cal)
conf.set_output_param("RIV_FLUX_FILE", "riv.nc")
ctx = SimpleNamespace(grid=grid, output_path=S, config={"runoff": {"outputs": {"ROF2OCN_LIQ_RMAPNAME": str(S / "map.nc")}}})
conf.process(ctx)
out = xr.open_dataset(S / "riv.nc", decode_times=False)
for v in flux_vars:
    n = f"{v}_riv_flux"
    print(f"{n:15s} value={float(out[n].isel(time=1).mean()):.4g}  units={out[n].attrs.get('units')}")
