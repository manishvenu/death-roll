# 5. gridgen and Dan's solver side by side, and what to raise in review

This chapter pulls together chapters 1–4b and 7. Details and evidence are linked from each
row; nothing here is new measurement.

## 5.1 Same problem

Both compute the unique conformal map of the outline (with its 4 corners) onto a rectangle
(chapter 1). Driscoll & Vavasis, the authors of the CRDT algorithm gridgen runs, say so
directly (1998, §9, p. 1797): mapping a quadrilateral onto a rectangle "is equivalent to
solving Laplace's equation … with the Dirichlet values of 0 and 1 on two generalized sides
separated by two generalized sides with homogeneous Neumann conditions." That sentence is
Dan's formulation. They then solve it with a Schwarz–Christoffel formula; Dan solves the
Laplace problem directly, which is the "conjugate function method" of Hakula, Quach &
Rasila (2013).

## 5.2 Different numerics

| | gridgen (gridgen-c / pygridgen) | Dan's solver (#151 + #149's refinement) |
|---|---|---|
| What is written down | the map as a Schwarz–Christoffel formula, canonical domain → polygon (02 §1.2) | ξ(x, y) and η(x, y) as solutions of Laplace's equation (03 §7) |
| Unknowns | n − 3 log cross-ratios, one per diagonal of a Delaunay triangulation of the polygon's vertices (02 §1.7) | ξ and η at every node of a ~250k-node mesh fitted to the outline (03 §5) |
| Solve | nonlinear: fixed-point or Broyden iteration, no iteration cap, convergence not proven (02 §2.4) | two sparse linear solves (03 §7) |
| Modulus | from the solved image region; printed as width/height with `-v` (02 §2.6) | $\sqrt{E_\xi/E_\eta}$ = ny/nx; the energies bracket it, $1/E_\eta \le M \le E_\xi$ (03 §8) |
| nx, ny | chosen by the user, as node counts; README states the direction backwards (02 §2.6, 04b) | chosen automatically for square cells from `n_cells` or `resolution_km` |
| How grid nodes are made | invert the image map at each lattice node (secant, DOPRI8 ODE fallback), then evaluate the physical SC integral, in the local map of the quadrilateral the node falls in (02 §2.4) | barycentric interpolation of (x, y) over the mesh's triangles in (ξ, η) space (`_sample`), then snap the edges onto the outline and pin the corners (03 §9–10) |
| Boundary fit | on the coastline by construction | snapped onto the outline explicitly |
| Corners and reflex vertices | singularities built into the formula exactly | approximated; slow convergence there without #149's refinement (04 §4.3) |
| Elongated domains | prevertices crowd: the best-case gap is about $8e^{-\pi L/2}$, so plain SC fails near L ≈ 24 in double precision; CRDT's per-quadrilateral maps fix this (04 §4.4) | no crowding: curved channels from L = 5 to 50 solve to ~1e-9 modulus error (04 §4.4) |
| Accuracy on smooth exact cases | ~1e-12 (solver tolerance) | node and orthogonality errors ∝ h², modulus ∝ h³; at 250k points, 4.6e-4 cells and 0.012° on the annulus (04 §4.1) |
| Cost driver | number of polygon vertices (each is an unknown and a singularity; hence `thin`) | number of mesh points; also linear in outline vertices through `shapely.distance` (04 §4.2) |
| Code | ~3,000 lines of numerical C plus Triangle (650 KB) | ~250 lines of core numpy/scipy |
| Maintenance | pygridgen last pushed 2024-10; needs `setuptools<81` to import today | part of mom6_forge |
| Extras | −1 corners (non-rectangular images, NaN-masked nodes), `focus` / `grid` stretching | none yet; ±1 corners "being worked on separately" per #149 |
| Known bugs | pygridgen's `nppe` ignored; `nnnodes` typo in examples; `abs()` on a complex value (02 §2.8) | see §5.4 |

**Bottom line.** gridgen is more exact, Dan's is simpler and more robust. On smooth
4-corner outlines they give the same grid to about 1/1000 of a cell (chapter 4b). At sharp
corners #151 alone falls well short of gridgen, and #149's refinement closes most of that
gap.

