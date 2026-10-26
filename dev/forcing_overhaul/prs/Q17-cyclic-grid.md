# Support cyclic-x grids with an open WW3 boundary

## Why

A Southern Ocean band that wraps in longitude (cyclic in x, with an OBC to the north)
did not run:
- **OBC:** `process_obc_conditions` asserted that the grid is not cyclic before computing
  the per-boundary download boxes. mom6_forge's `get_bounding_boxes`, which the IC step
  calls, refused cyclic grids too.
- **MOM6:** CrocoDash always set `OCN_CYCLIC_X = False`, so visualCaseGen wrote
  `REENTRANT_X = False` and the east/west seam stayed closed.
- **CICE:** the east/west boundary was always `zero_gradient`.
- **WW3:** the grid inputs (`ww3_grid.inp` and its x/y/bottom/mapsta files) were written
  when the case was created, with mom6_forge's default open edges. That default opens no
  edge on a cyclic grid. `ww3_grid` then dropped the north row, WW3 sent the coupler's
  1e30 fill as Stokes drift there, and MOM6 blew up on its first step. On non-cyclic
  grids the default opened all four edges, whatever boundaries were configured.

## What

This replaces closed #311. The change is the same, rebuilt on the `declared-output-files`
PR (configurators declare `output_files(ctx)`) and the `configure-existing-case` PR
(`Case.forcing_inputs()`, and `_bind` reading the case back from
`_crocodash_state.json`).

- **OBC:** drop the cyclic-grid assert. The visualCaseGen bump brings a mom6_forge whose
  `get_bounding_boxes` allows cyclic grids (ESMCI/visualCaseGen#50).
- **MOM6:** on a cyclic-x grid, set `OCN_CYCLIC_X = True`, plus the `Global` extent and
  `OCN_LENX = 360` that visualCaseGen requires for it. visualCaseGen then writes
  `REENTRANT_X = True`.
- **Case state:** creation records `cyclic_x` in `_crocodash_state.json`. `_bind` reads it
  and `forcing_inputs()` passes it on as `case_cyclic_x`. It is a derived key, so
  `crocodash dump` leaves it out of the `case:` section.
- **CICE:** new input `case_cyclic_x` (default `False`). When it is true, the east/west
  boundary is `cyclic`.
- **WW3:**
  - new inputs `case_grid_name` and `case_session_id` (default `None`);
  - `configure()` writes the grid inputs, with the configured `boundaries` as the only
    open (mapsta 2) edges;
  - case creation no longer writes them.

  These are configure-time files, not process outputs, so `output_files()` is unchanged.
- **Docs:** the developer table of mom6_forge calls now lists `write_ww3_input` under
  `forcing/ww3.py`.

## Tests

- CICE on a cyclic-x case gets a `cyclic` east/west boundary (from #311).
- WW3's `configure()` opens only the configured edges in `mapsta` (from #311).
- Adapted: the `WW3_GRID_INP_DIR` test stubs the grid-input write, as in #311.
- Already covered:
  - the `forcing_inputs()` coverage test checks the three new `case_*` inputs;
  - the `so1deg_wav` golden config, a WW3 + CICE config.json without the new inputs,
    still loads, with the defaults filled in.

## Notes for reviewers

- **The visualCaseGen pin must change before merge.** The submodule points at
  `fb8d0195`, the head of the unmerged ESMCI/visualCaseGen#50. Once #50 merges, re-pin to
  that ESMCI main commit. Never merge a pin to an unmerged PR head.
- **`cyclic_x` is optional within state 1.2.0, with no version bump.** `_bind` reads it
  with `state.get("cyclic_x", False)`; every other key is still read strictly. Cases
  created before this PR set `OCN_CYCLIC_X = False`, so reading them as non-cyclic
  matches how they were set up.
- **New inputs have defaults.** A config.json written before this PR still loads.
  Configuring writes the new inputs from `forcing_inputs()`.
- **WW3 grid inputs now need `configure_forcings()`.** Every CrocoDash case configures
  its forcings anyway. A case created but never configured has no `wav/` files.
- **One-time WW3 re-fetch.** WW3's staging-staleness check compares its stored inputs.
  The first reconfigure of an existing WW3 case after this PR adds `case_grid_name` and
  `case_session_id`, so the staged spectra are fetched again once.
- **CICE restoring on a cyclic grid is not handled.** mom6_forge's
  `SupergridBase.expand()` raises on cyclic grids. It was not handled in #311 either.
- Real-case check: on Derecho, #311's change ran a 1° cyclic Southern Ocean case
  (GWR_JRA, `REENTRANT_X = True`) clean for 2 days, and a clone of it checked the cyclic
  CICE boundary. Rerun it by hand on this base before opening.

Closes #339

🤖 Generated with [Claude Code](https://claude.com/claude-code)
