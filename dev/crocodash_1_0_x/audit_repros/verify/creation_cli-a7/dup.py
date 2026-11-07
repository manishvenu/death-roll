import sys, re, json
from pathlib import Path
# env workaround for the known CESM_crocodash MOM_RPS 'param_file_reader' artifact
sys.path.insert(0, str(Path('~/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS').expanduser()))
from CrocoDash.shareable import duplicate_case, ForkBundle

V = Path(__file__).resolve().parent
A = V / "cases/audit_v7_src"
B = V / "cases/audit_v7_dup"; IB = V / "inputs/audit_v7_dup"
C = V / "cases/audit_v7_fork"; IC = V / "inputs/audit_v7_fork"

def dt_lines(case):
    return [l.strip() for l in open(Path(case) / "user_nl_mom") if re.match(r"\s*DT\s*=", l)]
def xmlval(case, var):
    for fn in sorted(Path(case).glob("env_*.xml")):
        m = re.search(rf'<entry id="{var}" value="([^"]*)"', fn.read_text())
        if m: return m.group(1)

nb = duplicate_case(A, B, IB, bundle_dir=V / "bundles")
info = json.load(open(V / "bundles/audit_v7_src_case_bundle/non_standard_case_info.json"))
print("RESULT non_standard_case_info:", json.dumps(info))
print("RESULT SRC  DT:", dt_lines(A), " STOP_N:", xmlval(A, "STOP_N"))
print("RESULT DUP  DT:", dt_lines(B), " STOP_N:", xmlval(B, "STOP_N"))
print("RESULT BUNDLE user_nl_mom DT:", dt_lines(V / "bundles/audit_v7_src_case_bundle"))

fk = ForkBundle(V / "bundles/audit_v7_src_case_bundle")
fk.fork(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(), machine="derecho",
        project_number="ncgd0011", new_caseroot=C, new_inputdir=IC,
        plan={"xml_files": True, "user_nl": True, "source_mods": True, "xmlchanges": True})
print("RESULT FORK DT:", dt_lines(C), " STOP_N:", xmlval(C, "STOP_N"))
