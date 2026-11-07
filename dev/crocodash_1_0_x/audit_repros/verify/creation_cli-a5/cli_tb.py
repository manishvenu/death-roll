# Full traceback of the `crocodash bundle` path (cli._bundle) with one line in user_nl_cpl.
import argparse, sys
from pathlib import Path
sys.argv = ["x"]
exec(open(Path(__file__).resolve().parent / "bundle_diff.py").read().split("# 0. control")[0])
nl_cpl.write_text(cpl0 + "\norb_iyear = 1990\n")
args = argparse.Namespace(caseroot=str(SRC), cesmroot=str(CESM), machine="derecho",
                          project="ncgd0011", output_dir=str(S / "bundles"))
try:
    cli._bundle(args)
finally:
    restore()
