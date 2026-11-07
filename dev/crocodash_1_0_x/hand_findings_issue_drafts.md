# Issue drafts for the hand-found findings (not filed)

One draft per finding, generated from AUDIT.md. Nothing here has been posted. Each body is the AUDIT.md entry under a one-line provenance note, the same shape as the issues already filed from the audit (#359–#373). Check the target repo and board before filing.

## H1: `crocodash dump > file.yaml`, as the docs show, writes log lines into the YAML, so `crocodash create --config file.yaml` fails

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** `crocodash dump > file.yaml`, as the docs show, writes log lines into the YAML, so `crocodash create --config file.yaml` fails

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro
- **Confidence:** high
- **Location:** CrocoDash/logging.py:28 (`StreamHandler(sys.stdout)`); CrocoDash/visualCaseGen/visualCaseGen/gui.py:18 (the `[gui]` line); docs/source/for_users/cli.md:109
- **Already fixed on main:** No
- **Related:** C11 (relative caseroot); first-pass lead "dump writes caseroot relative" (recipe.py:277)

**What's wrong.** The CLI docs say to save a case with `crocodash dump --caseroot <case> > mycase_copy.yaml`. CrocoDash's logger writes to stdout, the same stream as the YAML. The file therefore starts with `INFO [gui] Constructing visualCaseGen GUI` and `INFO [CrocoDash.recipe] Setup configuration arguments...`, and `crocodash create --config mycase_copy.yaml` fails with `yaml.scanner.ScannerError: mapping values are not allowed here` at line 3, column 5. Second problem: when `--caseroot` is given as a relative path, the dumped `caseroot:` is relative too. `create` then hits C11 and fails with "Cannot write to /glade/u/home/<user>/cases/<name>".

**Repro.** `crocodash dump --caseroot cases/audit_gwr2 > gwr3.yaml`; change the caseroot/inputdir names; `crocodash create --config gwr3.yaml` → ScannerError. With the two INFO lines removed and an absolute caseroot (`audit_repros/extra/gwr3_clean.yaml`), `create` succeeds. The rebuilt GWR_JRA case then has the same case state and CICE/WW3 forcing config as the original, apart from the expected new session id. Expected: the dumped file is valid YAML and recreates the case.

**Root cause.** `setup_logger` sends INFO records to `sys.stdout`, and `_dump` prints the YAML to stdout.

**Smallest fix.** Send log output to stderr (at least in the CLI), or add `--output FILE` to `dump`. Also write `caseroot` as an absolute path in `case_to_yaml`.

</details>

## H2: Runoff coastline mask wraps around on non-cyclic grids, so the edge opposite a land edge counts as coast and receives runoff

- **Target repo:** NCAR/mom6_forge
- **Title:** Runoff coastline mask wraps around on non-cyclic grids, so the edge opposite a land edge counts as coast and receives runoff

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** mom6_forge
- **Severity:** wrong result
- **Evidence:** confirmed by repro, through CrocoDash process_forcings. A first-pass verifier also saw it as a side observation, noted in M2's Related field.
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:122
- **Already fixed on main:** No (same line 122 on 83d7692)
- **Related:** M1, M2 (same runoff-mapping code)

**What's wrong.** `extract_coastline_mask` pads the land/sea mask with `np.pad(..., mode="wrap")`. On a regional (non-cyclic) grid, this makes the column on one edge a neighbour of the column on the opposite edge. Ocean cells on the edge opposite a land edge, usually an open boundary, are then flagged as coast. The nearest-neighbour and smoothed runoff maps deliver runoff to them.

**Repro.** `audit_repros/extra/gwr2.py`: a GWR_JRA case on an 8x8 grid with land in columns 0–1 and reference products, then `process_forcings`. In `GLOFAS_to_gw_map_nn.nc`, the destination columns receiving runoff are [2, 7]. Expected: [2] only. Column 7 is the east (open) edge.

**Root cause.** Wrap padding is only right for cyclic grids.

**Smallest fix.** Pad with `mode="edge"`, so a cell's outside neighbour is itself and never makes it coast. Wrap only in x, and only for cyclic-x grids.

</details>

## H3: Runoff mapping fails with "nearest neighbor map maps no runoff at all" for every domain south of 60°S (the GLOFAS grid stops there) and for all-ocean domains

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** Runoff mapping fails with "nearest neighbor map maps no runoff at all" for every domain south of 60°S (the GLOFAS grid stops there) and for all-ocean domains

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash. The check itself is in mom6_forge and is deliberate; the message and the flow belong to CrocoDash.
- **Severity:** crash for Antarctic domains (no way through except a compset without runoff); misleading error for all-ocean test boxes
- **Evidence:** confirmed by repro (both triggers)
- **Confidence:** high
- **Location:** CrocoDash/forcing/runoff.py:180 → mom6_forge/mapping.py:1184 (`gen_rof_maps`) → mapping.py:1092 (`_check_runoff_conserved`)
- **Already fixed on main:** No (mom6_forge main has the same check)
- **Related:** H2; M1 (the map_overlap mask). Not in TRIAGE, QUEUE or the open issues.

**What's wrong.** Every JRA compset (GR_JRA, CR_JRA, GWR_JRA, ...) activates Runoff, which is marked [REQUIRED], with ROF_GRID=GLOFAS. The GLOFAS v4 mesh covers only 59.975°S to 89.975°N (`GLOFAS_esmf_mesh_v4.nc` centerCoords). So a domain wholly south of 60°S has no source cells at all, even with a real coastline. An Antarctic case therefore stops in process_forcings with `ValueError: nearest neighbor map maps no runoff at all.`, which happens on a polar-stereographic EPSG:3031 grid (a preset in the grid creator) or on any Ross/Weddell/Amundsen shelf box. An all-ocean domain (an open-ocean box or flat test bathymetry) gets the same error because its coastline mask is empty. The message names neither cause nor a way out.

**Who hits it.** Anyone building an Antarctic or Southern Ocean shelf domain with a JRA compset. Domains that straddle 60°S work, and get runoff only from their northern part.

**Repro.**

- Antarctic: `audit_repros/extra/polar.py <dir> wed EPSG:3031 -2200000 -1000000 1000000 2200000`. The case:
  - Weddell Sea, 24x24 cells at 50 km, 76.7°S–62.2°S;
  - GEBCO_LOWRES topo, 97% ocean with real Antarctic coast;
  - GR_JRA, GLORYS from RDA, CICE restart restoring.

  Grid, topo, case creation and the GLORYS fetch all succeed, then process_forcings fails at runoff with the ValueError. The same case's IC, OBC and CICE inputs process fine with runoff skipped (`crocodash process --caseroot ... --ic --bc --cice`).
- All-ocean: `audit_repros/extra/gwr.py`: GWR_JRA on an 8x8 grid with flat 1000 m bathymetry gives the same ValueError.
- Expected: for Antarctica, a runoff map that maps nothing (GLOFAS has no rivers there) or a clear message naming the options; the same for an all-ocean box. Whether CESM accepts an empty map is untested.

**Root cause.** Runoff mapping assumes at least one GLOFAS source cell and one coastal ocean cell are in reach, and `_check_runoff_conserved` treats zero mapped runoff as an error.

**Smallest fix.** In `Runoff.process`, detect "domain south of the GLOFAS grid" and "no coast" before building maps. Then either write a zero map, or raise a message that names the cause and the options (a compset without runoff, or a runoff source that covers Antarctica). Antarctic users need the zero map or another source, because GLOFAS will never cover them.

</details>

## H4: `VGrid.from_file` crashes with AttributeError when given a `pathlib.Path`

- **Target repo:** NCAR/mom6_forge
- **Title:** `VGrid.from_file` crashes with AttributeError when given a `pathlib.Path`

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** mom6_forge
- **Severity:** misleading error (minor)
- **Evidence:** confirmed by repro
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/vgrid.py:143
- **Already fixed on main:** No. #155 renamed the reader to `from_vgrid_file`, which still has the bare `file_path.endswith(".nc")` assert.
- **Related:** none. CrocoDash's recipe.py passes strings, so YAML recipes aren't affected.

**What's wrong.** `VGrid.from_file(Path("vgrid.nc"))` raises `AttributeError: 'PosixPath' object has no attribute 'endswith'`. Users who pass `Path` objects, as CrocoDash's own code does, get a confusing error.

**Repro.** `audit_repros/extra/mf_checks.py`, section 7.

**Smallest fix.** Use `str(filename).endswith(".nc")`, or `Path(filename).suffix == ".nc"`.

</details>

## H5: MOM6 silently drops the end of INPUTDIR paths of 128 characters or more, and CrocoDash doesn't check, so runs fail with "Unable to open OBC file .../ocnforcing_obc_..."

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** MOM6 silently drops the end of INPUTDIR paths of 128 characters or more, and CrocoDash doesn't check, so runs fail with "Unable to open OBC file .../ocnforcing_obc_..."

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** crash (at model run time, with a misleading error)
- **Evidence:** confirmed by a Derecho run (2026-11-06 late). Before that it was from reading the MOM6 source CrocoDash builds against, and the weekly crocontainer CESM tests had hit the same failure.
- **Confidence:** high
- **Location:** CrocoDash/case.py init_args_check (no length check); CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_creator.py:735 (writes `INPUTDIR = <inputdir>/ocn`); MOM6 `core/MOM_open_boundary.F90:1273` and `framework/MOM_domains.F90:132` (`character(len=128) :: inputdir`, then `slasher()`)
- **Already fixed on main:** No
- **Related:** none filed

**What's wrong.** MOM6 reads INPUTDIR into a 128-character buffer in the OBC and domain code, then appends "/". If `<inputdir>/ocn` is 128 characters or longer, the slash is lost and MOM6 looks for `.../ocnforcing_obc_segment_001.nc`. Case() and configure_forcings accept such paths without a word. The audit's own scratch cases had a 168-character INPUTDIR, and nothing complained.

**Repro.** Any Case() whose `inputdir/ocn` path is 128 characters or longer, e.g. `audit_repros/extra/dates.py` run from the session scratchpad, writes `INPUTDIR = <168 chars>` to user_nl_mom with no warning. MOM6 side: `grep -n "len=128) :: inputdir" components/mom/MOM6/src/core/MOM_open_boundary.F90`.

**Run-time confirmation.** I ran two cases on Derecho (develop queue, 1 task, the same executable), identical except for INPUTDIR:
- `audit_rA`, with a 45-character INPUTDIR, initialises and runs;
- `audit_rB`, with the same files under a 140-character INPUTDIR, stops at MOM6 initialisation with `FATAL:  Unable to open OBC file /glade/derecho/scratch/manishrv/ar/i/long_xxxx…xxxforcing_obc_segment_001.nc`. The path is cut at 128 characters and loses `/ocn/` (`audit_repros/extra/run_tests/clone_runs.sh`).

**Root cause.** A fixed-length Fortran buffer in MOM6, with no matching check upstream of it.

**Smallest fix.** In `init_args_check`, refuse (or warn about) any `inputdir` where `len(str(Path(inputdir).resolve() / "ocn")) > 127`, with a message that names the MOM6 limit. Optionally, report the buffer size upstream to MOM6.

</details>

## H6: A time of day in date_range is silently dropped: the run starts at 00:00 (START_TOD=0)

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** A time of day in date_range is silently dropped: the run starts at 00:00 (START_TOD=0)

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** wrong result (minor)
- **Evidence:** confirmed by repro
- **Confidence:** high
- **Location:** CrocoDash/case.py configure_forcings (RUN_STARTDATE / STOP_N xmlchanges); CrocoDash/forcing/mom6.py:419 (dates stored as %Y%m%d)
- **Already fixed on main:** No
- **Related:** first-pass lead "config.json stores conditions dates as %Y%m%d, so dump/duplicate/fork turn a 12:00 start into midnight and change STOP_N"; 1.1 Q5/#335 (TimeRequest)

**What's wrong.** `date_range=["2020-01-01 12:00:00", "2020-01-03 12:00:00"]` is accepted, but the case gets RUN_STARTDATE=2020-01-01, START_TOD=0 and STOP_N=2. The boundary records are at 00:00. The model starts 12 hours earlier than requested, with no warning. A dumped or recreated case then changes STOP_N too.

**Repro.** `audit_repros/extra/dates.py`, first date range.

**Smallest fix.** Either refuse a non-midnight time with a clear error (products are daily), or set START_TOD and keep the time through the config.

</details>

## H7: Case(override=True) can't recreate a case made for another machine (e.g. ubuntu-latest from Casper): it cleans the host's CIME_OUTPUT_ROOT, so create_newcase aborts on the old bld/run dirs

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** Case(override=True) can't recreate a case made for another machine (e.g. ubuntu-latest from Casper): it cleans the host's CIME_OUTPUT_ROOT, so create_newcase aborts on the old bld/run dirs

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** misleading error
- **Evidence:** confirmed by repro
- **Confidence:** high
- **Location:** CrocoDash/case.py:205-212 (third `case_dirs` entry, `Path(self.cime.cime_output_root) / self.caseroot.name`); visualCaseGen/cime_interface.py:753-762 (`cime_output_root` comes from the host machine's config)
- **Already fixed on main:** No
- **Related:** C6 (same line). C6's more accurate fix, reading EXEROOT and RUNDIR from the old case, fixes this too.

**What's wrong.** override=True removes `<host CIME_OUTPUT_ROOT>/<case name>`. A case created for a different machine (non-local creation) keeps its EXEROOT and RUNDIR under *that* machine's CIME_OUTPUT_ROOT; for ubuntu-latest that's `$HOME/cesm/scratch/<case>`. Those dirs are left in place, and create_newcase, which visualCaseGen runs with `--handle-preexisting-dirs a`, aborts. Case() then raises "a previous case with the same name left its build/run directories behind (see the message above)". The message above is only CIME's "ERROR: Aborting by user request", which names no directory. So override=True never works for such a case.

**Who hits it.** Users who create a case on GLADE for the crocontainer's ubuntu-latest machine (or any machine whose output root differs from the host's), then rerun with override=True. This is niche: the documented container path creates a derecho case and forks it inside the container.

**Repro.** `audit_repros/extra/nonlocal.py <dir> ubuntu-latest reference_ocean`, run on Casper with HOME pointed at a scratch dir, so that `$HOME/cesm/scratch` stays out of the real home.

- First run: the case is created, configured and processed (NTASKS 4, BATCH_SYSTEM none, CALENDAR and STOP_N right).
- Second run, the same call with override=True: "Removing previous case files" for inputdir and caseroot only, then the abort above.
- Deleting `$HOME/cesm/scratch/<case>` by hand lets the third run succeed.
- Expected: override removes the old case's own EXEROOT and RUNDIR, wherever they are. Observed: they are left behind, and the case can't be recreated.

**Root cause.** The cleanup uses the host's output root, not the old case's.

**Smallest fix.** Before deleting the old caseroot, read EXEROOT and RUNDIR from it (env_build.xml, env_run.xml) and remove those (C6's fix). Also name the leftover dirs in the error.

</details>

## H8: chl processing refuses every grid except a plain lat-lon `Grid()`: process_forcings fails late with "This function currently only supports rectangular grids"

- **Target repo:** CROCODILE-CESM/regional-mom6
- **Title:** chl processing refuses every grid except a plain lat-lon `Grid()`: process_forcings fails late with "This function currently only supports rectangular grids"

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** regional-mom6 (CROCODILE-CESM fork, as pinned in CrocoDash/rm6), reached through CrocoDash's Chl configurator
- **Severity:** crash (late, after IC/OBC; the message is clear but there is no way through except dropping chl)
- **Evidence:** confirmed by repro
- **Confidence:** high on the failure. Medium that MOM6 needs nothing else: MOM6 reads CHL_FILE on the model domain by index, so the LAT/LON axes are metadata only (from reading).
- **Location:** CrocoDash/rm6/regional_mom6/chl.py:51-53 (`assert grid.is_rectangular()`); the 1-D LAT/LON taken from the middle row and column at chl.py:122-123; called from CrocoDash/forcing/chl.py `Chl.process`
- **Already fixed on main:** No
- **Related:** first-pass rm6 lead (now confirmed and removed from *Unverified leads*); closed CrocoDash #234 (curvilinear grids). Not in TRIAGE or QUEUE.

**What's wrong.** `interpolate_and_fill_seawifs` asserts that the grid is rectangular in lat/lon. Only `Grid(lenx, leny, resolution, ...)` passes. These all fail (`Grid.is_rectangular()` is False):
- `Grid.from_center`, even with angle 0;
- `Grid.from_projection`: polar EPSG:3995/3031, and Albers EPSG:3338 as in the gallery's KitchenSink;
- `Grid.from_supergrid` on the gallery's NWA12 hgrid.

configure_forcings accepts `chl_processed_filepath` for any grid. The AssertionError comes from process_forcings only after the IC and OBC steps.

**Who hits it.** Anyone who turns on chlorophyll (penetrative shortwave) on a projected, rotated or file-based grid. The gallery's chl example uses a plain `Grid()`, so it doesn't show this.

**Repro.** `audit_repros/extra/chl_polar.py <dir>` on the Arctic case from `polar.py`:

- with no extra argument it fails with the AssertionError above;
- with `bypass` it patches `is_rectangular` to True and writes 12 months with no NaNs on wet cells. Summer values reach 5.2 mg/m^3, and the polar-night months (Oct–Mar) are filled with 0.

So the regridding itself (`regrid_with_subsampling` on the 2-D qlon/qlat) handles the polar grid.

**Root cause.** The rectangular check guards only the 1-D LAT/LON axis values written to the file.

**Smallest fix.** Drop the assert. Write nominal 1-D axes (e.g. the cell index, or the centre row and column as now), or 2-D `geolon`/`geolat` alongside them, since the data is already on the model grid.

</details>

## H9: `Grid.subgrid_from_supergrid` fails with "Lower left corner must be to the left of upper right corner" for valid boxes across the parent grid's x-seam or inside its tripolar cap

- **Target repo:** NCAR/mom6_forge
- **Title:** `Grid.subgrid_from_supergrid` fails with "Lower left corner must be to the left of upper right corner" for valid boxes across the parent grid's x-seam or inside its tripolar cap

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** mom6_forge
- **Severity:** misleading error
- **Evidence:** confirmed by repro
- **Confidence:** high
- **Location:** mom6_forge/grid.py:731-740 (`subgrid_from_supergrid`: nearest (j, i) per corner, then `full_grid[llc_j:urc_j, llc_i:urc_i]`); grid.py:926-954 (`get_indices`: KD-tree on raw (lat, lon) degrees)
- **Already fixed on main:** No (NCAR/mom6_forge main 83d76928 has the same code)
- **Related:** none found in the open issues, TRIAGE or QUEUE

**What's wrong.** The subgrid is the index box between the nearest grid points to the two corners. That only works where the parent's i index increases with longitude between them. On the gallery's global 1/12° hgrid (`HGRID_TRIMMED`, 4320x3240, longitudes −287 to 73) it fails in two ways:
- a box that crosses the parent's x-seam at 73°E, e.g. llc (0, 65), urc (10, 81), the Laccadive Sea and Maldives, gets llc_i > urc_i;
- a box reaching into the tripolar cap, e.g. llc (50, 10), urc (75, 40), Baltic to Barents: (75°N, 40°E) maps to column 3512, left of (50°N, 10°E) at column 3544.

Both raise the AssertionError in the title, which suggests the user swapped the corners. Boxes that stay below the cap and inside one seam span work (the gallery's Hawaii example gives 142x203).

**Who hits it.** Users carving a regional grid out of a global tripolar MOM6 grid for the Nordic Seas, Barents Sea or Arctic, or for any region straddling the parent's longitude seam.

**Repro.** `audit_repros/extra/subgrid.py`: the Hawaii box works, and the two boxes above fail with the AssertionError.

**Root cause.** The corner-to-index mapping assumes a lat-lon-aligned, non-wrapping parent.

**Smallest fix.** For a cyclic parent, roll the grid in i so the seam falls outside the box before slicing. In the cap, raise a message that names the real cause: the box isn't an index rectangle there, so the user should pass index bounds or stay south of the cap. Optionally accept explicit (j, i) bounds.

</details>

## H10: An inputdir containing a space makes the model abort during initialisation, with no message naming the path

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** An inputdir containing a space makes the model abort during initialisation, with no message naming the path

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** crash (at model run time, with no useful message)
- **Evidence:** confirmed by a Derecho run
- **Confidence:** high
- **Location:** CrocoDash/case.py `init_args_check` (no whitespace check); the paths are written unquoted to user_nl_mom `INPUTDIR` and, through visualCaseGen, to `OCN_DOMAIN_MESH`/`ICE_DOMAIN_MESH`/`WAV_DOMAIN_MESH`/`MASK_MESH`
- **Already fixed on main:** No
- **Related:** R2 (the CLI download script breaks on the same paths); first-pass lead from the hand checks (now confirmed and removed from *Unverified leads*)

**What's wrong.** Case() and configure_forcings accept an inputdir with a space (e.g. `~/My Cases/run1`, common on laptops) and write it unquoted everywhere. `nuopc.runconfig` then holds `mesh_ocn = /glade/.../ar/i/sp ace/ocn/ESMF_mesh_….nc`, and the run dies in driver/mediator initialisation. cesm.log shows only `ESMF_Finalize: Error closing trace stream` and an MPI_Abort, and the med, drv and ESMF logs don't name the path.

**Repro.** `audit_rC`, a keepexe clone of the working Derecho case `audit_rA`, with the same input files copied under `.../ar/i/sp ace/ocn` and INPUTDIR plus the four mesh paths pointed there (`audit_repros/extra/run_tests/clone_runs.sh`). `audit_rA` initialises and runs; `audit_rC` aborts as above.

**Root cause.** CIME's runconfig and the NUOPC attribute reader split values on whitespace.

**Smallest fix.** In `init_args_check`, refuse an inputdir (and caseroot) containing whitespace, with a message that says why.

</details>

## H11: A MARBL compset with GLORYS (the default product) fails in configure_forcings with "This product does not have marbl tracer var names", which doesn't say what to use instead

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** A MARBL compset with GLORYS (the default product) fails in configure_forcings with "This product does not have marbl tracer var names", which doesn't say what to use instead

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** misleading error (early, at configure time)
- **Evidence:** confirmed by repro
- **Confidence:** high
- **Location:** CrocoDash/raw_data_access/base.py:347-350 (`write_metadata(include_marbl_tracers=True)` on a product without `marbl_var_names`); reached from configure_forcings for any %MARBL-BIO compset
- **Already fixed on main:** No
- **Related:** none found

**What's wrong.** BGC boundary tracers need a conditions product with BGC fields: CESM_POP_OUTPUT, or reference_ocean as a placeholder. GLORYS, the default product, has none. So `CR1850MARBL_JRA` + GLORYS stops in configure_forcings with `ValueError: This product does not have marbl tracer var names and cannot be written out as such.` That message names neither the cause (BGC compset, physics-only product) nor the products that work.

**Repro.** `audit_repros/extra/marbl_glorys.py`: create a CR1850MARBL_JRA case, then call configure_forcings with GLORYS / get_glorys_data_from_rda.

**Smallest fix.** Check this in configure_forcings when BGC is active, and raise a message listing the products that define `marbl_var_names`.

</details>

## H12: CESM_MOM_OUTPUT reads MOM6 output from a Gregorian-calendar run 2 days early, so nested boundary data is shifted by 2 days, or comes back empty near the end of the record

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** CESM_MOM_OUTPUT reads MOM6 output from a Gregorian-calendar run 2 days early, so nested boundary data is shifted by 2 days, or comes back empty near the end of the record

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** wrong result (silent); crash when the shifted window falls off the end of the parent record
- **Evidence:** confirmed by repro on real MOM6 output from a CrocoDash case run on Derecho
- **Confidence:** high
- **Location:** CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:229 (`xr.open_mfdataset(files, combine="by_coords")` with default time decoding), then `convert_cftime_to_numeric` (:544) and the `sel` on :255. Same pattern in `read_single_variable_tseries_data`.
- **Already fixed on main:** No
- **Related:** C12 (NO_LEAP handling for this product); the unverified CARIB12 lead (its January mean decodes as 2000-01-14 12:00, two days before the true mid-month). Not in TRIAGE, QUEUE or the open issues.

**What's wrong.** MOM6 (FMS) writes history time as `days since 0001-01-01 00:00:00` with `calendar = "gregorian"`, but it means proleptic Gregorian. Because the reference date is before 1582, xarray follows CF: "gregorian" is the mixed Julian/Gregorian calendar. So every timestamp decodes 2 days early. The day-by-day selection in `get_mom6_output_data` then returns data from 2 days later than the dates asked for, with no warning. At the end of the parent record it returns nothing. The product exists to nest a child domain inside a parent MOM6 run, and CrocoDash's own GLORYS cases run CALENDAR=GREGORIAN, so a CrocoDash parent hits this. (A NO_LEAP parent does not.)

**Repro.** `audit_repros/extra/run_tests/mom_output_dates.py <hist dir>` on the history of `audit_rD`, a 3-day CrocoDash run made on Derecho for this audit:
- The file stores 737424.04 … 737426.96, which is 2020-01-01 01:00 → 2020-01-03 23:00 in proleptic Gregorian.
- xarray decodes it as 2019-12-30 01:00 → 2020-01-01 23:00.
- `get_mom6_output_data(["2020-01-02","2020-01-02"], …)` selects **0 records**, although the file covers that day.

**Root cause.** FMS labels a proleptic calendar "gregorian" with an epoch before 1582, and the reader trusts the label.

**Smallest fix.** Open with `decode_times=False`. When the calendar is `gregorian`/`standard` and the units' epoch is before 1582-10-15, decode with `calendar="proleptic_gregorian"`. Otherwise decode as given. Apply this in both CESM_MOM_OUTPUT readers.

</details>

## H13: ERA5 2D wave spectra are already "going to", but CrocoDash treats them as "coming from" and flips them 180°, so ERA5-forced WW3 boundaries send waves the wrong way

- **Target repo:** CROCODILE-CESM/CrocoDash
- **Title:** ERA5 2D wave spectra are already "going to", but CrocoDash treats them as "coming from" and flips them 180°, so ERA5-forced WW3 boundaries send waves the wrong way

<details><summary>Body</summary>

Found by hand after the CrocoDash 1.0.x audit (2026-11-06), against CrocoDash main b8991c89 and the copies it pins (regional-mom6 3ca8b9b, visualCaseGen 0eb6fd6, mom6_forge d74c851). Repro scripts are in the CROC monorepo under dev/crocodash_1_0_x/audit_repros/extra/.

- **Repo:** CrocoDash
- **Severity:** wrong result (silent)
- **Evidence:** confirmed by a live CDS download compared against an independent product. The full `process_forcings` run was stopped after 2 of its 4 CDS requests (about 10 minutes each); the 180° flip on the way to the WW3 files is from reading the code.
- **Confidence:** high
- **Location:** CrocoDash/raw_data_access/datasets/era5.py:314 (`direction_convention = DIRECTION_COMING_FROM`, which the module docstring itself calls "UNVERIFIED"); CrocoDash/forcing/ww3.py:169-172 (`to_direction_to` adds 180° for COMING_FROM), applied at ww3.py:407
- **Already fixed on main:** No. It's the same on main and on the 1.1 branch `drop-loose-access-args` (#348).
- **Related:** #348 (1.1 ERA5/GLOFAS fetch rework, which doesn't touch the convention). Not in TRIAGE or QUEUE.

**What's wrong.** ERA5's spectral directions (param 251.140) are the direction the waves travel *to*, the oceanographic convention, unlike ERA5's mean wave direction. CrocoDash declares them "coming from" and rotates every ERA5 spectrum by 180° before writing the WW3 boundary files. So with `ww3_obc_product_name="era5_wave_spectra"`, the boundary swell points the opposite way: waves that should enter the domain leave it, and vice versa.

**Repro.**

1. `audit_repros/extra/run_tests/era5_live.py` pulls one day (2019-06-05, 24 hourly fields) over 40–44°N, 60–56°W through `ERA5_WAVE_SPECTRA.get_era5_2d_spectra`. The download and decode work: 12 MB of GRIB, about 6 minutes in the CDS queue.
2. `era5_vs_ww3.py` compares it, at the same 144 point-times, with CESM-WW3-JRA. That product is "to" by construction (WW3 source) and was checked against the run's Stokes drift.
   - Hs agrees: median 1.85 vs 1.89 m, r = 0.94. So the log10 decode is right.
   - ERA5's *raw* mean direction is within **6°** (median) of WW3-JRA's "to" direction.
   - After CrocoDash's 180° flip it is **174°** off.

**Root cause.** The convention was assumed from documentation and never checked against data.

**Smallest fix.** Set `ERA5_WAVE_SPECTRA.direction_convention = DIRECTION_TO`, and remove the "UNVERIFIED" caveat from the module docstring. A regression test could compare an ERA5 pull's mean direction against WW3-JRA, or check it against the bulk `mwd` from `reanalysis-era5-single-levels`, which is "coming from" and so should differ by 180°.

</details>
