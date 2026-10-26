# Forcing overhaul plan: land the open PRs, then reshape

All repository paths are relative to `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/`. `tip:` means `origin/skip-finished-forcing-steps`. The reports are cited as [OUT], [TIME], [SHARE], [CFC], [PARAM] and [VCG], with section numbers. They live in `/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/4dbe039a-6c11-455b-bddb-0c09a996c41b/scratchpad/reports/`.

## 0. Facts I checked that change the plan

- **Conflicts between the stacks are fewer than feared.** I simulated merges with `git merge-tree`. #312, #310, #313 and #315 do not conflict with any timing PR. There are only two real conflicts:
  - #316 against #305, in `ic.py`, `mom6.py` and `obc.py`;
  - #310 against #297, in `bgc.py` and `test_bgc.py`.
- **#297 applies cleanly to main.** Its 5 commits rebase onto main with no conflicts (simulated with `--merge-base=cesm-tseries-slice-time`).
- **#316 applies cleanly straight onto #310**, without #313 or #315.
- **rm6 PR #76 is still OPEN.** #297 pins its head commit, 12194c7.
- **#269 silently undoes a polar-domain fix.**
  - Its head removes `ignore_degenerate=True` from `_regrid_obc_chunk`.
  - That line is present at #269's merge-base (4d503756) and on main.
  - #269 also conflicts with #305 and #316 in `mom6.py` and `obc.py`.
  - #311 conflicts with #310 only in `tests/forcing/test_ww3.py`.
- **Two configurators check file existence every time they are deserialized.** `ChlConfigurator.validate_args` (chl.py:65-69, [PARAM §7.6]) and `BGCRiverNutrients.validate_args` (tip bgc.py:223-224) both do this. Because `resolve_process_targets` deserializes every entry, a missing unrelated path breaks:
  - `crocodash process --bc`;
  - bundle and fork across machines;
  - `inspect()`;
  - any golden-file test.

  Chl's override also skips `super().validate_args`.
- **Real config.json files on disk already differ from one another.** For example, `/glade/derecho/scratch/manishrv/croc_input/so_bgc` has `case_supergrid_path` in its conditions and cice inputs, written by a branch. So "unversioned = 1.0.0" names a family of layouts, not one layout. Reading old files tolerantly is required, not optional.
- **The MCP server would show `schema_version` as a forcing.** MCP `tools/status.py:47` treats every key except caseroot and conditions as an active forcing.
- **CI details.**
  - `check_submodule_bumps.yml` only runs on PRs into main.
  - The API-docs check excludes vCG, and only changes when CrocoDash modules are added or removed.
  - `gh stack` v0.1.0 is installed. `gh stack init <existing branches…>` adopts existing branches as a stack.

## 1. Target end state

### 1.1 Where things live

| Module | What it owns after the series | What is removed |
|---|---|---|
| `forcing/base.py` | <ul><li>The configurator framework.</li><li>Tolerant `deserialize`, `ReconfigureRequired` and `require_output_param`.</li><li>`ParamSpec` and `ForcingConfigRegistry.param_specs()`.</li><li>`read_config`/`write_config` and the `CONFIG_*` constants.</li><li>`WorkflowContext`.</li><li>**`ReadCrocoDashCase`**: a case on disk, which may be a caseroot **or** a bundle directory. It provides `state`, `forcing_config`, `inputdir` (relative state paths resolve against the root; `Path(root)/abs` stays absolute), `workflow_context()`, `configurators()`, `record()`, `user_changes()` and `bundle(out)`. It needs no CIME and no cvars.</li></ul> | The dead `run_configurators(config_path)` branch (tip base.py:271); cvars use |
| `case_state.py` | State file I/O, plus the one version policy `check_version(found, supported, migrations, path)`, shared by state, config and bundle. Also the state migrations. | — |
| `forcing/driver.py` | `run_workflow` with dry run and skip; the versioned record; fingerprints that don't depend on the case | — |
| `case.py` | `class Case(ReadCrocoDashCase)`: <ul><li>creation (vCG; cvars used only inside `__init__`);</li><li>`from_caseroot`;</li><li>configure, process and validate;</li><li>`xmlchange`, `append_user_nl`, `apply_user_changes`;</li><li>`restore_forcing_files`.</li></ul> | <ul><li>The CASEROOT guard (tip case.py:620-628).</li><li>The cvars reads after creation (tip:630, 671-686).</li><li>Validation that depends on `fcr`.</li></ul> |
| `recipe.py` | YAML ⇄ Case: <ul><li>load and validate;</li><li>`build_*`;</li><li>`create_case_from_yaml`;</li><li>a lossless `case_to_yaml(source)`;</li><li>`create_case_from_bundle(source, config)`;</li><li>`write_annotated_yaml`.</li></ul> | `remove_configs` |
| `cli.py` | Verbs: create, dump, **configure** (new), process, bundle, fork, duplicate (an alias of fork-from-caseroot), template. Also the interactive prompts over ParamSpecs. | — |
| `forcing/atm.py` | A ~40-line registered `StreamYears` shim, so the `"streamyears"` config key and the MCP listing survive [VCG op.2] | The CDEPS logic |
| `shareable.py`, `forcing/user_nl_blocks.py`, `forcing/cdeps_streams.py` | — | Deleted (the last two move to vCG) |
| visualCaseGen | <ul><li>`case_tools.xmlchange/append_user_nl(..., caseroot=None, ninst=None)`.</li><li>`visualCaseGen/user_nl_blocks.py`, with a `tag=` parameter.</li><li>`visualCaseGen/cdeps_streams.py` and `stream_years.py` (`plan_stream_years`, `apply_stream_years`).</li></ul> | — |

