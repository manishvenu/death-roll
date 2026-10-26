# Read config.json tolerantly and version it

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

- **Tolerant reading** (`BaseConfigurator.deserialize`):
  - an input missing from an entry takes its constructor default;
  - an output missing from it stays `None`;
  - keys a class no longer declares are ignored;
  - a missing input with no default, or an entry the constructor now rejects, raises a
    new `ReconfigureRequired` ("rerun configure_forcings()").
- **Versioning:** `write_config`/`read_config` in `forcing/base.py`.
  - config.json gets a `schema_version` (1.0.0), and an unversioned file reads as 1.0.0.
  - A file from a newer CrocoDash is refused.
  - `CONFIG_MIGRATIONS` is the hook for the first real rename.
  - Every reader and writer goes through these two functions.
  - Every loop over config.json skips the top-level `CONFIG_META_KEYS`.
- **File checks:** Chl and BGCRiverNutrients no longer check that their input file exists
  in `validate_args`, which also runs when config.json is read back, possibly on another
  machine. They warn in `configure()` instead; the process step still fails if the file
  is missing. Runoff's `validate_args` now calls the base check.
- **Round trip:** `generate_configure_forcing_args` hands back `function_overrides`: the
  stored access-method arguments that differ from their defaults.
- **Dead code:** the never-used `run_configurators(config_path)` branch is removed.
- **Docs:** new developer page `config_compatibility.md` on how to change a configurator
  without breaking existing cases.

## Tests

- An entry with an undeclared key and a missing output still loads; a missing required
  input raises `ReconfigureRequired`.
- An unversioned config.json reads as 1.0.0, and a newer one is refused.
- Three config.json files written by real cases still load (golden configs: an old
  StreamYears/runoff case, a MARBL case, a WW3/CICE case; personal paths replaced).
- The access-method arguments a user changed survive `generate_configure_forcing_args`.
- No module outside `forcing/base.py` builds a config.json path, so no reader skips the
  version check.
- Real-case check (by hand): of the 69 config.json files under `croc_input`, 66 load.
  The other 3 are CICE cases from before CICE restoring required a product; they now
  raise `ReconfigureRequired` instead of crashing. On main, 16 of 69 load.

## Notes for reviewers

- `ReconfigureRequired` subclasses `ValueError`. `configure_forcings` already treats an
  unreadable previous config.json as "no record", so an incompatible old file just means
  its forcing files get regenerated.
- No PR in this series needs a version bump: tolerant reading absorbs added and removed
  params. Bump only for renames, with a migration.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
