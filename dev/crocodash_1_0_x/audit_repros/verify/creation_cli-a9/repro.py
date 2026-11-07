import sys, json, re, logging
from pathlib import Path
D = Path(sys.argv[1])
logging.basicConfig(level=logging.INFO)
from CrocoDash.recipe import load_config, create_case_from_yaml

def report(case, label):
    cfg = json.load(open(case.inputdir / "extract_forcings" / "config.json"))
    entries = [k for k in cfg if k != "caseroot"]
    bnc = cfg["conditions"]["outputs"].get("boundary_number_conversion")
    unl = (case.caseroot / "user_nl_mom").read_text()
    tides_lines = [l for l in unl.splitlines() if re.match(r"\s*(TIDES|OBC_TIDE_CONSTITUENTS)\b", l)]
    nseg = [l for l in unl.splitlines() if "OBC_NUMBER_OF_SEGMENTS" in l]
    print(f"[{label}] config.json entries: {entries}")
    print(f"[{label}] boundaries used: {list(bnc)}")
    print(f"[{label}] user_nl_mom tide lines: {tides_lines}")
    print(f"[{label}] user_nl_mom {nseg}")

# Exactly what `crocodash create --config case.yaml --configure-only` does (cli._create)
config = load_config(D / "case.yaml")   # validate_config_structure: no error
print("load_config OK; forcings keys:", sorted(config["forcings"]))
case = create_case_from_yaml(config, override=True, configure_only=True)
print("create_case_from_yaml returned without error")
report(case, "typo")

# Control: same case, correctly spelled keys
fc = dict(config["forcings"])
fc["tidal_constituents"] = fc.pop("tidal_constituent")
fc["boundaries"] = fc.pop("boundary")
case.configure_forcings(**fc)
report(case, "correct")
