# Report: output-file-awareness stack (#312 → #317), #321, #322, and the uncommitted config-schema-version diff

Notation used below:
- `tip:` means origin/skip-finished-forcing-steps.
- `csv:` means the worktree `CrocoDash-worktrees/config-schema-version`, with its uncommitted diff applied on origin/main 510139f9.
- Other refs are named in full. Line numbers are for the ref given.

## A. Topology and review status (FACTS)

- **Stack shape.** The stack is linear and each branch is 0 commits behind its parent:
  - main b8b87f04
  - #312 fc873e01
  - #310 7b368d29
  - #313 5de7b034
  - #315 f15de95d and 6ec5f4e3
  - #316 92435492
  - #317 72226b94
- **Drift from main.** The bottom of the stack, #321 (d5fec5e6) and #322 (a684f21f) are each 2 commits behind main. Those two commits, #323 and #324, only touch `.github/workflows/testing.yml`, so there is no code drift.
- **Reviews.** No PR has a human review or an inline thread. `gh api …/pulls/N/comments` returns nothing for all 8 PRs, and `reviews` is `[]`. The only comments are the codecov and docs-preview bots.
- **Codecov gaps worth knowing:**
  - #310: `case.py` patch coverage is 33% (the `validate_case` change).
  - #316: `driver.py` patch coverage is 81.8%.
  - #317: the `process_fingerprint` overrides in `cice.py` and `ww3.py` are at 50% patch coverage, and `mom6.py` at 66.7%.

## B. What each PR does (FACTS)

**#312 read-crocodash-case (→ main).**
- **Purpose:** one reader, which doesn't need CIME, for a case on disk.
- **API added:** `forcing.base.ReadCrocoDashCase(caseroot)` (read-crocodash-case:base.py:110).
  - Attributes: `caseroot`, `state` (from `case_state.read`), `inputdir`, `ocn_dir = inputdir/"ocn"`, and `forcing_config`. `forcing_config` is config.json read with `json.load`, or `{}` if the file is missing.
  - Method: `workflow_context(config=None, preview=False)`.
- **API removed:** `driver._load(config_path)` and `driver._build_context(config, state, inputdir, preview)`.
- **API changed:**
  - `CaseBundle` now subclasses `ReadCrocoDashCase`.
  - `run_workflow` reads config.json, then calls `ReadCrocoDashCase(config["caseroot"])`.
- **Files:** `base.py`, `driver.py`, `shareable.py`, and `tests/forcing/test_driver.py`, whose `case_state` patch target moves to `CrocoDash.forcing.base.case_state`. Also a new `tests/shareable/test_read_case.py`.
- **Why the class lives in `base.py`:** the PR body says it avoids an import cycle (shareable → recipe → case → driver).
- **Persisted files:** none.

**#310 declared-output-files.**
- **Purpose:** each configurator declares its model-input files from `ctx`. This replaces the `is_file` flag, four hand-written overrides, and the filename-prefix glob in `bundle()`.
- **API:**
  - `BaseConfigurator.output_files(ctx) -> {flag: [Path]}`, which returns `{}` by default (tip:base.py:780).
  - `get_output_filepaths(ctx, flag=None)` (tip:798). Its argument used to be `ocn_ice_directory`.
  - New `missing_output_files(ctx, flag=None)` (tip:808).
  - `validate_output_filepaths(ctx)` (tip:817).
  - New `ReadCrocoDashCase.configurators()` (tip:141-147), which filters only `key != "caseroot"` (tip:146).
- **Removed:**
  - The `is_file=` keyword on `OutputParam`, `UserNLConfigParam` and `XMLConfigParam`. This breaks any configurator outside the repo that passes it.
  - The `get_output_filepaths` overrides in tides, runoff, cice and ww3.
  - `shareable.INPUTDIR_FILE_PREFIXES`.
- **Added:** `runoff.MAPPING_SUBDIR`.
- **Behaviour changes:**
  - BGCIronForcing writes to `ctx.output_path`.
  - Bundles now include the MARBL tracer OBC files and `fesedfluxred`, and drop the unfilled `init_*.nc`.
  - `validate_case` really checks (tip:case.py:1142).
- **Persisted files:** none.

