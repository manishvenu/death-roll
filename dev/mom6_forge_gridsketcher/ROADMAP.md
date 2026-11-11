# Roadmap: breaking up mom6_forge PR #149 (GridSketcher) into reviewable PRs

## Context
NCAR/mom6_forge#149 (Dan Amrhein, branch `amrhein:gridsketcher`, head `55e7010b`) is
6,275 added lines in 22 files and 21 commits. It adds a conformal orthogonal grid
generator (`Grid.from_outline`), grid-quality diagnostics, a TopoEditor overlay for open
boundaries, and a large ipywidgets map editor (GridSketcher). Nobody can review it as one
PR. The plan is to re-cut it into a series of small, stacked PRs, starting with the math,
and work through them over the next few weeks.

Decisions so far:
- Each chunk is a branch off `origin/main` (or off the chunk before it), built in its own
  mom6_forge worktree under `regional_mom_workflows/mom6_forge-worktrees/`. The main
  checkout (currently on `fix-polar-bathymetry-seam`) is never touched.
- **Review-then-hand-off flow:**
  - Manish cuts each chunk as an ordinary commit under his own identity. Setting Dan as the
    author would cause attribution and authentication trouble.
  - Each chunk opens as a **draft PR** for Manish's own review. It credits Dan and links
    #149.
  - Once Manish has reviewed a chunk, he closes his PR. Dan then reopens the same cut from
    his own fork and branch, so the final authorship is his.
  - No Claude co-author lines.
- Code is pulled from the #149 head with `git show 55e7010b:<path>` and then trimmed.
  Nothing is cherry-picked, because the 21 commits interleave all the features.
- Nothing is pushed and no PR is opened without explicit approval each time.
- black runs on every chunk. Verification runs through CI on push; local pytest only on
  request.
- When the series lands, #149 is closed as superseded, with Dan's agreement.

## Size breakdown of #149
| Area | Lines | Files |
|---|---|---|
| Widget | 1,891 | `grid_sketcher.py` |
| Widget tests | ~1,630 | `test_grid_sketcher*.py`, `_ipympl_worker.py` |
| Conformal solver | 696 | `_conformal.py` |
| Its tests | 365 | `test_conformal.py` |
| Diagnostics | 515 | `corner_diagnostics.py` |
| Diagnostics tests | 333 | `test_corner_diagnostics.py` |
| Grid API and supergrid | ~140 | `grid.py`, `_supergrid.py` |
| TopoEditor overlay | ~40 + 86 tests | `topo_editor.py` |
| Docs and notebook | ~350 | |

---

## PR 1: dx/dy haversine fix (#145, already open)
- `_supergrid.py`: `_is_rectilinear_lonlat`, plus the fallback in `_calc_dx_dy_checked`.
- It is commit 1 of #149. Review and merge #145 first, since every later chunk sits on top
  of it.

## PR 2: the conformal solver, without corner refinement (the math) ← IN PROGRESS
**Status (2026-10-06):**
- Built in worktree `mom6_forge-worktrees/conformal-solver`, branch `conformal-solver`,
  stacked on #145's head `3a2a002`.
- 1,211 added lines in 6 files. black is clean; the smoke check of `from_outline` and
  `write_supergrid` passes.
- Committed as `db0db39`, pushed to `origin/conformal-solver`, and opened as draft PR **NCAR/mom6_forge#151** (review only). CI runs the tests.
- Changes to tests versus #149:
  - a local `_ortho(cg)` helper replaces `diag.grid_quality` and `diag.cell_metrics`;
  - `cf._cell_geometry` is used for cell sizes;
  - the California test no longer asserts the "nearly flat" warning or `ortho_max < 5`
    (both return in PR 2b or PR 3).
Branch `conformal-solver`, off `main` after #145 merges (or stacked on #145 until then).

**`mom6_forge/_conformal.py`**, taken from #149 and trimmed:
- Keep:
  - the `MapProjection` dataclass, `projection_for`, `as_projection`, `unwrap_lon`,
    `_pole_contained` and `_lon_steps`;
  - the polygon helpers: `_signed_area`, `is_simple`, `orient_ccw`, `interior_angles`,
    `order_corners`;
  - `ConformalGrid`, `outline_area_km2`, `n_cells_for_resolution`,
    `nominal_resolution_km` and `_validate_and_orient`;
  - `_sides`, `_mesh`, `_stiffness`, `_harmonic`, `_solve_mesh`, `_sample` and `solve`.
- Strip corner refinement:
  - remove `_spots`, `_levels` and `REFINE`;
  - `_sides` spaces its points h apart;
  - `_mesh` drops the fine-disc loop and the `ds` and `level` masks;
  - `_solve_mesh` drops the `spots` argument.
