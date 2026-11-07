# GLORYS and the reference products: fetch by region and when

## Why

- **Each method read four loose floats and its dates its own way.** GLORYS's
  three methods and the three reference products still took
  `dates`/`lat_min`/`lat_max`/`lon_min`/`lon_max` through Q20's adapter.
- **GLORYS RDA and reference_ocean thinned per GET chunk.** Each chunk picked its
  dates from its own start, so `subsample_freq="5D"` gave gaps of 5 and 2 days in
  turn across 7-day chunks.
- **Each added its own buffer.** RDA had an overridable `buf=1.0`. The CDS method
  added a fixed 1. The CLI script got regional_mom6's fixed 0.24. The reference
  products padded with `np.arange` and never clamped latitude.
- **The CLI script kept only the last request.** CrocoDash checked for
  `get_glorys_data.sh`, but regional_mom6 wrote `get_glorys_data.pbs`, so every
  call started a new script. The script fetched only the last chunk of the last
  boundary.
- **The GLORYS seam tests were vacuous.** They mocked the data and checked the
  branches of `longitude_slicer`, which RDA no longer uses. Two of them used
  boxes that a Region refuses (`lon_min > lon_max`).

## What

- **The six methods take `region` and `when`.** They no longer take `dates`,
  `freq`, the four numbers or a buffer of their own.
