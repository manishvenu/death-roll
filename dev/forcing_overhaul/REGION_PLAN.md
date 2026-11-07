# Region as the general longitude cutter: tests, open bugs, and queryearth

Written 2026-10-30, after the hand checks of stack T. `Region` (Q20, #345) already replaces
`longitude_slicer` inside CrocoDash (GLORYS RDA, CESM output, CICE, WW3-JRA). This file plans
what it takes for it to replace `longitude_slicer` everywhere it is used, and what that means
for queryearth. SPACE_TIME.md still holds the class contract.

## Where longitude_slicer is used today

| Caller | Source | What it cuts |
|---|---|---|
| `mom6_forge/_source_bathy.py:157` | GEBCO, SRTM, ETOPO (1-D, up to 86,400 columns) | bathymetry; skipped for pole-encircling grids |
| `regional-mom6/regional_mom6.py:2288` | ERA5 surface fields (0..360, descending latitude) | atmospheric forcing |
| CrocoDash `glorys.py`, `cice_output.py` | GLORYS RDA, CICE grids | removed by Q21/Q22; now `Region.select` |

`longitude_slicer` takes only 1-D, uniformly spaced, global longitudes. It keeps a count of
columns worked out from the spacing, centred on the box's midpoint, and labels them in the
caller's convention.

## What the comparison found

`hc_slicer_diff.py` (in `/glade/derecho/scratch/manishrv/hc1030/`) ran both on four 1-D
conventions (-180..180, 0..360, 0..360 with descending latitude, a source starting at 250E)
against ten boxes each.

- **Where both work, they keep the same columns.** The one exception is a column exactly on
  the east edge: Region keeps it and longitude_slicer drops it. That is a longitude_slicer
  bug (a 0..359 box on 1° data loses 358.5).
- **longitude_slicer refuses valid boxes** that Region cuts correctly: 170..190 on
  -180..180 data, -5..5 and the full circle on 0..360 data, and -190..-170 on a source
  starting at 250E. It says "the data doesn't include the longitude", which is wrong.
- **The labels differ.** longitude_slicer returns 245..255 for a 245..255 request. Region
  normalises `lon_min` to [-180, 180) and returns -114.9..-105.1. ESMF doesn't care: it
  works on the sphere. Code that afterwards selects by the grid's own numbers would break.
  This is the main decision before Region can replace longitude_slicer in mom6_forge and
  regional-mom6.

On real 2-D data (HR POP, CESM-HR FOSI, 3600×2400, with NaN coordinates on POP's
eliminated all-land blocks), `Region.select` has two bugs. Both are at the pushed head
(1d315602):

1. **A box spanning a continent keeps the whole globe.** The NaN land blocks split the box's
   columns into runs. `select` reads that as a tripole fold and keeps all 3,600 columns
   (Sahel 10–15°N; South America 10°S–0°). The data is still right, just global-width.
   Ocean boxes, Florida, Panama and Central America were fine.
2. **Labels jump by 360 at the west edge of a 2-D cut.** A 2-D cut is an index rectangle,
   so it holds cells just west of `lon_min`, and those are relabelled +360 (Italy, 8–19°E,
   gives 8.0..368.0). ESMF is unaffected. Coverage checks, plots and min/max are not.

Fixes:

- **Bug 1:** when looking for runs, a gap whose columns are all NaN over the box's rows
  joins the runs on each side.
- **Bug 2:** relabel around the box's middle, onto [mid - 180, mid + 180). A 1-D result is
  unchanged, and a 2-D one becomes continuous.
- **Label convention:** if the stored `lon_min` keeps the caller's value (only checking
  lon_min ≤ lon_max ≤ lon_min + 360), the same relabel also gives the caller's convention.
  245..255 then comes back as 245..255, as longitude_slicer does.

Raw file names stay stable, because a given grid always uses one convention.

## Test plan

These tests follow the repo's rule of one test per real guarantee. Each test checks against
a brute-force oracle rather than hand-written expected arrays. The oracle: keep every source
cell whose (lon - lon_min) mod 360 ≤ width and whose lat is in [lat_min, lat_max], and
nothing else unless the source folds. That way a parametrised matrix stays a few lines.

