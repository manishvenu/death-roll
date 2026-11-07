#!/bin/bash

set -e

# Created 2026-11-06 09:36:41

CASEDIR="/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/fakehome/cases_rel/audit_ccl_r2d"

/glade/u/home/manishrv/work/installs/CESM_crocodash/cime/scripts/create_newcase --compset 1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV --res USER_RES --case "${CASEDIR}" --machine derecho --run-unsupported --handle-preexisting-dirs a --pecount S --project ncgd0011 --non-local

cd "${CASEDIR}"

