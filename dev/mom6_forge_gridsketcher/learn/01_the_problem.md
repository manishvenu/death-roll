# 1. What are we solving for?

This chapter is about the *problem*, not about either algorithm. gridgen and Dan's
solver are two ways of computing the same mathematical object, and most of the
confusing behaviour (tiny corner cells, starved bays, the "auto" projection) belongs to
that object, not to either code. Chapters 2 and 3 cover how each method computes it.

All numbers here were measured on PR #151's code (worktree `conformal-solver`, head
`db0db39`) with the California test outline
(`tests/data/california_bays.outline.json`: 30 vertices, corners `[0, 6, 22, 29]`).

---

## 1.1 A grid is a map

A structured grid is a smooth map from a logical rectangle to the physical region, sampled
at regular points:

$$
(\xi, \eta) \in [0,1]\times[0,1] \;\longmapsto\; (x, y) \in \text{region}.
$$

Grid node $(i, j)$ is the image of $(\xi, \eta) = (i/n_x,\ j/n_y)$. A MOM6 supergrid
(`ocean_hgrid.nc`, shape $(2n_y+1, 2n_x+1)$) samples the same map at half steps, so
tracer points are $(\xi,\eta) = ((i+\tfrac12)/n_x, (j+\tfrac12)/n_y)$.

Grid quality is a property of the map's Jacobian. Write the local stretching factors

$$
h_\xi = \left|\frac{\partial \mathbf{x}}{\partial \xi}\right|,\qquad
h_\eta = \left|\frac{\partial \mathbf{x}}{\partial \eta}\right| .
$$

Then a cell's size is $dx \approx h_\xi\,\Delta\xi$ by $dy \approx h_\eta\,\Delta\eta$ (these
are MOM6's `dx`, `dy`). Two properties matter:

| Property | Condition on the map | What it means for cells |
|---|---|---|
| **Orthogonal** | $\partial_\xi \mathbf{x} \perp \partial_\eta \mathbf{x}$ everywhere | grid lines cross at 90°; cells are rectangles |
| **Conformal** | orthogonal *and* $h_\xi\,\Delta\xi = h_\eta\,\Delta\eta$ | cells are squares; their size may still vary |

MOM6 writes its equations in orthogonal curvilinear coordinates, so orthogonality is the
requirement (see `07_ocean_grids_and_mom6.md`). Conformal is the special orthogonal grid
with an aspect ratio of 1 in every cell: isotropic resolution, and no direction wastes the
CFL budget.

## 1.2 Conformal = angle-preserving

A map is **conformal** when, at every point, it acts on tiny shapes as a rotation plus a
uniform scaling, with no shear and no one-directional stretch. A tiny square comes out as a
tiny square (rotated, resized); angles between curves are preserved.

In terms of the logical coordinates as functions of position, $\xi(x,y)$ and $\eta(x,y)$,
conformality is the **Cauchy–Riemann equations** (up to a constant scale between ξ and η,
see 1.5):

$$
\xi_x = \eta_y,\qquad \xi_y = -\eta_x
\quad\Longleftrightarrow\quad
\nabla\xi \perp \nabla\eta \ \text{ and }\ |\nabla\xi| = |\nabla\eta| .
$$

Equivalently, $\xi + i\eta$ is an analytic (complex-differentiable) function of
$x + iy$. Examples ocean modellers already use:

- **The Mercator grid.** Mercator's $y = \ln\tan(\pi/4 + \varphi/2)$ makes
  $(\lambda, y) \mapsto$ sphere conformal, so a uniform grid in the Mercator plane is the
  familiar "equal-aspect" grid with $\Delta\varphi = \Delta\lambda\cos\varphi$.
- **Polar stereographic / Lambert conformal conic.** Conformal projections: a square in the
  map is a square on the Earth (only resized).
