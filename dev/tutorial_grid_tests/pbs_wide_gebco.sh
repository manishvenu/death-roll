#!/bin/bash
#PBS -N wide_gebco
#PBS -A ncgd0011
#PBS -q casper
#PBS -l select=1:ncpus=8:mem=200GB
#PBS -l walltime=03:00:00
#PBS -j oe
#PBS -o /glade/u/home/manishrv/documents/croc/dev/tutorial_grid_tests/logs/wide_gebco.pbs.log

cd /glade/u/home/manishrv/documents/croc/dev/tutorial_grid_tests
conda run -n CrocoDash crocodash create --config alaska_albers_wide_glorys.yaml --override
echo "CREATE_EXIT=$?"
