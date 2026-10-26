# Write the grid files the case configs name, instead of grids in YAML

## Why

CrocoDash's create config now names the grid files (`case:` `ocn_grid`, `ocn_topo`,
`ocn_vgrid`) instead of describing the grids in `grid:`, `topo:` and `vgrid:` sections
(CROCODILE-CESM/CrocoDash#343). Every config here describes its grid, so each
needs its grid files written first.

## What

- **Panama demo:** `container_scripts/panama_grids.py` writes the demo's grid files
  (GEBCO bathymetry, 75 hyperbolic levels) into `/workspace/grids`.
  `panama_demo_setup.sh` runs it before `crocodash create`, and `panama_case_config.yaml`
  names the files. The Dockerfile copies it into the image, and the end-to-end CI job
  mounts this PR's copy.
- **YAML config mode:** `run_case.sh` runs a grid script mounted at `/workspace/grids.py`,
  with `/workspace/grids` as its output, before `crocodash create`. Without one, mount
  the grid files themselves. `panama_grids.py` is the template; the README shows both
  mounts.
- **Weekly tests:** `cesm_tests/labsea_grids.py` writes the Labrador domain's grid files
  into each test's directory, in the test's CREATE_NEWCASE phase. `run_mom_tests.py`
  names them in the test's config, and `config.yaml` keeps only the forcing.
- **NYF sample:** `setup_nyf_test_case.py` writes the grid files its config names, then
  creates the case.

## Tests

Both grid scripts were run against GEBCO on GLADE, and their files read back with
CrocoDash's `read_grids()`: Labrador 20×16 (min_depth 10, 10 levels) and Panama 60×60
(min_depth 9.5, 75 levels). The new `panama_case_config.yaml` passes CrocoDash's new
config check.

## Notes for reviewers

- **Merge right after CROCODILE-CESM/CrocoDash#343's PR.** The weekly tests follow both repos' branch
  tips, so they fail between the two merges, in either order. The image's CrocoDash
  (this repo's submodule) needs bumping past that PR for the Panama demo and YAML mode;
  until then, the image reads only the old config format.
- Grid building moves from YAML into short Python scripts against mom6_forge's API
  (re-exported by CrocoDash). If that API changes, these scripts fail loudly and change
  with it.

Closes #18

🤖 Generated with [Claude Code](https://claude.com/claude-code)
