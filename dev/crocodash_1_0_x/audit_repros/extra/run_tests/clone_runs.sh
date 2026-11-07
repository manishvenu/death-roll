#!/bin/bash
# Run on Derecho after audit_rA is built. Creates keepexe clones of audit_rA that differ only in
# where INPUTDIR (and, for C/E, the ocean/ice/wave/mask mesh paths) point, then submits them.
#   B: INPUTDIR 140 characters long (H5)
#   C: INPUTDIR and meshes under a directory whose name contains a space
#   E: INPUTDIR and meshes relative to the directory CrocoDash ran in (C9)
set -x
CIME=/glade/work/manishrv/installs/CESM_crocodash/cime/scripts
BASE=/glade/derecho/scratch/manishrv/ar
LONG=$(cat /glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/gap3/longdir.txt)
MESH=$(basename "$(ls $BASE/i/rA/ocn/ESMF_mesh_*.nc)")
cd $BASE/c || exit 2
for X in B C E; do
  rm -rf audit_r$X /glade/derecho/scratch/manishrv/audit_r$X
  $CIME/create_clone --case audit_r$X --clone audit_rA --keepexe || { echo "CLONE_FAIL $X"; continue; }
  cd audit_r$X
  ./xmlchange RUNDIR=/glade/derecho/scratch/manishrv/audit_r$X/run
  case $X in
    B) DIR="$LONG/ocn" ;;
    C) DIR="$BASE/i/sp ace/ocn" ;;
    E) DIR="i/rA/ocn" ;;
  esac
  sed -i "s|^INPUTDIR = .*|INPUTDIR = $DIR|" user_nl_mom
  if [ "$X" != "B" ]; then
    ./xmlchange "OCN_DOMAIN_MESH=$DIR/$MESH"
    ./xmlchange "ICE_DOMAIN_MESH=$DIR/$MESH"
    ./xmlchange "WAV_DOMAIN_MESH=$DIR/$MESH"
    ./xmlchange "MASK_MESH=$DIR/$MESH"
  fi
  grep -n "^INPUTDIR" user_nl_mom
  ./xmlquery EXEROOT,RUNDIR,BUILD_COMPLETE,OCN_DOMAIN_MESH,TOTALPES,JOB_QUEUE
  ./case.submit
  echo "SUBMIT_EXIT $X $?"
  cd $BASE/c
done
