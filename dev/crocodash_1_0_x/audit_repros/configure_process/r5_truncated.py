"""R5: a raw OBC chunk truncated by a killed run is reused on resume."""
import shutil, os
from pathlib import Path
import xarray as xr
from CrocoDash.forcing import utils
S = Path(__file__).parent / "r5"
src = Path(__file__).parent / "input/audit_cp_1/extract_forcings/raw_data/north_unprocessed.2020-02-27_2020-03-02.nc"
for fmt in ("NETCDF4", "NETCDF3_64BIT"):
    full = S / f"full_{fmt}.nc"
    xr.open_dataset(src).load().to_netcdf(full, format=fmt)
    part = S / f"north_unprocessed.2020-02-27_2020-03-02_{fmt}.nc"
    data = full.read_bytes()
    part.write_bytes(data[: len(data) // 2])   # what a killed write leaves
    print(fmt, "size", len(data), "-> is_valid_netcdf:", utils.is_valid_netcdf(part))
    calls = []
    out = utils.fetch_raw_chunk(lambda **k: calls.append(k), ["2020-02-27", "2020-03-02"],
                                dict(lat_min=0, lat_max=1, lon_min=0, lon_max=1), S, part.name, [], {}, name="north")
    print("  fetch_raw_chunk re-downloaded:", bool(calls))
    try:
        ds = xr.open_dataset(part); v = ds["temp"].values; print("  read OK; NaNs:", int(xr.DataArray(v).isnull().sum()), "zeros:", int((v == 0).sum()), "of", v.size)
    except Exception as e:
        print("  read error:", type(e).__name__, str(e)[:200])
