# Plan: build the forcing overhaul around the case as stored on disk

**How sources are cited**
- Reports: OS = output-stack.md, TS = timing-stack.md, SI = shareable-inventory.md, CR = case-from-caseroot.md, PM = param-model.md, VM = vcg-move.md.
- `tip:` means `origin/skip-finished-forcing-steps`.
- Line numbers are on `tip` unless another ref is named.

## 1. Where the series ends up

### 1.1 Modules

| Module | What it owns after the series |
|---|---|
| `CrocoDash/case_state.py` | Stays a leaf module (it imports only json, pathlib and logging). It owns the reader and writer for every file CrocoDash persists, plus one shared version policy:<br>• the state file: `read` and `write` keep their names because the MCP server calls them; `SCHEMA_VERSION` stays **1.1.0**<br>• config.json: `CONFIG_FILENAME`, `CONFIG_SCHEMA_VERSION`, `CONFIG_UNVERSIONED="1.0.0"`, `CONFIG_META_KEYS`, `config_path(inputdir)`, `read_config`, `write_config`<br>• the process record: `RECORD_VERSION`, `read_record`, `write_record`<br>• the creation baseline: `read_baseline`, `write_baseline`<br>• the policy: `check_version(doc, path, supported)` |
| `CrocoDash/forcing/base.py` | Only the configurator framework:<br>• the Param classes, with a new `derived=True` flag on InputParam<br>• `BaseConfigurator`: a tolerant `deserialize`, `missing_outputs`, a `serialize` that checks values are JSON, `output_files`, a portable `process_fingerprint`, `process_version`, `clean(ctx, flag)`<br>• `ForcingConfigRegistry`, with a new `describe_args(compset)`; its filters use `CONFIG_META_KEYS`<br>• `WorkflowContext`<br>The dead `run_configurators(config_path)` branch (OS §C) is deleted. |
| `CrocoDash/read_case.py` (new) | **`ReadCrocoDashCase(caseroot, *, inputdir=None)`**: the only reader. It needs neither CIME nor vCG, and reads either a case or a bundle.<br>• Methods: `workflow_context`, `configurators`, `forcing_args`, `to_yaml(annotate=False)`, `fork_params`, `user_changes(target)`, `bundle(out)`.<br>• Plus `restore_outputs(src, dst)` and the bundle manifest constants.<br>• It imports only `case_state` and `forcing.base`, so neither cycle is possible: driver → reader, and shareable → recipe → case → driver. |
| `forcing/driver.py` | • `run_workflow(config_path, preview=False, force=False, **flags)` keeps its signature, because the MCP server and PBS scripts call it.<br>• Reads config.json once.<br>• Refuses stale entries.<br>• Skips finished steps; a step that does run starts clean. |
| `case.py` | `Case`:<br>• `__init__` (creation; signature unchanged)<br>• `from_caseroot`<br>• `configure_forcings` (signature unchanged, no `cvars`)<br>• `reconfigure_forcings(**changes)`<br>• `forcing_args`, `process_forcings`, `validate_case`<br>• `xmlchange`, `set_user_nl`, `apply_user_changes`<br>• `bundle`, `to_yaml`<br>• classmethod `fork`<br>• `expt` |
| `recipe.py` | Only the YAML create path. The forcings check moves before `Case()` (SI §G.8). `case_to_yaml` becomes a one-line wrapper (the MCP server imports it). `generate_configure_forcing_args` moves to the reader. |
| `cli.py` | Commands: create, dump `--annotate`, **configure** (new), process, bundle, fork, duplicate (an alias of fork), template. Also the prompt loop and the annotated-YAML writer. Its existing handler-local imports are for startup speed, not for dodging cycles, so they stay; every new module imports at the top. |
| `forcing/atm.py` | A registered StreamYears shim of about 60 lines that calls vCG. It keeps the `"streamyears"` config.json key, the MCP server's `list_forcing_configs` and the docs working (VM opinion 2). |
| vCG `custom_widget_types/case_tools.py` | • Keyword-only `caseroot=`, `ninst=` and `cimeroot=`, falling back to `cvars` so `CaseCreator`'s positional calls still work (VM §4).<br>• A new `xmlquery`.<br>• Commands built as argument lists instead of `shell=True`, with stderr in the error message. |
| vCG `custom_widget_types/user_nl_blocks.py` | The moved module, with an explicit caseroot and ninst, a `tool=` parameter for the marker text, and a new `upsert`. CrocoDash passes `"CrocoDash configure_forcings"`, so blocks in existing cases still parse (VM risk 3). |
| vCG `custom_widget_types/stream_years.py` | `cdeps_streams` plus StreamYears' `_plan`/`_apply`, reading `DATM_MODE`/`DROF_MODE` through a read-only CIME case. |