## 5.3 Head-to-head results (chapter 4b)

The same polygons in the same plane, with matched orientation and node counts. Distances
are in units of the local cell size.

| Case | Modulus, Dan (250k) vs gridgen | Dan − gridgen nodes, max / RMS | Against the exact answer |
|---|---|---|---|
| Rectangle | 4e-14 | 3e-10 / – | both exact |
| Trapezoid | 1.3e-9 | 8.7e-4 / 1.6e-5 | (no exact answer) |
| Annulus sector, 2:1 | 1.2e-7 | 2.6e-4 / 5.9e-5 | both 8.6e-4, the floor set by drawing arcs as chords |
| Annulus sector, 22:1 | 1.5e-8 | 2.1e-4 / 3.0e-5 | both 1.7e-3, same floor |
| California, #151 | 4.1e-5 | 4.3 / 0.12 (worst: 15.7 km, next to the 204° corner) | (no exact answer) |
| California, #149 refined | 3.8e-7 | – / 0.0077 | (no exact answer) |

Orthogonality on California, interior p99 / max, and the maximum near the 186° / 204°
corners:

| Solver | interior p99 / max | near 186° / 204° |
|---|---|---|
| #151 | 2.6° / 40° | 21° / 40° |
| #149 refined | 0.36° / 7.7° | 2.7° / 7.7° |
| gridgen | 0.16° / 3.1° | 0.15° / 0.79° |

What this says:
- **On smooth outlines the two methods agree to about 1/1000 of a cell**, and the gap
  shrinks at second order as Dan's mesh is refined. So the finite-element method computes
  the right map.