- **Each buffer moves into `@accessmethod(buf=...)` with its old value:**

  | method | `buf` |
  |---|---|
  | glorys RDA | 1.0. Still overridable under the same name, so stored `{"buf": 1.0}` keeps working |
  | glorys CDS | 1.0 (was fixed) |
  | glorys CLI script | 0.24 (was regional_mom6's fixed pad) |
  | reference_ocean | 1.0 |
  | reference_ice | 0. CICE still adds its own degree (see the notes) |
  | reference_waves | 0 |

  `get_function_default_args` now lists `buf` for all six. So the CDS and CLI
  methods gain an overridable `buf`, and a new CLI case's config.json stores
  `function_args: {"buf": 0.24}` where it used to store `{}`.
- **GLORYS RDA:**
  - It reads the files for `when.days()`, so thinning comes from the one window
    request.
  - It cuts them with `region.select(ds, "longitude", "latitude")`, in place of
    a latitude `sel` and `longitude_slicer`. A box across 180E comes back west
    to east, each column once.
- **GLORYS CDS:**
  - It passes the padded box as it is. copernicusmarine 2.0.1 wraps longitudes
    itself: it puts both ends on [-180, 180), shifts the dataset when the east
    end is the smaller, and reads a span of 360 or more as the globe. So a box
    across 180E is one request, and `lon_ranges` isn't needed.
  - The time range is the whole days, ending at 23:59:59 of the last day, as
    before.
- **GLORYS CLI script:**
  - It writes its own `copernicusmarine subset` line. The dataset, the depth
    range and the 0.24 pad are the ones regional_mom6 wrote, and the variables
    come from the request.
  - It appends each line to one `get_glorys_data.sh` in the raw folder. A line
    already there is not added again, so rerunning `process_forcings` doesn't
    double the script.
  - The script is now `.sh`, which is the name `how_to_use` and the gallery
    already give. It carries no PBS directives. regional_mom6 added them only
    when given a `project`, and CrocoDash never passed one.
- **reference_ocean** writes one record per `when.days()` over the region.
- **reference_ice** takes `when` and ignores it, since the restart is one static
  snapshot. It takes `when` rather than nothing because `DatedBaseProduct` still
  requires `dates` until Q23.
- **reference_waves** spreads its stations along the region's long axis, every
  6 h of each day from start to end.
- **Docs:**
  - In `adding_data_access.md`, the `subsample=True` bullet now points to
    `when.days()`.
  - `submodule_api_usage.md` drops `rm6.get_glorys_data`. Its `longitude_slicer`
    row now points to `cice_output.py`, its last user.
- **Kept:**
  - `base.sample_dates`: GLOFAS still uses it until Q23.
  - `make_dates_end_inclusive`: the CDS and CLI methods still use it for the end
    of the last day. Q23 deletes it together with the textual dates test.

## Tests

- New tests:
  - `test_rda_box_across_180`: the box 170..190 returns 169..191, ascending and
    unique. Each source column is tagged with its own longitude, so the test
    also checks that the data follows its label. It replaces the three seam
    tests: the antimeridian wrap, `lon_max` of exactly 180, and the near-global
    box.
  - `test_cli_script_keeps_every_request`: two chunks give two subset lines, and
    asking for the first again adds nothing. It replaces the test that only
    checked the script existed.
- Updated:
  - The RDA days test is thinned with `TimeRequest.every("MS", ...)` instead of
    `freq`.
  - `test_reference.py` calls the methods with `region` and `when`.
    reference_ocean is thinned with `TimeRequest.every`.
  - The slow GLADE and Copernicus GLORYS tests: only their call changed.
  - `test_case_integration_config` expects the CLI's `function_args` to be
    `{"buf": 0.24}`.
- I ran these locally without pytest's runner, and all passed:
  - the 2 new tests;
  - the updated RDA days test;
  - all of `test_reference.py`, including the toy `validate_method` calls;
  - the inclusive-dates allowlist test.
- Every changed module imports.
- Not run:
  - the 2 slow tests, which need GLADE data and a Copernicus account;
  - `test_case_integration_config`, which needs a CESM case.
- Checked by hand in a scratch script:
  - `get_function_default_args` for the six methods.
  - reference_ocean through `fetch_raw_chunk`. With the default `buf`, its box
    is -83..-78. With a stored `{"buf": 2.0}`, it is -84..-77.
  - reference_ice through CICE's `call_access_method` with its padded box.
  - The OBC engine with reference_ocean on the panama grid and
    `extra_args={"buf": 1.0}`: GET through the fork pool, then regrid and merge.
    The segment came out finite.
  - copernicusmarine 2.0.1's longitude handling, read in the installed source.

## Notes for reviewers

- **Changed lines:** +148/−266 against region's head (c0667295).
- **Built on Q20.** When Q20 merges, rebase with
  `git rebase --onto origin/main c0667295 glorys-reference-requests`.
- **Thinning now holds across GET chunks** for GLORYS RDA and reference_ocean.
  Every chunk takes its part of one `TimeRequest.every`, so `5D` stays 5 days
  apart.
- **Merge hazard with Q22.** reference_ice keeps `buf=0` because
  `forcing/cice.py` still pads its box by 1. Q22 removes that pad. Whichever PR
  lands second should set reference_ice to `buf=1.0`, so its buffer stays at 1
  degree.
- **Every buffer is unchanged.** The CLI script keeps 0.24 rather than taking the
  CDS method's 1.0, as the survey suggested. That change would fix no bug, and
  users can now override the value.
- **A copernicusmarine quirk, not handled here.** Its wrap check treats a
  longitude of exactly 0 as false (`max and min and max < min`). So a box that
  crosses 180E and has one edge exactly on 0°/360° would come back empty. Only a
  box wider than 180° with an edge on the prime meridian can hit it.
- **The CDS method can't thin.** `configure_forcings` already refuses
  `subsample_freq` for it with #327's message. A direct call with a thinned
  `when` gets every day.
- **Copernicus coverage is still open-ended** (open question 4 of the survey).
  That is not in this PR.
- **Still to check by hand:**
  - A GLORYS RDA case on Derecho, ideally on a grid across 180E. Its raw OBC
    files should cover about 169..191, and its OBCs should be the same as
    before.
  - A CLI case: run `get_glorys_data.sh`, then `process_forcings`. Every chunk
    file of every boundary should be there.
  - The CDS method once with a box across 180E. This needs a Copernicus
    account.
  - An RDA (or reference_ocean) case on a small grid whose edge is within 1 degree
    of -180 but doesn't cross it. RDA now labels its longitudes past 180 where the
    old code gave -180..-170. Its regridded segments should match the old output.

Closes #346

🤖 Generated with [Claude Code](https://claude.com/claude-code)
