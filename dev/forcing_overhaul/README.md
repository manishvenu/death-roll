# Forcing overhaul

This folder tracks the CrocoDash forcing overhaul. Its goals:
- forcing that is genuinely configurable;
- a `Case` that can be read back from its caseroot and do everything;
- `shareable.py` deleted, with `crocodash create --from` replacing fork and duplicate;
- prompts for every forcing input, in create and configure;
- a create config that is just `Case()`'s and `configure_forcings()`'s arguments, with
  grids as files;
- CESM-case configuration moved into visualCaseGen.

| File | What it is |
|---|---|
| `GAINS.md` | What users and developers gain. Start here. |
| `DESIGN.md` | Decisions, names, target end state, testing policy, stacks, risks. |
| `QUEUE.md` | Status of every PR in the series: the single source of truth. |
| `QUEUE_DETAIL.md` | Each PR's scope, test budget and dependencies, plus the real-case checks. |
| `prs/QNN-<branch>.md` | Each PR's drafted title and body, written when the branch is built. |
| `research/` | The investigation: 6 code reports, 3 competing designs, 2 critiques, and `final-synthesis.md`. |

## How the queue works

- **Only PRs ready for review are open on GitHub**, at most 2 from the CrocoDash queue.
  Tiny PRs (under ~50 lines) and PRs blocked on another repo don't count toward the 2.
  Everything else is a built branch, pushed to origin with no PR, plus a drafted body in
  `prs/`.
- **Opening a PR is one command:**
  `gh pr create --base main --head <branch> --body-file prs/QNN-<branch>.md`
  (run `module load gh` first).
- **When a PR merges** (main squash-merges):
  1. rebase that stack's next branch onto main:
     `git rebase --onto origin/main <old-base> <branch> --update-refs`;
  2. run black (`dev_tools/black_CrocoDash.sh`) and an import check;
  3. re-push;
  4. update `QUEUE.md`;
  5. open the next PR.
- **Every branch is already built and pushed** (decided 2026-10-23). A review change to an
  early PR means rebasing the branches above it; `QUEUE.md`'s merge hazards say where
  they conflict.
- **The visualCaseGen PRs (E1–E3) open together on ESMCI.** They are independent of each
  other.
- **Branches live in worktrees** (see "Where things are" below). The main CrocoDash
  checkout is never used for this work.

## Resuming in a new session

Read `QUEUE.md` first. Its "Next actions" list says what to do now. For the PR you're
working on, read its body in `prs/` and its row in `QUEUE_DETAIL.md`. `DESIGN.md` holds the
decisions; don't reopen them.

**Permissions** (from the user, 2026-10-23):
- Committing and pushing this effort's queue branches is allowed without asking.
- Opening, closing or retargeting a PR, or editing a PR description, needs the user's OK
  each time.
- Never merge into CrocoDash main. No Co-Authored-By lines. No @-mentions in PR text.
- Don't run pytest unless asked; CI runs when a PR opens. Use the `dev_cd` conda env for
  black and import checks.

**Where things are:**
- **CrocoDash branches:** `regional_mom_workflows/CrocoDash-worktrees/<dir>`. Most
  directories are named after their branch, except these:

  | Directory | Holds | Use it for |
  |---|---|---|
  | `interior-obc-v2` | `interior-obc-segments` | Q16 |
  | `interior-obc-segments` | `interior-obc-new` (old #269) | nothing; keep |
  | `cyclic-grid` | `cyclic-grid` (old #311) | nothing; keep |
  | `product-time-sampling`, `cesm-tseries-time-slice` | old #306 branches | nothing |
  | `fork-cli-and-prompts`, `bundle-and-fork` | the fork-based Q14/Q13, superseded 2026-10-26 | nothing; use `forcing-walkthrough` and `bundle-and-create-from` |

- **visualCaseGen (ESMCI) branches:** `regional_mom_workflows/visualCaseGen-worktrees/<branch>`.
  `e123-integration` is a local-only merge of E1–E3 for import checks; never push it.
- **crocontainer:** `regional_mom_workflows/crocontainer-worktrees/<branch>`:
  `fork-new-bundle` (C1, merged) and `grid-files` (C2).
- **CrocoGallery:** `regional_mom_workflows/gallery-worktrees/crocodash-cli-overhaul` (G1).
- **Closed PR heads:** local `parked/<branch>` branches in the main CrocoDash clone
  (listed in `QUEUE.md`).

**Q19** sits on Q15's branch, not a merge; QUEUE.md gives its rebase.

**Branches built on local merges** (Q13, Q14, Q16, Q17): `QUEUE.md` gives each one's base
merge commit. Once the branches in that merge land on main,
`git rebase --onto origin/main <merge commit> <branch>` keeps only the branch's own
commits. rerere is on, so earlier conflict resolutions are reused.

## Testing policy (short)

- **One test per guarantee.** Name the bug a test catches before adding it.
- **No change-detector tests.**
- **Extend existing test files** with tiny inline data and mocked CIME; nothing that
  matters goes behind `slow`.
- **Tests stay a minority of each PR.**
- **Real-case checks** are listed per stack in `QUEUE_DETAIL.md` and run by hand once.
