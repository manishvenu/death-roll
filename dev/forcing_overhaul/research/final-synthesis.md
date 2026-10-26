# Forcing overhaul: the final plan

Sources are cited as follows: [OUT], [TIME], [SHARE], [CFC], [PARAM] and [VCG] are the six reports; [LTR], [COD] and [CF] are the three proposals; [FEAS] and [SEQ] are the two critiques. `tip` means `origin/skip-finished-forcing-steps`. Sizes are changed lines (additions plus deletions).

**Facts I re-checked for this synthesis:**
- **Old configs already fail today.** Main's `deserialize` is strict (`base.py:677-689`). 53 of the 69 `config.json` files under `/glade/derecho/scratch/manishrv/croc_input` lack the conditions output `ENABLE_BUGS_BY_DEFAULT`, so `crocodash process` already fails on them. None of the 69 is versioned, and 66 still carry `preview`.
- **The import graph rules out a new reader module.** `forcing/__init__.py` imports every module in the package, `driver.py` included. `check_version` requires an exact MAJOR.MINOR match.
- **`--force` does nothing for ic/bc today.**
  - `stale_outputs` (added in #294, already on main) deletes conditions and WW3 files when a reconfigure changes their configuration.
  - `--force` only bypasses `is_done`, and the engines skip finished files (`obc.py:654`, `mom6.py:336-345`).
- **External bundle contract and CI blind spots.**
  - The container CI job copies the current CrocoDash into the image but runs the image's own `run_case.sh:24-32`. That script detects a bundle by `crocodash_case.yaml` and runs `crocodash fork --bundle … --plan`.
  - cesm-runner's `container.py:399` also requires `crocodash_case.yaml`.
  - The bundle and container jobs run only on main or `workflow_dispatch`, and CI never passes `--runslow`.
- **Open PRs.**
  - #269 (559 lines) deletes `ignore_degenerate=True` together with its polar-domain comment.
  - #295 (amrhein, 351 lines, unreviewed) overlaps the stacks in only one `reference.py` hunk, against #302.
  - #306 touches one module plus its test.
  - The POP month shift is already on main. The `freq="D"` bug only appears once #303 lets POP take `freq`.

---

## 1. Target end state

### 1.1 Architecture

| Module | What it owns at the end | What is removed |
|---|---|---|
| `forcing/base.py` | <ul><li>The configurator framework.</li><li>Tolerant `deserialize`, `ReconfigureRequired` and `require_output_param`.</li><li>`InputParam(derived=…)`, `ParamSpec` and `registry.param_specs()`.</li><li>`read_config`, `write_config`, `CONFIG_*` and `CONFIG_MIGRATIONS`.</li><li>`WorkflowContext`, with its Grid/Topo imports moved to the top.</li><li>**`ReadCrocoDashCase`**: read-only, with no CIME and no cvars, for a caseroot or a bundle. It provides `state`, `inputdir`, `ocn_dir` (the supergrid's directory), a lazy `forcing_config`, `workflow_context(config=None)` and `configurators()`.</li></ul> | <ul><li>The dead `run_configurators(config_path)` branch.</li><li>The scan of `case.__dict__`.</li></ul> |
| `case_state.py` | <ul><li>State I/O; `SCHEMA_VERSION` stays **1.1.0**.</li><li>The one version policy, `check_version(doc, path, supported, migrations)`.</li></ul> | — |
| `forcing/driver.py` | <ul><li>`run_workflow(config_path, preview, force, **flags)`, signature unchanged (MCP `_bg_worker.py:38` calls it).</li><li>A versioned record.</li><li>Portable fingerprints.</li><li>`clean` before a forced or out-of-date rerun.</li></ul> | — |
| `case.py` | `class Case(ReadCrocoDashCase)`: <ul><li>`__init__` (creation; the only place cvars are used; takes `session_id=None`) and `from_caseroot`.</li><li>`forcing_inputs` and `forcing_args`.</li><li>`configure_forcings`, `process_forcings` and `validate_case`.</li><li>`xmlchange`, `set_user_nl`, `user_changes` and `apply_user_changes`.</li><li>`bundle`, `fork`, `fork_params` and `expt`.</li></ul> | <ul><li>The CASEROOT guard.</li><li>cvars reads after creation.</li><li>Runoff's `case_cime`.</li></ul> |
| `recipe.py` | YAML only: <ul><li>load and validate (forcings are checked *before* `Case()`);</li><li>the builders and `create_case_from_yaml`;</li><li>a lossless `case_to_yaml`;</li><li>`annotated_yaml`.</li></ul> | <ul><li>`generate_configure_forcing_args`, which becomes `Case.forcing_args`.</li><li>`remove_configs`.</li></ul> |
| `cli.py` | <ul><li>Commands: create, dump [`--annotate`], **configure** (new), process, bundle, fork, duplicate (= `fork --no-input`), template.</li><li>The prompt loop.</li></ul> | — |
| `forcing/atm.py` | A registered `StreamYears` shim of about 40 lines, keeping the same name, inputs and outputs, that calls vCG. | The CDEPS logic |
| vCG `case_tools.py` | <ul><li>Keyword-only `caseroot=` and `ninst=`, falling back to cvars so `CaseCreator`'s positional calls stay valid.</li><li>Commands built as argument lists, with stderr in the error message.</li></ul> | `shell=True` |
| vCG `custom_widget_types/user_nl_blocks.py` and `stream_years.py` | The moved modules, taking the caseroot and ninst explicitly, with a `tag=` parameter. CrocoDash passes today's marker text. | — |
| Deleted outright | <ul><li>`shareable.py` and `tests/shareable/`.</li><li>`forcing/user_nl_blocks.py` and `forcing/cdeps_streams.py`.</li><li>`BundleDifferences` and `non_standard_case_info.json`.</li></ul> | |

The import graph keeps its shape: base ← driver ← case ← recipe ← cli. There are no new top-level modules, so no new import cycles and no API-doc churn beyond the deletions.

### 1.2 Files on disk and their compatibility rules

**One policy for every versioned file** (`case_state.check_version`):
- Same MAJOR.MINOR: accept.
- Older MINOR: run `migrations` one step at a time. If a step is missing, refuse.
- Newer MINOR, or a different MAJOR: refuse with "written by a newer CrocoDash; upgrade".
- An unversioned `config.json` is read as 1.0.0. An unversioned state file logs a warning, as today.

| File | Version | Rules |
|---|---|---|
| `caseroot/_crocodash_state.json` | 1.1.0, unchanged | <ul><li>Nothing is added to it.</li><li>`esmf_mesh_path` is derived as `<supergrid dir>/ESMF_mesh_{grid}_{session}.nc`, with a glob as fallback.</li><li>Paths come from the state file, so older `ocnice/` cases read correctly [CFC §6.5].</li></ul> |
| `caseroot/_crocodash_baseline.json` (new) | 1.0.0, optional | <ul><li>Holds `{replay_lines, user_nl:{file:text}, xml_files}`, written once at the end of `Case.__init__`.</li><li>If it is missing or has an unknown version, fork falls back to comparing names.</li></ul> |
| `inputdir/extract_forcings/config.json` | Written as 1.0.0 | **Per-entry tolerance, which needs no version bump:** <ul><li>a missing input takes its constructor default, otherwise raises `ReconfigureRequired`;</li><li>a missing output reads as `None`, and `require_output_param` raises only where a step needs that output;</li><li>extra keys are ignored.</li></ul> **When to bump MINOR** (with a migration and a golden fixture): only when tolerant reading would *silently misread* an old file, or when a migration can genuinely upgrade it (renames). No PR in this series needs a bump. |
| `…/process_record.json` | `{schema_version:"1.0.0", steps:{flag:{fingerprint, files}}}` | Treated as a cache. A missing file, another version or an unparseable file reads as `{}`, so the steps rerun **without cleaning**; the engines skip files that already exist. |
| Bundle `bundle.json` | 2.0.0 | Older bundles are refused with "re-bundle, or `crocodash create --config crocodash_case.yaml`". |
| Bundle `crocodash_case.yaml` | — | Stays at the top of the bundle: it is the human-readable recipe and the marker crocontainer and cesm-runner look for. |
| user_nl block markers | Text frozen | vCG takes a `tag=` parameter, and CrocoDash passes `CrocoDash configure_forcings` [VCG risk 3]. |

**How future version changes get checked:**
- Golden `config.json` fixtures copied from real cases must load.
- A committed parameter snapshot must match. Every parameter change is then a reviewed diff, and the failure message prints the new snapshot and asks "tolerated, or bump plus migration?".
- The migration chain from 1.0 to the current version must be complete.

**Fingerprint.** One function serves both the driver's skip check and fork's file restore. It is built from:
- the configurator's own `config.json` entry, plus the entries it depends on, plus the conditions dates for CICE and WW3;
- with absolute paths under the inputdir or cesmroot rewritten as `$INPUTDIR` or `$CESMROOT`;
- plus a per-class `process_version`.

`clean(ctx, flag)` runs before a rerun when the recorded fingerprint differs, or under `--force`. It deletes the step's declared outputs; conditions also deletes unfilled ICs and regridded chunks, but keeps raw downloads. A step with no record entry is never cleaned, so resuming after a crash stays cheap [FEAS].

### 1.3 The Case read back from disk

```python
case = Case.from_caseroot(path, *, cesmroot=None)  # caseroot or bundle; no create_newcase, case.setup, or vCG initialize
case.configure_forcings(**case.forcing_args() | changes)
case.process_forcings(force=False, bc=True)
case.xmlchange("STOP_N", 30); case.set_user_nl("mom", {"DT": 900})
case.bundle(out_dir)
new = Case.fork(path, caseroot=..., inputdir=..., changes=..., plan=...)
```

- **One construction path.** `__init__` creates the case and then calls `_bind(caseroot)`; `from_caseroot` is `cls.__new__` plus `_bind` [CFC §7A]. Created and read-back cases can't drift apart.
- **Loaded eagerly, as plain attributes from the state file:**
  - caseroot, inputdir, cesmroot (an override wins), compset_lname, machine, project, ninst;
  - the atm and rof grid names, ntasks_ocn, job_*;
  - session_id, grid_name, and the grid, topo, vgrid and mesh paths;
  - `override=False`;
  - `is_non_local`: computed once at creation, and `True` on read-back, as shareable already assumed;
  - extract_forcings_path;
  - `_configure_forcings_called`, which is whether `config.json` exists.
- **Loaded lazily:**
  - `forcing_config`, re-read after configure so it never goes stale [FEAS];
  - `ocn_grid`, `ocn_topo` and `ocn_vgrid` as `cached_property`; on a created case, the instance values win;
  - `_cime_case`, CIME's `Case(read_only, non_local)` from `<cesmroot>/cime`. This import happens at run time because the path is only known then; it is not there to dodge a cycle. Only StreamYears, runoff and `expt` use it.
- **`forcing_inputs()`** is an explicit dict of the `case_*` values: cesmroot, inputdir, compset_lname, session_id, grid_name, esmf_mesh_path, supergrid_path and forcing_product, plus cyclic_x once #311 lands. It replaces the `__dict__` scan, so lazily loaded attributes can't silently disappear [CFC §6.7]. A coverage test enforces it.
- **The cesmroot override** affects only what CrocoDash itself reads (CDEPS XML, the CIME import) and is never saved. A case whose SRCROOT is gone, such as `streamyr_v15`, can be read, processed, bundled and forked; edits to it fail with a clear message [FEAS].
- **Every write names its caseroot.**
  - vCG `xmlchange(..., caseroot=)` and `user_nl_blocks.write(..., caseroot=, ninst=)`; configurators reach the case through `registry.case`.
  - A static test allows `cvars[` only in creation methods.
  - This deletes the guard and the "writes go to the last case created" bug, and the MCP's `CASE_BUILD_LOCK` is then only needed around creation.

### 1.4 Bundle and fork

**Bundle layout:**
```
<name>_case_bundle/
  bundle.json
  crocodash_case.yaml
  caseroot/
    state, baseline, user_nl_*, replay.sh, *.xml, SourceMods/
  inputdir/
    extract_forcings/config.json, extract_forcings/process_record.json
    grid files
    declared outputs, at their relative paths
```
`ReadCrocoDashCase` moves the state's paths onto the bundle copy, so a bundle reads exactly like a caseroot.

**`Case.fork(source, …)` runs in this order:**
1. **Pre-flight checks** [SHARE G1, G8]. Check that the source has forcings. Refuse:
   - an inputdir equal to or inside the source's;
   - the same basename on the same machine (the two cases would share `CIME_OUTPUT_ROOT/<name>`);
   - an existing target, unless `override=True` is passed explicitly.
2. **Create the case** with `Case(...)`, using the source's lazily loaded grids and its `session_id`, so file names match.
3. **Apply the user's changes**, before configure, so the CrocoDash blocks leave out keys the user set.
4. **Configure:** `configure_forcings(**source.forcing_args() | changes)`.
5. **Restore forcing files.** For each step, copy the declared files when the fingerprints computed from the two `config.json` files match and every file exists in the source; then record the step as done. Sources without a record still reuse their files [FEAS]. `plan["forcing_files"]` chooses `"matching"` (the default), `"all"` (today's wholesale copy) or `"none"`.
6. **Print a summary.**

**Duplicate** is fork from a caseroot with no changes. The plan keys stay `xml_files`, `user_nl`, `source_mods` and `xmlchanges`, and all default to yes, which matches duplicate's behaviour today, the docs and the MCP.

**What counts as the user's changes**, when a baseline exists:
- **xmlchanges:** lines in replay.sh after `replay_lines`, read by a single parser that handles `./xmlchange`, the absolute Tools path, `--id/--val` and comma lists;
- **user_nl:** lines outside CrocoDash blocks that aren't in the baseline, in every `user_nl_*` file including `_streams` and `_NNNN`;
- **SourceMods:** all of it;
- **xml files:** top-level ones the target lacks.

**What is filtered out:**
- always: variables that `configure_forcings` sets;
- on a machine change: PE layout, `JOB_*` and `PROJECT`.

Without a baseline, fork compares names against the case it has just created. That is today's behaviour, minus the throwaway reference case [CF].

### 1.5 Where the proposals disagreed, and what I chose

| Choice made | Why |
|---|---|
| `ReadCrocoDashCase` keeps its name and stays in `forcing/base.py`. | Driver imports it and `forcing/__init__` imports driver, so any home outside `forcing/` creates a cycle [FEAS]. |
| `Case` inherits from `ReadCrocoDashCase` [LTR], plus an explicit `forcing_inputs()` [CF]. | One construction path, with no delegation layer. |
| The state file stays at 1.1.0 [COD]. | Older installs require an exact version match, so a bump would make them refuse every new case [SEQ]. |
| A missing output reads as `None` and is guarded by `require_output_param` [LTR]. [COD]'s rule ("stale, so refuse") is not adopted. | [COD]'s rule refuses most real configs before any remedy exists. |
| `freq` stays inside `function_overrides`, typed through `ParamSpec` [LTR]. It does not become a new conditions input [COD/CF]. | This fixes the round trip for *every* override key without changing the file layout, and avoids recipe's conditions special case [SEQ]. |
| The POP month shift applies only to monthly cadence. [CF]'s rejection of `freq` finer than monthly is not adopted. | Rejecting would remove the day_1 use case. |
| Fingerprints substitute `$INPUTDIR` [CF] rather than strip `case_*` [LTR]. | Stripping leaves absolute runoff, CICE and WW3 paths in the fingerprint, so fork would regenerate those steps [FEAS]. |
| `clean` is a new method [COD], separate from `stale_outputs`. | The two have different triggers. |
| Writes use vCG's `xmlchange(caseroot=)`, with a 10-line local fallback [LTR]. CrocoDash does not call the CIME tools directly [CF]. | One implementation serves both repos, and the fallback takes ESMCI off the critical path. |
| Fork lives on `Case` [SEQ], not in recipe, and keeps the source's session id [CF]. | Satisfies decision 4, and file names match on restore. |
| Old bundles are refused. | A legacy reader would keep the name-diff code alive. |
| A `ParamSpec` view plus a `derived` flag. [CF]'s Input rewrite and JSON Schema are not adopted. | Scope. |
| The file-existence checks in Chl and BGCRiverNutrients warn at configure time and raise at process time. | A fork that restores the outputs doesn't need the raw input files. |

---

## 2. What happens to each existing branch and PR

| Item | Verdict | Changes |
|---|---|---|
| #312 | Merge now (P6) | It is the bottom of S1, and the config-schema-version work sits directly on it. |
| config-schema-version (uncommitted worktree) | Re-cut as **P11** | <ul><li>Keep its constants and helpers in `base.py`, and `supported=` on `check_version`.</li><li>Drop the 3 hunks aimed at code #312 deleted [OUT D].</li><li>`ReadCrocoDashCase` reads lazily through `read_config` and takes an optional `config=`, so `run_workflow` checks the version before reading state (`test_config_version.py:121-124`).</li><li>Import `check_version` by name, so tests that patch `base.case_state` can't disable it [OUT D.6].</li><li>Add migrations and the refusal of newer files.</li><li>Use `CONFIG_META_KEYS` in the registry and recipe filters.</li><li>Drop shareable's `CONFIG_FILENAME` import [OUT D.4].</li><li>The source-scan guard now covers `base.py`.</li><li>Fix `test_read_case.py:43,49` and move the reader tests to `tests/forcing/`.</li></ul> |
| #310 | Rebase onto P11 and amend (P18) | <ul><li>`configurators()` skips `CONFIG_META_KEYS` [OUT D.2].</li><li>If #297 is already in [TIME R2]: <ul><li>declare `ctx.output_path/MARBL_FE_INTERIOR_SOURCE_FILE` (an empty list when the output is `None`);</li><li>keep the writer on `ctx.output_path`;</li><li>drop #297's `is_file=True`.</li></ul></li><li>Move 16 test lines into #313, taking it from 404 to 400 or fewer.</li></ul> |
| #313 | Keep (P19) | It is test-only. CI never runs slow tests, so run its slow tests once by hand on a Casper compute node. |
| #315 | Keep and un-draft (P20) | <ul><li>It fixes fork losing `ice/` and `mapping/` *today*.</li><li>Its staleness risk already exists on main [FEAS].</li><li>P37 replaces it and P44 deletes it.</li></ul> |
| #316 | Keep (P21) | <ul><li>Keep `min_chunk_days=` and `lookback_days=` on the engine calls and in their signatures [TIME R1].</li><li>No schema bump: every reader ignores the missing `preview`.</li></ul> |
| #317 | Keep, small amendment (P22) | <ul><li>Read through `read_config`, and keep `import json` [OUT D].</li><li>`_print_forcing_files` fingerprints the config as written and then read back [OUT D.8].</li><li>Changes to the record format go in P23.</li></ul> |
| #302 | Amend (P14) | <ul><li>Drop `anchor`: it changes nothing and is wrong for POP.</li><li>Drop the per-method `time_sampling=` override, which nothing uses.</li><li>Raise `TypeError` instead of using `assert` [TIME §4].</li></ul> |
| #303 | Amend (P15) | <ul><li>Validate `freq_handling` when the decorator is applied.</li><li>Drop the rule that every dated method must accept `freq`, and the boilerplate it forced.</li><li>Process passes a method only the arguments it accepts, so dev configs that carry `freq: null` don't raise `TypeError`.</li><li>POP shifts months only for monthly cadence.</li><li>`generate_configure_forcing_args` emits `function_overrides` (the function args minus the method's defaults). This fixes bundle, duplicate and fork for cesm_mom_output [TIME §3].</li></ul> |
| #305 | Amend (P16); merge after P9 | <ul><li>P9 makes its `or` fallbacks reachable, so its claim that older config.json files fall back becomes true [TIME §2.7].</li><li>Drop the "power users can override chunk sizes" comment.</li><li>The archive-edge and wiring fixes are in P17.</li></ul> |
| #306 | Retarget to main (P5) | <ul><li>It is independent [FEAS].</li><li>A synthetic test replaces the never-run GLADE assertion as the merge gate.</li></ul> |
| #297 | Retarget to main (P10) | <ul><li>Rebase: `git rebase --onto origin/main origin/cesm-tseries-slice-time bgc-fe-interior-source`.</li><li>Re-pin rm6 to #76's merge commit, with the `submodule-bump` label.</li><li>Add `require_output_param` for the iron file.</li><li>Re-request review from mnlevy1981: the approval was on a commit that contained #302–#306.</li><li>Re-run the CR1850MARBL_JRA case.</li><li>PR body: existing MARBL cases must reconfigure, then delete `ocn/*_obc_segment.nc` (or use `--force` once P23 is in) to get clipped OBCs.</li></ul> |
| #309, #321, #322 | Merge as-is (P1–P3) | Real fixes now; #321's and #322's code is deleted in P43. |
| #295 | Review and merge (P4) | <ul><li>No proposal sequenced it [FEAS X7].</li><li>Its one overlap is in `reference.py`; resolve it on #302's side.</li><li>Its rotation fix makes existing CICE restoring files stale, so add a note on regenerating them.</li></ul> |
| #269 | Amend and split (P30) | <ul><li>Restore `ignore_degenerate=True`, with a test (Q1).</li><li>Store boundaries as JSON segment specs, so dump and fork round-trip them.</li><li>Relax the check at `recipe.py:67-71`.</li><li>Take `case_supergrid_path` from `forcing_inputs()`.</li><li>Split into an engine PR and a configurator PR (it is 559 lines today).</li><li>Land it after P17 and P21.</li></ul> |
| #311 | Amend (P31) | <ul><li>Rebase over #310 (conflict in `test_ww3.py`).</li><li>Pin an ESMCI main commit once ESMCI #50 has merged, never the draft head.</li><li>Give the new inputs defaults.</li><li>Take `case_cyclic_x` from `forcing_inputs()`.</li></ul> |
| #271 | Close | Its base, `class-merge`, isn't in main. Its ideas land in P25 and P27. |
| #307, #320, #279, #289 | Untouched | Out of scope. |

---

## 3. The PR series, in merge order

All repos are CrocoDash (CD) unless marked. IDs give one valid merge order; items within the same wave can merge in any order. The new tests are flat files with plain markers. They don't use the `slow` marker (CI skips slow tests), and they mock CIME where they don't need a real case.

### Wave 0: now, all in parallel

| ID | Repo: branch ← base | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P1–P3 | CD #309, #321, #322 ← main | As they are | 13 / 61 / 81 | Existing | — |
| P4 | CD #295 ← main | Review and merge before P14 | 351 | Its own | — |
| P5 | CD #306 → retarget main | Add a synthetic tseries-slicing test; un-draft | ~180 | `test_cesm_ocean_output.py` | — |
| P6 | CD #312 ← main | As it is | 162 | Existing | — |
| P7 | rm6 #76 | Merge (the user's own PR) | — | — | — |
| P8 | **ESMCI** `case-tools-caseroot` ← main | **Make case_tools take an explicit caseroot.** <ul><li>Keyword-only `caseroot=` on `xmlchange`, and `caseroot=`/`ninst=` on `append_user_nl`, both falling back to cvars.</li><li>Argument lists instead of `shell=True`.</li><li>stderr in the error message.</li></ul> | ~120 | 1_unit `test_case_tools.py` (tmp_path, a stub `./xmlchange`) | — |

### Wave 1: reading old configs, plus the timing stack

**Singles on main:**

| ID | Repo: branch ← base | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P9 | CD `tolerant-config-read` ← main | **Read config.json entries written by older CrocoDash.** <ul><li>Tolerant `deserialize`, `ReconfigureRequired` and `require_output_param`.</li><li>Chl, BGCRiverNutrients and Runoff call `super().validate_args()`; the file-existence check becomes a warning at configure and an error at process.</li><li>**Deletes** the dead `run_configurators(config_path)` branch.</li><li>New `docs/source/for_developers/config_compatibility.md`, with a toctree entry.</li><li>The remedy text says "re-run configure_forcings"; P28 later names the CLI command.</li></ul> | ~280 | `test_base.py` | — |
| P10 | CD #297 → main | The §2 amendments | ~235 | `test_bgc.py` | P7, P9 |
| P11 | CD `config-schema-version` ← main (just after P6) | **Version config.json and read it through one checked reader** (the §2 list) | ~350 | `tests/forcing/test_config_version.py`, `tests/forcing/test_read_case.py` | P6 |
| P12 | **MCP** `config-schema-version` | Use `read_config` and `CONFIG_META_KEYS` at `status.py:40-47`, `case.py:63-70` and `844-852`, and `resources.py:34` | ~40 | MCP tests | P11 |
| P13 | CD `config-golden-files` ← main | **Test-only.** <ul><li>Fixtures from real configs: so_bgc (MARBL), so1deg_wav (WW3), ctnp (function_args), one from before ENABLE_BUGS_BY_DEFAULT, one with #305's outputs and one with custom_segments; plus hand-written tides and chl entries.</li><li>A `config_params.json` snapshot.</li><li>`test_config_compat.py`: every fixture loads, every registered configurator is covered, the snapshot matches, and the migration chain is complete.</li></ul> | ~600 | Itself | P9, P11 |

**Stack T:** `gh stack init product-time-sampling product-freq-subsample time-aware-forcing-steps time-window-edges`

| ID | Repo: branch ← base | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P14 | #302 ← main | §2 | ~180 | `test_base_registry.py` | P4 (if ready) |
| P15 | #303 ← P14 | §2 | ~300 | Adds tests for POP daily dates and the override round trip | — |
| P16 | #305 ← P15 | §2 | ~360 | Existing | P9 |
| P17 | `time-window-edges` ← P16 | **Clamp padded windows at archive edges; count run days as end − start; prove the engines receive the chunk arguments.** <ul><li>Access methods with a fixed archive (GLORYS-RDA from 1993-01-01, the CESM tseries span) clamp the window and warn.</li><li>A wiring test checks that `process_bc` and `process_ic` pass `min_chunk_days` and `lookback_days`.</li></ul> | ~140 | `test_time_windows.py`, `test_mom6_engine.py` | — |

### Wave 2: stack S1, and the first half of stack C

**Stack S1** (P6 merged; P11 at its bottom). Set it up with:
```
git rebase --onto config-schema-version read-crocodash-case skip-finished-forcing-steps --update-refs
gh stack init config-schema-version declared-output-files output-files-reference-check shareable-restore-output-files forcing-preview-dry-run skip-finished-forcing-steps process-record-version
```

| ID | Repo: branch ← base | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P18 | #310 ← P11 | §2 | ≤400 | Existing | P10, if it merged first |
| P19 | #313 ← P18 | Adds the 16 moved lines; test-only | ~530 | Slow tests, run by hand | — |
| P20 | #315 ← P19 | Un-draft | 150 | Existing | — |
| P21 | #316 ← P20 | Rebase, keeping #305's chunk arguments | ~220 | P17's wiring test | P17 by default, but either order is safe |
| P22 | #317 ← P21 | §2 | ~357 | Existing | — |
| P23 | `process-record-version` ← P22 | **Version the record, make fingerprints portable, and make `--force` regenerate files.** <ul><li>The record format and fingerprint from §1.2.</li><li>`process_version`, including the CICE and WW3 overrides.</li><li>`clean(ctx, flag)`.</li><li>Steps that declare no files are never recorded [OUT E].</li><li>`ocn_dir` comes from the supergrid's directory, and `stale_outputs`/`clean` use `ctx.output_path` (fixes `ocnice/` cases [FEAS X5]).</li></ul> | ~320 | `test_driver.py`: <ul><li>the record behaves as a cache;</li><li>the fingerprint is equal across two inputdirs;</li><li>`--force` deletes and rewrites files;</li><li>a step without a record entry is never cleaned.</li></ul> | — |

**Stack C** opens on main now; P27 and later wait for S1 to merge. Set it up with `gh stack init user-nl-blocks-caseroot configure-without-cvars forcing-inputs case-from-caseroot configure-existing-case`.

| ID | Repo: branch ← base | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P24 | `user-nl-blocks-caseroot` ← main | **Make user_nl blocks take their caseroot.** <ul><li>`write(owner, model, groups, *, caseroot, ninst, tag=…)` is keyword-only, so existing test patches still work.</li><li>It gets its own log formatter.</li><li>New `upsert()` for edits outside the blocks.</li><li>`configure()` and atm.py pass the caseroot and ninst from `registry.case`.</li></ul> | ~290 | `test_user_nl_blocks.py` without cvars; the log assertion at `test_base.py:248` | — |
| P25 | `configure-without-cvars` ← P24 | **Write xml and user_nl changes into the case's own caseroot.** <ul><li>**Deletes** the guard (`case.py:618-628`).</li><li>session_id and grid_name are captured at creation; `is_non_local` is computed once.</li><li>Every xmlchange and `XMLConfigParam.apply` passes the caseroot.</li><li>Runoff drops `case_cime` and cvars, and reads ROF_GRID and ROF_DOMAIN_MESH from `_cime_case`.</li><li>A static test that `cvars[` appears only in creation methods.</li><li>Pins P8 (`submodule-bump` label), or falls back to a 10-line local helper that P45 later swaps out.</li></ul> | ~330 | Replaces `test_configure_forcings_rerun.py:164-177` with a two-case test (stubbed CIME tools, not slow) | P8, or the fallback |
| P26 | `forcing-inputs` ← P25 | **Explicit `Case.forcing_inputs()`**, replacing the `__dict__` scan | ~160 | Coverage test over every registered configurator | — |

### Wave 3: read-back, the parameter model, the vCG move

**The rest of stack C:**

| ID | Repo: branch ← base | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P27 | `case-from-caseroot` ← P26 | **Read a full Case back from its caseroot.** <ul><li>`Case(ReadCrocoDashCase)`, `_bind` and `from_caseroot(cesmroot=)`.</li><li>Lazy grids and `_cime_case`.</li><li>`validate_case` and `_print_forcing_files` use `configurators()`.</li><li>`expt` uses `ocn_dir`.</li></ul> | ~360 | `tests/test_case_from_caseroot.py`: a fake caseroot in tmp_path, an `ocnice/` layout, and an unversioned state file | S1 merged |
| P28 | `configure-existing-case` ← P27 | **`crocodash configure --caseroot X [--config Y] [--set k=v]`.** <ul><li>A lossless `Case.forcing_args()`, moved from recipe.</li><li>`ReconfigureRequired` now names this command.</li><li>**Deletes** `remove_configs`.</li></ul> | ~280 | `test_cli.py`; a round-trip test of `forcing_args` | P15 |

**Singles and other repos:**

| ID | Repo: branch ← base | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P29 | CD `forcing-param-specs` ← main | **Declare every forcing input once.** <ul><li>`derived=True` on start/end dates, calendar and function_args.</li><li>`ParamSpec(name, configurator, required, default, comment, is_path, choices, derived)` and `registry.param_specs(compset, config=None)`.</li><li>`function_overrides` is expanded per key: `freq` is required exactly when the product is `USER_SPECIFIED`, with notes from `resolve_time_sampling`.</li><li>WW3's constructor now requires the product name.</li><li>Fix the tides, WW3 and runoff (km) comments.</li><li>`serialize` rejects values that aren't JSON.</li><li>Unknown keyword arguments produce a warning.</li><li>The printout during case creation comes from the specs.</li></ul> | ~370 | `tests/forcing/test_param_specs.py`: every non-derived user argument is an InputParam with a comment, and every fixture re-serializes | P13, P15 |
| P30a, P30b | CD #269, split into `interior-obc-engine` and `interior-obc-new` | §2 | Each <400 | Includes an `ignore_degenerate` test | P17, P21 |
| P31 | CD #311 | §2 | ~150 | — | P18, ESMCI #50 |
| P32 | **ESMCI** `user-nl-blocks` ← main | Move P24's module unchanged (`tag=` now required) | ~390, plus a test-only overflow PR if needed | 1_unit | P24 |
| P33 | **ESMCI** `stream-years` ← main | <ul><li>Move `cdeps_streams`.</li><li>Add `plan_stream_years(cesmroot, case, component, y0, y1, padding, narrow)` and `apply_stream_years(caseroot, ninst, component, plan, tag)`.</li><li>Keep the calls to private CDEPS methods in one function.</li></ul> | ~390 | 2_integration (vCG's CI has a CESM tree) | P32 |

vCG's CI only runs on PRs into main, so ESMCI PRs are opened one after another, each against main, rather than as a gh stack. The user can self-merge there once alperaltuntas approves.

### Wave 4: sharing, the MCP, deletions

**Stack D** (on main after P28): `gh stack init case-edits case-user-changes bundle-from-case case-fork share-cli fork-prompts`

| ID | Branch | Title and scope | ~Δ | Tests | Depends on |
|---|---|---|---|---|---|
| P34 | `case-edits` | **Record what case creation wrote; let users edit cases explicitly.** <ul><li>The baseline file.</li><li>`Case.xmlchange`.</li><li>`Case.set_user_nl`, an upsert into any user_nl file.</li></ul> | ~250 | `test_case_changes.py` | P27 |
| P35 | `case-user-changes` | <ul><li>`user_changes()` and `apply_user_changes(plan)`.</li><li>One replay.sh parser.</li><li>The CrocoDash-owned and machine-specific filters.</li><li>SourceMods subdirectories are created as needed.</li></ul> | ~390; split the parser out if it runs over | Fake caseroots: with a baseline, without one, and with a machine change | — |
| P36 | `bundle-from-case` | <ul><li>`Case.bundle()` (layout in §1.4).</li><li>Reading bundle directories.</li><li>Refusing old bundles.</li><li>The CLI is not changed yet.</li></ul> | ~330 | `test_case_bundle.py` | P23 |
| P37 | `case-fork` | <ul><li>`Case.fork` and `Case(session_id=)`.</li><li>File restore gated on fingerprints.</li><li>The guards and the summary.</li><li>Duplicate is fork from a caseroot.</li><li>Port #315's two scenario tests.</li></ul> | ~390; split the guards out if it runs over | `test_case_fork.py`, not slow, using the CESMROOT case factory | — |
| P38 | `share-cli` | **CLI changes:** <ul><li>`bundle`: the old `--cesmroot`, `--machine` and `--project` flags are accepted and ignored, with a warning.</li><li>`fork --source` (with `--bundle` as an alias): cesmroot, machine and project default to the source's; `--plan` gains `forcing_files`.</li><li>`duplicate` becomes `fork --no-input`; `--bundle-dir` also bundles the source.</li></ul> **Elsewhere:** `testing.yml` is updated, and `shareable.md` becomes `sharing.md`. | ~300 | `test_cli.py`; run `testing.yml` through **workflow_dispatch** on the branch before merging | — |
| P39 | `fork-prompts` | **Prompts built from `param_specs`:** <ul><li>case fields come first, and a changed compset recomputes which configurators are active;</li><li>machine-specific paths missing on this machine are asked again;</li><li>the copy plan is confirmed;</li><li>end of input keeps the defaults.</li></ul> **Non-interactive modes:** `--write-yaml F`, `--config F`, `--no-input`. **Also:** `recipe.annotated_yaml`, `dump --annotate` and `Case.fork_params`. | ~380 | `test_fork_prompts.py` | P29 |

**Other repos:**
- **P40** (MCP `share-v2`, ~250 lines, after P39):
  - `bundle_case`, `fork_case` and `duplicate_case_tool` use the Case API;
  - a new `fork_template` tool returns the annotated YAML;
  - `list_forcing_configs` returns `param_specs`, which **deletes** `_SET_BY_CONFIGURE_FORCINGS`;
  - drop the monkeypatch at `tools/shareable.py:153`;
  - hold `CASE_BUILD_LOCK` only around case creation.
- **P41** (crocontainer `crocodash-bundle-v2`, after P38):
  - bump CrocoDash and rebuild the image;
  - then a one-line PR in CrocoDash to update the image tag in `testing.yml`;
  - `run_case.sh` does not change.

**Stack E** (after P40): `gh stack init drop-shareable-tests drop-reference-case drop-shareable`

| ID | Scope | ~Δ |
|---|---|---|
| P42 | **Test-only.** Delete `tests/shareable/`. Move `_load_FType_MOM_params` into `tests/user_nl_helpers.py` [FEAS X6]. | ~1000 |
| P43 | **Delete** `CaseBundle`, `BundleDifferences`, identify/diff and the user_nl readers, the CIME helpers, and #321's and #322's code. | ~390 |
| P44 | **Delete** the rest of the module; regenerate the API docs; fix the documentation drift [SHARE G7]. | ~380 |

**vCG consumption leaves** (on main, whenever the ESMCI PRs merge; each carries the `submodule-bump` label and regenerates `CrocoDash.forcing.rst`):

| ID | Scope | ~Δ |
|---|---|---|
| P45 | `vcg-user-nl-blocks`: <ul><li>pin P32 and switch the imports in base.py, atm.py and case.py;</li><li>**delete** `forcing/user_nl_blocks.py`;</li><li>point the tests at vCG;</li><li>keep one test that blocks written by today's code still parse.</li></ul> | ~300 |
| P46 | Test-only: remove the moved tests. | — |
| P47 | `vcg-stream-years`: pin P33; StreamYears becomes the shim; **delete** `cdeps_streams.py`. | ~330 |
| P48 | Test-only: shrink `test_atm.py` to shim tests. | — |

**How CrocoDash avoids waiting on ESMCI:**
- P24 refactors user_nl_blocks in place inside CrocoDash.
- P25 has the local-helper fallback if P8 hasn't merged.
- P45–P48 are leaves: nothing else depends on them.
- If V3 is declined because it uses private CDEPS methods, `cdeps_streams` stays in CrocoDash under the same function names, and only user_nl_blocks moves.

**What can run in parallel:**
- Wave 0 is fully parallel.
- In wave 1, Stack T runs alongside P9→P10 and P11→P12/P13.
- In wave 2, S1 runs alongside P24–P26 and P8.
- In wave 3, P27–P28 run alongside P29, P30, P31 and P32→P33.
- In wave 4, D runs, then P40/P41, then E; P45–P48 land whenever ESMCI merges.

---

## 4. How each decision is met

| Decision | PRs |
|---|---|
| 1. A Case read back from its caseroot can do everything | <ul><li>P24 and P25: writes without cvars.</li><li>P26 and P27: `from_caseroot`.</li><li>P28: configure from the CLI.</li><li>P34: xmlchange and user_nl edits.</li><li>P36: bundle.</li><li>Processing already needs no Case.</li></ul> |
| 2. Bypass vCG's global state | P8, P24 and P25: writes take the caseroot, the guard is deleted, and a static test enforces it. P27 never calls `initialize`. |
| 3. Move the CESM-case configuration into vCG | P24 (prepares in place), P32/P33 (ESMCI), P45–P48 (consume). A registered StreamYears shim stays in CrocoDash (Q2). |
| 4. shareable.py goes away | <ul><li>P18: declared files.</li><li>P22 and P23: the record.</li><li>P34 and P35: the baseline replaces the reference case.</li><li>P36–P39: the replacements.</li><li>P40: the MCP.</li><li>P42–P44: the deletion.</li></ul> |
| 5. Fork and duplicate merged; the bundle stays the transport | P36 (bundle 2.0.0), P37 (`Case.fork`; duplicate = fork from a caseroot), P38 (CLI; the flags crocontainer uses are kept), P41. |
| 6. Fork asks for each parameter both ways | <ul><li>P29: ParamSpecs, and the tests that make parameters JSON-configurable by requirement.</li><li>P39: prompts, `--write-yaml`, `--config` and `--no-input`.</li><li>P40: the MCP uses the same `Case.fork` and the same annotated YAML.</li></ul> |
| 7. config.json gets a schema_version | <ul><li>P11: version, policy and migrations.</li><li>P9: tolerant reading.</li><li>P13: golden files and snapshot.</li><li>P12: MCP.</li><li>P23: record.</li><li>P36: bundle.</li><li>P34: baseline.</li><li>The state file stays at 1.1.0.</li></ul> |
| 8. The timing stack | <ul><li>Real fixes kept: P14–P17, P5 and P10.</li><li>Cut: `anchor`, the per-method override and the boilerplate.</li><li>New fixes: POP daily dates, the archive edge, the off-by-one, the round trip.</li><li>Typed `freq`: through P29.</li></ul> |

---

## 5. How each stack is verified

- **Wave 0:** CI.
  - #295: a CICE restoring case on Derecho.
  - #306: the synthetic test.
- **P9, P11 and P13 (reading configs, versioning, golden files).** In CI, with no CESM:
  - the version matrix (unversioned, older MINOR with a migration, newer, different MAJOR) for both config.json and state;
  - tolerant reading;
  - the golden files, snapshot and migration chain.
  - By hand, before merging P9 and P11, a read-only sweep on Derecho: `resolve_process_targets(read_config(p))` over all 69 `croc_input` configs. Expect 69 of 69 to load, against 16 of 69 on main.
- **Stack T.** CI:
  - the time-window sweep;
  - the engine wiring test;
  - POP daily dates;
  - the `function_overrides` round trip;
  - the clamp, against a fake coverage.

  Real runs on Derecho:
  - a GLORYS-RDA case starting 1993-01-01;
  - a monthly CESM-POP case;
  - P10: CR1850MARBL_JRA, end to end.
- **S1.** CI, plus #313's slow tests by hand on Casper. Then a real case on Casper:
  1. process;
  2. a rerun prints `[skip]`;
  3. `--force --bc` rewrites the files (check the mtimes);
  4. `--preview`, including through the MCP once P12 is in.
- **Stack C.** Mocked tests that are not marked slow:
  - a fake caseroot;
  - `forcing_inputs()` covers every configurator;
  - two cases in one process each write to their own caseroot;
  - configure on a read-back case produces the same blocks and xmlchange arguments as on a created one.

  Real runs on Derecho:
  - read back a fresh case, an older `ocn/` case, and `streamyr_v15` (`ocnice/` layout and a deleted cesmroot). Read, preview and bundle should work; edits should fail clearly;
  - then `crocodash configure` and a 1-day run.
- **Stack D.** Unit tests:
  - the bundle layout, version and path re-rooting;
  - restore gating (boundary reorder, date change, session-id names, `"all"`/`"none"`);
  - user changes (with a baseline, without one, a machine change, `_streams` and `_NNNN` files);
  - prompts (end of input, and the round trip through `--write-yaml`).

  Before merging P38, run `testing.yml` through workflow_dispatch: those jobs only run after merge.

  Real runs on Derecho:
  - duplicate a case and run it for a day;
  - bundle on Derecho and fork inside the container.
- **vCG.** vCG's CI (1_unit, and 2_integration with CESM; these stream tests skip everywhere in CrocoDash today [VCG §1]). CrocoDash: shim tests with patched vCG, and on a DATM%JRA case `user_nl_datm_streams` must be byte-identical before and after.
- **Do old cases still load?** The golden files in CI. Plus the read-only sweep (`from_caseroot`, `configurators()`, `process --preview`, bundle to scratch) over every caseroot in `/glade/u/home/manishrv/croc_cases` and every inputdir, before merging P9, P11, P27 and P36.

---

## 6. Risks and what to do about them; out of scope

1. **ESMCI review is slow, or V3 is refused.**
   - The vCG PRs feed only leaf PRs, and P25 has a fallback.
   - Never pin a PR head that hasn't merged: #297's rm6 pin and #311's vCG pin show the hazard.
   - Each vCG pin is an ESMCI main commit, so a later pin includes every earlier merge.
2. **A rebase silently drops a fix.**
   - #316 against #305: P17's wiring test.
   - #269's `ignore_degenerate`: a test in P30.
   - #297 against #310: the iron file declaration, plus #313's output check.
3. **Tolerant reading hides real breakage.**
   - Only constructor defaults are filled in.
   - Outputs read as `None`, and `require_output_param` raises where a step needs them.
   - The snapshot forces every change into review.
4. **The external bundle contract.**
   - Keep `crocodash_case.yaml`, `fork --bundle/--plan`, and the bundle flags as ignored no-ops.
   - Run workflow_dispatch before merging P38.
   - Rebuild the image in P41.
5. **CI blind spots.** Core guarantees live in tests that aren't marked slow; the post-merge jobs run through workflow_dispatch.
6. **One-time reruns.**
   - P23 makes existing records read as `{}`, so steps rerun without cleaning; the engines skip existing files, so this is cheap.
   - After the timing stack, reconfiguring an old case changes the conditions fingerprint, so ic/bc regenerate once. That is legitimate, because the windows changed.
   - Forking an old case regenerates ic/bc for the same reason, unless `forcing_files="all"`. Put this in the release notes.
7. **Cases whose CESM tree is gone.** Read, process, bundle and fork only; this is documented.
8. **CIME is process-global.** Use one cesmroot per process; `_cime_case` checks that the CIME already imported matches.
9. **Windows where the MCP could break.** P12 lands right after P11, and P40 before P42.
10. **#297's approval and evidence don't survive the rebase.** Re-run the MARBL case.
11. **Size estimates near 400** (P25, P27, P29, P35, P37, P39). Each has a named split point.
12. **`--non-local` on read-back** skips CIME's case-git commits [CFC §6.3]. Documented.

**Out of scope:**
- **Timing work:** rm6 #77 and timestamps driven by `anchor`; time windows for WW3 and checking its `freq`; a separate IC fingerprint [TIME R5]; reaching GLOFAS subsampling.
- **Parameter model:** unifying the CICE, WW3 and conditions function-argument conventions [PARAM §7.4]; making runoff's inputs record intent [PARAM §7.7] (fork asks again for machine-missing paths instead); JSON Schema validation, or raising on unknown keyword arguments; generating gallery templates from the specs.
- **MCP:** its machine-dependent `function_name` choice.
- **CIME and vCG:** CIME `create_clone`; repairing a case's SRCROOT; making vCG's GUI import lazy.
- **Other:** structured output from `configure()`.
- **Other PRs:** #307, #320, #279, #289.

---

## 7. Questions only the user can answer

1. **#269 deletes `ignore_degenerate=True`** together with its polar-domain comment. Was that intentional for interior segments? *Default: restore it, with a test.*
2. **The StreamYears shell.** Decision 3 moves the StreamYears configurator, but vCG can't import CrocoDash's registry. The plan moves all the CDEPS logic into vCG and keeps a registered shim of about 40 lines in CrocoDash, so the `streamyears` config key, the MCP listing and the docs survive. *Default: keep the shim.*
3. **Sharing compatibility defaults.**
   - Refuse bundles made before 2.0, with a remedy, instead of writing a legacy reader.
   - Fork restores only forcing files whose fingerprints match; `--plan '{"forcing_files":"all"}'` gives today's wholesale copy.

   *Default: both as stated.*
4. **The version-bump policy.** Bump `CONFIG_SCHEMA_VERSION` only when tolerant reading would silently misread an older file, or a migration can genuinely upgrade it; otherwise rely on tolerant reading plus the reviewed snapshot. Under that rule the version stays 1.0.0 through this whole series. The alternative is a bump on every parameter change, which means about 8 serialized bumps and collisions between parallel PRs. *Default: the first rule.*

### Critical files for implementation
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/base.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/driver.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case_state.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/crocontainer/container_scripts/run_case.sh