# Forcing data: one way to handle space and time

Decided 2026-10-30 ("Yes. Do it all. As long as Region and TimeRequest are fairly small
intuitive classes"). Background and the full survey of today's code, with file:line, are in
`research/space-time-design.md`. Where the two differ, this file wins: it slims that design's
classes and drops its `AccessMethod` class (and its PR, Q24).

## The two classes

Each is a frozen dataclass of a few fields and four methods. Products and callers use nothing
else of them.

```python
# CrocoDash/raw_data_access/region.py
@dataclass(frozen=True)
class Region:
    """A lat/lon box to fetch. Longitudes run east from lon_min to lon_max, so a box
    across 180E is 170..190, and a 360-wide box is every longitude."""
    lat_min: float
    lat_max: float
    lon_min: float  # put on [-180, 180); lon_max moves with it
    lon_max: float  # lon_min <= lon_max <= lon_min + 360, else ValueError

    @classmethod
    def around(cls, lon, lat) -> "Region": ...
        # The smallest box holding these points (any shape), going the short way round.
    def padded(self, deg) -> "Region": ...
        # Grown by deg on every side; latitudes stop at +-90, the width at 360.
    def select(self, ds, lon="lon", lat="lat") -> xr.Dataset: ...
        # ds cut to the box by index. 1-D or 2-D lon/lat. Columns come west to east
        # across the source's own seam, each once, and longitudes are relabelled onto
        # lon_min..lon_min+360. On a 2-D source where the box's cells fall in more than
        # one column run (a tripole fold), every column of those rows is kept.
        # ValueError if no cell is in the box.
    def lon_ranges(self, west=-180) -> list[tuple[float, float]]: ...
        # The box's longitudes as one or two ranges inside [west, west + 360), for
        # remote APIs that can't take a range across their own seam.


# CrocoDash/raw_data_access/time_request.py
@dataclass(frozen=True)
class TimeRequest:
    """The records to fetch: every record from start to end, both days included, or,
    with dates, one record per date: the one whose time bounds hold it (the nearest
    one when the data has no time bounds)."""
    start: pd.Timestamp
    end: pd.Timestamp
    dates: tuple[pd.Timestamp, ...] | None = None  # thinned; None keeps every record

    @classmethod
    def every(cls, freq, start, end) -> "TimeRequest": ...
        # One date per freq from start to end, worked out once for the whole window,
        # so every chunk of it thins on the same dates. freq comes from configure,
        # where resolve_time_sampling already checked it is coarser than the data.
    def between(self, start, end) -> "TimeRequest": ...
        # One chunk of this request, keeping only its dates that fall inside.
    def days(self) -> list[pd.Timestamp]: ...
        # The days to read: the thinned dates, or every day start..end.
    def select(self, ds, time="time") -> xr.Dataset: ...
        # The records of ds this request asks for, in ds's own calendar (cftime and
        # noleap included; a Feb 29 date becomes Mar 1 there): those from start to
        # the end of the end day, then, with dates, the record whose time bounds hold
        # each date (CF `bounds` on the time coordinate), or the nearest record when
        # there are no bounds; each once. This is #327's rule: a mean stamped
        # mid-interval (MOM6) still counts for its own interval. ValueError naming the
        # window if none is left.
```

Not in either class: the configure-time checks (`resolve_time_sampling` and the coverage
check stay where they run), the IC rule (its caller takes `select(ds).isel(time=-1)` of a
window ending at the start), and the `data_freq` spacing check (it stays in the CESM readers,
the only methods that take `data_freq`).

## The rules every product follows

- **Space.**
  - A dated access method takes `region`, never `lat_min`/`lat_max`/`lon_min`/`lon_max`.
  - The buffer is added once, by `@accessmethod`. The decorator takes the product's
    default, `@accessmethod(..., buf=1.0)`. Its wrapper accepts `buf=` and passes
    `region.padded(buf)` to the method.
    - `buf` stays the name everywhere, so stored `function_args` like `{"buf": 1.0}`
      (e.g. the so1deg_wav golden config) keep working with no migration.
    - `get_function_default_args` lists `buf` for `function_overrides`.
  - Readers cut files with `region.select`. Remote APIs take `region.lon_ranges(...)`, or
    the box as is when they accept longitudes past 180.
  - Each product keeps its effective buffer from today, applied once. Change one only to
    fix a bug, and say so in the PR body.
- **Time.**
  - A dated access method takes `when`, a `TimeRequest`, never `dates`/`freq`.
  - The window is whole days with the end day included. Thinning is only to a coarser
    cadence, from `TimeRequest.every`.
  - The IC uses the record at or before the start.
  - A run outside the product's coverage fails at configure. The one-record padding past
    coverage keeps #333's warnings.
- **Errors** are raised early and say what to do, e.g. *"glorys has data 1993-01-01 →
  …; the run 1990-01-01 → 1990-02-01 is outside it. Move date_range inside it or choose
  another product."* A method that can't thin keeps #327's message ("cannot sub-sample it;
  drop subsample_freq").
- **Static products** (gebco, srtm, seawifs, tpxo, cice_restart's snapshot) take no `when`.
  A product with a box takes `region`.

## Delivery (stack T continues; one concept per PR, ~700 lines max)

| Q | Branch | Scope | Tests (the whole budget) | Needs |
|---|---|---|---|---|
| Q5 (#335) | `time-request` (re-cut; `tseries-time-slice` stays on origin at 2ac2823f) | <ul><li>`TimeRequest`.</li><li>`fetch_raw_chunk` passes `when=` to methods that take it and today's `dates` to the rest, for now.</li><li>OBC builds one `when` for the padded window: GET chunks take `when.between`, and REGRID slices with `TimeRequest(s, e).select`.</li><li>The IC is `TimeRequest(start - lookback, start)`, never thinned, and takes `select(...).isel(time=-1)`.</li><li>The CESM readers take `when`: #335's window slice and thinning are `when.select`.</li><li>Coverage refusal at configure.</li></ul> | <ul><li>`5D` thinning stays 5 days apart across two 7-day chunks.</li><li>A noleap IC starting on Feb 29 gets the record at or before it.</li><li>The CESM-POP reader keeps only the window's records (#335's test, kept).</li></ul> | Q7, Q8 (built on a local merge of `declared-output-files-v2` + `time-windows`) |
| Q20 | `region` | <ul><li>`Region`.</li><li>`@accessmethod(buf=)` pads once.</li><li>OBC edge boxes are `Region.around(ocean points)`, deleting `_ocean_bbox_for_boundary`'s plain min/max.</li><li>IC, CICE and WW3 boxes are `Region(**box)` from mom6_forge's `get_bounding_boxes`.</li><li>Every caller (OBC, IC, CICE, WW3) calls access methods through `fetch_raw_chunk`, or one helper next to it where no file is fetched. That one place passes `region=` to methods that take it and the 4 numbers to the rest, for now.</li></ul> | <ul><li>A grid split at ±180 gives an edge box of 170..190, and a polar edge a sub-arc.</li><li>`select` across a source's seam returns ordered, unique longitudes; a full circle gives each column once.</li></ul> | Q5 |
| Q21 | `glorys-reference-requests` | <ul><li>GLORYS (RDA, CDS, CLI script) and reference (ocean, ice, waves) on `region`/`when`.</li><li>The CLI script appends one `copernicusmarine subset` line per request: today it checks for `.sh` while rm6 writes `.pbs`.</li></ul> | <ul><li>RDA with a box across 180 returns ordered longitudes whose data matches its labels.</li><li>Two CLI calls keep both requests.</li></ul> | Q20 |
| Q22 | `cesm-cice-ww3jra-windows` | <ul><li>The CESM readers, cice_restart and CESM-WW3-JRA cut with `region.select`. `cice_restart` takes `buf=2.5`, and CICE's own ±1 goes.</li><li>CICE grid units come from the file's attributes (no `rad2deg` on degrees).</li><li>WW3-JRA gets `coverage()` that includes its spin-up.</li><li>A YYYYMM file end is read as the month's end.</li></ul> | <ul><li>CICE finds a box on a degree grid, and a box past the fold keeps every column of its rows.</li><li>A WW3-JRA run inside the spin-up is refused at configure.</li></ul> | Q20 |
| Q23 | `drop-loose-access-args` | <ul><li>ERA5 (`lon_ranges`, two areas across 180E, the globe for a full circle) and GLOFAS on `region`/`when`.</li><li>Delete `fetch_raw_chunk`'s adapters, the loose `required_args`, `make_dates_end_inclusive`, `convert_lons_to_180_range` and the three `validate_method` overrides: one validation builds a small `Region` and a 2-day `TimeRequest` inside coverage.</li><li>Update `adding_data_access.md`.</li></ul> | <ul><li>ERA5 across 180E gives two areas, and −180..180 the globe.</li><li>No registered dated method takes `lat_min` or `dates`.</li></ul> | Q21, Q22 |

Q16 (#338) and Q17 (#339) also need Q20: their segment and cyclic edge boxes become
`Region`s.

#327, #331 and #333 stay as built: `resolve_time_sampling` remains the configure-time check.

## As built (2026-10-30)

All five branches are pushed: `time-request` 4a92f657, `region` c0667295,
`glorys-reference-requests` e4d1532f, `cesm-cice-ww3jra-windows` 22e5beda and
`drop-loose-access-args` 1d315602. Where they depart from the rows above:

- **Q5:**
  - regrid_fn receives `when`.
  - `_record_at_start` raises when the start is outside the window.
  - `_obc_request` doesn't thin when `subsample_freq` equals the data's cadence (#327 already
    skipped that).
  - Thinned CESM subsets are named by their dates.
- **Q20:** CICE goes through `call_access_method`, not `fetch_raw_chunk`. Nothing would ever
  delete a CICE subset made with other `cice_function_args`, so it is fetched each run.
- **Q21:**
  - The CLI script keeps `buf=0.24`, writes `get_glorys_data.sh` (rm6 wrote `.pbs`), and doesn't
    add a request it already holds.
  - `reference_ice` ends at `buf=1.0` once Q22's `.padded(1)` is gone. See QUEUE.md's merge
    hazards.
- **Q22:**
  - CESM-WW3-JRA takes `when` as well.
  - CICE U points come from `qlon`/`qlat` on MOM6-format grids.
  - Grids whose radian values are labelled degrees are read by their values.
  - The coverage refusal lives in `time_windows.check_coverage`.
  - `WW3Configurator` gains start and end dates.
  - WW3-JRA's growth cap is `max_growth_deg=8.5` on top of `buf`.
  - `buffer_deg` is renamed `buf` everywhere.
- **Q23:**
  - Static products (cice_restart, reference_ice) and GLOFAS's processed-file script take no
    `when`.
  - ERA5 joins its areas on the region's longitudes, each meridian once.
  - The validation's toy dates start at each product's coverage.

Hand checks on GLADE, base e7bacfc9 against head 1d315602, in `/glade/derecho/scratch/manishrv/hc1030/`:

- **GLORYS RDA across 180E, and within 1° of -180:**
  - OBCs and IC match the base to 1e-14.
  - The IC request is one day.
  - Each case runs 2.5× faster (92 s against 248 s).
- **FOSI from 2000-07-01:**
  - The IC is the July mean (the base took January's).
  - OBC times run Jun–Oct with no repeats.
  - The base's OBC crashes on a repeated time label.
- **CESM-POP across POP's seam:** continuous longitudes and no NaNs. The base crashes as for FOSI.
- **GLADE-gated tests pass:** both cice_restart subsets, the CICE restoring process and
  CESM-WW3-JRA.
- **GLORYS via copernicusmarine across 180E:** correct, and matches RDA. It needs 17 GB
  (6 GB not across).
- **Open:**
  - `get_glorys_data_from_cds_api` returns a stale partial file after a retry
    (copernicusmarine writes `glorys_(1).nc`). This predates the stack.
  - Two `Region.select` bugs on 2-D sources (REGION_PLAN.md).

How Region could replace `longitude_slicer` everywhere, its test plan and the queryearth
question are in REGION_PLAN.md.
