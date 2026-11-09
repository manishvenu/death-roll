# Write user_nl and xml changes into each case's own caseroot

## Why

visualCaseGen keeps one process-wide `cvars`. Its CASEROOT, NINST, MACHINE and
MB_ATTEMPT_ID belong to whichever case was created last. Every user_nl and xml write
after creation went through it, so `configure_forcings()` refused to run on any case
except the one created last. That blocks configuring two cases in one notebook, and it
blocks working on a case read back from its caseroot.

## What

- **visualCaseGen's `xmlchange` and `user_nl_blocks`, given the caseroot.**
  - Every xmlchange after `create_newcase` calls visualCaseGen's
    `xmlchange(..., caseroot=)` (ESMCI #51, merged). It runs `./xmlchange` in that
    caseroot with an argument list and raises with stderr on failure.
  - user_nl blocks are written with visualCaseGen's `user_nl_blocks` (ESMCI #52), passing
    `caseroot`, `ninst` and `tag`. CrocoDash's copy of the module and its tests are
    deleted.
  - `USER_NL_TAG = "CrocoDash configure_forcings"` in `forcing/base.py` keeps the marker
    lines byte-identical, so blocks in existing cases still parse.
- **Configurators write into `registry.case`.**
  - `BaseConfigurator.configure()` writes its user_nl blocks and calls
    `XMLConfigParam.apply(caseroot)` with the registry case's caseroot, and passes `case.ninst`.
- **`Case`:**
  - The CASEROOT guard and its docstring paragraph are deleted.
  - `session_id` and `grid_name` are captured once during creation.
  - `is_non_local` is computed once, right after `create_newcase`.
  - Every xmlchange CrocoDash makes after `create_newcase` names `self.caseroot`:
    `configure_forcings`' CALENDAR, RUN_STARTDATE, STOP_OPTION and STOP_N, and
    `_apply_final_xmlchanges`.
  - `cvars` is now read only in `__init__` and the `_configure_*` methods.
- **Stream years are xml variables: a `DATM` configurator replaces StreamYears.**
  - CROCODILE-CESM/CDEPS#3 makes the interannual JRA, CORE2 IAF and GLOFAS streams read
    their years from `DATM_YR_*`/`DROF_YR_*`, and sets each compset's default range to the
    years its data covers.
  - `forcing.datm.stream_years(caseroot, component)` works the years out from the case's
    xml with `xmlquery`: `COMPSET`, `SRCROOT`, and the run dates from `RUN_STARTDATE`,
    `STOP_OPTION` and `STOP_N`.
    - `ALIGN` and `START` are the year before the run, and `END` the year after it.
      That gives the time interpolation data at both ends of the run.
    - The range is kept inside the data's years, which are the compset's CDEPS defaults.
      They're read with CIME's `Component.get_default_value`, the same call
      `create_newcase` uses for compset defaults.
    - Each model year then reads the same data year, and CDEPS lists only those years'
      files.
  - `configure_forcings` now sets `CALENDAR`, `RUN_STARTDATE`, `STOP_OPTION` and `STOP_N`
    before the configurators run, so they can read them.
  - The new `DATM` configurator (`forcing/datm.py`) is required for the interannual JRA
    and CORE2 IAF modes; RYF and NYF don't need it. It takes no arguments and declares
    the three `DATM_YR_*` as `XMLConfigParam`s.
  - Runoff xmlchanges `DROF_YR_*` itself when DROF is a JRA or GLOFAS mode. An NYF DROF
    has none, and this keeps the run dates out of Runoff's config.json entry and the
    map made from it.
  - Deleted: StreamYears, `cdeps_streams.py`, and the `user_nl_datm_streams`/
    `user_nl_drof_streams` blocks they wrote.
- **Runoff takes its grid from the case.** The runoff-to-ocean map has to start from the
  grid DROF runs on, so `rof_grid_name` and `rof_esmf_mesh_filepath` are no longer inputs.
  `configure()` reads the case's current ROF_GRID and ROF_DOMAIN_MESH with `./xmlquery`
  (a small `xmlquery` helper in `forcing/base.py`) and records them in config.json for the
  process step. To map from another grid, e.g. a subset of the runoff data, set it on the
  case. The `case_cime` argument and the `cvars["CUSTOM_ROF_GRID"]` lookup are gone.

## Tests

- Two cases in one process each write their user_nl block and their xmlchange into
  their own caseroot (`test_base.py`, with subprocess mocked).
- A JRA 1.5 and GLOFAS run through 2023 gets one extra year either side, kept inside each
  dataset (2022-2023 for JRA, 2022-2024 for GLOFAS), and a climatology gets none
  (`test_datm.py`, `xmlquery` and CIME's lookup mocked).
- Existing tests pass `caseroot`/`ninst` instead of patching `cvars`. The guard test
  and the assertion on visualCaseGen's log heading are removed. The user_nl_blocks tests
  moved to visualCaseGen with the module. StreamYears' tests are deleted with it.

## Notes for reviewers

- **Waits for ESMCI #52 and CDEPS#3.** This PR stays a draft until both are in.
  - The visualCaseGen pin is unchanged, and it has neither #51 nor #52. CI fails until the
    pin moves to ESMCI main after #52 merges.
  - CESM `crocodash` uses ESCOMP `cdeps1.0.101`, which doesn't have CDEPS#3. On it, the
    configuring a JRA case stops with "This case's DATM streams don't read DATM_YR_*",
    and DROF keeps its defaults.
  - It was checked locally against ESMCI main with #52 merged in:
    - every module imports;
    - two cases each write into their own caseroot, with a fake `./xmlchange` in each;
    - the strip-and-restore cycle `configure_forcings()` runs works;
    - the stream years, through a fake caseroot whose `./xmlquery` and `./xmlchange`
      are scripts, with CIME's real lookup against a CESM with CDEPS#3:
      - JRA 1.5 in 2023 gets 2022-2023;
      - JRA 1.4 with GLOFAS in 2010 gets 2009-2011;
      - RYF doesn't need DATM.

      Against CESM `crocodash`, DATM stops with the message above.
- **#52's new duplicate check doesn't affect CrocoDash.** That check rejects a variable
  set in two blocks.
  - CrocoDash's 66 user_nl parameters are all distinct.
  - The 21 CrocoDash blocks in existing cases on GLADE share no variable.
- **What changes in the stream years.**
  - StreamYears added one more leading year (two before the run). It now adds one on
    each side.
  - GLOFAS runoff is now aligned with any DATM, not only with a JRA one.
  - Run years outside the data now raise when configuring. StreamYears warned and kept
    the defaults, so those runs read other years' data.
  - An existing JRA case's `config.json` still has a StreamYears entry, and
    `crocodash process` stops on it ("Configurator Not Found") until
    `configure_forcings()` runs again. That rerun also removes the old
    `user_nl_datm_streams` block.
- **Writes during creation are unchanged.** These still go through visualCaseGen's `cvars`:
  - the xmlchanges inside `CaseCreator.create_case` (grids, meshes, ROF_GRID, case.setup);
  - `_set_ww3_timesteps` and `_set_cice_ndtd` (`append_user_nl`).

  They run inside `Case.__init__`, while `cvars` still belongs to this case.
- **The runoff grid is the same as before for existing setups.**
  - visualCaseGen's CaseCreator sets ROF_GRID to CUSTOM_ROF_GRID, and ROF_DOMAIN_MESH to
    `cime.get_mesh_path("rof", CUSTOM_ROF_GRID)` (case_creator.py:968-970). That is what
    Runoff used to compute.
  - The mesh is now read when configuring, so a later change to the case's
    ROF_DOMAIN_MESH is picked up.
  - An existing config.json without the recorded grid asks for configure_forcings() to be
    rerun before processing runoff.
- **Log output changes slightly.**
  - The title is plain text (no ANSI color).
  - With several instances, each file now lists its own entries. Before, the first
    instance's entries were shown under every file.
- **A configurator without a registry case passes `caseroot=None`.** That happens only
  when a configurator is built directly, as in tests.
  - Its user_nl write raises.
  - visualCaseGen's `xmlchange` falls back to its own CASEROOT.

  Every real configure goes through the registry, which always has the case.
- **Real-case check still to run by hand:** on Derecho, create two cases in one notebook,
  then configure the first and then the second.

Closes #250

🤖 Generated with [Claude Code](https://claude.com/claude-code)