- **$w = \log z$.** It maps an annulus sector conformally onto a rectangle: radial lines at
  equal angles and circles at *geometrically* spaced radii form a perfect conformal grid.
  (Chapter 4 uses this as an exact test of Dan's solver.)

## 1.3 The quadrilateral problem

The input to `Grid.from_outline` is a closed outline (a polygon on the Earth) with 4
vertices marked as the grid's corners. A region with 4 marked boundary points is called a
**quadrilateral** in this literature, even when its sides are long wiggly coastlines.

The **Riemann mapping theorem** says any simply connected region (no holes) can be mapped
conformally onto a disk. A consequence for quadrilaterals:

> There is exactly one rectangle $[0,1]\times[0,M]$, and exactly one conformal map of the
> quadrilateral onto it that sends the 4 corners to the 4 rectangle corners.

The number $M$ is the **conformal modulus** of the quadrilateral. It is *forced* by the
shape: you can't pick it. Consequences:

- **The grid is unique.** For a given outline, corners and cell count, there is exactly one
  ideal conformal grid. gridgen and Dan's solver both approximate *that* grid; they differ
  only in how accurately and how cheaply.
- **The aspect ratio is not yours to choose.** For square cells, $n_y/n_x$ must equal $M$.
  gridgen's README (item 7) tells you to read the "conformal modulus" from the log and set
  nx, ny to match by hand; Dan's solver does this automatically
  ([_conformal.py:471-475](../../../regional_mom_workflows/mom6_forge-worktrees/conformal-solver/mom6_forge/_conformal.py#L471-L475)).
  If you insist on a different nx/ny, the grid stays orthogonal but its cells become
  rectangles of aspect $M n_x / n_y$.
- **Reciprocity.** Relabel the corners so the sides swap roles (W/E ↔ S/N) and the modulus
  becomes $1/M$. This is the identity behind the accuracy check in 1.5.

## 1.4 Two equivalent ways to describe the same map

**(a) As an analytic function from the rectangle to the region.** For a polygon, any such
map must have the **Schwarz–Christoffel** form, a product of power factors, one per
polygon vertex. Finding it means finding a handful of constants. This is gridgen's route
(chapter 2).

**(b) As two harmonic functions on the region.** The real and imaginary parts of an
analytic function satisfy Laplace's equation, so the logical coordinates satisfy

$$
\nabla^2\xi = 0,\qquad \nabla^2\eta = 0 \quad\text{inside the region.}
$$

This is Dan's route (chapter 3). The boundary conditions come straight from the picture:

```
                N side: eta = 1            (for xi: zero flux)
          ┌───────────────────────────┐
  W side  │  xi contours  |  |  |  |  │  E side
  xi = 0  │  run S -> N   |  |  |  |  │  xi = 1
 (eta:    │  eta contours ─────────── │  (eta:
 0 flux)  │  run W -> E               │  0 flux)
          └───────────────────────────┘
                S side: eta = 0            (for xi: zero flux)
```

- **W and E map to the rectangle's vertical sides**, so $\xi = 0$ on W and $\xi = 1$ on E
  (Dirichlet conditions).
- **S and N map to horizontal sides**, where η is constant. Lines of constant ξ must meet
  them at right angles (the map is conformal), which means $\nabla\xi$ is tangent to the
  side: $\partial\xi/\partial n = 0$ on S and N (a zero-flux, or Neumann, condition).
- **η is the same problem turned 90°**: $\eta = 0$ on S, $\eta = 1$ on N, zero flux on W
  and E.

Physical picture: ξ is the steady temperature of a metal plate whose W edge is held at 0,
E edge at 1, with S and N insulated. The isotherms are the grid lines of constant ξ; the
heat-flow lines, which cross them at right angles, are the lines of constant η.

Strictly, one solve is enough: η is the harmonic conjugate of ξ, rescaled. Dan solves both
because each one gives a coordinate directly, and the pair gives the modulus *and* a free
accuracy check.

## 1.5 How the modulus falls out of an energy

Define the **Dirichlet energy** of a field, $E[u] = \int |\nabla u|^2\, dA$. In the
electrical picture (ξ is a voltage on a sheet of unit conductivity), $E_\xi$ is the sheet's
**conductance** between the W and E electrodes.

**On a rectangle** $W$ long (W→E) and $H$ tall: $\xi = x/W$, so
$E_\xi = (1/W^2)\cdot WH = H/W$; likewise $E_\eta = W/H$.

**On any region:** the Dirichlet energy is unchanged by a conformal change of variables.
If $w = f(z)$ is conformal, $|\nabla_z u|^2 = |f'|^2\,|\nabla_w u|^2$ while
$dA_z = |f'|^{-2}\, dA_w$, and the factors cancel. So the conductance of the physical
region equals that of the rectangle it maps onto:

$$
E_\xi = M,\qquad E_\eta = \frac{1}{M},\qquad E_\xi\,E_\eta = 1 .
$$

Dan's solver computes both energies and takes
$\text{aspect} = \sqrt{E_\xi / E_\eta}$, which equals $M$ exactly in the continuum. Why use
both instead of just $E_\xi$:

- **Finite elements overestimate both energies.** The exact field minimises the energy
  among all fields with the same fixed boundary values (Dirichlet's principle). A
  finite-element solution is the minimiser over a *smaller* set of functions, so its energy
  is at least the true one. Both $E_\xi$ and $E_\eta$ come out a little high, and the ratio
  cancels much of the error.
- **The product is a free error gauge.** $E_\xi E_\eta - 1 \ge 0$ measures discretisation
  error:

| case | mesh | $E_\xi$ | $E_\eta$ | $E_\xi E_\eta$ |
|---|---|---|---|---|
| 1000 × 600 km rectangle | 20k points | 0.600000 | 1.666667 | 1.000000 |
| California | 20k points (preview) | 3.0644 | 0.3281 | 1.0056 |
| California | 250k points (build) | 3.0581 | 0.3275 | 1.0017 |

(The rectangle is exact because a linear field is represented exactly by linear finite
elements.) This is the "reciprocal relation" of Hakula, Rasila and co-authors (reading
list, chapter 6).

## 1.6 From the map to a MOM6 grid

Given $M$ and a target cell count $N = n_x n_y$ (from `resolution_km` or `n_cells`):

$$
n_x = \sqrt{N/M},\qquad n_y = M\,n_x \quad(\text{rounded, at least } 1).
$$

California at 12,000 cells: #151's build mesh gives $M = 3.0556$ and $63 \times 193$.
The converged modulus is $3.05547$ (chapter 4), and $63 M = 192.49$ sits right on the
rounding edge, so the converged grid is $63 \times 192$. A modulus change of 3e-5 flips
$n_y$. Nothing is wrong; just don't treat nx, ny as exact test targets.

Sampling at uniform $(\xi,\eta)$ gives square cells. A cell spans $\Delta\xi = 1/n_x$,
which is a physical width of about $1/(n_x|\nabla\xi|)$, and $\Delta\eta = 1/n_y$, which is
a height of about $1/(n_y|\nabla\eta|)$. With $\xi$ and $\eta$ both running 0 to 1,
conformality means $|\nabla\eta| = |\nabla\xi|/M$, so the height is
$M/(n_y|\nabla\xi|) = 1/(n_x|\nabla\xi|)$, equal to the width.

**Cell size varies like $1/|\nabla\xi|$.** It is small where the field is compressed (the
region narrows) and large where the field is weak (pockets the field barely reaches).

## 1.7 On the Earth: why conformal projections, and what the projection really changes

The solve happens in a flat plane, so the outline is first projected. If the projection is
conformal, then *projection followed by the conformal map* is still conformal: square cells
in the plane are square on the Earth, only resized by the projection's scale factor $k$
(true size = plane size / $k$; `_cell_geometry` divides by $k$). That is why only Lambert
conformal conic, Mercator, transverse Mercator and polar stereographic are allowed.

**A consequence worth knowing for review.** The uniqueness in 1.3 also holds on the sphere
(or ellipsoid): a region of the Earth with 4 corners has exactly one conformal map onto a
rectangle. If $P_1$ and $P_2$ are two conformal projections, solving in either plane must
give the *same* grid on the Earth, provided both planes see the same region. They don't
quite: a straight edge between two outline vertices is a different curve on the Earth in
each projection (a rhumb line in Mercator, something closer to a great circle in Lambert).
So **the projection choice mostly decides how the edges between outline vertices are
drawn**, plus where the discretisation error goes.

Measured on California (3,000 cells, 250k-point mesh; script in
`projection_invariance.ipynb`):

| outline | aspect across lcc / merc / tmerc / stere | node distance from the lcc grid (cells ≈ 10 km) | `size_ratios` (what "auto" uses) |
|---|---|---|---|
| raw, 30 vertices | 3.056 / 2.989 / 3.058 / 3.108 | tmerc: median 0.18 km, max 1.35 km (merc and stere have different nx, ny) | 4.82 / **4.61** / 4.82 / 4.81 → picks merc |
| densified along geodesics every 5 km (566 vertices) | 3.0544 / 3.0545 / 3.0545 / 3.0543 | median 3–20 m, max 0.18–0.44 km | 4.94 / 4.87 / 4.94 / **4.65** → picks stere |

With geodesic edges the four projections give the same grid to within a few percent of a
cell, and the full-resolution cell-size ratios are equal to within 1% (6.67–6.72). The
coarse `size_ratios` estimate (256 cells, 1,000-point mesh) then picks stereographic on
what is essentially noise. For the raw outline, "auto" is in effect choosing which edge
curves you meant.

Review questions this raises:
- Should outline edges have one meaning (geodesics, say) whatever the projection,
  for example by densifying the outline before projecting? The grid would then not depend
  on the projection, and the 4 extra coarse solves in `size_ratios` would add nothing.
- If projection still matters for accuracy (the mesh is uniform in *projected* metres, so
  resolution in true kilometres varies with $k$), is "least cell-size variation from a
  256-cell solve" the right criterion?
- Projection does matter in one way: an outline that encircles a pole can only be solved
  in polar stereographic.

## 1.8 What the exact map does (properties of the problem, not of any method)

These happen to the *exact* conformal grid, so gridgen has them too. A method can compute
them more or less accurately; only moving the corners or editing the outline changes them.

**Grid corners.** Near a corner of interior angle $\alpha$, the map has to open or close
$\alpha$ to 90°. Locally it behaves like $w \approx z^{\,90^\circ/\alpha}$, so the
stretching $|dw/dz| \sim r^{\,90^\circ/\alpha - 1}$:
- **an obtuse corner** ($\alpha > 90°$) gives infinite stretching at the corner: tiny cells;
- **an acute corner** ($\alpha < 90°$) gives zero stretching: large cells;
- **the corner cell keeps the outline's angle.** Its two outer edges lie along the outline.

California places its two east corners on nearly straight parts of the coast:

| corner | outline angle | angle of the corner cell | corner-cell size (median cell 4.1 km) |
|---|---|---|---|
| SW | 86.2° | 86.2° | 8.5 km |
| SE | 185.7° | 185.7° (non-convex) | 0.57 km |
| NE | 203.5° | 203.5° (non-convex) | 0.43 km |
| NW | 80.1° | 80.1° | 11.1 km |

(12,000 cells, build mesh.) The two east corner cells are non-convex and about 10× smaller
than the median cell, so if wet they set the CFL time step. gridgen's README gives the same
advice: put corners where the outline turns by close to a right angle.

**Vertices along a side.** A side maps to a straight edge (180°), so a vertex of angle
$\alpha$ behaves like $z^{\,180^\circ/\alpha}$:
- **reflex vertices** ($\alpha > 180°$, a headland poking into the domain) give tiny cells
  around them;
- **convex kinks** ($\alpha < 180°$) give large cells.

This is also where a finite-element solve is least accurate, which is what #149's corner
refinement (PR 2b) addresses (chapter 3, chapter 4). Note the distinction: refinement
fixes the *orthogonality error* of the computed grid there (a property of the method), not
the small cell sizes (a property of the problem).

**Dead-end bays starve.** The field penetrates a side pocket of width $w$ roughly like
$e^{-\pi d/w}$ at depth $d$. A bay three widths deep sees a field about $10^{-4}$ times
weaker than at its mouth, so its cells are about $10^4$ times larger: the bay gets
essentially no cells. gridgen's −1 corners exist to give such a bay its own arm of the
image. With MOM6's rectangular index space the practical fix is to choose the outline (or
corners) so that bays you care about lie along the main grid direction.

**Overall size variation.** `size_ratios` reports the 99th over the 1st percentile of true
cell size; for California it is about 6.7 at 3,000 cells. Some of that is geometry and
some is the corner singularities, and the corner part grows as the grid is refined, because
the corner cells keep shrinking.

## 1.9 Glossary

| Term | Meaning |
|---|---|
| conformal map | angle-preserving map; locally rotation + uniform scaling |
| orthogonal grid | grid lines cross at 90°; cells may be rectangles |
| quadrilateral | a region with 4 marked boundary points (the grid corners) |
| conformal modulus $M$ | aspect ratio (height/width) of the unique rectangle the quadrilateral maps onto |
| harmonic function | a solution of Laplace's equation $\nabla^2 u = 0$ |
| Dirichlet condition | value fixed on a boundary ($\xi = 0$ on W) |
| Neumann / natural condition | zero normal derivative (zero flux) on a boundary |
| Dirichlet energy | $\int|\nabla u|^2\,dA$; the sheet's conductance |
| Dirichlet principle | the harmonic function has the least energy among functions with the same fixed values |
| harmonic conjugate | the partner $v$ of a harmonic $u$ such that $u + iv$ is analytic |
| Schwarz–Christoffel (SC) map | the formula for conformal maps onto polygons (chapter 2) |
| prevertex | the point in the canonical domain that maps to a polygon vertex (chapter 2) |
| crowding | prevertices bunching exponentially close for elongated regions (chapters 2, 4) |
| P1 finite elements | piecewise-linear functions on triangles (chapter 3) |
| scale factor $k$ | how much a map projection enlarges distances at a point |
| supergrid | MOM6's grid file at twice the resolution, holding corner, edge and centre points |