- Move `size_ratios` and `_cell_geometry` here from `corner_diagnostics.py`, so
  `projection="auto"` works without the diagnostics module.
- Leave out `solve_fields` (widget preview), `land_window`, `land_polygons`,
  `_land_geometry` and `PREVIEW_RASTER_POINTS`.

**`mom6_forge/grid.py`:**
- `Grid.from_lonlat_arrays`.
- `Grid.from_outline`, which uses `cf.size_ratios` instead of the `corner_diagnostics`
  import.
- `_from_conformal`. It sets `grid.outline` in memory only; the JSON persistence through
  `write_supergrid` waits for PR 5.

**Tests:**
- `tests/test_conformal.py`, from #149, without:
  - the three `land_*` tests;
  - `test_solve_fields_is_the_first_half_of_solve`;
  - `test_a_reflex_grid_corner_folds_no_cell`;
  - `test_many_reflex_vertices_keep_the_preview_mesh_small`.
  Loosen or mark xfail the reflex assertions in `test_california_cell_count_reflex_corners_and_outline_fit`.
- The `from_outline` and `from_lonlat_arrays` tests from #149's `tests/test_grid.py`.
- `tests/data/california_bays.outline.json` and its `conftest.py` fixture.

**Docs:** the API page entry for `_conformal`, if public, and a short `from_outline`
example in `widgets.md`, or in a grids page if that fits better.

**Expected size:** about 550 source lines and 350 test lines.

### Why corner refinement is a separate PR (PR 2b)
- **Where the fields break down:** the solver finds ξ and η as harmonic functions on the
  outline. At a vertex whose interior angle α is bigger than the "smooth" angle (90° at a
  grid corner, 180° anywhere else), the solution is singular, with gradient ~ r^(π/α − 1).
  That happens at a reflex vertex where the outline juts into the domain, such as a
  headland or bay mouth, or at an obtuse corner.
- **What a uniform mesh gets wrong there:** linear (P1) finite elements on a uniform mesh
  converge slowly near such a point. That error affects two things:
  - the Dirichlet energies, which set the aspect ratio and so nx/ny;
  - ξ and η near the vertex. They can stop being monotone there, so inverting the map
    folds or tangles cells.
- **What refinement does:** `_spots`/`_levels` halve the mesh spacing up to 5 times
  within about 6h of the sharpest vertices.
- **Who doesn't need it:** a convex outline (boxes, simple quads, every corner ≤ 90°)
  never refines. Meshes under 4,000 raster points don't refine either. The 20k-point
  preview does refine (5 spots), and Build does too (62 spots).
- **Measured on 2026-10-06** (Dan's `55e7010b` vs the trimmed solver; node orthogonality
  is the deviation from 90° at interior nodes):

  | case | refined p99 / max | unrefined p99 / max | folds |
  |---|---|---|---|
  | California, preview 20k | 0.56° / 4.0° | 5.5° / 45.7° | 0 / 0 |
  | California, build 250k | 0.46° / 3.0° | 2.3° / 34.1° | 0 / 0 |
  | reflex ring round pole | 3.0° / 50.0° | 29.8° / 50.6° | 0 / 0 |
  | plain lon/lat box | 0.03° / 0.33° | identical | 0 / 0 |

  Without refinement no cells fold, but the cells next to reflex corners are badly
  skewed. Use this table as the motivation in PR 2b.
- So PR 2 ships the clean algorithm, and PR 2b adds refinement with the tests that show
  why it is needed.

## PR 2b: mesh refinement at singular corners
- Restore `_spots`, `_levels`, `REFINE`, and the fine-disc and level masks in `_sides` and
  `_mesh`.
- Restore `test_a_reflex_grid_corner_folds_no_cell`,
  `test_many_reflex_vertices_keep_the_preview_mesh_small`, and the full California reflex
  assertions.
- Include a before/after figure in the PR description: cell folds at a reflex corner, with
  and without refinement.

## PR 3: grid diagnostics (`corner_diagnostics.py`)
- The rest of the module:
  - `cell_metrics` and `grid_quality` (size ratio, aspect, orthogonality, neighbour
    ratio);
  - `ocean_mask` and `timestep_limits` (CFL hints);
  - `open_boundary_runs` and `OBC_SIDES`;
  - `warnings` and `quality_messages`.
- `size_ratios` and `_cell_geometry` now live in `_conformal`, so import them from there.
- `tests/test_corner_diagnostics.py`.
- Consider renaming to `grid_diagnostics.py`, since most of it works on any `Grid`.

