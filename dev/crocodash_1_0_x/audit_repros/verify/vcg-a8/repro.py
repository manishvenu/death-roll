import sys, time, xml.etree.ElementTree as ET
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(__file__).resolve().parent
name = "audit_vcga8_crjra"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="va8")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="va8")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="CR_JRA", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
            atm_grid_name="TL319", machine="derecho", project="ncgd0011", override=True)
cr = S/"cases"/name
vals = {}
for f in ["env_build.xml", "env_run.xml", "env_case.xml"]:
    for e in ET.parse(cr/f).getroot().iter("entry"):
        vals[e.get("id")] = e.get("value")
for k in ["GRID","ATM_GRID","ATM_NX","ATM_NY","ATM_DOMAIN_MESH","LND_GRID","LND_NX","LND_NY",
          "OCN_GRID","OCN_NX","OCN_NY","ICE_GRID","ICE_NX","ICE_NY","ROF_GRID","ROF_NX","ROF_NY","ROF_DOMAIN_MESH"]:
    print(f"{k} = {vals.get(k)}")
for p in [cr/"CaseDocs"/"drof_in", cr/"CaseDocs"/"datm_in"]:
    print(p, p.exists())
    if p.exists():
        print([l for l in p.read_text().splitlines() if "global" in l])
