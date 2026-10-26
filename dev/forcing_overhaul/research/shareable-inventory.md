# shareable.py, recipe.py, cli.py and case_state.py at the output-files stack tip

All paths below are relative to `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash`. Line numbers are at **origin/skip-finished-forcing-steps (72226b94)** unless a reference says otherwise.

Abbreviations:
- `S` = CrocoDash/shareable.py
- `R` = CrocoDash/recipe.py
- `CLI` = CrocoDash/cli.py
- `CS` = CrocoDash/case_state.py
- `B` = CrocoDash/forcing/base.py
- `C` = CrocoDash/case.py
- `DRV` = CrocoDash/forcing/driver.py
- `VCG/x.py` = CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/x.py (submodule c553683)
- `csv` = the uncommitted config-schema-version worktree, diffed against origin/main

Sections 0 to E are facts I checked by reading the code, except parts marked OPINION. Section G holds the opinions and risks. Nothing was run.

## 0. What differs from main in this area
- **shareable.py:**
  - `CaseBundle` now subclasses `ReadCrocoDashCase` (S:121, 139). It no longer reads state or config.json itself; `ReadCrocoDashCase` does that (B:108-147).
  - `INPUTDIR_FILE_PREFIXES` is gone. `bundle()` now copies every file each configurator declares, via `configurators()` → `get_output_filepaths(ctx)` (S:304-311). That now includes the `conditions` entry; main skipped it and copied IC/OBC files by filename prefix.
  - New `_copy_output_files` (S:359-376), used by duplicate (S:412) and fork (S:553-559).
- **cli.py:** `process` gained `--preview` and `--force` (CLI:72-73, 239-249).
- **recipe.py and case_state.py** are the same as main.
- **New test file:** tests/shareable/test_read_case.py (159 lines).
- **The timing stack** (origin/bgc-fe-interior-source) doesn't touch any of these files. Its only change nearby is a `resolve_time_sampling` call in C's `configure_forcings`.

## A/B. Inventory and classification
Classes:
- **[S]**: subsumed, or drastically simpler, if a Case could be built from an existing caseroot.
- **[T]**: transport (bundle layout, copying files between cases or machines).
- **[F]**: fork/duplicate user experience (prompts, YAML review, copy plans).
- **[D]**: dead or duplicated.

