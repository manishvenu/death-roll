# ocn_topo built on a different Grid than ocn_grid: is it caught at Case()?
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
import xarray as xr
gA, _, vg = objs(name="vcgmm", res=0.5)            # 8x8
gB, tB, _ = objs(name="vcgmm", res=0.25)           # 16x16 grid + its topo
try:
    case = make("mismatch", ocn_grid=gA, ocn_topo=tB, ocn_vgrid=vg) if False else None
except Exception as e:
    print("RAISED", e)
from CrocoDash.case import Case
case = Case(cesmroot=CESMROOT, caseroot=S/"cases/audit_vcg_mismatch", inputdir=S/"input/audit_vcg_mismatch",
            compset=NYF, ocn_grid=gA, ocn_topo=tB, ocn_vgrid=vg, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("CREATED without error")
show(case.caseroot, ids=("OCN_NX","OCN_NY","OCN_DOMAIN_MESH"))
nl = (case.caseroot/"user_nl_mom").read_text().splitlines()
print([l for l in nl if l.startswith(("NIGLOBAL","NJGLOBAL"))])
with xr.open_dataset(case.topo_path) as t: print("topo file depth dims:", dict(t.depth.sizes))
with xr.open_dataset(case.esmf_mesh_path) as m: print("mesh elementCount:", m.sizes["elementCount"])
with xr.open_dataset(case.supergrid_path) as h: print("supergrid nx,ny:", h.sizes["nx"], h.sizes["ny"])
