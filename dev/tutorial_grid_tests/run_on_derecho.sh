#!/bin/bash
# Run a CrocoDash command on Derecho with the conda env properly activated.
#
# A non-interactive `ssh derecho '<cmd>'` does not run the env's activate.d
# hooks, so ESMFMKFILE is unset and esmpy falls back to a hard-coded
# /usr/local/esmf path that does not exist -- every CrocoDash import dies at
# `import xesmf`. Sourcing conda.sh and activating properly also picks up the
# libfabric/ucx hooks that MPI needs, so do that rather than exporting
# ESMFMKFILE alone.
#
# Usage: ssh derecho "bash /path/to/run_on_derecho.sh '<command string>'"
set -euo pipefail
source /glade/u/apps/opt/miniforge/25.11/etc/profile.d/conda.sh
conda activate CrocoDash
echo "ESMFMKFILE=${ESMFMKFILE:-<unset>}"
exec bash -c "$*"
