# Declare each dated product's time sampling; add data_freq and freq

## Why

Products say nothing about how their records are spaced in time, so everything
downstream treats GLORYS daily means, CESM-POP monthly means and ERA5 hourly snapshots
alike. The forcing workflow cuts every product into the same 7-day GET and 30-day
REGRID chunks, and a 30-day chunk of monthly data can fall between two records and come
out empty. Nothing in the data access layer could ask for fewer records either (a year
of daily GLORYS from RDA is 366 file opens; monthly it is 12), or be told the cadence of
an archive the user points it at (CESM-MOM output, a CESM-POP `day_1` archive).

This PR adds the declaration and the `data_freq` and `freq` arguments only. Sizing chunks and fetch
windows from the declaration comes in a later PR (#305, re-cut).

## What

Replaces #302 and #303, rebased onto current main and amended.

- **`TimeSampling(frequency, cell_method)`** is required metadata on every
  `DatedBaseProduct`. A bad declaration raises `TypeError` before the class is
  registered. `USER_SPECIFIED` marks a product whose cadence depends on the data the
  user points it at; `None` marks a static snapshot.

  | product | time_sampling |
  |---|---|
  | glorys, glofas, reference_ocean | `D`, mean |
  | cesm_pop_output | `MS`, mean |
  | cesm_mom_output | `USER_SPECIFIED` |
  | era5_wave_spectra | `h`, point |
  | cesm-ww3-jra, reference_waves | `6h`, point |
  | cice_restart, reference_ice | `None` |

- **Two arguments, set with `function_overrides`.** An access method's decorator says
  which ones it takes:
  - `@accessmethod(subsample=True)`: `freq` thins the data to a coarser cadence. The
    method fetches every `freq` instead of every record, with `sample_dates`. Used by
    GLORYS from RDA, GLOFAS via cdsapi, reference_ocean and the CESM readers.
  - `@accessmethod(data_freq=True)`: `data_freq` is the cadence of the data at the path
    the user gives. Used by the CESM-POP reader and both CESM-MOM readers; CESM-MOM
    output requires it.
  - `data_freq` only describes the files: they are read the same way whatever its
    value. The CESM readers check it against the spacing of the records they find, and
    raise when it doesn't match, e.g. `data_freq="D"` on a `month_1` archive.
  - `resolve_time_sampling` holds the rules: `freq` never finer than the data, nothing
    for a static product, and an argument only for a method that takes it.
    `configure_forcings` runs it, so a bad value fails at configure time.
  - A bad alias says so: "'monthly' isn't a pandas frequency alias, e.g. 'D', 'MS' or
    '6h'."
- **CESM-POP dates come from `time_bound`.**
  - POP stamps each mean at the end of its averaging interval, so January's mean is
    stamped Feb 1. A record stamped at its interval's end is now dated at the first day
    of that interval. That's the day, because POP's first interval starts a model step
    after midnight (00:31:40 in CESM-HR).
  - Monthly means get the same dates as main's `subtract_month`. Daily means get their
    own day; `subtract_month` used to move them back a month and put days 29–31 on the
    28th.
  - No flag depends on the cadence any more. MOM6 output, stamped mid-interval, is left
    alone.
- **CESM thinning:** with `freq`, the CESM readers keep, for each sampled date, the
  record whose averaging interval holds it (the nearest record when the data has no
  time bounds). `sample_dates` works in the data's calendar, e.g. noleap.
- **Older config.json:** `ConditionsConfigurator` passes the access method only the
  stored `function_args` it still takes. A config written by the #303 branch carries
  `"freq": null` whatever the method, and still processes.
- **Docs:** `adding_data_access.md` covers `time_sampling` and the two decorator flags.

Cut from #302/#303:
- `TimeSampling.anchor`: nothing read it except `describe()` text, and CESM-POP's
  `"end"` described stamps that `subtract_month` had already moved.
- The per-method `@accessmethod(time_sampling=...)` override: no product used it.
- The rule that every dated access method takes `freq=None`, and that parameter on the
  static, script-only and WW3 methods. A product defined outside the repo no longer
  needs it.
- `assert` in the declaration check: now `TypeError`, which `python -O` doesn't strip.
- `freq_handling="subsample"|"declare"`, which made each method take one meaning of a
  single `freq`. It is replaced by the two flags, so a CESM reader can be told its
  cadence and thin it.

## Tests

- Every registered dated product declares `time_sampling`; a missing one raises
  `ValueError`, a wrong type `TypeError`.
- `TimeSampling` rejects a bad alias or `cell_method`, gives `max_period_days` for
  D/MS/6h/YS, and is written into the product metadata.
- `resolve_time_sampling` returns the native sampling by default, sub-samples to a
  coarser `freq`, refuses a finer one, and refuses a non-native `freq` for a method that
  can't sub-sample.
- `data_freq` names the source cadence and `freq` thins it; a method that takes no
  `data_freq` refuses one; a `USER_SPECIFIED` product needs it; a static product takes
  neither.
- `sample_dates` strides from the `freq` anchor and falls back to the window start.
- reference_ocean with `freq="MS"` over a year returns 12 records.
- GLORYS from RDA with `freq="MS"` reads only the month starts in the window, and every
  day without `freq` (file lookups mocked).
- A CESM-POP file stamped like POP's, with `time_bound` and a first interval starting
  at 00:31:40, is dated at each month's first day. `freq="2MS"` keeps January and
  March, and `data_freq="D"` raises (synthetic noleap file, no GLADE).

## Notes for reviewers

- `data_freq` and `freq` stay keys in `function_overrides` here. A later PR replaces
  them with typed conditions inputs.
- **Nothing sizes chunks or pads the fetch window from the declaration yet.** On its
  own, `freq="MS"` runs per 7-day GET chunk, a chunk without a month start falls back to
  its first day, and nothing reads the record before the run's start. The time-windows
  PR sizes the chunks to the record spacing and pads the window by one spacing each
  side.
- Not tested, to keep within the test budget: the `function_args` filter.
- Checked by hand on GLADE against CESM-HR's `month_1` SSH for 1958:
  - the default reads Jan 1 to Dec 1;
  - `freq="QS"` reads Jan 1, Apr 1, Jul 1 and Oct 1;
  - `data_freq="D"` raises.
- The filter is only on the conditions path. #303 wrote `"freq": null` only into the
  conditions `function_args`. `ww3_obc_function_overrides` and `cice_function_args` hold
  only what the user typed, and nothing checks their keys at configure time, so
  filtering them would turn a typo's `TypeError` into a silently ignored argument.
- A `freq` or `data_freq` for a method that doesn't take it is refused by
  `configure_forcings`' existing "Invalid function_overrides key(s)" check.
- Re-running `configure_forcings` on a case configured before this PR marks its IC/OBC
  stale once. The conditions fingerprint includes `information`, which now carries
  `time_sampling`, and `function_args`, which now carries `freq` for the methods that
  take it.
- POP records are dated at the first day of their averaging interval at every
  cadence, monthly or daily.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
