import sys
from visualCaseGen.cime_interface import CIME_interface
try:
    CIME_interface(cesmroot=sys.argv[1])
except BaseException as e:
    print("RAISED:", type(e).__name__, e)
