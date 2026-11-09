# Open issues on neither board: walk-through (2026-11-09)

The 33 open issues in CrocoDash, mom6_forge, regional-mom6 and visualCaseGen that are on
neither project #10 (1.0.x) nor #9 (1.1), decided one at a time with the user. Nothing goes to
GitHub until the walk-through is done.

**Applied on GitHub 2026-11-09** (and checked from the project side). #250 shows "In progress" on #9 because
the board's "pull request linked" workflow moved it when #326 got "Closes #250".

| # | Issue | Decision |
|---|---|---|
| 1 | CrocoDash #123, unified BGC climatology product | Leave alone for now: needs thought (where BGC comes from when physics is GLORYS) |
| 2 | CrocoDash #132, Great Lakes BGC data | Leave alone: same BGC-source question as #123 |
| 3 | CrocoDash #133, tides from non-TPXO datasets | #9 Backlog, no sprint (after #362 and rm6 #15 land). Proposed comment: FES2022 as the first dataset |
| 4 | CrocoDash #137, resource estimates for large workflows | #9 Backlog. Comment: identify the resource allocations (memory, time) each step needs, to think about |
| 5 | CrocoDash #155, second IC fill through mom6_forge | #9 Backlog. Work: move the fill into the rm6 fork's setup_initial_condition (the fork already depends on mom6_forge) |
| 6 | CrocoDash #160, git hooks for environment changes | Close. Comment: hooks only help developers who install them; #307's locked environment is the fix for drift; reopen if it still bites after #307 |
| 7 | CrocoDash #187, optimize runoff mapping | Close for now: runoff mapping has been optimized |
| 8 | CrocoDash #189, self-describing mom6_forge output | #9 Backlog, retitled to what's left: write mom6_forge's version into the hgrid, topo and vgrid files (git logging is off by default since mf #65; vgrid attrs and dump→create rebuild already work) |
| 9 | CrocoDash #193, Kate's grid generation tools | Close. Comment: we're using Dan's AI-coded grid tools instead (GridSketcher) |
| 10 | CrocoDash #196, CESM integration tasks | #9 Backlog. Keep as the upstreaming tracker; rewrite the body as a current checklist (draft: enhancements/196_body.md), maybe retitle "Upstream CrocoDash's CESM changes" |
| 11 | CrocoDash #212, offline TopoEditor edits and the mesh | #9 Backlog (docs, 1_grids.md): edit topo before creating the case; after, recreate the case, or rewrite topo + mesh at the case's paths and rerun process_forcings for runoff and IC (both use the mask) |
| 12 | CrocoDash #240, CIME_MACHINE needed on a laptop | Bug: #10 (1.0.x) Backlog. Want: on an unported host, CESM_NOT_PORTED means "configure, don't execute": no CESM case (vCG's show-commands is fine), but CrocoDash still writes grids and generates forcings, to move to a ported machine later. Fix: re-cut the parked #271 (branch cesm-not-ported-case: c73e962d + 2cc6201c) on main; leave out its no-cesmroot mode and test-suite changes |
| 13 | CrocoDash #241, GLORYS storage on GDEX | #9 Backlog as a measurement: time a year-long GLORYS fetch, open+decompress vs read; ask GDEX (or copy to scratch) only if decompression dominates |
| 14 | CrocoDash #247, monthly boundaries from daily data | #9 Sprint 2 next to #327, which closes it (a monthly snapshot is what's wanted, and #327's freq thins to that). Add "Closes #247" to #327's body |
| 15 | CrocoDash #248, Gustavo's G-compset runs | Keep; rewrite as "test CESM_MOM_OUTPUT with a global G-compset parent" (draft: enhancements/248_body.md: tripolar lon/lat, velocity rotation, z_l/zos names, calendar #368/#378, cadence #353, #373). #9 Backlog, after #353 and #368 |
| 16 | CrocoDash #250, configure_forcings on several cases | #9 Sprint 2 next to #326; add "Closes #250" to #326's body |
| 17 | CrocoDash #251, defaults tuned for NWA12 (truncations) | #9 Backlog: docs "Tuning for your domain" + one line in Case() output. Comment: QueryEarth (#320) will hopefully help with this |
| 18 | CrocoDash #290, post-workshop wishlist | Close. Comment: the rest is handled (args cleanup: Q9 #330/Q1; StreamYears + user_nl_blocks: #326 and ESMCI #52; mom6_forge from_* calls: mf #155; pyGridGen: dropped with #193; MARBL missing-data fill: with #123); IOWAGA won't be addressed for now |
| 19 | CrocoDash #298, mask_dataset on CESM POP output | #9 Sprint 3 next to #353; rerun a POP boundary case once #331 and #333 merge, close if it passes |
| 20 | mom6_forge #6, later plots land in the TopoEditor | Bug: #10 (1.0.x) Backlog. Fix: the editor shouldn't stay pyplot's current figure, and should restore the interactive mode it turned off (topo_editor.py:292-313) |
| 21 | mom6_forge #19, make Grid's name required | #10 (1.0.x) Backlog (user's call). Breaking: update visualCaseGen, notebooks and docs that call Grid() without a name |
| 22 | mom6_forge #29, grid projections | Close: shipped as Grid.from_projection in mf #56 (merged 2026-05-21) |
| 23 | mom6_forge #68, clean up mpi_set_from_dataset | Close. Comment: the ESMF file-type bug was fixed by mf #91; the function is now mpi_set_depth_from_xesmf with documented steps; leftover prints are cosmetic |
| 24 | mom6_forge #108, tracer row on the equator | Close: already possible, choose ystart = -(n + 0.5) * resolution |
| 25 | mom6_forge #123, mask edits as 2-D arrays | #9 Backlog, widened (comment): apply depth and mask edits as array operations; DepthEditCommand and MaskEditCommand both loop per cell in __call__ (edit_command.py:96-102, 239-251); #106 only fixed storage |
| 26 | mom6_forge #141, TRPL closure for tripolar WW3 grids | Off the board: global tripolar WW3 (Alper's CESM work); no CrocoDash case reaches it, and #114 already refuses tripolar grids |
| 27 | mom6_forge #154, GridSketcher requests | Off the board until GridSketcher's core merges; note it in dev/mom6_forge_gridsketcher/ROADMAP.md; reply to the min-depth question (draft: enhancements/mf154_reply.md; check raw depth keeps land heights before posting) |
| 28 | regional-mom6 #27, functional tests for every function | Close: hard to manage; tests grow with each fix (#15, #79), and CrocoDash's case tests cover real use |
| 29 | regional-mom6 #49, logging instead of prints | #9 Backlog. Note: regional_mom6.py's 33 prints match COSIMA upstream line for line, so converting them in the fork adds merge conflicts |
| 30 | regional-mom6 #61, setup_bathymetry drops lon attrs | Close: setup_bathymetry now uses mom6_forge's Topo.set_from_dataset, and mf #91 writes the units into bathymetry_original.nc |
| 31 | visualCaseGen #33, empty warning in RidgeWorld | Close: fixed by ESMCI/visualCaseGen #42 (stage_widget.py:347-352 returns quietly when nothing remains) |
| 32 | visualCaseGen #43, help screen has no horizontal scroll | Off the board: vCG GUI only (one-line overflow: auto fix) |
| 33 | visualCaseGen #44, rmax error printed but run succeeds | Off the board. Comment: the GUI should skip or clamp a suggestion outside its allowed range (5000 > 4000 km); the suggestion function is being looked at in NCAR/mom6_forge#163 |
