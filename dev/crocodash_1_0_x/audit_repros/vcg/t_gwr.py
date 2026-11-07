import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
try:
    case = make("gwr", compset="GWR_JRA", atm_grid_name="TL319")
except BaseException as e:
    import traceback; traceback.print_exc(); sys.exit(1)
show(case.caseroot, ids=("OCN_GRID","ICE_GRID","WAV_GRID","ROF_GRID","OCN_DOMAIN_MESH","ICE_DOMAIN_MESH","WAV_DOMAIN_MESH","ROF_DOMAIN_MESH","MASK_MESH","ATM_GRID","LND_GRID","ATM_DOMAIN_MESH","LND_DOMAIN_MESH","OCN_NCPL","ICE_NCPL","WAV_NCPL","ATM_NCPL","ROF_NCPL","ROF2OCN_LIQ_RMAPNAME","ROF2OCN_ICE_RMAPNAME","ATM2OCN_FMAPNAME","GRID","RUNDIR","CALENDAR"))
for f in ("user_nl_cice","user_nl_ww3","user_nl_mom"):
    p = case.caseroot/f
    if p.exists():
        print("----", f); print("\n".join(l for l in p.read_text().splitlines() if l.strip() and not l.startswith("!")))
rd = Path("/glade/derecho/scratch/manishrv/audit_vcg_gwr/run")
print("RUNDIR exists", rd.exists(), list((rd/"ww3_moddef_create").glob("*")) if (rd/"ww3_moddef_create").exists() else None)
print(sorted(p.name for p in (case.inputdir).rglob("*")))