### shareable.py
| Item (lines) | What it does | Disk / CIME | Tests | Class |
|---|---|---|---|---|
| `copy_xml_files_from_case` (53-58) | Copies named files from one caseroot to another | caseroot `*.xml` | test_apply.py:5-25 | T |
| `copy_user_nl_params_from_case` (61-73) | Splits `k=v` lines of the old `user_nl_<comp>` and appends the selected ones via VCG `append_user_nl` | Writes into `cvars["CASEROOT"]`'s user_nl (VCG/case_tools.py:76), not into a path it is given | test_apply.py:28-61 (mocked) | T |
| `copy_source_mods_from_case` (76-84) | Copies the listed SourceMods files; does not create missing subdirectories | caseroot/SourceMods | test_apply.py:64-90 | T |
| `apply_xmlchanges_to_case` (87-98) | Replays the `./xmlchange K=V` lines in replay.sh for the selected K | `./xmlchange … --non-local`, hard-coded (S:98), run in `cvars["CASEROOT"]` (VCG/case_tools.py:121) | test_apply.py:93-116 (mocked) | T; also D (a second replay.sh parser with different rules from S:166-180) |
| `BundleDifferences` (106-113) | Four lists of names | → non_standard_case_info.json | indirect only | S |
| `CaseBundle.__init__` (138-147) | `ReadCrocoDashCase` init, then YAML, a CIME Case object, and four readers | — | test_bundle.py:50-53 (real CESM) | S |
| `_load_state_from_crocodash` (149-164) | Calls `case_to_yaml`, which reads state and config.json a second time and opens the topo file; sets cesmroot/machine/project; builds `init_args` (ESMF mesh found by glob; the `inputdir_ocn` key is only read by a test) | read | test_bundle.py:96-118 | S |
| `_read_xmlchanges` (166-180) | `{var: last value}` from replay.sh lines containing "xmlchange" | read | only through the diff tests | S/D |
| `_read_user_nls` (182-189) | Uses CIME `COMP_CLASSES`/`COMP_x` to find non-stub components, then parses each `user_nl_<comp>` | CIME object, used for nothing else | test_bundle.py:278-286 (mocked CIME) | S |
| `_read_xmlfiles` (191-192), `_read_sourcemods` (194-199) | Inventories: top-level `*.xml`; recursive SourceMods listing | read | test_bundle.py:289-314 | T |
| `get_user_nl_value` (201-204) | Reads INPUTDIR from the parsed user_nl_mom; only caller is S:288 | — | test_bundle.py:284 | D (state already gives `inputdir`, B:116-118) |
| `_read_user_nl_lines_as_obj` (206-221) | importlib-loads `<cesmroot>/components/mom/cime_config/MOM_RPS/FType_MOM_params.py` and calls `from_MOM_input` | runs CESM Python | test_bundle.py:153-158 | S (#321 patches this import) |
| `diff` (223-240) | Set difference, **by name only** | — | test_bundle.py:56-93 (two real cases) | S |
| `identify_non_standard_case_info` (242-272) | Builds a temporary reference case and diffs against it | Full `create_case_from_yaml(override=True, configure_only=True)` with stdout/stderr sent to devnull | test_bundle.py:121-150; integration tests | S |
| `bundle` (274-351) | Writes the bundle folder (layout in C) | copies files | test_bundle.py:171-275; integration | T (its YAML/JSON contents are S) |
| `CaseBundle.duplicate_case` (353-356) | Wrapper with no callers | — | none | D |
| `_copy_output_files` (359-376) | Copies every file the **new** case declares from the source inputdir or bundle, at the same relative path; skips files already present | writes new inputdir | test_read_case.py:90-110 | T |
| `duplicate_case` (379-440) | See C | two CIME cases | test_integration.py:23-43 (slow); test_read_case.py:141-159 (mocked) | S+T |
| `ForkBundle.__init__` / `_validate_bundle` (470-506) | Loads YAML and JSON; requires the listed xml_files/*, SourceMods/* and ocn/ to exist | read | integration only | T |
| `fork` (508-566) | Orchestration | one CIME case | test_integration.py:46-119; test_read_case.py:113-138 | F+T |
| `_configure_yaml_for_forked_case_args` (568-594) | Sets `case.{cesmroot,machine,project,caseroot,inputdir}`; points grid/topo/vgrid at bundle/ocn | — | test_fork.py:54-98 | T |
| `_guide_yaml_review` (596-646) | Prompts for 6 case fields plus `date_range` and `boundaries`; offers `$EDITOR`; asks for confirmation | temporary YAML | no direct test | F |
| `_resolve_copy_plan` (648-682) | One yes/no per non-empty category, **default False** | — | test_fork.py:15-51 | F |
| `apply_copy_plan` (684-706) | Calls the copy helpers with the bundle standing in for the old caseroot | xmlchange | integration | T |
| `ask_string` / `ask_yes_no` (714-738) | `input()`; end of input returns the default | — | test_fork.py:101-135 | F |
| `_get_case_obj` / `_run_xmlquery` (746-762) | `./xmlquery CIMEROOT -N`, then `sys.path.append(cimeroot)` (never removed), then `CIME.case.Case(read_only, non_local=True)` | subprocess | test_bundle.py:161-163 | S |

### recipe.py (same as main)
| Item (lines) | What it does | Tests (test_recipe_functions.py) | Class |
|---|---|---|---|
| `load_config` (31-36) | Reads YAML and validates it | 209-227 | keep |
| `validate_config_structure` (39-77) | Structural checks. **shareable never calls it.** | 105-206 | keep |
| `build_grid` / `build_topo` / `build_vgrid` (80-127) | Config dict → Grid/Topo/VGrid objects, including the from-file variants | 230-347 | keep; reusable for a read-back Case |
| `create_case_from_yaml` (130-166) | Builds the objects, calls `Case(..., override, **config["case"])`, then `configure_forcings`, then `process_forcings` unless `configure_only`. The check for a forcings section (157-161) runs **after** `Case()` (149-155). | No direct unit test; tests/test_cli.py mocks it | keep |
| `generate_configure_forcing_args` (169-217) | config.json → `configure_forcings` kwargs. Conditions maps to only 4 keys (186-193) and is then skipped in the loop (195), so `function_args` / `function_overrides` are **dropped**. `case_*` args are skipped (207). | 468-538 | S |
| `case_to_yaml` (220-271) | State + config.json + the topo file's `min_depth` attribute → YAML dict | 389-465 | S |

### cli.py and case_state.py
- `_create` (CLI:17-23): keep.
- `_dump` (26-31): S. It is a thin wrapper over `case_to_yaml` and has no CLI test.
- `_process` (34-74): keep, but it works out the config path itself (41-49) instead of using `ReadCrocoDashCase`, so D.
- `_bundle` (77-87): T. It requires `--cesmroot`/`--machine`/`--project` (CLI:266-274) even though the state file has them (S:152-154). They are used only for the reference case.
- `_duplicate_case` (90-99): F/T. The `--bundle-dir` help says "default: inside new caseroot" (CLI:296-301), but the default is None, which writes no bundle (S:437-438).
- `_fork` (152-165): F. Prints no summary when it succeeds.
- `_template`: unrelated (it delegates to crocogallery).
- case_state.py: `SCHEMA_VERSION` 1.1.0 (CS:27), `INIT_ARGS_EXCLUDE` (32-45), `DERIVED_KEYS` (52-65), `check_version`/`write`/`read` (68-115). Tested in test_recipe_functions.py:352-381. Keep: it is exactly the contract a read-back Case would consume.

### How the [S] items would collapse
The [S] code does two jobs:
1. **Rebuild the inputs to `Case()` and `configure_forcings` from disk** (R:169-271; S:149-164). If a Case could be built from a caseroot (state → R:80-127 builders, config.json → `ForcingConfigRegistry.get_configurator`, CIME xml through a case object), this becomes plain attribute access.
2. **Work out "what CrocoDash would have produced"** by building a throwaway CIME case and diffing names against it (S:182-272, 746-762). This goes away if CrocoDash records its own writes when it creates and configures a case (see D).

What a read-back Case would have to handle, all in C:
- `configure_forcings` refuses to run unless `cvars["CASEROOT"]` is this case (C:620-628). It also reads the session ID from `cvars["MB_ATTEMPT_ID"]` (C:630).
- Every xmlchange calls `cc._is_non_local()` (C:671-686).
- `process_forcings` needs `_configure_forcings_called` (C:737-740) and `extract_forcings_path`, which only `configure_forcings` sets (C:554).
- `validate_case` and `_print_forcing_files` use `self.fcr` (C:1127, 1145).
- The ESMF mesh path is not in the state file (S:157 globs for it), but runoff needs `case_esmf_mesh_path` (forcing/runoff.py:33).
- `ForcingConfigRegistry` passes every public Case attribute to configurators as `case_<attr>` (B:165-171).

## C. Flows
### bundle (CLI:77-87)
1. `CaseBundle(caseroot)`:
   - `case_state.read` and config.json (B:113-124)
   - `case_to_yaml`: state again, topo opened, config.json again (R:229-269)
   - `xmlquery` and a CIME Case object (S:746-762)
   - MOM_RPS parse of each non-stub user_nl (S:182-221)
   - replay.sh, `*.xml`, SourceMods (S:166-199)
2. `identify_non_standard_case_info(cesmroot, machine, project)` with the CLI values:
   - Creates a `TemporaryDirectory` and deep-copies the YAML with caseroot `temp_case-<uuid4>` and a temporary inputdir (S:252-263).
   - Runs `create_case_from_yaml` (S:268), which calls `Case()`:
     - `initialize_visualCaseGen` (C:132)
     - writes grid/topo/vgrid/SCRIP/ESMF files, plus CICE and WW3 files when needed (C:370-415)
     - `CaseCreator.create_case`: `create_newcase` (VCG/case_creator.py:151), xmlchanges, `./case.setup` (:166), namelist changes (:193)
     - writes the state file (C:1077-1095)
     - then `configure_forcings`: user_nl blocks, config.json, and CALENDAR/RUN_STARTDATE/STOP_* xmlchanges (C:668-687).
   - Runs `CaseBundle(tmp)`, which repeats step 1 on the temporary case, then `diff`.
   - The temporary directory is removed, but `$CIME_OUTPUT_ROOT/temp_case-<hex>/{bld,run}` is left behind; only #322 fixes that. For WW3 compsets, visualCaseGen also creates `RUNDIR/ww3_moddef_create` (VCG/case_creator.py:188).
3. `bundle(output_dir)` (S:274-351) writes `<case>_case_bundle/` containing:
   - every `user_nl_*` file and `replay.sh`
   - every declared forcing file that exists, at its inputdir-relative path (ocn/, ice/, wav/, mapping/)
   - 4 grid files in ocn/, taken from the INPUTDIR in user_nl_mom (S:288, 313-319)
   - `crocodash_case.yaml`, with the original absolute paths
   - `non_standard_case_info.json`
   - `xml_files/` and `SourceMods/`, listed items only

   It does **not** include `_crocodash_state.json`, config.json, process_record.json, the SCRIP/CICE/WW3 grid inputs, or any version marker.

### fork (CLI:152-165)
1. `ForkBundle(bundle)` loads the YAML and JSON and runs `_validate_bundle` (S:470-506).
2. `_configure_yaml_for_forked_case_args` (S:568-594).
3. `_guide_yaml_review` (S:596-646):
   - prompts for caseroot, inputdir, cesmroot, machine, project and compset, although the CLI already required the first five as flags (CLI:311-323);
   - prompts for `date_range` and `boundaries`;
   - offers `$EDITOR` only if it is set;
   - prints the YAML and asks "Proceed?".

   Nothing validates the edited YAML.
4. `_resolve_copy_plan` (S:648-682): four yes/no prompts that default to False, unless `--plan` was given.
5. **The CIME case is created:** `create_case_from_yaml(config, override=True, configure_only=True)` (S:550), the same chain as bundle step 2.
6. Every file in bundle/ocn that the new ocn/ lacks is copied (S:553-557), then `_copy_output_files` runs (S:559).
7. `apply_copy_plan` (S:684-706): xml files go into the new caseroot; user_nl params and xmlchanges go through visualCaseGen's global state.
8. `validate_case()` prints which forcings still need processing (S:564). `fork` returns the Case, and the CLI discards it.

### duplicate (CLI:90-99 → S:379-440)
1. `CaseBundle(source)`.
2. `identify_non_standard_case_info` with the source's own cesmroot/machine/project (S:389-391). This is **CIME case #1**, the temporary one.
3. A shallow copy of the YAML gets the new caseroot and inputdir; the grid paths still point into the source inputdir (S:393-396).
4. `create_case_from_yaml` (S:398). This is **CIME case #2**, the real duplicate.
5. Every file in the source's ocn/, ice/ and wav/ that the new directories lack is copied (S:400-410).
6. `_copy_output_files(source inputdir, new case)` (S:412).
7. All four categories of non-standard state are applied from the source caseroot, with no prompt (S:414-435).
8. A bundle is written only if `bundle_dir` is given (S:437-438). There are no prompts and no `validate_case` call.

## D. Non-standard case info
**What is captured and how.** Four lists of names (S:110-113), each compared against the temporary reference case (S:242-272):
- **xml files:** top-level `*.xml` names in the caseroot that the reference lacks (S:191-192, 234).
- **user_nl params:** for each non-stub component (S:184-189), names per module in a MOM_input-style parse of `user_nl_<comp>` that the reference lacks (S:226-232).
- **SourceMods:** relative paths of all files under SourceMods that the reference lacks (S:194-199). Neither CrocoDash nor visualCaseGen writes to SourceMods (grep finds nothing outside S).
- **xmlchanges:** variable names in replay.sh xmlchange lines that the reference's replay.sh lacks (S:166-180, 236-238).

Fork applies them from the bundle copies (S:684-706); duplicate applies them from the source caseroot (S:414-435).

**Blind spots, from the code:**
- **The diff compares names only.** A changed value of anything CrocoDash or visualCaseGen also sets is lost: STOP_N, NTASKS_OCN, or a user_nl override of a forcing parameter.
- **User overrides of forcing parameters are dropped even when they matter most.** `user_nl_blocks` deliberately leaves a user-overridden variable out of CrocoDash's block (forcing/user_nl_blocks.py:15-18). The reference case has that variable inside the block, and the block markers are `!` comments the parser skips (:20-21). So the name appears in both cases and the user's override is dropped.
- **Only `user_nl_<comp>` files are scanned.** `user_nl_datm_streams` (which CrocoDash writes through blocks) and multi-instance `user_nl_<comp>_NNNN` files are never read.
- **MOM parameter blocks break it.** `diff` indexes `other_case.user_nl_objs[key][subkey]` (S:231), which raises KeyError if the case has a `KPP%`-style block the reference lacks. The copy step matches bare names only (S:69-71).
- **Two replay.sh parsers with different rules** (S:166-180 vs S:87-98). `--id/--val` and comma-separated multi-settings are not read as name=value.
- **On your CESM_crocodash install** (/glade/u/home/manishrv/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS/param_file_reader.py), `from_MOM_input` parses with `user_nl=False`. So a `diag_table%…` line goes to the "Cannot parse" `SystemExit` (:59, :139), and a duplicated parameter raises `SystemExit` (:131). buildnml itself uses `read_user_nl_mom`.

**OPINION: a cheaper way if a Case could be read back.**
- **xmlchanges:** store the replay.sh line count (or a hash) in state after `Case.__init__` and after each `configure_forcings`. User changes are then the lines after that marker, values included, with no reference case and no CIME.
- **user_nl:** CrocoDash's own lines are already identifiable: blocks tagged with a sha (forcing/user_nl_blocks.py:32-35), `_keys_outside_blocks` (:83), and in-block edit detection in `report_edits` (:200). What case creation writes outside the blocks (visualCaseGen namelist changes, C:435-466) could be snapshotted at the end of `__init__`. User changes are then a diff against that snapshot. It would see values, cover every file including streams, and need no MOM_RPS import, so #321 becomes unnecessary.
- **xml files and SourceMods:** snapshot the names when the case is created, or treat all of SourceMods as user content.

This deletes identify/diff/`_read_user_nls`/`_get_case_obj` and the code #321/#322 add, and every bundle or duplicate stops building a reference case.

## E. Line counts
"Code" means non-blank, non-comment, non-docstring lines.

**shareable.py: 762 lines total, 501 code.**

| Concern | Code lines | Approx. raw lines |
|---|---|---|
| [S] reading and diff machinery (`CaseBundle` init/load/readers/`get_user_nl_value`/`_read_user_nl_lines_as_obj`/`diff`/identify, `BundleDifferences`, CIME utilities) | ~121 | ~245 |
| `duplicate_case` (mixed S+T) | 45 | 62 |
| [T] (copy helpers 40, inventories 8, `bundle` 61, `_copy_output_files` 15, `ForkBundle` init/validate 29, `_configure_yaml…` 26, `apply_copy_plan` 23) | ~202 | ~300 |
| [F] (`fork` 27, `_guide_yaml_review` 45, `_resolve_copy_plan` 31, `ask_*` 18) | ~121 | ~170 |
| [D] (wrapper 4, `get_user_nl_value` 4, second replay parser 12, `init_args["inputdir_ocn"]`) | ~20 | — |

Open PRs add more [S] code: #321 is +21/−11 and #322 is +37/−7 in shareable.py.

**recipe.py: 271 lines, 181 code.** The [S] parts are `case_to_yaml` (37) and `generate_configure_forcing_args` (41). They would move into Case rather than disappear.

**cli.py:** the bundle, duplicate and fork handlers are 31 code lines, and their argument parsers are 76 non-blank lines (CLI:252-329).

**Tests:** tests/shareable totals 949 lines:
- test_bundle.py: 314, of which about 165 test [S] functions and need a real CESM
- test_integration.py: 119, slow, about two CIME cases per test
- test_read_case.py: 159
- test_fork.py: 135
- test_apply.py: 116
- test_cli.py: 106

In tests/test_recipe_functions.py, about 155 lines (384-538) cover `case_to_yaml` and `generate_configure_forcing_args`.

**OPINION:** removing the [S] and [D] code leaves shareable.py at roughly 330-380 code lines. A declarative per-parameter fork prompt would replace `_guide_yaml_review`'s hard-coded field list rather than shrink [F].

## F. Facts that matter for folding config-schema-version into the stack
- **Textual conflicts in shareable.py.** `csv` edits `CaseBundle`'s config.json read (main S:168-177), which #312 removed. It also edits the `bundle()` loop that #310 rewrote. The `csv` hunk keeps the `config == "conditions"` skip; if the conflict is resolved that way at the tip, bundles stop including IC/OBC files, because the tip now picks them up through `configurators()` (S:305).
- **Driver conflict.** `csv`'s driver.py hunk targets `_load`, which #312 removed.
- **A crash at the tip without a follow-up change.** At the tip, `ReadCrocoDashCase` reads config.json (B:119-124), but DRV:125-126 and CLI:59-60 still call `json.load` first. With `csv`'s top-level `schema_version` key, `configurators()` (B:143-147, which skips only `"caseroot"`) would call `get_configurator("1.0.0")` and fail. That breaks bundle, fork, duplicate, `_print_forcing_files` and `validate_case`. The tip copies of B:328 and B:342 need the same `CONFIG_META_KEYS` change `csv` makes on main.
- **Formats with no version:** the bundle (S:321-332) and process_record.json (DRV:57-77).
- **External consumer.** The MCP server (/glade/u/home/manishrv/documents/croc/dev/MCP_CrocoDash/crocodash_mcp/tools/shareable.py:150-153) replaces the private `_guide_yaml_review` and defaults every copy flag to True, the opposite of the CLI's defaults.

## G. Opinions and risks
1. **Data loss through `override=True`.** shareable always passes `override=True` (S:268, 398, 550). With that, `Case` deletes the caseroot, the inputdir and `$CIME_OUTPUT_ROOT/<basename>` (C:199-206).
   - Duplicating `/a/mycase` to `/b/mycase` deletes the source's bld/run directories, because both cases share the basename.
   - Passing `--inputdir` equal to the source's inputdir deletes the source's files before anything is copied.
   - There is no guard against either.
2. **Session IDs in file names.** A new Case gets a new session ID (C:956). The BGC iron and river-nutrient file names include it (forcing/bgc.py:115-117, 230). `_copy_output_files` looks for the new names in the source, so it silently misses these files. Fork and duplicate also end up with two sets of grid files: the old-suffix copies and the newly generated ones.
3. **Copied forcing files can be stale.** Fork copies forcing files even when the reviewer changed `date_range` or the compset, and `validate_case` still reports them as fine. At the same time, process_record.json is not carried over, so the #317 skip logic reruns every step. A copied record wouldn't match anyway: the fingerprints include `case_*` paths and session IDs.
4. **The YAML round trip drops `function_overrides`** (R:186-195). That includes `member` and the timing stack's `freq` (docs/source/for_developers/adding_data_access.md:172 on origin/bgc-fe-interior-source). dump, bundle, fork and duplicate all revert to the defaults without saying so, yet cli.md:102 calls dump "the exact inverse of create".
5. **Global-state coupling.** Edits made after creation go to whichever case was created last (VCG/case_tools.py:76, 121). Duplicate only works because the real case is created after the temporary one.
6. **The metadata for per-parameter fork prompts mostly exists already:**
   - `InputValueParam` vs `InputFileParam`, each with a comment (B:393-421)
   - required vs optional from constructor defaults (B:206-222)
   - which configurators a compset activates (B:188-204)
   - `Case` already prints each required configurator's arguments (C:236-248)

   Gaps:
   - `get_user_args` filters only on the `case_` prefix (B:221), so the injected `compset` (B:172) shows up as a user argument for conditions.
   - The kwargs form one flat namespace; for `boundaries`, the conditions value wins (test_recipe_functions.py:522-530).
   - Conditions' input params don't match its constructor arguments: `date_range` vs `start_date`/`end_date` (forcing/mom6.py:421-436, 492-514).
7. **Documentation has drifted from the code:**
   - docs/source/for_users/shareable.md:29-31 says non-standard state is carried over, but the prompts default to No.
   - shareable.md:72 says ocn/ holds "all ocean input files".
   - shareable.md:212 imports `copy_configurations_to_case`, which doesn't exist.
   - docs/source/for_users/compsets_and_inputs.md:23 says bundle/fork/duplicate avoid re-parsing CIME; they don't.
   - The comment at tests/shareable/test_fork.py:127-128 contradicts S:658-681.
8. **Half-made cases.** `create_case_from_yaml` creates the CIME case before it checks for a forcings section (R:149-161). Forking a bundle that has no forcings leaves a half-made case behind.