### 1.2 Files on disk, their versions and compatibility rules

**One policy for every versioned file:**
- Same MAJOR.MINOR: accepted, whatever the PATCH.
- A newer file: refused, with "upgrade CrocoDash".
- An older MAJOR: refused.
- An older MINOR: `migrations[(M, m)]` run one step at a time. Each step either upgrades the dict or raises `ReconfigureRequired(configurator, "crocodash configure --caseroot …")`.

| File | Version | Rule |
|---|---|---|
| `<caseroot>/_crocodash_state.json` | 1.1.0 → **1.2.0** (C3 adds `esmf_mesh_path` and `baseline`) | <ul><li>The 1.1→1.2 migration rebuilds the mesh path from `ESMF_mesh_{grid}_{session}.nc` in the supergrid directory (tip case.py:401) and sets `baseline=None`.</li><li>Unversioned: accepted with a warning, as today.</li></ul> |
| `<inputdir>/extract_forcings/config.json` | unversioned ≡ 1.0.0; written as 1.0.0 | Entries are read tolerantly: <ul><li>a missing input with a constructor default gets that default;</li><li>a missing input without a default raises `ReconfigureRequired`;</li><li>a missing output reads as `None`, and `require_output_param` raises an error that says what to do;</li><li>extra keys are ignored.</li></ul> Bump MINOR (and add a migration) only for renames, new required inputs, or changed meaning. |
| `<inputdir>/extract_forcings/process_record.json` | **1.0.0** (A9): `{schema_version, steps: {flag: {fingerprint, files}}}` | Treated as a cache: any mismatch or unreadable file reads as `{}`. The fingerprint is: <ul><li>the configurator's own entry plus its `depends_on` entries, with `case_*` inputs stripped;</li><li>plus a per-class `process_version`.</li></ul> |
| `<bundle>/bundle.json` | **2.0.0** | <ul><li>Uses the policy.</li><li>It carries `user_changes` and the source (caseroot, machine).</li><li>Old bundles (`crocodash_case.yaml` + `non_standard_case_info.json`) are refused, with "re-bundle, or `crocodash create` from its yaml".</li></ul> |
| Creation baseline (in state 1.2.0) | `{replay_lines, user_nl: {file: text}, xml_files: […]}` | If it is absent (cases from before 1.2), the bundle adds `raw/user_nl_*` and `raw/replay.sh` and prints a warning. |
| user_nl block marker | The text is frozen: `! >>> CrocoDash configure_forcings: <owner> [sha:…]` | vCG takes `tag=`, and CrocoDash always passes today's exact text [VCG op.3]. |

**How future version changes get checked (T1):**
- Frozen golden config files must load.
- A committed snapshot of declared parameters (one line per configurator) must match, so every change to the parameters is a reviewed diff.
- The migration chain must be complete.

### 1.3 The read-back Case

```python
case = Case.from_caseroot(caseroot, *, cesmroot=None)  # never creates or deletes anything; no create_newcase or case.setup
case.configure_forcings(...); case.process_forcings(...)
case.xmlchange("STOP_N", 30); case.append_user_nl("mom", [("DT", 900)])
case.bundle(out_dir)            # inherited from ReadCrocoDashCase
```

