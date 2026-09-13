#!/bin/bash
#PBS -N process_forcings
#PBS -A ncgd0011
#PBS -q develop
#PBS -l select=1:ncpus=4:mem=64GB
#PBS -l walltime=03:00:00
#PBS -j oe

# Same as pbs_process_forcings.sh but with a much longer walltime -- for
# domains whose GLORYS download is large enough (e.g. a pole-centered box
# needing a near-global longitude slice) to need more than an hour. The
# original 1hr cap was this script's own -l walltime request, not a limit
# enforced by the develop/cpudev queue itself (qstat -Qf cpudev shows no
# resources_max.walltime) -- so stay on the fast dev queue and just ask for
# more time, rather than routing to the slower/more-contended main queue.
# Usage: qsub -v CASE_DIR=/path/to/case_dir pbs_process_forcings_longwall.sh

set -euo pipefail

export ESMFMKFILE=/glade/work/manishrv/conda-envs/CrocoDash/lib/esmf.mk

conda run -n CrocoDash python \
    /glade/u/home/manishrv/documents/croc/dev/MCP_CrocoDash/tools/_bg_worker.py \
    "${CASE_DIR}"
