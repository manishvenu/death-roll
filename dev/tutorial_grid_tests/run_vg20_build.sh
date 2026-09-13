#!/bin/bash
set -e
source $(conda info --base)/etc/profile.d/conda.sh
conda activate CrocoDash
# CrocoDash from the cice-new worktree; regional_mom6 / visualCaseGen / mom6_forge
# resolve to the main checkout via the env's editable installs.
export PYTHONPATH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/e9abe6da-4d71-45fe-90b7-adea5e006690/scratchpad/wt-cice-new
export ESMFMKFILE=/glade/work/manishrv/conda-envs/CrocoDash/lib/esmf.mk
cd /glade/u/home/manishrv/documents/croc/dev/tutorial_grid_tests
python -u build_small_alaska_vg20.py
