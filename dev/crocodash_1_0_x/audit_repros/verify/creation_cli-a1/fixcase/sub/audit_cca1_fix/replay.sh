#!/bin/bash

set -e

# Created 2026-11-06 14:06:21

CASEDIR="/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/verify/creation_cli-a1/fixcase/sub/audit_cca1_fix"

/glade/u/home/manishrv/work/installs/CESM_crocodash/cime/scripts/create_newcase --compset 1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV --res USER_RES --case "${CASEDIR}" --machine derecho --run-unsupported --handle-preexisting-dirs a --pecount S --project ncgd0011 --non-local

cd "${CASEDIR}"

./xmlchange OCN_GRID=cca1fix --non-local

./xmlchange OCN_NX=4 --non-local

./xmlchange OCN_NY=4 --non-local

./xmlchange OCN_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/verify/creation_cli-a1/fixin/sub/audit_cca1_fix/ocn/ESMF_mesh_cca1fix_ea43d4.nc --non-local

./xmlchange ICE_GRID=cca1fix --non-local

./xmlchange ICE_NX=4 --non-local

./xmlchange ICE_NY=4 --non-local

./xmlchange ICE_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/verify/creation_cli-a1/fixin/sub/audit_cca1_fix/ocn/ESMF_mesh_cca1fix_ea43d4.nc --non-local

./xmlchange WAV_GRID=cca1fix --non-local

./xmlchange WAV_NX=4 --non-local

./xmlchange WAV_NY=4 --non-local

./xmlchange WAV_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/verify/creation_cli-a1/fixin/sub/audit_cca1_fix/ocn/ESMF_mesh_cca1fix_ea43d4.nc --non-local

./xmlchange MASK_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/verify/creation_cli-a1/fixin/sub/audit_cca1_fix/ocn/ESMF_mesh_cca1fix_ea43d4.nc --non-local

./xmlchange ATM_GRID=T62 --non-local

./xmlchange LND_GRID=T62 --non-local

./xmlchange ATM_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/T62_040121_ESMFmesh.nc --non-local

./xmlchange LND_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/T62_040121_ESMFmesh.nc --non-local

./case.setup --non-local

./xmlchange MOM6_MEMORY_MODE=dynamic_symmetric --non-local

