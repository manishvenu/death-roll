# Forcing overhaul plan, built around one declared parameter model

**How to read this:**
- `CD/` means `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/`.
- `MCP/` means `/glade/u/home/manishrv/documents/croc/dev/MCP_CrocoDash/crocodash_mcp/`.
- Line numbers are for origin/main. `tip:` means origin/skip-finished-forcing-steps.
- Report citations look like [output §x], [timing], [inventory], [caseroot], [params] and [vcg].

**The core idea.**
- Declare every forcing input once, on its configurator.
- config.json stores each input as JSON, exactly as the user gave it. Resolved values go in outputs, and process steps read only outputs.
- That one rule drives validation, the JSON schema for each compset, MCP discovery, the fork prompts and the annotated YAML. It also makes config.json → YAML → config.json lossless.

**What follows from it:**
- A Case read back from its caseroot is just: the state file, config.json, and write helpers that are told the caseroot.
- Fork is: a lossless YAML, a new Case, reuse of forcing files only when their fingerprints match, and a replay of the user's own changes.
- After that, shareable.py has nothing left to do.

## 1. Target end state

### 1.1 The parameter contract (`CD/forcing/base.py`)

**One input class.** `Input(name, comment, *, type=None, choices=None, kind=None)` replaces `InputValueParam` and `InputFileParam`. Those two behave identically, and nothing reads their File/Value marker [params §1]. The `kind` values are:
- `"user"` (the default): the user is asked for it and it round-trips.
- `"case"` (the default for `case_*` names): comes from `Case.forcing_inputs()`. Never asked for, never written to YAML.
- `"derived"`: computed in the constructor (start/end dates, calendar).

`choices` is either a list or `callable(values)`. Examples: forcing products of the right type, or the access methods of the chosen product.

**Required and default come from the constructor signature.** It already declares them.
- A strict test requires constructor arguments to equal the declared inputs. Today the check only requires a subset (tip:base.py:620-636).
- That removes the constructor-only adapters:
  - `date_range` becomes a stored input;
  - `case_cime` is deleted;
  - `case_forcing_product` is replaced by the shared `product_name`.

**Values are JSON by requirement.**
- `configure_forcings` converts Timestamp, Path and #269's `Segment` objects once, as they come in.
- Building a configurator and deserializing one are then the same operation [params §6].

**Inputs record intent; outputs record what was resolved.**
- An input of None means "work it out". Process steps read outputs.
- This fixes three current losses:
  - runoff writing suggested values back into its inputs (runoff.py:104-110);
  - config.json keeping only the merged function arguments (case.py:590-608);
  - hand-edited chunk sizes disappearing [params §4, §7.5].

**User input names are unique across configurators.**
- The exceptions are the declared shared inputs: `date_range`, `boundaries` and `product_name`.
- WW3's step-day inputs are renamed `ww3_get_step_days` and `ww3_regrid_step_days`.

**Who reads the declarations:**
- `ForcingConfigRegistry.describe(compset=None)`: the MCP's `list_forcing_configs`, the printout when a Case is created, the fork prompts and the annotated YAML.
- `json_schema(compset)`: validation of YAML and of MCP input. An optional configurator's required inputs become `dependentRequired`; that expresses the tides "all three or none" rule.
- `user_args(config)`: dump, fork and reconfigure.
- `configure_forcings` raises `TypeError` on an unknown keyword argument. Today unknown arguments are dropped silently (tip:base.py:231-234).

### 1.2 Where things live

