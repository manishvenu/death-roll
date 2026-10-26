# Declare each forcing's output files and preview them

## Why

Nothing in CrocoDash knows which files a forcing step writes. Several places guess, and
they disagree:
- **`is_file=`** on output params. The base `get_output_filepaths` returned only the
  flagged files that already existed. `validate_output_filepaths` then checked that
  those same files exist, so it was always true, and `validate_case()` never reported
  anything.
- **Four hand-written overrides:**
  - tides globbed `tu_*`/`tz_*`;
  - runoff resolved stored absolute paths;
  - CICE and WW3 looked in sibling directories.
- **A filename-prefix glob in `bundle()`** (`forcing_obc_segment_`, `init_`). It misses
  the MARBL tracer OBC files and copies the unfilled `init_*.nc` that MOM6 never reads.
  `fesedfluxred` had no `is_file`, so it was never bundled.

The dry run had the same problem. `preview` was an output in config.json that users
edited by hand, and only `ic` and `bc` honoured it, returning date pairs that the driver
threw away. Every other step ran for real during a "preview".

Later work in this series (skipping finished steps, fork copying files whose settings
match) needs one list of a step's files, computed from config.json before anything runs.

## What

This replaces closed #310 and #316, rebuilt on `Case.configurators()` and
`Case.workflow_context()` instead of the closed `ReadCrocoDashCase` (#312). It carries
one check from #313.

- **`BaseConfigurator.output_files(ctx) -> {process flag: [Path]}`.** Each configurator
  declares the model input files each of its steps writes. They are built from `ctx`
  and the configurator's own params, never from a stored absolute path, so the
  declarations still hold for a case read back from somewhere else. A glob is used only
  where the count depends on the data (WW3 spectra). The default is `{}`.
  - Conditions: the three filled IC files; one `forcing_obc_segment_NNN.nc` per
    boundary; with MARBL, one `<tracer>_obc_segment.nc` per tracer.
  - Tides: `tz_`/`tu_segment_NNN.nc` per boundary.
  - Chl, BGC IC, BGC iron (all three files) and BGC river nutrients: their file params,
    under `ocn/`.
  - Runoff: the smoothed map in `mapping/`, via a new `runoff.MAPPING_SUBDIR` that
    `configure()` and `process()` also use.
  - CICE: `ice/cice_forcing.nc`, only when restoring is on.
  - WW3: `wav/ww3.point*_spec.nc`, `spec.list` and `ww3_bounc.nml`, and nothing when the
    product is `none`.
- **Helpers on the base class:**
  - `get_output_filepaths(ctx, flag=None)`: the declared files that exist, with globs
    expanded;
  - `missing_output_files(ctx, flag=None)`;
  - `validate_output_filepaths(ctx)`.
- **Removed:** the `is_file=` keyword on `OutputParam`, `UserNLConfigParam` and
  `XMLConfigParam`; the four `get_output_filepaths` overrides; and
  `shareable.INPUTDIR_FILE_PREFIXES`.
- **BGCIronForcing writes to `ctx.output_path`**, the same directory it declares.
  Before, it built `inputdir/"ocn"` by hand.
- **`Case.validate_case()` really checks.** It uses `configurators()` and
  `workflow_context()`, so it also works on a case read back with `from_caseroot`.
- **Bundle copies the declared files** that exist, keeping the inputdir layout
  (`ocn/`, `ice/`, `wav/`, `mapping/`), instead of the prefix glob.
- **Preview:** `case.process_forcings(preview=True)`, `run_workflow(case, preview=True)`
  and `crocodash process --preview` print each requested step's declared files as `present` or `missing`, then return
  without processing anything.
  - Removed: the `preview` argument of `process_initial_condition` and
    `process_obc_conditions`, `WorkflowContext.preview`, the `preview` argument of
    `Case.workflow_context()`, and the conditions `preview` output in config.json.
  - Older config.json files that still have `conditions.outputs.preview` load fine: the
    tolerant reading from #325 ignores keys a class no longer declares.
- **Docs:** `--preview` on the CLI and process-forcings pages; the developer guide shows
  how to declare `output_files`; the bundle contents in shareable.md.

## Tests

- For every registered configurator, the files declared from a representative config
  are unique across all steps and all lie under the case's inputdir, even when the
  context points at a different inputdir from the one the case was configured with.
  (The one check carried from #313.)
- Adapted, not added:
  - the CICE, WW3, BGC and bundle tests call the new `ctx`-based helpers, and the bundle
    test now expects an undeclared `forcing_obc_segment_fake.nc` to be left out;
  - the `preview` arguments and config keys are dropped from the driver and conditions
    tests, and the CLI test now checks that `--preview` reaches `run_workflow`;
  - removed with the code they covered: the OBC engine's preview test, and a WW3 test
    that the old whole-directory listing skipped subdirectories.
- Real-case check (by hand, read-only), using copies of three cases' state files bumped
  to 1.2: `crocodash process --all --preview` on
  - `arctic_50km_cice_on` (CICE restoring): `ice/cice_forcing.nc`, 4 OBC and 3 IC files
    present;
  - `big_alaska_sea_ice_waves` (CICE + WW3): also the spectra, `spec.list` and
    `ww3_bounc.nml` present;
  - `so_bgc` (MARBL, GLOFAS runoff, never processed): every BGC, tracer OBC and
    `mapping/` file reported missing, and nothing ran.

## Notes for reviewers

- **`is_file=` is gone.** A configurator written outside this repo that passes it now
  gets a `TypeError`, and one that doesn't override `output_files` declares nothing.
- **config.json layout:** `conditions.outputs.preview` is no longer written. A CrocoDash
  from before #325 can't read the new file, but it can't read #325's versioned files
  either.
- **Bundle contents change:**
  - added: the MARBL tracer OBC files and `fesedfluxred`;
  - dropped: the unfilled `init_*.nc`, any other file that merely matched the old
    prefixes, and WW3's grid `.inp` files in `wav/`. The grid files are written when a
    case is created, so a forked case makes its own.
- **Restoring files on fork is not here.** Fork still copies only the bundle's `ocn/`
  and `wav/`. Copying the declared files back, only for steps whose settings match, is
  later work in this series.
- **Clash with #305's time windows.** That work adds `min_chunk_days`/`lookback_days` to
  the same IC/OBC engine signatures this PR drops `preview` from. Whichever lands second
  keeps their new arguments and leaves `preview` out.
- **MCP:** dev/MCP_CrocoDash's `preview=True` now gets the per-step file list on stdout
  rather than the IC/OBC date plans.

Closes #332

🤖 Generated with [Claude Code](https://claude.com/claude-code)
