# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

CROC (CROCODILE) is a monorepo of Git submodules for building and running regional ocean model configurations inside CESM with MOM6. Primary production code is in `regional_mom_workflows/`; exploratory/dev work is in `dev/`.

GitHub org: https://github.com/CROCODILE-CESM — all remote repos live here. Development follows standard GitHub flow: feature branches, PRs, review, merge.

Key submodules:
- `regional_mom_workflows/CrocoDash` — Main integration layer; entry point for most case setup tasks
- `regional_mom_workflows/regional-mom6` — MOM6 configuration, forcing generation, regridding
- `regional_mom_workflows/mom6_forge` — Grid, bathymetry, and vertical grid generation
- `regional_mom_workflows/visualCaseGen` — Jupyter GUI for CESM case creation (constraint-satisfaction driven)
- `dev/SeaSloth` — Performance benchmarking suite for CrocoDash/mom6_forge/xESMF; tracks operation timing across commits and publishes an interactive HTML dashboard via ASV
- `regional_mom_workflows/gallery` — CrocoGallery, is the main demo and tutorial place for CrocoDash

## Important Paths on GLADE

| Purpose | Path |
|---|---|
| CESM installs (with MOM6) | `~/work/installs/` |
| CESM cases | `~/croc_cases/` (symlink → `croc_cases/`) |
| MOM6 input data | `~/scratch/croc_input/` (symlink → `croc_input/`) |

`croc_cases/` and `croc_input/` at the repo root are symlinks to the above scratch locations.

## Architecture

**CrocoDash** (`regional_mom_workflows/CrocoDash/CrocoDash/`) is the integration layer:
- `case.py` — main `Case` class; orchestrates CESM init, grid, forcing, and regional-mom6 operations
- `extract_forcings/` — forcing extraction modules: `bgc.py`, `runoff.py`, `tides.py`, regrid utilities
- `raw_data_access/` — data registry and product access
- `forcing_configurations/` — forcing config registry
- `rm6/` — embedded submodule copy of regional-mom6
- `visualCaseGen/` — embedded submodule copy of visualCaseGen
- `gallery/` — embedded submodule copy of CrocoGallery


**visualCaseGen** uses constraint satisfaction (via `ProConPy/csp_solver.py` and `config_var.py`) to validate CESM case configs before creation. Interfaces with CIME through `cime_interface.py`.

**regional-mom6** (`regional_mom6/`) handles regridding (`regridding.py`), MOM6 parameter management (`MOM_parameter_tools.py`), grid rotation (`rotation.py`), and the main `Experiment` class (`regional_mom6.py`). Uses xarray/dask + xesmf.

**mom6_forge** (`mom6_forge/`) generates horizontal grids (`grid.py`, `grid_creator.py`), vertical grids (`vgrid.py`, `vgrid_creator.py`), and bathymetry (`topo.py`, `topo_editor.py`).

## Linting

mom6_forge, CrocoDash, CrocoGallery use **black**. Always run before committing, except for CrocoDash, used dev_tools/black_CrocoDash.sh

```bash
# Apply
black <package_src_dir>
```

Per-package source paths:
- CrocoDash: `CrocoDash/`
- regional-mom6: `regional_mom6/`
- mom6_forge: `mom6_forge/`
- visualCaseGen: `visualCaseGen/` and `ProConPy/`
- CrocoGallery: `gallery/`
- pyDARTdiags: `src/pydartdiags/`

## Conda Environments

Each submodule under `regional_mom_workflows/` has its own dedicated conda environment that installs the package in editable mode (`-e ./`). Always use the matching env when running tests or working in a submodule:

| Submodule | Conda env |
|---|---|
| `CrocoDash` | `CrocoDash` |
| `mom6_forge` | `mom6_forge` |
| `regional-mom6` | `mom6-regional-dev` |
| `visualCaseGen` | `visualCaseGen` |

Example: `conda run -n mom6_forge pytest tests/`

## Running Tests

Each submodule has its own test suite. Run from within the submodule directory using the matching conda environment (see above).

**CrocoDash** (from `regional_mom_workflows/CrocoDash/`):
```bash
# Fast unit/integration tests
pytest --ignore=CrocoDash/visualCaseGen -m "not workflow" -vv --showlocals --tb=short

# Workflow tests (slower, may require data access)
pytest -m "workflow" -s --ignore=CrocoDash/visualCaseGen

# With coverage
pytest --ignore=CrocoDash/visualCaseGen -m "not workflow" --cov=CrocoDash --cov-report=xml --cov-branch
```

