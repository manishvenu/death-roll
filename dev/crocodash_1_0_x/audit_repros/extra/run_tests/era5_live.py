import sys, time
from pathlib import Path
from CrocoDash.raw_data_access.datasets.era5 import ERA5_WAVE_SPECTRA as P, build_era5_spectra_request
req = build_era5_spectra_request(["2019-06-05", "2019-06-05"], 40.0, 44.0, -60.0, -56.0)
print("REQUEST", req, flush=True)
t = time.time()
out = P.get_era5_2d_spectra(["2019-06-05", "2019-06-05"], 40.0, 44.0, -60.0, -56.0, output_folder=Path(sys.argv[1]), output_filename="era5_spectra.nc")
print("DONE", out, round(time.time() - t), "s", flush=True)
import xarray as xr; ds = xr.open_dataset(out); print(ds); 
