Use a global CESM G-compset run (MOM6 + CICE forced by JRA, e.g. Gustavo's) as the initial and boundary conditions of a regional CrocoDash case, through `CESM_MOM_OUTPUT`.

`CESM_MOM_OUTPUT` exists, but it was written for nesting in a regional parent. Things to check on a global tripolar parent, each a known gap:

- **Grid:** the reader takes the 1-D `xh`/`yh` axes as longitude and latitude (`cesm_ocean_output.py:155-185`). On a tripolar grid (tx2_3v2, tx0.66v1) that is wrong in the northern cap; it needs `geolon`/`geolat`.
- **Velocities:** `uo`/`vo` are grid-relative on a tripolar grid and need rotating to east/north, as #359 does for POP.
- **Variable names:** the product hard-codes `z_l` and `zos`. A CESM MOM6 run the 1.0.x audit looked at writes `z1_l` and `SSH`.
- **Calendar:** G cases are NO_LEAP, see #368. A Gregorian parent hits #378.
- **Cadence:** monthly means need #353's fix (1.1, early).
- **Missing variables** fail late with an unrelated error: #373.

Start after #353 and #368 land.
