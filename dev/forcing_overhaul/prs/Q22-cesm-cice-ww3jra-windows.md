# CESM output, CICE restart and CESM-WW3-JRA read seam-ordered windows

## Why

- **The CESM readers masked instead of cutting.** They built a lat/lon mask
  (`bbox_mask`) and applied `where(drop=True)`.
  - A box across the source grid's own seam came back with its columns in the
    source's order, not west to east.
  - `where` broadcast the 2-D mask onto variables without those dims, such as
    `time_bound`.
- **Buffers were added twice.** The tseries readers padded the box by 1.5, then
  `subset_dataset` padded it by 1 more. CICE added its own degree on top of
  cice_restart's 1.5.
- **cice_restart could no longer read its grid file.** `tx2_3v3_grid.nc` is now a
  MOM6 grid file: degrees, dims `ny`/`nx`, and `ulon` is the C-grid u-point. The
  reader applied `rad2deg` to degrees and cut the grid by `nj`/`ni`. The CICE-format
  companion files on GLADE (`tx2_3v3_cice_grid.nc`,
  `cice_grid_tx2_3v3_260305_cdf5.nc`) still hold radians, but label `tlon`/`tlat`
  as degrees, so the reader has to take both.
- **CESM-WW3-JRA never refused its spin-up.** It only checked, inside the call,
  that the restarts exist, so a run in the database's first month went through. Its
  box code was its own (`_axis_indices`, `lon_min % 360` plus the span).