**Deleted by the end:**
- `shareable.py` and `tests/shareable/`
- `forcing/user_nl_blocks.py` and `forcing/cdeps_streams.py`
- the `cvars` guard (case.py:618-628)
- Runoff's `case_cime` argument and its `cvars` reads
- `BundleDifferences` and `non_standard_case_info.json`

### 1.2 Files on disk and how they stay compatible

**One policy for every versioned file.**
- A reader accepts any file with the same MAJOR version. A newer MINOR logs a warning and its unknown keys are ignored.
- A different MAJOR raises an error that names the remedy.
- Writers stamp the current version.
- This replaces the exact MAJOR.MINOR match, which would reject every existing case at the first bump (OS §D).

| File | Version | Written by | Compatibility |
|---|---|---|---|
| `caseroot/_crocodash_state.json` | **1.1.0, unchanged** | `Case.__init__` | Nothing new is stored in it. `esmf_mesh_path` is derived as `<supergrid dir>/ESMF_mesh_{grid}_{session}.nc` (CR §5). The reader takes paths from the state rather than assuming `ocn/`, so older `ocnice/` cases read correctly (CR §6.5). |
| `caseroot/_crocodash_baseline.json` (new, D4) | 1.0.0 | End of `Case.__init__`, once | Holds `{user_nl: {file: text}, replay_lines: N}`. When it is missing (cases made before D4), fork falls back to the old compare-by-name diff. |
| `inputdir/extract_forcings/config.json` | 1.0.0; a file with no version is read as 1.0.0; each schema change bumps MINOR | `configure_forcings` | **Inputs are the contract and outputs are a cache:**<br>• A missing input takes its constructor default, otherwise a `KeyError` names it.<br>• A missing declared output marks the entry **stale**. `process` then refuses with "run `crocodash configure --caseroot …`", which rebuilds the outputs from the stored inputs.<br>• A file that a tolerant reader can't absorb needs a MAJOR bump. |
| `…/process_record.json` | `record_version: 1` | driver | It behaves as a cache: a version mismatch or a parse error reads as `{}`.<br>• The fingerprint is portable: it holds this configurator's own inputs and those of the configurators it depends on, minus `case_*`, plus the declared `fingerprint_outputs` and `process_version`.<br>• The unread `files` list is dropped (OS §C). |
| `bundle.json` | 2.0.0 (the old layout counts as 1) | `ReadCrocoDashCase.bundle` | Fork rejects a bundle without a manifest: "re-bundle with CrocoDash ≥ X". |
| `crocodash_case.yaml` in the bundle | none | `to_yaml()` | Human-readable recipe. crocontainer's `run_case.sh:24` and cesm-runner's `container.py:399` look for this file to detect a bundle. Fork doesn't read it. |

**"Future version updates are checked."** A3 commits `tests/forcing/config_schema.json`, a golden file with each configurator's inputs (marked required or optional) and outputs, plus a golden list of state keys.
- The test regenerates both from the registry and from `Case.__init__`.
- Any difference without a version bump fails, and the failure message prints the new JSON to paste in.
- An added input that has no default, or a removed input, needs a MAJOR bump; any other change needs at least MINOR.

### 1.3 The Case read back from a caseroot

```python
Case.from_caseroot(caseroot, *, cesmroot=None) -> Case
```

