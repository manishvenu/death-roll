# Case(machine=None): docstring says default None and __init__ has `machine or self.cime.machine`,
# but init_args_check gets the raw None first.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
from visualCaseGen.initialize import initialize
cime = initialize(CESMROOT)
print("cime.machine detected =", cime.machine)
try:
    make("mach", machine=None)
except Exception as e:
    print("RAISED:", type(e).__name__, e)