| Module | After the series |
|---|---|
| `CD/case.py` `Case` | `__init__(…, session_id=None)` creates the case (vCG, create_newcase, case.setup) and then sets `self.files`. Also: `from_caseroot`, `from_bundle`, `configure_forcings` (no cvars), `reconfigure`, `process_forcings`, `xmlchange`, `append_user_nl`, `forcing_inputs`, `case_args`, `bundle`, `fork_config`, `fork`, `validate_case` |
| `CD/case_files.py` `CaseFiles` (successor of `ReadCrocoDashCase`, moved out of base.py) | **Reads:** the state file; config.json and the process record, lazily; `configurators()`; `workflow_context()`; `ocn_dir`, taken from the state's supergrid path so old `ocnice/` cases work [caseroot §6.5].<br>**CIME access:** `xmlquery`, `get_value` and `xmlchange` through `<cesmroot>/cime/CIME/Tools/* --caseroot <caseroot> --non-local`, called with an argument list. replay.sh still records each change.<br>**Other writes:** `write_user_nl_block`, `append_user_nl`.<br>**Sharing:** `user_changes`, `apply_user_changes`, `copy_reusable_outputs`, `bundle`.<br>This and case.py are the only modules that import vCG. |
| `CD/forcing/base.py` | `Input`.<br>`BaseConfigurator`: deserialize that tolerates missing keys, `require_outputs`, `process_version`, `output_files`, a fingerprint that is portable between cases.<br>`ForcingConfigRegistry`: `describe`, `json_schema`, `user_args`.<br>config.json I/O: `CONFIG_*`, `read_config`, `write_config`, `CONFIG_MIGRATIONS`.<br>`WorkflowContext.from_state`. |
| `CD/forcing/driver.py` | `run_workflow(config_path, preview, force, **flags)`. The signature is unchanged, because `MCP/tools/_bg_worker.py:38` calls it. It reads config.json with `read_config`, then the state with `case_state.read`, then builds the context with `WorkflowContext.from_state`.<br>It never imports `case_files`. `forcing/__init__` auto-imports driver.py, which is why #312 had to put the reader in base.py; that workaround is no longer needed. |
| `CD/forcing/atm.py` | A thin `StreamYears` shim. Same inputs, same `streamyears` config.json entry. It calls `case.files`, which calls the vCG `stream_years` module |
| `CD/recipe.py` | YAML only: `load_config`, `validate_config` (driven by the schema), the grid/topo/vgrid builders, `create_case_from_yaml`, and `case_to_yaml(caseroot, annotated=False)`, which becomes lossless |
| `CD/cli.py` | `create`; `dump [--annotated]`; `reconfigure`; `process`; `bundle` (no `--cesmroot/--machine/--project`); `fork --from B\|C [--write-yaml F \| --yaml F \| --no-input]`, keeping `--bundle` as an alias; `duplicate`, which is `fork --no-input`; `template`. Also the prompt helpers |
| vCG `custom_widget_types/user_nl_blocks.py`, `stream_years.py` | The moved modules. They take the caseroot and ninst as arguments, use no cvars, and take the marker tag as a parameter. CrocoDash passes the existing `CrocoDash configure_forcings` tag |
| Deleted | `shareable.py`, `forcing/user_nl_blocks.py`, `forcing/cdeps_streams.py`, `ReadCrocoDashCase`, the special cases in `generate_configure_forcing_args`, the cvars guard (case.py:618-628), `InputValueParam`/`InputFileParam`, and the dead branch of `run_configurators(config_path)` |

**Import graph:**
- `case_files` imports `forcing.base`, `forcing.driver` and `case_state`.
- Nothing under `forcing/` imports `case_files` or vCG. `crocodash process` and the MCP background workers therefore never build vCG's GUI.
- `case` imports `case_files`; `recipe` imports `case`.
- `WorkflowContext` currently imports Grid and Topo inside a function. Those imports move to the top of the file.

### 1.3 Persisted files

**`<caseroot>/_crocodash_state.json`**
- Version: 1.1.0 now. R3 bumps it to **1.2.0**, adding `esmf_mesh_path`, plus `cyclic_x` once #311 lands.
- Rule shared by every reader:
  - same MAJOR, MINOR ≤ current: migrated forward in memory. For 1.1 → 1.2, the mesh path is derived from the `ESMF_mesh_{grid}_{session}.nc` naming.
  - newer MINOR, or a different MAJOR: raise.
  - unversioned: warn, as today.
- This replaces the exact-match check at case_state.py:68-93.

**`<caseroot>/_crocodash_baseline.json`** (new in S1)
- Version 1.0.0. Optional.
- Holds the replay.sh line count, the user_nl lines outside CrocoDash's blocks, and the names of the top-level xml files, all as of the end of case creation.
- If it is missing or has an unknown version, fork falls back to comparing names only.

**`<inputdir>/extract_forcings/config.json`**
- An unversioned file is read as 1.0.0 (A2). Every PR that changes a declared param name bumps the MINOR version.
- Same reader rule as the state file.
- `CONFIG_MIGRATIONS` handles renamed or removed *user* inputs.
- Deserialize becomes tolerant:
  - a missing input gets its constructor default;
  - a missing output becomes None;
  - unknown keys are ignored.