**How it is built.**
- `cls.__new__` plus `_bind(ReadCrocoDashCase(caseroot))`.
- It never creates anything, never deletes anything, never writes the state file, and never runs `initialize_visualCaseGen`. That satisfies decision 2.
- It costs only a few small JSON reads.

**Loaded eagerly, as plain attributes.** They must be plain attributes because `ForcingConfigRegistry` turns public `__dict__` entries into `case_*` inputs (base.py:159-166; CR §6.7):
- caseroot, inputdir, cesmroot, compset_lname, machine, project, ninst
- atm_grid_name, rof_grid_name, ntasks_ocn, job_*
- session_id, grid_name, the grid, topo and vgrid paths, the derived esmf_mesh_path
- `is_non_local=True` (as `shareable.py:98` and `751` already assume) and `override=False`
- if config.json exists: `extract_forcings_path`, `_configure_forcings_called`, `date_range`, `boundaries`, `forcing_product_name`

**Loaded lazily.**
- forcing_config, record and baseline (through the reader).
- `ocn_grid`, `ocn_topo` and `ocn_vgrid` as `cached_property` (an instance assignment in `__init__` overrides them on a created case).
- `_cime_case`, which only `expt` uses.

**cesmroot override.**
- It applies to that one object and is not saved.
- It feeds `case_cesmroot` (StreamYears) and is passed as `cimeroot` to vCG `xmlchange`/`xmlquery`, so writes still work when the caseroot's tool symlinks point at a deleted install. This has already happened: `streamyr_v15` (CR §6.4).
- If the state's cesmroot no longer exists and no override is given, it warns.

**How writes reach the caseroot.**
- Every Case method passes `self.caseroot`, `self.ninst` and `self.is_non_local` explicitly.
- Configurators reach the case through `self.registry.case`.
- A static test fails if `cvars[` appears outside the `_configure_*` creation methods.

**Single read path.** The CLI commands process, dump, bundle and configure all get their case from `Case.from_caseroot`. The driver can't import case.py (case.py imports the driver), and a bundle is not a case you can write to, so those two use the `ReadCrocoDashCase` that `from_caseroot` wraps. There is one reader with two front ends.

### 1.4 Bundle and fork share one code path

**Bundle layout:** `<name>_case_bundle/` holds:
- `bundle.json`
- `crocodash_case.yaml`
- `caseroot/`: state, baseline, `user_nl_*`, `replay.sh`, top-level `*.xml`, `SourceMods/`
- `inputdir/`: `extract_forcings/{config.json, process_record.json}`, the three grid files, and every declared output file that exists, at the same relative paths

**One reader for both sources.** `ReadCrocoDashCase(b/"caseroot", inputdir=b/"inputdir")` moves every path recorded under the state's inputdir onto the bundle copy. A bundle and a live case therefore read the same way, and duplicate is fork with a caseroot as its source.

**Fork order:**
1. Create the Case. Grids load from the source's files. `override` stays off unless asked for, and fork refuses a target inputdir equal to the source's, or the same case name on the same machine (SI §G.1).
2. `apply_user_changes`.
3. `configure_forcings(**args)`.
4. `restore_outputs`.
5. Print which forcing files were restored and which still need processing.

**Restoring forcing files.** A step's files are copied only when:
- the portable fingerprints of the source and the new case are equal,
- the source's record doesn't contradict that, and
- every file the step declares exists in the source.

Copies follow the order of the declared lists, so names that embed the session id map correctly; globs copy into the target directory. This fixes:
- wrong segments after the boundary order changes (OS §F);
- stale OBC files kept after a date change (TS R4);
- BGC, chl and runoff files missed because their names contain the session id (SI §G.2);
- records that don't survive a fork (OS §F).

**Carrying over the user's own changes (D4).**
- **user_nl files**, including `_streams` and `_NNNN`: carry every line outside CrocoDash's blocks that isn't in the baseline. In the new case it replaces the line with the same key outside the blocks, or is appended. For older cases with no baseline, only keys the new case doesn't set are appended.
- **xmlchanges:** rerun verbatim, before configure, the `replay.sh` lines after `replay_lines` (for older cases, after the last `case.setup` line). `configure_forcings` then sets the forcing-owned variables again.
- **SourceMods:** all files. **XML files:** top-level `*.xml` files the new case lacks.
- The plan keys `xml_files`, `user_nl`, `source_mods`, `xmlchanges` don't change and default to True (matching shareable.md:29-31 and the MCP server).
- This needs no reference case and no MOM_RPS parser. Unlike the old name-only diff it carries values, overrides of forcing parameters and the stream files (SI §D).

