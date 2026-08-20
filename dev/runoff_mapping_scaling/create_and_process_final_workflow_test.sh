#!/usr/bin/env bash
# Reproduces the final_workflow_test case exactly as built during the
# runoff-mapping-scaling investigation (mom6_forge PR #125): creates a
# CrocoDash case with no rof_esmf_mesh_filepath override (real 21.6M-element
# global GLOFAS mesh), then processes all forcings (OBC, IC, runoff).
#
# Run on a Derecho login node with the CrocoDash conda env available.
#
# Usage: ./create_and_process_final_workflow_test.sh

set -euo pipefail

REPO_ROOT="/glade/u/home/manishrv/documents/croc"
NESTED_MOM6_FORGE="$REPO_ROOT/regional_mom_workflows/CrocoDash/CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py"
FIXED_MOM6_FORGE="$REPO_ROOT/regional_mom_workflows/mom6_forge/mom6_forge/mapping.py"
CASEROOT="$HOME/croc_cases/runoff_mapping_scaling/final_workflow_test"

cd "$REPO_ROOT/dev/runoff_mapping_scaling"

# --- Step 1: temporarily patch CrocoDash's nested mom6_forge copy ----------
# Only needed until PR #125 is merged and CrocoDash's submodule pointer is
# updated to include it. Safe to skip (comment out) once that's true.
echo "Backing up nested mom6_forge/mapping.py and applying the fix..."
cp "$NESTED_MOM6_FORGE" "${NESTED_MOM6_FORGE}.bak"
cp "$FIXED_MOM6_FORGE" "$NESTED_MOM6_FORGE"
trap 'echo "Reverting nested mom6_forge/mapping.py..."; mv "${NESTED_MOM6_FORGE}.bak" "$NESTED_MOM6_FORGE"' EXIT

# --- Step 2: create the case and configure forcings (not yet processed) ---
mkdir -p "$HOME/croc_cases/runoff_mapping_scaling" "$HOME/scratch/croc_input/runoff_mapping_scaling"
conda run -n CrocoDash python create_configure_only.py final_workflow_test.yaml --override

# --- Step 3: process all forcings (OBC, IC, runoff) ------------------------
conda run -n CrocoDash crocodash process --caseroot "$CASEROOT" --all

echo ""
echo "Done. Case is at: $CASEROOT"
echo "Next, from an actual Derecho login node:"
echo "  cd $CASEROOT"
echo "  ./case.setup"
echo "  ./case.build"
echo "  ./case.submit"
