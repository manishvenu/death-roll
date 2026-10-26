# Critique of the three forcing-overhaul proposals

## Facts I verified (they change the scoring)

- **forcing/__init__.py imports every module in the package, driver.py included.**
  - At the tip, driver.py imports `ReadCrocoDashCase` from base.py.
  - If the reader moves to `CrocoDash/read_case.py` while driver still imports it, the import chain becomes read_case → forcing package → driver → read_case.
  - In a fresh process where `CrocoDash.read_case` is imported first, this raises ImportError on a partially initialised module.
  - So case-on-disk-model's claim that "neither cycle is possible" is false.
- **The state version check is an exact two-sided MAJOR.MINOR match on main** (case_state.py, `check_version`).
  - Bumping the state to 1.2.0 makes every older install refuse new cases.
  - crocontainer pins CrocoDash 2f28301c, which is not an ancestor of main.
- **Re-running a forcing step does not regenerate final files that already exist.**
  - `_merge_boundary` skips the final OBC file if it exists (obc.py:654).
  - The IC files and the BGC per-tracer split files are skipped the same way (mom6.py:187-194 and 335-342).
  - `force` only bypasses `is_done` (driver.py:172).
  - So a rerun triggered by `--force` or by a `process_version` bump leaves stale ic/bc files in place.
- **Deserializing a config runs the file-existence checks** (base.py:607 and 715).
  - It calls `cls(**inputs)`, which runs `validate_args`.
  - Chl and BGCRiverNutrients check that their input file exists, so reading a source config on another machine raises.
- **External bundle consumers.**
  - crocontainer's `run_case.sh:24-32` detects a bundle by `crocodash_case.yaml` and runs `crocodash fork --bundle … --plan '{xml_files,user_nl,source_mods,xmlchanges}'`.
  - cesm-runner `container.py:399` requires `crocodash_case.yaml`.
- **MCP.** `status.py:47` lists every config key except caseroot and conditions as a forcing, so `schema_version` would show up there; this is cosmetic. Process-flag resolution goes through CrocoDash's own `available_process_flags`. The MCP does not use `ReadCrocoDashCase` or `read_config`.
- **Measured PR sizes (changed lines).**
  - #312 162, #310 **404**, #313 516 (tests and docs), #315 150, #316 220, #317 352.
  - #302 207, #303 265, #305 354, #306 137, #297 221.
  - config-schema-version: 114 code + 192 test = **306**.
- **Merge simulations.**
  - #297 applies cleanly to main; against the output stack it conflicts only in bgc.py and test_bgc.py.
  - #305 and #316 conflict in ic.py, mom6.py and obc.py whichever lands first.
  - #316 applies cleanly onto #310 alone.
  - #269 drops `ignore_degenerate=True`, which is present on main and at #269's merge base.
