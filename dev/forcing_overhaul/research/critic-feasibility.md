# Feasibility review of the three forcing-overhaul proposals

**Conventions.** `CD` means `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash`. `tip` means `origin/skip-finished-forcing-steps` and `T` means `origin/bgc-fe-interior-source`; other branch refs are named in full. Conflict checks used `git merge-tree` in its old three-argument mode, which writes nothing to the repo.

## 0. Cross-cutting facts I verified (cited below as X1–X9)

- **X1 — the bundle contract has three consumers none of the plans fully protect.**
  - `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/crocontainer/container_scripts/run_case.sh:24` detects a bundle only by `crocodash_case.yaml`.
  - Lines 25-32 of the same script run `crocodash fork --bundle --caseroot --inputdir --cesmroot --machine --project --plan '{xml_files,user_nl,source_mods,xmlchanges}'`.
  - The container pins its own CrocoDash as a submodule at 2f28301c.
  - `/glade/u/home/manishrv/documents/croc/dev/MCP_cesm_runner/cesm_runner_mcp/tools/container.py:399` also requires `crocodash_case.yaml`.
  - CD `main:.github/workflows/testing.yml:145-155` runs `crocodash bundle --cesmroot --machine --project`.
  - `testing.yml:163-239` runs the image `sha-acfa305` through `run_case.sh`.
  - Both CI jobs run only on pushes to main or workflow_dispatch, so any breakage appears after merge.
- **X2 — `--force` and a `process_version` bump regenerate nothing for ic/bc/runoff**, because the engines skip finished files:
  - `tip:CrocoDash/forcing/obc.py:654-661` (`_merge_boundary` returns early if the file exists);
  - `tip:CrocoDash/forcing/mom6.py:335-344` (the IC `_all_written` check);
  - `T:CrocoDash/forcing/mom6.py:196` (`_split_bgc_tracers_into_files` skips when all its files exist);
  - `tip:CrocoDash/forcing/runoff.py:161-175` (an existing map is reused).

  So #297's clipping (commit 37cea8d3) would never reach OBC files that already exist.
- **X3 — CI never runs `slow` tests.** `main:testing.yml:119` has no `--runslow`, and `tests/conftest.py` skips slow tests by default.
- **X4 — on-disk config.json layouts.** I surveyed 69 files under `/glade/derecho/scratch/manishrv/croc_input/*/extract_forcings/config.json`:
  - none has a `schema_version`;
  - the conditions entry has at least 4 output layouts: 50 lack `ENABLE_BUGS_BY_DEFAULT`, 6 carry the timing-stack outputs, 2 carry `custom_segments`;
  - 66 still carry `preview`;
  - in `so_bgc`, the runoff outputs are absolute paths under the inputdir.
- **X5 — `ocn/` is still hard-coded** at `tip:CrocoDash/forcing/mom6.py:763` (`stale_outputs`) and `tip:CrocoDash/case.py:792` (`expt`). For old `ocnice/` cases, `stale_outputs` then finds nothing to delete.
- **X6 — after #321, a test helper imports from shareable.** `tests/user_nl_helpers.mom_parser` imports `CrocoDash.shareable._load_FType_MOM_params`. Its callers are `tests/forcing/test_user_nl_blocks.py:11` and `tests/test_configure_forcings_rerun.py:13`.
- **X7 — #295 is unsequenced.** It is open, by amrhein, and touches `cice.py`, `cice_output.py`, `reference.py` and tests. Those overlap #302, #303, #310 and #317. No plan mentions it.
- **X8 — CI gating details.**
  - The vCG CI (`ci-tests.yml:6-9`) runs only on PRs into main or ci, so stacked ESMCI PRs get no CI until they are retargeted.
  - `check_submodule_bumps.yml` runs only on PRs into main.
  - The API-docs job (`deploy_sphinx_docs.yml:26-52`) changes only when a CrocoDash module is added or removed.
- **X9 — ESMCI access.** The user has maintain and push permission on ESMCI/visualCaseGen (`gh api` permissions). PRs #37, #41, #45 and #46 were each merged by the user after an approval from alperaltuntas.

---

## Proposal 1: land-then-reshape

**Verified**
- **Conflict map (trivial merge-tree scan):**
  - #316 vs #305 conflicts in `ic.py` (2), `mom6.py` (3) and `obc.py` (2).
  - #310 vs #297 conflicts in `bgc.py` (2) and `test_bgc.py` (1).
  - #312, #313 and #315 are clean against every timing PR; #310 is clean against all of them except #297.
