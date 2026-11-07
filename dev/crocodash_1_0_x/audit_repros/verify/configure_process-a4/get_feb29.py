"""GET side: CESM_MOM_OUTPUT.get_mom6_output_data with a Feb 29 bound, as CrocoDash builds it for
(a) the IC request of a case starting 2020-02-28 (ic.py: start + 1 day), and
(b) a 7-day GET chunk of a case starting 2020-02-02 (chunks ..., Feb 23 - Feb 29)."""
from pathlib import Path
from CrocoDash.forcing import ic, obc
from CrocoDash.raw_data_access.datasets.cesm_ocean_output import CESM_MOM_OUTPUT
import pandas as pd
S = Path(__file__).resolve().parent
print("IC dates for start 20200228:", ic.process_initial_condition(product_name="CESM_MOM_OUTPUT", function_name="get_mom6_output_data", variables=None, extra_args=None, dataset_varnames=None, start_date="20200228", hgrid_path=None, raw_data_dir=S/"x", output_data_dir=S/"x", regrid_fn=None, preview=True))
pairs = obc._make_date_pairs(pd.Timestamp("2020-02-02").to_pydatetime(), pd.Timestamp("2020-03-05").to_pydatetime(), 7)
print("GET pairs for start 20200202:", [(a.strftime('%m-%d'), b.strftime('%m-%d')) for a, b in pairs])
for dates in (["2020-02-28", "2020-02-29"], ["2020-02-23", "2020-02-29"]):
    try:
        CESM_MOM_OUTPUT.get_mom6_output_data(dates=dates, lat_min=30, lat_max=34, lon_min=-60, lon_max=-56,
            output_folder=S / "get_out", output_filename="x.nc", dataset_path=str(S / "parent"), preview=True)
        print(dates, "OK")
    except Exception as e:
        print(dates, "RAISED", type(e).__name__, e)
