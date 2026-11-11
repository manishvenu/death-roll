# 06 — Reading list: conformal maps, the modulus, and how ocean grids get made

An annotated, checked reading list for reviewing
[NCAR/mom6_forge#151](https://github.com/NCAR/mom6_forge/pull/151) (`Grid.from_outline`,
head `db0db39`), chunk 1 of Dan Amrhein's #149. The code is in
`mom6_forge/_conformal.py`. The notation follows `01_the_problem.md`: ξ runs W→E, η runs
S→N, the rectangle is $W$ wide and $H$ tall, and the **conformal modulus** is $M = H/W$.

**How the links were checked (2026-11-02).**

- **Free**: I opened it. For a PDF, I downloaded it and checked the title page.
- **Paywalled**: the DOI resolves, and I checked its metadata (authors, journal, pages) on
  Crossref. The publisher page either needs a subscription or blocked my automated fetch
  (SIAM, Elsevier, AIAA, AMS, World Scientific and Princeton all returned 403). Where a
  free preprint exists, it is listed too.
- **Unverified**: I could not open it. These are collected at the end.

**Difficulty tags.** `intro` needs only calculus. `intermediate` assumes PDEs, numerics and a
first pass through the intro items. `research` is primary literature.

**Terms used below.** A *conformal map* preserves angles locally: a tiny square maps to a
tiny square, rotated and scaled. A *quadrilateral* is any simply connected region with four
marked boundary points, the corners. Its *conformal modulus* $M$ is the height/width of the
one rectangle it maps onto conformally, corners to corners. The *Dirichlet energy* is
$E[u]=\int|\nabla u|^2\,dA$. A *harmonic conjugate* $v$ of a harmonic $u$ is the function
that makes $u+iv$ analytic. Its level curves cross those of $u$ at right angles. A
*Schwarz–Christoffel (SC) map* is the explicit integral formula for the conformal map from a
disk or half-plane onto a polygon. Its unknowns are the *prevertices*: the points that map
to the polygon's corners. *Crowding* is prevertices bunching exponentially close together
for elongated regions.

---

## If you only read three things

1. **Orloff, *Topic 10: Conformal transformations*** (MIT 18.04), §10.2–10.6 and §10.9
   (`intro`, about 1 hour). Read this to see why analytic functions preserve angles and why
   harmonic functions are the right tool. [Free PDF][orloff]. Olver §4–5 [olver] covers the
   same ground at more depth.
2. **Hakula, Quach & Rasila (2013), "Conjugate function method for numerical conformal
   mappings"**, §2–3 (`intermediate`, about 1 hour). This is Dan's algorithm in published
   form. You solve one Dirichlet–Neumann Laplace problem per direction. The modulus is the
   Dirichlet energy (their eq. (2)). Combining the two solutions gives the map (their
   Algorithm 3.2). [arXiv:1103.4930][hqr13].
3. **Trefethen & Driscoll (1998), "Schwarz–Christoffel mapping in the computer era"**
   (ICM survey, 10 pages, `intermediate`). Read §1–2 and §5. This is what gridgen and
   pygridgen compute and why crowding forced CRDT. [Free PDF][icm98].

Bonus, one paragraph: **Driscoll & Vavasis (1998), §9, p. 1797** says outright that mapping a
"generalized quadrilateral" onto a rectangle "is equivalent to solving Laplace's equation on
the polygon with the Dirichlet values of 0 and 1 on two generalized sides separated by two
generalized sides with homogeneous Neumann conditions." That sentence links gridgen's
method to Dan's. [Free copy][crdt-wb].

---

## Which reading explains which part of the PR

| PR code | What to read |
|---|---|
| `MapProjection`, `projection_for`, `as_projection` | Wikipedia *Conformal map projection* (§1); Hedstrom 2020 slides (§8); gridgen's `geographic` option (§8) |
| `_sides`, `_mesh` | Persson & Strang 2004; Shewchuk 2002 (§6) |
| `_stiffness` | Crane DDG notes ch. 6.2; Wikipedia *Discrete Laplace operator*; Pinkall & Polthier 1993 (§6) |
| `_harmonic` | Hakula et al. 2013 §2.1; Alberty et al. 1999; Thompson et al. ch. IX §A (§5–7) |
| `aspect = sqrt(e_xi / e_eta)`, nx/ny | Wikipedia *Extremal length*; Hakula et al. 2011 eq. (2.1); gridgen README item 7 (§2, §8) |
| `_sample`, `solve` (inverting at uniform ξ, η) | Hakula et al. 2013 Alg. 3.2 and 4.1; Thompson et al. ch. X (§5, §7) |
| `corner_angles`, sharp corners | gridgen README item 6; Hakula et al. 2011 §3.8 (§2, §8) |
| `size_ratios`, cell-size spread | Wikipedia *Conformal map projection*; `01_the_problem.md` §1.7 |
| why orthogonal at all | `07_ocean_grids_and_mom6.md` |

---

## 1. Gentle introductions to conformal maps

**1.1 Wikipedia, "Conformal map."** <https://en.wikipedia.org/wiki/Conformal_map> — Free.
`intro`. It opens with "a conformal map is a function that locally preserves angles, but not
necessarily lengths." Read the two-dimensions section, which covers the Riemann mapping
theorem (any simply connected proper subdomain of the plane maps conformally onto the disk),
and "Applications → Cartography" (Mercator and stereographic are conformal). *Explains:* the
vocabulary of the whole PR.

