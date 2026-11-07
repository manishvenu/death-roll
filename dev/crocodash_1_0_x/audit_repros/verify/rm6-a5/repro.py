"""rm6-a5: change_MOM_parameter(delete=True) misbehaviour. Pure file I/O, no data."""
import tempfile, traceback
from pathlib import Path
import regional_mom6, regional_mom6.MOM_parameter_tools as mpt
print("regional_mom6 from:", regional_mom6.__file__)

def run(label, content, steps):
    d = Path(tempfile.mkdtemp(dir="."))
    (d / "MOM_override").write_text(content)
    print(f"\n=== {label} ===\nbefore: {content!r}")
    try:
        for kw in steps:
            mpt.change_MOM_parameter(d, **kw)
    except Exception as e:
        print("EXCEPTION:", type(e).__name__, e)
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print("  at", Path(tb.filename).name, tb.lineno)
    print("after:  ", repr((d / "MOM_override").read_text()))

# 1. rm6's own shipped demo MOM_override (no comments); delete DT
run("A: demo file, delete DT", "#override DT=50\n#override DT_THERM=300\n",
    [dict(param_name="DT", delete=True)])
# 2. add with default comment=None via the same API, then delete it
run("B: add then delete via API", "#override DT=50\n",
    [dict(param_name="KH", param_value="100.0"), dict(param_name="KH", delete=True)])
# 3. commented lines: deleting DT also removes DT_THERM
run("C: commented, delete DT", "#override DT = 1800 ! set by user\n#override DT_THERM = 18000 ! set by user\n",
    [dict(param_name="DT", delete=True)])
# 4. plain (non-#override) line in MOM_override, as written by change_MOM_parameter(override=False)
run("D: plain line, delete FOO", "#override DT=50\n",
    [dict(param_name="FOO", param_value="1", override=False), dict(param_name="FOO", delete=True)])
