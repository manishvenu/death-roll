# Declare each dated product's time sampling and add an optional freq

## Why

Products say nothing about how their records are spaced in time, so everything
downstream treats GLORYS daily means, CESM-POP monthly means and ERA5 hourly snapshots
alike. The forcing workflow cuts every product into the same 7-day GET and 30-day
REGRID chunks, and a 30-day chunk of monthly data can fall between two records and come
out empty. Nothing in the data access layer could ask for fewer records either (a year
of daily GLORYS from RDA is 366 file opens; monthly it is 12), or be told the cadence of
an archive the user points it at (CESM-MOM output, a CESM-POP `day_1` archive).

This PR adds the declaration and the `freq` argument only. Sizing chunks and fetch
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

- **`freq`** (set with `function_overrides={"freq": ...}`) is taken only by methods
  marked `@accessmethod(freq_handling=...)`:
  - `"subsample"` fetches every `freq` instead of every record: GLORYS from RDA, GLOFAS
    via cdsapi, reference_ocean.
  - `"declare"` takes `freq` as the cadence of the source: the CESM-POP reader and both
    CESM-MOM readers. CESM-MOM output requires it.
  - `resolve_time_sampling` holds the rules (never finer than native, none for a static
    product). `configure_forcings` runs it, so a bad `freq` fails at configure time.
- **CESM-POP dates:** the month shift (`subtract_month`) now applies only to monthly
  data. With `freq="D"`, every record used to move back a month, and days 29–31 all
  landed on the 28th.
- **Older config.json:** `ConditionsConfigurator` passes the access method only the
  stored `function_args` it still takes. A config written by the #303 branch carries
  `"freq": null` whatever the method, and still processes.
- **Docs:** `adding_data_access.md` covers `time_sampling` and `freq_handling`.

Cut from #302/#303:
- `TimeSampling.anchor`: nothing read it except `describe()` text, and CESM-POP's
  `"end"` described stamps that `subtract_month` had already moved.
- The per-method `@accessmethod(time_sampling=...)` override: no product used it.
- The rule that every dated access method takes `freq=None`, and that parameter on the
  static, script-only and WW3 methods. A product defined outside the repo no longer
  needs it.
- `assert` in the declaration check: now `TypeError`, which `python -O` doesn't strip.
- Unchecked `freq_handling`: a typo silently meant "native only". It now raises
  `ValueError` when the method is decorated.

## Tests

- Every registered dated product declares `time_sampling`; a missing one raises
  `ValueError`, a wrong type `TypeError`.
- `TimeSampling` rejects a bad alias or `cell_method`, gives `max_period_days` for
  D/MS/6h/YS, and is written into the product metadata.
- `resolve_time_sampling` returns the native sampling by default, sub-samples to a
  coarser `freq`, refuses a finer one, and refuses a non-native `freq` for a method that
  can't sub-sample.
- With `"declare"`, `freq` is the source cadence; a `USER_SPECIFIED` product needs it; a
  static product takes none.
- `sample_dates` strides from the `freq` anchor and falls back to the window start.
- reference_ocean with `freq="MS"` over a year returns 12 records.
- New: CESM-POP read with `freq="D"` keeps its dates (synthetic noleap file, no GLADE).

## Notes for reviewers

- `freq` stays a key in `function_overrides` here. A later PR replaces it with typed
  conditions inputs. Nothing sizes chunks from the declaration yet.
- Not tested, to keep within the test budget: the `freq_handling` check and the
  `function_args` filter.
- The filter is only on the conditions path. #303 wrote `"freq": null` only into the
  conditions `function_args`. `ww3_obc_function_overrides` and `cice_function_args` hold
  only what the user typed, and nothing checks their keys at configure time, so
  filtering them would turn a typo's `TypeError` into a silently ignored argument.
- A `freq` for a method without `freq_handling` is now refused by `configure_forcings`'
  existing "Invalid function_overrides key(s)" check.
- Re-running `configure_forcings` on a case configured before this PR marks its IC/OBC
  stale once. The conditions fingerprint includes `information`, which now carries
  `time_sampling`, and `function_args`, which now carries `freq` for the methods that
  take it.
- POP daily records keep the stamps POP wrote, at the end of each averaging day. Only
  monthly records are shifted.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
