import sys, numpy as np, xarray as xr
from pathlib import Path
from CrocoDash.recipe import case_to_yaml, create_case_from_yaml, build_grid
S = Path(sys.argv[1]); src = S/"cases/audit_pol_arc"
cfg = case_to_yaml(src)
print("grid cfg", cfg["grid"]); print("forcings keys", list(cfg.get("forcings", {}).keys()))
g2 = build_grid(cfg["grid"])
hg = xr.open_dataset(cfg["grid"]["supergrid_path"])
print("rebuilt grid", g2.nx, g2.ny, "| max |tlon diff|", float(np.abs(((g2.tlon.values - hg.x.values[1::2, 1::2]) + 180) % 360 - 180).max()),
      "| max |tlat diff|", float(np.abs(g2.tlat.values - hg.y.values[1::2, 1::2]).max()))
cfg["case"]["caseroot"] = str(S/"cases/audit_pol_arc2"); cfg["case"]["inputdir"] = str(S/"input/audit_pol_arc2")
case = create_case_from_yaml(cfg, override=True, configure_only=True)
import subprocess
for v in ["OCN_NX", "OCN_NY", "STOP_N", "RUN_STARTDATE", "CALENDAR"]:
    a = subprocess.run(["./xmlquery", v, "--value"], cwd=src, capture_output=True, text=True).stdout.strip()
    b = subprocess.run(["./xmlquery", v, "--value"], cwd=S/"cases/audit_pol_arc2", capture_output=True, text=True).stdout.strip()
    print("XML", v, a, "->", b, "" if a == b else "  <-- DIFFERS")
c1 = json_cfg = (S/"input/audit_pol_arc/extract_forcings/config.json").read_text()
c2 = (S/"input/audit_pol_arc2/extract_forcings/config.json").read_text()
import json, difflib
d = [l for l in difflib.unified_diff(json.dumps(json.loads(c1), indent=1, sort_keys=True).splitlines(), json.dumps(json.loads(c2), indent=1, sort_keys=True).splitlines(), lineterm="", n=0) if l.startswith(("+ ", "- ", "+\t", "-\t", "+ ", "-  ", "+  "))]
print("config.json diff lines:", len(d)); print("\n".join(d[:30]))
t1 = xr.open_dataset(next((S/"input/audit_pol_arc/ocn").glob("ocean_topog_*.nc"))).depth.values
t2 = xr.open_dataset(next((S/"input/audit_pol_arc2/ocn").glob("ocean_topog_*.nc"))).depth.values
print("topo identical:", bool(np.array_equal(t1, t2)), "ocean cells", int((t1 > 0).sum()), int((t2 > 0).sum()))
