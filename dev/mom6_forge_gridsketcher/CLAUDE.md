# mom6_forge GridSketcher / conformal grids (PR #149 split)

Notes and learning material for reviewing Dan Amrhein's NCAR/mom6_forge#149 (GridSketcher:
conformal regional grids from a sketched outline), which is being re-cut into small PRs.

## Files here
- `ROADMAP.md`: the chunk plan (#145 → PR 2 solver = #151 → 2b refinement → 3 diagnostics →
  4 TopoEditor overlay → 5 GridSketcher core → 6 extras → 7 docs), decisions, and the
  measured refined-vs-unrefined orthogonality table. Read it first.
- `learn/`: material for understanding the math. Start at `learn/README.md`.

## Where the code is
| What | Where |
|---|---|
| PR #151 (chunk 1: solver) | worktree `regional_mom_workflows/mom6_forge-worktrees/conformal-solver`, branch `conformal-solver`, head `db0db39` (stacked on #145's `3a2a002`) |
| Solver | `mom6_forge/_conformal.py`; API `Grid.from_outline` in `mom6_forge/grid.py` |
| Tests | `tests/test_conformal.py`, `tests/test_grid.py`, fixture `tests/data/california_bays.outline.json` |
| Full #149 | head `55e7010b` (amrhein fork, branch `gridsketcher`); objects are in the worktree: `git show 55e7010b:<path>` |

Never edit the main mom6_forge checkout (`regional_mom_workflows/mom6_forge`); build each
chunk in its own worktree under `regional_mom_workflows/mom6_forge-worktrees/`.

## Running code against the worktree
```bash
cd regional_mom_workflows/mom6_forge-worktrees/conformal-solver
PYTHONPATH=$PWD ESMFMKFILE=/glade/work/manishrv/conda-envs/dev_mf/lib/esmf.mk \
  conda run -n dev_mf python my_script.py   # check mom6_forge.__file__ is in the worktree
```
In notebooks: `sys.path.insert(0, WORKTREE)` and assert `mom6_forge.__file__`.

## Review flow and rules
- Chunks are cut by Manish under his own identity as **draft, review-only** PRs that credit
  Dan and link #149. After review the draft is closed and Dan reopens the same cut from
  their fork. Dan is never set as commit author. No Claude co-author lines.
- Ask before every commit, push, PR, or GitHub comment. No @-mentions in anything posted.
- black on every chunk; CI runs the tests on push (no local pytest unless asked).

## Established facts (2026-11-02, on `db0db39`)
- #151 itself is purely additive (1,211 lines added, none removed). The only change to existing
  behaviour in the branch is #145's dx/dy haversine fallback for non-rectilinear lon/lat grids.
- California, 12k cells: #151 at 250k gives aspect 3.0556 → 63×193; the converged modulus is
  3.05547 → 63×192 (63·M = 192.49 is on the rounding edge). E_ξ·E_η = 1.0017 (250k mesh), 1.0056 (20k).
  Solve ≈1.9 s. Corner angles 86/186/204/80°; the two east corner cells are non-convex and
  ~10× smaller than the median cell.
- The projection only changes the grid through how edges between vertices are drawn: with
  outline edges densified along geodesics, all four projections give the same grid (aspect to
  4 digits, nodes to metres), and `size_ratios`' coarse ranking is noise
  (`learn/projection_invariance.ipynb`).
- Dan's method is the "conjugate function method" (Hakula, Quach & Rasila 2013); gridgen uses
  Schwarz–Christoffel via CRDT. Same map, different numerics. Dan's PR cites only the gridgen /
  SC papers.
