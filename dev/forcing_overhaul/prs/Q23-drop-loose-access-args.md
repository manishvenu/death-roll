# ERA5 and GLOFAS by region and when; drop the loose access arguments

## Why

- **ERA5 couldn't fetch a box across 180E.** `build_era5_spectra_request`
  wrapped each end onto -180..180 on its own. A box across 180E (170..190)
  raised `NotImplementedError`, and -180..180 became a 2° sliver, since both
  ends wrapped to -180.
- **ERA5's buffer was fixed.** The request builder added 1° to every side, and
  nothing could change it.
- **GLOFAS still took `dates` and `freq`.** It was the last dated product that
  did, and it picked its days with `sample_dates` on every call.
- **The adapters were waiting for this PR.** Q5 and Q20 left them so products
  could move over one PR at a time:
  - `call_access_method` passed `dates` and the four numbers to methods that
    didn't take `when` and `region`;
  - `_STANDS_IN_FOR` relaxed the required-args check;
  - three `validate_method` overrides built toy `dates` and lat/lon;
  - a textual test grepped every dated method's source for
    `make_dates_end_inclusive`;
  - `convert_lons_to_180_range` had no caller.
- **reference_ice lost its degree at the base merge.** Q21 gave it `buf=0`,
  since CICE added 1°. Q22 removed that degree for methods that take `region`.
  Together, reference_ice got no buffer at all.

## What

- **ERA5** (`era5.py`):
  - `get_era5_2d_spectra(when, region, ...)` takes `@accessmethod(buf=1.0)`, its
    old value. It is now overridable as `buf` through
    `ww3_obc_function_overrides`.
  - `build_era5_spectra_requests(when, region)` returns one request per range
    of `region.lon_ranges(-180)`. That is one request, two for a box across
    180E, or the globe for a full circle. Latitudes come clamped to ±90 by
    `Region.padded`.
  - Each request is retrieved and decoded on its own, and each GRIB file is
    deleted after it is decoded. The parts are joined along longitude on the
    region's branch, each meridian once: two areas across 180E, like a full
    circle's one, both hold 180E.
- **GLOFAS** (`glofas.py`):
  - `get_global_data_with_python(when, ...)` asks for `when.days()`. Its `freq`
    parameter goes. It keeps `subsample=True`, so a thinned `when` asks for
    fewer days.
  - `get_processed_global_glofas_script_for_cli` drops its unused
    `dates="UNUSED"`. The script fetches one fixed file, so it takes no `when`.
- **Static snapshots take no `when`** (SPACE_TIME.md's rule):
  - `cice_restart` drops `dates`, and its warning no longer names a range.
  - `reference_ice` drops `when`. It declares `buf=1.0`, the degree
    `forcing/cice.py` used to add.
  - CICE's caller calls the method directly with the domain's `Region`. It
    still doesn't go through `fetch_raw_chunk` (see Q20's notes).
- **Adapters deleted:**
  - `utils.call_access_method`. `fetch_raw_chunk` calls the method with
    `when=` and `region=`.
  - `takes_when` and `_STANDS_IN_FOR`. The required-args check and
    `validate_call` are plain again.
  - The loose `required_args`. `DatedBaseProduct` adds none.
    `ForcingProduct` adds `variables`, `region` and `name`.
  - `ConditionsConfigurator._function_args` passes only `data_freq`.
    `subsample_freq` reaches the method as the thinned `when`, and no method
    takes `freq` any more. `get_function_default_args` no longer special-cases
    `freq`.
  - `base.sample_dates`. GLOFAS was its last user.
  - `make_dates_end_inclusive`. GLORYS's CDS and CLI methods add
    `_TO_LAST_SECOND` (1 day minus 1 second) to `when.end` themselves. The
    strings they send are the same as before.
  - `convert_lons_to_180_range`.
- **One validation.** `BaseProduct.validate_method` builds the toy call from
  what the method takes:
  - `region=Region(30, 30.1, 30, 30.1)`;
  - `when`, the first two days of the product's `coverage()`, read with the
    method's defaults plus the caller's kwargs. It starts at 2000-01-01 when
    the start is unknown;
  - `data_freq="D"` for a `USER_SPECIFIED` product.

  The `DatedBaseProduct`, `ForcingProduct` and `CESM_WW3_JRA` overrides are
  deleted.
- **Docs:** `adding_data_access.md` shows a method taking `region` and `when`,
  `buf=` in the decorator, how `lon_ranges` and `when.days()`/`when.select`
  are used, and what the toy validation passes.

## Tests

- New:
  - `test_era5_area_across_180`: 170..190 gives the areas `78.0/170.0/68.0/180.0`
    and `78.0/-180.0/68.0/-170.0`, and -180..180 gives one area,
    `78.0/-180.0/68.0/180.0`.
  - `test_dated_methods_take_region_and_when`: no dated method in the registry
    takes `lat_min`, `lat_max`, `lon_min`, `lon_max`, `dates` or `freq`. It
    replaces the textual allowlist test.