**1.2 Wikipedia, "Conformal map projection."**
<https://en.wikipedia.org/wiki/Conformal_map_projection> — Free. `intro`. It lists Mercator,
transverse Mercator, Lambert conformal conic and stereographic: exactly the four `KINDS` in
`_conformal.py`. It also notes that every Tissot indicatrix of a conformal projection is a
circle, meaning the local scale is the same in all directions and only its size changes from
place to place. *Explains:* why solving in a conformal projection keeps square cells square
on the Earth, and why the only distortion left is cell **size** (what `size_ratios` measures).

**1.3 Douglas N. Arnold, "Graphics for complex analysis" (1997).**
<https://www-users.cse.umn.edu/~arnold/complex.html> — Free. `intro`. A page of animated GIFs.
Under the power map it says "all the right angle intersections remain right angles throughout
the deformation." It also has a Schwarz–Christoffel section showing how prevertices and angles
reshape a polygon. This is the quickest visual for "a conformal map turns a square grid into
an orthogonal curvilinear grid." *Explains:* the picture behind `solve`.

**1.4 J. C. Ponce Campuzano, *Complex Analysis: A Visual and Interactive Introduction*,
"Conformal mapping" chapter.** <https://complex-analysis.com/content/conformal_mapping.html> —
Free. `intro`. It gives the definition, the proof that an analytic function with $f'\neq0$ is
conformal, and an applet where you drag the corners of a square under different maps.

**1.5 Jeremy Orloff, *Topic 10 Notes: Conformal transformations*, MIT 18.04 (Spring 2018).**
[PDF][orloff] — Free (22 pp.). `intro`. Read §10.2 (geometric definition), §10.4 (analytic ⇒
conformal), §10.5 (harmonic functions), §10.6 (Riemann mapping theorem) and §10.9 (solving the
Dirichlet problem by mapping). These are short lecture notes that match the math the PR needs.
*Explains:* why the PR solves Laplace's equation at all.

**1.6 Peter J. Olver, *Complex Analysis and Conformal Mapping* (lecture notes, 2024).**
[PDF][olver] — Free (87 pp.). `intro`→`intermediate`. Read §4 "Harmonic Functions"
(pp. 15–26). It shows that the gradient of a harmonic function and the gradient of its
harmonic conjugate are orthogonal, which is why ξ- and η-lines cross at right angles. Then
read §5 "Conformal Mapping" (pp. 27–43) and §6 "Applications … to Laplace's Equation" (p. 44
on). *Explains:* why two harmonic coordinates give an orthogonal grid.

**1.7 Tristan Needham, *Visual Complex Analysis*, 25th anniversary ed. (Oxford UP, 2023;
paperback ISBN 978-0-19-286892-3; first ed. 1997).** The book itself was not opened (see
"could not verify"). `intro`. This is the standard geometric book on complex analysis; the
amplitwist and conformal-mapping chapters are the relevant ones.

---

## 2. Conformal modulus, extremal length, and the Dirichlet energy

`01_the_problem.md` §1.5 already derives $E_\xi = M$, $E_\eta = 1/M$ and
$E_\xi E_\eta = 1$. The readings below are the sources for those facts. One addition that
helps in review: the finite-element energies are upper bounds (§6), so
$1/E_{\eta,h} \le M \le E_{\xi,h}$. The code's `aspect = sqrt(e_xi / e_eta)` is therefore the
geometric mean of a lower and an upper bound on $M$, for the region the mesh triangles cover.

**2.1 Wikipedia, "Extremal length."** <https://en.wikipedia.org/wiki/Extremal_length> — Free.
`intermediate`. Read §2.1 "Extremal distance in rectangle": the extremal length between the
left and right sides of a $w\times h$ rectangle is $w/h$, and the reciprocal family has $h/w$.
Read §4 "Conformal invariance", which the page calls "the primary reason why the concept of
extremal length is useful". In §7 the discrete extremal length equals an effective
resistance. *Explains:* why the modulus is an intrinsic number of the outline-plus-corners,
independent of how you compute it.

**2.2 Wikipedia, "Sheet resistance."** <https://en.wikipedia.org/wiki/Sheet_resistance> —
Free. `intro`. "Ohms per square": a square sheet has the same resistance at any size, and
$R = R_s\,L/W$. With ξ as a voltage, $E_\xi$ is the conductance between the W and E edges,
and $1/E_\xi$ counts the squares in series. That is exactly nx/ny when the cells are square.
*Explains:* the aspect formula, in electrician's terms.

**2.3 Wikipedia, "Dirichlet's principle."**
<https://en.wikipedia.org/wiki/Dirichlet%27s_principle> — Free. `intro`. The solution of
Laplace's equation with given boundary values "can be obtained as the minimizer of the
Dirichlet energy." *Explains:* why the energy in `_harmonic` is meaningful and why FE energies
come out high (§6).

