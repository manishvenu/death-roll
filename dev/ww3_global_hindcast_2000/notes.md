# Global CESM+WW3 hindcast (Jan 2000) — working notes

Companion to the full plan (written during planning, not checked into this
repo): the goal is a global CESM+WW3 run archived as real reference data,
feeding a new `CESM_WW3_OUTPUT` raw_data_access product in CrocoDash on a
branch off PR #268 (`ww3-new`). This directory holds the case-setup artifacts
for the run itself; the CrocoDash product code is a separate, later step once
the run has produced real data to read.

Environment note: this session runs on a Casper node. CIME's `case.setup`/
`case.build`/`case.submit`/`xmlquery`/`xmlchange` all enforce a machine-match
check against the case's configured machine (`derecho`) and fail if invoked
from the wrong host. `ssh derecho` **works from this session** (confirmed
2026-08-12) — use it for every CIME lifecycle command. GLADE is shared, so
plain file edits (user_nl_*, points.list, notes) don't need ssh.

## Confirmed configuration

- **CESM checkout**: `~/work/installs/cesm3_0_beta08_gui` — already has the
  WW3 component, the `GW_JRA` compset, and grid `TL319_t232_wg37` wired in.
  No submodule merging needed.
- **Compset**: `GW_JRA` =
  `2000_DATM%JRA-1p5-2023_SLND_CICE_MOM6_DROF%JRA-1p5-2023_SGLC_WW3`
  (`components/mom/cime_config/config_compsets.xml`). MOM6 + CICE + WW3,
  JRA55-do v1.5 reanalysis winds (real, 1958–2023) — not an active atmosphere,
  much cheaper, and consistent with the rest of CROC's MOM6 stack.
- **Grid**: `TL319_t232_wg37` — global ~1°. `t232`=tx2_3v2 (MOM6/CICE
  tripole), `wg37`=wgx3v7 (WW3 curvilinear, confirmed shape **116 x 100**
  from `grid_inp.wgx3v7.260527/g37_{x,y,mapsta}.inp`).
- **Input data**: all confirmed present on
  `/glade/campaign/cesm/cesmdata/inputdata` — no staging needed.
  - Wave grid: `wav/ww3/grid_inp.wgx3v7.260527/`
  - JRA55 v1.5 forcing: `ocn/jra55/v1.5_noleap/JRA.v1.5.<var>.TL319.{1999,2000}.*.nc`
    (calendar is **noleap** — Jan has 31 days regardless, not an issue for a
    Jan-only window, but worth remembering if run length crosses Feb).
- **Real coupled run precedent**: a regional MOM6+WW3 run (8 days, real ERA5
  boundary spectra) already ran clean end-to-end on Derecho
  (`dev/ww3_obc_dev/ww3_boundaries_demo_real_era5.ipynb`) — confidence the
  coupled model itself is stable; what's new here is running it *globally*
  and *archiving point-spectra output*.

## Point/spectral output — the one manual step

CESM's WW3 supports native point output
(`namelist_definition_ww3.xml`'s `output_type_nml` ->
`type%point%file`, default `'points.list'`) — the same mechanism NOAA's own
global hindcast uses to feed regional nests with boundary spectra.

**Confirmed by reading `components/ww3/cime_config/buildnml` directly: this
is not automatic.** `buildnml` only stages `wav_in` and `mod_def.ww3` into
`$RUNDIR` — it never copies or references `points.list`. WW3 reads
`points.list` from its own working directory (`$RUNDIR`) at run time, so it
has to be placed there by hand after `case.setup` creates `$RUNDIR` and
before `case.submit` actually runs the model. See `setup_case.ipynb` step 4.

`generate_points_list.py` in this directory builds that file directly from
the wgx3v7 grid's own coordinate + status-map files (not an independent
land/sea mask, so every point is guaranteed WW3-active on the exact grid the
model runs on). `mapsta==1` selects only plain active sea points (excludes
mapsta 2/3 boundary/excluded-sea edge cases). `--stride` subsamples to
control point-output volume; default 2. Ran successfully at stride=3 → 896
points; stride=1 would give ~roughly 4x that (full 116x100 sea-point count).

