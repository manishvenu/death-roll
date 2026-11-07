#!/bin/bash

set -e

# Created 2026-11-06 09:42:18

CASEDIR="/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/cases4/audit_ccl_r4b"

/glade/u/home/manishrv/work/installs/CESM_crocodash/cime/scripts/create_newcase --compset 1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV --res USER_RES --case "${CASEDIR}" --machine derecho --run-unsupported --handle-preexisting-dirs a --pecount S --project ncgd0011 --non-local

cd "${CASEDIR}"

./xmlchange OCN_GRID=ccr4 --non-local

./xmlchange OCN_NX=8 --non-local

./xmlchange OCN_NY=8 --non-local

./xmlchange OCN_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs4/audit_ccl_r4b/ocn/ESMF_mesh_ccr4_fa7fac.nc --non-local

./xmlchange ICE_GRID=ccr4 --non-local

./xmlchange ICE_NX=8 --non-local

./xmlchange ICE_NY=8 --non-local

./xmlchange ICE_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs4/audit_ccl_r4b/ocn/ESMF_mesh_ccr4_fa7fac.nc --non-local

./xmlchange WAV_GRID=ccr4 --non-local

./xmlchange WAV_NX=8 --non-local

./xmlchange WAV_NY=8 --non-local

./xmlchange WAV_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs4/audit_ccl_r4b/ocn/ESMF_mesh_ccr4_fa7fac.nc --non-local

./xmlchange MASK_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs4/audit_ccl_r4b/ocn/ESMF_mesh_ccr4_fa7fac.nc --non-local

./xmlchange ATM_GRID=T62 --non-local

./xmlchange LND_GRID=T62 --non-local

./xmlchange ATM_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/T62_040121_ESMFmesh.nc --non-local

./xmlchange LND_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/T62_040121_ESMFmesh.nc --non-local

./case.setup --non-local

./xmlchange MOM6_MEMORY_MODE=dynamic_symmetric --non-local

./xmlchange JOB_QUEUE=develop --non-local

./xmlchange JOB_WALLCLOCK_TIME=01:30:00 --non-local

./xmlchange CALENDAR=GREGORIAN --non-local

./xmlchange RUN_STARTDATE=2020-01-01 --non-local

./xmlchange STOP_OPTION=ndays --non-local

./xmlchange STOP_N=3 --non-local