**#313 output-files-reference-check.**
- Tests and docs only, about 516 changed lines.
- Test-only helpers check that settings and declarations agree in both directions.
- New slow test `tests/forcing/test_output_files.py`. It has a `_BUILDERS` registry, and a fast test fails when a process flag is missing from it.
- `check_glade` exemption for the new test file.
- Slow-test results on Casper:
  - chl and runoff skip with a reason;
  - bgcrivernutrients was killed on a login node.

**#315 shareable-restore-output-files.**
- **API:** new `shareable._copy_output_files(source_inputdir, case)` (tip:shareable.py:359-376). It copies each file the new case declares, at the same relative path, and only if the destination doesn't exist.
- **`duplicate_case`:**
  - now uses `rcc.ocn_dir` and `rcc.inputdir` (tip:402);
  - then calls `_copy_output_files` (tip:412).
- **`ForkBundle.fork`:**
  - copies the bundle's `ocn/` (tip:553-557), then calls `_copy_output_files` (tip:559);
  - the copy of the bundle's `wav/` directory was removed.
- **What it fixes:**
  - fork lost `ice/` and `mapping/`;
  - duplicate lost `mapping/`.

**#316 forcing-preview-dry-run.**
- `run_workflow(preview=True)` and `crocodash process --preview` print each step's declared files as present or missing, then return `{}` (tip:driver.py:175-186).
- **Removed:**
  - `WorkflowContext.preview`;
  - the `preview` argument of `workflow_context`;
  - the `preview` argument of `ic.process_initial_condition` and `obc.process_obc_conditions`;
  - ConditionsConfigurator's `preview` ConfigOutputParam, so `conditions.outputs.preview` is no longer written to config.json. **This changes config.json's layout.**
- `resolve_components` now excludes `"preview"`.
- The PR body flags two things:
  - a conflict with #305 (whichever merges second should keep the deletion);
  - an unrelated slow-test failure that also happens on main.

**#317 skip-finished-forcing-steps.**
- **Signatures:**
  - `run_workflow(config_path, preview=False, force=False, **flags)` (tip:driver.py:106);
  - `Case.process_forcings(force=False, **kwargs)`;
  - CLI flag `--force`.
- **New driver API:**
  - `RECORD_FILENAME` (tip:35);
  - `read_record(inputdir)` (tip:61-68);
  - `is_done(configurator, flag_name, ctx, record)` (tip:85-93);
  - `summarize_paths(paths, limit=5)`.
- **New driver internals:** `_record_path`, `_write_record` (tip:71-77, which writes a `.tmp` file then `os.replace`), and `_fingerprint` (tip:80-82).
- **`BaseConfigurator.process_fingerprint(cls, config)`** (tip:base.py:821-830) returns the configurator's own config.json entry plus the entries named in `depends_on_outputs`. Overrides:
  - Conditions (tip:mom6.py:798-802) reuses `_fingerprint`;
  - CICE (tip:cice.py:467) and WW3 (tip:ww3.py:585) add the conditions dates.
- **`Case._print_forcing_files(config)`** (tip:case.py:1122-1140) runs at the end of `configure_forcings` (tip:666).
- **New persisted file:** `process_record.json` (schema in section C).

**#321 load-mom-rps-param-reader (→ main).**
- New `shareable._load_FType_MOM_params(cesmroot)`. It puts `MOM_RPS` on `sys.path` only for the duration of `exec_module`.
- `CaseBundle._read_user_nl_lines_as_obj` uses it, and so does `tests/user_nl_helpers.mom_parser`.
- **Persisted files:** none.

**#322 clean-temp-case-output (→ main).**
- New `shareable._remove_case_output_dirs(caseroot)`, which removes the temporary case's EXEROOT and RUNDIR via `xmlquery` (guarded).
- `identify_non_standard_case_info` wraps the temporary case creation and the diff in a `try/finally` that calls it.
- **Persisted files:** none.

**#321 and #322 vs. the stack.** I checked the hunk ranges in main coordinates. There is no textual overlap with the stack, with each other, or with csv:
- `shareable.py`:
  - stack: 44-51, 120-181, 314-332, 376-414, 548-564;
  - #321: 218-234, 745;
  - #322: 275-287, 762+;
  - csv: 37-42, 168-178, 320-326.
- `tests/shareable/test_bundle.py`:
  - stack: 197-208, 250-258;
  - #321: 1-7, 309;
  - #322: 140-153.

