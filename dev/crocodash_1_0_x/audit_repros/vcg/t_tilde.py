# "~" in caseroot/inputdir is not expanded by Case().
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import *
rel = os.path.relpath(S, os.path.expanduser("~"))   # S expressed under ~ (HOME/scratch is a symlink to derecho scratch)
for kind in ("inputdir", "caseroot"):
    kw = {kind: f"~/scratch/{os.path.relpath(S, '/glade/derecho/scratch/manishrv')}/{'input' if kind=='inputdir' else 'cases'}/audit_vcg_tilde"}
    print(kind, "=", kw[kind], " parent exists after expanduser:", Path(kw[kind]).expanduser().parent.exists())
    try:
        make("tilde", **kw)
    except BaseException as e:
        print("  RAISED:", type(e).__name__, str(e)[:250])