## PR 4: TopoEditor open-boundary overlay
- Covers `topo_editor.py`: the `open_boundaries=False` keyword, the `open_boundaries`
  property and `_update_open_boundaries`.
- Adds the #149 additions to `tests/test_topo_editor.py`.
- Depends on PR 3. Small, and useful to CrocoDash on its own, because it feeds
  `configure_forcings(boundaries=...)`.

## PR 5: GridSketcher core
- `grid_sketcher.py`, reduced to:
  - drawing points, dragging, inserting on an edge, deleting with right-click, toggling a
    corner with double-click;
  - Undo/Redo and Clear;
  - the live preview, the projection buttons with the recommended one outlined, and
    Build and Save;
  - error and warning lists.
- Brings back `solve_fields`, `PREVIEW_RASTER_POINTS`, `land_window`, `land_polygons` and
  `_land_geometry` into `_conformal.py`.
- `outline` JSON persistence: `write_supergrid` writes the `outline` attribute and
  `from_supergrid_ds` reads it, so the sketcher can reopen a grid. Also the
  `test_supergrid.py` additions.
- The matching subset of `test_grid_sketcher.py`.
- Aim for a widget under about 900 lines. Anything not listed above goes to PR 6.

## PR 6: GridSketcher extras (each optional, possibly several PRs or dropped)
- Orthographic globe and re-centring after a long pan (`test_grid_sketcher_globe.py`).
- Draw Box, the move and rotate handles, and Shift-drag to scale.
- Bathymetry and mean-SSH contour overlays, with checkboxes and level sliders.
- Timestamped status history, and boxing flagged cells too small to see.
- The ipympl real-browser harness (`_ipympl_worker.py`, `test_grid_sketcher_ipympl.py`).
  It is worth keeping if the widget sticks around, but it is heavy.

## PR 7: docs and notebook
- The GridSketcher and acknowledgements sections of `widgets.md`, the notebook
  `9_corner_grid_sketcher.ipynb`, the `notebooks.md` entry, `api/mom6_forge.rst` and the
  `contributing.md` changes.
- Docs for each earlier chunk ship with that chunk. This PR only covers the widget
  walkthrough.

## Dependency graph
```
#145 ─► PR2 solver ─┬─► PR2b refinement
                    ├─► PR3 diagnostics ─┬─► PR4 TopoEditor overlay
                    │                    └─► PR5 GridSketcher core ─► PR6 extras ─► PR7 docs
```

## Execution steps for PR 2 (next session)
0. Copy this roadmap to `croc/dev/mom6_forge_gridsketcher/ROADMAP.md`, so it lives with
   the dev notes and can be ticked off.
1. `git fetch origin && git fetch https://github.com/amrhein/mom6_forge gridsketcher`
   to get `55e7010b`.
2. Create the worktree:
   `git worktree add ../mom6_forge-worktrees/conformal-solver -b conformal-solver origin/main`.
   If #145 is still open, stack the branch on its branch instead.
3. Pull each file with `git show 55e7010b:<path> > <path>`, then trim it as listed under
   PR 2.
4. Run `black mom6_forge/ tests/`.
5. Commit as Manish, with "Extracted from #149 by Dan Amrhein" in the message and no
   Claude co-author line. Ask before committing.
6. Ask before pushing, then open a **draft** PR for review only. It links #149 and #145
   and states that corner refinement is deferred to PR 2b.
7. After review, close the draft PR and hand Dan the branch name and the review notes,
   so he can reopen it from his fork.

## Verification for each chunk
- `git diff origin/main --stat` matches the expected size, and no widget imports remain
  in PR 2 or PR 3. Check with grep for `ipywidgets`, `cartopy.feature` and `GridSketcher`.
- A quick smoke run in the `mom6_forge` env:
  `Grid.from_outline(lon, lat, resolution_km=10)` on a lon/lat box and on the California
  outline. Check the grid shape, that dx and dy are positive, and that `write_supergrid`
  succeeds.
- Run the chunk's own test file once, only if Manish asks. Otherwise CI covers it on push.
- For PR 4 and PR 5, try them by hand in JupyterLab.

## User requests to take up after the core merges

NCAR/mom6_forge#154 (Melissa Moulton, 2026-10-13):
- a high-resolution coastline and GEBCO depth contours in the viewer, toggled on once zoomed in;
- grid sizes under 0.1 km;
- a satellite image layer (cartopy WMTS: BlueMarble_NextGeneration, or MODIS true colour with a date), in GridSketcher or the TopoEditor; separately, a river editor for moving river mouths on high-resolution grids.
