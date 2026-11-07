#!/bin/bash
# usage: build_on_derecho.sh <caseroot>
set -x
cd "$1" || exit 2
./xmlchange NTASKS=1,ROOTPE=0,NTHRDS=1
./case.setup --reset
./xmlchange JOB_WALLCLOCK_TIME=00:30:00 --subgroup case.run
./xmlquery TOTALPES,NTASKS_OCN,JOB_QUEUE,JOB_WALLCLOCK_TIME
./case.build
echo "BUILD_EXIT $?"