**regional-mom6** (from `regional_mom_workflows/regional-mom6/`):
```bash
pytest tests/
```

**mom6_forge** (from `regional_mom_workflows/mom6_forge/`):
```bash
pytest tests/
```

**visualCaseGen** (from `regional_mom_workflows/visualCaseGen/`):
```bash
pytest tests/
```
Tests are tiered: `1_unit/`, `2_integration/`, `3_system/`, `4_static/`.


## Submodule Management

Initialize or sync all submodules after clone or pull:
```bash
git submodule update --init --recursive
```

Several submodules contain nested submodules (e.g., `visualCaseGen` embeds `external/mom6_forge/` and `external/ipyfilechooser/`; `CrocoDash` embeds `rm6/` and `visualCaseGen/`). Always use `--recursive`.

When making changes that span the outer repo and a submodule, commit the submodule first, then update the pointer in the outer repo.

## Fast CrocoDash Case Setup (Minimal / NYF)

For quick test or reference cases, flat bathymetry, NYF compset — use this pattern with the `CrocoDash` conda env:

```python
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

CESMROOT = Path("~/work/installs/CROCESM_workshop_2025").expanduser()
CASEROOT = Path("~/croc_cases/<casename>").expanduser()
INPUTDIR = Path("/glade/u/home/manishrv/scratch/croc_input/<casename>")

grid = Grid(lenx=10.0, leny=10.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="<name>")
topo = Topo(grid, min_depth=10.0, git=False)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="<name>")

case = Case(
    cesmroot=CESMROOT, caseroot=CASEROOT, inputdir=INPUTDIR,
    compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
    ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid,
    atm_grid_name="T62", machine="derecho", project="ncgd0011", override=True,
)
case.configure_forcings(
    date_range = ["2020-01-01 00:00:00", "2020-01-09 00:00:00"]
)
case.process_forcings()
```

- **NYF compset**: `1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV` (same as CR_JRA alias but with `DATM%NYF`)
- **Forcings are required** — every CrocoDash case must call `configure_forcings` then `process_forcings`. There is no valid case without them.
- `case.setup` generates `Buildconf/*.input_data_list` (useful for checking the file manifest), but the case is not runnable until forcings are configured and processed.

## MCP Servers

Three MCP servers expose CROC functionality to LLM agents. All are private repos under the CROCODILE-CESM org.

| Server | Repo | Dev path | Purpose |
|--------|------|----------|---------|
| CrocoDash MCP | `CROCODILE-CESM/MCP_CrocoDash` (public) | `dev/MCP_CrocoDash/` | Grid creation, case setup, forcing config/processing |
| CESM Runner MCP | `CROCODILE-CESM/MCP_cesm_runner` (private) | `dev/MCP_cesm_runner/` | Case build, submit, xmlquery/change, log monitoring |
| Regional Ocean Debugger MCP | `CROCODILE-CESM/MCP_regional_ocean_debugger` (private) | `dev/MCP_regional_ocean_debugger/` | Log triage, MOM_input inspection, CFL checks, domain knowledge search |

### Full workflow with all three servers

A complete session — from blank slate to running model — looks like this:

**Step 1 — Define and set up the case (CrocoDash MCP)**
```
"Create a 1/4° case over the Gulf of Mexico for Jan–Feb 2020 using GLORYS forcing on Derecho"
→ create_grid → create_case → configure_forcings → process_forcings
```

**Step 2 — Build and run (CESM Runner MCP)**
```
"Build the case and submit it"
→ case_setup → case_build → case_submit
"Is it running?"
→ get_job_status → tail_log
"Change the run length to 5 days and resubmit"
→ xmlchange(STOP_N=5) → case_submit
```

**Step 3 — Debug if something goes wrong (Regional Ocean Debugger MCP)**
```
"It crashed — what happened?"
→ find_errors → classify_error → query_domain_knowledge
"What DT should I use for 1/4°?"
→ suggest_timestep(0.25)
"What do experts say about OBC sponge layers?"
→ query_domain_knowledge("OBC sponge")
"Show me the MOM_input timestep settings"
→ read_mom6_params(case_dir, filter="DT")
```

The three servers are designed to be called in sequence — CrocoDash sets up, CESM Runner drives the CIME lifecycle, and the Debugger closes the loop on failures.

