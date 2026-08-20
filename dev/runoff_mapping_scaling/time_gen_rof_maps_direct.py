"""
Time mom6_forge.mapping.gen_rof_maps() directly, with no CrocoDash/DROF involved.

This isolates the cost of the mapping-file-generation step itself (nearest-
neighbor regrid + smoothing) from CrocoDash pipeline overhead. Two ROF source
mesh choices (see NOTES.md):
  - "regional" (default): ajanney's regional GLOFAS_CARIB12_mesh.nc
    (319,200 elements, 270 active)
  - "global": the production global GLOFAS ESMF mesh registered in CIME's
    config_grids.xml (21,600,000 elements, all flagged active - no land/ocean
    masking baked into the mesh itself, so map_overlap's masking step has real
    work to do). Much bigger, so a code change's effect should show up more
    clearly here - but a single run can take many minutes.
Ocean mesh is always tiny_gulf01's ESMF_mesh (24x24 = 576 cells).

This is the baseline/comparison harness for the runoff-mapping-scaling effort in
dev/runoff_mapping_scaling/NOTES.md - re-run the same way (same mesh choice,
same rmax/fold) after each isolated code change to measure its effect, and diff
the output mapping files to confirm the change didn't alter the numerical result.

Usage (on a Derecho login node, mom6_forge conda env):
    python time_gen_rof_maps_direct.py [--mesh regional|global] [--output-dir DIR] [--clean]
"""

import argparse
import shutil
from pathlib import Path
from time import process_time, time

from mom6_forge.mapping import gen_rof_maps

REFERENCE_DIR = Path(
    "~/scratch/croc_input/runoff_mapping_scaling/reference_files"
).expanduser()
ROF_MESH_PATHS = {
    "regional": REFERENCE_DIR / "GLOFAS_CARIB12_mesh.nc",
    "global": Path(
        "/glade/campaign/cesm/cesmdata/inputdata/lnd/dlnd7/GLOFAS/"
        "GLOFAS.v4.dis24.ESMFmesh_20260501.nc"
    ),
}
OCN_MESH_PATH = Path(
    "~/scratch/croc_input/runoff_mapping_scaling/tiny_gulf01/ocnice/"
    "ESMF_mesh_runoff_scale_tiny_gulf01_f93a94.nc"
).expanduser()

RMAX_KM = 50
FOLD_KM = 100
MAPPING_FILE_PREFIX = "GLOFAS_to_runoff_scale_tiny_gulf01_map"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--mesh",
    choices=["regional", "global"],
    default="regional",
    help="Which ROF source mesh to use (default: regional, ajanney's CARIB12 mesh).",
)
parser.add_argument(
    "--output-dir",
    default="~/scratch/croc_input/runoff_mapping_scaling/tiny_gulf01/mapping_timing_test",
    help="Directory to write timing-test mapping files to (kept separate from the "
    "existing tiny_gulf01/mapping/ baseline outputs).",
)
parser.add_argument(
    "--clean",
    action="store_true",
    help="Remove --output-dir before running, so file-exists side effects from a "
    "previous run don't leak into this timing.",
)
args = parser.parse_args()

ROF_MESH_PATH = ROF_MESH_PATHS[args.mesh]

output_dir = Path(args.output_dir).expanduser()
if args.clean and output_dir.exists():
    shutil.rmtree(output_dir)

assert ROF_MESH_PATH.exists(), f"Missing ROF mesh: {ROF_MESH_PATH}"
assert OCN_MESH_PATH.exists(), f"Missing ocean mesh: {OCN_MESH_PATH}"

print(f"ROF mesh:  {ROF_MESH_PATH}")
print(f"OCN mesh:  {OCN_MESH_PATH}")
print(f"Output:    {output_dir}")

wall_start = time()
cpu_start = process_time()
gen_rof_maps(
    rof_mesh_path=ROF_MESH_PATH,
    ocn_mesh_path=OCN_MESH_PATH,
    output_dir=output_dir,
    mapping_file_prefix=MAPPING_FILE_PREFIX,
    rmax=RMAX_KM,
    fold=FOLD_KM,
)
wall_elapsed = time() - wall_start
cpu_elapsed = process_time() - cpu_start

print(f"\ngen_rof_maps() wall elapsed: {wall_elapsed:.2f} s ({wall_elapsed/60:.2f} min)")
print(f"gen_rof_maps() CPU elapsed:  {cpu_elapsed:.2f} s ({cpu_elapsed/60:.2f} min)")
print(f"CPU utilization over the call: {100*cpu_elapsed/wall_elapsed:.0f}%")
