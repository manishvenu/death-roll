# Region: build each fetch box one way and pad it once

## Why

- **The OBC edge box could be a whole latitude band.** It was a plain min/max of
  the edge's ocean longitudes (`_ocean_bbox_for_boundary`). Production runs this
  path, because `process_bc` always passes the bathymetry. On a grid stored split
  at ±180, or a polar grid whose edge crosses 180E, the box came out -180..180, so
  every GET chunk fetched the whole band.
- **Callers built boxes two ways.** The MOM6 OBC used that min/max. The IC, CICE
  and WW3 used mom6_forge's `get_bounding_boxes`. Both were then passed on as
  four loose floats.
- **Buffers are added in many places.** Each product adds its own, and CICE adds
  another degree on top.
- **CICE called its access method directly with its own loose arguments.** It now goes
  through the same adapter as the other callers (`call_access_method`), though not
  `fetch_raw_chunk`; see the notes.

## What

- **`Region`** (`raw_data_access/region.py`) is a frozen dataclass of `lat_min`,
  `lat_max`, `lon_min` and `lon_max`.
  - `lon_min` is put on [-180, 180), and `lon_max` moves with it.
  - `lon_max` runs east of `lon_min` by at most 360, so a box across 180E is
    170..190. Anything else raises `ValueError`: *"lon_min 190.0 and lon_max
    170.0 are not a box: lon_max runs east of lon_min by at most 360, so for a
    box across 180E give lon_max past 180, e.g. 170..190."*
  - It has four methods:
    - `around(lon, lat)`: the smallest box holding the points, going the short
      way round.
    - `padded(deg)`: grown by `deg` on every side. Latitudes stop at ±90 and the
      width at 360.
    - `select(ds, lon, lat)`: `ds` cut to the box by index, from 1-D or 2-D
      lon/lat. Columns come west to east across the source's own seam, each
      once, and longitudes are relabelled onto `lon_min..lon_min+360`. On a 2-D
      source where the box's cells fall in more than one column run (a tripole
      fold), every column of those rows is kept.
    - `lon_ranges(west)`: one or two ranges inside `[west, west + 360)`, for
      remote APIs that can't take a range across their own seam.
  - No product uses `select` or `lon_ranges` yet. Q21 and Q22 move the readers
    onto them, and Q23 moves ERA5.
