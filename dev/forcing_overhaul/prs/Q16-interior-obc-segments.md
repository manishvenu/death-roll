# Accept interior open-boundary segments in configure_forcings

## Why

`configure_forcings(boundaries=...)` only takes the four domain edges. Some regional
domains need an open boundary inside the grid too, such as a strait that cuts off a
basin. regional_mom6's `Segment` can already describe such a line.

Closed #269 added this, but it had three problems:
- It deleted `ignore_degenerate=True` from the OBC regrid. That brings back the ESMF
  `rc=506` abort for domains near the poles.
- config.json kept only the segment's name, with its geometry in a `custom_segments`
  output. `dump`, `fork` and `crocodash configure` rebuild a case's arguments from
  config.json, so they lost the segment.
- recipe.py rejected any boundary that isn't an edge name.

## What

This replaces closed #269. It is rebuilt on the `declared-output-files`,
`configure-existing-case` and `time-windows` PRs.

- **A boundary is an edge name, a `Segment` or a segment spec.** The spec is
  `{"name": ..., **Segment.to_spec()}`, which is `name`, `axis`, `index`, `index_range`
  and `ocean_side`, in supergrid indices. `configure_forcings` turns a `Segment` into
  its spec. Conditions and tides store that spec in their `boundaries` input in
  config.json.
- **Conditions:**
  - It has a new `case_supergrid_path` input, which comes from `Case.forcing_inputs()`.
    It defaults to None, so an older config.json still loads.
  - An interior segment's `OBC_SEGMENT_NNN` position comes from
    `Segment.mom6_obc_position_string()`. Edges keep their fixed strings.
  - `validate_args` accepts specs and requires unique boundary names.
  - An interior segment's `forcing_obc_segment_NNN.nc` is declared in `output_files`,
    just like an edge's.
- **The OBC engine (`obc.py`):**
  - New helpers: `boundary_key` and `get_segment`.
  - `process_obc_conditions(custom_segments=...)` downloads an interior segment's data
    over the segment's own bounding box.
  - `_regrid_obc_chunk(custom_segments=...)` rebuilds the segment, and `process_bc`
    binds `custom_segments` to both.
  - `ignore_degenerate=True` and its polar-domain comment stay.
- **Tides** calls `Segment.regrid_tides` directly, through rm6's
  `prepare_tpxo_tidal_forcing`. It no longer goes through `rmom6.experiment`, which only
  knows edges. The files and their numbering are the same as before.
- **Round trip:** `Case.forcing_args()` now returns conditions' stored `boundaries`,
  specs included, not the names from `boundary_number_conversion`. recipe.py's check
  accepts mappings.
- **The stale-file check skips `case_*` inputs.** These inputs say where the case keeps
  a file, not what the files are made from. Without the skip, every existing config.json
  would lack `case_supergrid_path`, so the first reconfigure after this PR would delete
  the case's IC and OBC files. A forked case would lose them the same way.
- **Removed `Case.expt`**, as #269 did. Nothing used it, and it passed `boundaries` to
  `rmom6.experiment`, which can't take a spec.
- **Docs:** an "Interior Open Boundaries" example on the configure-forcings page, and the
  YAML form of a spec in cli.md.

**Changes from #269:**
- `ignore_degenerate=True` is kept, with a test.
- The spec lives in the `boundaries` input itself. #269 kept a name there plus a
  `custom_segments` output, and tides read conditions' output. Here tides reads its own
  `boundaries` input, and there is no `custom_segments` output.
- `case_supergrid_path` comes from `forcing_inputs()`.
- The edge position strings stay hard-coded, so a case with only edges doesn't need the
  supergrid at configure time. For all four edges, `Segment` gives the same strings
  (checked by hand).
- Left out of this PR:
  - `boundaries=None`, which auto-detects the open edges from the topography. It would
    change behaviour for every case, so it is its own PR (Q25, #352).
  - The CI `esmf=*=nompi_*` change. It is already on main.

## Tests

- An interior segment, given as its spec, is fetched, regridded and merged into its own
  `forcing_obc_segment_001.nc`. This uses `reference_ocean`, so no download is needed.
- Tides are regridded for every boundary, the interior one included, and are numbered
  like the OBC strings. The regrid itself is mocked. This replaces the
  `experiment`-based tides test.
- An interior segment survives config.json → `forcing_args()` → configure unchanged.
- The OBC regrid asks rm6 for `ignore_degenerate=True`. rm6's regrid call is mocked.
- Adapted existing tests:
  - the `process_bc` wiring test expects `custom_segments` on the regrid step;
  - the `forcing_args` fixture stores `boundaries` in conditions' inputs, as real
    config.json files do;
  - the CIME configure test no longer touches `case.expt`.
- Dropped from #269:
  - its edge-only `reference_ocean` test, which the existing dz-thinning test already
    covers;
  - its Segment-serialization test, since no `Segment` reaches a configurator now.

## Notes for reviewers

- **A WW3 case with an interior segment fails at configure.** WW3 still checks that its
  `boundaries` are strings. #269 had the same gap. Supporting interior segments in WW3
  is out of scope here.
- **`obc.py` imports rm6's `Segment`.** It needs the segment to compute an interior
  segment's bounding box. #269 did the same. That box is the segment's full extent,
  not trimmed to ocean points as an edge's is.
- **Tides' TPXO regridders don't pass `ignore_degenerate`.** They didn't on main
  either.
- **rm6 requirements.** This needs `Segment.to_spec`, `Segment.from_spec`,
  `Segment.mom6_obc_position_string` and `prepare_tpxo_tidal_forcing`. All four are in
  the rm6 commit CrocoDash pins now.
- **Hand checks.** I ran the new paths in the dev environment, outside pytest:
  - configure with an interior segment;
  - the config.json round trip;
  - an interior OBC run with `reference_ocean`;
  - tides;
  - the `ignore_degenerate` call.
- **Not done:** a MOM6 run with an interior segment on Derecho. That is the by-hand
  check for this PR.

Closes #338

🤖 Generated with [Claude Code](https://claude.com/claude-code)
