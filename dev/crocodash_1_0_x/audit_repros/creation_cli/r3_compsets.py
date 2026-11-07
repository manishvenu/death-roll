import os, sys, json, subprocess, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
which = sys.argv[1:]
for alias in which:
    name = "audit_ccl_" + alias.lower()
    cr = D / "cases3" / name; ip = D / "inputs3" / name
    cr.parent.mkdir(exist_ok=True); ip.parent.mkdir(exist_ok=True)
    try:
        c = make_case(cr, ip, name="cc" + alias.lower()[:6], compset=alias, atm="TL319")
        print(alias, "CREATED lname=", c.compset_lname, "alias=", c.compset_alias)
        for comp in ("ww3", "cice"):
            f = cr / f"user_nl_{comp}"
            if f.exists():
                print(alias, comp, [l.strip() for l in open(f) if l.strip() and not l.startswith("!")])
        print(alias, "inputdir:", sorted(str(p.relative_to(ip)) for p in ip.rglob("*") if p.is_file()))
        st = json.load(open(cr / "_crocodash_state.json")); print(alias, "STATE", {k: st[k] for k in ("compset_lname","rof_grid_name","atm_grid_name")})
        q = subprocess.run("./xmlquery WAV_NCPL,ICE_NCPL,OCN_NCPL,NTASKS_OCN,NTASKS_WAV,NTASKS_ICE --non-local", shell=True, cwd=cr, capture_output=True, text=True)
        print(alias, "XML", q.stdout.replace("\n", " "))
    except Exception as e:
        print(alias, "FAILED:", type(e).__name__, str(e)[:600])