**config-schema-version (uncommitted, on main).**
- **New in `base.py`:**
  - `CONFIG_FILENAME` (csv:base.py:25);
  - `CONFIG_SCHEMA_VERSION = "1.0.0"` (:26);
  - `CONFIG_UNVERSIONED = "1.0.0"` (:28);
  - `CONFIG_META_KEYS = {"schema_version", "caseroot"}` (:29);
  - `write_config(path, config)` (:32), which puts `schema_version` as the first key;
  - `read_config(path)` (:39-45), which calls `setdefault` and then `case_state.check_version(..., supported=CONFIG_SCHEMA_VERSION)`.
- **Changed:** `case_state.check_version(state, state_path, supported=SCHEMA_VERSION)` (csv:case_state.py:68).
- **Reader and writer sites moved onto the helpers:**
  - `case.py` 559/564/659/739-740;
  - `cli.py` 48-63;
  - `driver._load` (csv:51);
  - `recipe.py` 199/269-271;
  - `shareable.py` 172-175/323;
  - the registry filters (csv:base.py:316,330).
- **New test file** `tests/forcing/test_config_version.py`, which includes two source-scan guards. The scan skips `base.py` (test_config_version.py:157-158).

## C. Inventory of record files at the tip (FACTS)

**`_crocodash_state.json` (in the caseroot).** Schema:
- `schema_version` (state schema version 1.1.0, set at case_state.py:27);
- `inputdir`, `cesmroot`, `supergrid_path`, `topo_path`, `vgrid_path`, `grid_name`, `session_id`, `compset_lname`, `machine`;
- `_init_args`: `atm_grid_name`, `rof_grid_name`, `ninst`, `project`, `ntasks_ocn`, `job_queue`, `job_wallclock_time`.

Reads and writes:
- **Write:** case.py:1077-1095 `_write_state` → `case_state.write` (case_state.py:97-101), at the end of `__init__`.
- **Read:** case_state.py:104-115 `read` (`json.load`, then `check_version`) is the only reader. It is called from:
  - base.py:115 `ReadCrocoDashCase.__init__`, which is reached from driver.py:127, case.py:1124, case.py:1144, shareable.py:139 (`CaseBundle` via `super()`), shareable.py:412 and shareable.py:553;
  - cli.py:43 (`process --caseroot`);
  - recipe.py:230 `case_to_yaml`, which is reached from `cli dump` and shareable.py:151.

**`<inputdir>/extract_forcings/config.json`.** Schema:
- top-level `caseroot`;
- one key per active configurator (lowercased name), each holding `{"name", "inputs", "outputs"}` from `serialize()` (base.py:734-740);
- the conditions entry embeds product metadata through `write_metadata()` (mom6.py:562); no separate metadata file is written.

Reads and writes, with the helper each one goes through:

| Location | Read/write | Through |
|---|---|---|
| case.py:654-656 `configure_forcings` | write | `json.dump`, direct |
| case.py:555-562 (previous config) | read | `json.load` direct; `OSError`/`ValueError` give `{}` |
| case.py:742-744 `process_forcings` | read | `json.load` direct, then the path is passed on to `run_workflow` |
| driver.py:125-126 `run_workflow` | read | `json.load` direct |
| base.py:119-123 `ReadCrocoDashCase.__init__` | read | `json.load` direct; reads the case's own file even when `--config` names another one |
| base.py:271-288 `run_configurators(config_path)` | read and write | `json.load`/`json.dump` direct; **this branch is dead**, because the only callers pass `None` (case.py:642, tests/forcing/test_base.py:161) |
| cli.py:44, 50-52, 59-60 `_process` | read | `json.load` direct |
| recipe.py:265-268 `case_to_yaml` | read | `json.load` direct |

**Dict consumers that hard-code the top-level meta keys** (all skip only `"caseroot"`, or `"conditions"`/`"caseroot"`):
- base.py:328 `available_process_flags`;
- base.py:342 `resolve_process_targets`;
- base.py:146 `configurators()`;
- recipe.py:195.

**How many times each command reads the same file:**
- `CaseBundle(...)`: each file twice (base.py:115/119 and recipe.py:230/265).
- `Case.process_forcings`: config.json three times (case.py:744, driver.py:126, base.py:122).
- `crocodash process --caseroot`: state twice and config.json three times.

