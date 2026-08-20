"""
Time just the runoff-mapping step (mom6_forge.mapping.gen_rof_maps, via
CrocoDash.extract_forcings.driver.run_workflow(runoff=True)) for a case that
has already been through configure_forcings (e.g. via create_configure_only.py).

Every other forcing component is left off, so this isolates the nearest-
neighbor regrid + smoothing-kernel cost that we're trying to scale/optimize -
this is the workaround for a bug in the CrocoDash MCP server's process_forcings
tool (dev/MCP_CrocoDash/tools/case.py and _bg_worker.py both pass cice=/ww3=
kwargs to run_workflow(), which has never had those parameters, so the MCP
tool currently TypeErrors on every call regardless of compset - fixed in this
repo but the running MCP server process needs a restart to pick it up).

Usage (on a Derecho login node, CrocoDash conda env):
    python time_runoff_step.py <path/to/case_inputdir>
"""

import argparse
import time
from pathlib import Path

from CrocoDash.extract_forcings.driver import run_workflow

parser = argparse.ArgumentParser()
parser.add_argument("case_dir", help="Case inputdir (contains extract_forcings/config.json)")
args = parser.parse_args()

config_path = Path(args.case_dir) / "extract_forcings" / "config.json"

start = time.monotonic()
run_workflow(config_path=config_path, runoff=True)
elapsed = time.monotonic() - start

print(f"runoff mapping step elapsed: {elapsed:.1f} s ({elapsed/60:.2f} min)")