- Derived outputs are never migrated. Instead, `require_outputs()` raises `StaleConfigError`, telling the user to run `crocodash reconfigure`.
- CI enforces this in two ways:
  - a fingerprint of all param names must match `KNOWN_SCHEMAS[CONFIG_SCHEMA_VERSION]`;
  - every released version has a flat fixture `tests/forcing/config_<ver>.json`, and loading each fixture must succeed.

**`<inputdir>/extract_forcings/process_record.json`**
- Version 1.0.0, set by the #317 amendment. Layout: `{"schema_version", "steps": {flag: {fingerprint, files}}}`.
- It is a cache: missing, mismatched or malformed reads as `{}`, so the steps rerun.
- The fingerprint includes `process_version` and uses `$INPUTDIR` and `$CESMROOT` in place of real paths, so it can be compared between cases.

**`bundle.json` with `case/` and `inputdir/` folders**
- Version 2.0.0 (S3). The reader accepts MAJOR 2 with MINOR ≤ current.
- A v1 bundle (a `crocodash_case.yaml` and no manifest) goes through a legacy reader of about 40 lines.
- The state, baseline and config.json inside a bundle are checked by their own readers.

**The `! >>> CrocoDash configure_forcings:` markers in user_nl files**
- The marker text is frozen. vCG's parser takes the tag as a parameter, so existing cases keep working [vcg risk 3].

### 1.4 Read-back Case API

```python
case = Case.from_caseroot(caseroot, *, cesmroot=None)  # never creates, deletes, or runs case.setup
src  = Case.from_bundle(bundle_dir)                     # read-only; writes raise
case.configure_forcings(...); case.reconfigure(**changes); case.process_forcings(force=False, **flags)
case.xmlchange("STOP_N", 30); case.append_user_nl("mom", [("DT", 900)]); case.bundle(out_dir)
new = src.fork(src.fork_config(caseroot, inputdir, cesmroot=..., machine=..., project=...))
```

**Loaded eagerly.** `CaseFiles` reads the state (migrated if needed) and sets plain attributes:
- caseroot, inputdir, cesmroot, compset_lname, machine, project, ninst;
- session_id and grid_name;
- the supergrid, topo, vgrid and ESMF mesh paths;
- the remaining init args, with `override=False`.

They must be plain attributes because that is what the `case_*` inputs need [caseroot §6.7].

**Loaded lazily (cached):**
- config.json, then `fcr` (deserialized from it), and `_configure_forcings_called`, which is true when config.json exists.
- `ocn_grid`, `ocn_topo` and `ocn_vgrid`, rebuilt from the state paths [caseroot §4]. Only fork, #269's boundary auto-detection and #311's `cyclic_x` need them.
- CIME values, through `files.xmlquery`. `expt` gets RUNDIR this way.
- **Never loaded:** vCG's `initialize`, cvars, and a CIME `Case` object.

**How the `case_*` inputs are provided.**
- `Case.forcing_inputs()` returns an explicit dict.
- It replaces the scan over `case.__dict__` at tip:base.py:164-171.
- A test checks that every `kind="case"` input of every registered configurator is in that dict, so #269 and #311 can't add one silently.

**The `cesmroot` override:**
- It changes the CIME tools path, the CDEPS reads and `case_cesmroot`.
- It is never written back to the state file.
- If env_case.xml's SRCROOT no longer exists, the case can be read and forked but not edited [caseroot §6.4].

**How writes find the caseroot.**
- Always through `self.files`; configurators use `self.registry.case.files`.
- Case creation still uses vCG's global state internally, but nothing after `__init__` touches cvars.
- This ends "configure_forcings writes into the case created last" [caseroot §6.1].

### 1.5 Fork pipeline

`fork(config, carry=True)` runs in this order:

1. **Validate** the config against `json_schema`.
2. **Create the new case:** `Case(ocn_grid=self.ocn_grid, …, session_id=self.session_id, **config["case"])`.
   - Keeping the session id means the grid and forcing file names don't change. That fixes the files fork currently misses because their names contain the session id [inventory G2].
   - fork never imports `recipe`, so there is no import cycle.
3. **Apply the user's changes before configuring.**
   - Order matters: `user_nl_blocks.write` must see a key the user set outside the blocks, so it leaves that key out of the new block.
   - With a baseline:
     - user_nl lines are compared by value;
     - xmlchanges are the replay.sh lines after the recorded line count.
   - Without a baseline, only names are compared, against the case just created; it serves as the reference case at no extra cost [inventory D].
   - xml variables CrocoDash owns are skipped.
   - If the machine changes, PE, queue and project variables are skipped.
