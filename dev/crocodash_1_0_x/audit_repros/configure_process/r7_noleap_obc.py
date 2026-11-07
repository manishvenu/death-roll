"""R7: obc engine with a NO_LEAP product (as CESM_POP_OUTPUT/CESM_MOM_OUTPUT are)
over a leap year: a REGRID chunk ending on Feb 29 crashes."""
import shutil
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.forcing import obc, utils
from CrocoDash.grid import Grid

S = Path(__file__).parent / "r7"
if S.exists():
    shutil.rmtree(S)
S.mkdir()
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="r7")
grid.write_supergrid(S / "hgrid.nc")

def fake_noleap_access(dates, lat_min, lat_max, lon_min, lon_max, output_folder, output_filename, variables, name=None, **kw):
    # Daily noleap records over [dates[0], dates[1]], like a CESM day_1 tseries subset.
    t = xr.date_range(dates[0], dates[1], freq="D", calendar="noleap", use_cftime=True)
    ds = xr.Dataset({"temp": ("time", np.arange(len(t), dtype=float))}, coords={"time": t})
    ds.to_netcdf(Path(output_folder) / output_filename)

utils.get_data_access_function = lambda p, f: fake_noleap_access

def regrid_chunk(ds, hgrid, boundary, seg_id, outfolder, dataset_varnames, start_date, regridders):
    ds.to_netcdf(Path(outfolder) / f"forcing_obc_segment_{seg_id:03d}.nc")
    return regridders

try:
    obc.process_obc_conditions(
        start_date="20200101", end_date="20200305",
        boundary_number_conversion={"north": 1},
        product_name="FAKE_NOLEAP", function_name="get", variables=[], extra_args={},
        dataset_varnames={}, hgrid_path=S / "hgrid.nc",
        raw_dataset_path=S / "raw", regridded_dataset_path=S / "regridded", output_path=S / "out",
        regrid_chunk_fn=regrid_chunk, get_step_days=7, regrid_step_days=30)
    print("OK")
except Exception as e:
    print("RAISED", type(e).__name__, e)
print("raw:", sorted(p.name for p in (S / "raw").glob("*.nc")))
print("regridded:", sorted(p.name for p in (S / "regridded").glob("*.nc")))
