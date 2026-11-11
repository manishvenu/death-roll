# 07 — Why orthogonal, and what MOM6 needs from a grid

Context for reviewing [NCAR/mom6_forge#151](https://github.com/NCAR/mom6_forge/pull/151):
what MOM6 assumes about the horizontal grid, how non-orthogonality would show up in a C-grid
model, what MOM6 needs at every supergrid point, and why square cells are worth having. The
annotated sources are in `06_reading_list.md`.

MOM6 source links are pinned to `mom-ocean/MOM6` main at
[`0e9a561`](https://github.com/mom-ocean/MOM6/tree/0e9a5611a9f6c99bfea12665da3a9146183521ee)
(2026-10-07). I read that code myself; quotes are exact. Anything I *infer* rather than read is
labelled **(inference)**.

## Short answers

1. **Does MOM6 assume orthogonal grids? Yes.** The docs say so ("MOM6 uses generalized
   orthogonal curvilinear horizontal coordinates"). The grid pages are titled "Global/Regional
   **Orthogonal** Grids". The code reads only edge lengths, areas and node positions. It has no
   input for the angle between grid lines and never checks it. A skewed grid is simply treated
   as if it were orthogonal, without any warning.
2. **How much skew is tolerable?** I found **no published number for MOM6** (or ROMS). The
   closest hard number is from another orthogonal-curvilinear C-grid model, Delft3D-FLOW:
   $|\cos\theta| < 0.02$ between grid lines, i.e. within about 1.1° of 90°, with larger values
   allowed near closed boundaries. Textbook "a moderate skew is fine" guidance (Thompson et
   al.) is for schemes that *keep* the non-orthogonal metric terms, which MOM6 does not.
3. **Every supergrid point must hold real coordinates.** MOM6 reads `x, y, dx, dy, area` over
   the whole logically rectangular array. Land comes from depth (`MINIMUM_DEPTH` /
   `MASKING_DEPTH`), not from the grid file. Nothing tolerates NaNs. gridgen grids with −1
   corners have NaN nodes, so they are a poor fit for MOM6. The PR's four-corner design
   avoids the problem by construction.
4. **Square cells** give one resolution number per cell. They also give the largest gravity-
   wave time step for a given cell area, and they keep MOM6's viscosity length scale honest.
   MOM6 even has a built-in "ISOTROPIC" Mercator grid built on the same reasoning as the
   PR's nx/ny choice.

---

## 1. What MOM6 says and does about orthogonality

### 1.1 The documentation

- **Notation page** ([mom6.readthedocs.io … Notation](https://mom6.readthedocs.io/en/main/api/generated/pages/Notation.html);
  source [`src/core/_Notation.dox` L9–14](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/core/_Notation.dox#L9-L14)):
  > "MOM6 uses generalized orthogonal curvilinear horizontal coordinates. However, the
  > equations are simpler to write using Cartesian coordinates, and it is very straightforward
  > to generalize the horizontal coordinates using the methods in Chapters 20 and 21 of
  > [Griffies 2004]."

  The book is S. M. Griffies, *Fundamentals of Ocean Climate Models* (Princeton UP, 2004),
  [doi:10.1515/9780691187129](https://doi.org/10.1515/9780691187129). The DOI was checked on
  Crossref; I did not read chapters 20–21.
- **Grid pages.** The docs' Grids section has
  [Global Orthogonal Grids](https://mom6.readthedocs.io/en/main/api/generated/pages/Global_Grids.html)
  and [Regional Orthogonal Grids](https://mom6.readthedocs.io/en/main/api/generated/pages/Regional_Grids.html).
  Both are stubs. The regional page has empty "Map Projections" and "Open Boundary Segments"
  sections (checked in the `.rst` source). So the title is the only statement, but it is
  unambiguous.
- **Model overview** ([`src/core/MOM.F90` L4786–4792](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/core/MOM.F90#L4786-L4792)):
  MOM6 solves the primitive equations in "general orthogonal horizontal coordinates."
- **Coriolis/advection** ([`MOM_CoriolisAdv.F90` L2341–2349](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/core/MOM_CoriolisAdv.F90#L2341-L2349)):
  the Arakawa–Hsu and Sadourny schemes "have been modified to use general orthogonal
  coordinates as described in Arakawa and Lamb, Mon. Wea. Rev. 1981." That paper is
  [doi:10.1175/1520-0493(1981)109<0018:APEAEC>2.0.CO;2](https://doi.org/10.1175/1520-0493(1981)109%3C0018:APEAEC%3E2.0.CO;2)
  (Crossref checked; AMS page blocked my fetch).
- **Discrete grids** ([page](https://mom6.readthedocs.io/en/main/api/generated/pages/Discrete_Grids.html)):
  > "When the horizontal grid is generated, it is actually computed on the 'supergrid' at
  > twice the nominal resolution of the model. The grid file contains the grid metrics and the
  > areas of this fine grid."

  and
  > "The default is for grids to be re-entrant in the x-direction; this needs to be turned off
  > for regional grids."

  It also gives $\text{areaCu} = dxCu \cdot dy\_Cu$: velocity-cell area as length × width,
  which only holds for right angles (§1.3).
- **Indexing** ([page](https://mom6.readthedocs.io/en/main/api/generated/pages/Horizontal_Indexing.html)):
  "The model can use curvilinear grids/coordinates in the horizontal." Curvilinear, yes; the
  pages above make clear it means *orthogonal* curvilinear.
- **Practitioners.** Kate Hedström's 2020 regional-MOM6 webinar (archived slides, see 06 §8.8)
  says: "Need to make an orthogonal grid in some coordinate system … One way is to build in
  flat space using conformal map projections." WikiROMS says ROMS likewise "requires"
  orthogonal curvilinear grids (06 §8.9).

### 1.2 What the grid file gives MOM6

`set_grid_metrics_from_mosaic`
([`MOM_grid_initialize.F90` L170–352](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/initialization/MOM_grid_initialize.F90#L170-L352))
reads exactly five supergrid fields: `x` (L214), `y` (L239), `dx` and `dy` (L263–264), `area`
(L291). Then:

- Model-grid lengths are sums of two supergrid half-edges, e.g.
  `G%dxT(i,j) = tmpV(i2-1,j2-1) + tmpV(i2,j2-1)`.
- `areaT` is the sum of the four supergrid sub-cell areas.
- Coordinates must be lon/lat. The comment at L256–259 says "the grid coordinates are
  assumed to be degrees of longitude and latitude."
- **`angle_dx` is never read.** Grepping `src/` and `config_src/` for `angle_dx` finds
  nothing. Instead, `initialize_grid_rotation_angle`
  ([`MOM_shared_initialization.F90` L568–626](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/initialization/MOM_shared_initialization.F90#L568-L626))
  computes **one** angle per tracer cell from the four corner lon/lats: "the angle between
  logical north on the grid and true north."

So no field anywhere carries the angle between the i- and j-lines, nor the off-diagonal metric
term $g_{12}$. Nothing checks it either: grepping for "orthog" in grid initialisation finds only
OBC-corner comments.

A side note on file formats. GFDL's `make_hgrid` labels its `tile` variable `conformal="true"`
for ocean grid types and writes `angle_dy` only for the non-conformal cubed-sphere grids (06
§8.7). mom6_forge writes `angle_dx` (units "radians"; `make_hgrid` uses "degrees_east") and no
`tile` variable. MOM6 reads neither, so this does not affect MOM6.

### 1.3 Where right angles are baked into the discretisation

Three places in the code only make sense if the grid lines are perpendicular:

1. **One velocity plays two roles.** In the continuity equation, `u` times the face length
   `dy_Cu` gives the volume flux *through* the east face
   ([`MOM_continuity_PPM.F90` L732](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/core/MOM_continuity_PPM.F90#L732)).
   In the vorticity, the same `u` times `dxCu` is the circulation *along* the north and south
   edges of a q-cell
   ([`MOM_CoriolisAdv.F90` L417–418](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/core/MOM_CoriolisAdv.F90#L417-L418)):
   `dudy(I,J,kk) = (u(I,j+1,k) * G%dxCu(I,j+1)) - (u(I,j,k) * G%dxCu(I,j))`. On a skewed grid the
   component normal to a face (flux) and the component along the crossing grid line
   (circulation, pressure gradient) are different numbers. Thompson et al. ch. III, p. 3: "Only
   in an orthogonal coordinate system are the two types of base vectors parallel, since for a
   non-orthogonal system, the normal to a coordinate surface does not necessarily coincide
   with the tangent to a coordinate line crossing that surface"
   ([ch. III PDF][twm3]).
2. **Velocity-cell area is length × width.** `G%areaCu(I,j) = G%dxCu(I,j) * G%dy_Cu(I,j)`
   ([L1334](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/initialization/MOM_grid_initialize.F90#L1334),
   and L1342 for v). A parallelogram has area $dx\,dy\sin\theta$.
3. **One rotation for both components.** The NUOPC cap rotates wind stress (and Stokes drift)
   into grid directions with a single orthonormal rotation per cell:
   `u_flux = cos_rot*taux - sin_rot*tauy`, `v_flux = cos_rot*tauy + sin_rot*taux`
   ([`mom_cap_methods.F90` L170–173](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/config_src/drivers/nuopc_cap/mom_cap_methods.F90#L170-L173)).
   That is only right if the i- and j-directions are 90° apart.

**Bottom line:** the belief that "MOM6 assumes orthogonal grids" is correct, and it is a
silent assumption.

---

## 2. How non-orthogonality enters a C-grid model, and how much is tolerable

### 2.1 The terms an orthogonal formulation drops

Write the grid-line tangent vectors as $\mathbf a_1 = \partial\mathbf x/\partial i$ and
$\mathbf a_2=\partial\mathbf x/\partial j$, with angle $\theta$ between them. The metric is

$$
g_{11}=|\mathbf a_1|^2,\quad g_{22}=|\mathbf a_2|^2,\quad
g_{12}=\mathbf a_1\!\cdot\!\mathbf a_2=|\mathbf a_1||\mathbf a_2|\cos\theta,\quad
\sqrt g = |\mathbf a_1||\mathbf a_2|\sin\theta .
$$

An orthogonal formulation sets $g_{12}=0$ and $\sqrt g = h_1h_2$: in MOM6 terms
$h_1 \leftrightarrow dx$, $h_2\leftrightarrow dy$. Write the velocity as
$\mathbf v = u^{(1)}\hat{\mathbf a}_1 + u^{(2)}\hat{\mathbf a}_2$, with $u^{(k)}$ its physical
contravariant components. Let $\hat{\mathbf n}_1$ be the unit normal of the east face (that
face runs along $\hat{\mathbf a}_2$). Then

$$
\underbrace{\mathbf v\cdot\hat{\mathbf n}_1 = u^{(1)}\sin\theta}_{\text{what carries volume flux}}
\qquad
\underbrace{\mathbf v\cdot\hat{\mathbf a}_1 = u^{(1)} + u^{(2)}\cos\theta}_{\text{what the pressure gradient and circulation act on}}
$$

A general curvilinear model keeps both kinds of component and converts between them (see
Thompson et al. ch. III, covariant vs contravariant base vectors). An orthogonal model has
$\theta = 90^\circ$, so both are $u^{(1)}$, and it stores just one number per face.

**(inference)** When an orthogonal-only model like MOM6 runs on a skewed grid, it drops the
$u^{(2)}\cos\theta$ cross term. The resulting error is **first order in $\cos\theta$** (the
$\sin\theta$ factor is only second order) and does
**not** shrink as resolution increases: it is a wrong equation, not a truncation error. The
Delft3D manual says the same about its own orthogonal formulation (next section).

### 2.2 Published guidance

| Source | Model / setting | What it says |
|---|---|---|
| **Delft3D-FLOW User Manual** v4.07.03, §4.5.2.1 "Grid parameters", p. 27 ([PDF][d3dflow]) | Orthogonal curvilinear C-grid shallow-water model; RGFGRID exists "to fulfil the Delft3D-FLOW requirement of orthogonality" | "Orthogonality: cos(φ) < 0.02, where φ is the angle between the grid lines." "Aspect ratio: must be in the range [1 to 2], unless the flow is predominantly along one of the grid lines." "Ratio of neighbouring grid cells: should be less than 1.2 in the area of interest up to 1.4 far away." |
| **RGFGRID User Manual** v4.07.03, §6.1.8, p. 96, and p. 70 ([PDF][d3drgf]) | Same | "The error in the computed direction of the pressure term in Delft3D-FLOW is proportional to these values. In offshore areas the orthogonality should be less than 0.02. Near closed boundaries, higher values are sometimes acceptable." p. 70: "Keep this value low in the inner model area, e.g. 0.02-0.04." |
| **Thompson, Warsi & Mastin** (1985), ch. V, PDF p. 8 ([ch. V][twm5]) | Finite differences that keep the full transformed equations | Truncation error "varies inversely with the sine of the angle between the coordinate lines"; for skew up to 45° the extra terms are no larger than those from non-uniform spacing; "Reasonable departure from orthogonality is therefore of little concern…"; but "grids should probably be made as nearly orthogonal at the boundaries as is practical." **Does not transfer to MOM6**, which has no cross terms to keep. |
| **Sankaranarayanan & Spaulding (2003a)**, *J. Comput. Phys.* 184(1), 299–320, [doi:10.1016/S0021-9991(02)00042-6](https://doi.org/10.1016/S0021-9991(02)00042-6) (abstract: [URI Digital Commons](https://digitalcommons.uri.edu/oce_facpubs/432); paywalled) | 2D boundary-fitted shallow-water model *with* non-orthogonal terms | Truncation error grows as the grid angle decreases. In a seiche test, RMS error rises sharply at 30°. In a Narragansett Bay tidal test, elevations were insensitive to grid angle but currents were not. |
| **Sankaranarayanan & Spaulding (2003b)**, *Int. J. Numer. Meth. Fluids* 42(7), 741–763, [doi:10.1002/fld.552](https://doi.org/10.1002/fld.552) (abstract: [URI](https://digitalcommons.uri.edu/oce_facpubs/430)) | Fourier analysis, Arakawa C-grid, non-orthogonal | Dispersion grows as the grid angle decreases. Stable down to 30° for Crank–Nicolson and three-level schemes. |
| **MOM6, ROMS** | — | **No number found.** Both say only that grids must be orthogonal. ROMS forum threads on this blocked automated access (unverified). |

The θ in the Thompson symbol was lost in text extraction. I read the rendered page: the extra
terms scale with $\cot\theta$ ($\theta$ = angle between grid lines) and the book says "For
θ <= 45°". Taken literally that bound looks reversed (cot θ ≤ 1 needs θ ≥ 45°), so treat the
45° figure loosely.

Converting the Delft3D numbers: $\cos\varphi<0.02$ means $|90^\circ-\varphi| < 1.15^\circ$, and
0.04 means 2.3°.

### 2.3 How this lines up with the PR

A conformal grid is orthogonal by construction. What is left is discretisation error, worst
near sharp outline corners. Measured on California (ROADMAP.md, "Measured on 2026-10-06";
deviation from 90° at interior nodes):

- **#151 solver (unrefined), 250k mesh:** p99 2.3°, max 34.1°.
- **With #149's corner refinement:** p99 0.46°, max 3.0°.

#151's own benchmark test asserts `np.median(_ortho(cg)) < 1.0` (degrees), skipping the node
rings within about 2h of the outline (`tests/test_conformal.py`, `_ortho`). That median
threshold is the same size as Delft3D's 1.15°. Delft3D's guidance is about the *offshore /
inner* area and explicitly allows more "near closed boundaries", where these skewed cells sit
when the corners are on land. The open question for review is cells next to a sharp corner that
is **open ocean** (an OBC). That is what PR 2b's refinement is for. Delft3D's aspect-ratio
guidance (1–2) is also worth comparing with the benchmark's `aspect.max() < 20`.

---

## 3. Every supergrid point must be defined

### 3.1 What MOM6 needs

- **A full logically rectangular array.** `set_grid_metrics_from_mosaic` reads `x, y, dx,
  dy, area` for the whole `(2ny+1, 2nx+1)` supergrid. Masking does not make any point
  optional.
  - Coriolis is computed from the latitudes at every q-point:
    `f(I,J) = (2.0*omega) * sin((PI*G%geoLatBu(I,J))/180.)` over the whole data domain
    ([`MOM_shared_initialization.F90` L505–507](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/initialization/MOM_shared_initialization.F90#L505-L507)).
  - The rotation angle comes from every cell's corner lon/lats.
  - Halo extrapolation (`extrapolate_metric`, which uses 999 or 0 as "missing") is for
    *halos only*.
- **Land comes from topography.** `initialize_masks`
  ([L1181–1188](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/initialization/MOM_grid_initialize.F90#L1181-L1188))
  "sets mask2dT, mask2dCu, mask2dCv, and mask2dBu to mask out flow over any points which are
  shallower than Dmask." `MINIMUM_DEPTH` (L1223): "If MASKING_DEPTH is unspecified, then
  anything shallower than MINIMUM_DEPTH is assumed to be land and all fluxes are masked out."
- **`MASKTABLE` is about processors, not points.**
  ([`MOM_domains.F90` L318–325](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/framework/MOM_domains.F90#L318-L325))
  "This feature masks out processors that contain only land points." It skips work. It does
  not excuse missing coordinates: the grid file is still read in full.
- **NaNs.** Nothing in grid initialisation handles them. **(inference)** A NaN coordinate
  would propagate into Coriolis, rotation angles and metric reciprocals. Multiplying by a 0
  land mask does not cure it, because IEEE `NaN*0 = NaN`. I did not run MOM6 to confirm
  the failure mode.
- The CESM side (ESMF mesh files, built by mom6_forge from the supergrid) also needs node
  coordinates for every cell, masked or not **(inference; not checked in ESMF docs)**.

### 3.2 gridgen grids with masked (−1) regions

With more than four corners (some β = −1, e.g. side channels), gridgen's image region is a
"set of intersecting rectangles", not one rectangle. Grid nodes that fall outside it come out as
NaN. This is in the code at
[`gridgen.c` L2270–2300](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2270-L2300):
`if (in_poly(...)) map_point(gg, z); else output_point(gg, NaN, NaN);`. pygridgen then turns
NaN nodes into masked arrays
([`grid.py` L285–287](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L285-L287)),
and pyroms does the same.

**How ROMS/pyroms users handled it (what I could confirm):**

- Every pyroms example uses **four corners** (`beta = [1, 1, 1, 1]`), so no NaN region
  arises. That includes the one that writes a MOM6 `ocean_hgrid.nc`
  ([`examples/grid_MOM6/make_grid.py`](https://github.com/ESMG/pyroms/blob/1370d22ab94c877648f82ffc440d25d782dfce62/examples/grid_MOM6/make_grid.py#L114-L123)).
  Land is then masked separately: Hedström's slides list pyroms' `editmask` GUI and coastline
  tools.
- gridgen's README says islands need "masking", i.e. a land mask on top of a simply
  connected grid.
- I found **no documented workflow** for filling NaN nodes of a multi-corner gridgen grid so
  that ROMS or MOM6 can read it. The ROMS forum may have one, but it was not accessible
  (unverified).

**For this PR:** four corners and one rectangle in (ξ, η) mean every supergrid node is a real
point inside the outline. The outline has to enclose the whole model rectangle, land included,
and land then comes from topography. That fits MOM6 exactly.

---

## 4. Why square cells, beyond orthogonality

- **One resolution per cell.** A conformal map is locally a rotation plus a uniform scaling.
  In a conformal projection the Tissot indicatrices are circles (06 §1.2), so a square in the
  projected plane is a square on the Earth to first order. What varies is only the *size*,
  through the projection scale factor and the map's $|f'|$. `size_ratios` and `_cell_geometry`
  measure exactly that. (Which projection is used changes the grid only through how edges
  between outline vertices are drawn: `01_the_problem.md` §1.7 and `projection_invariance.ipynb`.)
- **Viscosity uses a blended spacing.** MOM6's Smagorinsky, Leith and "MICOM" viscosity
  scales all use
  `grid_sp_h2 = (2.0*dx2h*dy2h) / (dx2h + dy2h)`
  ([`MOM_hor_visc.F90` L3382](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/parameterizations/lateral/MOM_hor_visc.F90#L3382)).
  That is the harmonic mean of $dx^2$ and $dy^2$, dominated by the *short* side. On a 1:4
  cell the long direction is under-resolved while the closure is tuned to the short one.
  Square cells remove that ambiguity.
- **Time step (CFL).** MOM6's barotropic limit
  ([`MOM_barotropic.F90` L3787–3798](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/core/MOM_barotropic.F90#L3787-L3798))
  sums gravity-wave terms of the form $g H\,dy/(dx\cdot\text{area})$ over both directions. That
  amounts to $gH(1/dx^2+1/dy^2)$ ("pretty accurate for gravity waves, but … a conservative
  estimate since it ignores the stabilizing effect of the bottom drag"). For a fixed cell area
  $A$ and aspect $r=dy/dx$, $1/dx^2+1/dy^2=(r+1/r)/A$, which is smallest at $r=1$. Relative to
  square cells of the same area, the stable time step shrinks by $\sqrt{(r+1/r)/2}$: about
  4 % at r = 1.5, 12 % at r = 2, 46 % at r = 4 (my arithmetic). For a fixed cell count,
  squares buy the longest time step.
- **MOM6 already thinks this way.** The built-in `GRID_CONFIG = "mercator"` has an
  `ISOTROPIC` option
  ([`MOM_grid_initialize.F90` L712–720](https://github.com/mom-ocean/MOM6/blob/0e9a5611a9f6c99bfea12665da3a9146183521ee/src/initialization/MOM_grid_initialize.F90#L712-L720)):
  > "If true, an isotropic grid on a sphere (also known as a Mercator grid) is used. With an
  > isotropic grid, the meridional extent of the domain (LENLAT), the zonal extent (LENLON),
  > and the number of grid points in each direction are _not_ independent."

  The PR does the same: the conformal modulus ties nx/ny to the outline.
- **Other models' rules of thumb.** Delft3D: aspect ratio 1–2 (§2.2). gridgen's README: set
  (ny−1)/(nx−1) from the reported conformal modulus "to generate a grid with aspect ratio
  close to 1."

---

## 5. Ocean grid tools at a glance

Last-commit dates are from the GitHub API on 2026-11-02 (default branch).

| Tool | Grid kind | Method | Status (last commit) |
|---|---|---|---|
| **mom6_forge `Grid.from_outline`** (this PR) | Regional, 4 corners, orthogonal with square cells, fits an outline | Conformal projection → two P1-FEM Laplace solves (conjugate function method) → invert at uniform (ξ, η) | PR #151 open, review-only |
| mom6_forge other constructors ([NCAR/mom6_forge](https://github.com/NCAR/mom6_forge)) | Regional lat-lon (`Grid(...)`); uniform in a pyproj CRS (`from_projection`); rotated rectangle (`from_center`); from supergrid or ESMF mesh | Analytic | main 2026-09-30 |
| [gridgen-c](https://github.com/sakov/gridgen-c) | Regional, multi-corner, "quasi-orthogonal", fits a polygon | Schwarz–Christoffel via CRDT; optional stereographic `geographic` mode | **2026-07-17** (v1.51.6), active |
| [pygridgen](https://github.com/pygridgen/pygridgen) | Same as gridgen | Python wrapper (ctypes) + `focus` | 2024-10-26 |
| [pyroms](https://github.com/ESMG/pyroms) | ROMS grids (gridgen-based), masks, bathymetry; one MOM6 converter example | Wraps gridgen; Basemap projections | 2023-12-13 |
| [octant](https://github.com/hetland/octant) | ROMS/GETM front end to gridgen | — | 2019-07-13, README marked deprecated |
| [SeaGrid](https://github.com/sea-mat/seagrid) | Regional, 4 corners, orthogonal, ROMS/POM/ECOM output | Conformal projection → Ives–Zacharias conformal map to a rectangle → Poisson fill (MATLAB) | 2017-01-12 |
| [ESMG gridtools](https://github.com/ESMG/gridtools) | Regional MOM6 supergrid: tilted rectangle in Mercator/LCC/stereographic | Uniform in a conformal projection; no coastline fitting | 2022-05-06 (pushed 2023-03-19) |
| [FRE-NCtools `make_hgrid`](https://github.com/NOAA-GFDL/FRE-NCtools) | Regular lat-lon, tripolar, cubed sphere, Cartesian, `from_file` | Analytic | 2026-09-10, active |
| [GFDL ocean_model_grid_generator](https://github.com/NOAA-GFDL/ocean_model_grid_generator) | Global tripolar / displaced-pole caps for MOM | Analytic (Murray-type) | 2024-07-17 |
| [COSIMA regional-mom6](https://github.com/COSIMA/regional-mom6) | Regional MOM6 experiments; grid from mom6_forge `Grid` | "only 'even_spacing' is supported" | 2026-10-05, active |
| [SC Toolbox](https://github.com/tobydriscoll/sc-toolbox) | General SC maps incl. rectangle and CRDT (`crrectmap`); not ocean-specific | Schwarz–Christoffel (MATLAB) | 2026-06-16 |
| Delft3D RGFGRID ([manual][d3drgf]) | Orthogonal curvilinear grids for Delft3D-FLOW | Splines → grid → "Orthogonalise" iterations | Manual v4.07.03 checked; repository not checked |

**Aside on mom6_forge's existing constructors (not part of #151).** `from_center` "Uses an
azimuthal equidistant projection." That projection is not conformal, so a uniform rectangle in
it is not exactly orthogonal on the Earth away from the centre. **(inference)** For regional
sizes the skew should be tiny: the projection's two scale factors differ by about
$(\rho/R)^2/6$, e.g. ~0.1 % at 500 km from the centre. It could still be worth a one-line
docstring note. `from_projection` is orthogonal only if the CRS passed is conformal.

---

## 6. Could not verify

- A **MOM6-specific tolerance** for non-orthogonality: none found in the docs, the source, or
  the GitHub issues of mom-ocean/MOM6, NOAA-GFDL/MOM6 or COSIMA/regional-mom6. Issue search for
  "non-orthogonal" and "orthogonal grid" found nothing relevant.
- What MOM6 actually does at run time with NaNs in `ocean_hgrid.nc` (§3.1 is from reading the
  code, not from running it).
- ROMS forum threads on orthogonality limits (403, not archived), and the live WikiROMS pages
  (403; archived copies used).
- Griffies (2004) chs. 20–21 and Arakawa & Lamb (1981): citations checked through Crossref, but
  not read.

[twm3]: http://web.archive.org/web/2019id_/http://www.hpc.msstate.edu/publications/gridbook/PDFS/chapt03.pdf
[twm5]: http://web.archive.org/web/2019id_/http://www.hpc.msstate.edu/publications/gridbook/PDFS/chapt05.pdf
[d3dflow]: https://content.oss.deltares.nl/delft3d4/Delft3D-FLOW_User_Manual.pdf
[d3drgf]: https://content.oss.deltares.nl/delft3d4/RGFGRID_User_Manual.pdf
