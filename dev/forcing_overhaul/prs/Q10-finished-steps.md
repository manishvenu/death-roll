# Skip forcing steps that already finished

## Why

`process_forcings` reruns every selected step every time. Rerunning a case after one
step failed, or after adding one component, repeats hours of work that is already done.

The engines do skip a final file that already exists (`obc.py`'s merge, `mom6.py`'s IC
fill and BGC split). That is how a crashed run resumes. It also means that rerunning a
step does not regenerate its files: when a step's configuration changes, or the user
reruns it on purpose, the old files stay.

## What

This replaces closed #317. It is rebuilt on the `Case` that `run_workflow` now receives
and on each configurator's declared `output_files`, which come from earlier work in this
series. Changes from #317:
- **Names:** `process_fingerprint` becomes `step_settings`, and `process_record.json`
  becomes `extract_forcings/finished_steps.json`.
- **Versioned file, read as a cache:** `{"schema_version": "1.0.0", "steps": {flag:
  {"settings", "files"}}}`. If the file is missing, no step counts as finished. If it is
  unreadable, malformed or from another major version, a warning is printed and the file
  is ignored. A run never fails because of it. Writes are atomic (`.tmp` +
  `os.replace`), as in #317.
- **Portable settings:** in the recorded settings, the case's inputdir and cesmroot
  become `$INPUTDIR` and `$CESMROOT`. The same configuration in another inputdir (a
  forked or bundled case) therefore compares equal.
- **`process_version`:** a class attribute, default 1, that is part of the settings.
  Bump it when a step's files change for the same configuration, so that existing cases
  rerun the step.
- **`clean`:** before a step that has an entry runs again (forced, or its settings
  changed), it deletes the files the entry lists and the step's declared files that
  exist, so they are regenerated. It deletes nothing for a step with no entry, such as a
  first run or files from an older CrocoDash. It deletes only paths inside the inputdir.
- **Steps that declare no files are never recorded**, so they always run. In #317, a
  step with nothing declared was recorded as done and then skipped forever.
- **`--force` applies to the requested steps only.** A dependency that runs only because
  a requested step needs it (runoff for `--bgcrivernutrients`) is still skipped when
  finished. It is not regenerated.
- **Dropped:** #317's `Case._print_forcing_files` at the end of `configure_forcings`.
  `--preview` reports the same thing.

In detail:
- `BaseConfigurator.step_settings(config)` returns `process_version`, the
  configurator's own config.json entry and the entries named in `depends_on_outputs`.
  The overrides from #317 are kept: conditions uses the slice of its entry that
  `stale_outputs()` compares, so turning tides on doesn't rerun ic/bc; CICE and WW3 add
  the conditions dates.
- `driver.portable_settings(configurator, config, inputdir, cesmroot)` is the JSON form
  that gets recorded and compared. `read_finished_steps(inputdir)` and
  `clean(ctx, configurator, step, entry)` are also in the driver.
- A step is finished when its entry's settings equal the current ones and none of its
  declared files is missing. A finished step prints `[skip] <step>` and doesn't run.
  `run_workflow(..., force=True)`, `Case.process_forcings(force=True)` and
  `crocodash process --force` rerun it.
- Each step that declares files is recorded after it runs, with the files that exist. A
  step that didn't write every declared file prints a warning. It is still recorded,
  so the next run cleans it and runs it again.
- `--preview` marks each step `finished` or `would run`, using the same check.
- Docs:
  - the process-forcings page has a short section on skipping and `--force`;
  - the CLI page documents `--force`;
  - the developer guide says when to override `step_settings()` and when to bump
    `process_version`.

## Tests

- A finished step is skipped on rerun.
- `force=True` reruns a finished step, and its old file is gone when the step starts.
- `portable_settings` is equal for the same config under two different inputdirs and
  cesmroots.
- The existing runoff→bgcrivernutrients dependency test now gives its fake case an
  inputdir and a map name, because the driver reads each step's declared files.

## Notes for reviewers

- **What `--force` regenerates.** `clean` deletes only declared final files. On
  `--force`, raw and regridded chunks in `extract_forcings/` and the unfilled
  `init_*.nc` are reused, and the finals are rebuilt from them. When the conditions
  settings change, `configure_forcings` already removes those intermediates
  (`stale_outputs`).
- **Settings are still specific to a case** in two ways. Runoff, chl and BGC record
  `case_session_id` and `case_grid_name`. Fork has to reuse the source's session id and
  grids for those steps' settings to match.
- **A code change alone doesn't rerun a step.** The settings cover configuration only.
  Any fix that changes a step's output for the same configuration has to bump that
  configurator's `process_version`.
- **`finished_steps.json` is not bundled yet.** Fork and bundle carry it over in later
  work in this series. Until then, a forked case reruns every step once.
- **Real-case check (by hand, on Casper):**
  - a second `crocodash process --all` prints `[skip]` for every step;
  - `--force --bc` rewrites the OBC files (check their mtimes);
  - `--preview` lists every step as `finished` or `would run`, with its files.

Closes #336

🤖 Generated with [Claude Code](https://claude.com/claude-code)
