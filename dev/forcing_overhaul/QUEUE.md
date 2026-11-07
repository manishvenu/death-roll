# Forcing overhaul: queue status

The single source of truth for where each PR stands. Each item's scope, test budget and
dependencies are in `QUEUE_DETAIL.md`.

**Status:** `queued` → `building` → `built` (committed locally) → `pushed` (no PR) →
`open #N` → `merged`.

**Rules:**
- Build everything ahead (decided 2026-10-23: all remaining branches are built and pushed, PRs open one by one).
- **1.1 merges are paused until 1.0.x ships** (decided 2026-11-06). A 1.0.x bug phase comes first,
  in org project #10 "CrocoDash 1.0.x": sprints Bugs 1 (Nov 10), Bugs 2 (Nov 17) and Audit
  (Nov 24), planned in `dev/crocodash_1_0_x/`. #326 and #327 stay open and unmerged. This
  board's Sprints 3–13 moved 3 weeks later (Sprint 3 = Dec 1 … Sprint 13 = Feb 9; ids and
  item sprints checked unchanged), then one more week for a second audit week (Audit 2, Dec 1):
  Sprint 3 = Dec 8 … Sprint 13 = Feb 16 (2026-11-06, ids and item sprints checked unchanged). When 1.0.x is tagged, every queue branch rebases onto it;
  the timing stack drops the ported #306 commits in favour of `TimeRequest.select`.