- **`@accessmethod(buf=)` pads once.**
  - For a method that takes `region`, the decorator wraps the method with
    `functools.wraps`, so its signature and registration are unchanged. The
    wrapper takes `buf=` (the decorator's value by default) and passes
    `region.padded(buf)`.
  - A method that takes `region` but has no `buf` fails at import: *"... takes
    region, so @accessmethod needs its buffer: pass buf=, in degrees (0 for
    none)."*
  - `get_function_default_args` lists `buf` for such a method. So
    `function_overrides`, and stored `function_args` like `{"buf": 1.0}`, keep
    working.
- **OBC edge boxes are `Region.around(ocean points)`.** `_ocean_region` replaces
  `_ocean_bbox_for_boundary`'s plain min/max. Without a bathymetry file (WW3),
  the edge boxes are Regions of `get_bounding_boxes`'s.
- **IC, CICE and WW3 boxes** are Regions of mom6_forge's `get_bounding_boxes`.
  CICE keeps its own degree as `.padded(1)`; Q22 removes it.
- **One call path.** `utils.call_access_method(fn, when, region, **args)` is the
  only adapter. It passes `when=` and `region=` to a method that takes them, and
  `dates` and the four numbers to the rest. `fetch_raw_chunk` calls it, and so
  does CICE (see the notes).
- **Registry.** `region` stands in for the four numbers in the required-args
  check, in `validate_call` and in the toy validation call
  (`Region(30, 30.1, 30, 30.1)`). This is the same treatment Q5 gave `when` for
  `dates`.
- **Docs.** `adding_data_access.md` covers `region` and `buf`, and the API docs
  list the new module.

## Tests

- A grid stored split at ±180 gives an edge box of 170..190. A polar north edge
  that bends round the pole from 135E to 225E gives 135..225, not -180..180.
- `select` on a 1-D source whose longitudes start at 250E and repeat the first
  column at the end: a box across either seam returns ascending, unique
  longitudes, each with its own data, and a full circle gives each of the 360
  columns once.
- `@accessmethod` pads `region` once by `buf`, a caller's `buf` replaces the
  default, and `get_function_default_args` lists it. The test defines a tiny
  product, since no real one takes `region` yet.
- Updated:
  - The tmask OBC box test now compares Regions. Its old check compared a box on
    the grid's 0..360 branch with one on -180..180, so it always passed.
  - The inclusive-dates allowlist gets the new test product.
- I ran these locally without pytest's runner: the 3 tests above, the updated
  tmask test and the allowlist test. All passed, and every changed module
  imports.
- Checked by hand in a scratch script:
  - `select` on a 2-D curvilinear source whose columns start at 320E. A box
    across its seam gives one ascending run, and a full circle keeps all 180
    columns once. A tripole-like fold keeps every column of its rows.
  - `select` on a source with descending latitudes.
  - `lon_ranges`: 170..190 gives 170..180 and -180..-170, and a full circle gives
    -180..180.
  - `padded`'s caps, and the error messages.
  - reference_ice through CICE's call with the padded box.
  - rm6's regridder gives the right values from a source on -83..-78 to targets on
    278..281.

## Notes for reviewers

- **Changed lines:** +406/−127 against time-request's head (4a92f657).
- **Exact longitudes.** `Region.around` ends at the edge points as given, and
  `select` compares in float64 and relabels by whole turns, so a longitude already
  in the box keeps its source value. It drops the source's `valid_min`/`valid_max`,
  which would make netCDF4-python mask the longitudes moved past 180 (xarray
  ignores them; the old `longitude_slicer` dropped them too). A 2-D cut that keeps
  every column starts at the west; at a tripole fold it keeps the source's order.
- **Built on Q5.** When Q5 merges, rebase with
  `git rebase --onto origin/main 4a92f657 region`.
- **OBC boxes are now on [-180, 180).**
  - The OBC box used to be on the grid's own branch: 278..281 for the panama test
    grid. It is now -82..-79, like the IC and WW3 boxes already were.
  - GLORYS RDA's `longitude_slicer` returns data on the requested branch, so a
    0..360 grid's raw OBC files now carry -180..180 longitudes.
  - The regrid doesn't mind, as checked above. I found no code that compares raw
    longitudes with the grid's.
- **An OBC box across 180E now ends past 180**, e.g. 170..190, as the IC box
  already did. GLORYS RDA and the CESM readers handle it, since the IC already
  sends it to them.
- **Known until the next PR:** GLORYS RDA still cuts with mom6_forge's
  `longitude_slicer`, which raises when a box's midpoint lies between the source's last
  longitude (179.92) and 180. Fetching a whole latitude band hid this on grids split at
  ±180; this PR's tighter edge boxes can reach it there (e.g. an edge from 175.0 to
  184.9). The next PR moves GLORYS onto `Region.select`, which takes the slicer off this
  path. The same slicer check already fails today for such edges on grids stored on
  0..360.
- **CICE goes through `call_access_method`, not `fetch_raw_chunk`.** This differs
  from SPACE_TIME.md, which allows the helper only where no file is fetched.
  - `fetch_raw_chunk` skips a file that already exists, and CICE has no
    `stale_outputs`. A rerun with another `restart_path` would silently reuse the
    old subset.
  - So CICE still fetches on every run. Moving it onto `fetch_raw_chunk` needs a
    CICE `stale_outputs` first.
- **CICE's box is `padded(1)` instead of ±1.** It differs only at the extremes.
  Latitudes stop at ±90, where reference_ice used to make rows past the pole, and
  the width stops at 360.
- **`Region(**box)` doesn't work on `get_bounding_boxes` output.** Its dicts also
  carry `crosses_antimeridian`, which a Region has no use for, so the callers pass
  the four values.
- **`around` of a ring of points** is 360 minus its widest gap, e.g. 350 for a
  ring at 10° spacing. Padding by half the spacing makes it every longitude.
  Regional grids have no ring edges. Q17's cyclic edges should be built as
  full-circle Regions.
- **Buffers are unchanged.** No product takes `region` yet, so each still adds
  its own buffer. Q21, Q22 and Q23 move them onto `buf`, each keeping its value.
- **Merge hazard with Q16 and Q17.** Both change `process_obc_conditions`' box
  code. They need `_ocean_region` in place of `_ocean_bbox_for_boundary`, and
  must pass Regions to `_get_boundary`. Q16's `_segment_bbox` becomes a
  `Region.around`.
- **Still to check by hand on GLADE:** a GLORYS RDA case on a grid across 180E.
  Its raw OBC files should cover about 169..191, not the whole band, and its OBCs
  should be unchanged.

Closes #345

🤖 Generated with [Claude Code](https://claude.com/claude-code)