- **A YYYYMM file end was read as the month's first day** when choosing CESM
  files. A run starting after the 1st of a file's last month skipped that file.
  (`tseries_coverage` already read it as the month's end.)

## What

- **CESM readers** (`cesm_ocean_output.py`):
  - `get_cesm_single_variable_data`, `get_mom6_single_variable_data` and
    `get_mom6_output_data` take `region` in place of the four numbers and cut with
    `region.select`. The tseries readers cut each variable on its own coordinates
    (`grid_coords`). `get_mom6_output_data` cuts each C-grid point (tracer, u, v)
    on its own axes.
  - Each buffer moves into `@accessmethod(buf=)` at today's effective value,
    applied once:
    - POP tseries (`get_cesm_single_variable_data`): `buf=2.5` (1.5 in the reader
      plus 1 in `subset_dataset`).
    - MOM6 tseries (`get_mom6_single_variable_data`): `buf=2.5`, the same path.
    - `get_mom6_output_data`: `buf=1.5`, its old `buffer_deg` default. The
      `buffer_deg` parameter goes.
  - `bbox_mask` is deleted.
  - `get_date_range_from_filename` reads a YYYYMM end as that month's last day,
    for `parse_dataset` and `tseries_coverage` alike.
- **cice_restart** (`cice_output.py`):
  - `get_cice_restart_subset` takes `region`, with `buf=2.5` (its 1.5 plus CICE's
    1). `buffer_deg` goes.
  - `_grid_window` replaces `find_cice_index_window`. It cuts the 2-D `tlon`/`tlat`
    with `region.select`:
    - a box across the grid's seam (73°E on tx2_3v3) is one run of columns;
    - a box whose cells fall either side of the tripole fold gets every column of
      its rows.
  - Radians are told from degrees by the values, not the `units` attribute, which
    the CICE-format tx2_3v3 files get wrong for `tlon`/`tlat`. A global grid's
    lon or lat in degrees always reaches past 2π, so values that don't are
    radians. The window is taken by position, so `ny`/`nx` files work.
  - U points are each T cell's NE corner, as `forcing/cice.py` regrids them. They
    are the file's `ulon`/`ulat` when those have the T points' shape (a CICE grid
    file), else `qlon`/`qlat[j+1, i+1]` (a MOM6 grid file). Each U longitude is
    put on its T point's branch.
- **CICE's caller** (`forcing/cice.py`) no longer pads the box for a method that
  takes `region`, which pads by its own `buf`. A method that doesn't yet
  (reference_ice) keeps the 1° pad until Q21 moves it onto `region`.
- **CESM-WW3-JRA** (`cesm_ww3_jra.py`):
  - `get_cesm_ww3_jra_spectra` takes `when` and `region`, with `buf=1.5`.
    `requested_timestamps(when)` gives the four restarts of each of `when.days()`.
  - `region.select` on the grid's 1-D axes finds the window, and `_axis_indices`
    is deleted. Only that window of each restart is read, in hyperslab runs as
    before.
  - The growing pad is `region.padded` one degree at a time, by up to
    `max_growth_deg=8.5` in all. A default call still stops at 10° of padding.
  - New `coverage()`: the first restart plus 30 days of spin-up, to the last day
    with all four restarts. That is 2018-12-01 → 2023-12-31 on the default database
    today. Without the database (off GLADE) it is `(None, None)`, so configure
    passes and the call says what is missing.
  - Its `validate_method` override passes a `TimeRequest`. Q23 deletes it.
- **WW3 configure refuses a run outside coverage.**
  - `WW3Configurator` takes `date_range`, stored as `start_date`/`end_date` inputs
    like the conditions' and StreamYears'.
  - Unless the product is `'none'`, configure checks the run against the
    product's `coverage()`: *"CESM-WW3-JRA has data 2018-12-01 → 2023-12-31; the
    run 2018-11-15 → 2018-12-15 is outside it. Move date_range inside it or choose
    another product."*
  - The check is `time_windows.check_coverage`, moved out of
    `ConditionsConfigurator.configure`, which calls it too. Its message is
    unchanged.

## Tests

- New:
  - A synthetic MOM6-style grid file (ny/nx, degrees, `qlon`/`qlat` corners). A
    Gulf of Mexico box finds the right cells, and its U points are the NE corners.
    An Arctic box whose cells fall either side of the fold gets all 36 columns of
    its row. The same grid as a CICE-format file in radians, with `tlon`/`tlat`
    labelled degrees, finds the same Gulf cells.
  - Two empty restart files (2018-11-01 and 2019-03-01) make a database. A run
    from 2018-11-15 to 2018-12-15 is refused at configure.
- Updated:
  - The CESM reader and cice_restart tests pass a `Region`.
  - The WW3-JRA tests build a `TimeRequest` and a `Region`. The latitude test
    matches `Region.select`'s message.
  - The inclusive-dates allowlist comment for WW3-JRA now names `when`.
- Deleted, with the code they covered:
  - the two `bbox_mask` tests;
  - the two GLADE-only `find_cice_index_window` tests;
  - the WW3-JRA descending-pair test, and the −10..360 full-turn case. `Region`
    refuses both boxes.
- I ran these locally without pytest's runner, and all passed:
  - every test in `test_cesm_ocean_output.py`, `test_cice.py` and
    `test_cesm_ww3_jra.py` that needs no GLADE data;
  - the inclusive-dates tests and the two new tests;
  - the WW3 configurator tests next to the new one;
  - the reference_ice process test in `forcing/test_cice.py`.
- Every changed module imports.
- Checked by hand on GLADE, reading single files only:
  - The GLADE-gated cice_restart tests and
    `test_process_cice_forcing_produces_output` pass against `tx2_3v3_grid.nc` and
    the reference restart.
  - `tx2_3v3_grid.nc`, `tx2_3v3_cice_grid.nc` and
    `cice_grid_tx2_3v3_260305_cdf5.nc` give the same windows: 30×34 for the Gulf
    of Mexico box and 61×23 for a −5..5° box at 0°, 0° (both padded 2.5°).
  - cice_restart on tx2_3v3:
    - a Gulf of Mexico box gives 30×34 cells, with U points about 0.33° east and
      0.3° north of their T points;
    - a 60..90°E box across the 73°E seam gives one ascending run of 52 columns;
    - an 80..90°N box gives 40 rows of all 540 columns.
  - CESM-WW3-JRA on the default database:
    - its first restart is 2018-11-01 06:00 and its last 2024-01-01 00:00, so
      `coverage()` is 2018-12-01 → 2023-12-31;
    - one day of a box across 0°E (30..32°N, −5..5°E) gives 16 ascending columns,
      −7.5..7.5, with finite spectra;
    - the registry toy call passes.
  - A file `…SSH.195801-195812.nc` is chosen for a run starting 1958-12-15.
  - The so1deg_wav golden config's `ww3` entry still loads.

## Notes for reviewers

- **Changed lines:** +317/−453 against region's head (c0667295). That is a little
  over the ~700 target; most of it is deleted code and its tests.
- **Built on Q20.** When Q20 merges, rebase with
  `git rebase --onto origin/main c0667295 cesm-cice-ww3jra-windows`.
- **Merge hazard with Q21: reference_ice's buffer.** reference_ice adds no buffer
  of its own and gets CICE's degree, which `forcing/cice.py` now adds only for a
  method that doesn't take `region`. When Q21 moves reference_ice onto `region`,
  it should declare `buf=1.0` and delete that fallback.
- **Renamed arguments.** `buffer_deg` (CESM-MOM output, cice_restart, WW3-JRA)
  becomes `buf`, and WW3-JRA's `max_buffer_deg` becomes `max_growth_deg`.
  - Conditions `function_args` store the defaults, so `get_mom6_output_data`
    cases carry `buffer_deg`. `_function_args` drops keys a method no longer
    takes, so those cases still process, with `buf=1.5`. A `buffer_deg` a user
    overrode there is dropped the same way: set `buf` instead.
  - `cice_function_args` and `ww3_obc_function_overrides` hold only what users
    typed. A typed `buffer_deg` now raises `TypeError`.
- **The CESM subset file names change**, since they carry the box. A rerun
  fetches its CESM subsets once more.
- **Windows have a new shape.**
  - The CESM readers keep every cell of the index window, where `where` used to
    NaN the cells outside the box.
  - Longitudes come back on the box's own range: a POP box that read 288..293
    now reads −72..−67, and WW3-JRA's are no longer on 0..360. The regrid and
    `_wrap_lons_like` don't mind.
  - For CICE, a box at the fold gets every column of its rows. The old slicer
    took one column range from row 0.
- **A WW3-JRA box with no cell centre in it now raises at once.** The old
  `_axis_indices` read the neighbours outside it. With the default `buf` of 1.5
  on the 1° database, every box holds cells.
- **WW3Configurator gains `start_date`/`end_date` inputs.**
  - Its config.json entry changes, so the first `configure_forcings` after this
    marks `extract_forcings/ww3` stale once.
  - An older entry without them still loads; both default to None, and then
    configure skips the check.
  - `process()` still reads the conditions' dates.
- **cice_restart still takes `dates`.** It is a static snapshot, and Q23 drops the
  loose arguments.
- **Units are read from the values.** A global grid file is in radians when its
  lon or lat never passes 2π, whatever its `units` say. A regional grid within
  ±6.3° of 0°, 0° in degrees would be misread, but cice_restart reads global
  restarts only.
- **Still to check by hand on GLADE:**
  - a CICE restoring case end to end on the new tx2_3v3 grid;
  - a CESM-POP IC/OBC case whose box crosses POP's seam;
  - `test_process_ww3_obc_with_cesm_ww3_jra`.

Closes #347

🤖 Generated with [Claude Code](https://claude.com/claude-code)
