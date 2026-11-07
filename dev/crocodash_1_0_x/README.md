# CrocoDash 1.0.x bug phase

A bug-fix phase before the 1.1 forcing-overhaul sprints resume (decided 2026-11-06).

- **Board:** org project #10, "CrocoDash 1.0.x"
  (https://github.com/orgs/CROCODILE-CESM/projects/10), with these sprints:
  - Bugs 1: Nov 10;
  - Bugs 2: Nov 17;
  - Audit: Nov 24;
  - Audit 2: Dec 1 (added 2026-11-06 for the audit's 48 findings, plus 13 found by hand after it).
- **1.1:** project #9 is paused, and its Sprints 3–13 moved 4 weeks later (Sprint 3 = Dec 8) (see
  `../forcing_overhaul/QUEUE.md`). #326 and #327 stay open, unmerged, until 1.0.x ships.
- **Release:** v1.0.2 from main. No release branch, no backports.

## Files

- `TRIAGE.md`: every candidate bug, from #9's bug items and the open issues of CrocoDash,
  ESMCI/visualCaseGen, NCAR/mom6_forge and CROCODILE-CESM/regional-mom6. Nothing is added to the
  board or labelled until the list is approved.
- `AUDIT.md`: the Claude audit's report (phase 2).
- `prs/`: drafted PR descriptions.

## Phase 1: CESM output timing (#353)

- **IC:** fixed in 1.0.x by #358, #306's commit 2ac2823f (the record at or before the start).
- **Boundaries: a known issue in 1.0.x (decided 2026-11-06).** Each weekly fetch holds the
  whole year, and the regrid crashes. Cutting chunks to their window needs Q8's window sizing
  and padding, so the fix is 1.1's Q6 + Q8 (#331, #333), first in #9's Sprint 3 (Dec 1).

**Release notes, known issues:** forcing a case from monthly CESM output (FOSI tseries)
builds the initial condition but not the open boundaries; that needs 1.1.

## Phase 2: the audit prompt

Start it in a new Claude Code session in `~/documents/croc`, with `ultracode` in front of the
prompt, after TRIAGE.md is finished. Replace `<SHA>` with main's commit.

```
Audit CrocoDash and its stack (regional-mom6, mom6_forge, visualCaseGen) for correctness
bugs that users would hit. Report only: change no code outside a scratch worktree, commit
nothing, push nothing, take no GitHub action, and use no @-mentions anywhere.

Context: this feeds the "CrocoDash 1.0.x" bug project (CROCODILE-CESM org project #10,
Audit sprint). Another agent manages that track and will file your findings as issues in
the repo each one belongs to, so write every finding as a ready-to-file issue.

Target: CROCODILE-CESM/CrocoDash main at <SHA> (record it in the report). Make your own
worktree: git -C regional_mom_workflows/CrocoDash worktree add
../CrocoDash-worktrees/audit <SHA>, then git submodule update --init --recursive in it.
Never touch the main checkout or the sibling checkouts in regional_mom_workflows/.
Audit the copies pinned inside that worktree, because those are what users get:
CrocoDash/rm6 (regional-mom6), CrocoDash/visualCaseGen, and
CrocoDash/visualCaseGen/external/mom6_forge. Each repo's own main may differ. If a finding is
already fixed there, say so: it then only needs a pin bump.
Environment: conda env dev_cd; export ESMFMKFILE=/glade/work/manishrv/conda-envs/dev_cd/lib/esmf.mk;
PYTHONPATH=<wt>:<wt>/CrocoDash/rm6:<wt>/CrocoDash/visualCaseGen:<wt>/CrocoDash/visualCaseGen/ProConPy:<wt>/CrocoDash/visualCaseGen/external/mom6_forge.

Scope:
- CrocoDash: case.py, cli.py, recipe.py, shareable.py, forcing/*, raw_data_access/*.
- regional-mom6: segments and regridding for open boundaries, initial conditions and tides,
  rotation, and everything else CrocoDash calls.
- mom6_forge: Grid, Topo and VGrid creation, their file writers (supergrid, topog, vgrid,
  ESMF mesh, SCRIP, CICE grid, WW3 inputs), and runoff mapping.
- visualCaseGen: case creation as CrocoDash drives it (CaseCreator, case_tools, and the
  constraints for the compsets CrocoDash uses).
Out of scope: the MCP servers, CrocoGallery and the visualCaseGen GUI widgets.

Skip what's already known. Read first:
- dev/crocodash_1_0_x/TRIAGE.md;
- the open issues of CROCODILE-CESM/CrocoDash, ESMCI/visualCaseGen, NCAR/mom6_forge and
  CROCODILE-CESM/regional-mom6 (`module load gh`, then `gh issue list -R <repo> --state open`);
- dev/forcing_overhaul/QUEUE.md (the 1.1 queue and what it already fixes).
Don't report flaky test hangs or the known pre-existing test failures.

Method: walk the user flows end to end:
- grid, topography and vertical-grid creation, and the files they write;
- Case() creation through visualCaseGen, for CrocoDash's compsets (regional, MARBL, CICE, WW3);
- configure_forcings for each forcing type: conditions, tides, chl, runoff, BGC, CICE, WW3,
  DATM stream years;
- process_forcings, including the regional-mom6 regridding it calls, and its resume and skip;
- CLI create, dump, process, bundle, fork, template;
- YAML recipes;
- config.json round trips.
If you split the work across reviewers, use about six: CrocoDash creation, CLI and recipes;
CrocoDash configure and process; raw data products; regional-mom6; mom6_forge;
visualCaseGen. Then verify each finding.

Look for:
- wrong defaults;
- unit, sign and index errors;
- date, calendar and off-by-one errors;
- longitude, antimeridian and pole handling;
- path handling (relative paths, an inputdir inside the caseroot, non-local cases);
- resume and idempotency that reuse stale files;
- errors that are swallowed or misleading;
- global state shared across cases;
- leaked file handles or processes.

Verify each finding with the smallest repro you can: a Python snippet, synthetic data, the
reference products (reference_ocean / get_reference_ocean_data), or a targeted test function.
Don'ts:
- no large downloads;
- no recursive scans of GLADE or GDEX data directories;
- no case builds or submits;
- don't run the full pytest suite;
- don't write to croc_cases, croc_input or CESM inputdata.
Mark each finding "confirmed by repro" or "from reading only".

Output: dev/crocodash_1_0_x/AUDIT.md, grouped by repo (CrocoDash, regional-mom6, mom6_forge,
visualCaseGen), up to ~15 findings per repo, most severe first. For each:
- issue title, as you would file it;
- the repo it belongs to;
- severity (crash / wrong result / misleading error / cosmetic);
- file:line, as a path in the worktree;
- repro (command, expected vs observed);
- root cause;
- smallest fix;
- confidence;
- whether it is already fixed on that repo's main;
- related issue or PR numbers.
End with the areas you checked and found fine.
```
