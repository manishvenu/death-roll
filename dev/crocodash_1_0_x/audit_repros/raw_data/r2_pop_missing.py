import sys, shutil
from pathlib import Path
import xarray as xr
sys.path.insert(0, str(Path(__file__).parent))
from mkpop import make
from CrocoDash.forcing import utils
from CrocoDash.raw_data_access.registry import ProductRegistry
ProductRegistry.load()
S = Path(sys.argv[1]); shutil.rmtree(S, ignore_errors=True)
src = make(S/"src")
fn = utils.get_data_access_function("CESM_POP_OUTPUT", "get_cesm_single_variable_data")
box = dict(lat_min=24.0, lat_max=26.0, lon_min=275.0, lon_max=278.0)
vars_ = ["UVEL","VVEL","SSH","TEMP","SALT"]
print("=== (a) dates outside the archive (2005) ===")
out = utils.fetch_raw_chunk(fn, ["2005-01-01","2005-01-02"], box, S/"raw_a", "ic_unprocessed.nc", vars_, {"dataset_path": str(src)}, name="ic")
print("fetch_raw_chunk returned", out, "exists:", out.exists())
print("=== (b) SSH files missing from the archive ===")
for f in src.glob("*.SSH.*"): f.unlink()
out = utils.fetch_raw_chunk(fn, ["2000-03-01","2000-03-02"], box, S/"raw_b", "ic_unprocessed.nc", vars_, {"dataset_path": str(src)}, name="ic")
ds = xr.open_dataset(out, decode_times=False)
print("fetch_raw_chunk returned", out, "exists:", out.exists(), "data vars:", sorted(ds.data_vars))
