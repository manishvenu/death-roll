"""vcg-a10: a regional grid named like a standard CESM ocnice grid.

usage: repro.py <grid_name> <casename> <override:0|1>
Creates a tiny NYF case, configures reference_ocean forcings, then renders
MOM_input / MOM_override / mom.input_data_list with MOM's own MOM_RPS code
(exactly as components/mom/cime_config/buildnml does) into out/<casename>/.
"""
import os, sys, json
from pathlib import Path
S = Path(__file__).resolve().parent
name, casename, override = sys.argv[1], sys.argv[2], bool(int(sys.argv[3]))
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

cesmroot = Path(os.environ["CESMROOT"])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name=name)
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name=name)
try:
    case = Case(cesmroot=cesmroot, caseroot=S / "cases" / casename,
                inputdir=S / "input" / casename,
                compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
                ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
                machine="derecho", project="ncgd0011", override=override)
except Exception as e:
    print(f"Case() RAISED {type(e).__name__}: {e}")
    sys.exit(0)

print("ocnice domains contain name:", name in case.cime.domains["ocnice"])
print("OCN_GRID =", case._cime_case.get_value("OCN_GRID"))
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-05 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data")
print("configured")

sys.exit(0)
# Render MOM inputs the way buildnml does, but into our own scratch dir.
from CIME.case import Case as CIMECase
momcfg = cesmroot / "components/mom/cime_config"
sys.path.insert(0, str(momcfg / "MOM_RPS"))
from FType_MOM_params import FType_MOM_params
from FType_input_data_list import FType_input_data_list
from param_file_reader import read_user_nl_mom
json_dir = cesmroot / "components/mom/param_templates/json"
out = S / "out" / casename
out.mkdir(parents=True, exist_ok=True)
with CIMECase(str(S / "cases" / casename), read_only=True) as cc:
    print("OCN_GRID (re-read) =", cc.get_value("OCN_GRID"))
    FType_MOM_params.from_json(json_dir / "MOM_input.json").write(
        output_path=out / "MOM_input", output_format="MOM_input", case=cc, inst_suffix="")
    params, _ = read_user_nl_mom(S / "cases" / casename / "user_nl_mom")
    FType_MOM_params(params).write(output_path=out / "MOM_override", output_format="MOM_override",
        def_params=FType_MOM_params.from_MOM_input(out / "MOM_input"))
    final = FType_MOM_params.from_MOM_input(out / "MOM_input")
    final.append(FType_MOM_params.from_MOM_input(out / "MOM_override"))
    FType_input_data_list.from_json(json_dir / "input_data_list.json").write(
        out / "mom.input_data_list", cc, final)
print("rendered to", out)