- **California is where #151 falls short, and the cause is the missing corner
  refinement.** #151 is 0.12 cells RMS off gridgen. #149's refinement brings that to
  0.008, with the modulus within 4e-7. Refinement doesn't close the gap entirely next to
  the obtuse corners (7.7° against gridgen's 0.79°).
- **gridgen did not converge on the 22:1 sector** at its default precision (1e-12). Its
  residual stalls between about 1e-11 and 1e-8, and the C loop has no iteration cap.
  - One run hit "F(): NaN detected" and called `exit(1)`, which kills the Python process,
    so a Jupyter kernel would die.
  - Moving vertices by about 1 nm usually lets it converge, and `precision=1e-8` works.
  - Dan's solver had no trouble on the same polygon.
- **Speed is similar for these outlines.** Dan takes 2–3 s at 250k points, whatever the
  outline. gridgen takes 2 s for the rectangle and trapezoid, 7 s for California, and
  44–89 s for the many-vertex sectors.

## 5.4 What to raise in review

Each item says where the evidence is. "Verified" means it was reproduced by running code.

**Correctness and robustness (#151 as it stands)**

1. **Self-intersection is checked in lon/lat, but the mesh is built in the projected
   plane** ([_conformal.py:362](../../../regional_mom_workflows/mom6_forge-worktrees/conformal-solver/mom6_forge/_conformal.py#L362)).
   A 60–70°N box with a narrow notch is simple in lon/lat, self-intersects in LCC,
   transverse Mercator and stereographic, and `solve` returns about 700 folded cells out of
   2,000 without raising. Fix: check `is_simple(x, y)` after projecting. *Verified (03 §15).*
2. **The boundary band is not a constrained triangulation**, so bent land features narrower
   than about h/3 get bridged. A 0.2 km zig-zag spit at h = 3.2 km gives a 21% aspect error
   and folded cells. Straight inlets are safe; California is clean even at h ≈ 17 km. It
   matters mainly for coarse meshes (the 20k preview, `size_ratios`' 1k solves).
   *Verified (03 §15, `figures/pipeline_bridging.png`).*
3. **Without refinement, cells near obtuse corners and reflex vertices are badly skewed.**
   California: worst node 34.1° off square at build resolution, 45.7° in the preview,
   against 3.0° and 4.0° with #149's refinement. The extra skew sits mainly at the obtuse
   grid corners. MOM6 drops non-orthogonal metric terms and never checks orthogonality,
   and the nearest published guideline (Delft3D) is about 1°. Against gridgen, #151's
   California grid is 0.12 cells RMS off, and #149's refined solver is 0.008. Suggest
   shipping PR 2b together with #151, or right after it, rather than as an optional extra.
   *Verified (04 §4.3, 04b, 07 §2).*
4. **The "auto" projection.** `Grid.from_outline` (via `size_ratios`) and `cf.solve`
   (via `projection_for`) pick different projections and different grids for California
   (Mercator 63×188 against LCC 63×193). With the outline's edges densified along
   geodesics, all four projections give the same grid (aspect to 4 digits, nodes to
   metres), and the coarse `size_ratios` ranking is noise. Suggest defining edges
   independently of projection (densify along geodesics before projecting), picking the
   projection by a simple rule, and keeping polar stereographic for outlines round a pole.
   *Verified (01 §1.7, `projection_invariance.ipynb`, 03 §15).*
5. **Corners far from 90° make tiny or non-convex corner cells.** California puts corners at
   186° and 204°: those corner cells are non-convex and ~10× smaller than the median, so
   they set the CFL step. This belongs to the exact map, not the solver. #149 had a "nearly
   flat" warning; consider warning or refusing beyond some angle. *Verified (01 §1.8).*
6. **Solve time grows linearly with outline vertex count** (`shapely.distance` from every
   lattice point to the ring, no spatial index): 2.4 s at 130 vertices, 20 s at 8,194, at
   250k points. Relevant for outlines traced from detailed coastlines. *Verified (04 §4.2).*

**Claims and docs**

7. **"Cells are orthogonal by construction"** (#149 commit `d357c62`) holds only to
   discretisation accuracy. Away from the outline, the refined grid's remaining
   0.46°/3.0° (p99/max on California, measured with the tests' `_ortho`, which skips
   nodes near the outline) is mostly the discrete cells of the exact map at that cell
   count. It doesn't change from 80k to 1M mesh points but falls as cells are added
   (04 §4.3). Right next to the obtuse corners, refined Dan still reaches 7.7° where gridgen
   has 0.79° (04b). Suggested wording: "orthogonal to discretisation accuracy", reporting
   $E_\xi E_\eta - 1$ as the error measure.
8. **Cite the method that is actually used.** The module docstring cites gridgen and the
   Schwarz–Christoffel papers only. Add Hakula, Quach & Rasila (2013) and the
   Driscoll–Vavasis §9 equivalence (06 §5).
9. **Leftovers from trimming #149:** the `ConformalGrid.h` docstring says "finer round
   singular vertices" (L282); a `# --- land ---` heading with no tests under it
   (`tests/test_conformal.py` L286); a bare `except Exception` in `size_ratios` (L614).
10. **ROADMAP correction (ours, not Dan's):** "Build does too (62 spots)" is the cap;
    California refines 8 vertices (03 §14).

**Design questions for Dan**

11. Why finite elements rather than a Schwarz–Christoffel port: the compiled dependency,
    crowding, or plans for stretching or islands? (Chapter 4b gives one concrete answer:
    gridgen stalled or crashed on a 22:1 curved channel that Dan's solver handled.)
12. What is the MOM6 use case for ±1 corners, and how would the area outside a
    non-rectangular image be filled, given MOM6 needs every supergrid point (07 §3)?
13. Stretching is cheap in this method: any separate stretch $\xi' = g(\xi)$,
    $\eta' = h(\eta)$ keeps the grid orthogonal. `_sample` would need a non-uniform
    sampler (02 §2.7, §6). Worth a later chunk?
14. The nearest-node fallback in `solve` never fired in any test, including bridged meshes
    (03 §15). Should it raise instead, as gridgen writes NaN?

## 5.5 What is still open
- No MOM6-specific orthogonality tolerance exists in the docs or literature (07 §6).
- The bridging threshold (bent features narrower than about h/3) is empirical: 2 shapes,
  4 rotations, 3–4 mesh sizes.
