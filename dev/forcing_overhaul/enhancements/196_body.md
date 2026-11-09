Tracks the CESM changes CrocoDash needs, until they are upstream. Until then, CrocoDash builds against the `crocodash` branch of CROCODILE-CESM/CESM, which carries all of them.

Status on 2026-11-09:

- [ ] **MARBL OBC tracers**, plus the NUOPC cap change for GLOFAS: NCAR/MOM6#404. Approved 2026-09-08, not merged.
- [ ] **Regional tests, %REGIONAL compsets, input.nml and MOM_input defaults, PE layouts**: ESCOMP/MOM_interface#316 (open). It replaces CROCODILE-CESM/MOM_interface#9 and the `workshop_2025` branch.
  - #350 makes CrocoDash set the PE layout itself, so the regional PE layouts can come out of ESCOMP/MOM_interface#316 once #350 merges.
- [ ] **User-resolution grid for visualCaseGen** (so CrocoDash doesn't edit ccs_config): merged on our fork in CROCODILE-CESM/ccs_config_cesm#3. No upstream PR yet.
- [ ] **GLOFAS grid** (ccs_config) **and the CDEPS and CICE changes**: only on our forks' `workshop_2025` branches. No upstream PRs yet. Related: CROCODILE-CESM/CDEPS#3 (interannual stream years, draft).

Blocker noted in May 2026: the regional OBC exact-restart (ERS) failure. In June it was traced to the OBC-exterior thickness halo that `vertvisc_coef` reads in MOM_vert_friction.F90. A fix is in progress.
