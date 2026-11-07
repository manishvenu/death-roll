# Variant: the second Case() fails inside visualCaseGen.initialize (bad cesmroot).
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
A = make("first2")
try:
    make("second2", cesmroot=Path("/glade/u/home/manishrv/work/installs/CESM_typo"))
except BaseException as e:
    print("second Case() failed as expected:", type(e).__name__, str(e)[:80])
try:
    A.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                         product_name="reference_ocean", function_name="get_reference_ocean_data")
    print("configure_forcings on A OK")
except BaseException as e:
    print("configure_forcings on A RAISED:", type(e).__name__, repr(e))
