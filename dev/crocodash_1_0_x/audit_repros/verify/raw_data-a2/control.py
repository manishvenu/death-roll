import json, copy, xarray as xr
from datetime import datetime
from pathlib import Path
from CrocoDash.forcing.mom6 import _regrid_obc_chunk
R = Path(__file__).resolve().parent / "run/input/audit_verify_a2_nest"
raw = xr.open_dataset(R / "extract_forcings/raw_data/south_unprocessed.2020-02-27_2020-03-02.nc")
cfg = json.loads((R / "extract_forcings/config.json").read_text())
def find(d):
    if isinstance(d, dict):
        if "u_var_name" in d and "calendar" in d: return d
        for v in d.values():
            r = find(v)
            if r: return r
info = find(cfg)
hgrid = xr.open_dataset(next(R.rglob("ocean_hgrid*.nc")))
base = Path(__file__).resolve().parent / "run"
# control 1: noleap product calendar, window without Feb 29
o1 = base / "ctl_noleap_mar"; o1.mkdir(exist_ok=True)
_regrid_obc_chunk(raw.sel(time=slice("2020-03-01", "2020-03-02")), hgrid, "south", 1, o1, info, datetime(2020, 3, 1), None)
d = xr.open_dataset(o1 / "forcing_obc_segment_001.nc", decode_times=False)
print("noleap, Mar window: OK time", d.time.values, d.time.attrs)
# fix check: gregorian calendar (what the parent ran), window with Feb 29
info2 = copy.deepcopy(info); info2["calendar"] = {"cf": "standard", "cesm": "GREGORIAN", "mom6": "gregorian"}
o2 = base / "fix_gregorian"; o2.mkdir(exist_ok=True)
_regrid_obc_chunk(raw, hgrid, "south", 1, o2, info2, datetime(2020, 2, 27), None)
d = xr.open_dataset(o2 / "forcing_obc_segment_001.nc", decode_times=False)
print("gregorian, Feb27-Mar2 window: OK time", d.time.values, d.time.attrs)