4. **Configure:** `configure_forcings(**config["forcings"])`.
5. **Reuse forcing files:** copy a step's files and its record entry only when its portable fingerprint equals the source's and the source step finished. That stops stale files being copied after a date or boundary edit [output §F; timing R4].
6. **Refuse unsafe targets:**
   - a target directory that already exists;
   - a target that is, or is inside, the source's directories;
   - a clash on `$CIME_OUTPUT_ROOT/<basename>`.

   It never passes `override=True` [inventory G1].

## 2. What happens to each existing branch or PR

**Output-file stack**

| Item | Verdict | Details |
|---|---|---|
| #312 | Keep | Base of the stack. R1 later moves the reader class to `CaseFiles` |
| config-schema-version (uncommitted) | Re-cut as A2, on top of #312 | Drop the hunks for `_load` and `CaseBundle` (#312 deleted those) and move the checks to `run_workflow` and `ReadCrocoDashCase` [output §D]. The version check runs before `case_state.read`. New policy: older MINOR is migrated, newer is rejected. Add tolerant deserialize, `require_outputs` and the fingerprint test. Keep the guard against a bare `"config.json"` string; drop the guard "uses CONFIG_FILENAME ⇒ calls read_config", which #312 breaks [§D.4]. Fix test_read_case.py:43,49. Keep `import json` in driver.py for #317 |
| #310 | Keep, rebase onto A2 | `configurators()` must skip `CONFIG_META_KEYS` [§D.2]. The PR is 404 lines, so trim some incidental churn during the rebase to get under 400 |
| #313 | Keep | Tests and docs only; the size exemption applies |
| #315 | Close | Its unconditional copy brings back stale files after an edit [output §F]. S2 replaces it. Port its two scenario tests (fork restores `ice/` and `mapping/`; duplicate restores `mapping/`) into S2/S3 |
| #316 | Keep, re-target onto #313 | It has no textual dependency on #315. Bump config.json to 1.1 because it removes the `preview` output |
| #317 | Amend | Versioned record that is treated as a cache, `process_version`, portable fingerprints [output §E] |

**Timing stack**

| Item | Verdict | Details |
|---|---|---|
| #302 | Amend; merge to main on its own | Drop `anchor`: it changes no behaviour and is wrong for CESM-POP. Drop the unused per-method `time_sampling=` override. Raise `TypeError` instead of using `assert` [timing §4] |
| #303 | Amend | `freq` becomes a typed input (see T1) |
| #305 | Amend | Keep its real fixes (see T2) |
| #306 | Keep, re-target to main | It only touches cesm_ocean_output.py. Run its GLADE-only assertion before taking it out of draft |
| #297 | Amend, re-base onto #317 as a separate leaf PR | It waits on rm6 #76 (open) |

**Other PRs**

| Item | Verdict | Details |
|---|---|---|
| #321 | Merge now | Your CESM_crocodash MOM_RPS has `param_file_reader.py` (checked), so bundle/duplicate/fork fail today. S6 deletes this code later |
| #322 | Merge now | Every bundle or duplicate leaves `temp_case-*` directories in scratch. S6 deletes this code later |
| #269 | Rebase onto T2 and amend | `boundaries` is stored as JSON: either `"south"` or `{"name","axis","index","index_range","ocean_side"}` from `Segment.to_spec()`. `custom_segments` is then derived from it. Bump config.json. If it lands after R2, add `case_supergrid_path` to `forcing_inputs()`. Its removal of `expt` simplifies read-back |
| #311 | Separate track | Waits for ESMCI #50. Once rebased after R2: put `case_cyclic_x` in `forcing_inputs()` and `cyclic_x` in the state file, and bump config.json. Whichever vCG pointer bump lands second must include both. Only pin ESMCI main |
| #309 | Merge now | Independent |
| #271 | Leave out of this series | Its base, class-merge, isn't on main. Its ideas (session id set in `__init__`, the non-local flag decided once) are covered by R2 and S2 |

## 3. Ordered PR series

