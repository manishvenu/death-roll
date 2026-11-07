"""Render MOM_input / MOM_override / mom.input_data_list for an existing case
with MOM's own MOM_RPS code (as buildnml steps 1, 2, 3, 5 do), into out/<casename>/."""
import os, sys
from pathlib import Path
S = Path(__file__).resolve().parent
casename = sys.argv[1]
cesmroot = Path(os.environ["CESMROOT"])
sys.path.insert(0, str(cesmroot / "cime"))
sys.path.insert(0, str(cesmroot / "cime/CIME/Tools"))
momcfg = cesmroot / "components/mom/cime_config"
sys.path.insert(0, str(momcfg / "MOM_RPS"))
from CIME.case import Case as CIMECase
from FType_MOM_params import FType_MOM_params
from FType_input_data_list import FType_input_data_list
from param_file_reader import read_user_nl_mom
json_dir = cesmroot / "components/mom/param_templates/json"
out = S / "out" / casename
out.mkdir(parents=True, exist_ok=True)
caseroot = S / "cases" / casename
with CIMECase(str(caseroot), read_only=True, non_local=True) as cc:
    print("OCN_GRID =", cc.get_value("OCN_GRID"))
    FType_MOM_params.from_json(json_dir / "MOM_input.json").write(
        output_path=out / "MOM_input", output_format="MOM_input", case=cc, inst_suffix="")
    params, _ = read_user_nl_mom(caseroot / "user_nl_mom")
    FType_MOM_params(params).write(output_path=out / "MOM_override", output_format="MOM_override",
        def_params=FType_MOM_params.from_MOM_input(out / "MOM_input"))
    final = FType_MOM_params.from_MOM_input(out / "MOM_input")
    final.append(FType_MOM_params.from_MOM_input(out / "MOM_override"))
    FType_input_data_list.from_json(json_dir / "input_data_list.json").write(
        out / "mom.input_data_list", cc, final)
print("rendered to", out)