**2.4 Hakula, Rasila & Vuorinen (2011), "On moduli of rings and quadrilaterals: algorithms and
experiments," *SIAM J. Sci. Comput.* 33(1), 279–302,
[doi:10.1137/090763603](https://doi.org/10.1137/090763603).** Paywalled; free preprint
[arXiv:0906.1261][hrv11]. `research`. Read §2.1, where eq. (2.1) states that the modulus
equals the Dirichlet integral of the Dirichlet–Neumann solution, citing Ahlfors. Read §4 on
the reciprocal identity $M(Q)\,M(\tilde Q)=1$, used as an error estimate. Read §3.8 on
geometric mesh grading toward corners (they isolate each corner and refine recursively). They
benchmark against the SC Toolbox. *Explains:* the aspect formula and the
$E_\xi E_\eta - 1$ error gauge. §3.8 is the relevant contrast to the PR's uniform-$h$ mesh near
sharp corners.

**2.5 Lars V. Ahlfors, *Conformal Invariants: Topics in Geometric Function Theory*
(McGraw-Hill 1973; AMS Chelsea reprint 2010),
[doi:10.1090/chel/371](https://doi.org/10.1090/chel/371).** Publisher page
<https://www.ams.org/chel/371> loads; the book is paywalled. `research`. The classical source
on extremal length. Hakula et al. cite "p. 65 / Thm 4.5" for the Dirichlet-integral formula
for the modulus. Read it only if you want proofs.

**2.6 Papamichael & Stylianopoulos, *Numerical Conformal Mapping: Domain Decomposition and the
Mapping of Quadrilaterals* (World Scientific, 2010),
[doi:10.1142/7511](https://doi.org/10.1142/7511).** Paywalled; DOI checked on Crossref.
`research`. A whole book on the modulus of quadrilaterals. Hakula et al. cite its ch. 2
(Thm 2.3.3) for the same Dirichlet-integral formula, and its ch. 3 domain-decomposition method
for long, thin quadrilaterals. *Explains:* what to do about very elongated domains if
accuracy ever matters there.

---

## 3. Schwarz–Christoffel mapping

**3.1 Trefethen & Driscoll (1998), "Schwarz–Christoffel mapping in the computer era," *Doc.
Math.* Extra Vol. ICM III, 533–542.** [Free PDF (EMS Press)][icm98]. `intermediate`. This is
the best 10-page overview. §2 covers the numerical SC algorithms. §5 explains crowding with
one number: for a rectangle of aspect ratio $L$, prevertices are "separated by intervals that
shrink in proportion to $\exp(-\pi L/2)$. For $L = 30$ … only about $10^{-21}$." §5 also
explains CRDT's idea: compose locally well-behaved Möbius maps. *Explains:* why gridgen needs
CRDT, and why the PR's FE route has no crowding problem in the first place.

**3.2 Driscoll & Trefethen, *Schwarz–Christoffel Mapping* (Cambridge UP, 2002),
[doi:10.1017/CBO9780511546808](https://doi.org/10.1017/CBO9780511546808).** The Cambridge page
loads; the book is paywalled. `intermediate`. This is the book on SC mapping, cited by
`_conformal.py` [2]. Go to the chapters on the rectangle and strip maps and on crowding when
you need depth beyond 3.1.

**3.3 T. A. Driscoll, *Schwarz–Christoffel Toolbox User's Guide*, v2.3.**
<https://tobydriscoll.net/project/sc-toolbox/guide.pdf> (same file in the repo:
<https://github.com/tobydriscoll/sc-toolbox>) — Free (26 pp.). `intro`→`intermediate`. Read
§4.3 "Cross-ratio (CR) formulations" (p. 16). Crowding means prevertices "becoming
indistinguishable in double precision when the local aspect ratio exceeds about 20." Read
"Rectified maps" (p. 16–17), the trick gridgen uses: same prevertices, new angles. Read
footnote 7 (p. 17): a rectilinear polygon with four angles of ½ "is a rectangle and the side
lengths determine the rectangle's aspect ratio, or conformal modulus." The 1994 original is
Cornell TR 94-1422, <https://hdl.handle.net/1813/6204>. The toolbox repo's last commit was
2026-06-16. *Explains:* gridgen's "image polygon" and its modulus output.

**3.4 L. N. Trefethen (1980), "Numerical computation of the Schwarz–Christoffel
transformation," *SIAM J. Sci. Stat. Comput.* 1(1), 82–102,
[doi:10.1137/0901004](https://doi.org/10.1137/0901004).** Free author copy:
<https://people.maths.ox.ac.uk/trefethen/publication/PDF/1980_1.pdf>. `research`. This is the
SCPACK paper that gridgen acknowledges. §2 covers the "parameter problem" (finding the
prevertices) and compound Gauss–Jacobi quadrature, which is gridgen's `nnodes` parameter. §3
covers evaluating the map and its inverse. Skim it.

**3.5 Lehel Banjai, "Schwarz–Christoffel mapping for difficult cases" (slides, Stony Brook
CCG workshop 2007).** <https://www.math.stonybrook.edu/~ccg2007/banjai.pdf> — Free (40
slides). `intro`→`intermediate`. Visual crowding: as a rectangle gets longer, one prevertex
creeps toward 1 (0.95…, 0.998…). One slide shows that where crowding appears depends on the
normalisation, the observation CRDT builds on. The paper behind it is Banjai (2008),
"Revisiting the crowding phenomenon in Schwarz–Christoffel mapping," *SIAM J. Sci. Comput.*
30(2), 618–636, [doi:10.1137/060677392](https://doi.org/10.1137/060677392) (paywalled).

**3.6 T. K. DeLillo (1994), "The accuracy of numerical conformal mapping methods: a survey of
examples and results," *SIAM J. Numer. Anal.* 31(3), 788–812,
[doi:10.1137/0731043](https://doi.org/10.1137/0731043).** Copy on the author's site:
<https://www.math.wichita.edu/~delillo/DeLillo_SINUM_1994.pdf>. `research`. Read §3 "Crowding
estimates" if you want to know how bad crowding gets as a function of elongation. Its point:
the global aspect ratio is what causes it.

---

## 4. CRDT (what gridgen and pygridgen actually run)

**4.1 T. A. Driscoll & S. A. Vavasis (1998), "Numerical conformal mapping using cross-ratios
and Delaunay triangulation," *SIAM J. Sci. Comput.* 19(6), 1783–1803,
[doi:10.1137/S1064827596298580](https://doi.org/10.1137/S1064827596298580).** SIAM is
paywalled. **Working free copies:**

- The archived copy of gridgen's dead link:
  [web.archive.org … gridgen-c.googlecode.com/files/crdt.pdf][crdt-wb] (snapshot
  2016-01-11). This is the published SIAM version, 21 pp., byte-identical (same MD5) to the
  next item.
- <https://www.math.stonybrook.edu/~bishop/classes/math401.F09/crdt.pdf> (C. Bishop's course
  page).
- Tech-report versions: Cornell TR 96-233 (Feb 1996), <https://hdl.handle.net/1813/5567>; and
  NASA/RIACS TR 96.05 (Jan 1996), scanned, 35 pp.,
  <https://ntrs.nasa.gov/api/citations/19960020954/downloads/19960020954.pdf>.
- Driscoll's own site links `tobydriscoll.net/_docs/driscoll-numerical-conformal-mapping-1998-a.pdf`,
  but it returns 404.

`research`. Sections: §2 Delaunay triangulation, §3 splitting edges (extra vertices so
triangles aren't slender), §4 cross-ratios and embeddings, §5 the algorithm, §6 "On the
circumvention of crowding", §8 computing maps, §9 applications. **§9 (p. 1797)** is the
paragraph quoted at the top: mapping onto a rectangle is a 0/1 Dirichlet + zero-Neumann
Laplace problem, and the rectangle's aspect ratio "must be a certain unknown value, known as
the conformal modulus." *Explains:* that Dan and gridgen solve the same problem; and why
gridgen splits long edges and works quadrilateral by quadrilateral.

**4.2 Trefethen & Driscoll ICM survey §5** (item 3.1): the accessible summary of CRDT. Read
it before 4.1.

**4.3 SC Toolbox guide §4.3** (item 3.3): the user-level view of CRDT (`crdiskmap`,
`crrectmap`).

**4.4 C. J. Bishop (2010), "Bounds for the CRDT conformal mapping algorithm," *Comput. Methods
Funct. Theory* 10(1), 325–366,
[doi:10.1007/BF03321771](https://doi.org/10.1007/BF03321771).** Springer page loads
(paywalled). Free preprint: <https://www.math.stonybrook.edu/~bishop/papers/crdt.pdf> (44 pp.).
`research`. It proves one of Driscoll & Vavasis's conjectures: CRDT's initial guess is always
within a bounded distance of the true map. Convergence itself is still not proven (the
abstract says the method "is not proven to converge"). Useful context only.

**4.5 gridgen's built-in description.** `gridgen -a` prints a 40-line plain-language summary
of CRDT. In the source it is
[gridgen.c lines 285–327](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L285-L327).
Free. `intro`. It explains "one forward and one backward transformation with the same
prevertices but different vertex angles", and that "the main obstacle … is a potential loss of
precision … ('crowding')." It is the shortest correct explanation of what gridgen does.

---

## 5. The conjugate function method and other PDE/FEM routes to conformal maps

**5.1 Hakula, Quach & Rasila (2013), "Conjugate function method for numerical conformal
mappings," *J. Comput. Appl. Math.* 237(1), 340–353,
[doi:10.1016/j.cam.2012.06.003](https://doi.org/10.1016/j.cam.2012.06.003).** Paywalled;
free preprint [arXiv:1103.4930][hqr13] (v5). `intermediate`→`research`. **This is the closest
published match to the PR.** Read Def. 2.1 (modulus of a quadrilateral) and Def. 2.2
(reciprocal identity). Eq. (2) states $M(Q)=\iint|\nabla u|^2$ for the solution with $u=0$ and
$u=1$ on two opposite sides and $\partial u/\partial n=0$ on the other two. Lemma 2.3 shows
that the harmonic conjugate of $u$ is $h\,\tilde u$, where $\tilde u$ solves the *conjugate*
(rotated) problem. That is why the PR can get η from a second Laplace solve instead of
integrating Cauchy–Riemann. The univalence argument after Lemma 2.3 shows why the map cannot
fold. Algorithm 3.2 is the method. Algorithm 4.1 evaluates the FE solution at a point (find the
element, take barycentric weights), the same idea as `_sample`, run in the other direction.
*Explains:* `_harmonic`, the aspect formula, and `solve`.

**5.2 Hakula, Rasila & Vuorinen (2011)**, item 2.4. Same group, the modulus-only paper with
hp-FEM and corner grading.

**5.3 Hakula, Quach & Rasila (2019), "The conjugate function method and conformal mappings in
multiply connected domains," *SIAM J. Sci. Comput.* 41(3), A1753–A1776,
[doi:10.1137/17M1124164](https://doi.org/10.1137/17M1124164).** Paywalled; free preprint
<https://arxiv.org/abs/1502.02047>. `research`. The extension to domains with holes. This is
only relevant if islands inside the outline ever become part of the grid problem. Today they
come from topography, see `07_ocean_grids_and_mom6.md` §3.

**5.4 Thompson, Warsi & Mastin, *Numerical Grid Generation*, ch. IX §A "Conformal systems"**
(full entry in §7). `intermediate`. It derives, in 1985 grid-generation language, the
"properly posed boundary value problems" for conformal coordinates: Dirichlet on two sides and
zero normal derivative on the other two, for each coordinate (its eqs. (19)–(20), chapter PDF
p. 5). It also introduces the distortion function $F=h_2/h_1$, the grid aspect ratio, and
notes that $F=1$ gives conformal coordinates. *Explains:* that the PR's boundary conditions are
textbook grid generation, not something new.

**5.5 Papamichael & Stylianopoulos (2010)**, item 2.6.

**5.6 Keenan Crane, *Discrete Differential Geometry: An Applied Introduction* (CMU notes,
updated 2025), ch. 7 "Surface Parameterization."** [Free PDF][crane] (174 pp.). `intermediate`.
§7.1–7.4 cover conformal structure, the Cauchy–Riemann equation, and discrete conformal
parameterisation by minimising an energy. This is the graphics community's version of the
same idea, with very clear pictures.

---

## 6. P1 finite elements for Laplace's equation

The PR uses piecewise-linear ("P1") finite elements on triangles. Three facts matter for
review:

- On one triangle the stiffness entries are the **cotangent weights**: the off-diagonal entry
  for edge $ij$ is $-\tfrac12\cot$ of the angle opposite that edge. `_stiffness` computes it as
  (edge·edge)/(4·area). A right angle gives $\cot 90^\circ=0$, which is why `_stiffness` calls
  `eliminate_zeros()` with the comment "the hypotenuses of right triangles".
- Non-positive off-diagonals (non-obtuse triangles, or in 2D a Delaunay mesh) make the matrix
  an M-matrix. That gives a **discrete maximum principle**: ξ and η stay in [0, 1] and have no
  spurious interior extrema, which is what keeps the inverted grid from folding.
- **The FE energy is an upper bound.** The P1 solution minimises the energy over a subspace
  with the same 0/1 side values (Céa's lemma: energy-norm best approximation), so
  $E_h \ge E$.

**6.1 Crane, *DDG* notes, ch. 6 "The Laplacian."** [Free PDF][crane]. `intermediate`. §6.2
"Discretization via FEM" derives the cotan formula from P1 hat functions. §6.4 builds the
sparse matrix. §6.7 covers boundary conditions, Dirichlet and Neumann. The derivation is the
same as `_stiffness`, with pictures. *Explains:* `_stiffness`, and the Neumann sides in
`_harmonic` getting zero flux "for free" (natural boundary condition).

**6.2 Wikipedia, "Discrete Laplace operator," section "Mesh Laplacians."**
<https://en.wikipedia.org/wiki/Discrete_Laplace_operator> — Free. `intro`. The cotangent
formula in one equation, with angles $\alpha_{ij},\beta_{ij}$ opposite edge $ij$.

**6.3 U. Pinkall & K. Polthier (1993), "Computing discrete minimal surfaces and their
conjugates," *Experimental Mathematics* 2(1), 15–36,
[doi:10.1080/10586458.1993.10504266](https://doi.org/10.1080/10586458.1993.10504266).** DOI
checked on Crossref. The Project Euclid page
(<https://projecteuclid.org/journals/experimental-mathematics/volume-2/issue-1/Computing-discrete-minimal-surfaces-and-their-conjugates/em/1062620735.full>)
answered HTTP 200 but I could not read its content, so free full text is unconfirmed.
`research`. The classic source of the cotan formula, and of discrete *conjugate* harmonic
functions. Historical interest.

**6.4 J. Alberty, C. Carstensen & S. A. Funken (1999), "Remarks around 50 lines of Matlab:
short finite element implementation," *Numerical Algorithms* 20, 117–137,
[doi:10.1023/A:1019155918070](https://doi.org/10.1023/A:1019155918070).** Springer page loads
(paywalled); I found no free copy. `intermediate`. A 2D Laplace solver with mixed Dirichlet and
Neumann conditions in about 50 lines. Element-by-element stiffness assembly into a sparse
matrix, then solving for the free nodes with the Dirichlet values moved to the right-hand
side: the same pattern as `_stiffness` + `_harmonic`.

**6.5 P.-O. Persson & G. Strang (2004), "A simple mesh generator in MATLAB," *SIAM Review*
46(2), 329–345, [doi:10.1137/S0036144503429121](https://doi.org/10.1137/S0036144503429121).**
Free author copy: <http://persson.berkeley.edu/distmesh/persson04mesh.pdf> (17 pp.).
`intro`→`intermediate`. Meshing a region from a signed-distance function plus a Delaunay
triangulation, keeping the triangles whose centroid is inside. `_mesh` does a simpler version:
a lattice kept more than h/2 from the outline, boundary points h apart, Delaunay, then drop
triangles whose centroid is outside. *Explains:* `_mesh` and what "drop triangles outside the
outline" can and cannot guarantee.

**6.6 J. R. Shewchuk (2002), "What is a good linear finite element? Interpolation,
conditioning, anisotropy, and quality measures" (preprint).**
<https://people.eecs.berkeley.edu/~jrs/papers/elemj.pdf> — Free (70 pp.). `intermediate`. §2
covers how element angles affect interpolation and gradient error (large angles hurt
gradients). §3 covers stiffness-matrix conditioning (small angles hurt). Read §2 intro and §3
lightly. *Explains:* why `_mesh` drops near-zero-area ("flat") triangles, and why the lattice
of squares split into right triangles is a good mesh. Gradient accuracy matters here because
cell shapes come from ∇ξ, ∇η.

**6.7 P. G. Ciarlet & P.-A. Raviart (1973), "Maximum principle and uniform convergence for the
finite element method," *Comput. Methods Appl. Mech. Eng.* 2(1), 17–31,
[doi:10.1016/0045-7825(73)90019-4](https://doi.org/10.1016/0045-7825(73)90019-4).** Paywalled.
`research`. The original discrete maximum principle for P1 on non-obtuse ("acute")
triangulations.

**6.8 J. Xu & L. Zikatanov (1999), "A monotone finite element scheme for convection-diffusion
equations," *Math. Comp.* 68(228), 1429–1446,
[doi:10.1090/S0025-5718-99-01148-5](https://doi.org/10.1090/S0025-5718-99-01148-5).** DOI
checked on Crossref. The AMS page blocked my fetch, so whether it is free is unverified.
`research`. Its abstract (seen through search indexes, not on the AMS page) says that in 2D
the monotonicity condition amounts to the triangulation being Delaunay. This is the weaker
(Delaunay) form of the condition in 6.7.

**6.9 Wikipedia, "Céa's lemma."** <https://en.wikipedia.org/wiki/C%C3%A9a%27s_lemma> — Free.
`intermediate`. Section "Error estimate in the energy norm": for a symmetric problem "the
subspace solution $u_h$ is the best approximation to the full-space solution $u$ in respect to
the energy norm." With Dirichlet's principle (2.3), this is why $E_{\xi,h}\ge E_\xi$ and
$E_{\eta,h}\ge E_\eta$.

---

## 7. Orthogonal grid generation in general

**7.1 J. F. Thompson, Z. U. A. Warsi & C. W. Mastin, *Numerical Grid Generation: Foundations
and Applications* (North-Holland, 1985).** **Free, with the author's permission**: the authors'
Mississippi State page (copyright transferred to Thompson in 1997) grants "permission … for
downloading in entirety." The live page (`hpc.msstate.edu/publications/gridbook/`) now returns
404, but the Wayback Machine has it:
<http://web.archive.org/web/20190907142813/http://www.hpc.msstate.edu:80/publications/gridbook/>.
Chapter PDFs I downloaded and checked:
[ch. III][twm3], [ch. V][twm5], [ch. VI][twm6], [ch. IX][twm9], [ch. X][twm10]. The archived "complete" PDF
link is not in the archive (404). `intermediate`. Read:

- **Ch. III "Transformation Relations"**, p. 3: "Only in an orthogonal coordinate system are
  the two types of base vectors parallel." This is the covariant/contravariant distinction
  that an orthogonal model like MOM6 collapses (07 §1.3, §2.1).
- **Ch. V "Truncation Error"**, PDF p. 8: the error from non-orthogonality "varies inversely
  with the sine of the angle between the coordinate lines," and "Reasonable departure from
  orthogonality is therefore of little concern when the rate-of-change of grid spacing is
  reasonable." **Caveat:** this is for schemes that *keep* the non-orthogonal metric terms.
  MOM6 does not (see 07).
- **Ch. VI §A "Laplace system"**: the Winslow-type system and its extremum principle, which
  "guarantees a one-to-one mapping."
- **Ch. IX "Orthogonal Systems"**: the aspect function $F$ (p. 3) and §A "Conformal systems"
  (p. 5), the PR's boundary-value problem.
- **Ch. X "Conformal Mapping"**: "very rigid in the sense that little control can be exerted
  over the distribution of the grid points." That is the trade-off the PR accepts: no
  resolution control, in exchange for square cells.

*Explains:* where the PR sits among grid-generation methods.

**7.2 A. M. Winslow (1966), "Numerical solution of the quasilinear Poisson equation in a
nonuniform triangle mesh," *J. Comput. Phys.* 1(2), 149–172,
[doi:10.1016/0021-9991(66)90001-5](https://doi.org/10.1016/0021-9991(66)90001-5).** Paywalled.
`research`. The origin of "solve Laplace for the logical coordinates on a triangle mesh, then
invert." Winslow fixes values on all four sides, so the grid is smooth but not orthogonal. The
PR's Neumann sides are what make it conformal.

**7.3 G. Ryskin & L. G. Leal (1983), "Orthogonal mapping," *J. Comput. Phys.* 50(1), 71–100,
[doi:10.1016/0021-9991(83)90042-6](https://doi.org/10.1016/0021-9991(83)90042-6).**
Paywalled. `research`. The classic orthogonal (not necessarily conformal) mapping via a
distortion function, with conformal as the special case $F=1$ (Thompson ch. IX summarises
this).

**7.4 L. Eça (1996), "2D orthogonal grid generation with boundary point distribution control,"
*J. Comput. Phys.* 125(2), 440–453,
[doi:10.1006/jcph.1996.0106](https://doi.org/10.1006/jcph.1996.0106).** Paywalled. `research`.
Orthogonal grids that also let you place boundary points: the control that a pure conformal
map lacks. Read it if anyone asks for resolution control on the sides.

**7.5 P. Knupp & S. Steinberg, *Fundamentals of Grid Generation* (CRC Press, 1993; ISBN
978-0-8493-8987-0).** Publisher page:
<https://www.routledge.com/Fundamentals-of-Grid-Generation/Steinberg/p/book/9780849389870>
loads. I found no free copy. `intermediate`. A more modern textbook alternative to 7.1.

**7.6 D. C. Ives & R. M. Zacharias (1989), "Conformal mapping and orthogonal grid
generation," *J. Propulsion and Power* 5(3), 327–333,
[doi:10.2514/3.23156](https://doi.org/10.2514/3.23156).** Paywalled. `research`. The conformal
method inside SeaGrid (§8.5).

---

## 8. Ocean grid generation in practice

**8.1 R. J. Murray (1996), "Explicit generation of orthogonal grids for ocean models," *J.
Comput. Phys.* 126(2), 251–273,
[doi:10.1006/jcph.1996.0136](https://doi.org/10.1006/jcph.1996.0136).** Paywalled. The OSTI
record with the abstract loads:
<https://www.osti.gov/biblio/447028-explicit-generation-orthogonal-grids-ocean-models>.
`intermediate`. **Global** orthogonal grids (moving the pole onto land: the tripolar grids MOM
uses) built from the conformal properties of stereographic and Mercator projections. It is in
MOM6's own bibliography (`docs/zotero.bib`). It is not about regional coastline-fitting, but
it shows why ocean modellers reach for conformal projections.

**8.2 gridgen-c (Pavel Sakov).** <https://github.com/sakov/gridgen-c> — Free; last commit
2026-07-17 (v1.51.6). `intermediate`. Read the inner
[`gridgen/README`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/README),
item 4:

- (2) "can handle simply connected regions only. If you have a region with islands …, you have
  to use masking."
- (6) "each boundary vertex represents a singularity … Try to make the angles … at the
  location of designated grid corners close to the right angle."
- (7) for aspect ratio ≈ 1, "look at the value of 'conformal modulus' reported … and make the
  ratio (ny − 1) / (nx − 1) close to this number."

Item 7 is the manual version of the PR's automatic nx/ny. `gridgen -h` documents
`beta_i = (1 − angle_i/π)·2` (the sum must be 4: four corners of +1). It also documents a
`geographic lon0 lat0` option that projects stereographically before gridding. *Explains:* the
PR's corners (β = +1), corner-angle warnings, and nx/ny.

**8.3 pygridgen.** Docs <https://pygridgen.readthedocs.io/en/latest/>; repo
<https://github.com/pygridgen/pygridgen> (last commit 2024-10-26) — Free. `intro`. The
[basics tutorial](https://pygridgen.readthedocs.io/en/latest/tutorial/basics.html) covers β
(+1 closes, −1 makes a side channel, the sum must be 4), `ul_idx`, and `focus`. In the code,
[`CGrid.__init__`](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L285-L287)
turns gridgen's NaN nodes into masked arrays.
[`CGrid.orthogonality`](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L537-L555)
is a ready-made orthogonality-error metric.

**8.4 pyroms (ESMG).** <https://github.com/ESMG/pyroms> — Free; last commit 2023-12-13.
`intermediate`. Every grid example uses gridgen with **four corners, `beta = [1, 1, 1, 1]`**,
in a conformal projection: LCC (Yellow Sea), north polar stereographic (Arctic), Mercator.
[`examples/grid_MOM6/make_grid.py`](https://github.com/ESMG/pyroms/blob/1370d22ab94c877648f82ffc440d25d782dfce62/examples/grid_MOM6/make_grid.py#L114-L123)
builds a gridgen grid in polar stereographic and writes a MOM6 `ocean_hgrid.nc`. This is the
workflow the PR replaces. Its README credits the conversion script to Mehmet Ilicak and
Alistair Adcroft.

**8.5 SeaGrid (Chuck Denham, USGS).** <https://github.com/sea-mat/seagrid> — Free; last commit
2017-01-12 (MATLAB). `intro`. The README says: "Starting from a conformal projection (such as
Mercator) …, SeaGrid uses the Ives-Zacharias scheme to conformally map the curved perimeter to
a rectangle, after which, a Poisson solver fills the interior with orthogonally distributed
grid points." That is the same recipe as the PR: conformal projection, then a conformal map to
a rectangle.

**8.6 ESMG gridtools.** Docs <https://mom6gridtools.readthedocs.io/en/dev/>; repo
<https://github.com/ESMG/gridtools> (last commit 2022-05-06) — Free. `intro`. A Jupyter/Panel
GUI that builds MOM6 supergrids as (optionally tilted) uniform rectangles in Mercator, Lambert
conformal conic or stereographic projections (`gridtools/app.py`). These are orthogonal because
the projection is conformal. It does not fit a coastline.

**8.7 FRE-NCtools `make_hgrid` (NOAA-GFDL).** <https://github.com/NOAA-GFDL/FRE-NCtools>
(last commit 2026-09-10); man page
[`man/make_hgrid.txt`](https://github.com/NOAA-GFDL/FRE-NCtools/blob/960380832c839d008d71c9786d98dba4acf08303/man/make_hgrid.txt)
— Free. `intro`. GFDL's supergrid writer: regular lat-lon, tripolar, cubed-sphere, Cartesian,
`from_file`. "The output data is on a super grid (model grid size x refinement(=2))." A detail
from `make_hgrid.c`: the `tile` variable carries `conformal = "true"`, except for the
cubed-sphere types, which set `"FALSE"` and are the only ones that also write `angle_dy`
([lines 948–957, 1237–1243](https://github.com/NOAA-GFDL/FRE-NCtools/blob/960380832c839d008d71c9786d98dba4acf08303/src/make-hgrid/make_hgrid.c#L1237-L1243)).

**8.8 Kate Hedström, "Setting up Regional MOM6" (2020 MOM6 webinar slides).** Live link
`www2.cesm.ucar.edu/events/2020/MOM6/files/2020-MOM6-Hedstrom.pdf` returns 401. Archived:
[web.archive.org snapshot 2024-07-10][hed20] — Free (33 slides). `intro`. Slide 2 says: "Need
to make an orthogonal grid in some coordinate system … One way is to build in flat space using
conformal map projections • Mercator • Lambert conformal conic • Polar stereographic." Slide 3
lists tools (pygridgen, Gridbuilder, …). Slide 22 says "Check angle across dateline!" This is
the practitioner's version of the PR's design. *Explains:* `MapProjection`.

**8.9 WikiROMS, "Grid Generation."** The live <https://www.myroms.org/wiki/Grid_Generation>
returns 403 to automated fetches. Archived (2025-02-17):
<http://web.archive.org/web/20250217184416/https://www.myroms.org/wiki/Grid_Generation> — Free.
`intro`. "Several software packages are available to generate the orthogonal curvilinear grids
that ROMS requires." It lists SeaGrid ("4 corners") and gridgen ("arbitrary number of
corners").

**8.10 K. S. Hedström (2018), *Technical Manual for a Coupled Sea-Ice/Ocean Circulation Model
(Version 5)*, OCS Study BOEM 2018-007.** <https://www.boem.gov/BOEM-2018-007> — Free (182 pp.).
`intermediate`. The ROMS formulation in orthogonal curvilinear coordinates. §7.1.6 says the
grid file comes from Wilkin & Hedström's grid package, "the Matlab SeaGrid, or by some other
method", and that curved grids also need `dndx`, `dmde` (the metric-derivative terms).

**8.11 S. Xu, B. Wang & J. Liu (2015), "On the use of Schwarz–Christoffel conformal mappings to
the grid generation for global ocean models," *Geosci. Model Dev.* 8, 3471–3485,
[doi:10.5194/gmd-8-3471-2015](https://doi.org/10.5194/gmd-8-3471-2015).** Free (CC-BY), page
<https://gmd.copernicus.org/articles/8/3471/2015/>. `research`. SC maps for global orthogonal
ocean grids. The authors suggest the approach could carry over to regional domains.

**8.12 K. W. Hess (1995), *Orthogonal curvilinear grid generation*, NOAA Tech. Rep. NOS OES 007.**
<https://repository.library.noaa.gov/view/noaa/30407> — Free (60 pp. PDF). `intermediate`.
Orthogonal grids for the Princeton Ocean Model built line by line (cubic splines, orthogonality
enforced at segment or cell centres). A non-conformal alternative, useful for contrast.

**8.13 COSIMA regional-mom6.** Docs <https://regional-mom6.readthedocs.io/en/latest/api.html>;
repo <https://github.com/COSIMA/regional-mom6> (last commit 2026-10-05) — Free. `intro`. Its
grid comes from mom6_forge `Grid` objects; `hgrid_type` "Currently, only 'even_spacing' is
supported." Its `recalculate_rotation_angle()` recomputes `angle_dx` "using MOM6's
expanded-supergrid method." That is relevant to how boundary velocities get rotated (07 §1).

---

## Could not verify

- **Needham, *Visual Complex Analysis*** (1.7): the publisher page rendered empty. Only the
  ISBN and edition were confirmed, through bookseller and library listings and a
  *Mathematical Gazette* review.
- **Video explainers.** I found none I could open. A Mathemaniac "Essence of complex analysis
  #3" video (with a "conformal maps" chapter) shows up in aggregator listings, but I could not
  confirm a YouTube link. Use Arnold's animations (1.3) instead.
- **Publisher landing pages** for SIAM, Elsevier/JCP, AIAA, AMS (*Math. Comp.*, *MWR*), World
  Scientific and Princeton UP returned 403 to my fetches. The citations above were checked
  through Crossref DOI metadata instead.
- **Pinkall & Polthier** (6.3): whether the full text is free on Project Euclid.
- **Thompson et al. complete PDF**: not in the Wayback Machine. The chapter PDFs are (7.1).
- **ROMS forum threads on orthogonality limits** (`myroms.org/forum/…p=6499`, `p=23468`):
  blocked (403), not archived.
- **Driscoll's own PDFs** of CRDT and the SC Toolbox paper on tobydriscoll.net: 404.
- **Hedström's 2011 "Grid Generation for ROMS" slides** (`myroms.org/wiki/images/2/24/Gridgen.pdf`):
  403, not archived.

[orloff]: https://ocw.mit.edu/courses/18-04-complex-variables-with-applications-spring-2018/ef46ddd9941227b8700c945bb7475ae9_MIT18_04S18_topic10.pdf
[olver]: https://www-users.cse.umn.edu/~olver/ln_/cml.pdf
[hqr13]: https://arxiv.org/abs/1103.4930
[hrv11]: https://arxiv.org/abs/0906.1261
[icm98]: https://ems.press/content/book-chapter-files/27266?nt=1
[crdt-wb]: http://web.archive.org/web/20160111093238/http://gridgen-c.googlecode.com/files/crdt.pdf
[crane]: https://www.cs.cmu.edu/~kmcrane/Projects/DDG/paper.pdf
[twm3]: http://web.archive.org/web/2019id_/http://www.hpc.msstate.edu/publications/gridbook/PDFS/chapt03.pdf
[twm5]: http://web.archive.org/web/2019id_/http://www.hpc.msstate.edu/publications/gridbook/PDFS/chapt05.pdf
[twm6]: http://web.archive.org/web/2019id_/http://www.hpc.msstate.edu/publications/gridbook/PDFS/chapt06.pdf
[twm9]: http://web.archive.org/web/2019id_/http://www.hpc.msstate.edu/publications/gridbook/PDFS/chapt09.pdf
[twm10]: http://web.archive.org/web/2019id_/http://www.hpc.msstate.edu/publications/gridbook/PDFS/chapt10.pdf
[hed20]: http://web.archive.org/web/20240710234708/https://www2.cesm.ucar.edu/events/2020/MOM6/files/2020-MOM6-Hedstrom.pdf
