# Step 2 (fresh process, as the CLI is): CaseBundle diff against a reference case.
# The reference case CrocoDash makes is named temp_case-<uuid>; to keep the audit's
# "audit_" naming rule, create_case_from_yaml is wrapped to build it at
# cases/audit_v_a5_ref and symlink the temp path to it. Nothing else is patched.
import argparse, shutil, traceback
from pathlib import Path
import CrocoDash.shareable as sh
from CrocoDash import cli

S = Path(__file__).resolve().parent
SRC = S / "cases/audit_v_a5_src"
REF = S / "cases/audit_v_a5_ref"
CESM = Path("~/work/installs/CESM_crocodash").expanduser()

_orig = sh.create_case_from_yaml


def _wrapped(config, **kw):
    tmp_caseroot = Path(config["case"]["caseroot"])
    config["case"]["caseroot"] = str(REF)
    config["case"]["inputdir"] = str(S / "inputs/audit_v_a5_ref")
    r = _orig(config, **kw)
    tmp_caseroot.symlink_to(REF)
    return r


sh.create_case_from_yaml = _wrapped

nl_cpl = SRC / "user_nl_cpl"
nl_mom = SRC / "user_nl_mom"
cpl0, mom0 = nl_cpl.read_text(), nl_mom.read_text()


def restore():
    nl_cpl.write_text(cpl0)
    nl_mom.write_text(mom0)


def run(label, fn):
    print(f"\n===== {label}", flush=True)
    try:
        out = fn()
        print("OK ->", out, flush=True)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"RAISED {type(e).__name__}: {e!s}  at {Path(tb.filename).name}:{tb.lineno} in {tb.name}: {tb.line}", flush=True)


# 0. control, full CLI bundle path (identify_non_standard_case_info + bundle), no user edits
args = argparse.Namespace(caseroot=str(SRC), cesmroot=str(CESM), machine="derecho",
                          project="ncgd0011", output_dir=str(S / "bundles"))
run("control: identify_non_standard_case_info (what `crocodash bundle` runs first), unedited case",
    lambda: sh.CaseBundle(SRC).identify_non_standard_case_info(str(CESM), "derecho", "ncgd0011"))
print("ref user_nl_cpl parsed:", sh.CaseBundle(REF).user_nl_objs.get("cpl"))
print("ref user_nl_mom modules:", list(sh.CaseBundle(REF).user_nl_objs["mom"].keys()))

ref = sh.CaseBundle(REF)

# 1. a global user_nl_mom param the reference lacks -> should be reported (works)
restore()
nl_mom.write_text(mom0 + "\nHFREEZE = 10.0\n")
run("user_nl_mom global param HFREEZE", lambda: sh.CaseBundle(SRC).diff(ref).user_nl_missing_params)

# 2. a line in user_nl_cpl (empty in the reference)
restore()
nl_cpl.write_text(cpl0 + "\norb_iyear = 1990\n")
run("user_nl_cpl orb_iyear = 1990", lambda: sh.CaseBundle(SRC).diff(ref).user_nl_missing_params)

# 3. a MOM parameter block (KPP%) the reference lacks
restore()
nl_mom.write_text(mom0 + "\nKPP%\nN_SMOOTH = 2\n%KPP\n")
run("user_nl_mom KPP% block", lambda: sh.CaseBundle(SRC).diff(ref).user_nl_missing_params)

# 3b. the same block parameter in prefixed form (new reader only)
restore()
nl_mom.write_text(mom0 + "\nKPP%N_SMOOTH = 2\n")
run("user_nl_mom KPP%N_SMOOTH prefixed", lambda: sh.CaseBundle(SRC).diff(ref).user_nl_missing_params)

# 4. full CLI bundle path and duplicate_case path with the cpl edit
restore()
nl_cpl.write_text(cpl0 + "\norb_iyear = 1990\n")
shutil.rmtree(S / "bundles", ignore_errors=True)
run("`crocodash bundle` path, user_nl_cpl edited", lambda: cli._bundle(args))

# 5. proposed fix monkeypatched: .get(...) with defaults
def fixed_diff(self, other_case):
    user_nl_missing = {}
    for key, value in self.user_nl_objs.items():
        user_nl_missing[key] = []
        for subkey, subvalue in value.items():
            if isinstance(subvalue, dict):
                for subsubkey in subvalue:
                    if subsubkey not in other_case.user_nl_objs.get(key, {}).get(subkey, {}):
                        user_nl_missing[key].append(subsubkey)
    return user_nl_missing

nl_mom.write_text(mom0 + "\nKPP%\nN_SMOOTH = 2\n%KPP\n")
run("fixed diff, cpl + KPP edits", lambda: fixed_diff(sh.CaseBundle(SRC), ref))
restore()
