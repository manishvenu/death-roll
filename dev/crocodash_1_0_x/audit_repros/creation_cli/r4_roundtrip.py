import os, sys, json, yaml, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from CrocoDash.recipe import case_to_yaml, create_case_from_yaml
(D/"cases4").mkdir(exist_ok=True); (D/"inputs4").mkdir(exist_ok=True)
A = D/"cases4/audit_ccl_r4a"; IA = D/"inputs4/audit_ccl_r4a"
grid, topo, vgrid = objs("ccr4")
topo2 = Topo(grid, min_depth=25.0); topo2.set_flat(1000.0)
case = Case(cesmroot=CESMROOT, caseroot=A, inputdir=IA, compset=NYF, ocn_grid=grid, ocn_topo=topo2,
            ocn_vgrid=vgrid, atm_grid_name="T62", machine="derecho", project="ncgd0011", override=True,
            job_wallclock_time="01:30:00", job_queue="develop")
case.configure_forcings(date_range=["2020-01-01 12:00:00", "2020-01-04 00:00:00"], boundaries=["north", "west"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data",
                        function_overrides={"resolution_deg": 0.25})
cfgA = json.load(open(IA/"extract_forcings/config.json"))
y = case_to_yaml(A)
txt = yaml.dump(y, default_flow_style=False, sort_keys=False)
print("DUMP:\n" + txt)
y2 = yaml.safe_load(txt)
y2["case"]["caseroot"] = str(D/"cases4/audit_ccl_r4b"); y2["case"]["inputdir"] = str(D/"inputs4/audit_ccl_r4b")
caseB = create_case_from_yaml(y2, override=True, configure_only=True)
stA = json.load(open(A/"_crocodash_state.json")); stB = json.load(open(D/"cases4/audit_ccl_r4b/_crocodash_state.json"))
for k in stA:
    if stA[k] != stB.get(k): print("STATE DIFF", k, stA[k], "->", stB.get(k))
cfgB = json.load(open(D/"inputs4/audit_ccl_r4b/extract_forcings/config.json"))
for sec in cfgA:
    if isinstance(cfgA[sec], dict) and "inputs" in cfgA[sec]:
        for k, v in cfgA[sec]["inputs"].items():
            if cfgB[sec]["inputs"].get(k) != v: print("CONFIG DIFF", sec, k, v, "->", cfgB[sec]["inputs"].get(k))
print("topo min_depth A:", topo2.min_depth, "B:", caseB.ocn_topo.min_depth)
import xarray as xr
ta = xr.open_dataset(stA["topo_path"]); tb = xr.open_dataset(stB["topo_path"])
print("topo depth equal:", bool((ta.depth.values == tb.depth.values).all()), "attrs A:", dict(ta.attrs), "B:", dict(tb.attrs))
for f in ("user_nl_mom",):
    la = [l for l in open(A/f) if not l.startswith("!") and "_ccr4_" not in l]; lb = [l for l in open(D/"cases4/audit_ccl_r4b"/f) if not l.startswith("!") and "_ccr4_" not in l]
    print(f, "lines only in A:", [l.strip() for l in la if l not in lb][:10]); print(f, "lines only in B:", [l.strip() for l in lb if l not in la][:10])
import re
def xml(case, var):
    for fn in Path(case).glob("env_*.xml"):
        m = re.search(rf'id="{var}"[^>]*>.*?<value[^>]*>([^<]*)</value>', open(fn).read(), re.S)
        if m: return m.group(1)
for v in ("RUN_STARTDATE", "STOP_N", "JOB_WALLCLOCK_TIME", "CALENDAR"):
    print("XML", v, xml(A, v), xml(D/"cases4/audit_ccl_r4b", v))
