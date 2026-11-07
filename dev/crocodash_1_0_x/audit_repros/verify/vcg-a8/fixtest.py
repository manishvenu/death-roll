# Same as repro.py, but with the proposed fix monkeypatched into CaseCreator.
import xml.etree.ElementTree as ET
from pathlib import Path
from visualCaseGen.custom_widget_types import case_creator as cc
from ProConPy.config_var import cvars
_orig = cc.CaseCreator._update_component_grids_xml
def _patched(self, custom_grid_path, ocn_grid, ocn_grid_mode, do_exec):
    _orig(self, custom_grid_path, ocn_grid, ocn_grid_mode, do_exec)
    if ocn_grid_mode == "Create New":
        for comp, var in (("atm", "CUSTOM_ATM_GRID"), ("lnd", "CUSTOM_LND_GRID"), ("rof", "CUSTOM_ROF_GRID")):
            g = cvars[var].value
            if g in (None, "", "null"):
                continue
            d = self._cime.domains[comp][g]
            cc.xmlchange(f"{comp.upper()}_NX", d.nx, do_exec, self._is_non_local(), self._out)
            cc.xmlchange(f"{comp.upper()}_NY", d.ny, do_exec, self._is_non_local(), self._out)
cc.CaseCreator._update_component_grids_xml = _patched
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(__file__).resolve().parent
name = "audit_vcga8_fix"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="va8f")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="va8f")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="CR_JRA", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
            atm_grid_name="TL319", machine="derecho", project="ncgd0011", override=True)
vals = {}
for f in ["env_build.xml"]:
    for e in ET.parse(S/"cases"/name/f).getroot().iter("entry"):
        vals[e.get("id")] = e.get("value")
for k in ["ATM_GRID","ATM_NX","ATM_NY","LND_NX","LND_NY","ROF_GRID","ROF_NX","ROF_NY"]:
    print(f"{k} = {vals.get(k)}")
