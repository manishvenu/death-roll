# 02 — How gridgen makes a grid (read from the source)

This note is for reviewing mom6_forge PR #151 (`Grid.from_outline`, chunk 1 of Dan Amrhein's #149) against the tool it cites as its model: Pavel Sakov's **gridgen-c**, plus its Python wrapper **pygridgen**. Everything about gridgen below comes from its source code. Each claim links to the exact lines at a fixed commit:

| Repo | Commit read | Notes |
|---|---|---|
| `sakov/gridgen-c` | [`222cc71f859d6f483a7ba7a435e5cb9f41977906`](https://github.com/sakov/gridgen-c/tree/222cc71f859d6f483a7ba7a435e5cb9f41977906) | tagged v1.51.6 in `CHANGELOG`, though `version.h` still says 1.51.5 |
| `pygridgen/pygridgen` | [`18d78c7737a4ee1722ec73238ea689a6527d025f`](https://github.com/pygridgen/pygridgen/tree/18d78c7737a4ee1722ec73238ea689a6527d025f) | |
| Dan's solver | `mom6_forge/_conformal.py` in the `conformal-solver` worktree, commit `db0db39e` | cited by function name and line number |

The paper behind the method is Driscoll & Vavasis, *Numerical conformal mapping using cross-ratios and Delaunay triangulation*, SIAM J. Sci. Comput. 19(6), 1783–1803 (1998), called **CRDT** from here on. I read the published version and cite it by section. gridgen turns out to be a fairly literal implementation of the paper's §3–§5 and its §9 rectangle-map application, with a grid generator added on top.

Plan: §0 summary · §1 the math from scratch · §2 gridgen-c step by step · §3 pygridgen · §4 gridgen in pseudocode · §5 correspondence with `_conformal.py` · §6 what MOM6 does and doesn't need · §7 what the source doesn't settle.

---

## 0. The short version

1. **How gridgen gets grid nodes:** it builds the image region (a rectangle, or a rectilinear polygon if you use −1 corners) and lays a uniform lattice over its bounding box. Then, separately for each node $\zeta$, it **inverts** the image map to get a point $w$ in the unit disk, and **evaluates** the physical map forward at $w$:
   $z = f(\tilde f^{-1}(\zeta))$.
   - The inversion is a secant iteration, with an ODE solve (DOPRI8, an 8th-order Runge–Kutta integrator) as fallback.
   - Both maps are Schwarz–Christoffel (SC) integrals sharing the same prevertices (defined in §1.2). They differ only in the angles they use.
   - Each node is evaluated in the "local" copy of the map that belongs to the triangulation quadrilateral containing it (§2.4 j).
2. **The unknowns** are $n-3$ real numbers $\sigma_i = \ln(-\rho_i)$, one per diagonal of a constrained Delaunay triangulation of the polygon. Here $\rho_i$ is the cross-ratio of the four prevertices of quadrilateral $i$, and $n$ counts vertices after edge splitting. The unknowns are not the prevertex positions themselves.
3. **The equations:** for each quadrilateral, $\ln\lvert\text{cross-ratio}\rvert$ of the SC images must equal the same quantity for the real polygon. gridgen solves them by simple iteration or by Broyden starting from Jacobian $=I$; the paper calls the latter "Shortcut CRDT".
4. **How it handles crowding:** by never using one global placement of the prevertices. For each quadrilateral it re-embeds all prevertices so that quadrilateral's four sit as a rectangle centred on the origin. It evaluates that quadrilateral's equation in that embedding, and later maps grid nodes in that quadrilateral with the same embedding.
5. **How nx and ny are set: you choose them.** gridgen prints the conformal modulus (width/height of the image bounding box) only with `-v`, and pygridgen throws away the image rectangle it receives. For square cells the code needs $(n_x-1)/(n_y-1) \approx$ the printed modulus. The README states the ratio the other way round (§2.6). Dan's code instead computes the modulus as $\sqrt{E_\xi/E_\eta}$ and picks nx and ny itself.
6. **Every polygon vertex is a singularity** of the map. At a non-corner vertex with interior angle $\alpha$, grid spacing behaves like $\lvert\zeta-\zeta_j\rvert^{\alpha/\pi-1}$. At a grid corner it behaves like $\lvert\zeta-\zeta_j\rvert^{2\alpha/\pi-1}$, which is regular only when $\alpha=90^\circ$. This belongs to the exact conformal map, so Dan's FEM solution has the same behaviour.
7. **Masking:** lattice nodes outside the image polygon are written as `NaN NaN`, and pygridgen turns them into masked values. This only happens with −1 (reflex) or non-right-angle image corners.
8. **Custom node spacing** (the `grid` file, or pygridgen's `focus`) means passing arbitrary points in $[0,1]^2$, which are scaled to the image bounding box. With per-axis stretching this keeps the grid orthogonal and gives up square cells. It is the most directly reusable idea for MOM6.
9. **Bugs and oddities found while reading:**
   - The library entry point that pygridgen calls never stores `nppe`, so pygridgen's `nppe` argument has no effect.
   - The `-h` help text gives outdated defaults.
   - A few other small issues are listed in §2.8.

---

## 1. The math, from scratch

### 1.1 Why conformal maps give orthogonal grids

Write points in the plane as complex numbers $z = x + iy$. A map $z = F(\zeta)$ is **conformal** if it is analytic (complex-differentiable) with $F'(\zeta) \neq 0$. Near any point it acts like multiplication by the complex number $F'(\zeta)$: a rotation plus a scaling by $\lvert F'\rvert$, the same in every direction.

- Two curves crossing at right angles in the $\zeta$-plane therefore cross at right angles in the $z$-plane.
- A tiny $\Delta\times\Delta$ square becomes a tiny, slightly curved square of side $\lvert F'\rvert\Delta$.

So take a region $\Omega_\zeta$ where an orthogonal grid is trivial (a rectangle), find a conformal $F$ from it onto your ocean polygon $P$, and push the lattice through $F$. The result is orthogonal everywhere, and its cells have aspect ratio 1 wherever the lattice cells are square. Cell *size* varies like $\lvert F'\rvert$, and you don't control that. This is the shared idea of gridgen and of Dan's PR.

The hard part is constructing $F$ for an arbitrary polygon. gridgen does it with **Schwarz–Christoffel maps**. Dan does it by solving Laplace's equation on a mesh.

### 1.2 The Schwarz–Christoffel formula

The **Riemann mapping theorem** says every simply connected region except the whole plane can be mapped conformally and one-to-one from the unit disk $D=\{\lvert w\rvert<1\}$. For a **polygon** that map has a nearly explicit form, the Schwarz–Christoffel formula. gridgen uses its disk version (CRDT eq. 1; [`swcr.h` L41–59](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.h#L41-L59)):

$$
f(w) \;=\; A + B\int_0^{w}\prod_{j=1}^{n}\Big(1-\frac{\omega}{w_j}\Big)^{\beta_j}\,d\omega,
\qquad \beta_j = \frac{\alpha_j}{\pi}-1 .
$$

- $z_1,\dots,z_n$ are the polygon vertices, counter-clockwise, with interior angles $\alpha_j$.
- $w_1,\dots,w_n$ lie on the unit circle in the same order. They are the **prevertices**: $f(w_j)=z_j$.
- $A$ (translation) and $B$ (rotation plus scale) are complex constants.

Textbooks also write it with the upper half-plane as source, $f(x)=A+C\int^x\prod_j(\xi-x_j)^{\alpha_j/\pi-1}d\xi$. It is the same idea with real prevertices $x_j$.

```
        unit disk (w-plane)                         polygon (z-plane)
             . - ~ ~ - .                       z4 *--------------* z3
          w3*            * w2                     |               \
         '                  '      f              |                \
        :        0           :   ------>          |                 * z2
         .                  .                     |                /
          w4*            * w1                  z5 *---------------* z1
             ' - ~ ~ - '
   arcs between prevertices  -->  straight edges between vertices
```

**Why the edges come out straight, and why $\sum\beta_j=-2$.** Walk along the unit circle, $\omega=e^{i\theta}$, so $d\omega = ie^{i\theta}d\theta$ and $\arg d\omega=\theta+\pi/2$. For $w_j=e^{i\theta_j}$,

$$1-e^{i(\theta-\theta_j)} = -2i\,\sin\!\tfrac{\theta-\theta_j}{2}\;e^{i(\theta-\theta_j)/2},$$

so $\arg(1-\omega/w_j) = (\theta-\theta_j)/2-\pi/2$. That increases linearly with slope $\tfrac12$ and **jumps by $-\pi$** as $\theta$ passes $\theta_j$. The direction of the image boundary is $\arg(f'(\omega)\,d\omega)$, so between prevertices

$$\frac{d}{d\theta}\arg\big(f'\,d\omega\big) \;=\; 1+\tfrac12\textstyle\sum_j\beta_j .$$

This is zero, giving a straight edge, exactly when $\sum_j\beta_j=-2$. That condition is the same as saying the exterior turning angles $\tau_j=\pi-\alpha_j$ add up to $2\pi$, true for any simple polygon. gridgen checks it for the physical polygon in [`gridgen_check`, gridgen.c L1574–1594](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1574-L1594). At $w_j$ the direction jumps by $-\pi\beta_j=\pi-\alpha_j$, which is exactly the turning angle at $z_j$.

**Why every vertex is a singularity.** Near $w_j$, $f'(w)\sim C\,(w-w_j)^{\beta_j}$ and $f(w)-z_j\sim C'(w-w_j)^{\alpha_j/\pi}$. The disk's straight boundary (angle $\pi$) is opened or closed to angle $\alpha_j$.

- $f'\to0$ at a convex vertex ($\alpha_j<\pi$).
- $f'\to\infty$ at a reflex vertex ($\alpha_j>\pi$).

Every coastline kink is a point where the map, and therefore the grid spacing, is singular. That is what the README warns about in [gridgen/README L85–91](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/README#L85-L91): "each boundary vertex represents a singularity … try to make the polygon section smoother; using a few smaller turns instead of one sharp turn". A vertex with $\alpha_j=\pi$ ($\beta_j=0$) drops out of the product. gridgen skips it in the integrand ([`sc_prod`, swcr.c L327–347](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L327-L347)), but it still counts as a prevertex for bookkeeping.

### 1.3 The parameter problem

With the $w_j$ known, $f$ is just quadrature. The hard part is finding the $w_j$. Count the unknowns:

- $n$ angles $\theta_j=\arg w_j$, plus the complex $A$ and $B$: $n+4$ real numbers.
- The disk's self-maps (Möbius maps $g(w)=e^{i\phi}\frac{w-r}{1-\bar r w}$) have 3 real degrees of freedom, so 3 prevertices can be fixed arbitrarily.
- $A$ and $B$ are fixed afterwards by matching two vertices.

That leaves **$n-3$ real unknowns and $n-3$ real equations**. Classic codes (SCPACK, the SC Toolbox) take side-length ratios and orientations as the equations (CRDT §1). Solving these is the **SC parameter problem**.

### 1.4 Three β conventions (this trips everyone up)

gridgen uses the letter β for three different things:

| Symbol | Where | Formula | Meaning | Sum |
|---|---|---|---|---|
| $\beta^{g}_k$ | user input: 3rd column of the `input` file, pygridgen `beta` | $2(1-\tilde\alpha_k/\pi)$ | turning of the **image** boundary at vertex $k$, in quarter turns: +1 = 90° left turn (convex corner), −1 = 90° right turn (reflex corner), 0 = not a corner | **4** |
| $\beta_k$ | SC exponent of the physical map, computed from geometry ([`calculate_betas`, gridgen.c L1048–1092](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1048-L1092)) | $\alpha_k/\pi-1$ | the polygon's own angle at $z_k$ | −2 |
| $\tilde\beta_k$ | SC exponent of the image ("rectified") map ([`set_newbetas`, L1627–1646](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1627-L1646)) | $-\beta^g_k/2$ | interior angle $\tilde\alpha_k$ of the image at vertex $k$: −½ is 90°, +½ is 270°, 0 is straight | −2 |

The user's $\beta^g$ describes the **image region, not the coastline**. The coastline's real angles are always measured from the coordinates. $\sum\beta^g=4$ simply says the image boundary turns through $2\pi = 4\times90°$ ([help text, gridgen.c L361–368](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L361-L368)). With only ±1 values, that means $\#(+1)-\#(-1)=4$. Four +1 corners give a rectangle; six +1 and two −1 give an L-, T- or Z-shaped rectilinear region. Example 4 uses three corners of $\beta^g=4/3$, an equilateral-triangle image ([examples/xy.4](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/examples/xy.4)).

### 1.5 The image region, the "rectified map", and the conformal modulus

The trick is in CRDT §9, and the `-a` help text spells it out in [gridgen.c L283–329](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L283-L329). Keep the **same prevertices** $w_j$ found for the polygon, but put the image angles $\tilde\beta_j$ into the SC integral:

$$\tilde f(w) = \tilde A + \tilde B\int_0^w\prod_j\Big(1-\frac{\omega}{w_j}\Big)^{\tilde\beta_j}d\omega .$$

This **rectified map** sends the disk onto a polygon whose angles are 90° at the corners and 180° everywhere else, a rectangle in the 4-corner case. The composition $\tilde f\circ f^{-1}$ is then a conformal map from the polygon $P$ to the rectangle, carrying the marked vertices to the rectangle's corners. gridgen evaluates the inverse, $f\circ\tilde f^{-1}$, at lattice points.

**The conformal modulus is forced, not chosen.** A conformal map of the disk has only 3 real degrees of freedom, so you can't send 4 marked boundary points to the corners of an arbitrary rectangle. Exactly one rectangle shape works, $[0,M]\times[0,1]$, and its aspect $M$ is a conformal invariant of ($P$, 4 corners), the **conformal modulus** (CRDT §9). In gridgen, $M$ appears as the shape of the image the rectified map produces. Its sides are wherever the SC integral places them, and gridgen prints the bounding box's width/height ([gridgen.c L1910–1912](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1910-L1912)). The same $M$ can be written as a Dirichlet energy, which is the link to Dan's code:

- $\eta$ harmonic, $=0$ on S, $=1$ on N, zero normal flux on W and E: $\int\lvert\nabla\eta\rvert^2=M$.
- $\xi$ harmonic, $=0$ on W, $=1$ on E, zero flux on S and N: $\int\lvert\nabla\xi\rvert^2=1/M$.

So $E_\xi E_\eta=1$ exactly, and Dan's $\sqrt{E_\xi/E_\eta}$ estimates $1/M$ (see §5). This is the "conjugate function method" family; gridgen reaches the same $M$ through SC integrals instead. The CRDT paper says the same in §9: "Computation of this mapping is equivalent to solving Laplace's equation on the polygon with the Dirichlet values of 0 and 1 on two generalized sides separated by two generalized sides with homogeneous Neumann conditions."

**How corner angles show up in the grid.** Near an image corner $\tilde\beta_j=-\tfrac12$, so $\zeta-\zeta_j\propto(w-w_j)^{1/2}$ and $z-z_j\propto(w-w_j)^{\alpha_j/\pi}$. Hence

$$\frac{dz}{d\zeta}\propto(\zeta-\zeta_j)^{2\alpha_j/\pi-1}.$$

This is regular only when the coastline angle at the chosen corner is $\alpha_j=90°$. At a 120° corner the spacing grows like $\lvert\zeta-\zeta_j\rvert^{1/3}$, so cells crowd into the corner. Above 90° the exponent is positive and cells shrink toward the corner. The California test outline in this PR has corners of 86/186/204/80°, giving exponents ≈ −0.04/+1.07/+1.27/−0.11. That fits the measured result that its two east-corner cells are about 10× smaller than the median (see `../CLAUDE.md`). At a non-corner vertex $\tilde\beta_j=0$, the rectified map is smooth there, and $dz/d\zeta\propto(\zeta-\zeta_j)^{\alpha_j/\pi-1}$. Hence README item 6: "make the angles in the boundary polyline at the location of designated grid corners close to the right angle". All of this is a property of the true conformal map. Any method that approximates it well, Dan's included, inherits it.

### 1.6 Crowding: why plain SC fails on elongated domains

The arc length of the unit circle between two prevertices is $2\pi$ times the **harmonic measure** of that polygon side, seen from the conformal centre $f(0)$. Harmonic measure is the probability that a random walk from $f(0)$ first hits that side. Down a channel of width $W$ it decays like $e^{-\pi L/W}$ with distance $L$. (A strip maps to a half-plane by $\exp(\pi z/W)$; CRDT Fig. 9 shows this $e^{-\pi L}$ slope.) So:

```
   z-plane                                              w-plane (unit circle)
   +---------------------+                                  . - ~ ~ - .
   |                     |                               *'             '*
   |    f(0) *           +-------------------------+    :                  :
   |                     |     channel, L/W = 12   |    :         0        :
   |                     +-------------------------+     .                **** <- all far-end
   +---------------------+                                ' - ~ ~ - '         prevertices
                                                                              within ~e^-38
```

With $L/W\approx 11.5$ the far-end prevertices are about $e^{-36}\approx 2\times10^{-16}$ apart. They can no longer be told apart in double precision, so the SC integrand can't be evaluated near them, and neither the map nor its inverse is usable there. This is **crowding**. The CRDT paper (§1) puts it as: "if the aspect ratio is 20 to 1, then at least 14 significant digits are lost". It is a problem of the *representation*, one fixed placement of the prevertices, not of the map itself. A typical open-ocean regional domain (aspect 2–4) barely crowds. Estuaries and fjords, gridgen's home turf, crowd badly.

### 1.7 The CRDT idea

CRDT, "cross-ratios of the Delaunay triangulation", replaces the prevertex angles with **Möbius-invariant** unknowns. That lets it pick a fresh, uncrowded placement of the prevertices for every local computation.

**(a) Split edges** (CRDT §3) so each quadrilateral (step b) is well-conditioned:

- *Phase 1:* at any vertex with interior angle $\le\pi/4$, add a vertex on each adjacent edge (CRDT: at the midpoints of the sides of the largest isosceles triangle cut off there), and protect the two edges next to it.
- *Phase 2:* any unprotected edge $e$ with $d(e) < \ell(e)/(3\sqrt2)$ is split into thirds. Here $d$ is the distance to the nearest "foreign" vertex. Repeat until no edge is split.

The new vertices have angle $\pi$, so they don't change the SC integrand. They only add unknowns.

**(b) Constrained Delaunay triangulation** of the polygon, using its vertices only and no interior points. That gives $n-2$ triangles and $n-3$ **diagonals** (interior edges). Each diagonal and its two triangles form a **quadrilateral** $Q_i$, so there are exactly as many quadrilaterals as unknowns. Triangles sharing a diagonal define a tree (the dual graph).

```
         b                      quadrilateral Q_i = (a, b, c, d), counter-clockwise
        / \                     diagonal a–c = an interior edge of the triangulation
       /   \                    cross-ratio  rho(a,b,c,d) = (d-a)(b-c) / ((c-d)(a-b))
      a-----c   <- diagonal
       \   /                    on a circle: rho is a negative real number (CRDT Lemma 1),
        \ /                     because the angles at a and c are inscribed in
         d                      complementary arcs and sum to pi
```

**(c) Unknowns: $\sigma_i = \ln\!\big(-\rho(w_{a},w_{b},w_{c},w_{d})\big)$** for each quadrilateral (CRDT eq. 3). These are logs of the prevertex cross-ratios. Cross-ratios are unchanged by Möbius maps, so $\sigma$ describes the prevertex configuration *up to* the 3-parameter freedom, without committing to any one placement.

**(d) Embeddings.** Given $\sigma$ and the positions of three prevertices of one triangle, all others follow (CRDT Theorem 1). Walk the dual tree. Each step places the one new vertex $d$ of the next quadrilateral from Lemma 2:

$$d = \frac{hc + a}{h+1},\qquad h = \frac{\rho_0\,(b-a)}{c-b},\qquad \rho_0=-e^{\sigma}.$$

Different starting triangles give Möbius-equivalent placements, called **embeddings**, and they all produce the same polygon up to similarity (Theorem 2). CRDT uses a specific embedding $E_i$ for each quadrilateral $i$ (§5, step 3): its four prevertices form **a rectangle centred on the origin**. They are well separated and far from every crowded cluster:

```
     w_b = -cos(a) + i sin(a)        w_a = cos(a) + i sin(a)
                 *-----------------------*
                 |           0           |        tan^2(a) = -rho = e^sigma
                 *-----------------------*
     w_c = -cos(a) - i sin(a)        w_d = cos(a) - i sin(a)
```

**(e) Equations.** In embedding $E_i$, compute the SC images $\zeta$ of $Q_i$'s four prevertices by integrating from 0 along straight lines with $A=0$, $B=1$. Then require

$$F_i(\sigma) \;=\; \ln\lvert\rho(\zeta_a,\zeta_b,\zeta_c,\zeta_d)\rvert - c_i = 0,\qquad c_i = \ln\lvert\rho(z_a,z_b,z_c,z_d)\rvert .$$

That is $n-3$ equations in $n-3$ unknowns (CRDT eq. 6 and step 3). A cross-ratio doesn't change under similarity, so the unknown $A$ and $B$ don't matter. Proposition 1 (credited to Snoeyink): angles plus the $n-3$ values $\lvert\rho_i\rvert$ determine the polygon up to similarity. A solution therefore gives the right polygon.

**(f) Why crowding no longer hurts** (CRDT §6). Equation $i$ is evaluated in embedding $E_i$, where its four prevertices are not crowded. The quadrature never passes close to a crowded prevertex. Crowded clusters still exist in each embedding, but only far from the quadrilateral being evaluated. Each $f_i$ is accurate in and near $Q_i$, and CRDT effectively computes $n-3$ overlapping local SC maps (§5, step 4).

**(g) Solving.** Start from $\sigma^{(0)}=c$, i.e. assume prevertex cross-ratios match vertex cross-ratios. Iterate $\sigma\leftarrow\sigma - F(\sigma)$ (CRDT eq. 7). The authors observed linear convergence every time and say the Jacobian "approximates the identity", though they couldn't prove it. A faster option is Gauss–Newton with Broyden updates starting from $F'=I$, which they call "Shortcut CRDT" (§7). Neither convergence nor the near-identity Jacobian is proved (§10).

**(h) Using the solution: the quadrilateral graph** (CRDT §8–9). Two quadrilaterals that share a triangle share three prevertices. So the affine constants $(A_i,B_i)$ of one local map follow accurately from a neighbour's. Walking the graph builds the constants multiplicatively, without the cancellation that causes crowding errors. Section 9 does this for the rectified map to get the rectangle and its modulus: "only for those embeddings in which h is comparable to |B̃_i| do we need to track the image of the line". It ends: "We believe that this technique can be generalized to perform grid generation for any polygon … a more general region whose angles are integer multiples of π/2 … The main obstacle is in automatically assigning the most appropriate angle at each prevertex." **gridgen is that generalization, with the user assigning the angles.**

---

## 2. gridgen-c as implemented

### 2.1 File map

| File | Role |
|---|---|
| [`main.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/main.c#L40-L109) | CLI. `-a` prints the algorithm, `-h` the parameter format, `-v`/`-V`/`-VV` set verbosity. Calls `gridgen_generategrid(prmfile)`. |
| [`gridgen.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c) | Everything specific to CRDT and to grids: parameter parsing, quadrilaterals, the nonlinear solve, image polygon, node mapping, output. |
| [`swcr.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c) | SC integral (`sc_w2z`) and its inverse (`sc_z2w`). Ported from SCPACK: compound Gauss–Jacobi quadrature, secant method plus ODE. |
| [`broyden.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/broyden.c#L21-L79) | One Broyden step on a dense negative-inverse-Jacobian matrix $W$. |
| [`ode.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/ode.c#L42-L62), [`zode.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/zode.c#L73-L126) | DOPRI8 (Hairer–Nørsett–Wanner) and a wrapper for complex values along a straight path. |
| [`vertlist.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c) | Polygon as a circular list: reading, thinning, orientation, CRDT edge splitting (phases 1 and 2), triangulation call. |
| [`delaunay.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/delaunay.c#L100-L240) + `triangle.c` | Shewchuk's Triangle with switches `"eznC"` + `"p"` (+`Q`): a constrained Delaunay triangulation with no Steiner points (Triangle's `-p` doc, [triangle.c L1580–1588](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/triangle.c#L1580-L1588)). Triangles outside the segments are discarded ([L2195–2205](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/triangle.c#L2195-L2205)). |
| [`geom.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/geom.c) | Point-in-triangle, point-in-quadrilateral, point-in-polygon (`in_poly`), point–edge distance. |
| [`issimplepoly.c`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/issimplepoly.c#L1-L25) | Shamos–Hoey self-intersection test. |
| `hash.c`, `istack.c` | Hash table and integer stack. |

### 2.2 Parameter-file entries (what the code actually reads)

Parsing happens in [`gridgen_create`, gridgen.c L627–841](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L627-L841). Keys are matched as the first word on a line by `key_find`/`prm_read` ([L435–502](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L435-L502)). The file is rewound once for each key, so order doesn't matter, and an unknown or misspelled key is silently ignored. Examples 5 and 6 write `nnnodes`, so they silently get the default ([prm.5](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/examples/prm.5)).

| Key | Default in code | Clamp | What it does |
|---|---|---|---|
| `input <file>` | **required** | – | Polygon vertex file ([L640–643](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L640-L643)); format in §2.3. |
| `output <file>` | stdout | – | Node file ([L818–821](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L818-L821)). |
| `nx`, `ny` | 25, 25 | [2, 10001] | **Node** counts (not cells) of the uniform image lattice ([L796–816](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L796-L816); constants [L62–64](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L62-L64)). Not read at all if `grid` is given. |
| `grid <file>` | none | – | Custom node positions in $[0,1]^2$ index space, replacing nx and ny ([L781–794](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L781-L794)); §2.7. |
| `nnodes` | **10** | [5, 20] | Gauss–Jacobi nodes per quadrature subinterval ([L760–767](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L760-L767), [L59–61](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L59-L61)). Help: about $-\log_{10}(\text{precision})$. |
| `precision` | **1e-12** | [1e-14, 1e-3] | Stopping tolerance on $\lVert F\rVert_2$. Also used as the tolerance for inversion, ODE, point-in-polygon and snapping ([L772–779](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L772-L779), [L56–58](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L56-L58)). |
| `newton` | 1 | – | 0: simple iteration. 1: Broyden from $W=-I$. See §2.4 g and §2.8 ([L769–770](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L769-L770)). |
| `thin` | 1 | – | Removes consecutive near-duplicate vertices, closer than 1e-6 × bbox extent in both x and y ([L722–735](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L722-L735); [`vertlist_thin`, vertlist.c L166–191](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L166-L191)). A deleted vertex's nonzero β moves to its predecessor. |
| `checksimplepoly` | 1 | – | Shamos–Hoey self-intersection test ([L737–755](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L737-L755)). |
| `sigmas <file>` | none | – | Binary file of the $n-3$ solved $\sigma$. Read as the initial guess if present and the right length; written after a solve ([L823–826](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L823-L826), [L1400–1403](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1400-L1403), [L1480–1490](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1480-L1490)). σ depends only on the polygon after thinning and splitting, never on the corners or nx/ny, so it can be reused when only those change (help item 7, [L381–384](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L381-L384)). |
| `rectangle <file>` | none | – | Writes the image-region corner coordinates as text ([L828–831](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L828-L831), [L1914–1918](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1914-L1918)). |
| `nppe` | 3 | – | Points per internal edge used to draw curved images of the quadrilaterals for point location; 0 means straight-line images ([L833–835](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L833-L835); explained in the struct comment [L200–238](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L200-L238)). |
| `geographic <lon0> <lat0>` | off | – | Input is lon/lat. The code projects it stereographically onto a **unit sphere** with tangent point (lon0, lat0), the "South Pole" in the code's wording, and converts nodes back at output ([L645–675](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L645-L675), [L681–697](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L681-L697); `ll2xy`/`xy2ll` [L591–625](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L591-L625)). Stereographic is conformal, so orthogonality survives the round trip. CLI only; the library entry point has no projection. |

The `-h` help text ([L338–347](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L338-L347)) still shows `nnodes` 12 and `precision` 1e-10. The code defaults are 10 and 1e-12, changed in v1.42 ([CHANGELOG L51–55](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/CHANGELOG#L51-L55)). Trust the code.

### 2.3 The input polygon file

[`vertlist_read`, vertlist.c L218–251](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L218-L251) reads lines of `x y [beta[*]]`, separated by space, comma, semicolon or tab, and skips lines starting with `#`. A missing β means 0. A `*` attached to the β token (e.g. `1*`) makes that vertex the start of the list. Its image goes to $(0,1)$, the **upper-left** corner, and the edge to the next vertex points down (help remark 2). Excerpt from [examples/xy.1](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/examples/xy.1), an estuary with one channel:

```
-1.0 0.1 1*        <- upper-left grid corner
0.0 0.1
...
0.4713967368 0.2180787357 -1      <- reflex image corner (270 deg in the image)
...
1 1.1 1
2.0 1.1 1
...
```

### 2.4 The pipeline, step by step

The driver is [`gridgen_generategrid`, gridgen.c L2308–2408](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2308-L2408). The library variant [`gridgen_generategrid2`, L2412–2517](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2412-L2517) has the same body.

**a. Read, project, orient, clean.** All of this happens in `gridgen_create`. After the optional projection, a clockwise polygon (negative shoelace area) is reversed with its first vertex kept first ([L711–718](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L711-L718); [`vertlist_change_order`, vertlist.c L300–315](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L300-L315)). Then thinning and the simplicity check run. The vertex limit is 3–10000 ([L52–53](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L52-L53)).

**b. Image corners.** [`get_rpoints`, L973–1046](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L973-L1046):
- every vertex with $\beta^g\ne0$ is an image corner;
- it requires $\lvert\beta^g\rvert\le2$, at least 3 corners, and $\lvert\sum\beta^g\rvert=4$ within 1e-6;
- it then rescales all β by $\sum/4$. A sum of exactly −4 is therefore accepted and every sign flipped. That is undocumented, but it follows from [L1006–1018](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1006-L1018).

**c. CRDT edge splitting, then triangulation.**
- [`vertlist_process_phase1`, vertlist.c L384–443](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L384-L443): at every vertex where $\cos(\text{angle})>1/\sqrt2$ (interior angle under 45°), insert a point on each adjacent edge at half the shorter edge length and mark the vertex `protected`.
- [`vertlist_process_phase2`, L478–566](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L478-L566): if the nearest vertex of the triangles at the edge's first endpoint is closer than $\ell/(3\sqrt2)$ to an unprotected edge, trisect it and recurse.

These are CRDT §3's rules. The paper measures $d(e)$ geodesically to all foreign vertices; gridgen uses Euclidean distance to vertices of nearby triangles only. Inserted vertices get $\beta^g=$ NaN, so they are never corners. The final triangulation is [`vertlist_triangulate`, L445–476](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L445-L476), with the polygon edges as segments.

**d. Physical angles.** [`calculate_betas`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1048-L1092) sets $\beta_k=\alpha_k/\pi-1$ for every vertex, and [`gridgen_check`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1574-L1594) asserts $\sum\beta_k=-2$.

**e. Quadrilaterals and target cross-ratios.**
- [`set_quadrilaterals`, L1094–1215](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1094-L1215): every triangulation edge whose vertex indices aren't consecutive is a diagonal. Its two triangles make `quadrilateral{vids[4], tids[2]}`, with the diagonal running `vids[0]`–`vids[2]` (struct [L79–93](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L79-L93)). Two quadrilaterals are neighbours if they share a triangle.
- `nquadrilaterals = npoints - 3` ([L2362](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2362)).
- [`calculate_cis`, L1217–1245](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1217-L1245) computes $c_i=\ln\lvert\rho(z)\rvert$ with exactly CRDT's ρ ([L1239](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1239)).

**f. Quadrature setup.** [`sc_create`, swcr.c L273–300](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L273-L300) precomputes a Gauss–Jacobi rule with weight $(1+x)^{\beta_k}$ for each vertex, so the endpoint singularity at a prevertex is integrated exactly, plus one Gauss–Legendre rule. Nodes come from Golub–Welsch. The integral from $w_0$ to $w_1$ ([`sc_integrate`, L445–456](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L445-L456)):
- is split at the midpoint, so each half starts at its (possibly singular) endpoint;
- each half is subdivided so no piece is longer than the distance to the nearest other prevertex ([`sc_integrate_`, L408–438](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L408-L438)).

This is Trefethen's compound Gauss–Jacobi scheme from SCPACK (header [L12–18](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L12-L18)). The integrand loops over all $n$ prevertices ([`sc_prod`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L327-L347)), so every map evaluation costs $O(n\cdot\texttt{nnodes}\cdot\#\text{subintervals})$.

**g. The CRDT solve.** [`find_sigmas`, L1384–1503](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1384-L1503) with residual [`F`, L1351–1382](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1351-L1382). For each quadrilateral $i$, `F` calls:
- [`calculate_fi`, L1300–1324](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1300-L1324) to build embedding $E_i$. It sets $\alpha=\arctan\sqrt{e^{\sigma_i}}$ and places `vids[0..2]` at $\pm\cos\alpha\pm i\sin\alpha$, the centred rectangle of §1.7 d.
- [`process_quadri`, L1247–1298](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1247-L1298), which recursively places every other prevertex over the neighbour graph using Lemma 2's $d=(hc+a)/(h+1)$ ([L1258–1261](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1258-L1261)). If two prevertices are bit-identical (crowded), the new one is set equal to them. The comment there reads: "crowding … occurs for quadrilaterals far from the starting one … and can be safely ignored".
- [`calculate_dzetas`, L1331–1349](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1331-L1349), which integrates from 0 to the quadrilateral's four prevertices and fits $B_i=(z_2-z_0)/(\zeta_2-\zeta_0)$ and $A_i$ on the diagonal. That is CRDT step 4, done on every residual evaluation.

All $n-3$ embeddings are kept (`gg->ws`, size $(n-3)\times n$, [L1405](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1405)), along with every $(A_i,B_i)$. Residual: $F_i=\ln\lvert\rho(\zeta)\rvert-c_i$ ([L1368](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1368)). The iteration ([L1423–1467](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1423-L1467)):
- starts from $\sigma=c$, or cached sigmas;
- with `newton 0`, iterates $\sigma\leftarrow\sigma-F$, CRDT eq. 7;
- with `newton 1`, calls [`broyden_update`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/broyden.c#L37-L79) starting from $W=-I$ ([L1409–1416](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1409-L1416)), i.e. Shortcut CRDT;
- stops when $\lVert F\rVert_2\le$ `precision`, with **no iteration cap**.

One residual evaluation costs $(n-3)$ full $O(n)$ embeddings plus $4(n-3)$ SC integrals, so roughly $O(n^2)$.

**h. Image polygon and modulus.**
- [`set_newbetas`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1627-L1646) sets $\tilde\beta=-\beta^g/2$, and `newsc` is a second `swcr` with these exponents ([L2395](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2395)).
- [`calculate_newzs`, L1822–1935](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1822-L1935) picks a quadrilateral containing the first corner and its next vertex ([`get_first_quadrilateral`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1648-L1683)). In that quadrilateral's embedding it sets $\tilde A,\tilde B$ so the first corner lands at $i$ and the next vertex at $0$ ([L1853–1878](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1853-L1878)). So **the first polygon segment after the corner has length 1 in the image** and fixes the image's arbitrary scale.
- [`calculate_zs`, L1706–1738](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1706-L1738) walks the quadrilateral graph. Each neighbour gets its $(\tilde A,\tilde B)$ from its diagonal endpoints, which are already placed, and contributes one new image vertex. This is CRDT §9's multiplicative propagation.
- [`align_newzs`, L1765–1811](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1765-L1811) cleans up rounding. Corner coordinates within 5·eps of 0 or 1 snap to it, and every vertex on an axis-parallel image side gets its x (or y) set exactly equal to the side's.
- The conformal modulus, (xmax − xmin)/(ymax − ymin) of the image corners, is printed with `-v` ([L1910–1912](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1910-L1912)). The corners also go to the `rectangle` file or the library's `xrect`/`yrect` ([L1914–1932](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1914-L1932)).

**i. Approximate images of the quadrilaterals** ([`map_quadrilaterals`, L2082–2243](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2082-L2243)). To pick the right local map for an image point, gridgen must know which quadrilateral's image contains it. For each diagonal it:
1. puts `nppe` points on the *physical* straight diagonal;
2. inverts the physical map (`sc_z2w` with `gg->sc`) in that quadrilateral's embedding;
3. maps forward with the rectified map.

The result is a polygon approximating each quadrilateral's curved image. Polygon edges need no extra points, because they map to straight image sides.

**j. Grid nodes** ([`generate_grid`, L2245–2306](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2245-L2306)). Over the bounding box of the image corners, with $dzx=W/(n_x-1)$ and $dzy=H/(n_y-1)$, loop `j` (y, bottom to top) outer and `i` (x, left to right) inner. For each lattice point $\zeta$:
1. Snap it onto the bounding-box edges if within eps ([`align_onboundaries`, L2064–2080](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2064-L2080)).
2. If `in_poly(ζ, image corners)` is false, output `NaN NaN`: **masking**, [L2278–2282](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2278-L2282).
3. Otherwise call [`map_point`, L1990–2062](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1990-L2062):
   - `z2q` finds the image quadrilateral $q$ containing $\zeta$, searching from the last hit so consecutive nodes are cheap ([L1954–1970](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1954-L1970)). **If none contains it, the whole program exits.**
   - If $\zeta$ is within eps of one of $q$'s image vertices, use that prevertex directly. This makes the grid corners exact.
   - Otherwise invert the rectified map in embedding $E_q$ with [`sc_z2w`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L526-L603). It first runs a **secant iteration** seeded with (nearest vertex image, its prevertex) and ($\tilde A_q$, 0); at most 20 steps, and it gives up if $\lvert w\rvert>2$ ([L538–566](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L538-L566)). Failing that, it integrates the **inverse ODE** $dw/d\zeta = 1/\tilde f'(w)$ with DOPRI8 along the straight image segment from $\tilde A_q$ (where $w=0$) to $\zeta$ ([L585–597](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L585-L597); RHS `f` [L487–502](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L487-L502); path parameterisation [zode.c L73–94](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/zode.c#L73-L94)).
   - Then **evaluate the physical map forward**: $z=A_q+B_q\int_0^w\prod(1-\omega/w^{(q)}_j)^{\beta_j}d\omega$ in the same embedding ([L2040–2045](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2040-L2045)). If the ODE also fails (status 2), the node is `NaN NaN` ([L2046–2047](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2046-L2047)).
4. Write the node, unprojected if `geographic` ([`output_point`, L1972–1988](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1972-L1988)). The output starts with `## nx x ny` and has one `x y` line per node.

Boundary nodes land on the coastline **automatically**: the SC map sends each straight image side onto its polygon side. There is no explicit snapping onto the polygon, unlike Dan's code.

### 2.5 Masking, and what −1 corners do

```
  image plane (bounding box of corners); '.' = node written as NaN NaN

  (0,1) *--------------------------------*
        |                                |
        |       image region             |        a channel entering at the
        |                                |        bottom right, given its own
        *----------------*  . . . . . . .|        rectangular arm by two
                    -1 ->|  . . . . . . .|        -1 corners
                         |  . . . . . . .|
                         *---------------*
```

Masking is a single point-in-polygon test against the image corners. That test is exact because image sides between corners are straight. With four +1 corners the image fills its bounding box and **nothing is masked**. Masking appears only with −1 corners or non-right angles. Two consequences follow from `generate_grid` (my inference, not stated in the docs):

- The reflex image corners sit wherever the map puts them, generally *not* on lattice lines. Along those inner image sides, the edge of the unmasked grid is a staircase that comes within one cell of the true side without following it, so those grid edges don't lie exactly on the coastline.
- Non-right image angles (e.g. example 4's triangle) give a lattice clipped by slanted sides, with no lattice line along them.

### 2.6 How the conformal modulus is reported, and an orientation trap

The printed value is the image **width/height** ([L1912](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1912)). Width runs along the lattice's `i`/`nx` direction ([L2264–2275](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2264-L2275)). Square cells need $W/(n_x-1)=H/(n_y-1)$, i.e.

$$\frac{n_x-1}{n_y-1}\approx\text{printed modulus}.$$

[README L93–95](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/README#L93-L95) says the opposite: "make the ratio (ny − 1) / (nx − 1) close to this number". The code's convention is backed by:
- example 6's generator, which sets $dy=dx\cdot\text{mod}$ in normalized index space ([mkprotogrid.6.awk L1–28](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/examples/mkprotogrid.6.awk#L1-L28));
- example 3, the elongated shape from the CRDT paper, which uses `nx 200`, `ny 40` ([prm.3](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/examples/prm.3)).

Tracing the corners of xy.3 by hand, its image is wide and short. I did not run it, so whoever runs gridgen should confirm with `-v`.

Orientation: the `*`/`ul_idx` corner is the image's upper-left, its next side is the image's left side, and the lattice's row 0 is the image's bottom. In Dan's notation, that is gridgen's printed modulus $=W/H=1/\texttt{aspect}$, when gridgen's first side is Dan's W side.

### 2.7 The custom node-spacing (`grid`) file

When `grid` is given, the file is read as `x y` points in $[0,1]^2$, also through `vertlist_read`, so `#` lines are skipped ([L781–794](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L781-L794)). Each point becomes $\zeta = (x_{\min}+xW) + i(y_{\min}+yH)$ in the image bounding box, then goes through the same mask and `map_point` steps, in file order ([L2285–2302](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2285-L2302)). No header is written; example 6 adds one with [`addheader.sh`](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/examples/addheader.sh) ([makefile L15–18](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/examples/makefile#L15-L18)).

The code accepts *any* point set. Only a tensor product $\{(x_i, y_j)\}$ gives curves that are images of image-space coordinate lines and so meet at right angles. Example 6 is such a set: x uniform, with y spacing varying as $1+(a-1)\sin^2(\pi y)$, $a=2$. The resulting grid is **orthogonal but no longer conformal**, since cell aspect varies. README item 4 calls this the main way to control cell density besides moving corners ([L52–80](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/README#L52-L80)).

### 2.8 Smaller things noticed while reading

These are minor; none changes the method.

- **`nppe` is ignored by the library entry point.** `gridgen_create2` takes an `nppe` argument and never assigns `gg->nppe` ([L845–969](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L845-L969)), so the default 3 from [`gridgen_init` L581](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L581-L582) is always used. `create2` also skips the precision clamp, and it has no geographic option.
- `sc_z2w` checks `abs(w) > 1.0 + eps` with integer `abs` on a complex value ([swcr.c L572](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/swcr.c#L572)). That truncates Re w to int, so the check almost never fires; `cabs` was presumably meant.
- The phase-2 split loops `ii` over the edge's two endpoints but indexes the triangles with `i`, so only the first endpoint's triangles are checked twice ([vertlist.c L510–524](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L510-L524)).
- `newton > 1` allocates an $n\times 8$ buffer that `broyden_update` then treats as $n\times n$ ([L1417–1418](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1417-L1418)). It looks like an unfinished limited-memory Broyden; use only 0 or 1.
- The nonlinear loop has no maximum iteration count ([L1467](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1467)).

---

## 3. pygridgen

`Gridgen(xbry, ybry, beta, shape, ul_idx=0, focus=None, proj=None, nnodes=14, precision=1e-12, nppe=3, newton=True, thin=True, checksimplepoly=True, verbose=False, autogen=True)` ([grid.py L708–862](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L708-L862)).

**Mechanics.** It loads `libgridgen.so` with `numpy.ctypeslib.load_library`, trying `sys.prefix/lib` and then `/usr/local/lib` ([L803–818](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L803-L818)). It makes one ctypes call to `gridgen_generategrid2` ([L959–983](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L959-L983)), then reads nodes back with `gridnodes_getx/gety` from the gridutils library and reshapes them to `(ny, nx)` ([L985–993](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L985-L993)). The library entry point only exists if gridgen-c was built against gridutils' `gridnodes.h` ([configure.in L65–72](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/configure.in#L65-L72)).

| Python argument | C argument (`gridgen_generategrid2`) | Effect / caveat |
|---|---|---|
| `xbry, ybry` | `xbdry, ybdry` | after `proj` if one is given ([L831–833](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L831-L833)) |
| `beta` | `beta` (= $\beta^g$) | Python checks the sum ≈ 4 ([L836–838](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L836-L838)) |
| `ul_idx` | `ul` → `vertlist_setfirstnode` ([gridgen.c L854–855](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L854-L855); [vertlist.c L568–577](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/vertlist.c#L568-L577)) | Replaces the file's `*`. Rotates the list so this index is first; the first **corner** at or after it becomes the image's upper-left. Put it on a +1 vertex. |
| `shape=(ny, nx)` | `nx, ny` | **node** counts. The docstring says "number of cells", but C builds `nx×ny` nodes ([L954–957](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L954-L957), [L2261–2284](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L2261-L2284)) and Python reshapes to `(ny, nx)`. |
| `focus` | `ngrid, xgrid, ygrid` | see below |
| `nnodes` (14) | `nnodes` | clamped to [5, 20] in C |
| `precision` | `precision` | **not** clamped on this path |
| `newton` (bool) | `newton` | True → 1 → Broyden |
| `thin`, `checksimplepoly` | same | The `thin` docstring ("Toggle to True when … narrow in one dimension") doesn't match the C code, which only removes near-duplicate vertices (§2.2). |
| `nppe` | `nppe` | **no effect** (§2.8) |
| `verbose` | `gridgen_setverbose` | `verbose ≥ 1` prints the conformal modulus to stderr, the only way pygridgen shows it |
| (internal) `sigmas, nsigmas` | `double** sigmas, int* nsigmas` (byref) | C allocates and returns the solved σ ([L1496–1502](https://github.com/sakov/gridgen-c/blob/222cc71f859d6f483a7ba7a435e5cb9f41977906/gridgen/gridgen.c#L1496-L1502)); Python keeps them on the object, so calling `generate_grid()` again after changing `shape` or `focus` warm-starts the solve ([L937–940](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L937-L940)) |
| (internal) `nrect, xrect, yrect` | image corners | passed byref, then **discarded**: they are local variables ([L942–945](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L942-L945)) |

NaN nodes become `numpy.ma` masked arrays ([L995–998](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L995-L998)). With `proj`, the returned grid stays in **projected** coordinates; `Gridgen` does not unproject.

**How `focus` is implemented** ([L44–219](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L44-L219); used at [L947–957](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L947-L957)):
1. Build a uniform `mgrid` of `ny×nx` points on $[0,1]^2$.
2. Pass it through each `_FocusPoint` in turn. Each point stretches **one** axis with
   $$s\mapsto s-\tfrac{\sqrt\pi}{2}\,e\,\big(1-\tfrac1{f}\big)\,\mathrm{erf}\!\big(\tfrac{s-p}{e}\big),$$
   renormalised so 0 → 0 and 1 → 1 ([L90–98](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L90-L98)). $p$ is the position, $e$ the extent, $f$ the factor, and erf is an analytic approximation ([L20–41](https://github.com/pygridgen/pygridgen/blob/18d78c7737a4ee1722ec73238ea689a6527d025f/pygridgen/grid.py#L20-L41)).
3. Hand the result to C as a custom `grid` point set (§2.7).

The derivative of that stretch is $1-(1-1/f)\,e^{-((s-p)/e)^2}$, which equals $1/f$ at $s=p$. Cells are about $f$ times smaller at the focus, with a Gaussian-shaped transition. Each map touches one axis only, so the point set stays a tensor product: **orthogonality is kept, square cells are given up**. Focus lives entirely in index space; the C solver never sees it.

---

## 4. gridgen in pseudocode

```
gridgen(P = [(x_k, y_k, βg_k)], nx, ny or gridpoints, eps, nnodes, newton):
  if geographic: P ← stereographic(P; tangent at lon0,lat0)       # unit sphere
  P ← make_ccw(P); P ← thin(P); assert simple(P)
  corners ← {k : βg_k ≠ 0};  assert |Σ βg| = 4                     # image turning, quarter turns
  P ← split(P)          # chop angles < 45°; trisect edges with d(e) < ℓ/(3√2); new vertices βg = 0
  T ← constrained_delaunay(P)            # vertices only: n-2 triangles, n-3 diagonals
  Q_i ← two triangles on diagonal i      # quadrilateral graph: neighbours share a triangle
  β_k ← α_k/π − 1 (all vertices, from geometry);   c_i ← ln|ρ(z of Q_i)|
  σ ← cached sigmas or c
  repeat                                                # CRDT parameter problem
    for each i:
      E_i ← embed(σ): Q_i as rectangle about 0, others via d = (hc+a)/(h+1)
      ζ ← ∫_0^{w} Π(1−ω/w_j)^{β_j} dω at Q_i's 4 prevertices in E_i
      F_i ← ln|ρ(ζ)| − c_i ;   (A_i, B_i) ← affine fit of ζ → z on Q_i's diagonal
    σ ← σ − F(σ)  [newton 0]   or Broyden step with J₀ = I  [newton 1]
  until ‖F‖₂ ≤ eps
  β̃_k ← −βg_k/2 (0 off corners)                       # rectified map, same prevertices
  image vertices: first corner ↦ i, next vertex ↦ 0; (Ã_i, B̃_i) propagated over quadrilateral graph
  modulus ← width/height of bbox(image corners)          # printed with -v only
  quasi-images of Q_i ← map nppe points on each diagonal: z → w (E_i) → ζ
  for ζ in uniform nx×ny lattice on bbox  (or user points scaled into bbox):
    if ζ ∉ image polygon:  emit NaN;  continue                     # masking
    q ← quadrilateral whose quasi-image contains ζ
    w ← solve Ã_q + B̃_q ∫_0^w Π(1−ω/w_j)^{β̃_j} dω = ζ   (secant; else DOPRI8 ODE from w=0)
    z ← A_q + B_q ∫_0^w Π(1−ω/w_j)^{β_j} dω            # same embedding E_q
    emit unproject(z)
```

---

## 5. Step-by-step correspondence with Dan's `_conformal.py`

Line numbers refer to `mom6_forge/_conformal.py` at `db0db39e`.

| # | Step | gridgen-c | Dan's `_conformal.py` | Difference that matters |
|---|---|---|---|---|
| 1 | Inputs | polygon + $\beta^g$ on every corner (≥3 corners, ±1 or other values, Σ = 4); first corner set by `*`/`ul_idx` | lon/lat outline + exactly 4 corner indices (`_validate_and_orient` L347–372). `order_corners` (L260–265) makes the SW corner (smallest x + y) first. | Dan supports only 4 corners and no −1 (reflex image) corners. Corner orientation is automatic, not user-chosen. |
| 2 | Map plane | CLI: unit-sphere stereographic (`geographic`); library: none (pygridgen's `proj` with no unprojection) | `projection_for` / `as_projection` (L132–225): lcc, merc, tmerc or stere on WGS84. `Grid.from_outline` picks the kind with the least cell-size spread via `size_ratios` (L589–618). Unprojects at the end of `solve` (L567). | Both use conformal projections, so orthogonality on the Earth is kept. Dan's is ellipsoidal and chosen automatically; gridgen leaves it to the user. |
| 3 | Orientation and validity | reverse if clockwise; thin; Shamos–Hoey | `orient_ccw` (L240–247), `is_simple` via shapely (L234–237), dateline unwrap and pole handling (L105–129) | gridgen has no dateline or pole handling. |
| 4 | Boundary refinement | CRDT splitting for **conditioning** (angles < 45°, $\ell/(3\sqrt2)$ rule) | `_sides` (L375–390) adds points about $h$ apart for **resolution** | Different purpose: gridgen's extra vertices are SC bookkeeping; Dan's are FEM degrees of freedom. |
| 5 | Triangulation | constrained Delaunay of polygon vertices only (no interior points); n−2 triangles. A data structure, not a discretisation | `_mesh` (L393–423): about `raster_points` (250k) nodes. Interior lattice squares plus a scipy Delaunay of the near-boundary band. | gridgen's mesh has no interior; Dan's mesh *is* the discretisation. |
| 6 | Unknowns | $n-3$ log cross-ratios σ (n = polygon vertices after splitting) | nodal values of ξ and of η, about 250k each | Few unknowns with an expensive residual, versus many unknowns in a linear system. |
| 7 | Equations and solver | nonlinear $F_i=\ln\lvert\rho(\zeta)\rvert-c_i$; simple iteration or Broyden from $J=I$; each residual is $O(n^2)$ | `_stiffness` (P1 Laplacian, L426–435) + `_harmonic` ×2 (L438–451): linear, sparse direct `spsolve`. ξ: 0 on W, 1 on E; η: 0 on S, 1 on N; zero flux elsewhere. | Dan's is linear and always solvable; CRDT convergence is a conjecture (CRDT §10). Dan's accuracy is limited by the mesh, gridgen's by `precision` (~1e-12). |
| 8 | Crowding | multiple embeddings, one per quadrilateral (§1.7 f) | not applicable: no disk and no prevertices | The underlying map is the same, so exponentially thin "dead-water" arms exist in both; it is a property of the map, not the method. |
| 9 | Image / modulus | rectified SC map with $\tilde\beta=-\beta^g/2$, affine constants propagated over the quadrilateral graph; modulus = W/H printed with `-v` | `aspect = sqrt(E_ξ/E_η)` (L471) = H/W = ny/nx (the `ConformalGrid` docstring says so, L280) | Reciprocal conventions: gridgen modulus = 1/`aspect`. Exactly $E_\xi E_\eta=1$, so the square root of the ratio averages the two estimates. (General FEM background, not checked against this code: conforming P1 energies are upper bounds of the exact ones.) |
| 10 | nx, ny | **user-supplied node counts**; square cells need $(n_x-1)/(n_y-1)\approx$ modulus | **automatic**: `nx = round(sqrt(n_cells/aspect))`, `ny = round(nx·aspect)` (L473–474), from `n_cells` or `resolution_km` (`n_cells_for_resolution` L318–334). nx and ny are **cell** counts. | Dan automates exactly the step gridgen leaves to the user. |
| 11 | Computational lattice | uniform over the image bounding box, or user `grid` points / pygridgen `focus` | uniform supergrid $(2n_y+1)\times(2n_x+1)$ on $(\xi,\eta)\in[0,1]^2$ (`solve` L548–550) | Dan has no custom-spacing hook. |
| 12 | Getting x, y at a lattice point (the inverse map) | per node: find quadrilateral image (`z2q`), invert rectified SC (secant, then ODE), forward physical SC in the same embedding | `_sample` (L480–506): for every mesh triangle's image in (ξ, η) space, find the lattice points inside and interpolate (x, y) barycentrically. A **piecewise-linear inverse**, vectorised. | gridgen inverts point by point, exactly, at $O(n)$ per evaluation. Dan inverts all points at once by "triangle rasterisation", with accuracy set by the mesh. |
| 13 | Points with no preimage | outside the image polygon → NaN (masking); failed inversion → NaN; no containing quadrilateral → exit | points in no triangle image → coordinates of the nearest mesh node (`solve` L551–555) | gridgen flags failures with NaN, while Dan's code quietly substitutes the nearest node. |
| 14 | Boundary nodes | on the coastline **by construction** (SC maps image sides onto polygon sides) plus `align_onboundaries` snapping in image space | **explicit snapping**: each side's nodes placed by arc length where the side's ξ or η equals the uniform values (`solve` L556–563) | gridgen gets this for free; Dan needs a post-processing step. |
| 15 | Corners | exact: `map_point` uses the prevertex directly when ζ is within eps of a vertex image | pinned: `XY[corners] = P[corners]` (L565) | Equivalent outcome. |
| 16 | Corner-angle singularity | inherent, $dz/d\zeta\propto\zeta^{2\alpha/\pi-1}$; README advises 90° corners | inherent as well. `corner_angles` is recorded (L465) but `Grid.from_outline` (grid.py L645–706) doesn't warn about it. | The `ConformalGrid.h` docstring says "finer round singular vertices" (L282), but `_sides`/`_mesh` use a single uniform `h`. Worth checking during review. |
| 17 | Reuse across runs | `sigmas` cache, independent of corners and nx/ny | the mesh and fields don't depend on `n_cells` (`_solve_mesh` L454–477), but are recomputed on every call; corners change the boundary conditions | A cache in the style of `sigmas`, keyed on (outline, corners, projection), would make trying several resolutions cheap. |
| 18 | Output | text `x y` (+ NaN) or gridnodes arrays | `ConformalGrid` supergrid in lon/lat and projected x/y | |

Dan's pipeline in the same style, for laying side by side with §4:

```
_validate_and_orient → as_projection → to_xy → order_corners
_sides (h-spaced boundary) → _mesh (lattice + Delaunay band) → _stiffness (P1)
ξ, E_ξ ← _harmonic(K, W→0, E→1);  η, E_η ← _harmonic(K, S→0, N→1)
aspect ← √(E_ξ/E_η);  nx, ny ← from n_cells and aspect
XY ← _sample: barycentric (x,y) at uniform (ξ,η) supergrid, inside mesh-triangle images
fallback: nearest node;  snap outer rows/cols onto sides by arclength;  pin 4 corners
to_lonlat
```

---

## 6. What gridgen does that a MOM6 grid doesn't need, and what it does that MOM6 could use

**Not needed for MOM6:**

- **−1 (reflex) and non-right-angle image corners, and the masked bounding-box nodes that come with them.** A MOM6 `ocean_hgrid.nc` needs finite coordinates at every supergrid point; land comes from the topography mask, not from missing coordinates. gridgen's NaN nodes would have to be filled with made-up positions that correspond to no real geography. The inner image sides also aren't on lattice lines (§2.5), so those parts of the grid don't follow the coastline. Dan's 4-corner restriction gives up nothing MOM6 can use directly. The price is that a side arm off the main domain gets almost no cells (dead water), which is a property of any 4-corner conformal map.
- **CRDT's anti-crowding machinery.** It is needed only for SC representations of strongly elongated domains (channels more than about 10 widths long). Dan's FEM route has no prevertices, so it can't crowd. Its loss of resolution in long arms is the map's own behaviour and shows up identically in gridgen.
- **Precision to 1e-12 in the map.** Grid metrics in MOM6 are computed from the node positions. A conformal map accurate to the mesh resolution gives orthogonality to a similar tolerance. This is an argument about engineering, not a measurement.
- **The unit-sphere stereographic option.** Dan's choice of WGS84 conformal projections covers it and does better.

**Could be used:**

- **Custom node spacing in index space** (gridgen `grid` file, pygridgen `focus`). Any per-axis stretching $\xi\mapsto s(\xi)$, $\eta\mapsto t(\eta)$ of the lattice keeps the grid orthogonal, and cell aspect is then $s'/t'$ instead of 1. That is the only resolution control gridgen offers besides moving corners. For MOM6 it would give refinement near a coast or an open boundary without losing orthogonality. In Dan's code the lattice is hard-wired as uniform: `_sample` takes `lo + step·(i, j)`. A stretched lattice would need either a sampler that takes arbitrary (ξ, η) points, or sampling on a fine uniform lattice followed by 1D interpolation per axis.
- **Telling the user the modulus and the corner angles.** gridgen hides the modulus behind `-v`, and Dan's code already turns it into nx and ny, which is better. The README's corner-angle advice (keep corners near 90°, because the exponent is $2\alpha/\pi-1$) could become a warning in `from_outline`, since `corner_angles` is already computed.
- **Caching the expensive solve** (`sigmas`): independent of resolution, so several resolutions can be tried cheaply.
- **Boundary exactness by construction** is a strength of gridgen; Dan's code gets the same result with explicit arc-length snapping. Nothing to adopt, but this is one place the two outputs can be compared directly: nodes on the outline, corner positions.

---

## 7. What the source does not settle

- **README vs code on the modulus ratio** (§2.6). I derived the code's convention by reading it and checked it against examples 3 and 6. I didn't run gridgen. Running `gridgen -v prm.3` and comparing the printed modulus with nx=200, ny=40 would settle it.
- **Convergence.** Neither the code nor the paper proves that the CRDT iteration converges or that the Jacobian is close to I. The paper calls it a conjecture, supported by experiments (§7, §10). The code has no iteration cap.
- **gridutils** (`gridnodes_create`, `gridnodes_getx`) wasn't inspected. I assume the contiguous storage that pygridgen's `x[0][i]` read relies on but didn't verify it.
- **conda-forge builds** of gridgen/pygridgen may carry patches, e.g. for the `nppe` issue; I didn't check the feedstocks.
- **DOPRI8 internals** (step control, failure modes): I read only the header and the call site.
- **Whether the phase-2 `i`/`ii` indexing and the `abs(w)` check are deliberate.** The code reads like oversights, but there is no comment either way.
- **How well gridgen's per-node maps join up across quadrilateral boundaries.** At convergence the local maps agree up to `precision`. Nothing in the code checks how much adjacent nodes mapped with different embeddings disagree.
- **The FEM upper-bound remark** in §5 row 9 is general finite-element theory and wasn't verified against `_mesh`. Whether the mesh domain exactly matches the polygon near reflex vertices wasn't checked.

---

### Sources

- gridgen-c source at [`222cc71f`](https://github.com/sakov/gridgen-c/tree/222cc71f859d6f483a7ba7a435e5cb9f41977906): `gridgen/README`, `CHANGELOG`, `gridgen.c`, `swcr.c`, `broyden.c`, `ode.c`, `zode.c`, `vertlist.c`, `delaunay.c`, `geom.c`, `triangle.c` (switch docs), `examples/`.
- pygridgen source at [`18d78c77`](https://github.com/pygridgen/pygridgen/tree/18d78c7737a4ee1722ec73238ea689a6527d025f): `pygridgen/grid.py`, `README.rst`, `tests/test_focus.py`.
- T. A. Driscoll & S. A. Vavasis, *Numerical conformal mapping using cross-ratios and Delaunay triangulation*, SIAM J. Sci. Comput. 19(6):1783–1803, 1998. Readable copy: [math.stonybrook.edu/~bishop/classes/math401.F09/crdt.pdf](https://www.math.stonybrook.edu/~bishop/classes/math401.F09/crdt.pdf). Preprint: [NASA NTRS 19960020954](https://ntrs.nasa.gov/api/citations/19960020954/downloads/19960020954.pdf).
- T. A. Driscoll & L. N. Trefethen, *Schwarz–Christoffel Mapping*, Cambridge University Press, 2002. General background; not quoted here.
- `mom6_forge/_conformal.py` and `mom6_forge/grid.py` (`Grid.from_outline`) in `regional_mom_workflows/mom6_forge-worktrees/conformal-solver` at `db0db39e`.