- **One construction path.** `Case.__init__` ends with `self._bind(caseroot)` (create, then read back). `from_caseroot` is `cls.__new__` followed by `_bind`. Created and read-back cases therefore can't drift apart [CFC §7A].
- **Loaded eagerly** (JSON only, milliseconds): the checked or migrated state and config, set as plain attributes:
  - cesmroot (an override wins), caseroot, inputdir, compset_lname, machine, project, ninst;
  - atm/rof grid names, ntasks_ocn, job_*;
  - session_id, grid_name, supergrid/topo/vgrid/esmf_mesh paths;
  - `override=False` [CFC §6.6];
  - `is_non_local=True`: read-back writes always pass `--non-local`, as shareable did;
  - extract_forcings_path;
  - `_configure_forcings_called` = whether config.json exists.

  `ocn_dir` becomes the supergrid's directory rather than `inputdir/"ocn"`, because older cases use `ocnice/` [CFC §6.5].
- **Loaded lazily** (`functools.cached_property`):
  - `ocn_grid`, `ocn_topo` and `ocn_vgrid`, built from the state paths. The imports stay at the top of the file.
  - `_cime_case`: CIME's `Case(read_only=True, non_local=True)` from `<cesmroot>/cime`. Its import is the one runtime import, because the path is only known at runtime.
  - Only StreamYears, Runoff and `expt` touch `_cime_case`.
  - `cime` is `None`.
- **How `case_*` inputs are provided.** The mechanism is unchanged: the registry scans public attributes (tip base.py:168). `_bind` makes sure every one that is consumed (cesmroot, inputdir, compset_lname, session_id, grid_name, esmf_mesh_path, supergrid_path) is a plain attribute [CFC §6.7].
  - Runoff drops `case_cime` and `cvars["CUSTOM_ROF_GRID"]` (tip runoff.py:53-73).
  - Runoff instead reads ROF_GRID and ROF_DOMAIN_MESH from `registry.case._cime_case`.
- **The `cesmroot` override** affects only what CrocoDash itself reads: the CDEPS XML for StreamYears and the CIME import path. CIME writes still need the case's own SRCROOT. A dead SRCROOT breaks configure and xmlchange, but not process or bundle [CFC §6.4].
- **How writes find the caseroot: they are always given it.**
  - vCG `xmlchange(..., caseroot=self.caseroot)`;
  - `user_nl_blocks.write(caseroot, ninst, …)`;
  - configurators use `self.registry.case`.

  Nothing reads cvars after creation. That removes the "configure writes into the last case created" bug, its guard, and the reason the MCP holds a build lock around configure [CFC §3, §6.1].

## 2. What happens to each existing PR

