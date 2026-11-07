#!/bin/bash

set -e

# Created 2026-11-06 09:48:11

CASEDIR="/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/cases8/audit_ccl_r8alias"

/glade/u/home/manishrv/work/installs/CESM_crocodash/cime/scripts/create_newcase --compset CR1850MARBL_JRA --res USER_RES --case "${CASEDIR}" --machine derecho --run-unsupported --handle-preexisting-dirs a --pecount S --project ncgd0011 --non-local

cd "${CASEDIR}"

./xmlchange OCN_GRID=ccr8a --non-local

./xmlchange OCN_NX=8 --non-local

./xmlchange OCN_NY=8 --non-local

./xmlchange OCN_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs8/audit_ccl_r8alias/ocn/ESMF_mesh_ccr8a_d99084.nc --non-local

./xmlchange ICE_GRID=ccr8a --non-local

./xmlchange ICE_NX=8 --non-local

./xmlchange ICE_NY=8 --non-local

./xmlchange ICE_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs8/audit_ccl_r8alias/ocn/ESMF_mesh_ccr8a_d99084.nc --non-local

./xmlchange WAV_GRID=ccr8a --non-local

./xmlchange WAV_NX=8 --non-local

./xmlchange WAV_NY=8 --non-local

./xmlchange WAV_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs8/audit_ccl_r8alias/ocn/ESMF_mesh_ccr8a_d99084.nc --non-local

./xmlchange MASK_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs8/audit_ccl_r8alias/ocn/ESMF_mesh_ccr8a_d99084.nc --non-local

./xmlchange ATM_GRID=TL319 --non-local

./xmlchange LND_GRID=TL319 --non-local

./xmlchange ATM_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/TL319_151007_ESMFmesh.nc --non-local

./xmlchange LND_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/TL319_151007_ESMFmesh.nc --non-local

./xmlchange ROF_GRID=GLOFAS --non-local

./xmlchange ROF_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/lnd/dlnd7/GLOFAS/GLOFAS.v4.dis24.ESMFmesh_20260501.nc --non-local

./case.setup --non-local

./xmlchange MOM6_MEMORY_MODE=dynamic_symmetric --non-local

