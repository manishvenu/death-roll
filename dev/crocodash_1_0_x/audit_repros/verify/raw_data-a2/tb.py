import json, traceback, xarray as xr
from datetime import datetime
from pathlib import Path
from CrocoDash.forcing.mom6 import _regrid_obc_chunk
R = Path(__file__).resolve().parent / "run/input/audit_verify_a2_nest"
raw = xr.open_dataset(R / "extract_forcings/raw_data/south_unprocessed.2020-02-27_2020-03-02.nc")
print("raw time:", [str(x)[:19] for x in raw.time.values], raw.time.encoding.get("calendar"))
cfg = json.loads((R / "extract_forcings/config.json").read_text())
def find(d):
    if isinstance(d, dict):
        if "u_var_name" in d and "calendar" in d: return d
        for v in d.values():
            r = find(v)
            if r: return r
info = find(cfg); print("config.json product calendar:", info["calendar"], "time_units:", info["time_units"])
from mom6_forge.grid import Grid
import xarray as xr
hgrid = xr.open_dataset(next((R/"ocnice").glob("ocean_hgrid*.nc")) if (R/"ocnice").exists() else next(R.rglob("ocean_hgrid*.nc")))
out = Path(__file__).resolve().parent / "run/tb_out"; out.mkdir(exist_ok=True)
try:
    _regrid_obc_chunk(raw, hgrid, "south", 1, out, info, datetime(2020, 2, 27), None)
except Exception:
    tb = traceback.format_exc().splitlines()
    print("\n".join(l for l in tb if "File " in l and ("CrocoDash" in l or "regional_mom6" in l)))
    print(tb[-1])