**Second, more important gap found while writing `setup_case.ipynb`:**
`namelist_definition_ww3.xml` exposes `type%point%file` but never defines
`date%point%start/stride/stop` (confirmed by grepping every "point"-related
entry in the file — one hit). The Fortran reader
(`model/src/w3nmlshelmd.F90`'s `READ_OUTPUT_DATE_NML`) defaults
`DATE%POINT%STRIDE` to `'0'` when it's absent from the namelist, which is
WW3's own "off" convention — so `points.list` staged correctly would still
produce *no* point output without this fix. `add_point_output_dates.py`
works around it the way `buildnml` itself supports: writing a
`$CASEROOT/SourceMods/src.ww3/namelist_definition_ww3.xml` override (copy of
the real file + the 3 missing entries) — buildnml's own comment says a user
definition there "*replaces* existing definition", so it must be the full
file, not a diff/fragment. `setup_case.ipynb` step 3a runs this before step 3b
sets the actual point-output namelist values via `user_nl_ww3`.

## Timing

- **Spin-up**: start **1999-12-01**, run through **2000-01-31** (≈62 days).
  Not a rigorous spin-up study — just cheap insurance so the wave field (and
  CICE/MOM6 state) isn't still responding to a cold start during the archived
  Jan 2000 window. Flag Dec 1999 output as spin-up, not part of the archived
  product data, unless kept separately for reference.
- Point-output cadence: hourly, matching `ERA5_WAVE_SPECTRA`'s cadence in
  CrocoDash's existing WW3 forcing pipeline (`raw_data_access/datasets/era5.py`)
  so the new product's time resolution matches what `WW3Configurator` already
  expects.

## Open items / risks for later steps

- `ww3_ounp` post-processing of the raw point output into per-point spectra
  NetCDF is a separate manual step **after** the run completes — not covered
  by this directory yet.
- Data archived under `croc_input/` (scratch), per user's decision — not
  campaign storage. Exact subdirectory layout TBD once real output exists;
  mirror `CESM_POP_OUTPUT`'s FOSI archive convention when it's created.

## Shakeout run results (2026-08-12 → 2026-08-14)

Ran the actual case end-to-end at `~/croc_cases/g.ww3hindcast.jra.TL319_t232_wg37.2000-01`
with `STOP_N` temporarily set to 3 days (`1999-12-01` → `1999-12-04`),
`points.list` at `--stride 2` (1967 points). **Succeeded** — case.run and
st_archive both completed cleanly (`CaseStatus`: "model execution success",
"st_archive success").

**Two real bugs found and fixed while getting the build to succeed** (beyond
the SourceMods namelist-definition gap already documented above):
- `STOP_OPTION=nday` is invalid — CIME's real valid-value list is
  `none/never/nsteps/nseconds/nminutes/nhours/ndays/nmonths/nyears/date/end`.
  It's `ndays`, not `nday`. Fixed in `setup_case.ipynb`.
- Even after adding the `date_percent_point_percent_*` XML entries via
  the SourceMods override, `user_nl_ww3` values with embedded spaces
  (`'19991201 0'`) or plain unquoted tokens (`3600`) get rejected by CIME's
  `NamelistDefinition.is_valid_value` with "Invalid values [...]" — the
  underlying check is `is_valid_fortran_namelist_literal(type_, scalar)`,
  and since these entries are declared `type=char`, every value must be a
  properly single-quoted Fortran string literal (`'19991201 0'`, `'3600'`),
  not a bare token. Fixed in `setup_case.ipynb`'s user_nl_ww3 cell.

**Point output confirmed working**: `out_pnt.ww3` (raw binary, native WW3
point-output format) appeared in `$RUNDIR`, **354,621,832 bytes for 3 days
at 1967 points, hourly** — this is the actual artifact `ww3_ounp` post-
processes into per-point spectra NetCDF. Scaling to the full 63-day window:
≈354.6MB × 21 ≈ **6.9 GB** — trivial for scratch storage.

**Native WW3 "field" history (`*.ww3.hi.*.nc`) never appears** — `wav/hist/`
in the archive is empty even though `wav_in`'s `output_type_nml`/
`output_date_nml` clearly configure "Type 1: Fields of mean wave parameters"
hourly (confirmed in the wav log). Root cause, worked out by comparing
against what actually *did* get archived: CESM's WW3 NUOPC cap appears to
route gridded diagnostic fields through **CMEPS's own coupler-history
export mechanism** instead of calling WW3's native field-output writer —
confirmed by finding `cpl/hist/*.cpl.hx.ww3.<date>.nc`, which contains
`wavImp_Sw_Hs`, `wavImp_Sw_t01`, `wavImp_Sw_t0m1`, `wavImp_Sw_thm`,
`wavImp_Sw_lamult/ustokes/vstokes` on the full 116×100 wave grid. Point
output and restart, by contrast, clearly ARE handled by WW3's own native I/O
(both files exist with expected native-format names) — only the "field"
path seems to go through the mediator instead. **Not a blocker**: this
`cpl.hx.ww3` file is exactly what's needed for the Phase C QC sanity check
(Hs range, plausibility) even though it isn't the `wav/hist` layout
`dev/ww3_obc_dev/animate_hs.py` was written against for an earlier regional
run — that earlier run may have had `type%field%file` wired differently, or
this cap behavior is compset/coupling-config dependent; not investigated
further since point output (the data the actual product needs) is
unaffected.

**Walltime**: model execution alone (excluding queue wait) took **27m8s**
for 3 simulated days ⇒ ≈542.7s/sim-day. Scaling to the full 63-day window:
≈9.5 hours — comfortably inside the 12-hour walltime `case.submit` already
requested by default for this PE layout (896 OCN + 384 ATM/ROF/CPL/ICE + 128
WAV tasks, ~1400 total). **Queue wait, separately, was long** — over a day
(submitted 2026-08-13 10:15, started 2026-08-14 13:24) on Derecho's `main`
queue for this size job — worth expecting for the full run too, independent
of the run itself succeeding quickly once it starts.

**Not yet decided**: whether to reset `STOP_N` back to 63 and resubmit the
full window on this same case (straightforward — case is already built and
configured correctly) — that's the next real go/no-go decision, separate
from this shakeout.