## 2. What happens to each existing branch and PR

| Item | Disposition | What and why |
|---|---|---|
| #309 | **Merge as-is now** | 13 lines and independent. Merging it before D1 means D1's later edit of `_apply_final_xmlchanges` is a simple rebase. |
| #321 | **Merge as-is now** | Fixes `ModuleNotFoundError` in bundle, duplicate and fork with the MOM_RPS split. No overlap with anything (OS §B). E3 moves `_load_FType_MOM_params` into `tests/user_nl_helpers.py`, its only remaining user. |
| #322 | **Merge as-is now** | Fixes the `temp_case-*` directories left in scratch. Deleted in E3 together with the reference case. |
| #312 | **Amend in place (A1)** | • Move the class to `read_case.py`. That frees base.py from the source-scan guard's blind spot (OS §D.1) and gives bundle, YAML and fork a home outside base.py.<br>• Read `forcing_config` lazily, so it isn't read 3 times and isn't read when `--config` names another file (OS §C, §D opinion).<br>• Take `ocn_dir` from `supergrid_path` (CR §6.5).<br>• Move the test to `tests/test_read_case.py` and regenerate the API docs. |
| config-schema-version (uncommitted worktree) | **Commit as A2 on top of A1** | • Put the helpers in `case_state.py`.<br>• Use the shared MAJOR-only policy (OS §D bump issue).<br>• The reader, `run_workflow` (before the reader, as its test requires), cli, case.py and recipe read through `read_config`.<br>• Its 3 hunks that target code #312 deletes simply disappear (OS §D). |
| #310 | **Rebase onto A3 and amend** | • `configurators()` must skip `CONFIG_META_KEYS`, or it raises `TypeError` on any versioned file (OS §D.2).<br>• After T0, declare `MARBL_FE_INTERIOR_SOURCE_FILE` (TS R2).<br>• Move its `test_configurators` additions (16 lines) into #313 to get under 400 lines (it is +230/−174 today). |
| #313 | **Keep** | Rebase only. It is the test-only exception (~530 lines). |
| #315 | **Close** | Its `_copy_output_files` copies files without checking the configuration (OS §F boundary example; TS R4), misses files named with the session id (SI §G.2), and lives in the file being deleted. E1a replaces it with the fingerprint-gated restore. |
| #316 | **Keep, rebased onto #313** | • A MINOR schema bump, since it drops the `preview` output.<br>• Merge it **before** #305 so that #305's rebase, not #316's, resolves the shared lines. That removes the risk of silently dropping `min_chunk_days`/`lookback_days` (TS R1). |
| #317 | **Amend in place (B4); split part out (B5)** | B4:<br>• make the fingerprint portable and drop `case_*` inputs; conditions' `_fingerprint` becomes inputs-only, which also fixes R6 (TS)<br>• version the record and move its I/O to `case_state`<br>• drop `files`<br>B5 takes `--force`: it is currently a no-op for ic/bc, because `_merge_boundary` (obc.py ~654) and the IC `_all_written` check (mom6.py ~336) skip finals that already exist. |
| #302, #303 | **Close; re-cut as T1** | Removes:<br>• the failure at import time for any product defined outside the repo<br>• `anchor`/`cell_method`, which change no behaviour<br>• the method-level override nothing uses<br>• `freq_handling` typos being silent<br>• POP daily dates shifted back a month<br>• `freq` being lost on the round trip (TS §3, §4)<br>• #303's import conflict with the worktree (TS §2.8) |
| #305 | **Keep as T2, rebased onto T1 and #316, and amended** | Details in §3. |
| #306 | **Keep as T3** | Take it out of draft after the GLADE-only assertion has been run on GLADE. |
| #297 | **Retarget to main (T0)** | • Its code doesn't depend on #302–#306 (TS §0).<br>• It is approved and the MARBL fix is real.<br>• Merge rm6 #76 first, then re-pin rm6 to that merge commit.<br>• Landing it before #310 removes R2 (TS). |
| #269 | **Hold until D3b; then amend** | • Give custom segments a JSON form, because `Segment` objects can't round-trip (PM §8).<br>• Relax the boundary check at recipe.py:68.<br>• Declare output files for custom segments.<br>• MINOR schema bump. |
| #311 | **Hold until D1** | Merge vCG #50 so D1's submodule bump carries it; #311 then drops its own pointer change. `cyclic_x` still works from the lazily loaded grid. |
| #271 | **Close** | Its base, `class-merge`, isn't in main. D1 delivers its session_id and is_non_local cleanups. CESM_NOT_PORTED is out of scope. |

