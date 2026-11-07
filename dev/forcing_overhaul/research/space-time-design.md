# Forcing data: one way to handle space and time

**Date:** 2026-10-30
**Code:** worktree `tseries-time-slice` @ 2ac2823f. Paths without a prefix are under its `CrocoDash/`. `tests/` is the worktree's tests folder. `rm6` is `regional_mom6/regional_mom6.py` at the pin. Plan files are in `dev/forcing_overhaul/`.

**Recommendation.** Use two of the three angles together: request objects and minimal shared steps.
- **Request objects.** The caller builds two values once and passes them to every dated access call. A `Region` is the box. A `TimeRequest` holds the window, cadence, thinning and calendar.
- **Minimal shared steps.** The registry stops storing a bare staticmethod. It stores an `AccessMethod` object instead. Every call goes through that object, so no call can skip the standard steps. It:
  - checks that the `TimeRequest` was built for this method;
  - adds the buffer, exactly once;
  - checks the records the method wrote.
- **What stays.** Products are still plain functions declared with `@accessmethod`. Registration, metadata, `function_overrides` and the `product_name`/`function_name` stored in config.json keep working.
- **What I rejected.** The base-class template (section 10).

How the choice scores on the three lenses:
- **Correctness.** Seam handling, buffering, anchored thinning and the at-or-before-start rule each live in exactly one function.
- **Simplicity.** It adds two value types and one call object, and no class hierarchy. Each product loses its own box and date code.
- **Deliverability.** There is one concept per PR: `TimeRequest` (Q5), then `AccessMethod` (Q24), then `Region` (Q20). A temporary adapter lets callers switch first. Products then move over in three small PRs, and the last of them deletes the adapter.

---

## 1. The problem today

**Space.** Each product reads the four box numbers its own way.

