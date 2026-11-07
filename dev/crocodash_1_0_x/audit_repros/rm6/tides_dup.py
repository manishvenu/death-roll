import sys, traceback
import sys; sys.path.insert(0, "/glade/u/home/manishrv/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS")
from pathlib import Path
from CrocoDash.shareable import duplicate_case
S = Path(sys.argv[1])
try:
    duplicate_case(S/"cases/audit_rm6_tide1", S/"cases/audit_rm6_tide1dup", S/"input/audit_rm6_tide1dup")
    print("DUPLICATE OK")
except Exception as e:
    traceback.print_exc()
