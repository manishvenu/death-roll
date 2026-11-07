# Writes one raw OBC chunk the way process_bc does (fetch_raw_chunk -> access method),
# big enough that a kill lands mid-write.
import sys
from pathlib import Path
from CrocoDash.raw_data_access.datasets.reference import REFERENCE_OCEAN
from CrocoDash.forcing import utils
out = Path(sys.argv[1])
print("writing", flush=True)
utils.fetch_raw_chunk(REFERENCE_OCEAN._access_methods["get_reference_ocean_data"].__func__,
    ["2020-01-01", "2020-01-30"], dict(lat_min=20.0, lat_max=30.0, lon_min=-60.0, lon_max=-50.0),
    out, "north_unprocessed.2020-01-01_2020-01-30.nc", ["u","v","ssh","temp","salt"], {"resolution_deg": 0.04}, name="north")
print("finished (should not get here)", flush=True)