- Updated:
  - `test_era5.py`: the builder tests call `build_era5_spectra_requests`. The
    fake-client test and the slow CDS test pass `when` and `region`.
  - `test_base_registry.py`: the dummy products take `region` and `when`.
  - `test_ic.py`: the IC's access call gets `when` and a `Region`. This also
    replaces the stale `longitude_slicer` comment, one of QUEUE.md's minor
    review points.
  - `test_ww3.py`: the fake ERA5 product takes `region` and `when`, with
    `buf=0`.
  - `test_reference.py` and `raw_data_access/test_cice.py`: the static methods
    are called without dates. `test_glofas.py`'s slow test passes `when`.
- Deleted, with the code they covered:
  - `test_dates_inclusive.py` (the allowlist test and the two
    `make_dates_end_inclusive` tests);
  - the two `convert_lons_to_180_range` tests and the two `sample_dates` tests;
  - the ERA5 custom-buffer test. The builder takes no buffer, and Q20's
    `test_accessmethod_pads_the_region_once_by_buf` covers `buf`.
- I ran these locally without pytest's runner, and all passed:
  - the 2 new tests;
  - every fast test in `test_base_registry.py`, `test_era5.py`,
    `test_reference.py`, `test_dataset_utils.py` and `test_glofas.py`;
  - `test_cice_window_on_degree_grid`,
    `test_process_initial_condition_downloads_then_regrids`,
    `test_process_ww3_obc_multi_station`,
    `test_process_ww3_obc_with_reference_waves` and
    `test_process_cice_forcing_with_reference_ice`;
  - the 19 tests in `test_mom6_engine.py` that need no fixtures, for
    `_function_args`;
  - `test_reference_ocean_obc_thins_dz_to_the_sea_floor`, which runs
    reference_ocean through the real OBC GET (`fetch_raw_chunk`), REGRID and
    MERGE.
- Every changed module imports.
- Not run, because they need the network, credentials or GLADE data:
  - `test_validate_all_registered_access_methods`;
  - the slow ERA5, GLOFAS and GLORYS calls;
  - the GLADE-gated cice_restart tests.
- Checked by hand: the toy call each registered method gets. I swapped a
  recorder with the same signature in for every method, and stubbed
  `tseries_coverage`, which walks `dataset_path`:
  - GLORYS (all three methods): 1993-01-01 → 1993-01-02;
  - CESM-WW3-JRA: 2018-12-01 → 2018-12-02, from its real `coverage()` (was
    2019-01-01);
  - the CESM tseries readers: their coverage's first day;
  - `cesm_mom_output`: also `data_freq="D"`;
  - ERA5, GLOFAS python, reference_ocean and reference_waves: 2000-01-01 →
    2000-01-02;
  - cice_restart and reference_ice: `region` only;
  - the static products: neither.

## Notes for reviewers

- **Changed lines:** +242/−531 against the base merge (bd0f0f73).
- **Built on a local merge of Q21 and Q22** (bd0f0f73). When both merge, rebase
  with `git rebase --onto origin/main bd0f0f73 drop-loose-access-args`.
- **The reference_ice merge hazard is resolved here:** `buf=1.0`, and CICE's
  fallback pad for methods without `region` is gone.
- **GLOFAS's script takes no `when`.** The survey had it take `when` and ignore
  it. A parameter kept only to be ignored is the kind of loose argument this
  PR removes, and SPACE_TIME.md already lets static outputs skip `when`.
- **Calls with the old arguments now fail.** That includes direct calls such as
  `get_era5_2d_spectra(dates=..., lat_min=...)`, and `ProductRegistry.call`,
  whose required-args check now asks for `region`. The gallery and the MCP
  servers only name these methods, so nothing there changes.
- **Stored configs are unchanged.** `_function_args` already dropped keys a
  method doesn't take, such as the `"freq": null` that #303's configs carry.
  `ww3_obc_function_overrides` and `cice_function_args` hold only what users
  typed.
- **The generated `functions.csv` still says cice_restart ignores `dates`.**
  `generate_info.py` rebuilds it, and the table is already stale for
  reference_ice, so I left it.
- **Still to check by hand:**
  - `test_validate_all_registered_access_methods` on GLADE, with CDS and
    Copernicus credentials.
  - ERA5 once with a box across 180E (needs a CDS account). There should be two
    retrieves, joined, with stations on both sides of 180E.
  - ERA5 for a full circle, which only a cyclic domain (Q17) asks for. The 0.5°
    grid may return both -180 and 180, which would give one duplicate station.
  - A CICE restoring case with cice_restart on GLADE
    (`test_process_cice_forcing_produces_output`).

Closes #348

🤖 Generated with [Claude Code](https://claude.com/claude-code)