- **#297 applies cleanly to main.** `mom6.py` is changed on both sides but merges without conflict markers; the PR is 221 lines.
- **#316 and #317 apply without #315.**
- **rm6 #76 is still OPEN at 12194c7**, the commit #297 pins.
- **#269 removes `ignore_degenerate=True` and its comment.** The line is present at `4d503756:CrocoDash/forcing/mom6.py:144` and at `main:CrocoDash/forcing/mom6.py:144`. This is a real regression and only this proposal caught it.
- **#269 conflicts with #305 and #316** in `mom6.py` and `obc.py`; **#311 conflicts with #310** only in `test_ww3.py`.
- **File-existence checks during deserialize:**
  - Chl checks at `tip:chl.py:65-69` and skips `super()`; BGCRiverNutrients checks at `tip:bgc.py:223-227`.
  - `resolve_process_targets` deserializes every entry (`tip:driver.py:131`), so `--bc` fails if the chl file has gone.
- **The on-disk layouts differ.** `so_bgc` carries `case_supergrid_path`, and X4 strengthens the point that reading old files tolerantly is mandatory.
- **Other facts that checked out:**
  - MCP `status.py:47` would list `schema_version` as a forcing.
  - The CI facts in X8 hold.
  - `gh stack` v0.1.0 is installed, and `gh stack init` adopts existing branches.
  - #271 is CONFLICTING.
  - The boundary-reorder risk in #315 already exists on main, which copies `ocn/` wholesale.

**Refuted**
- **Risk 6 is wrong about the runoff map.** The map is not named with the session id:
  - its name is `{rof}_to_{grid}_map_r{rmax}_f{fold}_nnsm.nc` (`CD/CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:1051-1053`);
  - the session-id name built at `tip:runoff.py:99` is dead code, overwritten at `:112`.

  The runoff map would be regenerated on fork for a different reason: A9's fingerprint keeps the absolute inputdir paths stored in `ROF2OCN_*_RMAPNAME` (`so_bgc` config.json). The same applies to CICE `ice_ic` (`tip:cice.py:415,422-428`) and `WW3_GRID_INP_DIR` (`tip:ww3.py:486,559`). As a result, the fork regenerates the most expensive non-ocean step.
- **"process_version covers code-only changes"** — false without a clean step (X2), and the proposal has none.
- **"File checks break `inspect()`"** — false. `inspect` passes `""` (`tip:base.py:706-709`), and `Path("").exists()` is True.
- **"`gh stack` needs push access to ESMCI, otherwise use a fork"** — unnecessary; see X9.
- **"Give #269's new input a constructor default"** — it already has `case_supergrid_path=None`.
- **"Additions under 400"** reinterprets the cap, which is on changed lines. Four PRs exceed it:

  | PR | Changed lines |
  |---|---|
  | #310 | about 420 |
  | VB2 | about 480 |
  | VB3 | about 465 |
  | D4 | about 1700 |

**Unverifiable**
- **"A dead SRCROOT breaks xmlchange."** A missing customize directory is tolerated (`/glade/work/manishrv/installs/CESM_crocodash/cime/CIME/config.py:77-104`). But `get_model()` guesses from the stale SRCROOT (`.../CIME/utils.py:522-552`) unless CIME_MODEL is set. The user's `~/.cime/config` sets `CIME_MODEL=cesm`.
- **C1's size of about 230 lines** likely undercounts. At least 10 test files set `cvars` directly (VCG report §1).

**Hidden work missed**
- **External consumers (X1).** Bundle 2.0 drops `crocodash_case.yaml`; `fork --plan/--bundle` are not kept; D1 drops the `bundle --cesmroot/--machine/--project` flags that `testing.yml` uses; the container's CrocoDash pin needs a bump.
- **D4 breaks two test areas:**
  - the `tests/user_nl_helpers` dependency in X6;
  - #312's `ReadCrocoDashCase` tests, which live in `tests/shareable/test_read_case.py` and would be deleted with that directory.
