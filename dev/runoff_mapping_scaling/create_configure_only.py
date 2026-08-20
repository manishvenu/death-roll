"""
Create a scaling-test case and run configure_forcings only - deliberately
skips process_forcings, unlike `crocodash create` (whose CLI hardcodes
configure_only=False and always auto-chains into a full process_forcings run
across every forcing component). That matters here because we want to time
just the runoff-mapping step in isolation via CrocoDash's process_forcings()
granular process_* flags, run separately afterward.

Usage (on a Derecho login node, CrocoDash conda env):
    python create_configure_only.py <path/to/case.yaml> [--override]
"""

import argparse

from CrocoDash.recipe import load_config, create_case_from_yaml

parser = argparse.ArgumentParser()
parser.add_argument("config")
parser.add_argument("--override", action="store_true")
args = parser.parse_args()

config = load_config(args.config)
case = create_case_from_yaml(config, override=args.override, configure_only=True)
print(f"Case created and forcings configured (not processed): {case.caseroot}")
