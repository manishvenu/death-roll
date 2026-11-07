# Two CESM roots in one process: is the second CIME_interface read from the second tree?
import sys
from visualCaseGen.initialize import initialize
A = "/glade/u/home/manishrv/work/installs/CESM_crocodash"
B = "/glade/u/home/manishrv/work/installs/CESM_wu2r05"
for root in (A, B):
    cime = initialize(root)
    import CIME
    print("requested", root)
    print("  cime.cimeroot     =", cime.cimeroot)
    print("  CIME module from  =", CIME.__file__)
    print("  CONFIG_CPL_FILE   =", cime._files.get_value("CONFIG_CPL_FILE"))
    print("  MACHINES_SPEC_FILE=", cime._files.get_value("MACHINES_SPEC_FILE"))
    print("  cime_output_root  =", cime.cime_output_root)
print("sys.path cime entries:", [p for p in sys.path if p.endswith("/cime")])
