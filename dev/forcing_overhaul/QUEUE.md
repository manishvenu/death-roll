# Forcing overhaul: queue status

The single source of truth for where each PR stands. Each item's scope, test budget and
dependencies are in `QUEUE_DETAIL.md`.

**Status:** `queued` → `building` → `built` (committed locally) → `pushed` (no PR) →
`open #N` → `merged`.

**Rules:**
- Build everything ahead (decided 2026-10-23: all remaining branches are built and pushed, PRs open one by one).
- At most 2 CrocoDash queue PRs open at once. The next to open is the lowest Q whose
  needs have merged. Tiny PRs (under ~50 lines) and PRs blocked on another repo (e.g.
  #297 waiting on rm6 #76) don't count toward the 2.
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

Q19, C2 and G1 were added 2026-10-26 by `board_new_issues.py` (already run; don't rerun):
#343 is blocked by #342, crocontainer #18 by #343, CrocoGallery #63 by #340, #341 and
#343. The stale crocontainer #16 ← #340 link was removed when #16 closed.

**Sprints (board field `Sprint`, weekly from Tue 2026-10-27, set up 2026-10-27).** Each
week the user readies two queue PRs (assigned to them, "In progress"); the next week they
go to review (alper's review *requested*, not assigned). An item sits at least one sprint
after everything it needs is under review, so its needs have merged when it reaches review.

| Sprint (week of) | Review (alper) | Getting ready (user) |
|---|---|---|
| 1 (Oct 27) | #325, ESMCI #51–#53, #279, #309, mom6_forge #155 | — |
| 2 (Nov 3) | | #326 (Q2, after ESMCI merges), #327 (Q3) |
| 3 (Nov 10) | | #329 (Q4), #330 (Q9) |
| 4 (Nov 17) | | #331 (Q6), #332 (Q7) |
| 5 (Nov 24) | | #333 (Q8), #336 (Q10) |
| 6 (Dec 1) | | #335 (Q5), #334 (Q11) |
| 7 (Dec 8) | | #337 (Q12), #341 (Q14) |
| 8 (Dec 15) | | #340 (Q13), #338 (Q16) |
| 9 (Dec 22) | | #342 (Q15), #339 (Q17, also needs ESMCI #50) |
| 10 (Dec 29) | | #343 (Q19), with crocontainer #18 and CrocoGallery #63 |

Sprints 3–10 items are issues for unopened PRs: assigned to the user, still Backlog until
their week. Sprints 7–10 were added 2026-10-27 with `updateProjectV2Field`, passing every
existing iteration's id back (that keeps them and their items; verified 17/17 unchanged).
Always pass the existing ids and check the assignments before and after.

**Pacing (user, 2026-10-26): don't open the next PR just because a slot is free.** Wait
for the open ones to merge, and ask before opening anything.

1. **#325 (Q1): wait for it to merge.** 6120f3de added the migration-loop guard and the
   "upgrade CrocoDash" message for newer files. Branches built on its old head 483ad56b
   (Q4, Q6, Q9 and above) rebase with `--onto origin/main 483ad56b`; Q4 also edits
   `case_state.check_version`, so expect a small conflict there.
2. **#326 (Q2) waits for ESMCI #51–#53 (decided 2026-10-26).** Once they merge, bump
   `CrocoDash/visualCaseGen` to ESMCI main on `vcg-case-config` (Q2 + Q18: +242/−1039,
   no local xmlchange helper, CrocoDash's `user_nl_blocks.py`/`cdeps_streams.py` deleted),
   rebase it onto main, and put it on #326's branch (force-push and description update
   need the user's OK). Q18 then no longer exists as its own PR. Rebase Q11–Q17 onto it;
   Q12 imports `user_nl_blocks` from visualCaseGen. #326 is a draft while it waits.
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
| Q1 | C | `config-read` | main | open, changes requested 2026-10-28; review addressed in 7e5e55bb (pushed). Updated description in `prs/Q01-config-read.md` and replies in `prs/Q01-review-replies.md`, both waiting for the user's OK to post | #325 |
| Q2 | — | `writes-name-caseroot` | main, ESMCI #51–#53 | draft, waiting for ESMCI #51–#53; will be replaced by the `vcg-case-config` content (tests pass, codecov/patch red on 2026-10-24; conflicts with #325 only in one case.py import line) | #326 |
| Q3 | T | `time-sampling` | main | draft since 2026-10-26 (opened just before the user said to hold it; mark ready when its turn comes) (38fa7f68) | #327 |
| Q4 | C | `case-from-caseroot` | Q1 | pushed (7fc0c524, on config-read) | |
| Q5 | T | `tseries-time-slice` | Q8 | pushed (64c04e3a, rebased onto time-windows; + IC uses the record at or before the start) | |
| Q6 | T | `typed-freq-inputs` | Q1, Q3 | pushed (81d73d05, on time-sampling + merged config-read) | |
| Q7 | C | `declared-output-files-v2` | Q4 | pushed (e1556bdb, on case-from-caseroot; + `process_forcings(preview=)` 2026-10-26; + input files checked before processing and shown in `--preview` 2026-10-28) | |
| Q8 | T | `time-windows` | Q1, Q6 | pushed (e8ca94cd, on typed-freq-inputs: #305's 4 commits + amendments) | |
| Q9 | — | `forcing-param-specs` | Q1 | pushed (0371a028, on config-read) | |
| Q10 | C | `finished-steps` | Q7 | pushed (9eeb7400, rebased onto e1556bdb 2026-10-28: the input-file check skips finished steps) | |
| Q11 | S | `configure-existing-case` | Q2, Q4 | pushed (499b8e1c, on case-from-caseroot + merged writes-name-caseroot) | |
| Q12 | S | `case-changes` | Q11 | pushed (ab4a5104, on configure-existing-case) | |
| Q14 | S | `forcing-walkthrough` | Q9, Q11 | pushed (5665e3a1, on local merge 1f839164 of Q11+Q9; +382/−17). Now before Q13. Re-cut 2026-10-26: the prompts are the general forcing walkthrough (create/configure/`ask=True`), not fork's | |
| Q13 | S | `bundle-and-create-from` | Q14, Q10, Q12 | pushed (e35016e6, on local merge ff293b36 of Q14+793c3832; +669/−506, most removals the old sharing doc and CLI tests). Re-cut 2026-10-26: `crocodash create --from` replaces fork; fork and duplicate removed | |
| Q15 | S | `drop-shareable` | Q13, MCP moved off shareable | pushed (5862c160, on bundle-and-create-from; pure deletion) | |
| Q16 | — | `interior-obc-segments` | Q7, Q8, Q11 | pushed (d18211d5, on local merge 94c65a44 of Q7+Q11+Q8; worktree `interior-obc-v2`; needs a Derecho run with an interior segment) | |
| Q17 | — | `cyclic-grid-v2` | Q7, Q11, ESMCI #50 | pushed (e3b23b08, on local merge 60bd25cc of Q7+Q11; pins vCG to the #50 head, re-pin to ESMCI main before opening; redo #311's Derecho cyclic run; the original `cyclic-grid` branch/worktree is untouched) | |
| Q19 | S | `yaml-grid-paths` | Q15 | pushed (c266a43b, on drop-shareable; +117/−314). The create config names the grid files; builders removed | |
| Q18 | — | `vcg-case-config` | E1–E3 merged | folded into Q2 (#326) on 2026-10-26; pushed (d8f52205, on writes-name-caseroot; keeps the old vCG pin until E1–E3 merge) | |

**Q18 note:** before opening, bump `CrocoDash/visualCaseGen` to ESMCI main with E1–E3 merged (label `submodule-bump`) and rebase onto main. Locally it was import-checked against `visualCaseGen-worktrees/e123-integration`, a local-only merge of E1+E2+E3 (never push it). Q12's `Case.set_user_nl` must not add to `forcing/user_nl_blocks.py`, which Q18 deletes.

**Merge hazards (found while building, 2026-10-23):**
- **Q7 vs Q8** (`ic.py`, `obc.py`, `mom6.py`): keep Q8's `min_chunk_days`/`lookback_days`/`_function_args()`/`_obc_dates()`, drop every `preview` argument and branch. Resolved this way in 94c65a44.
- **Q6 vs Q11** (`recipe.py` → `Case.forcing_args`): Q6 added the `data_freq`/`subsample_freq` round trip to `recipe.generate_configure_forcing_args`, which Q11 deletes and moves to `Case.forcing_args()`. Whichever merges second must carry the loop into `Case.forcing_args()` (done in 94c65a44).
- **Q9 vs Q11** (`recipe.py`, `forcing/base.py` registry init): Q9 makes `generate_configure_forcing_args` skip derived inputs and adds the unknown-kwarg warning next to the `case.__dict__` scan; Q11 moves that function to `Case.forcing_args()` and replaces the scan with `forcing_inputs()`. Whichever merges second must make `Case.forcing_args()` skip derived inputs and keep the warning.
- **Q16 vs Q17** (`Case.forcing_inputs()`): each adds one key (`case_supergrid_path`, `case_cyclic_x`); keep both.
- **Q16 vs Q10**: Q16 makes the conditions `_fingerprint` ignore `case_*` inputs; Q10's conditions `step_settings` reuses `_fingerprint`, so it inherits that (wanted: settings stay portable).
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
- **Superseded branches** (kept on origin, not to be opened): `fork-cli-and-prompts` (3825d243) and `bundle-and-fork` (a5c60030), the fork-based Q14/Q13 before the 2026-10-26 re-cut.

**Q5 note (decided 2026-10-23):** Q5 is the last step of stack T (Q3 → Q6 → Q8 → Q5).
Without Q8, monthly CESM data with an IC starting mid-month would error, and monthly OBC
is broken on main either way. Rebase Q5 onto Q8 when Q8 is built; it also shares
`cesm_ocean_output.py` with Q3.

## ESMCI/visualCaseGen

| E | Branch | Needs | Status | PR |
|---|---|---|---|---|
| E1 | `case-tools-caseroot` | — | open (+14717a6: a missing ./xmlchange raises RuntimeError) | ESMCI #51 |
| E2 | `user-nl-blocks` | Q2 built | open | ESMCI #52 |
| E3 | `stream-years` | — | open | ESMCI #53 |

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
