# Second Case() in a process with a different cesmroot sees the first root's compsets.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
from visualCaseGen.initialize import initialize
B = Path("/glade/u/home/manishrv/work/installs/CESM_wu2r05")
if sys.argv[1] == "after_A":
    initialize(CESMROOT)        # as if a CESM_crocodash case had been created earlier in this kernel
cime = initialize(B)
print("CR_JRA_GLOFAS in cime.compsets for", B.name, "->", "CR_JRA_GLOFAS" in cime.compsets)
try:
    make("tworoot", cesmroot=B, compset="CR_JRA_GLOFAS")
except BaseException as e:
    print("RAISED:", type(e).__name__, e)
