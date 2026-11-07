# Docstring example compsets lack %REGIONAL; does Case() accept them, and what domain type results?
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
lname = "1850_DATM%NYF_SLND_SICE_MOM6_SROF_SGLC_SWAV"   # NYF recipe from CLAUDE.md minus %REGIONAL
try:
    case = make("nonreg", compset=lname)
    show(case.caseroot, ids=("MOM6_DOMAIN_TYPE","COMPSET","OCN_GRID"))
except BaseException as e:
    print("RAISED:", type(e).__name__, str(e)[:300])
