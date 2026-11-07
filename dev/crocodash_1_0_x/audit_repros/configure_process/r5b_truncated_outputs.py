"""R5b: truncated final outputs (killed MERGE / IC fill) are accepted on resume."""
from pathlib import Path
import xarray as xr
from CrocoDash.forcing import obc, mom6
S = Path(__file__).parent / "r5"
ocn = Path(__file__).parent / "input/audit_cp_1/ocn"
for name in ("forcing_obc_segment_001.nc", "init_tracers_filled.nc"):
    data = (ocn / name).read_bytes()
    (S / name).write_bytes(data[: len(data) // 2])
print("merge returns:", obc._merge_boundary("001", [], S).name)  # skipped, no error
print("IC _all_written:", mom6._all_written([S / "init_tracers_filled.nc"]))
try:
    xr.open_dataset(S / "forcing_obc_segment_001.nc").load()
except Exception as e:
    print("reading the 'merged' file:", type(e).__name__, str(e)[:90])