**`<inputdir>/extract_forcings/process_record.json` (new in #317).** Schema:
- `{flag: {"fingerprint": <process_fingerprint, JSON-normalised>, "files": [inputdir-relative posix paths]}}`;
- no version and no metadata keys;
- `"files"` is written but never read: `is_done` uses only the fingerprint plus a freshly computed `missing_output_files`.

Reads and writes:
- **Read:** driver.py:61-68 `read_record` (`{}` only on `FileNotFoundError`), called from driver.py:168 and case.py:1125.
- **Write:** driver.py:71-77 `_write_record`, called after every finished or incomplete step (driver.py:221).
- **Delete:** case.py:651-652. `override=True` removes the whole `extract_forcings/` directory with `rmtree`.

**Bundle files:**
- `crocodash_case.yaml`: written at shareable.py:321-323.
- `non_standard_case_info.json`: written at shareable.py:325-332, read at shareable.py:478-483 as `BundleDifferences(**json.load)`. It is unversioned.
- **A bundle does not contain** `_crocodash_state.json`, `config.json` or `process_record.json`.

**Other markers CrocoDash owns:** the `! >>> CrocoDash configure_forcings: <owner> [sha:…]` blocks in `user_nl_*` (user_nl_blocks.py:31-33).

**Outside the repo: the MCP server** (`/glade/u/home/manishrv/documents/croc/dev/MCP_CrocoDash` @ d097e1f).
- Reads config.json with a direct `json.load`, so the version check would not run:
  - tools/case.py:63-70, which finds the caseroot from the inputdir via config.json's `"caseroot"` key;
  - tools/case.py:844-852;
  - tools/status.py:40-45;
  - resources.py:34.
- Reads the state through `case_state.read`: status.py:67 and case.py:663.
- Owns its own files:
  - `extract_forcings/process_forcings_status.json` (_bg_worker.py:14-18);
  - `<inputdir>/crocodash_mcp_reuse.json` (case.py:626).

## D. config-schema-version vs. the stack

### Facts: hunk by hunk (main coordinates)

| csv hunk | vs #312 | vs #310 and later |
|---|---|---|
| case.py imports, 2-15 (drop `json`, multi-line `base` import) | clean | **CONFLICT**: #310 rewrote line 12 to `ForcingConfigRegistry, ReadCrocoDashCase` |
| case.py 552-563 (previous config read) | clean | clean (tip:553-562) |
| case.py 652-659 (`write_config`) | clean | clean; #317's insert at tip:666 is outside the context |
| case.py 733-744 (`process_forcings` read) | clean | clean (tip:742-744) |
| case_state.py `check_version` | clean | clean (no stack PR touches it) |
| cli.py 34-63 | clean | clean (#316/#317 only touch tip:72-73 and argparse) |
| base.py import (line 7) | clean, but **duplicates** #312's `from CrocoDash import case_state` (read-crocodash-case:base.py:15) | same |
| base.py constants and helpers after `logger` | clean (#312's insert is at main 14/15) | clean |
| base.py registry filters (287, 301) | clean | clean (tip:328, 342) |
| driver.py imports, 20-28 | **CONFLICT**: #312 removes `Path`/`case_state` and rewrites line 28 | at the tip, `import json` **must stay**: tip:driver.py:66, 76, 82 use it |
| driver.py `_load`, 49-53 | **CONFLICT**: modify/delete, because #312 deletes `_load` | n/a |
| recipe.py, three hunks | clean | clean (stack never touches recipe.py) |
| shareable.py import, 37-42 | clean | clean |
| shareable.py `CaseBundle.__init__` read, 168-178 | **CONFLICT**: #312 deletes the block | n/a |
| shareable.py `bundle` loop, 320-326 | clean (the line still exists at read-crocodash-case:312) | **CONFLICT**: #310 rewrote it to `self.configurators()` |
| docs, `test_case_integration.py` | clean | clean |

That is 3 conflicting hunks against #312, and 5 against the tip.

### Facts: problems git would not flag

1. **`ReadCrocoDashCase.__init__` (tip:base.py:119-123) still uses `json.load`.** It needs `read_config` plus `CONFIG_FILENAME`. The source-scan guard can't catch this, because it skips `base.py` (test_config_version.py:157-158). The dead `run_configurators` branch (base.py:271-288) is hidden from the guard for the same reason.
2. **`configurators()` (tip:base.py:146) filters only `"caseroot"`.** On any versioned config.json it calls `get_configurator("1.0.0")`, and `obj_dict["name"]` (base.py:186) raises `TypeError`. That breaks `bundle()` (shareable.py:305) and `_copy_output_files`, which fork and duplicate both use (shareable.py:366).
3. **The version check must move into `run_workflow` at tip:driver.py:125-126, before `ReadCrocoDashCase`.** csv's `test_run_workflow_rejects_incompatible_version` asserts `case_state.read` is never called (test_config_version.py:121-124), so the check has to happen first.
4. **csv's shareable import would fail its own guard.** After #312, `shareable.py` no longer calls `read_config(`. If the explicit `CONFIG_FILENAME` import stays, `test_config_filename_users_read_with_read_config` (test_config_version.py:181-192) fails.
5. **tests/shareable/test_read_case.py:43 and :49 would fail.** `setdefault` injects `schema_version`, so the dicts no longer compare equal.
6. **#312's patch silently disables the config version check in `test_driver.py`.** Those tests patch `CrocoDash.forcing.base.case_state`, and `read_config` calls `check_version` through that same module name. Harmless, but the check doesn't run there.
7. **Older readers can't read a versioned file.** main, every stack branch without csv, and the MCP server running on an older CrocoDash all hit the `"schema_version"` key:
   - base.py:330/186 raise `TypeError`;
   - recipe.py:197 raises `ValueError("Configurator Not Found")`.
8. **The two fingerprint paths see different dicts.** `_print_forcing_files` fingerprints the in-memory config, which has no `schema_version` (tip:case.py:666/1124). `run_workflow` fingerprints the dict read from disk, which does. They agree today only because every `process_fingerprint` picks out specific keys (base.py:829-830, mom6.py:802, cice.py:467, ww3.py:585).

### Facts: how a version bump interacts with deserialisation

- `deserialize` raises `KeyError` for any declared input or output param missing from the file (tip:base.py:714-727). So adding a param breaks reading older files, and removing one breaks older readers.
- #316 drops `conditions.outputs.preview`. Pre-#316 code reading a post-#316 config.json fails with `KeyError 'preview'`.
- The timing stack:
  - adds `min_chunk_days`, `obc_start_date`, `obc_end_date` and `ic_lookback_days` (bgc-fe-interior-source:mom6.py:501-508);
  - replaces BGCIronForcing's three file params with `MARBL_FE_INTERIOR_SOURCE_FILE` (bgc-fe-interior-source:bgc.py:111-123).

  Old config.json files then fail in the new code: exactly the situation a bump is for. That rename also invalidates #310's bgcironforcing `output_files` (tip:bgc.py:123-133), which is a cross-stack conflict.
- With an exact MAJOR.MINOR match and `CONFIG_UNVERSIONED = "1.0.0"`, the first bump rejects every existing case. The only remedy offered is "recreate the case", because `configure_forcings` can't be rerun on a case on disk without a live `Case` object.

### Natural parent

**#312.**
- csv exists to send every config.json reader through `read_config`, and #312 is the PR that consolidates those readers: 3 of csv's hunks target code #312 deletes.
- After #312, the reader sites are:
  - `ReadCrocoDashCase.__init__`;
  - `run_workflow`;
  - `case.py` (×2);
  - `cli.py`;
  - `recipe.py`.
- `#310`'s `configurators()` is the one later hunk that must adopt `CONFIG_META_KEYS`.
- `#317` must keep `json` imported in `driver.py`.
- Versioning `process_record.json`, if you want it, can only sit at or after #317.

### Opinions/Risks

- **One reader.** Moving `read_config` into `ReadCrocoDashCase` and having `run_workflow`, cli, `case.py` and recipe read through it removes the triple reads. A lazily read `forcing_config` would also avoid a needless check of the case's own file when `--config` points elsewhere.
- **Bump policy.**
  - A strict two-sided match is a heavy hammer for config.json, which can be regenerated. Old-file/new-reader compatibility could be "minor bump plus tolerant deserialize".
  - #316 (and the timing stack) will be the first test of the bump policy.

## E. Should `process_record.json` be versioned?

### Facts

- **It behaves like a cache.** A missing record or a mismatched fingerprint means the step reruns. A structural change, such as an entry that isn't a dict, would raise in `entry.get` (driver.py:91).
- **Fingerprints cover configuration, not code.** Timing-stack commit 37cea8d3 ("Clip negative BGC boundary values to zero") changes only `mom6.py` code. A case whose `bc` step is already done would be skipped after upgrading, and would keep its unclipped OBC files.
- **Fingerprints are case-specific.** The full entries include `case_inputdir` and/or `case_session_id`:
  - runoff.py:19-22;
  - cice.py:231;
  - ww3.py:433;
  - bgc.py:90-91, 184-185;
  - chl.py:19-20.
- **Steps that declare nothing are recorded as done.** That is fine for CICE with restoring off and WW3 with product `none`. A configurator that keeps the default `output_files = {}` would be skipped forever after its first run. All in-tree configurators declare their files; ones written outside the repo are not protected.

### Opinion

Yes, version it, but with cache semantics: a mismatch or a missing version should read as `{}`, not raise. Folding config.json's `schema_version` and a per-configurator `process_version` into `process_fingerprint` (base.py:821-830) would cover both a config schema bump and code-only changes like 37cea8d3, without changing the file layout. Nothing iterates over the record at the tip, so adding a top-level key is low-risk.

## F. Constraints and opportunities for reversibility and fork

### Facts

- **The read half of a Case built from its caseroot already exists.** `ReadCrocoDashCase` doesn't need CIME and provides `state`, `inputdir`, `ocn_dir`, `forcing_config`, `workflow_context` and `configurators`. `configure_forcings`, however, needs more:
  - visualCaseGen's global `cvars["CASEROOT"]` pointing at this case (case.py:620-628);
  - `self.cc._is_non_local()` (case.py:671);
  - `self.fcr` and `ocn_grid`.
- **#312's "single place for `ocn/`" claim doesn't hold at the tip.**
  - `inputdir/"ocn"` is still built by hand at case.py:379, case.py:792 and mom6.py:763.
  - `"extract_forcings"` is built by hand in 10 places (case.py:554, cli.py:44, base.py:119/129, cice.py:510, driver.py:58, mom6.py:764, ww3.py:610/678, recipe.py:265).
- **The expensive parts of shareable are all CIME-bound:**
  - a CIME `Case` object (shareable.py:143, 746-751);
  - the MOM_RPS loader (#321);
  - a full temporary reference case built with `create_newcase` (shareable.py:252-272), whose leftovers #322 cleans up.

  The temporary case exists because only `configure_forcings`'s user_nl writes are marked as CrocoDash's. What `Case.__init__` writes to user_nl and xml is not marked (user_nl_blocks.py:12-14).
- **Fork's prompts are minimal.** `_guide_yaml_review` asks for 6 case fields plus `forcings.date_range` and `forcings.boundaries` (shareable.py:603-615). The pieces needed for prompting on each forcing input already exist:
  - required vs optional comes from the constructor signature (`get_ctor_signature`, base.py:207-216; a param is required when it has no default);
  - descriptions are the `InputParam` comments;
  - `InputFileParam` marks which inputs are paths, i.e. machine-specific.

### Risks

- **#315 can restore files that no longer match the case.** `_copy_output_files` copies whatever the new case declares, even if forcing params were changed during the fork review.
  - Example: boundaries `[south, north, east]` become `[north, east]`. The bundle's `forcing_obc_segment_001.nc` (south) then lands as segment 001, which is now north (segment numbers follow list position, mom6.py:~581). The tides `tz_`/`tu_` files are affected the same way.
  - `validate_case()` passes because the files exist.
  - The fix needs the source case's config.json in the bundle, so each step's fingerprint can be compared before copying.
- **Records don't survive fork or duplicate.** The bundle has no record, and the fingerprints are case-specific anyway. After a fork, `_print_forcing_files` reports every step as "to generate", and `crocodash process` reruns every step even though the files were restored.
- **`non_standard_case_info.json` and `crocodash_case.yaml` cross user boundaries but are unversioned.** Adding a field to `BundleDifferences` breaks `ForkBundle` for bundles written by older versions (shareable.py:483).