```
main─A1 #312─A2─A3 #310─A4 #313─A5 #316─A6 #317─┬─T1 #303'─T2 #305'        (T needs #302' on main)
                                                 ├─R1─R2─R3                   (T and R in parallel)
                                                 └─#297' leaf (rm6 #76)
main(after T2+R3)─P1─P2─P3─P4─S1─S2─S3─S4─[MCP M2]─S5─S6─S7
main(after R2; ESMCI V merged)─W1─W2─W3─W4         (in parallel with P and S)
Now, in parallel: #302', #306, #309, #321, #322 → main; ESMCI V1─V2; rm6 #76
MCP repo: M0 after A2, M1 after P3, M2 after S4
```

To rebuild stack A: close #315, rebase, then run `gh stack init read-crocodash-case config-schema-version declared-output-files output-files-reference-check forcing-preview-dry-run skip-finished-forcing-steps`.

**Stack A: forcing files** (CrocoDash, base main)

| PR | Branch | Title and scope | Key files | Lines | Tests | Unblocks |
|---|---|---|---|---|---|---|
| A1 | #312 read-crocodash-case | Unchanged | — | 162 | — | A2 |
| A2 | config-schema-version | **Version config.json and read it tolerantly.** The changes from the uncommitted work, plus: the new version policy for both state and config.json, `CONFIG_MIGRATIONS`, tolerant deserialize, `require_outputs`. Deletes the dead branch of `run_configurators` | base.py, case_state.py, driver.py, cli.py, case.py, recipe.py, shareable.py | ~380 | test_config_version.py: version checks, tolerant read, fingerprint, a minimal 1.0.0 fixture | Every PR that changes a param; M0 |
| A3 | #310 | Rebase onto A2, plus the meta-key filter | base.py | ≤400 | existing | A4 |
| A4 | #313 | Unchanged | — | 516 (tests/docs) | — | — |
| A5 | #316 | Rebase onto #313; config.json → 1.1 | — | ~225 | existing | — |
| A6 | #317 | Amend: versioned record, `process_version`, portable fingerprints | driver.py, base.py | ~390 | Record read as cache; same fingerprint across two inputdirs | T, R, S2 |

**Singles to main (in parallel now)**
- #302' (about 190 lines).
- #306.
- #309.
- #321 and #322.

