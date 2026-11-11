# Learning pack: conformal grids, gridgen, and Dan's solver (PR #151)

Material for reviewing NCAR/mom6_forge#151 (`Grid.from_outline`, chunk 1 of Dan Amrhein's
#149). Built 2026-11-02 from the code at `db0db39` (#151) and `55e7010b` (#149), the
gridgen-c and pygridgen sources, the literature, and new experiments.

## Reading order

| # | File | What it answers | Time |
|---|---|---|---|
| 0 | [primer.html](primer.html) (published: https://claude.ai/artifact/4UhkcjjCgd9UJwZ1JFjC3j) | **Start here.** The whole idea built from steady tracer diffusion, in plain language, with live demos | 30 min |
| 1 | [01_the_problem.md](01_the_problem.md) | What is being solved, independent of method: conformal maps, the unique grid, the modulus, why Laplace, what the exact map does at corners and bays, what the projection really changes | 30 min |
| 2 | [02_gridgen_method.md](02_gridgen_method.md) | How gridgen does it, from its C source: Schwarz–Christoffel, prevertices, crowding, CRDT, how nodes are made, its bugs | 45 min |
| 3 | [03_dans_method.md](03_dans_method.md) | Dan's solver line by line, with derivations, figures, what #149 adds, and review observations (§15) | 60 min |
| 4 | [04_experiments.md](04_experiments.md) | Does it compute the right map? Exact-answer test, California convergence, refinement, crowding | 30 min |
| 4b | [04b_gridgen_vs_dan.md](04b_gridgen_vs_dan.md) | The same outlines through gridgen and Dan's solver, compared node by node | 20 min |
| 5 | [05_side_by_side.md](05_side_by_side.md) | Both methods in one table, and the consolidated review questions | 15 min |
| 6 | [06_reading_list.md](06_reading_list.md) | Annotated, link-checked papers, books and notes, mapped to the parts of the PR they explain | reference |
| 7 | [07_ocean_grids_and_mom6.md](07_ocean_grids_and_mom6.md) | What MOM6 assumes about orthogonality, tolerances, why every supergrid point must be defined, other ocean grid tools | 20 min |

**Short path (about an hour):** chapter 1 → the "short version" at the top of 2 →
§0 of 3 (the pipeline on one page) → the summaries at the top of 4 and 4b → chapter 5.

## Notebooks (saved without outputs)

| Notebook | Env | Shows |
|---|---|---|
| [walkthrough_dans_solver.ipynb](walkthrough_dans_solver.ipynb) | `dev_mf` | each solver stage on a trapezoid and California: mesh, ξ/η fields, the mesh in (ξ, η) space, grid, quality maps |
| [experiments.ipynb](experiments.ipynb) | `dev_mf` | everything in chapter 4 (about 4 min) |
| [gridgen_vs_dan.ipynb](gridgen_vs_dan.ipynb) | `dev_gridgen` | everything in chapter 4b |
| [projection_invariance.ipynb](projection_invariance.ipynb) | `dev_mf` | the projection experiment in 01 §1.7 |

The `dev_mf` notebooks put the #151 worktree first on `sys.path` themselves.
`dev_gridgen` (`/glade/work/manishrv/conda-envs/dev_gridgen`) has pygridgen 0.3.0 from
conda-forge, with `setuptools<81` pinned because pygridgen still imports `pkg_resources`.
Source checkouts of gridgen-c (`222cc71`) and pygridgen (`18d78c7`) are in
[../external/](../external/), git-ignored.

Figures are in [figures/](figures/): `pipeline_*` (chapter 3), `exp_*` (chapter 4),
`cmp_*` (chapter 4b).

## The ideas in five lines
1. An outline with 4 corners has exactly one conformal map onto a rectangle; its aspect
   ratio (the conformal modulus) is forced by the shape. That map *is* the grid.
2. gridgen writes the map as a Schwarz–Christoffel formula and solves a nonlinear problem
   for its constants. Dan solves the equivalent Laplace problem (Dirichlet on two sides, zero
   flux on the other two) with linear finite elements. The CRDT paper itself (§9) states this
   equivalence.
3. Same target, different errors: gridgen is exact to ~1e-12 but needs CRDT to survive
   crowding; Dan's is approximate to the mesh but simple, linear and crowding-free. Corners
   are the finite-element method's weak spot, which #149's refinement fixes.
4. Tiny or non-convex corner cells, starved bays, and cell-size variation belong to the
   exact map, so both methods have them. Only the outline and corner placement change them.
5. MOM6 needs orthogonal grids with every point defined, so the 4-corner case is the part of
   gridgen that matters, and there is no published orthogonality tolerance for MOM6 (the
   closest guideline, Delft3D, is about 1°).