| # | Test | Matrix | Checks |
|---|---|---|---|
| 1 | `test_select_1d_against_the_oracle` | 5 sources (-180..180; 0..360; starting at 250E with the wrap column repeated; descending latitude; uneven spacing) × 7 boxes (inside; across ±180; across the source's seam; across 0; full circle; edges on cell centres; lon_min > 180) | kept columns = oracle; labels ascending, unique, continuous; data follows labels |
| 2 | `test_select_2d_against_the_oracle` | POP-like (columns from 250E), a tripole fold, NaN land blocks across the box, full circle | every oracle cell kept; extra columns only for a real fold; labels continuous along x (bugs 1 and 2) |
| 3 | `test_select_refuses` | narrower than a cell; outside a regional source; more than 360 wide | ValueError naming the box and the data's extent |
| 4 | `test_select_matches_longitude_slicer` | the cases longitude_slicer supports | same columns and data; delete it when longitude_slicer is gone |
| 5 | `test_select_real_sources` (GLADE, slow) | GLORYS RDA, ERA5, GEBCO, POP gx1v7, POP HR (NaN blocks), MOM6 tx2_3v3, a CICE grid × (inside, across ±180, across the source's seam) | the test 1/2 oracle, plus a time budget (GEBCO's 86,400 columns) |

Box membership on its own (edges, ±180, full circle) needs no separate test: tests 1 and 2
exercise it through `select`.

Outside the test suite, the end-to-end check is the one run today: build the same small case
with the base code and with the head code, then compare every output file. The scripts are
`hc_case.py`, `hc_compare.py` and `run_pair.sh` in `/glade/derecho/scratch/manishrv/hc1030/`.
Rerun it when Region's cutting changes, on these cases: across 180E, within 1° of -180, across
POP's seam, a FOSI case, and one bathymetry case once mom6_forge uses Region.

## Where Region should live if it replaces longitude_slicer everywhere

In **mom6_forge**, next to `longitude_slicer`, which it would replace. regional-mom6 and
CrocoDash both already depend on mom6_forge, and mom6_forge already depends on xarray.
CrocoDash would import `Region` from there. `TimeRequest` stays in CrocoDash: it is the only
package that fetches dated forcing.

Migration order:

1. Fix bugs 1 and 2, and make the label-convention decision, on `region` (restack Q21 to Q23).
2. Move `Region` to mom6_forge, with tests 1 to 4 (one mom6_forge PR).
3. Switch `_source_bathy` to `Region.select`. The pole-encircling special case becomes a
   full-circle Region.
4. Switch regional-mom6's ERA5 cut to it.
5. Delete `longitude_slicer` once nothing calls it.

## queryearth: should it take this over, or the other way round?

The two don't do the same job:

- **queryearth 0.7** decides whether two shapes or intervals meet, with no data involved.
  - Space is points and polygons, cut at ±180, with closed edges; pole-encircling rings are
    refused.
  - Time is one proleptic Gregorian calendar, deliberately.
  - Its only core dependencies are numpy and shapely.
  - It is pre-alpha (0.x, with API changes per minor release) and still in its design phase.
- **Region and TimeRequest** cut xarray data by index.
  - TimeRequest works in the data's own calendar (noleap, 360_day) and uses CF time bounds.

### If queryearth took Region and TimeRequest over

Gains:

- One antimeridian implementation for the org.
- A neutral home that mom6_forge, regional-mom6 and CrocoDash could all share.

Costs:

- **Dependencies.** xarray and cftime would join a core kept at two dependencies on
  purpose. An optional `queryearth[xarray]` module would contain that.
- **Calendars.** TimeRequest.select must follow noleap and CF bounds. Single-calendar time
  was a deliberate simplification of the core, so this would reverse it.
- **Release coupling.**
  - CrocoDash's main forcing path, and mom6_forge's bathymetry, would hard-depend on a
    pre-alpha package. Today only the `cd_qe_int` branch uses queryearth.
  - Every fix to a cut would wait for a queryearth release, which you approve by hand.
  - CrocoDash's pin (<0.8) would hold back fixes for a whole minor series.
- **Scope.** It is the "reballooning" you wanted to avoid.

### If Region and TimeRequest replaced queryearth's space and time

That doesn't work. Region is only a box. queryearth needs points and polygons: grid outlines,
the current and front shapes in CrocoDash's rules, and GLHE's lakes.

### Recommendation

Keep them separate, and make them agree on purpose:

- **Shared semantics:** closed edges, longitudes wrapped the same way, and a full circle at
  360.
- **One cross-check test, on the CrocoDash side once it depends on queryearth:** for a
  matrix of boxes and points (edges, ±180, near the poles), Region's oracle membership must
  equal `qe.space.meets(qe.space.box(...), qe.space.point(...))`.
- **One converter where CrocoDash queries its rules:**
  - Region → `qe.space.box(lon_min, lat_min, lon_max, lat_max)`;
  - `TimeRequest.start` and `.end` → `qe.time.interval`.

Revisit this only if a second, non-ocean user (GLHE?) needs to cut gridded data. That would
be the moment for a small shared package.
