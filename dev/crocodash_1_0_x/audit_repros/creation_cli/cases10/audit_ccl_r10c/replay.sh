#!/bin/bash

set -e

# Created 2026-11-06 09:50:45

CASEDIR="/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/cases10/audit_ccl_r10c"

/glade/u/home/manishrv/work/installs/CESM_crocodash/cime/scripts/create_newcase --compset GR_JRA --res USER_RES --case "${CASEDIR}" --machine derecho --run-unsupported --handle-preexisting-dirs a --pecount S --project ncgd0011 --non-local

cd "${CASEDIR}"

./xmlchange OCN_GRID=ccr10 --non-local

./xmlchange OCN_NX=8 --non-local

./xmlchange OCN_NY=8 --non-local

./xmlchange OCN_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs10/audit_ccl_r10c/ocn/ESMF_mesh_ccr10_338652.nc --non-local

./xmlchange ICE_GRID=ccr10 --non-local

./xmlchange ICE_NX=8 --non-local

./xmlchange ICE_NY=8 --non-local

./xmlchange ICE_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs10/audit_ccl_r10c/ocn/ESMF_mesh_ccr10_338652.nc --non-local

./xmlchange WAV_GRID=ccr10 --non-local

./xmlchange WAV_NX=8 --non-local

./xmlchange WAV_NY=8 --non-local

./xmlchange WAV_DOMAIN_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs10/audit_ccl_r10c/ocn/ESMF_mesh_ccr10_338652.nc --non-local

./xmlchange MASK_MESH=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs10/audit_ccl_r10c/ocn/ESMF_mesh_ccr10_338652.nc --non-local

./xmlchange ATM_GRID=TL319 --non-local

./xmlchange LND_GRID=TL319 --non-local

./xmlchange ATM_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/TL319_151007_ESMFmesh.nc --non-local

./xmlchange LND_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/share/meshes/TL319_151007_ESMFmesh.nc --non-local

./xmlchange ROF_GRID=GLOFAS --non-local

./xmlchange ROF_DOMAIN_MESH=/glade/campaign/cesm/cesmdata/inputdata/lnd/dlnd7/GLOFAS/GLOFAS.v4.dis24.ESMFmesh_20260501.nc --non-local

./case.setup --non-local

./xmlchange MOM6_MEMORY_MODE=dynamic_symmetric --non-local

./xmlchange ROF2OCN_LIQ_RMAPNAME=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs10/audit_ccl_r10c/mapping/GLOFAS_to_ccr10_map_r200_f400_nnsm.nc --non-local

./xmlchange ROF2OCN_ICE_RMAPNAME=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/creation_cli/inputs10/audit_ccl_r10c/mapping/GLOFAS_to_ccr10_map_r200_f400_nnsm.nc --non-local

./xmlchange CALENDAR=GREGORIAN --non-local

./xmlchange RUN_STARTDATE=2020-01-01 --non-local

./xmlchange STOP_OPTION=ndays --non-local

./xmlchange STOP_N=3 --non-local

