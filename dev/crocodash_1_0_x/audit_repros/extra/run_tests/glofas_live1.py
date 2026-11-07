import sys, time, zipfile
from pathlib import Path
from CrocoDash.raw_data_access.datasets.glofas import GLOFAS
t = time.time()
p = GLOFAS.get_global_data_with_python(["2020-01-15", "2020-01-15"], output_folder=Path(sys.argv[1]), output_filename="glofas_data.nc")
print("RETURNED", p, Path(p).stat().st_size, "bytes", round(time.time() - t), "s", flush=True)
print("is zip:", zipfile.is_zipfile(p))
import xarray as xr
try:
    xr.open_dataset(p); print("xr.open_dataset OK on returned path")
except Exception as e:
    print("xr.open_dataset FAILED:", type(e).__name__, str(e)[:200])
if zipfile.is_zipfile(p):
    z = zipfile.ZipFile(p); print("zip members:", z.namelist())
    out = Path(sys.argv[1]) / "unz"; z.extractall(out)
    for f in sorted(out.glob("*.nc")):
        ds = xr.open_dataset(f); tv = [v for v in ds.coords if "time" in v]
        print(f.name, dict(ds.sizes), {v: [str(x)[:10] for x in ds[v].values] for v in tv})
