# Case A created; a second Case() fails early (bad atm grid); then configure_forcings on A.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
A = make("first")
try:
    make("second", atm_grid_name="T63x")       # typo -> init_args_check raises after visualCaseGen was re-initialized
except Exception as e:
    print("second Case() failed as expected:", type(e).__name__, str(e)[:80])
try:
    A.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                         product_name="reference_ocean", function_name="get_reference_ocean_data")
    print("configure_forcings on A OK")
except BaseException as e:
    import traceback
    print("configure_forcings on A RAISED:", type(e).__name__, e)
    print(traceback.format_exc().splitlines()[-4:])