- **Its core guarantees rest on `slow` tests** (C1, C2, D2), which CI never runs (X3).
- **`ReadCrocoDashCase.record()` in `base.py` cannot import `driver.read_record`**, because the driver imports base (`tip:driver.py:33`). The record I/O has to move.
- **An eagerly loaded `forcing_config` goes stale** after `configure_forcings` runs on the same object.
- **Old cases get no files on fork.** Restore needs a recorded fingerprint, so cases from before #317/A9 restore nothing and re-run everything. Today's duplicate copies `ocn/`, `ice/` and `wav/` wholesale, so this is a regression.
- **No guard for the same basename on the same machine.** Such a case shares `$CIME_OUTPUT_ROOT/<name>/bld` and `/run` with its source.
- **Smaller gaps:**
  - the hard-coded `ocn/` in X5;
  - prompts must return defaults at end of input inside the container, which has no TTY;
  - #295 (X7);
  - the new docs page needs a toctree entry.
- **Decision 7 needs confirming.** "State stays at 1.1.0" — this plan bumps the state file to 1.2.0.

**Score: 6/10.** It has the most accurate PR-level facts and the most realistic order: tolerant reading first, #297 straight to main, the #269 catch. But A9 and fork reuse are broken (non-portable fingerprints, no clean step), external consumers are missed, and four PRs exceed the cap.

---

## Proposal 2: case-on-disk-model

**Verified**
- **Code facts:**
  - `case_state.py` is a leaf module: it imports `json`, `pathlib` and `CrocoDash.logging`.
  - The `run_workflow` signature is as stated; MCP `_bg_worker.py:38` calls it.
  - The ESMF mesh name can be derived from the state (`tip:case.py:402`).
  - The cvars sites at `case.py:383, 630, 671-686, 1089, 1106-1119` are as listed.
- **External consumers (X1).** Only this proposal found them: crocontainer `run_case.sh:24-32`, cesm-runner `container.py:399`, and the container's CrocoDash pin.
- **`--force` is a no-op for ic/bc (X2).** Also unique to this proposal. Its B5 `clean()` step is the right fix.
- **PR sizes:** #310 is +230/−174, and its test_configurators addition is 16 lines; #309 is 13 lines.
- **Smaller points:**
  - E3 handles the `_load_FType_MOM_params` move (X6).
  - The same-basename `CIME_OUTPUT_ROOT` guard is correct.
  - Its description of ESMCI merge practice is correct (X9).

**Refuted**
- **"`read_case.py` imports only case_state and forcing.base, so neither cycle is possible."** The cycle is real.
  - `CD/CrocoDash/forcing/__init__.py:7-20` imports every module in the package, including `driver.py`.
  - So importing `CrocoDash.read_case` first runs read_case → `forcing.base` → the package `__init__` → driver → `from CrocoDash.read_case import ReadCrocoDashCase` on a half-initialized module → ImportError.
  - CI hides this, because `tests/fixtures/objects.py:3` imports `CrocoDash.case` first.
  - It would hit a fresh MCP worker or a user script that imports the reader first.
- **§1.3 "the cimeroot override keeps writes working when symlinks dangle"** — its own risk 4 contradicts this.
  - CIME loads the stale SRCROOT into `GLOBAL` (`.../CIME/case/case.py:125-135`).
  - `get_model()` then guesses from it (`.../CIME/utils.py:540-552`) unless CIME_MODEL is set.
- **A3's rule "a missing declared output makes the entry stale, so process refuses":**
  - it would refuse at least 50 of the 69 on-disk configs, because they lack `ENABLE_BUGS_BY_DEFAULT`, which no process step reads (X4);
  - the remedy it names, `crocodash configure` (D3a), lands many PRs after A3;
  - cases with a dead cesmroot, such as `streamyr_v15`, cannot reconfigure at all.
- **"PBS scripts call `run_workflow`"** — they call the CLI (`CD/gallery/crocodash/advanced/submit_forcings.pbs:48`). The conclusion to keep the signature still holds.

