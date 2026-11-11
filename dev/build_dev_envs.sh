#!/usr/bin/env bash
# Build dev conda envs for the four regional_mom_workflows packages.
# Envs land in /glade/work/manishrv/conda-envs/ per ~/.condarc.

set -euo pipefail

ROOT=/glade/u/home/manishrv/documents/croc/regional_mom_workflows
LOG=/glade/u/home/manishrv/documents/croc/dev/build_dev_envs.log

exec >"$LOG" 2>&1
echo "==> start $(date)"

# Intel oneAPI compilers loaded in the shell corrupt pip source builds
# (icx crashes on matplotlib). Force pip to use wheels.
unset CC CXX FC CPP F77 F90

step() { echo; echo "==> [$(date +%H:%M:%S)] $*"; }

step "dev_rm6 (regional-mom6, ci base + editable) — python pinned to 3.11"
cd "$ROOT/regional-mom6"
# environment-ci.yml doesn't pin python; splice a pin so pip finds matplotlib wheels
TMP_YML=$(mktemp --suffix=.yml)
awk '/^dependencies:/{print;print "  - python=3.11";next}1' environment-ci.yml >"$TMP_YML"
mamba env create -n dev_rm6 -f "$TMP_YML"
rm -f "$TMP_YML"
conda run -n dev_rm6 pip install -e .

step "dev_vcg (visualCaseGen)"
cd "$ROOT/visualCaseGen"
mamba env create -n dev_vcg -f environment.yml

step "dev_cd (CrocoDash, incl. fastmcp for MCP servers)"
cd "$ROOT/CrocoDash"
mamba env create -n dev_cd -f environment.yml
conda run -n dev_cd pip install fastmcp

echo; echo "==> done $(date)"