- At most 2 CrocoDash queue PRs open at once. The next to open is the earliest-sprint
  item whose needs have merged (not the lowest Q; decided 2026-10-30). Tiny PRs (under ~50
  lines) and PRs blocked on another repo (e.g. #297 waiting on rm6 #76, #326 waiting on
  ESMCI #52 and CDEPS#3), drafts included, don't count toward the 2.
- Space and time in data access follow `SPACE_TIME.md` (decided 2026-10-30): `Region` and
  `TimeRequest` stay small (a few fields, four methods each).
- `REGION_PLAN.md`: what replacing `longitude_slicer` everywhere takes (Region's test plan,
  the move to mom6_forge), and why queryearth stays separate.
- E1–E3 open together on ESMCI.

## Next actions (as of 2026-10-26)

Every branch below is built and pushed; local heads match origin, and none is behind main.

**Board:** https://github.com/orgs/CROCODILE-CESM/projects/9 ("CrocoDash Version 1.1").
Every unopened PR is an issue in Backlog there (2026-10-26), with a "Depends on" line and
GitHub "blocked by" links between the issues (an open PR can't be a blocker, so waits on
#325/#326/#327/ESMCI #50 are text only). Each drafted PR body in `prs/` ends with
"Closes #N" for its issue. The visualCaseGen follow-up ideas stay off the board until the
user says otherwise.

| Q | Issue | Q | Issue | Q | Issue |
|---|---|---|---|---|---|
| Q4 | #329 | Q8 | #333 | Q13 | #340 |
| Q9 | #330 | Q11 | #334 | Q14 | #341 |
| Q6 | #331 | Q5 | #335 | Q15 | #342 |
| C1 | crocontainer #16 (closed) | Q10 | #336 | Q16 | #338 |
| Q7 | #332 | Q12 | #337 | Q17 | #339 |
| Q19 | #343 | C2 | crocontainer #18 | G1 | CrocoGallery #63 |
| Q20 | #345 | Q21 | #346 | Q22 | #347 |
| Q23 | #348 | Q25 | #352 | | |

Q19, C2 and G1 were added 2026-10-26 by `board_new_issues.py` (already run; don't rerun):
#343 is blocked by #342, crocontainer #18 by #343, CrocoGallery #63 by #340, #341 and
#343. The stale crocontainer #16 ← #340 link was removed when #16 closed.

Q20–Q23 and the Backlog bug #349 (static download script methods) were added 2026-10-30 by
`board_space_time.py` (already run; don't rerun), which also retitled #335 to Q5's
TimeRequest scope, closed #328 (duplicate of #329) and ESMCI #53 (superseded by CDEPS#3),
put #344 in Backlog and posted #327's description. Blocked-by: #335 ← #332, #333;
#345 ← #335; #346, #347 ← #345; #348 ← #346, #347; #338, #339 ← #345.

Q25 (#352, open-edge detection split out of #269) was added 2026-11-05 with Sprint 13
(Jan 19; every existing iteration passed back by id, all 12 unchanged). Blocked-by:
#352 ← #338, #339.

**Sprints (board field `Sprint`, weekly from Tue 2026-10-27, set up 2026-10-27).** Each
week the user readies two queue PRs (assigned to them, "In progress"); the next week they
go to review (alper's review *requested*, not assigned). An item sits at least one sprint
after everything it needs is under review, so its needs have merged when it reaches review.

| Sprint (week of) | Review (alper) | Getting ready (user) |
|---|---|---|
| 1 (Oct 27) | #325, ESMCI #51–#52, #279, #309, mom6_forge #155 | — |
| 2 (Nov 3) | | #326 (Q2, after ESMCI merges), #327 (Q3) |
| 3 (Dec 8) | | #331 (Q6), #333 (Q8), with #353 (CESM output boundaries, the 1.0.x known issue) |
| 4 (Dec 15) | | #329 (Q4), #330 (Q9) |
| 5 (Dec 22) | | #332 (Q7), #334 (Q11) |
| 6 (Dec 29) | | #335 (Q5 time-request), #336 (Q10) |
| 7 (Jan 5) | | #345 (Q20 region), #337 (Q12) |
| 8 (Jan 12) | | #346 (Q21), #347 (Q22) |
| 9 (Jan 19) | | #348 (Q23), #341 (Q14) |
| 10 (Jan 26) | | #340 (Q13), #338 (Q16) |
| 11 (Feb 2) | | #342 (Q15), #339 (Q17, also needs ESMCI #50) |
| 12 (Feb 9) | | #343 (Q19), with crocontainer #18 and CrocoGallery #63 |
| 13 (Feb 16) | | #352 (Q25) |

**Timing first (user, 2026-11-06):** 1.0.x ships with CESM-output boundaries as a known
issue (#353; its IC half is #358 in 1.0.x), so the fix, Q6 then Q8, takes the first 1.1
week. Q8 is readied in the same week as Q6, an exception to the one-sprint gap; it goes
to review once Q6 merges. Q4, Q9 and `pe-layout` moved to Sprint 4, Q7 and Q11 to 5, Q10
to 6; every need still sits at least a sprint ahead. #353 moved from #10 to #9 Sprint 3
(other #9 items and the iterations checked unchanged).

Sprints 3–12 items are issues for unopened PRs: assigned to the user, still Backlog until
their week. Sprints 7–10 were added 2026-10-27 and 11–12 on 2026-10-30 with
`updateProjectV2Field`, passing every existing iteration's id back (that keeps them and
their items; verified unchanged both times). Always pass the existing ids and check the
assignments before and after. The data-access work (Q5, Q20–Q23) goes ahead of the
sharing tail (Q13–Q15, Q19), decided 2026-10-30.

**Pacing (user, 2026-10-26): don't open the next PR just because a slot is free.** Wait
for the open ones to merge, and ask before opening anything.

1. **#325 (Q1): wait for it to merge.** 6120f3de added the migration-loop guard and the
   "upgrade CrocoDash" message for newer files. Branches built on its old head 483ad56b
   (Q4, Q6, Q9 and above) rebase with `--onto origin/main 483ad56b`; Q4 also edits
   `case_state.check_version`, so expect a small conflict there.
2. **#326 (Q2) waits for ESMCI #52 and CDEPS#3 (revised 2026-10-30).** Built locally on
   `writes-name-caseroot`, not pushed yet (pushing it fast-forwards #326; push and new
   description `prs/Q02-writes-name-caseroot.md` need the user's OK):
   - 3bef4b34: visualCaseGen's `xmlchange(caseroot=)` (ESMCI #51, merged 2026-10-27) and
     `user_nl_blocks` (ESMCI #52); CrocoDash's copy and the local helper deleted.
   - 471fb8ec..fbea1cf1 (pushed, description updated 2026-10-30): StreamYears and
     `cdeps_streams.py` deleted; `DATM` configurator (`forcing/datm.py`, user's name) and
     Runoff set `DATM_YR_*`/`DROF_YR_*` via `datm.stream_years(caseroot, component)`
     (xmlquery only, no Case attributes: user dislikes reaching into the Case). Assumes
     CROCODILE-CESM/CDEPS#3 is in CESM `crocodash` (ESCOMP cdeps1.0.101 today: JRA cases
     stop at configure). ESMCI #53 is no longer needed.
   - Bump the visualCaseGen pin to ESMCI main once #52 merges. `vcg-case-config`
     (d8f52205, the #53 version) is superseded. Rebase Q11–Q17 onto #326 when it merges;
     Q12 imports `user_nl_blocks` from visualCaseGen.
3. **When a PR merges:** rebase every branch built on it (the Status column names each
   base), re-push, update this file, then open the lowest Q whose needs are all on main.
4. **crocontainer #17 merged 2026-10-26** (e1fec8de; closed crocontainer #16). The
   user lets crocontainer PRs merge to main without asking. Once an image is built from
   main (Monday cron, or a build.yml dispatch), Q13 (#340) moves testing.yml's image tag
   from `sha-acfa305` to it.
4a. **Grid files in the create config (Q19, decided 2026-10-26):** a create config is
   `Case()`'s arguments (`case:`, with `ocn_grid`/`ocn_topo`/`ocn_vgrid` naming the grid
   files) plus `configure_forcings()`'s (`forcings:`); the grid sections and builders are
   gone. Built and pushed with its two companions:
   - **C2**, crocontainer `grid-files`: grid scripts for the demo, YAML mode
     (`/workspace/grids.py`), the weekly tests and the NYF sample. **Merge it right after
     Q19 merges**, not before: the weekly tests follow both repos' branch tips. Then bump
     crocontainer's CrocoDash submodule past Q19.
   - **G1**, gallery `crocodash-cli-overhaul`: starter config, CLI page (create --from,
     configure, no fork/duplicate) and the tutorials' `sharing.html` links. Open it once
     #340, #341 and Q19 are on main.
   - **MCP:** after Q19 merges, `create_case` writes the grid files (its `_build_*`
     helpers) and names them in `case:`.
5. **ESMCI #51–#53:** CI green, mergeable, review requested from alperaltuntas (none yet
   on 2026-10-26). The user merges after approval, or Claude does with an explicit OK.
6. **Before Q15 merges:** move the MCP server's `bundle_case`, `fork_case` and
   `duplicate_case_tool` off `shareable.py` (`dev/MCP_CrocoDash`), to `Case.bundle()` and
   `create_case_from_yaml(source=)`.
7. **Checks to run by hand** before their PRs merge: the Verification list at the end
   of `QUEUE_DETAIL.md`.

## CrocoDash

| Q | Stack | Branch | Needs | Status | PR |
|---|---|---|---|---|---|
| — | — | `job-queue-no-batch-system` | — | open | #309 |
| — | — | `bgc-fe-interior-source` | rm6 #76 | open (approved) | #297 |
| — | — | `pe-layout` | main | moved to 1.0.x 2026-11-06 (#10 Bugs 2; body `dev/crocodash_1_0_x/prs/pe-layout.md`, opens after #357 merges). pushed (6a944dae, 2026-11-05; issue #350; body `prs/pe-layout.md`). A `PELayout` configurator sets NTASKS/ROOTPE from the ocean point count: one shared node up to 64 MOM6 tasks, then MOM_interface's S/M/L carried over unchanged | |
| Q1 | C | `config-read` | main | open, changes requested 2026-10-28; review addressed in 7e5e55bb (pushed); description updated and one-line replies posted on all 11 comments (2026-10-28); waiting for alper's re-review | #325 |
| Q2 | — | `writes-name-caseroot` | main, ESMCI #52, CDEPS#3 | draft; pushed fbea1cf1 2026-10-30 (visualCaseGen user_nl_blocks/xmlchange; `DATM` configurator in forcing/datm.py + Runoff set DATM_YR_*/DROF_YR_* from xmlquery, one extra year each side clamped to the CDEPS compset defaults; run dates set before the configurators; StreamYears/cdeps_streams.py deleted; +331/−1189). Waits for ESMCI #52 (pin) and CDEPS#3 in CESM crocodash | #326 |
| Q3 | T | `time-sampling` | main | draft since 2026-10-26 (mark ready when its turn comes). 0d00fea7 (2026-10-30): `@accessmethod(subsample=True, data_freq=True)` replace freq_handling; `resolve_time_sampling(product, method, data_freq, freq)`; POP means dated from time_bound (first day of interval), no apply_month_shift; CESM readers thin with freq and check data_freq against the files; + GLORYS RDA subsample test (6957082c). Description posted 2026-10-30. On its own, freq="MS" gives ~weekly samples and no record before the start; Q8 fixes it | #327 |
| Q4 | C | `case-from-caseroot` | Q1 | pushed (7fc0c524, on config-read) | |
| Q5 | T | `time-request` | Q7, Q8 | pushed (4a92f657, 2026-10-30, on local merge e7bacfc9 of Q7 `declared-output-files-v2` + Q8 `time-windows`; +490/−216 incl. #335's two commits). `TimeRequest` per SPACE_TIME.md; thinning keeps the record whose time bounds hold each date (#327's rule). Replaces `tseries-time-slice` (2ac2823f, stays on origin; old head 64c04e3a kept as local `parked/tseries-time-slice-pre-1030`) | |
| Q6 | T | `typed-freq-inputs` | Q1, Q3 | pushed (55ecd9c3, rebased 2026-10-30 onto 0d00fea7 with --rebase-merges; still merges old config-read 483ad56b; data_freq/subsample_freq checked against the @accessmethod flags) | |
| Q7 | C | `declared-output-files-v2` | Q4 | pushed (e1556bdb, on case-from-caseroot; + `process_forcings(preview=)` 2026-10-26; + input files checked before processing and shown in `--preview` 2026-10-28) | |
| Q8 | T | `time-windows` | Q1, Q6 | pushed (f360bdf6, rebased 2026-10-30 onto 55ecd9c3: #305's 4 commits + amendments; window test checks a record at/before the start and at/after the end). Also fixes #353's boundary half: before opening, rerun the hc1030 FOSI case from 2000-07-01 on it (boundaries build, no repeated times). When rebasing onto 1.0.x main, #358's `_record_at_start` is there; keep it until Q5 replaces it | |
| Q9 | — | `forcing-param-specs` | Q1 | pushed (0371a028, on config-read) | |
| Q10 | C | `finished-steps` | Q7 | pushed (9eeb7400, rebased onto e1556bdb 2026-10-28: the input-file check skips finished steps) | |
| Q11 | S | `configure-existing-case` | Q2, Q4 | pushed (499b8e1c, on case-from-caseroot + merged writes-name-caseroot) | |
| Q12 | S | `case-changes` | Q11 | pushed (ab4a5104, on configure-existing-case) | |
| Q14 | S | `forcing-walkthrough` | Q9, Q11 | pushed (5665e3a1, on local merge 1f839164 of Q11+Q9; +382/−17). Now before Q13. Re-cut 2026-10-26: the prompts are the general forcing walkthrough (create/configure/`ask=True`), not fork's | |
| Q13 | S | `bundle-and-create-from` | Q14, Q10, Q12 | pushed (e35016e6, on local merge ff293b36 of Q14+793c3832; +669/−506, most removals the old sharing doc and CLI tests). Re-cut 2026-10-26: `crocodash create --from` replaces fork; fork and duplicate removed | |
| Q15 | S | `drop-shareable` | Q13, MCP moved off shareable | pushed (5862c160, on bundle-and-create-from; pure deletion) | |
| Q16 | — | `interior-obc-segments` | Q7, Q8, Q11, Q20 (its segment boxes become `Region`s; rebase when Q20 is built) | pushed (d18211d5, on local merge 94c65a44 of Q7+Q11+Q8; worktree `interior-obc-v2`; needs a Derecho run with an interior segment) | |
| Q17 | — | `cyclic-grid-v2` | Q7, Q11, ESMCI #50, Q20 (cyclic edges become full-circle `Region`s) | pushed (e3b23b08, on local merge 60bd25cc of Q7+Q11; pins vCG to the #50 head, re-pin to ESMCI main before opening; redo #311's Derecho cyclic run; the original `cyclic-grid` branch/worktree is untouched) | |
| Q20 | T | `region` | Q5 | pushed (c0667295, on time-request; +406/−127). Open: two `select` bugs on 2-D sources (a continent's NaN land blocks keep the whole globe; labels jump by 360 at the west edge) and the label-convention decision, in REGION_PLAN.md; fixing them restacks Q21–Q23 | |
| Q21 | T | `glorys-reference-requests` | Q20 | pushed (e4d1532f, on region; +148/−266). Open: `get_glorys_data_from_cds_api` returns the stale file after a retry (copernicusmarine writes `glorys_(1).nc`); predates the stack | |
| Q22 | T | `cesm-cice-ww3jra-windows` | Q20 | pushed (22e5beda, on region; +317/−453) | |
| Q23 | T | `drop-loose-access-args` | Q21, Q22 | pushed (1d315602, on local merge bd0f0f73 of Q21 + Q22; +242/−532). Old heads kept as local `parked/drop-loose-access-args-pre-fixes` (44ca90da) and `-mid-fixes` (1897713c) | |
| Q25 | — | `detect-open-boundaries` | Q16, Q17 | queued (not built; from #269's `interior-obc-new` b22a680f; body `prs/Q25-detect-open-boundaries.md`) | |
| Q19 | S | `yaml-grid-paths` | Q15 | pushed (c266a43b, on drop-shareable; +117/−314). The create config names the grid files; builders removed | |
| Q18 | — | `vcg-case-config` | E1–E3 merged | superseded 2026-10-30 by #326's a058fca8 (stream years go to CDEPS#3, not ESMCI #53); branch d8f52205 kept | |

**Q18 note:** before opening, bump `CrocoDash/visualCaseGen` to ESMCI main with E1–E3 merged (label `submodule-bump`) and rebase onto main. Locally it was import-checked against `visualCaseGen-worktrees/e123-integration`, a local-only merge of E1+E2+E3 (never push it). Q12's `Case.set_user_nl` must not add to `forcing/user_nl_blocks.py`, which Q18 deletes.

**Merge hazards (found while building, 2026-10-23):**
- **Q7 vs Q8** (`ic.py`, `obc.py`, `mom6.py`): keep Q8's `min_chunk_days`/`lookback_days`/`_function_args()`/`_obc_dates()`, drop every `preview` argument and branch. Resolved this way in 94c65a44.
- **Q6 vs Q11** (`recipe.py` → `Case.forcing_args`): Q6 added the `data_freq`/`subsample_freq` round trip to `recipe.generate_configure_forcing_args`, which Q11 deletes and moves to `Case.forcing_args()`. Whichever merges second must carry the loop into `Case.forcing_args()` (done in 94c65a44).
- **Q9 vs Q11** (`recipe.py`, `forcing/base.py` registry init): Q9 makes `generate_configure_forcing_args` skip derived inputs and adds the unknown-kwarg warning next to the `case.__dict__` scan; Q11 moves that function to `Case.forcing_args()` and replaces the scan with `forcing_inputs()`. Whichever merges second must make `Case.forcing_args()` skip derived inputs and keep the warning.
- **Q16 vs Q17** (`Case.forcing_inputs()`): each adds one key (`case_supergrid_path`, `case_cyclic_x`); keep both.
- **Q16 vs Q10**: Q16 makes the conditions `_fingerprint` ignore `case_*` inputs; Q10's conditions `step_settings` reuses `_fingerprint`, so it inherits that (wanted: settings stay portable).
- **#325 golden configs vs #326**: `streamyr_jra.json` and `so1deg_wav.json` (restored on #325 in dcb66254) have a StreamYears entry, which #326 deletes, so `test_golden_configs_load` fails once both are on main. Whichever lands second decides: skip the retired `streamyears` entry in `iter_configurator_entries` (it never had a process step), or drop it from those two files.
- **Q12 vs Q18**: Q12's `case.py` reads `user_nl_blocks._parse/_key/_TAG`; when Q18 switches to visualCaseGen's module (same names), only that import changes.
- **Q13 and the container CI job**: the pinned image's `run_case.sh` calls `crocodash fork`, which Q13 removes, so `run_cesm_crocontainer` fails until Q13's testing.yml points at an image built from crocontainer PR #17. The job copies the PR's CrocoDash into the image, so the image's own CrocoDash submodule doesn't matter.
- **Branches on local merges** (Q13, Q14, Q16, Q17): when their needs merge, `git rebase --onto origin/main <merge commit> <branch>` keeps only their own commits. Q14's merge commit is 1f839164; Q13's is ff293b36 (rebase Q13 onto the rebased Q14).
- **#325's review changes (7e5e55bb, 2026-10-28)** vs the branches built on its old head
  483ad56b (Q4, Q6, Q9 and everything above): `base.py` changed in `deserialize`, the
  getters, `InputParam(optional=)`, `configure()` and every config.json loop
  (`iter_configurator_entries`); chl.py/bgc.py lost their warnings; `json_safe` in
  registry.py. Expect conflicts when they rebase `--onto origin/main 483ad56b`. Q9 adds
  `derived=` to InputParam next to `optional=`: keep both. Code a later branch adds that
  loops over config.json should use `iter_configurator_entries`.
- **Q7's preview commit (d1ef365e, 2026-10-26):** Q10 is rebased onto it. The local merges
  that contain the old Q7 head ad374ac0 (Q13's 793c3832/ff293b36, Q16's 94c65a44, Q17's
  60bd25cc) pick it up from main when rebased `--onto origin/main <merge commit>`.
- **Q19 and its companions:** Q19 sits on `drop-shareable` (5862c160); once Q15 merges,
  `git rebase --onto origin/main 5862c160 yaml-grid-paths`. C2 and G1 are on their
  repos' main and need no rebase unless those move.
- **Q21 vs Q22, reference_ice's buffer (2026-10-30):** Q22 removes CICE's own `.padded(1)`
  and gives cice_restart `buf=2.5`. reference_ice had no buffer of its own and relied on
  that pad, so wherever Q21 and Q22 meet (Q23's base merge), REFERENCE_ICE's
  `get_reference_ice_data` must become `@accessmethod(buf=1.0)`.
- **Q20's CICE call path:** CICE goes through `utils.call_access_method`, not
  `fetch_raw_chunk`, because fetch_raw_chunk would reuse a stale subset (CICE has no
  `stale_outputs`). Moving it is out of this stack.
- **Minor review points, applied 2026-10-30 before pushing** (each in its own branch, then
  the stack rebased; Q22 and Q23 tests rerun, 63 and 81 passing): roll `Region.select`'s all-columns 2-D case so it
  starts west at lon_min (Q20), and fix test_ic.py's stale `longitude_slicer` comment (Q21).
  From the real CESM-HR check (2026-10-30, all checks passed): a thinned CESM subset's
  file name ends in `_{n}dates`, so two thinnings with the same count (QS vs QS-FEB) can
  reuse each other's cached raw subset; name it from the dates themselves (Q5,
  cesm_ocean_output.py ~762). And `check_data_freq`'s error could name the alias the
  spacing matches ('MS' for ~31 days), not only the spacing (Q5).
  From the real GLORYS RDA check (2026-10-30, all 6 checks passed): `Region.select`
  keeps the source longitude's `valid_min`/`valid_max` (-180/179.92) on labels it moves
  past 180, so netCDF4-python masks them (xarray doesn't; old `longitude_slicer` dropped
  them via assign_coords): drop those attributes when relabelling, and relabel in float64
  (adding 360 only where needed) so unmoved labels stay exactly the source's (Q20,
  region.py ~103).
  From the real-grid box check (2026-10-30; edge boxes correct and minimal on 14 grids,
  incl. ±180-split and polar; IC boxes unchanged): `Region.around` round-trips longitudes
  through 0..360, so lon_min can miss the westernmost point by ~1e-14 (harmless with any
  buffer; drops that column at buf=0): build it without the round trip (Q20, region.py
  ~36-47). Between Q20 and Q21, GLORYS RDA still goes through mom6_forge's
  `longitude_slicer`, which raises when a box's midpoint lies in (179.92, 180]
  (mom6_forge utils.py:73-74, pre-existing on 0..360 grids too); Q20's tighter boxes reach
  it on some ±180-split grids, and Q21 takes the slicer off that path. Keep Q20 and Q21
  in consecutive sprints; consider a mom6_forge issue for the slicer.
- **`pe-layout` vs every queue branch (2026-11-05):** each conflicts in `case.py` on the
  removed `NTASKS_OCN` xmlchange, the `_apply_final_xmlchanges(ntasks_ocn, …)` call and
  `import math`. Take `pe-layout`'s side and keep the rest of theirs; whichever merges
  second resolves it.
- **Superseded branches** (kept on origin, not to be opened): `fork-cli-and-prompts` (3825d243) and `bundle-and-fork` (a5c60030), the fork-based Q14/Q13 before the 2026-10-26 re-cut.

**Q5 note (revised 2026-10-30):** stack T is now Q3 → Q6 → Q8 → Q5 → Q20 → Q21/Q22 → Q23
(SPACE_TIME.md). Q5 keeps #335's behaviour (window-only records, IC at or before the start)
inside `TimeRequest.select`. Earlier note (2026-10-23): Q5 is the last step of stack T (Q3 → Q6 → Q8 → Q5).
Without Q8, monthly CESM data with an IC starting mid-month would error, and monthly OBC
is broken on main either way. Rebase Q5 onto Q8 when Q8 is built; it also shares
`cesm_ocean_output.py` with Q3.

## ESMCI/visualCaseGen

| E | Branch | Needs | Status | PR |
|---|---|---|---|---|
| E1 | `case-tools-caseroot` | — | open (+14717a6: a missing ./xmlchange raises RuntimeError) | ESMCI #51 |
| E2 | `user-nl-blocks` | Q2 built | open | ESMCI #52 |
| E3 | `stream-years` | — | closed 2026-10-30 (superseded by CDEPS#3) | ESMCI #53 |

All three are green in CI (2026-10-24). Each body ends with "Possible follow-ups in
visualCaseGen", listing where vCG itself could use the new code (CaseCreator passing
`caseroot=`, its own user_nl entries as tagged blocks, stream-year alignment at launch).

## Other repos

| Repo | What | When | Status |
|---|---|---|---|
| regional-mom6 | #76 (pinned by #297) | now | open |
| dev/MCP_CrocoDash | `read_config` + `CONFIG_META_KEYS` | after Q1 | queued |
| dev/MCP_CrocoDash | `list_forcing_configs` → `param_specs` | after Q9 | queued |
| dev/MCP_CrocoDash | bundle on `Case.bundle()`, fork/duplicate tools on `create_case_from_yaml(source=)` | before Q15 merges | queued |
| crocontainer | C1 `fork-new-bundle` (6af936c): `run_case.sh` runs `crocodash create --from /workspace/bundle --configure-only --no-input`; an old-format bundle stops it with a message instead of running the Panama demo; smoke test drops the fork check | any time (merging allowed) | merged 2026-10-26 (#17, e1fec8de) |
| crocontainer | C2 `grid-files` (6de3576): `panama_grids.py`, `labsea_grids.py`, `/workspace/grids.py` in YAML mode, NYF sample writes its grids; configs name the grid files | right after Q19 merges | pushed, no PR |
| CrocoGallery | G1 `crocodash-cli-overhaul` (c67b0324a): `starter_case.yaml` names grid files; `cli_workflow.md` create --from/configure; tutorials link `sharing.html` | after #340, #341, Q19 | pushed, no PR |
| dev/MCP_CrocoDash | `create_case` writes the grid files and names them in `case:` | after Q19 merges | queued |

## Triage of PRs that were open on 2026-10-23

Each close needs your OK. The comment is one line: "Parked: its work returns through the
forcing-overhaul queue as QNN". No @-mentions.

| PR | Action | Goes to | Done |
|---|---|---|---|
| #312 | close | Q4 | closed 2026-10-23 |
| #310, #316 | close | Q7 | closed 2026-10-23 |
| #313 | close | dropped (one fast check in Q7) | closed 2026-10-23 |
| #317 | close | Q10 | closed 2026-10-23 |
| #315 | close | Q13 | closed 2026-10-23 |
| #302, #303 | close | Q3 | closed 2026-10-23 |
| #305 | close | Q8 | closed 2026-10-23 |
| #306 | close | Q5 | closed 2026-10-23 |
| #321 | close | — (reopen if MOM_interface PR 353 lands before Q13) | closed 2026-10-23 |
| #322 | close | — (Q15 deletes the code) | closed 2026-10-23 |
| #269 | close | Q16 | closed 2026-10-23 |
| #311 | close | Q17 | closed 2026-10-23 |
| #271 | close | — | closed 2026-10-23 |

## Parked branches (preserved)

Every closed PR's branch is still on origin at its PR head. A local backup branch
`parked/<branch>` sits at the same commit in the main CrocoDash clone (local only, never
pushed). Don't delete either until its queue item has merged.

| PR | Branch | Head | Becomes |
|---|---|---|---|
| #312 | `read-crocodash-case` | fc873e01 | Q4 |
| #310 | `declared-output-files` | 7b368d29 | Q7 |
| #316 | `forcing-preview-dry-run` | 92435492 | Q7 |
| #313 | `output-files-reference-check` | 5de7b034 | (one check in Q7) |
| #317 | `skip-finished-forcing-steps` | 72226b94 | Q10 |
| #315 | `shareable-restore-output-files` | 6ec5f4e3 | Q13 |
| #302 | `product-time-sampling` | 34651f45 | Q3 |
| #303 | `product-freq-subsample` | a7aa6ef3 | Q3 |
| #305 | `time-aware-forcing-steps` | 542887a8 | Q8 |
| #306 | `cesm-tseries-slice-time` | 7883bee7 | Q5 |
| #321 | `load-mom-rps-param-reader` | d5fec5e6 | — (reopen if MOM_interface PR 353 lands first) |
| #322 | `clean-temp-case-output` | a684f21f | — |
| #269 | `interior-obc-new` | b22a680f | Q16 |
| #311 | `cyclic-grid` | bd306664 | Q17 (its own chain: mom6_forge #153 → vCG #50 → #311; local worktree `CrocoDash-worktrees/cyclic-grid` is untouched) |
| #271 | `cesm-not-ported-case` | aaac1abe | — |