| Product.method | How it selects the box | Buffer |
|---|---|---|
| glorys.get_glorys_data_from_rda | lat `sel`, then `longitude_slicer` (datasets/glorys.py:114-117) | `buf=1.0`, overridable (glorys.py:77) |
| glorys.get_glorys_data_from_cds_api | Raw numbers to copernicusmarine (glorys.py:144-155) | 1, fixed (glorys.py:146-149) |
| glorys.get_glorys_data_script_for_cli | Raw numbers to `rm6.get_glorys_data` (glorys.py:181-188) | 0.24, fixed (rm6:181) |
| cesm_pop_output / cesm_mom_output tseries readers | `bbox_mask` arc, then `where(drop=True)`. Columns are not rolled across the source's own seam (cesm_ocean_output.py:718-745, 851) | 1.5 + 1 = 2.5 (cesm_ocean_output.py:506-509, 846) |
| cesm_mom_output.get_mom6_output_data | `bbox_mask` per C-grid point on nominal axes (cesm_ocean_output.py:298-316) | 1.5 (cesm_ocean_output.py:242) |
| cice_restart.get_cice_restart_subset | `longitude_slicer` on tripole row 0 (cice_output.py:48-55). Applies `rad2deg` to a grid file that is now in degrees (cice_output.py:43-45) | Caller 1 + 1.5 (forcing/cice.py:524-527; cice_output.py:24) |
| era5_wave_spectra.get_era5_2d_spectra | Wraps each end separately. Raises on any box that crosses 180E; -180..180 becomes a 2° sliver (era5.py:139-142) | 1.0, fixed (era5.py:109, 154-157) |
| CESM-WW3-JRA.get_cesm_ww3_jra_spectra | `lon_min % 360` plus the span, read as cyclic index runs (cesm_ww3_jra.py:304-339, 550-564) | 1.5, growing to 10 (cesm_ww3_jra.py:587-594) |
| reference_ocean / reference_ice / reference_waves | `np.arange` around the box; latitude is never clamped (reference.py:135-136, 338-339, 434-441) | 1 / 0 (+ caller's 1) / 0 |

**Time.** Each product picks dates its own way.

| Product.method | Window and end | Thinning | Defect |
|---|---|---|---|
| glorys RDA, reference_ocean | `sample_dates`, whole days (base.py:123-129; glorys.py:86) | Anchored at each GET chunk's start | Gaps alternate 5 and 2 days for `5D` |
| glorys CDS / CLI | `make_dates_end_inclusive` gives 23:59:59 (glorys.py:142, 184) | None | Requests partly out of range only warn |
| CESM tseries readers | `select_records`, then `select_time_range` (cesm_ocean_output.py:690-715, 902-920) | Picks a record that the window slice then drops | IC with `QS` raises; a YYYYMM file end is read as day 1 (cesm_ocean_output.py:869-878) |
| cesm_mom_output.get_mom6_output_data | `date2num` slice from 00:00 to 23:59:59 (cesm_ocean_output.py:270-281) | Same as above | Raises on a Feb 29 window edge |
| era5 / CESM-WW3-JRA / reference_waves | Every hour, or 00Z–18Z every 6 h, of each day (era5.py:150-151; cesm_ww3_jra.py:220-238; reference.py:442-447) | None | WW3-JRA checks its range inside the call (cesm_ww3_jra.py:535-545) and never enforces the spin-up |
| glofas.get_global_data_with_python | Requests every year × month × day combination (glofas.py:43-56) | Declared, but over-fetches | Saves a zip under a `.nc` name (glofas.py:58, 62-63) |

**Callers.**
- **Two different box builders.**
  - IC, WW3 and CICE use mom6_forge `get_bounding_boxes`: forcing/ic.py:94-95, forcing/obc.py:804-806, forcing/cice.py:507.
  - The MOM6 OBC uses raw min/max over ocean points (forcing/obc.py:117-125). Production runs this path, because forcing/mom6.py:946 always passes the topo. On polar grids and on grids split at ±180 it fetches a whole latitude band.
- **The antimeridian flag is dropped.** `fetch_raw_chunk` forwards only four floats (forcing/utils.py:145-150). The only contract is the parameter names (base.py:398-405).
- **Windows exist only for conditions** (forcing/mom6.py:640-666). WW3 and CICE read the run dates directly (forcing/ww3.py:669-671; forcing/cice.py:514-518).
- **The IC is thinned with a lookback sized for unthinned data** (forcing/mom6.py:869-882, 662).
- **Two date slices raise on Feb 29 with noleap data:** REGRID (forcing/obc.py:409) and `_record_at_start` (forcing/mom6.py:319).
- **Two validation paths with loose arguments.**
  - `validate_method` injects `dates`/lat/lon at three places: base.py:373-383, base.py:435-446, and cesm_ww3_jra.py:466-470, which uses 2019 dates.
  - `ProductRegistry.call` → `validate_call` checks the loose `required_args` (registry.py:57-62; base.py:262-269).

## 2. The design

```python
# raw_data_access/region.py
@dataclass(frozen=True)
class Region:
    """A lon/lat box on the sphere. lon_min is in [-180, 180) and lon_max = lon_min + width,
    with 0 <= width <= 360, so a box across 180E ends past 180. width == 360 means every
    longitude. Latitudes are clamped to [-90, 90]."""
    lat_min: float; lat_max: float; lon_min: float; lon_max: float

    @classmethod
    def from_box(cls, lat_min, lat_max, lon_min, lon_max): ...  # any branch; lon_max < lon_min raises
    @classmethod
    def from_grid(cls, hgrid, part, ocean_mask=None): ...       # part is "ic" or an edge name: mom6_forge
                                                                # get_bounding_boxes, then tightened() to the
                                                                # edge's ocean points
    def tightened(self, lon, lat) -> "Region": ...              # smallest sub-arc of self holding the points
                                                                # (the arc logic stays in mom6_forge)
    full_circle: bool                                           # property
    def padded(self, deg) -> "Region": ...                      # the only place a buffer is added
    def lon_ranges(self, west) -> list[tuple]: ...              # for remote APIs: 1 or 2 ranges on [west, west+360)
    def index_window(self, lon, lat) -> tuple[slice, np.ndarray]: ...  # rows, and columns in seam order;
                                                                # 1-D or 2-D lon/lat; raises if empty. On a 2-D
                                                                # source whose cells in the box fall in more than
                                                                # one column run (a tripole fold), every column of
                                                                # those rows is returned
    def isel(self, ds, lon, lat, x_dim, y_dim) -> xr.Dataset: ...      # index_window applied; lon relabelled
                                                                # onto [lon_min, lon_min + 360)
    def axes(self, res): ...                                    # coordinates for the synthetic products

# raw_data_access/timing.py  (TimeSampling, USER_SPECIFIED and frequency_step move here from base.py)
@dataclass(frozen=True)
class TimeRequest:
    """Whole days start..end inclusive of one product method's data."""
    product: str; method: str
    start: pd.Timestamp; end: pd.Timestamp
    sampling: TimeSampling | None          # declared cadence, or data_freq (describes the data, never changes reads)
    thin: str | None = None                # coarser cadence only; dates come from sample_dates
    anchor: pd.Timestamp | None = None     # whole window's start, so every chunk thins on the same dates
    coverage: tuple = (None, None)
    calendar: str = "standard"; time_var: str = "time"
    at_start: bool = False                 # IC: keep the record at or before start

    @classmethod
    def for_method(cls, product, method, start, end, data_freq=None, freq=None, **method_args): ...
        # every refusal resolve_time_sampling makes today, plus the coverage check on the
        # unpadded run; runs at configure
    def chunk(self, start, end): ...       # same anchor and same thinning
    def initial(self, lookback_days): ...  # [start - lookback, start], no thinning, at_start=True
    def days(self): ...                    # whole days to read, thinned from the anchor
    def stamps(self): ...                  # every record time, for point products; clipped to coverage
    def api_range(self): ...               # ("YYYY-MM-DDT00:00:00", "YYYY-MM-DDT23:59:59")
    def select(self, ds): ...              # keep [start, end + 1 day) in the data's calendar (Feb 29 rolls to
                                           # Mar 1), thin to the nearest record per sample date, apply the
                                           # at-start pick, raise if empty
    def check(self, path): ...             # written file: records inside the window; with 2+ records, spacing
                                           # matches `thin or sampling` (0.8-1.25x, as select_records does today)

# raw_data_access/base.py
class AccessMethod:
    """What the registry stores for each @accessmethod function, and the one way to call it."""
    def __call__(self, *, when=None, region=None, buffer_deg=None, **args):
        if self.dated:
            if (when.product, when.method) != (self.product.product_name, self.name):
                raise TypeError(f"TimeRequest built for {when.product}.{when.method}, not {self}")
            args["when"] = when
        if self.spatial:
            pad = self.product.buffer_deg if buffer_deg is None else buffer_deg
            args["region"] = region.padded(pad)
        result = self.func(**args)
        if self.dated and self.type != "script" and when.sampling and not isinstance(result, xr.Dataset):
            when.check(Path(args["output_folder"]) / args["output_filename"])
        return result
```

After the change, every dated method looks like this:

```python
@accessmethod(description=..., type="python", subsample=True)
def get_glorys_data_from_rda(region, when, output_folder, output_filename, variables, dataset_path=RDA):
    ds = xr.open_mfdataset([day_file(d) for d in when.days()], ...)[variables]
    region.isel(ds, "longitude", "latitude", "longitude", "latitude").to_netcdf(...)
```

**The standard rules:**
- **Space**
  - Every box is a `Region`, built once by the caller.
  - The buffer is the product's `buffer_deg`, one name for every product. It can be overridden through `function_overrides["buffer_deg"]`, and `AccessMethod` adds it once.
  - Readers select with `isel`/`index_window` for files, or `lon_ranges` for remote APIs.
  - Full-circle boxes return each longitude once.
  - Fetched longitudes come back on the region's branch.
- **Time**
  - Every window is a `TimeRequest`: whole days, end inclusive.
  - Thinning is only to a coarser cadence, picked with `sample_dates` from the anchor.
  - The IC uses the record at or before the start.
  - Coverage of the unpadded run is checked at configure.

**What happens to each role `@accessmethod` plays today:**

| Role today | Where | After |
|---|---|---|
| Registration marker | base.py:195-203, 235-240 | Kept. `__init_subclass__` wraps each marked function in an `AccessMethod`, stores it in `_access_methods` and sets it back on the class. So `GLORYS.get_glorys_data_from_rda(...)` in tests and the gallery also runs the standard call |
| Stored as a staticmethod | base.py:196 | Replaced by the `AccessMethod` object (`get_access_function` docstring fixed, registry.py:43-49) |
| `ProductRegistry.call` / `validate_call` with loose `required_args` | registry.py:57-62; base.py:262-269 | `call` invokes the `AccessMethod`. `validate_call` becomes the method-name check plus `TimeRequest.for_method` (Q24) |
| description, type, how_to_use | generate_info.py:46-54; forcing/ic.py:86-91 | Kept, as plain attributes |
| subsample, data_freq flags | base.py:154, 168; forcing/mom6.py:591-594 | Kept as declarations; read only by `TimeRequest.for_method` |
| Signature contract by parameter name | base.py:247-256, 398-405 | Dated methods take `when`. Forcing methods take `region`, `when`, `variables`, `output_folder`, `output_filename`. `name`, which no product reads, is dropped (Q23) |
| Defaults for `function_overrides` | registry.py:63-77 | Read from `AccessMethod.func`, minus `region`/`when`, plus `buffer_deg` |
| Toy validation call | base.py:272-301, overridden at base.py:373-383, base.py:435-446, cesm_ww3_jra.py:466-470 | One validation on `AccessMethod`, with no overrides. It uses `Region.from_box(30, 30.1, 30, 30.1)` and a two-day `TimeRequest` that starts on the product's first covered day (2000-01-01 when coverage is open). USER_SPECIFIED products get the method's declared `data_freq`, or `'D'`. This keeps `test_validate_all_registered_access_methods` (tests/raw_data_access/test_base_registry.py:198-215) free of false coverage and data_freq refusals |

## 3. Per product

| Product.method | Change, or the graceful refusal |
|---|---|
| glorys.get_glorys_data_from_rda | Reads files for `when.days()`, with thinning anchored at the window start. `region.isel` replaces the lat `sel` plus `longitude_slicer`. `buf` becomes `buffer_deg = 1.0`, and stored configs are migrated (section 5) |
| glorys.get_glorys_data_from_cds_api | Passes the region's arc straight through (copernicusmarine handles >180 and ≥360) and uses `when.api_range()`. The pad becomes overridable. Refuses at configure: *"glorys.get_glorys_data_from_cds_api returns every D record in the range and cannot sub-sample it; drop subsample_freq, or use get_glorys_data_from_rda, which can."* |
| glorys.get_glorys_data_script_for_cli | Writes its own `copernicusmarine subset` line and appends it to one `get_glorys_data.sh`. This fixes the overwrite: the code checks for `.sh` while rm6 writes `.pbs` (glorys.py:178-180; rm6:187, 210, 217). Pads 1.0 instead of 0.24. Same freq refusal as the CDS method |
| reference_ocean.get_reference_ocean_data | `region.axes` with latitude clamped; `when.days()` |
| reference_ice.get_reference_ice_data | `region.axes` with latitude clamped; `buffer_deg = 1.0`, moved from forcing/cice.py:524-527. It is static, so it refuses freq: *"reference_ice returns a static snapshot; it takes no freq."* (base.py:148-152) |
| reference_waves.get_reference_wave_spectra | Stations along the region's long axis; `when.stamps()` |
| cesm_pop_output.get_cesm_single_variable_data | `region.isel` on TLAT/TLONG gives seam-ordered columns. This fixes the fold at about 110°W (t13) and 39.4°W (gx1v7) and stops broadcasting variables. One pad of 2.5. `when.select` replaces `select_records`/`select_time_range`/`_to_cftime`. `parse_dataset` reads a YYYYMM end as the month's end |
| cesm_mom_output.get_mom6_output_data | `region.isel` per C-grid point; `when.select`, so no `date2num` and Feb 29 is safe. The `time_var_name` argument is removed and the product's own is used. `buffer_deg = 1.5` |
| cesm_mom_output.get_mom6_single_variable_data | As the POP reader. `buffer_deg = 1.5` (was 2.5) |
| cice_restart.get_cice_restart_subset | `region.isel` on 2-D tlon/tlat replaces the row-0 slicer, which fixes the seam-gap ValueError near 73°E. A box that reaches the tripole fold gets every column of its rows, not two disjoint column runs. Units come from the attribute and dims from the file (ny/nx, degrees). `buffer_deg = 2.5`. It is static, so it refuses freq |
| era5_wave_spectra.get_era5_2d_spectra | `region.lon_ranges(-180)` gives one CDS area, two across 180E (concatenated), or the globe for a full circle. Latitude is clamped and `buffer_deg` becomes overridable. Refuses at configure: *"era5_wave_spectra.get_era5_2d_spectra returns every h record and cannot sub-sample it; drop the freq."* |
| CESM-WW3-JRA.get_cesm_ww3_jra_spectra | `Region.index_window` replaces `_axis_indices`/`_window_runs`, and the growing pad uses `region.padded`. New `coverage()` = (first restart + `spin_up_days=30`, last restart). Refuses at configure: *"CESM-WW3-JRA restarts are usable 2018-12-01 → 2024-01-01; the run 2018-11-01 → … is outside it."* `when.stamps()` is clipped to coverage, so an end on the last day is accepted. Its `validate_method` override (cesm_ww3_jra.py:466-470) is deleted |
| glofas.get_global_data_with_python | Takes `when` and loses `subsample`, so it refuses freq like the other Copernicus APIs. Requests `when.days()`, unzips into `output_filename`, then applies `when.select` |
| glofas.get_processed_global_glofas_script_for_cli | Takes `when` and ignores it, because it fetches one fixed file |
| gebco, srtm, seawifs, tpxo, cesm inputdata | Unchanged: static and without a box. mom6_forge `SourceBathy` and rm6 chl slice them downstream |

## 4. Callers

- **Conditions configure** (forcing/mom6.py:640-666). One `TimeRequest.for_method(product, fn, start, end, data_freq, subsample_freq, **function_args)` call replaces the two `resolve_time_sampling` calls and the `coverage` call.
  - A run (unpadded) outside coverage now fails here.
  - When only the one-record padding leaves coverage, #333's warnings (forcing/time_windows.py:91-101) stay as they are.
  - Q5 updates the `obc_window` docstring that says such a run fails at fetch (forcing/time_windows.py:54-55).
  - Otherwise `time_windows` is unchanged (chunk sizes, padded window, IC lookback, describe), and so are the outputs.
- **OBC** (forcing/obc.py, forcing/utils.py:119-157).
  - The window is `when = for_method(..., obc_start, obc_end, anchor=obc_start)`.
  - GET passes `when.chunk(s, e)` and the region to `fetch_raw_chunk`.
  - REGRID uses `when.chunk(s, e).select(ds)` instead of the string slice (obc.py:409).
  - Boxes come from `Region.from_grid(hgrid, b, ocean_mask=topo.supergridmask)`. `_ocean_bbox_for_boundary` (obc.py:73-125) and the fallback branch (obc.py:791-806) are deleted.
- **IC** (forcing/ic.py, forcing/mom6.py:311-324).
  - The request is `when.initial(lookback_days)`, which has no thinning. This fixes freq reaching the IC (forcing/mom6.py:869-882).
  - The box is `Region.from_grid(hgrid, "ic")`.
  - `when.select` on the raw file replaces `_record_at_start`.
- **CICE** (forcing/cice.py:309-322, 503-530).
  - The region is `Region.from_grid(expanded_grid, "ic")`, without the ±1.
  - `validate_args` runs `for_method`, so an unknown function name or a freq now fails at configure.
  - The call goes through `fetch_raw_chunk`. CICE therefore gains skip-if-exists and reads `output_folder/output_filename` instead of `subset_paths[0]`.
- **WW3** (forcing/ww3.py:539-555, 666-703).
  - `for_method` runs at configure, which adds coverage refusals and a function-name check.
  - It keeps the unpadded run dates; padding stays MOM6-only, per #333.
  - It keeps its GET/REGRID step inputs and full-edge `Region.from_grid(hgrid, b)` boxes.
  - `_wrap_lons_like` (ww3.py:372-377) stays, because it maps onto the target grid's branch.
- **BGC, chl, runoff, tides.** They make no access call and are unchanged. The `(lon+360)%360` in bgc.py:253-276 matches the GLOFAS grid for the map weights; it is not a fetch box.

## 5. Errors

| Mistake | Fails when | Message |
|---|---|---|
| `subsample_freq` on a method that can't thin | configure | `{p}.{m} returns every {f} record in the range and cannot sub-sample it; drop subsample_freq[, or use {m2}, which can].` |
| freq finer than the data; `data_freq` on a product's own data; USER_SPECIFIED without `data_freq` | configure | Existing messages (base.py:154-177) |
| Run (unpadded) outside the product's coverage | configure (new) | `{p} has data {first} → {last}; the run {start} → {end} is outside it. Move date_range inside it or choose another product.` When only the padding leaves coverage, #333's warning remains |
| `data_freq` doesn't match the files | first GET chunk (`when.check`, comparing with `thin or sampling` and skipped below 2 records) | `data_freq='MS' but the records in {file} are ~1 day apart; pass data_freq='D'.` |
| A chunk with no records | first such chunk (`select`/`check`) | `{p}.{m} returned no records for {start} → {end} from {source}; its data covers {coverage}.` |
| A box with no source cells (e.g. WW3-JRA beyond ±79.5°) | first GET chunk (`index_window`) | `{p} has no cells in {region}; its data spans latitudes {lo}..{hi}.` |
| A descending longitude box in a direct call | immediately (`Region.from_box`) | `lon_max is below lon_min; for a box across 180E give lon_max past 180, e.g. 170..190.` |
| A `TimeRequest` built for another method | call | `TypeError` naming both methods |
| config.json holds a renamed `function_args` key (`buf`) | reading config.json | No error. #325's config.json reader (forcing/base.py:720-744) maps `buf` → `buffer_deg` (Q21). This matters because stored `function_args` include the defaults, not only the user's overrides (forcing/mom6.py:869-882; registry.py:63-77; tests/forcing/golden_configs/so1deg_wav.json stores `{"buf": 1.0}`) |
| config.json holds a key that can't be mapped | reading config.json | `ReconfigureRequired`: `{p}.{m} takes no '{k}' any more (it takes: buffer_deg, …); run configure_forcings again.` Today the key is silently dropped (forcing/mom6.py:877-878) |
| A renamed or removed `function_name` in config.json | reading config.json | `ReconfigureRequired` instead of the raw `KeyError` (forcing/base.py:738-744; registry.py:47) |

## 6. Queue changes (review order)

| # | Q | Branch | Scope | Needs | Changed lines | Issue / PR |
|---|---|---|---|---|---|---|
| 1 | Q3 | `time-sampling` | Unchanged. Post the body from `prs/Q03-time-sampling.md` | main | +574/−49 (built) | PR #327 |
| 2 | Q6 | `typed-freq-inputs` | Unchanged | Q1, Q3 | built | #331 |
| 3 | Q8 | `time-windows` | Unchanged; one-record padding stays here | Q1, Q6 | +366/−29 (built) | #333 |
| 4 | Q5 | `time-request` (re-cut; `tseries-time-slice` parked at 2ac2823f) | `TimeRequest` only. Callers pass `when` through `fetch_raw_chunk`, which calls `when.check`. CESM readers take `when`: #335's window slice and at-or-before-start IC live in `select`. REGRID and IC select through it. Coverage refusal at configure, plus the `obc_window` docstring. An adapter turns `when` into loose dates for products not yet moved | Q7, Q8 | ~+400/−200 | #335, retitled |
| 5 | Q24 | `access-method` | `AccessMethod` in the registry. `ProductRegistry.call`/`validate_call` go through it. One toy validation replaces the three `validate_method` overrides. `when.check` moves from `fetch_raw_chunk` into `__call__` | Q5 | ~+200/−120 | new |
| 6 | Q20 | `region` | `Region`. `AccessMethod` pads once. obc/ic/cice/ww3 build Regions. Delete `_ocean_bbox_for_boundary` and CICE's caller pad. The adapter unpacks Regions for products not yet moved | Q24 | ~+400/−110 | new |
| 7a | Q21 | `glorys-reference-requests` | GLORYS ×3 and reference ×3 on `region`/`when`; their own CLI script. `buf` → `buffer_deg`, with the config.json migration in #325's reader. Unmappable keys and unknown `function_name` → `ReconfigureRequired`. Regenerate the golden configs. Replace the vacuous seam tests | Q20 | ~+340/−300 | new |
| 7b | Q22 | `cesm-cice-ww3jra-windows` | CESM ×3, cice_restart and CESM-WW3-JRA through `index_window`; WW3-JRA `coverage()`; month-end file parse | Q20 | ~+180/−280 | new |
| 8 | Q23 | `drop-loose-args` | ERA5 split areas; GLOFAS. Delete the adapter, the loose `required_args`, `make_dates_end_inclusive`, `convert_lons_to_180_range` and the textual inclusive-dates test. Update `adding_data_access.md` | Q21, Q22 | ~+180/−330 | new |

**#327, #331, #333** stay as built. In Q5, `resolve_time_sampling` and `sample_dates` move into `TimeRequest`.

**#335's scope moves into Q5.** The decided behaviour is unchanged: window-only records, and the IC record at or before the start.

**Other affected queue items:**
- **Q16 #338.** Needs Q20. `_segment_bbox` (interior-obc-v2 forcing/obc.py:69-77) becomes `Region.from_grid(hgrid, "ic").tightened(seg_lon, seg_lat)`.
- **Q17 #339.** Needs Q20. Cyclic north and south edges come out as full-circle Regions, and configure refuses east/west boundaries on cyclic grids.
- **Merge hazards.**
  - Q5 and Q20 touch forcing/ic.py, forcing/obc.py and forcing/mom6.py. That is why Q5 now needs Q7 as well as Q8. Q7's preview arguments are already resolved in favour of Q8's signatures (QUEUE.md:140).
  - Q21's migration edits #325's config.json reader, so #325 must have merged first.

**Keeping the 2-open rule.** Proposed rule text for QUEUE.md:11-12:
- At most 2 CrocoDash queue PRs are open at once. A draft counts unless it is blocked on another repo. Tiny PRs (under ~50 lines) and PRs blocked on another repo don't count.
- The next PR to open is the earliest-sprint item whose needs have merged, not the lowest Q number. Q13/Q14 already break Q order.

Today #325 (ready) and #327 (draft) count. #326 is exempt because it waits on ESMCI #52 and CDEPS#3. Q21 and Q22 are the only pair from this stack that may be open together, and only while nothing else is open.

## 7. Sprint changes

The cadence is unchanged: weekly from Tuesdays, about 2 PRs readied per week, each reviewed the following week. Five new PRs (Q20–Q24) extend the plan by three sprints. The forcing data work goes ahead of the sharing and CLI tail (Q12–Q15, Q19), because that is the work you are prioritising now.

| Sprint | Week of | Getting ready (you) | In review (alper requested) |
|---|---|---|---|
| 1 | Oct 27 | — | #325, ESMCI #51–#52, #279, #309, mom6_forge #155 |
| 2 | Nov 3 | #326 (Q2), #327 (Q3) | carry-over, CDEPS#3, ESMCI #54 |
| 3 | Nov 10 | #329 (Q4), #330 (Q9) | #326, #327 |
| 4 | Nov 17 | #331 (Q6), #332 (Q7) | #329, #330 |
| 5 | Nov 24 | #333 (Q8), #336 (Q10) | #331, #332 |
| 6 | Dec 1 | #335 (Q5, time-request), #334 (Q11) | #333, #336 |
| 7 | Dec 8 | Q24 access-method, #337 (Q12) | #335, #334 |
| 8 | Dec 15 | Q20 region, #341 (Q14) | Q24, #337 |
| 9 | Dec 22 | Q21, Q22 | Q20, #341 |
| 10 | Dec 29 | Q23, #340 (Q13) | Q21, Q22 |
| 11 | Jan 5 | #338 (Q16), #342 (Q15) | Q23, #340 |
| 12 | Jan 12 | #339 (Q17) | #338, #342 |
| 13 | Jan 19 | #343 (Q19), crocontainer #18, CrocoGallery #63 | #339 |
| 14 | Jan 26 | — | #343, crocontainer #18, CrocoGallery #63 |

Every item sits at least one sprint after each item it needs.

## 8. GitHub project changes (proposals only; nothing has been changed)

1. Retitle #335 to **"Every dated access call starts from a TimeRequest"** and replace its body with the Q5 scope above. Add #332 (Q7) as a blocker. It stays in Sprint 6, Backlog.
2. Create these issues, each assigned to manishvenu, status Backlog:
   - **Q24 "AccessMethod: every access call runs the same standard steps"**: blocked by #335, Sprint 7.
   - **Q20 "Region: build each fetch box one way and pad it once"**: blocked by Q24, Sprint 8.
   - **Q21 "GLORYS and reference products read through Region and TimeRequest"**: blocked by Q20 and #325, Sprint 9.
   - **Q22 "CESM output, CICE restart and CESM-WW3-JRA read seam-ordered windows"**: blocked by Q20, Sprint 9.
   - **Q23 "ERA5 and GLOFAS on Region/TimeRequest; drop the loose lat/lon/dates arguments"**: blocked by Q21 and Q22, Sprint 10.
3. Add Q20 as a blocker of #338 and #339.
4. Move these items to new sprints, with no status changes:

   | Item | From | To |
   |---|---|---|
   | #341 | 7 | 8 |
   | #340 | 8 | 10 |
   | #338 | 8 | 11 |
   | #342 | 9 | 11 |
   | #339 | 9 | 12 |
   | #343 | 10 | 13 |
   | crocontainer #18 | 10 | 13 |
   | CrocoGallery #63 | 10 | 13 |

5. Add the iterations Sprint 11 (2027-01-05), Sprint 12 (2027-01-12), Sprint 13 (2027-01-19) and Sprint 14 (2027-01-26). Pass every existing iteration id back, as QUEUE.md requires.
6. Replace PR #327's body with `prs/Q03-time-sampling.md`, which needs your OK.
7. Housekeeping found while reading:
   - Close #328 (open, not on the board) as a duplicate of #329.
   - Close or un-sprint ESMCI #53, which QUEUE.md:79-80 says is no longer needed.
   - Add #344 to Backlog for triage.
   - Create a Backlog issue, **"Static download methods crash on their defaults"**:
     - `output_folder=None` in seawifs.py:47, gebco.py:70 and srtm.py:59;
     - GEBCO returns `None` (gebco.py:40);
     - `write_bash_curl_script` opens the script before the folder exists (datasets/utils.py:28, 38).

## 9. Tests (1–3 per PR, one per guarantee)

- **#327, #331, #333:** their existing tests, unchanged.
- **Q5**
  - `test_thinning_is_anchored_across_get_chunks`: `5D` over two 7-day chunks stays 5 days apart. Catches the 5/2-day alternation (base.py:123-129 applied per chunk).
  - `test_initial_record_at_or_before_start`: noleap monthly data, `subsample_freq='QS'`, start 2000-02-29; one Feb record comes back. Catches the empty IC ValueError and the Feb 29 slice failure (forcing/mom6.py:319).
  - `test_data_freq_mismatch_is_reported`: a daily file declared `data_freq='MS'` raises the `check` message, and a daily file thinned to `5D` passes. Catches readers that never checked `data_freq`, and a check that compares against the wrong cadence.
- **Q24**
  - `test_validate_all_registered_access_methods` (existing, tests/raw_data_access/test_base_registry.py:198-215) passes with no `validate_method` overrides. Catches toy calls that trip coverage or USER_SPECIFIED refusals.
  - `test_time_request_for_another_method_is_refused`: a direct `GLORYS.get_glorys_data_from_rda(...)` call with a CDS `TimeRequest` raises `TypeError`. Catches direct calls that skip the standard steps.
- **Q20**
  - `test_edge_region_is_an_arc`: a grid split at ±180 gives 170..190, and a polar north edge gives a sub-arc of 135..225, not -180..180. Catches forcing/obc.py:117-125.
  - `test_index_window_crosses_source_seam_in_order`: column 0 at 250°E. A straddling box gives ascending, unique longitudes, and a full circle gives each column once. Catches the `where(drop=True)` fold and slicer complement arcs.
- **Q21**
  - `test_rda_box_across_180`: 170..190 returns 169..191 with data matching its labels. Replaces the vacuous tests at tests/raw_data_access/test_glorys.py:8-65 and 108-133.
  - `test_cli_script_keeps_every_request`: two calls write two subset lines. Catches glorys.py:178-180.
  - `test_stored_buf_migrates_to_buffer_deg`: the so1deg_wav golden config reads back with `buffer_deg=1.0`. Catches breaking every existing GLORYS-RDA case.
- **Q22**
  - `test_cice_window_on_degree_grid`: a ny/nx grid in degrees finds the Gulf of Mexico box, and an Arctic box past the fold returns every column of its rows. Catches cice_output.py:43-45 and disjoint fold columns.
  - `test_ww3_jra_refuses_spin_up_at_configure`: a November 2018 run is refused. Catches the missing spin-up check (cesm_ww3_jra.py:280-301).
- **Q23**
  - `test_era5_area_across_180`: 170..190 gives two areas and -180..180 gives the globe. Catches era5.py:139-142.
  - `test_dated_methods_take_region_and_when`: across the whole registry, no method takes `lat_min` or `dates`. Replaces the textual allowlist test (tests/raw_data_access/test_dates_inclusive.py:83-104).

## 10. Alternatives considered

**Base-class template, rejected.** Each product would implement locate/read hooks and inherit one `fetch()`. That breaks the things that hold the current system together:
- registration, which scans for staticmethods in the class `__dict__` (base.py:235-240);
- the flags, which are read off the wrapper with no default (forcing/mom6.py:591-594);
- about 40 direct `Product.method(...)` calls;
- everything keyed by method name: config.json, the golden configs, forcing/obc.py:521 and the MCP.

The hooks would still need a shared definition of a box and a window, and that is what `Region` and `TimeRequest` are. `AccessMethod` already gives one call that always runs the standard steps, without changing how products are written. If products ever need subclassing, they can switch to classmethods later.

**Minimal shared steps alone, rejected as the whole answer.** A wrapper that only normalises loose numbers can't carry the window's anchor, the at-start rule or coverage across chunks. Each product would still read four floats its own way; a descending pair already means four different things. The design keeps this angle's best idea, that the standard steps run in the registry's call, and replaces the loose arguments with values.

## 11. Open questions

1. **Keep #327, #331 and #333 as built, or re-cut them into `TimeRequest` now?** I recommend keeping them. They are built, #327 is open, and the move in Q5 is mechanical.
2. **Mean-record time stamps differ by product.** POP is dated at the interval start (cesm_ocean_output.py:662-687) and MOM6 output at mid-interval. GLORYS RDA is at noon, against 00:00 from Copernicus. I recommend leaving them: nearest-record thinning plus one-spacing padding select correctly for each. Standardise only if a run shows a phase shift.
3. **How to expose the buffer override.** I recommend one `function_overrides["buffer_deg"]` key for every product rather than a new typed input. Q9's per-key specs can type it later.
4. **Copernicus GLORYS coverage.** Both Copernicus methods use only the `my` dataset (glorys.py:143; rm6:213), but `coverage()` is open-ended (glorys.py:45-49). I recommend that Q21 sets the `my` end date after one catalogue check, so configure refuses later runs and points to RDA. Adding `myint` is a separate feature.
5. **Spatial refusals at configure.** I recommend keeping them at process time (first chunk) for now. They can move to configure once Q16 puts `case_supergrid_path` into the configure inputs.
6. **Holiday weeks (Sprints 9–10).** I recommend keeping the table. If alper is away, shift Sprint 9 onward by one week without reordering.

## Critiques not taken

- **Tripole fold (index_window), partly taken.** I dropped the claim that the fold rows are fixed and specified the fold behaviour. I chose "every column of those rows" over raising an error, because polar CICE/POP boxes are supported and regridding uses the 2-D coordinates.
- **Q5 bundling, partly taken.** `AccessMethod` is split out as Q24, and `ReconfigureRequired` moves into Q21's migration as suggested. The coverage refusal stays in Q5, because it is part of `TimeRequest.for_method`.
- **Duplicate alper reviewer on #325, taken by removing the item.** `gh pr view 325` shows one review request (alperaltuntas); the other alper entries are reviews, so the housekeeping item was dropped.