# Every dated access call starts from a TimeRequest

## Why

Each caller and each product works out its dates its own way, and several of
those ways break:

- **CESM tseries readers return whole files.** A FOSI file holds a year and a
  LENS2 file a decade, so every 7-day OBC chunk carried every record. REGRID then
  stopped on a duplicated time axis (`Cannot get left slice bound for non-unique
  label`). The IC took the file's first month, so a FOSI run starting 2000-07-01
  got January.
- **Thinning restarts at every chunk.** Each GET chunk thinned from its own first
  day, so `5D` over 7-day chunks came out 5, 2, 5, 2 days apart.
- **The IC was thinned.** `subsample_freq` reached the IC request, which reaches
  back one record spacing for unthinned data. A CESM IC with `QS` raised.
- **Feb 29 broke noleap data.** The REGRID string slice and the IC's record pick
  both raised on a Feb 29 window edge.
- **A run outside the product's data failed late**, when that data was fetched.

## What

Replaces #335's first branch (`tseries-time-slice`, 2ac2823f, kept on origin) and
keeps its behaviour: only the window's records, and the IC from the record at or
before the start. #335's two commits are cherry-picked unchanged; the third
commit is new.

- **`TimeRequest`** (`raw_data_access/time_request.py`) is a frozen dataclass of
  `start`, `end` and optional `dates`, with four methods:
  - `every(freq, start, end)`: one date per `freq` for the whole window.
  - `between(start, end)`: one chunk, keeping its own dates.
  - `days()`: the days to read.
  - `select(ds, time)`: the records from start to the end of the end day, then,
    with dates, the record whose time bounds hold each date (CF `bounds` on the
    time coordinate), or the nearest record when there are no bounds. This is
    #327's rule, so a MOM6 mean stamped mid-interval still counts for its own
    interval. It works in the data's calendar
    (cftime and noleap, where Feb 29 becomes Mar 1). It raises `ValueError`
    naming the window when nothing is left.
- **OBC.** The conditions configurator builds one request for the padded window.
  It is thinned only when `subsample_freq` is coarser than the data. Each GET
  chunk takes `when.between(...)`, and REGRID slices with
  `TimeRequest(s, e).select`. WW3 passes its run dates as a `TimeRequest`.
- **IC.** The request is `TimeRequest(start - lookback, start)` and is never
  thinned. `_regrid_ic` takes `when.select(raw).isel(time=[-1])`.
  `process_initial_condition` and the IC `regrid_fn` take `when` in place of
  `start_date` and `lookback_days`.
- **`fetch_raw_chunk`** passes `when=` to a method that takes it. Every other
  method gets its first and last days as `dates`, plus any `freq` in
  `function_args`, as before. This adapter goes once every product takes `when`.
- **CESM readers** (POP tseries, MOM tseries, `get_mom6_output_data`) take `when`
  in place of `dates` and `freq`.
  - The window slice and the thinning are `when.select`, run after POP's
    `time_bound` dating.
  - #327's `data_freq` spacing check stays, as `check_data_freq`.
  - `get_mom6_output_data` drops its `date2num` slice, which raised on Feb 29.
- **Coverage refusal at configure.** For example: *"glorys has data 1993-01-01 →
  …; the run 1990-01-01 → 1990-02-01 is outside it. Move date_range inside it or
  choose another product."* Only the padding stopping at the data's edge still
  warns, as in #333.
- **Registry.** `takes_when` in `base.py` lets a method take `when` in place of
  `dates` in the required-args check, `validate_call` and the toy validation
  call.
- **Docs.** `adding_data_access.md` mentions `when` and the coverage refusal, and
  the API docs list the new module.

## Tests

- `5D` thinning stays 5 days apart across two 7-day chunks. In the same test,
  `QS` over MOM6-style monthly means stamped mid-month, with time bounds, keeps
  January, April, July and October across two chunks.
- A noleap IC starting on Feb 29 gets February's mean. The test builds the
  request through `process_ic`, then picks the record.
- The CESM-POP reader keeps only the window's records (#335's test, kept).
- Existing tests are updated for `when`: the CESM readers, the IC and OBC
  engines, `process_ic`/`process_bc`, and the inclusive-dates allowlist.
  `test_regrid_ic_gives_the_vgrid_check_the_real_min_depth` had been broken
  since #335's record pick read `time_var_name`; it now passes.
- I ran these locally without pytest's runner: the 3 tests above, 25 other tests
  in the files this touches (including a WW3 process run and the reference-ocean
  OBC run), and the 3 cases of the time-windows bracket test. All passed.

## Notes for reviewers

- **Changed lines:** +490/−216 against the local merge of Q7 and Q8 (e7bacfc9).
  That includes #335's two commits (+99/−13).
- **Cached CESM subsets.** A thinned subset's file name carries its first and last
  sampled dates and their count, so two thinnings of one window (QS and QS-FEB)
  don't share a cached raw file. A `data_freq` that doesn't match the records names
  the alias they do match, e.g. `data_freq='MS'`.
- **Built on Q7 + Q8.** When they merge, rebase with
  `git rebase --onto origin/main e7bacfc9 time-request`.
- **The IC request changed for products not yet on `when`.** GLORYS used to ask
  for `[start, start + 1 day]` and now asks for `[start - lookback, start]`. With
  daily data the lookback is 0, so that is one day. The IC never gets `freq`.
- **Thinning keeps #327's rule.** Each date keeps the record whose time bounds
  hold it. Only data without bounds falls back to the nearest record, where a tie
  goes to the later record, so daily means stamped at noon keep their own day.
- **Thinning to the data's own cadence does nothing.** `subsample_freq="MS"` on
  monthly data builds an unthinned request, as #327's `select_records` and
  `resolve_time_sampling` already treated it. There is nothing to thin.
- **A record outside the IC window now raises**, where the old code passed a
  single record through unchecked.
- **Stale raw files.** As #335 said, GET skips raw files that already exist.
  Files fetched before this change can still hold every record. Delete
  `<inputdir>/extract_forcings/raw_data` before reprocessing a CESM-output case.
- **Still to check by hand on GLADE:**
  - The FOSI `month_1` OBC and IC for a run starting 2000-07-01: the IC is July
    and the OBC time axis has no repeats.
  - A GLORYS RDA case: its IC and OBC are unchanged apart from the IC's one-day
    request.

Closes #335

🤖 Generated with [Claude Code](https://claude.com/claude-code)
