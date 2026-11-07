# Duplicate the tides case with the shipped duplicate_case (as `crocodash duplicate` does).
import sys, os, traceback
# MOM_RPS on sys.path only to get past the known local param_file_reader environment artifact.
sys.path.insert(0, os.path.expanduser("~/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS"))
from pathlib import Path
import shutil
import CrocoDash.shareable as sh
D = Path(sys.argv[1]); mode = sys.argv[2]
if mode == "fix":
    # Monkeypatched smallest fix: duplicate_case's copy skips non-regular entries.
    class _Sh:
        def __getattr__(self, k): return getattr(shutil, k)
        @staticmethod
        def copy(src, dst, **kw):
            if Path(src).is_dir():
                print("  skip non-file", src); return dst
            return shutil.copy(src, dst, **kw)
    sh.shutil = _Sh()
name = "audit_va4_dup" if mode == "plain" else "audit_va4_dupfix"
try:
    sh.duplicate_case(D/"cases/audit_va4_src", D/f"cases/{name}", D/f"input/{name}")
    print("DUPLICATE OK")
except Exception:
    traceback.print_exc()
new_ocn = D/f"input/{name}/ocn"
if new_ocn.exists():
    files = sorted(p.name for p in new_ocn.iterdir())
    print(f"new ocn has {len(files)} entries:", files)
    src = sorted(p.name for p in (D/"input/audit_va4_src/ocn").iterdir() if p.is_file())
    print("tu/tz files carried over:", [f for f in files if f.startswith(("tu_","tz_"))])
    print("missing regular files vs source:", sorted(set(src) - set(files)))