| PR | Verdict | Change |
|---|---|---|
| **#312** | Keep as-is; merge first | — |
| **config-schema-version** (uncommitted worktree) | Re-cut as **A2** on #312 | <ul><li>`ReadCrocoDashCase` reads through `read_config` and takes an optional `config=`, so `run_workflow` reads the file once and checks it before reading state (as test_config_version.py:121-124 requires).</li><li>base.py imports `check_version` directly, so tests that patch `base.case_state` can't mock it away [OUT D.6].</li><li>Add the older-MINOR migration policy.</li><li>Drop shareable's explicit `CONFIG_FILENAME` import [OUT D.4].</li><li>Fix test_read_case.py:43 and :49.</li><li>The source-scan guard stops exempting base.py.</li><li>Delete the dead `run_configurators` branch.</li></ul> |
| **#310** | Amend while rebasing | <ul><li>`configurators()` skips `CONFIG_META_KEYS` [OUT D.2].</li><li>If #297 merged first: the iron `output_files` declares `MARBL_FE_INTERIOR_SOURCE_FILE` through `require_output_param`; drop `is_file=True` from that param; the writer uses `ctx.output_path` [TIME §2.3].</li><li>Extend T1's test to call `output_files(ctx)`.</li></ul> |
| **#313** | Keep; un-draft | — |
| **#315** | Keep as an interim fix; un-draft | <ul><li>It fixes fork losing `ice/` and `mapping/`.</li><li>The boundary-reorder risk already exists on main, which copies `ocn/` wholesale. D2 removes it.</li></ul> |
| **#316** | Keep; rebase over #305 | Delete the preview branches, but **keep** `min_chunk_days=`/`lookback_days=` on the real engine calls and in the `obc.py`/`ic.py` signatures [TIME R1]. #305's guard test enforces this. |
| **#317** | Keep; rebase | <ul><li>Use `read_config`, and keep `import json` [OUT D].</li><li>`_print_forcing_files` uses the config as written and then read back [OUT D.8].</li><li>Format changes go in follow-up A9.</li></ul> |
| **#302** | Amend before merging | <ul><li>Drop `anchor`: it changes nothing, and is wrong for POP.</li><li>Drop the per-method `time_sampling=` override, which no production code uses [TIME §4].</li><li>This shrinks `information.time_sampling` before it enters fingerprints [TIME R6].</li></ul> |
| **#303** | Amend | <ul><li>Validate `freq_handling` when the decorator is applied.</li><li>Drop the rule that every dated method must accept `freq`, along with the `freq=None` and `resolve_time_sampling` boilerplate on methods without freq_handling. `function_args` only carries keys the method has, so `freq` never reaches them.</li><li>`generate_configure_forcing_args` emits `function_overrides` = `function_args` minus the method's defaults. This fixes the hard failures in bundle, duplicate and fork for cesm_mom_output [TIME §3].</li></ul> |
| **#305** | Amend; merge only after T0 | <ul><li>Clamp the padded fetch window at a product's declared first/last date (the GLORYS RDA archive starts 1993-01-01).</li><li>Count run days as end − start.</li><li>Add a test that `process_bc`/`process_ic` pass `min_chunk_days` and `lookback_days` to the engines.</li></ul> |
| **#306** | Amend; un-draft | <ul><li>Apply `apply_month_shift` only to monthly sampling (the POP `freq="D"` bug, cesm_ocean_output.py:160/807).</li><li>Add a synthetic test, so it no longer relies on the GLADE assertion that has never run.</li></ul> |
| **#297** | Take it out of the stack; re-target to main | <ul><li>Wait for rm6 #76 to merge, then re-pin to its merge commit and add the `submodule-bump` label.</li><li>Re-request mnlevy1981's review, because the rebase drops the approved commit.</li><li>Its documented break stands: MARBL config.json files from before #297 need reconfiguring.</li></ul> |
| **#321, #322** | Merge as-is | Fixes for the interim. Their code dies with shareable in D4. |
| #269 (outside the series) | Amend before merging | <ul><li>Restore `ignore_degenerate=True`, with a test.</li><li>Accept JSON segment specs (dicts) in `boundaries` and emit them from `case_to_yaml`, so boundaries can still be set from JSON.</li><li>Rebase after #305 and #316.</li><li>Give its new input a constructor default.</li></ul> |
| #311 (outside the series) | Amend | <ul><li>Rebase over #310.</li><li>Give the new WW3/CICE inputs constructor defaults.</li><li>Pin an ESMCI **main** commit after ESMCI #50 merges, never the draft head.</li><li>Its visualCaseGen pin must be serialized with the V stack's pins.</li></ul> |
| #309 | Merge any time | It only affects case creation. |
| #271 | Close | <ul><li>Its base, `class-merge`, isn't in main, and the PR is CONFLICTING.</li><li>Its two ideas (session_id from state, resolving is_non_local once) are delivered by C1 and C2.</li></ul> |

## 3. Ordered PR series

All PRs are in CrocoDash unless marked. Sizes count changed lines. Every PR keeps additions under 400, except where noted. The new test files are flat, using the plain `slow` marker.

### S1 "forcing-records": the existing output stack with A2 inserted

Setup:
1. Branch A2 off `read-crocodash-case`.
2. Run `git rebase --update-refs` on the chain onto it.
3. Run `gh stack init read-crocodash-case config-schema-version declared-output-files output-files-reference-check shareable-restore-output-files forcing-preview-dry-run skip-finished-forcing-steps process-record-version`.

| # | Branch ← base | Title / scope | Δ | Tests | Unblocks |
|---|---|---|---|---|---|
| 1 | #312 `read-crocodash-case` ← main | as-is | 162 | existing | everything below |
| 2 | **A2** `config-schema-version` ← #312 | "Version config.json and read it through one checked reader." <ul><li>Constants and `read_config`/`write_config` (base.py).</li><li>The policy with migrations (case_state.py).</li><li>Every reader goes through it: case.py, cli.py, recipe.py, driver.py, `ReadCrocoDashCase`.</li><li>Deletes the dead branch.</li></ul> | ~350 (120 code) | `tests/forcing/test_config_version.py`, plus newer- and older-MINOR cases | #310 rebase, MCP M1 |
| 3 | #310 ← A2 | amended (§2) | ~420 → +15 | T1 extended | #313–#317 |
| 4–7 | #313, #315, #316, #317 | §2 | as now | — | — |
| 8 | **A9** `process-record-version` ← #317 | "Version process_record.json and make step fingerprints case-independent." <ul><li>driver.py: record nested under `steps`; any mismatch reads as `{}`.</li><li>`process_fingerprint` strips `case_*` and adds `process_version`, including the CICE and WW3 overrides.</li><li>Steps that declare no files are never recorded [OUT E].</li></ul> | ~130 | `test_driver.py` | D2 |

