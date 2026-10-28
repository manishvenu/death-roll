## Why

`config.json` is what `process_forcings`, `crocodash process` and `crocodash dump` read
back, often with a newer CrocoDash than the one that wrote it. Today:
- **Old cases break.** `BaseConfigurator.deserialize` raises `KeyError` for any declared
  input or output missing from the file. 53 of the 69 config.json files under my
  `croc_input` fail on main, because they predate the `ENABLE_BUGS_BY_DEFAULT` output.
  Every PR that adds a param would break them all again.
- **No version check.** Nothing records which CrocoDash wrote the file, and seven
  places read it with a bare `json.load`.
- **dump and fork lose the user's arguments.** The yaml round trip drops
  `function_overrides`, so dump and fork silently revert them to the defaults.

## What

- **Tolerant reading** (`BaseConfigurator.deserialize`) this makes our config.json way more cross version compatible!!:
  - an input missing from an entry takes its constructor default;
  - an output missing from it, or a missing input left `None` that isn't declared
    `optional=True`, can't be known: the entry still loads, and the step that reads it
    raises `ReconfigureRequired`, so the steps that don't need it still run. A `None`
    default is often a placeholder `configure_forcings()` fills in (a calendar, a start
    date), so only inputs where `None` really means "none" are optional (CICE's
    product and function names, WW3's overrides and step days);
  - keys a class no longer declares are ignored;
  - a missing input with no default, an entry the constructor now rejects (`ValueError`
    or `TypeError`), or an entry for a configurator that no longer exists, raises a
    new `ReconfigureRequired` ("rerun configure_forcings()").
- **Versioning:** `write_config`/`read_config` in `forcing/base.py`.
  - config.json gets a `schema_version` (1.0.0), and an unversioned file reads as 1.0.0.
  - A file from a newer CrocoDash is refused ("upgrade CrocoDash"); an older one with
    no migration asks for `configure_forcings()` again, not a new case.
  - `CONFIG_MIGRATIONS` is the hook for the first real rename.
  - Every reader and writer goes through these two functions.
  - Every loop over config.json goes through `iter_configurator_entries()`, which skips
    the top-level `CONFIG_META_KEYS`.
- **File checks:** Chl and BGCRiverNutrients no longer check that their input file exists
  in `validate_args`, which also runs when config.json is read back, possibly on another
  machine. `BaseConfigurator.configure()` warns about every missing `InputFileParam` file
  instead (Runoff's mesh paths included); the process step still fails if the file is
  missing. Runoff's `validate_args` now calls the base check and raises instead of
  asserting.
- **Round trip:** `generate_configure_forcing_args` hands back `function_overrides`: the
  stored access-method arguments that differ from their defaults. `json_safe()` is the
  one Path-to-string rule for those arguments, used when writing them and when
  comparing them.
- **Dead code:** the never-used `run_configurators(config_path)` branch is removed.
- **Docs:** new developer page `config_compatibility.md` on how to change a configurator
  without breaking existing cases.

## Tests

- An entry with an undeclared key and missing params still loads; reading a missing
  output or a non-optional input left `None` raises `ReconfigureRequired`, an optional one
  reads `None`, and a missing input with no default raises on loading.
- An unversioned config.json reads as 1.0.0, and a newer one is refused.
- The access-method arguments a user changed survive `generate_configure_forcing_args`.
- No module outside `forcing/base.py` builds a config.json path, so no reader skips the
  version check.
- Real-case check (by hand): of the 69 config.json files under `croc_input`, 66 load.
  The other 3 are CICE cases from before CICE restoring required a product; they now
  raise `ReconfigureRequired` instead of crashing. On main, 16 of 69 load. This reads
  config.json alone: `process`, `dump` and `bundle` first read the case's state file,
  which refuses a case created before #265, so tolerant reading applies to cases that
  check accepts (see `config_compatibility.md`).

## Notes for reviewers

- `ReconfigureRequired` subclasses `ValueError`. `configure_forcings` already treats an
  unreadable previous config.json as "no record", so an incompatible old file just means
  its forcing files get regenerated.
- No PR in this series needs a version bump: tolerant reading absorbs added and removed
  params. Bump only for renames, with a migration.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