**Stack T: time-aware forcing** (base A6; needs #302' merged)

**T1: #303' product-freq-subsample — "freq becomes a typed conditions input"**
- `freq_handling` is checked when a method is decorated; a misspelt value raises.
- Only methods that declare freq handling accept `freq`. That removes the `freq=None` boilerplate from static and script-only methods.
- `configure_forcings(freq=…)` becomes a conditions input:
  - validated in `validate_args` through `resolve_time_sampling`;
  - excluded from `get_function_default_args`;
  - passed to the access method only when the method handles `freq`.
- CESM-POP `declare` readers reject a `freq` finer than `MS`, which avoids the month-shift date bug [timing §4]. Bump config.json.
- Files: raw_data_access/base.py, datasets/*, forcing/mom6.py, case.py, docs.
- About 260 lines.
- Tests: the registry rules, the POP guard, and `freq` surviving a round trip through config.json.

**T2: #305' time-aware-forcing-steps — keep the chunk, window, lookback and empty-chunk fixes**
- Fix the off-by-one in `describe()`.
- GLORYS-RDA skips padded days that fall outside the archive, with a warning. Without this, a run starting 1993-01-01 asks for 1992-12-31 and fails.
- Delete the "power users can override" comment; P3 makes that true for real.
- Conflict with #316: keep `min_chunk_days` and `lookback_days`, drop `preview`. Add a regression test that monthly regrid chunks are never empty, to catch the risk in [timing R1].
- Bump config.json. About 380 lines.

**Leaf #297' bgc-fe-interior-source** (base A6)
- `output_files` names `MARBL_FE_INTERIOR_SOURCE_FILE` under `ctx.output_path` [timing R2].
- Adds a `require_outputs` guard.
- Bumps `process_version` for the BGC iron step and for conditions (the clipping change), so steps already finished rerun [output §E].
- Bump config.json. About 260 lines.
- Merge only after rm6 #76 has merged and the rm6 pointer is on rm6 main.

**Stack R: read-back Case** (base A6; in parallel with T)

**R1: case-files — "CaseFiles: one disk-and-CIME layer for a case"**
- Move `ReadCrocoDashCase` and rename it `CaseFiles`.
- Add `WorkflowContext.from_state`. The driver goes back to reading files directly.
- Add `xmlquery`, `get_value` and `xmlchange`.
- `ocn_dir` comes from the state file.
- `CaseBundle` temporarily subclasses `CaseFiles`.
- Files: case_files.py (new), base.py, driver.py, case.py, cli.py, shareable.py. About 320 lines.
- Tests: tests/test_case_files.py, made from the moved tests plus the `ocnice/` layout and a check of the CIME tool arguments.

**R2: configure-without-cvars**
- `user_nl_blocks.write` takes the caseroot and ninst, and writes its own log lines.
- `configure()`, `XMLConfigParam.apply`, StreamYears and runoff all go through `registry.case.files`:
  - runoff reads ROF_GRID and ROF_DOMAIN_MESH with `xmlquery`.
- session_id and grid_name come from the state file.
- `forcing_inputs()` is explicit, and `Case.xmlchange` and `Case.append_user_nl` become public.
- Deletes:
  - the cvars guard;
  - the `is_non_local` property;
  - `case_cime`;
  - every remaining cvars use under `forcing/`.
- About 370 lines.
- Tests:
  - two cases configured in one process, with the CIME tools mocked;
  - the rerun tests without the guard test;
  - the log assertion at test_base.py:248.
- Also brings in #321's 8-line fix to `tests/user_nl_helpers.mom_parser`.

**R3: case-from-caseroot**
- `from_caseroot` and the binding code.
- Lazy grid, topo and vgrid; `fcr` built from config.json.
- State file 1.2 and its migration.
- `expt` reads RUNDIR with `xmlquery`.
- About 300 lines.
- Tests on a fake caseroot:
  - configure writes the blocks and the expected xmlchange arguments;
  - process preview runs;
  - two read-back cases work in one process.

**Stack V: move code into visualCaseGen** (repo ESMCI/visualCaseGen, base ESMCI main; start now)

- **V1 user-nl-blocks:** move CrocoDash's module into vCG.
  - The caseroot and ninst are arguments.
  - The tag is a parameter, and the existing CrocoDash tag is recognised.
  - About 380 lines, with tests/1_unit/test_user_nl_blocks.py using tmp_path.
- **V2 stream-years** (base V1):
  - `cdeps_streams` plus the planning and applying code from atm.py.
  - The entry point is `align(cesmroot, case, component, mode, start, end, pad, narrow)`.
  - About 370 lines.
  - Tests: tests/2_integration/test_stream_years.py. vCG's CI checks out a full CESM tree, so these tests actually run. Today's test_atm.py skips everywhere [vcg §3].

**Stack W: switch CrocoDash to the vCG copies** (base main after R2)
- Each PR needs the `submodule-bump` label and regenerated API docs.
- **W1 use-vcg-user-nl-blocks** (about 260 lines):
  - bump the pointer;
  - case.py and case_files.py import vCG's module;
  - delete `forcing/user_nl_blocks.py`;
  - point its test at the vCG module.
- **W2 drop-moved-user-nl-tests:** test-only deletion.
- **W3 use-vcg-stream-years** (about 300 lines):
  - make atm.py the thin shim;
  - delete cdeps_streams.py.
- **W4 drop-moved-stream-tests:** test-only deletion.

If P1 lands first, W3 rebases on the atm.py changes.

**Stack P: configurable parameters** (base main after T2 and R3)

**P1: forcing-param-metadata**
- Adds `Input` with kind, type and choices.
- Makes the constructor-signature test strict.
- Adds JSON-only values, converted as they come in.
- Stores `date_range`; replaces `case_forcing_product` with `product_name`.
- Bumps config.json, with a migration:
  - `date_range` is rebuilt from start/end plus `date_format`;
  - `product_name` is copied from conditions.
- Files: base.py, every configurator, case.py. About 350 lines.
- Tests: test_params.py checks:
  - constructor sync;
  - coverage of the case inputs;
  - a JSON round trip for each configurator;
  - name uniqueness.

**P2: forcing-schema**
- Adds `describe` and `json_schema`.
- An unknown keyword raises `TypeError` with suggestions.
- The creation printout comes from `describe`, which fixes the misreported required arguments [params §3].
- `validate_config` uses the schema. That deletes the hand-written checks at recipe.py:61-77.
- Adds `dump --annotated`.
- About 350 lines. Unblocks M1 and S4.

**P3: forcing-inputs-record-intent**
- Conditions:
  - `function_overrides` becomes the input and `function_args` the resolved output;
  - `function_name=None` means auto: RDA when it is mounted, otherwise the script. This moves the MCP's rule from `MCP/tools/case.py:200-208` into CrocoDash;
  - chunk-size override inputs.
- WW3's step-day inputs are renamed.
- Runoff's resolved values move to outputs. Process steps read outputs.
- Migrations:
  - the old merged dict becomes the overrides, unchanged, which keeps old behaviour;
  - the WW3 renames.
- Bump config.json. About 330 lines.
- Tests: migrations checked against the fixtures.

**P4: lossless-case-yaml**
- A generic `user_args(config)` with no conditions special case [params §4].
- `case_to_yaml` works through `Case.from_caseroot().case_args()`.
- Deletes `generate_configure_forcing_args` and `remove_configs`.
- Adds `Case.reconfigure` and `crocodash reconfigure --caseroot [--config]`.
- About 320 lines.
- Tests: a round trip for each configurator with non-default values, covering:
  - `freq`;
  - the overrides;
  - chunk sizes;
  - custom segments once #269 is in.

**Stack S: sharing** (base P4)

**S1: creation-baseline**
- Writes the baseline file at the end of `__init__`.
- Adds `user_changes` and `apply_user_changes`.
- One replay.sh parser covers:
  - `./xmlchange`;
  - the absolute Tools path;
  - `--id`/`--val`;
  - comma lists.

  It replaces the two different parsers in shareable [inventory D].
- About 340 lines, tested on a fake caseroot.

**S2: fork-on-case**
- Adds:
  - `Case(session_id=…)`;
  - `fork_config`;
  - `fork`;
  - `copy_reusable_outputs`;
  - the target guards.
- `crocodash duplicate` becomes fork with no changes.
- About 380 lines.
- Tests in tests/test_fork.py:
  - files are reused when fingerprints match;
  - files are skipped after a date edit;
  - a user override survives;
  - the guard fires;
  - #315's two scenario tests.

**S3: bundle-v2**
- `Case.bundle` and `from_bundle`, with paths rebased onto the bundle.
- The legacy reader for v1 bundles.
- The CLI's `bundle` and `fork` switch over.
- About 360 lines.

**S4: fork-prompts**
- Prompts for each param from `describe`. After prompting, the whole registry is validated, and the offending param is asked again on error.
- Confirms what to carry over.
- `--write-yaml` writes the annotated YAML:
  - REQUIRED flags;
  - defaults;
  - choices;
  - a `carry:` block.
- `--yaml` reads an edited file. `--no-input` asks nothing.
- shareable.md becomes sharing.md.
- About 330 lines.

**Deleting shareable**
- **S5 drop-shareable-tests:** test-only.
- **S6 drop-reference-case:**
  - `CaseBundle`, `BundleDifferences`, identify/diff and its readers;
  - the CIME helpers;
  - `duplicate_case`;
  - about 390 lines removed.
- **S7 drop-shareable:**
  - everything left, including the module itself and its API docs entry;
  - about 380 lines removed.
- Splitting the deletion into S6 and S7 only serves the 400-line rule.

**MCP_CrocoDash**
- **M0** (after A2): use `read_config` and `CONFIG_META_KEYS` at `MCP/tools/status.py:40-47`, which would otherwise list `schema_version` as an active forcing. Also at resources.py:34 and case.py:63-70 and 844-852.
- **M1** (after P3):
  - `list_forcing_configs` returns `describe()`, which deletes `_SET_BY_CONFIGURE_FORCINGS` (discovery.py:18);
  - `validate_case_config` uses the schema;
  - drop the MCP's own function_name auto-selection.
- **M2** (after S4, before S5):
  - the bundle/fork/duplicate tools call the Case API;
  - `fork_case(..., forcings=, carry=)`;
  - a new `fork_template` tool returns the annotated YAML;
  - the monkeypatch at shareable.py:153 goes.

**What runs in parallel:**
- **Now:** stack A, the singles, V1 → V2.
- **After A6:** T, R, #297' and M0.
- **After R2 and V:** W, alongside P and S.
- **Critical path:** A → R → P → S.

All new tests are flat files (`tests/test_*.py`, `tests/forcing/test_*.py`) using the existing markers. They need no CESM, because the CIME tools are mocked.

## 4. How each decision is met

1. **A read-back Case does everything.**
   - R3: `from_caseroot`.
   - R2: writes that take the caseroot.
   - P4: `reconfigure`.
   - S3: bundling from a read-back case.
   - S2: a read-back case as the fork source.
   - It never runs create_newcase or case.setup.
2. **It bypasses vCG.**
   - R1/R2 use the CIME tools with `--caseroot`; cvars are only used during creation.
   - The guard is deleted.
   - A test configures two cases in one process.
3. **The CESM-case code moves to vCG.** V1/V2 in ESMCI, then W1–W4. A thin StreamYears configurator stays in CrocoDash, so the config.json entry and MCP output don't change [vcg opinion 2].
4. **shareable.py goes.** S1–S7. Where each surviving piece goes:
   - `copy_*`/`apply_*` become `CaseFiles.apply_user_changes`;
   - `bundle` becomes `Case.bundle`;
   - `duplicate_case` and `ForkBundle` become `Case.fork`/`from_bundle`;
   - the review prompts move to cli.py;
   - the YAML re-pointing becomes `fork_config`.
5. **Fork and duplicate merge.** S2 makes duplicate a fork with no changes. S3 keeps the bundle as the transport format, and it can be forked like a caseroot.
6. **Fork asks both ways.** P2 provides `describe` and the schema. S4 provides the interactive prompts and `--write-yaml`/`--yaml`. M2 calls the same `fork(config)` with a plain dict; the annotated YAML is just that dict with comments.
7. **schema_version, and checking future changes:**
   - A2: the version, the reader policy, migrations and tolerant deserialize;
   - a fingerprint test that forces a bump, plus fixtures for each released version;
   - bumps in A5, T1, T2, #297', P1, P3, #269, #311;
   - `reconfigure` regenerates derived outputs;
   - the state file follows the same rule (R3), the record is a cache (A6), the bundle has a manifest (S3) and the baseline is versioned (S1).
8. **Timing:** the real fixes stay (#305' chunking and windows, #306, #297'), and the extra concepts are cut (#302'). On `freq`:
   - **Why it is now a typed input:** CrocoDash's own chunking code (time_windows.py) reads `freq`, so it isn't something passed straight to the access function. Values only the access function reads stay in the overrides.
   - **Why one input and not two:** for a given product and method only one meaning applies — either thinning the data or declaring the archive's cadence. The prompt text comes from the product's declaration.

## 5. Top risks, and what is out of scope

**Risks:**
1. **A long chain with one person merging.**
   - Mitigation: the stacks run in parallel.
   - PRs blocked outside CrocoDash are leaves, never mid-stack: #297', W, #311.
2. **Tolerant reading could hide real errors.**
   - Mitigation:
     - required inputs still raise;
     - `require_outputs` guards the outputs a step needs;
     - the fingerprint test;
     - the version fixtures.
3. **Running the CIME tools from a read-back case:**
   - `--non-local` skips CIME's case-git commits [caseroot §6.3];
   - replay.sh now records absolute-path xmlchange commands, which S1's parser handles;
   - a dangling SRCROOT still blocks edits.
4. **vCG import cost and ESMCI acceptance.**
   - Importing any vCG module builds `GUI()`. So vCG imports stay confined to case.py and case_files.py.
   - Ask ESMCI to build the GUI lazily, as a follow-up.
   - The stream code relies on private CDEPS methods, which now run in vCG's CI [vcg opinion 5].
   - Until W lands, CrocoDash keeps working on its own copies.
5. **Behaviour changes users will notice:**
   - unknown kwargs raise (P2);
   - `function_name` is chosen automatically (P3);
   - the `bundle` CLI flags are gone (S3);
   - post-creation xmlchanges always run with `--non-local`.
6. **Rebase hazards:**
   - #316 against #305: there is a resolution rule and a regression test;
   - #297 against #310's `output_files`;
   - two PRs claiming the same config.json version: they conflict in `KNOWN_SCHEMAS`, so the clash is visible.
7. **Windows where the MCP could break:** M0 lands right after A2, and M2 before S5. `run_workflow(config_path=…)` doesn't change.
8. **Cases created before the baseline file** carry changes over by name only, which is what happens today.

**Out of scope:**
- removing vCG's global state during case creation;
- CIME `create_clone`;
- gallery templates generated from the schema;
- timestamp correction driven by `anchor`;
- time windows for WW3;
- separate IC and BC fingerprints [timing R5];
- repairing the SRCROOT of a case whose CESM was moved;
- vCG's `shell=True` xmlchange.

### Critical Files for Implementation
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/base.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/recipe.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/cli.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/mom6.py