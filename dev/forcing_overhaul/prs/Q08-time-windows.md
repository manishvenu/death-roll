# Size forcing chunks and fetch windows to the product's time sampling

## Why

Every product gets the same 7-day GET and 30-day REGRID chunks, and fetches exactly
the run's dates. That suits daily data, but not monthly data: CESM-POP output,
CESM-MOM output with `data_freq="MS"`, or GLORYS thinned with `subsample_freq="MS"`.
- **OBC:** a 30-day REGRID chunk can fall between two monthly records and come out
  empty.
- **OBC:** the records don't bracket the run. MOM6 interpolates between OBC records and
  stops on a model time outside them. Even daily GLORYS means, stamped at noon, start
  half a day after the run.
- **IC:** the request is `[start, start + 1 day]`, which holds no monthly record unless
  the run starts on one.

Padding the window by itself breaks at the edges of the archive. GLORYS starts on
1993-01-01, so a run starting that day would also ask for 1992-12-31 and get a
`FileNotFoundError` on RDA. A CESM tseries run near the end of its files would ask for a
month past them.

## What

Replaces #305 (closed). It is rebuilt on the typed `data_freq`/`subsample_freq` inputs
(branch `typed-freq-inputs`) and on tolerant config.json reading (#325).

**From #305:**
- **New module `forcing/time_windows.py`.** Here p is the product's longest record spacing
  in whole days, from the resolved sampling:
  - chunks: GET is max(7, p), REGRID is max(30, 2p), and the shortest chunk is p;
  - the boundary window is padded by p on each side of the run;
  - the IC lookback is p − 1, from the source's own spacing, so thinning doesn't change
    it;
  - `describe()` builds the `[info]`/`[warn]` lines that `configure()` prints.
- **`ConditionsConfigurator`** gets four config.json outputs: `min_chunk_days`,
  `obc_start_date`, `obc_end_date` and `ic_lookback_days`. They are part of the
  process fingerprint.
- **Engines:**
  - `_make_date_pairs(min_days=)` merges a short trailing chunk into the one before it;
  - REGRID raises a clear `ValueError` on a chunk with no records;
  - `process_initial_condition(lookback_days=)` is new.
- **Daily data** keeps its 7/30-day chunks. Its window is padded by one day on each side,
  and it has no IC lookback.
- **CI:** the smoke case runs Jan 2–4, so its padded window reads exactly the Jan 1–5
  files staged from S3.
- API docs are regenerated.

**Changed from #305:**
- **Windows are clamped to the product's coverage.**
  - New classmethod `DatedBaseProduct.coverage(method_name, **kwargs)` returns
    `(first, last)`. Either may be `None`, and the default is `(None, None)`.
  - GLORYS returns its 1993-01-01 start. Its end is left open because it keeps growing.
  - The CESM-POP tseries reader and the CESM-MOM tseries reader read the span from their
    file names, the same way the readers do. A YYYYMM end runs to the end of that month.
    The span is filtered by `member` and is the intersection over the requested
    variables.
  - `obc_window` stops the padding at the coverage but never cuts the run itself.
    `configure()` warns when it clamps.
  - The dev doc `adding_data_access.md` says how to declare coverage.
- **Run length:** `describe()` counts end − start days, the same as `STOP_N` (#305
  counted one extra day).
- **Sampling** comes from `subsample_freq` or `data_freq`, whichever the method reads.
  The native sampling comes from `resolve_time_sampling`, so #305's copy of the
  subsample rule (`native_sampling`) is gone. There is no `anchor`.
- **Removed:** the "power users can override the chunk sizes in config.json" comment. No
  input backs it.
- **Kept:** the `or` fallbacks (`_obc_dates()`, `min_chunk_days or 1`,
  `lookback_days or 0`). With #325's tolerant reading, a config.json written before this
  change loads with these outputs as `None`, so the fallbacks are now reachable. #305's
  claim that old configs "fall back to the old behaviour" was false until then.

## Tests

- Window sweep, over run lengths from 1 to 393 days: every REGRID chunk of the padded
  window holds a record, and the window stays inside the data's coverage. The cases are
  monthly data starting on the 2nd of a month and on Feb 29, and daily data starting on
  the first day of its archive (the clamp).
- Wiring: `process_bc` and `process_ic` pass `min_chunk_days`, the boundary window and
  `lookback_days` from config.json on to the engines, which are mocked.
- Adapted: the all-configurators smoke test passes `function_args={}`, because
  `configure()` now builds the access request from it. #305's duplicate `function_name`
  branch there is dropped.

## Notes for reviewers

- **Not covered by a test** (test budget):
  - REGRID's empty-chunk error (#305's test for it is dropped);
  - `tseries_coverage`;
  - the `describe()` text;
  - the `or` fallbacks.

  A throwaway script checked by hand:
  - POP coverage over fake tseries names: the intersection across variables, and the
    month-end;
  - GLORYS with `subsample_freq="MS"` starting 1993-01-01 gets the window
    1993-01-01 → 1993-02-05;
  - a config.json without the four outputs loads and falls back to the run dates, 1
    and 0.
- **The IC takes the first record of its window** (regional-mom6's
  `setup_initial_condition` uses `isel(time=0)`). The lookback for monthly data is 30
  days. So once the tseries readers slice time (the #306 re-cut, next in this stack), a
  run that starts on the 1st after a month shorter than 31 days gets the previous month's
  record. That affects starts on Mar, May, Jul, Oct and Dec 1. Today the readers return
  whole files, so the IC is the file's first record anyway, which is the bug #306 fixes.
  Follow-up: take the last record at or before the start.
- **Configure now lists the CESM tseries files.** `parse_dataset` walks `dataset_path`
  once, for example the FOSI `month_1` directory on GLADE, and prints its usual "Parsing
  dataset" lines. A path that doesn't exist (off GLADE) gives `(None, None)`, so nothing
  is clamped.
- **Re-running `configure_forcings`** on an existing case marks its IC/OBC stale once,
  because the four new outputs are in the fingerprint.
- **Merge with #316's successor (declared output files):** both change the same engine
  signatures. Whichever lands second keeps `min_chunk_days`/`lookback_days`, and the
  wiring test guards this. If that PR lands first, the ic/bc `preview` arguments it
  removes stay removed.
- **WW3 is untouched.** It still takes its own `get_step_days`/`regrid_step_days` inputs.

Closes #333
Closes #353 (its boundary half; the IC half was #358)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