## 3. The PR series in order

Size estimates count changed lines, tests included.

**Do now, all in parallel:**
- Merge #309, #321 and #322.
- Merge rm6 #76, then **T0** (#297 rebased onto main, ~220 lines).
- Open stacks S1, S2 and S5. S5 opens as soon as its base, #316, is rebased.

### Stack S1 `case-model` (CrocoDash; base main)

| # | Branch | Title | Scope and deletions | ~Lines | Tests | Unblocks |
|---|---|---|---|---|---|---|
| A1 | read-crocodash-case (#312) | Read a case back through `ReadCrocoDashCase` | See §2. Deletes `driver._load` and `_build_context`. | 190 | test_read_case.py | A2 |
| A2 | config-schema-version | Version config.json; read it only through `read_config` | `case_state` helpers and policy; every reader goes through it; meta-key filters (base, recipe); deletes the dead `run_configurators` branch; the guard now skips `case_state.py`. | 330 | tests/forcing/test_config_version.py (adapted from the worktree): a file with no version is accepted after a MINOR bump and rejected after a MAJOR bump | A3 |
| A3 | tolerant-config-schema | Read older config.json entries; refuse stale ones with a reconfigure hint | Tolerant `deserialize`; `missing_outputs`; the driver refuses stale steps that are requested, plus their dependencies; `serialize` checks values are JSON; the two golden files. | 350 | Tolerance and golden tests | B1, T0's bump, S5 |
| B1 | declared-output-files (#310) | Declare each forcing's output files | Amendments in §2. | 395 | Existing tests | B2 |
| B2 | output-files-reference-check (#313) | Test declared files against the settings | Test-only. | 530 | — | B3 |
| B3 | forcing-preview-dry-run (#316) | Replace the ic/bc preview with a driver dry run | Plus the golden-file and MINOR bump. | 230 | Existing tests | B4, S5 |
| B4 | skip-finished-forcing-steps (#317) | Skip steps that are already done | Amendments in §2. | 390 | Record versioning; a fingerprint that ignores `case_*` | B5 |
| B5 | rerun-steps-from-clean | A rerun step starts from clean files | • `process_version` goes into the fingerprint.<br>• `clean(ctx, flag)` (default: delete that flag's declared outputs; conditions also deletes raw and regridded data) runs before a rerun under `--force` or after a fingerprint mismatch.<br>• This covers code-only changes like 37cea8d3 (OS §E). | 150 | `--force` regenerates files; the engines' skip of existing files is bypassed | S3 |

### Stack S2 `vcg-case-writers` (ESMCI/visualCaseGen; base ESMCI main; runs in parallel with S1)

The user has merge rights there and self-merges; ask alperaltuntas to review V2 and V3.

| # | Branch | Title | Scope | ~Lines | Tests |
|---|---|---|---|---|---|
| V1 | caseroot-explicit-case-tools | case_tools take an explicit caseroot | Keyword-only `caseroot`, `ninst`, `cimeroot`; `xmlquery`; argument lists; stderr in errors. | 150 | 1_unit, with a stub `xmlchange` script in `tmp_path` |
| V2 | user-nl-blocks | Move CrocoDash's user_nl blocks into vCG | The module, generalised by `tool`; `upsert`. | 390 | 1_unit |
| V3 | stream-years | Align DATM/DROF stream years to run dates | `plan(caseroot, cesmroot, y0, y1, padding, narrow)` and `apply(...)`; the CDEPS calls are isolated in one function. | 370 | 2_integration. These tests currently skip everywhere (VM §1); vCG CI will run them. |

### Stack S3 `case-readback` (CrocoDash; base B5; retarget to main once S1 merges)

| # | Branch | Title | Scope and deletions | ~Lines | Tests | Depends on |
|---|---|---|---|---|---|---|
| D1 | write-through-caseroot | Write to the case through an explicit caseroot | • Bump vCG to V1 (`submodule-bump` label).<br>• Delete the guard.<br>• `self.session_id` and `self.is_non_local` (`cime.machine != machine`) are set once and used at case.py:383, 630, 671-686, 1089 and 1106-1119.<br>• Every write passes caseroot and ninst; `XMLConfigParam.apply(caseroot, …)`.<br>• Runoff: `xmlquery ROF_GRID/ROF_DOMAIN_MESH` replaces `case_cime` and `cvars`; resolved or suggested values move to outputs, so inputs stay "what the user asked for" (PM §7.7).<br>• MINOR schema bump. | 260 | Two Cases in one process each write into their own caseroot; replaces the guard test at test_configure_forcings_rerun.py:164-177 | V1 |
| D3a | case-from-caseroot | Read a Case back from its caseroot | • `from_caseroot` and `reconfigure_forcings` (stored args merged with changes; `None` deletes a key).<br>• `validate_case` and `_print_forcing_files` use `configurators()`.<br>• Lazy grids and `_cime_case`.<br>• CLI `configure`; process, dump and bundle go through `from_caseroot`. | 320 | Every `case_*` constructor argument is in `vars(from_caseroot(fixture))`; a reconfigure replay with patched helpers; no CESM needed | S1 |
| D3b | forcing-args-round-trip | Make dump → create an exact inverse | • Move the args and YAML functions to the reader.<br>• Emit `function_overrides` (the difference from the access-method defaults; fixes PM §4 and SI §G.4).<br>• `derived=True` on `start_date`, `end_date`, `calendar`, `function_args`. | 360 | configure → `forcing_args` → configure gives the same inputs | D3a |
| E1a | bundle-from-case | Bundle a case without CIME | Moving bundle paths onto a new root, `bundle()`, `restore_outputs`. | 300 | Restore gated on a matching fingerprint, including after a boundary reorder and with session-id names | D3b |
| E2 | fork-params | Ask for every forcing parameter on fork | • `describe_args`: required/default/help/is-path from the constructor and the InputParam comments, plus `arg_help` for arguments only the constructor takes.<br>• `fork_params`, the annotated YAML writer, the prompt loop (end of input keeps the defaults). | 300 | Annotation contents; required parameters flagged | D3b |
| D2 | use-vcg-stream-years | Use vCG's user_nl blocks and stream years | • Bump vCG to V3; delete the two CrocoDash modules and their tests.<br>• atm.py shim with a `case_caseroot` input.<br>• Regenerate `CrocoDash.forcing.rst`. | **~1000, about 900 of it deleted moved code**: a flagged exception | Shim test with patched vCG | V3 |
| D4 | creation-baseline | Record what creation wrote; edit cases explicitly | Baseline file; `Case.xmlchange`; `Case.set_user_nl` (upsert); `user_changes` and `apply_user_changes`. | 330 | Baseline diff, fallback for cases without a baseline, upsert | D2 |
| E1b | fork-case | One fork for bundles and caseroots | • `Case.fork(source, *, caseroot, inputdir, changes=None, plan=None, override=False)`.<br>• CLI fork, duplicate and bundle switched. Kept as they are: `--bundle`, `--plan` and its keys, and end-of-input defaults, all used by crocontainer's `run_case.sh:25-32`. `bundle` loses `--cesmroot`, `--machine`, `--project`.<br>• Recipe pre-flight check. | 380 | Duplicate with no changes; fork with changes; guards | E1a, E2, D4 |
| E3 | remove-shareable | Delete shareable | Delete `shareable.py` and `tests/shareable/`; rewrite shareable.md. | Deletion: flagged exception | — | M1, C1 |

**Lands between E1b and E3 (other repos):**
- **M1**, `CROCODILE-CESM/MCP_CrocoDash`, branch `use-case-fork`: switch `bundle_case`, `fork_case` and `duplicate_case_tool` to `Case.fork(..., changes=, plan=)` and the reader; optionally use `describe_args` in `list_forcing_configs`.
- **C1**, `crocontainer`: bump its CrocoDash submodule. `run_case.sh` doesn't change.

### Stack S5 `timing` (CrocoDash; base B3's branch; retarget to main later)

| # | Branch | Title | Scope | ~Lines |
|---|---|---|---|---|
| T1 | product-record-freq | Typed record cadence | • Products declare `time_sampling` as an alias string, `None` or `USER_SPECIFIED`.<br>• `@accessmethod(freq="subsample"\|"declare")`, checked when the product is registered; only those methods take `freq`.<br>• Conditions gets an optional input `record_freq` (it arrives through `configure_forcings` `**kwargs`, so no signature change), validated once; the resolved cadence is stored in outputs.<br>• POP's month shift applies only to monthly data.<br>• MINOR schema bump. | 300 |
| T2 | time-aware-forcing-steps (#305) | Size chunks and windows to the cadence | • Read T1's resolved cadence (delete `native_sampling`).<br>• Delete the `or` fallbacks: A3 marks old entries stale, and the fallbacks were never reachable anyway (TS §2.7).<br>• Fix the off-by-one in `describe()`.<br>• Clamp padding at a coverage start the product declares (the GLORYS-RDA 1993 regression).<br>• Add a test that `min_chunk_days` and `lookback_days` reach `obc`/`ic` (closes R1).<br>• MINOR schema bump; re-pin rm6 with #77 if monthly timestamps need it. | 360 |
| T3 | cesm-tseries-slice-time (#306) | Slice CESM tseries to the requested range | As it is. | 140 |

### When each stack can move

- **S1, S2 and T0** start now.
- **S5** opens on #316's branch.
- **S3** opens on B5 once V1 is merged.
- **D2** waits for V3, and **D4** waits for D2. Everything else in S3 can be reviewed while they wait.
- **M1 and C1** land after E1b; then **E3**.
- **#269** follows D3b and **#311** follows D1.

## 4. How each decision is met

1. **A Case read back from its caseroot can do everything** (configure, process, xml and user_nl edits, bundle):
   - D1 removes `cvars` from every write.
   - D3a adds `from_caseroot`, configure, reconfigure, process and validate.
   - D3b makes the stored arguments exact.
   - D4 adds `Case.xmlchange` and `set_user_nl`.
   - E1a adds `bundle`.
   - `create_newcase` and `case.setup` are never called on this path.
2. **The read-back Case bypasses vCG's global state.**
   - `from_caseroot` never calls `initialize`.
   - Writes go through V1's helpers with an explicit caseroot.
   - The guard is deleted in D1, so the "writes go into the last case created" problem is gone.
   - The MCP server's `CASE_BUILD_LOCK` is needed only while a case is being created.
3. **The case configuration moves into vCG.**
   - V2 moves user_nl blocks, V3 moves stream years, D2 deletes CrocoDash's copies.
   - The StreamYears shim stays registered, and the block marker text is unchanged.
4. **shareable.py goes away entirely.** E3 deletes it once everything it does has another home:

   | shareable item | New home |
   |---|---|
   | `CaseBundle`, `_load_state_from_crocodash`, `get_user_nl_value` | The reader |
   | `bundle` | `ReadCrocoDashCase.bundle` |
   | `identify_non_standard_case_info`, `diff`, `_read_user_nls`, MOM_RPS loader, `_get_case_obj`, `_run_xmlquery`, `_remove_case_output_dirs`, `BundleDifferences` | Deleted (baseline plus a diff computed at fork time) |
   | `copy_*` and `apply_*` helpers | `Case.apply_user_changes` |
   | `_copy_output_files` | `restore_outputs` |
   | `ForkBundle`, `fork`, `duplicate_case` | `Case.fork` |
   | prompts and `ask_*` | cli.py (E2) |

5. **Fork and duplicate are one command; a bundle is still the transport.** E1b; duplicate is fork with a caseroot as the source and no changes. Bundles carry `bundle.json` version 2.0.0.
6. **Fork asks for each parameter both ways.** E2, wired up in E1b:
   - `fork` prompts by default.
   - `--write-params` writes the annotated YAML (required parameters flagged; defaults and help as comments); `--params` reads it back.
   - The MCP server calls the same `fork_params` and then `Case.fork`.
   - "JSON-configurable by requirement" is enforced by A3 (serialize checks values are JSON) and by D3b's round-trip test.
7. **config.json gets a schema_version.**
   - A2 is its home, directly on top of #312.
   - A3 makes reading tolerant and adds the golden check for future bumps.
   - B4 and B5 version the record and add `process_version`.
   - The state file stays at 1.1.0, because the baseline is a separate file.
8. **The timing stack is revised but keeps its fixes:**
   - T0 is kept (rebased onto main).
   - T1 re-cuts #302 and #303 with typed `record_freq` and fewer concepts.
   - T2 keeps #305's fixes and fixes its two new bugs (the off-by-one and the archive-edge padding).
   - T3 keeps #306.

## 5. Top risks, and what is out of scope

### Risks

1. **ESMCI review is slow, or V2/V3 are refused.**
   - V1 is about 150 lines.
   - Only D2 and D4 consume V2 and V3, and both sit late in S3.
   - If they are refused, D2 is dropped and D4 puts `upsert` in CrocoDash's own `user_nl_blocks`; no other PR changes.
2. **The bundle format change breaks the container and the MCP server.**
   - crocontainer forks inside its own pinned CrocoDash (`run_case.sh:25-32`), and cesm-runner requires `crocodash_case.yaml`.
   - E1b keeps the flags, the plan keys, the end-of-input defaults and the YAML marker.
   - `bundle.json` gives a clear error on a format mismatch.
   - C1 and M1 must land before E3.
3. **Older cases** (no config version, `ocnice/`, no baseline, no record, a deleted cesmroot):
   - tolerant reading plus the stale check and `configure`
   - paths taken from the state
   - the name-based diff at fork time
   - restore gated on a fingerprint computed from config.json
   - the `cesmroot=` override
   - CI can't cover this. Validate manually on `streamyr_v15`.
4. **A moved cesmroot.** The CIME tools may still read the stale `SRCROOT` in `env_case.xml` (CR §6.4, unverified). Document it this way: reading, processing and stream planning work; xml writes need a working CIME.
5. **`is_non_local=True` on read-back** skips CIME's case-git commits for those xmlchanges (CR §6.3). Documented.
6. **Rebase hazards.** R1 is handled by stacking S5 on #316 plus the wiring test; R2 by landing T0 before #310; the worktree conflicts by placing A2 on A1; D1-vs-S1 conflicts by stacking D1 on top of S1.
7. **Code-only changes no longer invalidate records automatically** once fingerprints are inputs-only. Mitigation: B5's `process_version`, plus a line in the PR template asking whether a change alters process output.
8. **CIME is process-global**: the first `sys.path` entry wins (CR §6.2). `from_caseroot` doesn't import CIME unless it is needed.

### Out of scope

- A typed parameter model (types, choices, units) beyond the `derived` flag and `describe_args`.
- WW3 time windows and `ww3_obc_function_overrides.freq`.
- CESM_NOT_PORTED (#271).
- Changing the grid or compset of an existing case.
- Reconfiguring automatically inside the driver.
- Importing old-format bundles.
- Saving cesmroot overrides.
- Hardlinking files on duplicate.
- Adding chunk-plan lines back to `--preview`.

### Critical Files for Implementation
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/base.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case_state.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/driver.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_tools.py