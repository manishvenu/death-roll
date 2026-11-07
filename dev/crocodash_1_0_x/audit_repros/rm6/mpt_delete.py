"""regional_mom6.MOM_parameter_tools: deleting a parameter."""
import traceback
from pathlib import Path
from regional_mom6 import MOM_parameter_tools as mpt
d = Path("mpt"); d.mkdir(exist_ok=True)
(d/"MOM_override").write_text("#override DT = 1800\n#override DT_THERM = 3600\n")
try:
    mpt.change_MOM_parameter(d, "DT", delete=True)          # no comment on the line
except Exception:
    traceback.print_exc()
(d/"MOM_override").write_text("#override DT = 1800 ! set by user\n#override DT_THERM = 18000 ! set by user\n")
mpt.change_MOM_parameter(d, "DT", delete=True)
print("after deleting DT:", repr((d/"MOM_override").read_text()))   # DT_THERM is gone too
