# Read a case back from its caseroot

## Why

A `Case` only exists in the Python session that created it. To get one back for an
existing caseroot you have to recreate the case, which reruns `create_newcase` and
`case.setup`. So everything that works on an existing case reads the files itself:
the forcing driver and `crocodash process` each open `_crocodash_state.json` and
`config.json` on their own. A restarted notebook can't simply pick its case up again.
The rest of the forcing overhaul (configuring an existing case, bundle, fork) needs a
case read back from disk, through one reader rather than several.

The state file also lacks two things a read-back needs:
- the ESMF mesh path, which runoff requires (bundle globs for it today);
- a record of what creating the case left in the caseroot, so that later PRs can tell
  the user's own changes apart from CrocoDash's.

## What

- **`Case.from_caseroot(caseroot, *, cesmroot=None)`** builds a `Case` from the state
  file without `create_newcase`, `case.setup` or visualCaseGen. `cesmroot=` replaces a
  CESM tree that has moved; it is never saved. This is the one reader: it replaces the
  `ReadCrocoDashCase` idea from closed #312, which added a second, separate reader in
  `forcing/base.py`.
- **One construction path.** `Case.__init__` now ends by calling the same `_bind()` that
  `from_caseroot` uses, on the state file it has just written, so the two can't drift
  apart. `_bind` sets plain attributes, because `configure_forcings()` still passes the
  case's `__dict__` to the configurators as `case_*` inputs.
- **Lazy loading:**
  - `ocn_grid`, `ocn_topo`, `ocn_vgrid` and the read-only CIME case load from their files
    on first use. A created case keeps the objects it was given.
  - `forcing_config` rereads config.json on every access, so it never goes stale after a
    reconfigure.
  - New `configurators()`, and `workflow_context()`: the `WorkflowContext` the driver
    used to build itself.
- **Driver:** `run_workflow(case, *, preview=False, **flags)` takes the case instead of a
  config.json path. It reads no files itself, and `_load`/`_build_context` are gone. It
  doesn't import `CrocoDash.case`, since case.py imports the driver.
- **CLI:** `crocodash process --caseroot X` uses `Case.from_caseroot(X)`. `--config` and
  running from inside `extract_forcings/` take the caseroot from that config.json and do
  the same.
- **State 1.2.0** records `esmf_mesh_path` and a `created` snapshot, taken after the last
  creation-time xmlchange and user_nl write: `{replay_lines, user_nl: {file: text},
  xml_files}`.
  - A 1.1 or unversioned state file is refused ("Recreate the case with the current
    version of CrocoDash"). There is no migration.
  - Both new keys are in `DERIVED_KEYS`, so `crocodash dump` doesn't pass them to `Case()`.
- **Docs:**
  - the state-file example and version rules in compsets_and_inputs.md;
  - the Python API section of the process-forcings page now uses `Case.from_caseroot`;
  - the description of the `--config` flag.

## Tests

- A fake 1.2 caseroot (a state file and a config.json, with nothing at its cesmroot or
  grid paths) reads back and exposes its configurators, without CIME or visualCaseGen.
- A caseroot with a 1.1 state file is refused.
- Adapted, not added:
  - the driver tests pass a stand-in case instead of mocking the state file;
  - the `crocodash process` tests mock `Case.from_caseroot` instead of `case_state.read`;
  - in the `check_version` cases, an unversioned state is now refused.
- Real-case check (by hand, read-only), on a copy of the `so_bgc` case's state (MARBL,
  GLOFAS runoff, CICE) bumped to 1.2 by hand:
  - it reads back in about 1 ms with nothing loaded, and `configurators()` returns all
    8 entries;
  - the grid, topo, vgrid and CIME case load on first use;
  - `run_workflow(case, preview=True, ic=True, bc=True)` runs;
  - `crocodash process --caseroot` on it prints the help;
  - the real caseroot, still at 1.1, is refused;
  - nothing under the real caseroot or inputdir changed.

## Notes for reviewers

- **Existing cases must be recreated.** Every case created before this PR has a 1.1 (or
  older) state file, so `crocodash process`, `crocodash dump`, `bundle` and `duplicate`
  refuse it with the "Recreate the case" message. This is the agreed no-migration policy;
  it belongs in the release notes.
- **`override` now only applies at creation.** `_bind` sets `override=False`, so a case
  created with `override=True` no longer deletes its whole `extract_forcings/` (raw data
  included) when `configure_forcings()` reruns. `stale_outputs()` still removes the files
  made for an earlier configuration. The `rmtree` branch that became dead is removed.
- **A read-back case can't be configured yet.** `configure_forcings()` still writes
  through visualCaseGen's global state; later PRs in this series remove that.
- **`--config` only locates the case.** The case's own `extract_forcings/config.json` is
  processed, so a copy of config.json kept elsewhere is no longer used as given.
- **MCP:** dev/MCP_CrocoDash calls `run_workflow(config_path=...)` in
  `tools/_bg_worker.py` and twice in `tools/case.py`. After this merges, those calls need
  `run_workflow(Case.from_caseroot(caseroot), ...)`.
- `validate_case()` still uses the `fcr` that `configure_forcings()` sets, so it doesn't
  work on a read-back case yet.

Closes #329

🤖 Generated with [Claude Code](https://claude.com/claude-code)