### Wiring up to Claude Code (.mcp.json)

Create `.mcp.json` at the repo root (or `~/.claude/mcp.json` for global access).
Use the Python from the `CrocoDash` conda env since all three servers can share it:

```bash
# Find the right Python path
conda run -n CrocoDash which python
```

```json
{
  "mcpServers": {
    "crocodash": {
      "command": "/path/to/conda/envs/CrocoDash/bin/python",
      "args": ["/glade/u/home/manishrv/documents/croc/dev/MCP_CrocoDash/server.py"]
    },
    "cesm-runner": {
      "command": "/path/to/conda/envs/CrocoDash/bin/python",
      "args": ["/glade/u/home/manishrv/documents/croc/dev/MCP_cesm_runner/server.py"]
    },
    "ocean-debugger": {
      "command": "/path/to/conda/envs/CrocoDash/bin/python",
      "args": ["/glade/u/home/manishrv/documents/croc/dev/MCP_regional_ocean_debugger/server.py"]
    }
  }
}
```

Install all three into the env:
```bash
conda run -n CrocoDash pip install fastmcp
conda run -n CrocoDash pip install -e dev/MCP_cesm_runner/
conda run -n CrocoDash pip install -e dev/MCP_regional_ocean_debugger/
# CrocoDash MCP uses CrocoDash directly — no extra install needed
```

Initialize the knowledge base submodule (Regional Ocean Debugger):
```bash
cd dev/MCP_regional_ocean_debugger
git submodule update --init data/transcripts
```

### Fast iteration with crocontainer

Use **crocontainer** (`regional_mom_workflows/crocontainer/`) to run CESM interactively
inside a container — no PBS queue, no wait. The CESM Runner MCP manages the container
session; lifecycle tools (`case_build`, `case_submit`) route through it via `container=`.

**Runtimes:**
- **Derecho → Apptainer** — uses a writable sandbox built once from the registry image.
  `/glade` is bind-mounted transparently so all host paths work inside the container.
  CESM inputdata mounted directly from `/glade/campaign/cesm/cesmdata/inputdata`.
- **Laptop → Podman** — pulls `ghcr.io/crocodile-cesm/crocontainer:latest` directly.
  User specifies a local `inputdata_dir` (pre-downloaded NYF data, ~6.5 GB).

**One-time Derecho setup** (build the Apptainer sandbox, ~1 hr):
```bash
build_sandbox()   # via MCP, or:
qcmd -l walltime=03:00:00 -- apptainer build --sandbox \
  /glade/derecho/scratch/$USER/crocontainer_sandbox \
  docker://ghcr.io/crocodile-cesm/crocontainer:latest-amd64
```

**Typical fast-iteration session:**
```
start_container(scratch_dir="~/scratch/croc_scratch")
case_setup(case_dir, container="croc_session")
case_build(case_dir, container="croc_session")        # interactive, no queue
case_submit(case_dir, no_batch=True, container="croc_session")   # runs live
# Debugger MCP finds error → fix → resubmit in same conversation:
xmlchange(case_dir, "DT", "900")
case_submit(case_dir, no_batch=True, container="croc_session")
stop_container("croc_session")
```

### Knowledge base (Regional Ocean Debugger)

Backed by expert interview transcripts (`AidanJanney/RegionalMOM6_InterviewTranscripts`, private).
Git submodule at `dev/MCP_regional_ocean_debugger/data/transcripts/`.
**Do not make this repo public without authorisation.**
Topics: MOM6 configuration, OBC, tides, bathymetry, stability, BGC, regional ocean dynamics.

### MCP design principles (all three servers)

- **FastMCP** framework — consistent across all three
- **Stateless** — no in-memory state; each tool reads from the filesystem per call
- **File-backed** — config JSON, MOM_input, CaseStatus, etc. are the source of truth
- **No CI** for dev MCP repos — held to a lower standard than production submodules

## Development Workflow

- All remote repos are in the [CROCODILE-CESM GitHub org](https://github.com/CROCODILE-CESM)
- Use feature branches and open PRs for all non-trivial changes
- Each submodule is its own repo with its own CI (`.github/workflows/`): tests, coverage, docs, black check
- PRs should pass CI before merging
- `dev/` is for local experimentation — notebooks and scripts here are not held to the same standards as production submodule code
- **Always ask before committing or pushing.** Do not commit or push changes without explicit user approval, even after making requested edits.