### S2 "tolerant-config": on main, parallel to S1 from day one

| # | Branch ← base | Title / scope | Δ | Tests | Unblocks |
|---|---|---|---|---|---|
| 1 | **T0** `tolerant-config-read` ← main | "Read config.json entries written by older CrocoDash." <ul><li>`deserialize`: defaults, `None`, or `ReconfigureRequired`.</li><li>`require_output_param`.</li><li>Move the file-existence checks for Chl and BGCRiverNutrients into `configure()`, and call `super().validate_args()`.</li><li>New `docs/source/for_developers/config_compatibility.md`. A new file avoids clashing with #313's and #317's edits to `adding_forcing_configurations.md`.</li></ul> | ~220 | `test_base.py` | #305, #269, #311 |
| 2 | **T1** `config-golden-files` ← T0 | **Test-only.** <ul><li>`tests/forcing/data/config_1.0.0_marbl.json` (from so_bgc) and `…_wav.json` (from so1deg_wav), plus hand-written tides and chl entries.</li><li>The param snapshot `config_params.json`.</li><li>`test_config_compat.py`: every fixture entry deserializes, or raises `ReconfigureRequired` if listed as a known break (pre-#297 iron); every registered configurator appears in a fixture; the snapshot matches; the migration chain is complete.</li></ul> | ~550 | itself | decision 7's checks, P1 |

### S3 "time-sampling" and the single PRs

- **S3:** `gh stack init product-time-sampling product-freq-subsample time-aware-forcing-steps cesm-tseries-slice-time`.
  - #302 ← main.
  - #303 ← #302.
  - #305 ← #303. Gate: T0 is merged.
  - #306 ← #305.

  Each carries its §2 amendment (each amendment is ±40).
- **#297:** run `git rebase --onto origin/main origin/cesm-tseries-slice-time bgc-fe-interior-source`, then `gh pr edit 297 --base main`.
- **#321, #322, #309:** merge as they are.

### S4 "read-back-case" and "share-v2"

This stack starts once S1 and S3 have merged, because C1 rewrites configure_forcings lines that #303 and #317 also touch. It is one linear stack: C1 → C2 → C4 → C3 → D1 → D2 → D3 → D4.

| # | Branch | Title / scope | Δ | Tests | Depends / unblocks |
|---|---|---|---|---|---|
| C1 | `configure-without-cvars` ← main | "Write user_nl and xml changes into the case's own caseroot." <ul><li>Capture session_id and grid_name at creation.</li><li>**Delete the guard.</li><li>xmlchanges pass `caseroot` and `self.is_non_local`.</li><li>base.py `configure` and `XMLConfigParam.apply` take caseroot and ninst from `registry.case`.</li><li>`user_nl_blocks.write(caseroot, ninst, …)` gets its own log formatter.</li><li>Update atm.py; runoff.py drops cvars and `case_cime`.</li><li>Pin V1, with the `submodule-bump` label.</li></ul> | ~230 | <ul><li>`test_user_nl_blocks.py` without cvars.</li><li>Replace `test_refuses_to_write_into_a_case_created_later` (test_configure_forcings_rerun.py:164) with a slow test: "configure the first case after creating a second".</li><li>Update the log assertion at test_base.py:248.</li></ul> | Needs V1. Unblocks C2, V2. |
| C2 | `case-from-caseroot` ← C1 | "Read a full Case back from its caseroot." <ul><li>`Case(ReadCrocoDashCase)`, `_bind`, `from_caseroot(cesmroot=)`.</li><li>The lazy properties.</li><li>`validate_case` and `_print_forcing_files` use `configurators()`.</li><li>`ocn_dir` from the supergrid's directory.</li></ul> | ~330 | `tests/test_case_from_caseroot.py`: a fake caseroot in tmp_path, plus a slow create → read back → configure → `--preview` | C4, C3 |
| C4 | `configure-existing-case` ← C2 | "`crocodash configure`: rerun configure_forcings on an existing case." <ul><li>`--config forcings.yaml` and `--set k=v`.</li><li>`Case.forcing_args()`, a lossless `generate_configure_forcing_args`.</li><li>The `ReconfigureRequired` remedy points here.</li></ul> | ~160 | `tests/test_cli.py` | Remedy for any schema bump; D2 failure recovery |
| C3 | `case-change-tracking` ← C4 | "Record what case creation wrote; derive the user's changes from it." <ul><li>State 1.2.0 with its migration; the baseline is captured at the end of `__init__`.</li><li>`ReadCrocoDashCase.user_changes()`: <ul><li>xmlchanges in replay.sh after the baseline, minus the variables CrocoDash owns (the four run-date variables plus the `XMLConfigParam` names in config.json);</li><li>user_nl lines outside CrocoDash blocks that aren't in the baseline, including `_streams` and `_NNNN` files;</li><li>SourceMods;</li><li>new top-level xml files.</li></ul></li><li>`Case.xmlchange`, `append_user_nl`, `apply_user_changes`.</li></ul> | ~330 | `tests/test_case_changes.py` | D1, D2. Replaces the reference-case diff [SHARE D]. |
| D1 | `bundle-from-case` ← C3 | "Bundle a case from its files." <ul><li>`ReadCrocoDashCase.bundle(out)`: `bundle.json`, state with relative paths, config, record, source grid files, declared files at their inputdir-relative paths, SourceMods and xml files (or `raw/`).</li><li>The CLI `bundle` drops `--cesmroot`, `--machine` and `--project`.</li></ul> | ~330 | `tests/test_case_bundle.py` | D2, M2 |
| D2 | `fork-from-bundle` ← D1 | "Fork and duplicate through one path." `recipe.create_case_from_bundle(source, config)` runs: <ol><li>`Case()`;</li><li>`apply_user_changes`;</li><li>`configure_forcings`;</li><li>`Case.restore_forcing_files(source)`: copy a step's declared files only when the source's recorded fingerprint equals the new one, then record the step as done;</li><li>a summary.</li></ol> Also: <ul><li>`duplicate` passes the source **caseroot** as the source, so nothing is copied twice.</li><li>Never pass `override=True` implicitly; refuse when the new inputdir equals the source's [SHARE G1].</li><li>Check for `forcings` before calling `Case()` [SHARE G8].</li><li>The CLI is rewired.</li></ul> | ~370 | `tests/test_case_fork.py`: fingerprints match or differ, plus a slow end-to-end duplicate | D3 |
| D3 | `fork-prompts` ← D2 (P1 must be in main) | "Ask for each case and forcing input, interactively or through an annotated YAML." <ul><li>Walk the ParamSpecs: case fields first, so a changed compset recomputes the forcing set.</li><li>Ask again for anything machine-specific: cesmroot, machine, project, caseroot, inputdir, and `InputFileParam`s whose path is missing here.</li><li>The user-change categories default to **yes**.</li><li>`--write-yaml F` writes the annotated YAML and stops; `--config F` forks from it.</li><li>The `ask_*` helpers move into cli.py.</li></ul> | ~350 | `tests/test_fork_prompts.py` | M2 |
| D4 | `remove-shareable` ← D3, after M2 merges | Delete `shareable.py` (762 lines) and `tests/shareable/` (949 lines); rewrite `shareable.md`; regenerate the API docs. | deletion-only, over the 400-line cap by design | — | — |

### S5 "forcing-param-specs": one PR on main, in parallel with C1–C3

**P1 `forcing-param-specs`**, about 340 lines.
- `ParamSpec(path, default, required, comment, owner, machine_specific, choices)` and `ForcingConfigRegistry.param_specs(compset, product_name, function_name)`.
- Each configurator declares `derived_args`, so start/end dates, calendar, function_args and `compset` stop showing up as user arguments [PARAM §7.1].
- **"Typed freq" without moving where it is stored:** `function_overrides` is expanded per key from `get_function_default_args`. `freq` is required exactly when the product is `USER_SPECIFIED`, and its notes come from `resolve_time_sampling`.
- WW3's `ww3_obc_product_name` becomes required by the constructor, matching what `validate_args` already demands.
- Fix the wrong tides/WW3 comment examples.
- `make_serializable` raises on values that aren't JSON.
- The printout in `Case.__init__` (case.py:236-248) uses the specs.
- **Test** (`tests/forcing/test_param_specs.py`), which is what makes params "JSON-configurable by requirement":
  - every non-derived user argument is a declared `InputParam` with a comment;
  - every T1 fixture entry re-serializes to JSON.

### S6: ESMCI/visualCaseGen

Base these on ESMCI main c553683, not the standalone checkout's `bring_in_m6f_new`. `gh stack` needs push access to ESMCI; otherwise open them one after another from a fork.

| # | Branch | Scope | Δ | Tests |
|---|---|---|---|---|
| V1 | `case-tools-caseroot` | <ul><li>Keyword-only `caseroot=None` on `xmlchange`, and `caseroot=None, ninst=None` on `append_user_nl`. Both fall back to cvars, so every positional `CaseCreator` call stays valid.</li><li>Pass subprocess arguments as a list, with no `shell=True`.</li><li>Include stderr in the error [VCG §4, op.7].</li></ul> Open it **day one**. | ~120 | `tests/1_unit/test_case_tools.py` (tmp_path and a stub `./xmlchange`) |
| V2 | `user-nl-blocks` ← V1, opened after C1 merges | Move the already caseroot-explicit module verbatim, with `tag=` required | ~390 | `tests/1_unit` |
| V3 | `cdeps-stream-years` ← V2 | Move `cdeps_streams.py`, and add `stream_years.py` (`plan_stream_years(cesmroot, cime_case, component, start_year, end_year, padding, narrow)` and `apply_stream_years(caseroot, ninst, component, plan, tag)`) | ~390 | `tests/2_integration`. vCG's CI has a CESM tree; CrocoDash's `test_atm.py` currently skips everywhere [VCG §1]. |

### S7 "vcg-consume": on main, when V2/V3 merge

Rebasing costs only a few import lines.
- **VB2 `vcg-user-nl-blocks`:**
  - pin V2 and import `visualCaseGen.user_nl_blocks` with `tag="CrocoDash configure_forcings"`;
  - delete the CrocoDash module and its test, but keep one test that a block written by today's code still parses;
  - regenerate the API docs; add the `submodule-bump` label.

  About +30/−450; it is mostly a move.
- **VB3 `vcg-stream-years` ← VB2:**
  - pin V3;
  - StreamYears becomes a shim with the same name, inputs and outputs, so config.json needs no bump;
  - delete `cdeps_streams.py`;
  - regenerate the API docs.

  About +45/−420.

### MCP (CROCODILE-CESM/MCP_CrocoDash)

- **M1 `config-schema-version`, right after A2:**
  - Read config.json through `read_config`/`CONFIG_META_KEYS` in status.py:47, case.py:63-70 and 844-852, and resources.py:34.
- **M2 `share-v2`, after D3 and before D4:**
  - `bundle_case` uses `ReadCrocoDashCase.bundle`;
  - fork and duplicate use `create_case_from_bundle` and `write_annotated_yaml`, which removes the `_guide_yaml_review` monkeypatch at tools/shareable.py:153;
  - `list_forcing_configs` returns `param_specs`;
  - `CASE_BUILD_LOCK` is held only around case creation.

### Order and what can run in parallel

| Wave | What happens |
|---|---|
| 0 (now, all in parallel) | <ul><li>Merge #312, #321, #322, #309.</li><li>Open A2, T0, T1 and V1.</li><li>Amend #302, #303 and #306.</li><li>Re-target #297.</li></ul> |
| 1 | <ul><li>Merge in order: T0, #302, #303, #305, #306.</li><li>Merge A2, then M1.</li><li>Merge T1.</li><li>Merge #297 once rm6 #76 has merged.</li></ul> |
| 2 | Rebase S1 onto main, then merge #310, #313, #315, #316, #317 and A9. Merge A9 the same day as #317. |
| 3 | <ul><li>Run S4 up to C3 (C1 needs V1). P1 runs in parallel.</li><li>V2 follows C1; V3 follows V2. S7 lands whenever those merge.</li><li>If C1 is ready before V1 merges, give C1 a 10-line local `xmlchange(caseroot)` helper and swap it out in VB2.</li></ul> |
| 4 | D1 → D2 → D3 → M2 → D4. #269 and #311 can land any time after Wave 2, with their amendments. |

## 4. How each decision is met

| Decision | Delivered by |
|---|---|
| 1. A read-back Case does everything | C1 (writes without cvars), C2 (`from_caseroot`), C4 (configure on an existing case), C3 (`xmlchange` and `append_user_nl`), D1 (`bundle` is inherited). `create_newcase` and `case.setup` never run. |
| 2. Bypass vCG's global state | V1 + C1: every write takes the caseroot explicitly; the guard is deleted; `from_caseroot` never calls `initialize()`. |
| 3. CESM case configuration moves into vCG | C1 refactors in place, V2 and V3 move the code, VB2 and VB3 consume it. The registered StreamYears shim stays, so the config key and the MCP listing don't change. |
| 4. shareable.py goes away | <ul><li>#310: declared files.</li><li>#317 and A9: the record.</li><li>C3: the baseline replaces the throwaway reference case, so #321/#322's code dies too.</li><li>D1–D3: the replacement.</li><li>D4: the deletion.</li></ul> |
| 5. Fork and duplicate merge | D2: one function. `ReadCrocoDashCase` reads caseroots and bundles alike, so duplicate is fork with the caseroot as the source and no edits. `bundle.json` 2.0.0 stays the transport format. |
| 6. Prompts both ways | P1 (ParamSpecs and the JSON-configurable test), D3 (prompts, `--write-yaml`/`--config`), M2 (the MCP uses the same writer and reader). |
| 7. schema_version | <ul><li>A2: version and policy.</li><li>T0: tolerant reading.</li><li>T1: the checks that future changes must pass.</li><li>A9: the record.</li><li>C3: state 1.2 with its migration.</li><li>D1: bundle 2.0.</li></ul> |
| 8. The timing stack | <ul><li>The §2 amendments keep the real fixes: the empty REGRID chunk for monthly data, the IC lookback, window padding, tseries slicing, and BGC.</li><li>They cut `anchor`, the per-method override and the boilerplate.</li><li>They fix the archive-edge, POP-daily and round-trip bugs.</li><li>Typed `freq` comes through P1.</li></ul> |

## 5. Top risks and what to do about them

1. **ESMCI review is slow or rejects something.**
   - V1 is tiny and generic. If it isn't merged in time, C1 uses the local-helper fallback.
   - If V3 is declined because it uses private CDEPS methods, `cdeps_streams` stays in CrocoDash behind the same function names. Only user_nl_blocks moves.
   - Never pin a PR head that hasn't merged. #297's rm6 pin and #311's vCG pin show the hazard.
2. **A conflict resolution silently drops a fix** (#316 against #305, and #269's `ignore_degenerate`).
   - #305's engine-arguments test and an `ignore_degenerate` test in #269 catch it.
3. **Tolerant reading hides real breakage.**
   - Only inputs with defaults are filled in.
   - Outputs read as `None`, but `require_output_param` raises an actionable error.
   - The golden files and the snapshot force every change into review.
4. **Some forcing steps rerun once.**
   - A9's new fingerprints, and any change to `information`, invalidate records.
   - Records are a cache, so the steps simply rerun.
   - Land #302's amendment before #317, and A9 the same day as #317.
5. **Cases from before state 1.2 have no baseline.**
   - Their user changes go into the bundle's `raw/` folder and must be applied by hand.
   - That is a conscious trade against building a full throwaway case on every bundle. Document it.
6. **Session IDs in file names mean fork can't reuse every file.**
   - The new case gets a new session ID, so files named with it (BGC iron, river nutrients, the runoff map) are regenerated, not copied.
   - All three are cheap except the runoff map.
7. **CIME is shared across the whole process.**
   - Use one cesmroot per process. `_cime_case` checks that the CIME already imported has the same root.
8. **#297's approval and end-to-end evidence don't survive the rebase.**
   - The approval was on a commit that included #302–#306. Re-run the CR1850MARBL_JRA case after rebasing onto main.
9. **The MCP breaks between merges.** M1 must land with A2, and M2 before D4.
10. **The fork default flips.** Copying user changes now defaults to yes. Call this out in the docs.

**Explicitly out of scope:**
- rm6 #77, and making `anchor` drive timestamp corrections.
- Applying time windows and chunk settings to WW3.
- Unifying how CICE and WW3 pass product-function arguments.
- Keeping session_id across a fork.
- CIME `create_clone`.
- Repairing cases whose SRCROOT moved.
- A shared constant for the `extract_forcings` path (built by hand in 10 places).
- Making `configure()` return structured output instead of printing.
- Reaching GLOFAS subsampling.
- #271, #307 and #320.
- Generating crocogallery templates from ParamSpecs.

### Critical files for implementation
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/base.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/driver.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case_state.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/recipe.py