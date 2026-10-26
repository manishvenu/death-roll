# Write user_nl and xml changes into each case's own caseroot

## Why

visualCaseGen keeps one process-wide `cvars`. Its CASEROOT, NINST, MACHINE and
MB_ATTEMPT_ID belong to whichever case was created last. Every user_nl and xml write
after creation went through it, so `configure_forcings()` refused to run on any case
except the one created last. That blocks configuring two cases in one notebook, and it
blocks working on a case read back from its caseroot.

## What

- **`user_nl_blocks.write(owner, model, groups, *, caseroot, ninst, tag=...)`**
  - `caseroot` and `ninst` are required keywords. The module no longer reads `cvars` or
    imports visualCaseGen.
  - Its own short formatter prints the summary that `append_user_nl(..., do_exec=False)`
    used to print.
  - `tag` is also on `strip` and `report_edits`. Its default, `"CrocoDash configure_forcings"`,
    keeps the marker lines byte-identical, so blocks in existing cases still parse.
- **A small `xmlchange(var, val, *, caseroot, is_non_local=False)` in `forcing/base.py`.**
  It runs `./xmlchange VAR=VAL [--non-local]` in the caseroot, with an argument list
  rather than a shell string. On failure it raises with stderr included.
- **Configurators write into `registry.case`.**
  - `BaseConfigurator.configure()` writes its user_nl blocks and calls
    `XMLConfigParam.apply(caseroot)` with the registry case's caseroot, and passes `case.ninst`.
  - StreamYears does the same.
- **`Case`:**
  - The CASEROOT guard and its docstring paragraph are deleted.
  - `session_id` and `grid_name` are captured once during creation.
  - `is_non_local` is computed once, right after `create_newcase`.
  - Every xmlchange CrocoDash makes after `create_newcase` names `self.caseroot`:
    `configure_forcings`' CALENDAR, RUN_STARTDATE, STOP_OPTION and STOP_N, and
    `_apply_final_xmlchanges`.
  - `cvars` is now read only in `__init__` and the `_configure_*` methods.
- **Runoff takes its grid from the case.** The runoff-to-ocean map has to start from the
  grid DROF runs on, so `rof_grid_name` and `rof_esmf_mesh_filepath` are no longer inputs.
  `configure()` reads the case's current ROF_GRID and ROF_DOMAIN_MESH with `./xmlquery`
  (a small `xmlquery` helper sits next to `xmlchange`) and records them in config.json
  for the process step. To map from another grid, e.g. a subset of the runoff data, set
  it on the case. The `case_cime` argument and the `cvars["CUSTOM_ROF_GRID"]` lookup are
  gone.

## Tests

- Two cases in one process each write their user_nl block and their xmlchange into
  their own caseroot (`test_base.py`, with subprocess mocked).
- Existing tests pass `caseroot`/`ninst` instead of patching `cvars`. The guard test
  and the assertion on visualCaseGen's log heading are removed.

## Notes for reviewers

- **Writes during creation are unchanged.** These still go through visualCaseGen:
  - the xmlchanges inside `CaseCreator.create_case` (grids, meshes, ROF_GRID, case.setup);
  - `_set_ww3_timesteps` and `_set_cice_ndtd` (`append_user_nl`).

  They run inside `Case.__init__`, while `cvars` still belongs to this case.
- **The runoff grid is the same as before for existing setups.** visualCaseGen's
  CaseCreator sets ROF_GRID to CUSTOM_ROF_GRID, and ROF_DOMAIN_MESH to
  `cime.get_mesh_path("rof", CUSTOM_ROF_GRID)` (case_creator.py:968-970), which is what
  Runoff used to compute. It is now read when configuring, so a later change to the
  case's ROF_DOMAIN_MESH is picked up. An existing config.json without the recorded grid
  asks for configure_forcings() to be rerun before processing runoff.
- **`shareable.py`: one import moved.**
  - `forcing.base` now exports its own `xmlchange`. `shareable.py`'s
    `from CrocoDash.forcing.base import *` would have shadowed visualCaseGen's, so that
    import now comes after the star imports.
  - shareable still writes through `cvars`. It creates the new case last, so its writes
    land there. It is deleted later in the series.
- **Swapping in visualCaseGen's helper later.** The helper's keyword is `is_non_local=`,
  as in visualCaseGen's `xmlchange`. Once visualCaseGen's version takes `caseroot=`, the
  swap is an import change.
- **`CrocoDash.forcing` no longer imports visualCaseGen,** so importing it (e.g. for
  `crocodash process`) no longer builds visualCaseGen's GUI.
- **Log output changes slightly.**
  - The title is plain text (no ANSI color).
  - With several instances, each file now lists its own entries. Before, the first
    instance's entries were shown under every file.
- **A configurator without a registry case passes `caseroot=None`.** This only happens
  in tests. The real writers then raise a TypeError; they never write into the current
  directory.
- **Real-case check still to run by hand:** on Derecho, create two cases in one notebook,
  then configure the first and then the second.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