- **External repos.**
  - The user has maintain and push rights on ESMCI/visualCaseGen and has merged their own PRs there (#41, #45, #46).
  - rm6 #76 is the user's own PR: open, mergeable, not reviewed.
- **Tooling.** `gh stack` v0.1.0 is linear only (`init`/`add` stack on top; `--base` only changes the trunk). Main is squash-merged, so stacks that branch off a mid-stack PR need manual retargeting.

## land-then-reshape: 7/10

**(a) Decisions**

| # | Delivered by | Concern |
|---|---|---|
| 1 | C1, C2, C4, C3, D1 | — |
| 2 | V1 + C1 | Has a local-helper fallback |
| 3 | C1 → V2/V3 → VB2/VB3 | StreamYears shim remains (necessary). Fallback if V3 is declined is stated openly |
| 4 | D4 | **Watered down:** `create_case_from_bundle` and `write_annotated_yaml` land in recipe.py, but the user said survivors live on Case, ReadCrocoDashCase or cli.py |
| 5 | D2 | — |
| 6 | P1, D3, M2 | — |
| 7 | A2 on #312, T0, T1, A9 | Best-calibrated policy. But C3 bumps state to 1.2.0, against "state stays 1.1.0", and older installs refuse new cases |
| 8 | Amendments to #302–#306 | Keeps every fix and adds real bug fixes. Typed freq is only a ParamSpec view; the user made it optional |

**(b) Sequencing**
- Strong overall:
  - all stacks are linear and on main, with explicit `gh stack init` commands;
  - #305 waits for T0;
  - the #316 rebase keeps `min_chunk_days`/`lookback_days`, guarded by an engine-arguments test;
  - #297 vs #310 is handled whichever lands first;
  - M1 lands right after A2.
- Errors:
  - A9's `process_version` doesn't actually regenerate ic/bc files (no clean step).
  - T0's error text names `crocodash configure` in wave 1, but that command (C4) ships in wave 3.
  - It never mentions crocontainer or cesm-runner. D1's bundle layout drops the `crocodash_case.yaml` marker, and the fork CLI is rewired, so the container path breaks.

**(c) Sizing**
- Over the cap and not test-only:
  - #310: already 404, about 420 after the amendments;
  - VB2: about 480;
  - VB3: about 465;
  - D4: about 1,700 lines of deletions.
- C3 is estimated at 330 but is probably over 450.
- A2 at about 350 is credible.

**(d) Value early:** Best of the three. It keeps every open PR and closes only #271. Timing and #297 land in wave 1, #315 stays as an interim fix, and it catches #269's `ignore_degenerate` regression.

**(e) ESMCI:** Good. C1 has a local-helper fallback, V2 is opened only after C1 (so it is a verbatim move), and the vCG-consumption PRs are leaves.

## case-on-disk-model: 5/10

**(a) Decisions**

| # | Delivered by | Concern |
|---|---|---|
| 1 | D1, D3a, D3b, E1a, D4 | `Case.xmlchange`/`set_user_nl` (D4) is gated on V3 |
| 2 | D1 | Requires V1 merged first; no fallback |
| 3 | V1–V3, D2 | D2 is about 1,000 lines |
| 4 | E3 | Good mapping of where each shareable item goes |
| 5 | E1b | — |
| 6 | E2, E1b | — |
| 7 | A2, A3, golden-schema test | **Partial:** no migrations (anything tolerant reading can't absorb becomes a MAJOR bump that rejects every old file); a newer MINOR is accepted with only a warning; the helpers are moved out of forcing/base.py into case_state.py |
| 8 | T0–T3 | Closes #302/#303 and re-cuts them |

**(b) Sequencing**
- The `read_case.py` import cycle (see facts above).
- S3 can't open until ESMCI V1 has merged.
- E1b, M1, crocontainer C1 and E3 all sit behind D4 → D2 → V3, so the stream-years review in ESMCI gates the merging of fork and duplicate and the deletion of shareable.
- B1 (#310) is hard-ordered after #297, which waits on rm6 #76.
- Timing (S5) hangs off B3, a mid-stack branch, which `gh stack` doesn't support.
- T1's `record_freq` is dropped by recipe's conditions special case until D3b, so bundle, duplicate and fork break for USER_SPECIFIED products in the meantime.
- There is no MCP PR after A2.
- The A3 hint names `crocodash configure`, which only arrives in D3a.
- Un-drafting #306 needs a GLADE-only test run, but the user tests through CI.

**(c) Sizing:** D2 and E3 are over the cap, flagged by the plan as exceptions, but the cap only exempts test-only PRs. B4 (#317 is already 352 before its additions) and A3 are optimistic.

**(d) Value early:** Closes #315, #302 and #303. The timing fixes wait for B3, and #269 is held until D3b.

**(e) ESMCI:** No interim path. The user's self-merge rights lower the risk, but the review time for V2 and V3 is on the critical path.

What it does best: state stays at 1.1.0 (the baseline goes in its own file and the mesh path is derived), it preserves the `crocodash_case.yaml`/`--plan` contract and adds a crocontainer bump, B5 cleans outputs before a rerun, config is read lazily, and restore is gated on matching fingerprints.

## configurability-first: 6/10

**(a) Decisions**

| # | Delivered by | Concern |
|---|---|---|
| 1 | R2, R3, P4, S3 | Bundling from a read-back case comes last |
| 2 | R1/R2 | Calls the CIME tools directly with `--caseroot`; no ESMCI needed |
| 3 | V1/V2, W1–W4 | — |
| 4 | S5–S7 | Renames the user-named `ReadCrocoDashCase` to `CaseFiles` |
| 5 | S2/S3 | — |
| 6 | P1–P4, S4, M2 | The strongest of the three |
| 7 | A2 + version fixtures | But it bumps MINOR on every param-name change (8 or more bumps) while refusing newer files, so parallel PRs collide on `KNOWN_SCHEMAS` and installs keep disagreeing |
| 8 | T1/T2, #306, #297' | Fixes kept but delayed |

**(b) Sequencing**
- Clean import graph: the driver never imports `case_files`.
- The R stack has no ESMCI dependency.
- M0 and M2 are placed correctly.
- Errors:
  - The T stack and #297' sit on #317 (A6), so the real timing fixes and the approved MARBL fix wait for six PRs, and the stacks form a tree.
  - #297's `process_version` bump "so finished steps rerun" won't re-apply the clipping fix, because the engines skip existing files.
  - T1 round-trips freq only through config.json; YAML dump drops it until P4.
  - Bundle v2 drops `crocodash_case.yaml` and `--plan` with no crocontainer PR.
  - `StaleConfigError` points at `reconfigure` (P4) from A2 onward.
  - R1 adds a new module without regenerating the API docs.
  - #306 has the same GLADE-only problem.

**(c) Sizing:** The deletions are split correctly. But A2 is claimed at about 380 while config-schema-version alone is 306 plus tolerant reading and migrations, so about 550–600. A6 is claimed at about 390 on top of #317's 352. P2 is probably over 450.

**(d) Value early:** Closes #315. The path A → R → P → S is about 20 PRs before fork and duplicate are merged. It also adds scope nobody asked for: unknown kwargs raise TypeError, `function_name` is chosen automatically, and a JSON Schema with `dependentRequired`.

**(e) ESMCI:** Best of the three. The vCG work is entirely in leaf PRs.

## Ideas worth grafting
1. **(land-then-reshape)** Amend the open PRs in place.
   - Timing stays its own linear stack on main, and #305 waits for T0.
   - #297 is retargeted to main now: merge rm6 #76, re-pin, add the `submodule-bump` label, re-request review and re-run the MARBL case.
   - Fix #269's `ignore_degenerate`.
2. **(land-then-reshape)** T0, tolerant `deserialize`, as an early standalone PR. Move the Chl and BGCRiverNutrients existence checks from `validate_args` into `configure()`.
3. **(land-then-reshape)** One version policy:
   - same MAJOR.MINOR is accepted;
   - newer is refused;
   - older MINOR is migrated step by step;
   - bump only for renames, new required inputs, or changed meaning.

   Add golden fixtures from real cases, a param snapshot, and a test that the migration chain is complete.
4. **(land-then-reshape)** Leave #317 as it is; put record versioning and portable fingerprints in a separate A9.
5. **(case-on-disk-model)** B5: delete a step's declared outputs before any rerun.
6. **(case-on-disk-model)** Keep the state file at 1.1.0. Derive `esmf_mesh_path`, and keep the creation baseline in `_crocodash_baseline.json`.
7. **(case-on-disk-model)** Keep `crocodash_case.yaml` and the `fork --bundle/--plan` flags and keys. Re-pin crocontainer in lockstep with the bundle-format PR.
8. **(case-on-disk-model)** Lazy config read, `ocn_dir` from the state's supergrid path, a static test that bans `cvars[` outside case creation, and moving #310's 16 test lines into #313 so #310 fits under 400.
9. **(configurability-first)**
   - The driver never imports the reader; otherwise keep the reader inside forcing/.
   - Use an explicit `Case.forcing_inputs()` with a coverage test.
   - Write to the case through CrocoDash's own CIME tool calls, with W as leaf PRs.
   - Fork keeps the source session_id.
   - Split deletions: re-point the tests, delete the code, then delete the tests in a test-only PR.
10. **(land-then-reshape)** One construction path: `__init__` ends with `_bind`. Refactor user_nl_blocks in place in C1, then move it verbatim in V2. Land M1 right after A2.

## Mistakes to avoid
1. A reader module outside forcing/ that driver.py imports (case-on-disk-model).
2. Gating fork or the shareable deletion on ESMCI stream years, or the read-back stack on V1 with no fallback (case-on-disk-model).
3. Stacking the timing fixes or #297 behind the output stack, and stacks that branch off a mid-stack PR (configurability-first, case-on-disk-model).
4. Closing working PRs where an amendment would do: #315 (both), #302/#303 (case-on-disk-model).
5. PRs over the cap that aren't test-only, or overloaded amendments: land-then-reshape #310/VB2/VB3/D4, case-on-disk-model D2/E3, configurability-first A2/A6/P2.
6. A state bump under the exact-match check (land-then-reshape C3, configurability-first R3).
7. Invalidating records with `process_version` but no clean step (land-then-reshape, configurability-first).
8. Error messages naming `configure`/`reconfigure` before that command exists (all three). Ship it right after `from_caseroot`, or word the interim remedy as dump + create `--override`.
9. Changing the bundle layout without the crocontainer/cesm-runner contract (land-then-reshape, configurability-first).
10. Bumping on every change while refusing newer files (configurability-first), or accepting MAJOR-only with no migrations (case-on-disk-model).
11. Adding conditions inputs without fixing recipe's conditions special case in the same PR (case-on-disk-model T1, configurability-first T1).
12. Fork in recipe.py (land-then-reshape). Use `Case.fork` built from the source's lazily loaded grids instead.
13. GLADE-only manual runs as a merge gate for #306 (case-on-disk-model, configurability-first).
14. Churn on user-named APIs: renaming `ReadCrocoDashCase` (configurability-first), moving the config helpers out of base.py (case-on-disk-model).
15. Growing forcing/base.py with `bundle()` and `user_changes()` (land-then-reshape).

## Suggested combined skeleton
- **Wave 0:**
  - Merge #309, #321, #322 and #312, plus rm6 #76.
  - Open V1 on ESMCI; the user can self-merge.
  - A2 on #312, under 400 lines.
  - T0 on main.
  - Amend #302, #303, #305 and #306.
  - Retarget #297 to main.
  - Fix #269.
- **S1:** #312 → A2 → #310 (16 test lines moved out) → #313 → #315 → #316 → #317 → A9 → B5. M1 lands right after A2.
- **S3:** #302' → #303' → #305' (after T0) → #306'.
- **S4, on main after S1:**
  - C1: writes take an explicit caseroot, `forcing_inputs()`;
  - C2: `from_caseroot`, with the reader inside forcing/ and state kept at 1.1.0;
  - C4: `crocodash configure`;
  - C3: baseline file, plus `xmlchange`/`append_user_nl`;
  - D1: bundle, keeping the marker;
  - D2: `Case.fork`, keeping session_id, with restore gated on fingerprints;
  - D3: prompts and annotated YAML, with P1 in parallel;
  - M2 and the crocontainer re-pin;
  - the deletion, split into tests-only and two code PRs.
- **vCG:** V2 after C1, then V3. VB2 and VB3 are leaf PRs with their test deletions split out.

### Critical Files for Implementation
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/base.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/forcing/driver.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/case_state.py
- /glade/u/home/manishrv/documents/croc/regional_mom_workflows/crocontainer/container_scripts/run_case.sh