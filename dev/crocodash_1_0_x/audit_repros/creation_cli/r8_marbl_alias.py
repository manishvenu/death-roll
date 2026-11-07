import os, sys, json, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
(D/"cases8").mkdir(exist_ok=True); (D/"inputs8").mkdir(exist_ok=True)
for label, comp in [("alias", "CR1850MARBL_JRA"), ("lname", "1850_DATM%JRA-1p5-2023_SLND_DICE%SSMI_MOM6%REGIONAL%MARBL-BIO_DROF%GLOFAS_SGLC_SWAV")]:
    n = f"audit_ccl_r8{label}"
    try:
        c = make_case(D/"cases8"/n, D/"inputs8"/n, name="ccr8" + label[0], compset=comp, atm="TL319")
        st = json.load(open(D/"cases8"/n/"_crocodash_state.json"))
        print(label, "CREATED; state compset_lname:", st["compset_lname"], "| 'compset' in state:", "compset" in st)
    except Exception as e:
        print(label, "FAILED:", type(e).__name__, str(e)[:500])