**Unverifiable**
- T1 at about 300 lines (today #302 is 207 and #303 is 265).
- Whether T1 really removes the import-time failure for products defined outside the repo, while still requiring `time_sampling`.

**Hidden work missed**
- **CrocoDash's own CI bundle step.** E1b drops the `bundle --cesmroot/--machine/--project` flags that `testing.yml:150-155` uses (X1).
- **Replay for old cases.** The fallback replays everything after the last `case.setup` line, which includes `_apply_final_xmlchanges` (NTASKS_OCN, JOB_QUEUE). Forking such a case to ubuntu-latest, which has no batch system, makes `JOB_QUEUE` fail (see #309). Nothing filters machine-specific variables.
- **B5 must not clean on an absent record entry.** If it does, it breaks resuming after a crash, and A3 resets every record to absent, so the first run would wipe all raw chunks.
- **The atm shim's new `case_caseroot` input** needs a default, or a MAJOR bump under the proposal's own rule.
- **D2 (about 1000 lines) and E3 exceed the cap** and are not test-only.
- Also missed: X5 and X7.

**Score: 5/10.** It has the best external-compatibility work, keeps the state file at 1.1.0, and has the right clean step. But its core module placement creates an import cycle, and its stale-refusal rule plus late remedy would block most existing cases. Two PRs exceed the cap.

---

## Proposal 3: configurability-first

**Verified**
- **Param-model facts:**
  - `InputValueParam` and `InputFileParam` behave identically, and nothing reads the File/Value marker.
  - The ctor-sync check only requires a subset (`tip:base.py:619-636`).
  - Unknown kwargs are dropped silently (`:231-234`).
  - Runoff writes its suggested values back into its inputs (`runoff.py:106-111`).
- **Import graph is cycle-free.** The driver never imports the case reader. That correctly works around the `forcing/__init__` auto-import.
- **The lazy imports in `WorkflowContext` can move to the top.** `grid` and `topo` are thin mom6_forge re-exports, and `forcing/utils` imports only `raw_data_access.registry`.
- **CIME tools accept `--caseroot` and `--non-local`** (xmlquery:128,167; xmlchange:87,162), and they still record to `replay.sh`:
  - `.../CIME/Tools/xmlchange:297` opens the case with `record=True`;
  - `.../CIME/case/case.py:2345-2385` records `sys.argv`.
- **Reusing the session id on fork is safe.** `MB_ATTEMPT_ID` only names grid and mesh files: vCG `case_creator.py:402,927` and `tip:case.py:383-403`.
- **The `$INPUTDIR` substitution in fingerprints** correctly covers the absolute paths in the runoff, CICE and WW3 outputs.
- **#306 is independent** of #302/#303 and merges cleanly into main.
- **Other checks:**
  - #316 has no textual dependency on #315.
  - #310 is 404 lines.
  - All MCP line references are correct.
  - `MOM_RPS/param_file_reader.py` exists.
  - Machine-change filtering is a sound idea.
  - Tests that mock CIME and carry no `slow` marker will actually run in CI.

**Refuted**
- **#297' "process_version bump ⇒ finished steps rerun"** — they rerun but rewrite nothing (X2). The plan has no clean step.
- **Rejecting POP `freq` finer than MS** is a design objection, not a factual one: it removes the day_1 use case #303 advertises. That goes against "simplify, don't remove features"; fixing the month shift (P1/P2) keeps the feature.

**Likely underestimated (unverifiable as written)**

| PR | Planned size | Why it is likely larger |
|---|---|---|
| P1 | about 350 | about 49 InputParam declarations across 9 modules, plus 16 in the docs and 8 in tests, plus ctor rewrites and migrations |
| A2 | about 380 | the worktree work is already about 306 lines including its test, before tolerant reading, migrations and fixtures are added |
| A6 | about 390 | #317 alone is 352 lines |
| S3 | "about 40-line legacy reader" | it must reimplement the name-based apply logic after shareable is deleted |

- **The `KNOWN_SCHEMAS` rule forces about 8 serialized MINOR bumps** (A5, T1, T2, #297', P1, P3, #269, #311).

**Hidden work missed**
- **External consumers (X1).** The new fork CLI drops `--plan`, nothing says `crocodash_case.yaml` is kept, and the `bundle` CLI drops the flags `testing.yml` uses.
- **API-docs regeneration** for the new `case_files.py` in R1.
- **`jsonschema` is not declared** in `environment.yml`; it is only a transitive dependency.
- **MCP `validate_config_structure`** (`status.py:148`, `case.py:196`) breaks between P2 and M1 if it is renamed.
- **Delays an approved fix.** It parks the approved #297 behind six stack PRs.
- **Long critical path.** A → R → P → S is about 20 sequential PRs for a single merger.
- Also missed: X5, X7, and end-of-input prompt behavior.

**Score: 5/10.** It has the cleanest end-state model. But it adds the most new concepts, several PR sizes are underestimated, it repeats the process_version mistake, misses external consumers, and delays real fixes.

---

## Ideas to graft (correct and valuable)

1. **From P1:**
   - **#297 timing.** Land #297 on main after rm6 #76 merges, re-pinned to that merge commit, with the `submodule-bump` label. Then #310 declares `MARBL_FE_INTERIOR_SOURCE_FILE` and writes to `ctx.output_path`.
   - **#269 fix.** Restore `ignore_degenerate=True`, with a test.
   - **T0, tolerant reading, early on main:**
     - a missing input takes its ctor default, or raises `ReconfigureRequired`;
     - a missing output reads as None, and `require_output_param` raises only where a process step needs that output;
     - extra keys are ignored;
     - Chl and BGCRiverNutrients move their file checks into `configure()` and call `super().validate_args()`;
     - #305 waits for T0.
   - **T1 checks:** golden fixtures taken from real on-disk configs, a reviewed parameter snapshot, and a test that the migration chain is complete.
   - **A2 placement:** A2 sits on #312; `base.py` imports `check_version` directly.
   - **MCP M1** lands right after A2.
   - **Timing amendments:**
     - #305: clamp padding to archive coverage, count run days as end − start, add a wiring test;
     - #303: emit `function_overrides`;
     - #306: shift months only for monthly sampling.
   - **VB2** keeps a test that blocks written by today's code still parse.
2. **From P2:**
   - Keep `crocodash_case.yaml`, the `fork --bundle/--plan/...` flags and the plan keys, and make every prompt return its default at end of input. Bump crocontainer's CrocoDash pin before deleting shareable.
   - Add `clean(ctx, flag)` before `--force` or before a rerun whose recorded fingerprint differs. Never clean on an absent record.
   - Keep the state file at 1.1.0: derive `esmf_mesh_path`, and store the baseline in an optional `_crocodash_baseline.json`.
   - Fork refuses the same inputdir, or the same basename on the same machine.
   - Move `_load_FType_MOM_params` into `tests/user_nl_helpers`.
   - Compute fork-restore fingerprints from the source's config.json, so cases without a record still reuse files.
   - Move record I/O into `case_state`.
   - Add a static test that `cvars[` appears only in the creation methods.
   - Merge #316 before #305, with a wiring test.
3. **From P3:**
   - The driver never imports the case reader (`WorkflowContext.from_state`). Alternatively, keep `ReadCrocoDashCase` in `base.py`.
   - Fork reuses the source's session id.
   - Fingerprints substitute `$INPUTDIR` and `$CESMROOT` and include `process_version`.
   - Read-back writes call CIME tools directly (`--caseroot`, `--non-local`, argument lists), so vCG V1 leaves the critical path.
   - An explicit `Case.forcing_inputs()`, with a coverage test.
   - Skip PE, queue and project xmlchanges when the machine changes.
   - One replay.sh parser, covering `./xmlchange`, the absolute Tools path, `--id/--val` and comma lists.
   - Split the vCG-consumption and shareable-deletion PRs to stay under 400 lines.
   - Retarget #306 to main now.
   - Use mocked-CIME tests that are not marked `slow`.
   - Port #315's two scenario tests if #315 is closed.

## Ideas that must NOT be adopted

1. **P2's `CrocoDash/read_case.py` imported by `driver.py`** — it creates the import cycle.
2. **P2's "missing output ⇒ stale ⇒ refuse"** — it blocks most existing cases before any remedy exists.
3. **P1's A9 fingerprint ("strip `case_*`") as the fork-reuse gate**, and P1's premise that the runoff map is named with the session id.
4. **Any "bump process_version to force a rerun" claim without a clean step** (P1's A9, P3's #297').
5. **Dropping `crocodash_case.yaml`, `fork --plan/--bundle/--cesmroot/--machine/--project`, or `bundle --cesmroot/--machine/--project`** without updating crocontainer, cesm-runner and `testing.yml` in the same release.
6. **PRs over the cap that are not test-only:** P1's #310, VB2, VB3 and D4; P2's D2 and E3.
7. **P3's forced MINOR bump on every parameter-name change** (`KNOWN_SCHEMAS`).
8. **P3's rejection of POP `freq` finer than MS.**
9. **P3's parking of the approved #297** behind the whole output stack.
10. **Relying on `slow` tests for core guarantees**, since CI never runs them.
11. **P2's claim that the cimeroot override makes writes safe on a dead SRCROOT.** Treat those cases as read, process, bundle and fork only.
12. **P2's verbatim cross-machine xmlchange replay** for cases without a baseline.
13. **P1's eagerly cached `forcing_config` on the Case.** Make it lazy.
14. **P3's P1–P4 parameter overhaul at its stated sizes.** If adopted, split it.

### Critical Files for Implementation
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/base.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/driver.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case_state.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/crocontainer/container_scripts/run_case.sh