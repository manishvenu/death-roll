#!/bin/bash
set -e
CASE=/glade/u/home/manishrv/croc_cases/small-alaska-vg20
cd $CASE
./xmlchange NTASKS=20
./xmlchange JOB_WALLCLOCK_TIME=01:00:00
./case.setup --reset
./case.build
