# CrocoDash 1.0.x audit (2026-11-06)

Report only. No code was changed outside the scratch worktree, nothing was committed or pushed, and no GitHub action was taken.

## Target

| Repo | Audited copy (in the worktree) | Pinned commit | That repo's main |
|---|---|---|---|
| CROCODILE-CESM/CrocoDash | worktree `regional_mom_workflows/CrocoDash-worktrees/audit` | **b8991c89566b84a3d4372e7999c8852978fbfc79** (main, 2026-11-02, #309) | same |
| CROCODILE-CESM/regional-mom6 | `CrocoDash/rm6` | 3ca8b9b | e349363 (+7: #330–#334, #336, COSIMA merge) |
| ESMCI/visualCaseGen | `CrocoDash/visualCaseGen` | 0eb6fd6 | same |
| NCAR/mom6_forge | `CrocoDash/visualCaseGen/external/mom6_forge` | d74c851 (0.9.3) | 83d7692 (+2: #126, #155) |

Every **Location** below is a path in that worktree. **Already fixed on main** was checked against each repo's main. No finding is fixed on any main, so none of them can be closed by a pin bump alone.

## Summary

- **61 confirmed findings:** 48 from the audit (31 in CrocoDash, 2 in regional-mom6, 12 in mom6_forge and 3 in visualCaseGen), plus 13 checked by hand afterwards (H1–H13: 9 in CrocoDash, 3 in mom6_forge, 1 in regional-mom6). H5, H10 and C9 were confirmed by real model runs on Derecho, and H13 and C15 against the live CDS/EWDS services. 47 were confirmed by repro. One (C15, GLOFAS) was confirmed from reading and then reproduced by a second check.
- **Most severe (silent wrong results):** C1 (CESM-POP currents are rotated by the POP grid angle), C2 (a resumed process_forcings keeps half-written files and writes zero/NaN boundaries), C3 (BGC river nutrients are off by 100x), C4 (body tides use M2 only, whatever constituents are asked for), M1/M2 (runoff maps are wrong for domains that cross 0° or the equator, and for rotated grids), and R1 (tidal boundaries are zero within 1/6° of 0° longitude). Found by hand afterwards: H13 (ERA5 wave spectra are flipped 180°, so boundary waves travel the wrong way) and H12 (nesting from a Gregorian MOM6 parent reads it 2 days early).
- **Blocks a whole domain class:** H3 (every domain south of 60°S with a JRA compset fails in process_forcings, because the GLOFAS runoff grid stops at 60°S), and H8 (chl refuses every grid except a plain lat-lon `Grid()`: polar, Albers, rotated, `from_center` and the NWA12 supergrid).
- **Data loss:** C5 (every configure_forcings call deletes the raw downloads of an override=True case), C6 (override=True deletes the whole `<CIME_OUTPUT_ROOT>/<case name>` folder), and C13.1 (duplicate/fork always run with override=True).
- **Changes to the triage list:**
  - regional-mom6 #15 is not fixed. R1 reproduces it, so keep #15 open rather than closing it as TRIAGE.md section B plans.
  - CrocoDash #344 ("OBC Tide Params are Changing!", no details) may be C4 or C-short-2. Ask the reporter.
  - CrocoDash #240 (machine detection) is related to C14.
- **Not filed:** 5 cross-area duplicates (merged into the findings above), 1 already known (#350), and 1 not reachable from CrocoDash. See *Not filed* near the end.

## Method

- **Known-bug baseline:** TRIAGE.md (read once it existed), the open issues and open PRs of the four repos as of the morning of 2026-11-06, QUEUE.md, and the memory notes. Verifiers also checked issues filed during the day (#353–#358).
- **Find:** six reviewers, one per area: CrocoDash creation/CLI/recipes, CrocoDash configure and process, raw data products, regional-mom6, mom6_forge and visualCaseGen. Each walked its user flows with tiny real cases in scratch, using `reference_ocean` and a 4°x4° grid on `~/work/installs/CESM_crocodash`. Case() and process_forcings work end to end in about 30 s. They found 55 candidates.
- **Verify:** one adversarial verifier per finding. Each re-read the code, checked whether users can reach it and whether it is already known, wrote its *own* smallest repro, re-rated the severity, and checked each repo's main. A second skeptic re-checked any crash or wrong-result finding that was confirmed only by reading (one: C15, reproduced).
- **Deviation:** a planned second "gap" reviewer per area did not run. The org's spend limit cut the first run short, and the gap pass was dropped on resume to save credits. *Not covered* near the end lists what each reviewer did not reach. Those lists are the obvious scope for a follow-up.
- **No case was built, submitted or run.** Findings about what CESM or MOM6 would do at run time (e.g. C9's relative mesh paths) are confirmed up to the files CrocoDash writes.

## Sources

- **Repro scripts:** `dev/crocodash_1_0_x/audit_repros/<area>/` for reviewers and `audit_repros/verify/<id>/` for verifiers. They source `audit_repros/env.sh`, whose `WT` points at the audit worktree. Case and input dirs lived in the session scratchpad and may be gone; rerun the scripts to recreate them.
- **Full verifier output** (every field, all 50): `dev/crocodash_1_0_x/audit_repros/verifier_results.json`.

## CrocoDash

CROCODILE-CESM/CrocoDash, main at b8991c89. 31 confirmed findings: the 15 most severe are written up in full below (two of them are groups that one PR can fix), and 7 misleading-error findings follow in short form.

### C1. CESM_POP_OUTPUT passes grid-relative UVEL/VVEL as east/north, so IC and OBC currents are rotated by the POP grid's ANGLE

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `raw_data-a1`)
- **Confidence:** high
- **Location:** CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:38 (u_var_name="UVEL", v_var_name="VVEL" at :40, u/v lat/lon = TLAT/TLONG at :44-47; merged raw file written unrotated at :453-456). Consumers rotate by the target angle only: CrocoDash/rm6/regional_mom6/segment.py:892 (OBC), CrocoDash/rm6/regional_mom6/regional_mom6.py:1102 (IC)
- **Already fixed on main:** No (target is main). No open CrocoDash PR touches it (#358 and #327 contain no rotation changes). Sibling fixes: PR #295 (CICE restoring) and rm6 PR #74 (target-side sign); rm6 origin/main e349363 has no source-angle handling either.
- **Related:** CrocoDash PR #295 (same class of bug, CICE restoring velocities); regional-mom6 PR #74 (sign of the IC/OBC rotation onto the target grid); CrocoDash #353 (POP boundary time crash, which currently masks the OBC half for windows > 7 days) and PR #358 (its IC half); 1.1 queue Q22 / #347 (cuts CESM output with Region.select and rewrites this reader, so the rotation must be kept there); CrocoDash #298 (mask_dataset with CESM POP, different bug)

**What's wrong.** POP's UVEL/VVEL are components along the POP grid's own axes. Both FOSI and LENS2 files give long_name "Velocity in grid-x direction", and each file includes ANGLE (radians, at U points). CESM_POP_OUTPUT hands them to regional-mom6 as u_var_name/v_var_name. regional-mom6 assumes these are earth-relative and rotates only by the target grid's angle_dx. The source ANGLE gets copied into the raw *_unprocessed.nc and ic_unprocessed.nc files, but nothing reads it. As a result, initial-condition and open-boundary velocities point the wrong way, rotated by the POP grid angle at that location. Nothing warns about it. A secondary problem: u/v lat/lon metadata point at TLAT/TLONG, so the pipeline detects an Arakawa A grid and regrids UVEL/VVEL as if they sat at T points. They actually sit at U points, the NE cell corner, which is half a cell away.

**Who hits it.** configure_forcings(product_name="CESM_POP_OUTPUT", function_name="get_cesm_single_variable_data") with the default CESM-HR FOSI path, or with LENS2 (dataset_path=/gdex/data/d651056/CESM2-LE/ocn/proc/tseries/month_1, member=...), then process_forcings, for any domain where the POP grid is not aligned with lat/lon. ANGLE values I read from one real UVEL file of each:
- FOSI-HR tx0.1v3: Gulf of Alaska (56.9N, 215E) -18.9 deg; Labrador Sea +13.4; Nordic Seas (70N, 2E) -14.4; North Sea -7.9; Gulf of Maine +6.5; up to 89 deg north of 60N.
- LENS2 gx1v7: Nordic Seas +37.4; North Sea +12.1; Gulf of Alaska -11.3; Labrador Sea -6.6; Gulf of Maine -3.5; Gulf of Mexico -1.3.
- The tropics and the Southern Hemisphere are 0 on both grids.
The IC is always affected. The OBC is affected for windows of 7 days or less (one GET chunk); longer windows currently crash first on the known #353 boundary half.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/raw_data-a1 && timeout 900 $PY -u va1_pop_rotation.py run2   (script: dev/crocodash_1_0_x/audit_repros/verify/raw_data-a1/va1_pop_rotation.py)

Key lines:
- Synthetic POP tseries on a source mesh rotated 30 deg near 201E/0N: TLONG = 201 + (i cosA - j sinA)*0.25, TLAT = (i sinA + j cosA)*0.25, ANGLE = 30 deg.
- True flow is due east at 50 cm/s, stored POP-style: UVEL = 50cos30 = 43.30, VVEL = -50sin30 = -25.00.
- Grid(lenx=2, leny=2, resolution=0.25, xstart=200, ystart=-1), flat Topo of 1000 m, VGrid.uniform(10, 1000).
- Case(..., caseroot=.../cases/audit_va1_pop, compset NYF).
- case.configure_forcings(date_range=["2000-03-01 00:00:00","2000-03-06 00:00:00"], product_name="CESM_POP_OUTPUT", function_name="get_cesm_single_variable_data", function_overrides={"dataset_path": src}).
- case.process_forcings(), then read init_vel.nc and ocn/forcing_obc_segment_00[1-4].nc.

ANGLE values: dev/crocodash_1_0_x/audit_repros/verify/raw_data-a1/angles.py run on one FOSI and one LENS2 UVEL file.

- Expected: The target is a plain lat-lon grid (angle 0) and the true flow is due east at 0.5 m/s, so the IC and every OBC segment should have u = 0.5000 m/s and v = 0.0000 m/s.
- Observed: "IC init_vel.nc u: mean 0.4330 m/s" / "IC init_vel.nc v: mean -0.2500 m/s" (init_vel_filled.nc is the same). OBC segments 001-004, valid points: u_segment = 0.4330, v_segment = -0.2500 (min = max). The flow is rotated 30 deg clockwise, by exactly the source ANGLE, and the speed is unchanged. The ANGLE variable is present but unused in ic_unprocessed.nc and in the south/north *_unprocessed raw files. Real-file headers: UVEL:long_name = "Velocity in grid-x direction", UVEL:coordinates = "ULONG ULAT z_t time", and ANGLE:long_name = "angle grid makes with latitude line", units radians, coordinates "ULONG ULAT", in both FOSI and LENS2.

**Root cause.** In CrocoDash's product layer, u_var_name/v_var_name are taken to be earth-relative (east/north) components. That is what regional-mom6 assumes when it rotates only by the target grid angle in Segment.regrid_velocity_tracers and setup_initial_condition. CESM_POP_OUTPUT points them at POP's grid-relative UVEL/VVEL. read_single_variable_tseries_data and subset_dataset then subset and merge the files without converting to east/north using the file's ANGLE. Separately, u/v lat/lon are mapped to TLAT/TLONG instead of ULAT/ULONG.

**Smallest fix.** In read_single_variable_tseries_data (cesm_ocean_output.py:453-456), for CESM_POP_OUTPUT (e.g. a rotate_angle_var="ANGLE" argument passed by get_cesm_single_variable_data), rotate the merged dataset before writing it, whenever UVEL, VVEL and ANGLE are all present:
u_e = UVEL*cos(ANGLE) - VVEL*sin(ANGLE)
v_n = UVEL*sin(ANGLE) + VVEL*cos(ANGLE)
ANGLE is in radians at U points. Raise if UVEL/VVEL are present without ANGLE rather than passing them through unrotated, as PR #295 does for CICE. Optionally point u_lat_coord/u_lon_coord/v_lat_coord/v_lon_coord at ULAT/ULONG so velocities are regridded from their real positions. This fix is independent of rm6 PR #74, which fixes the sign of the earth-to-target rotation; rotated target grids need both.

### C2. process_forcings resume keeps half-written files from a killed run and silently writes zero/NaN boundary and initial conditions

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `configure_process-a5`)
- **Confidence:** high
- **Location:** CrocoDash/forcing/utils.py:137-143 (fetch_raw_chunk skip; the magic-byte check is in is_valid_netcdf, utils.py:103-110), CrocoDash/forcing/obc.py:654-662 and :690 (_merge_boundary skip + in-place write), CrocoDash/forcing/mom6.py:295-303 and :335-344 (_all_written / _regrid_ic skips) and :278 (_fill_missing_and_write in-place write), CrocoDash/forcing/mom6.py:187-195 and :224 (BGC per-tracer files, same pattern)
- **Already fixed on main:** No (target is main). No open PR fixes it. #336 / Q10 (branch finished-steps, 9eeb7400) also leaves it open. Its clean() deletes a step's files only when that step already has a finished_steps.json entry. A step killed before finishing has no entry, so its partial files are kept even with --force.
- **Related:** #336 (Q10 finished-steps: related, does not fix it); #355 / TRIAGE A8 (copernicusmarine partial-download leftover, a different code path and fix)

**What's wrong.** The resume checks in the forcing pipeline treat 'the file exists and its first 4 bytes are a netCDF/HDF5 signature' as 'this step finished'. That covers fetch_raw_chunk (raw OBC chunks and ic_unprocessed.nc), _merge_boundary (ocn/forcing_obc_segment_NNN.nc), _regrid_ic via _all_written (init_*.nc and init_*_filled.nc) and the BGC per-tracer split files. All of these are written in place under their final names: by the product's access function (e.g. glorys.py:106, reference.py:202), at obc.py:690, by rm6's setup_initial_condition, at mom6.py:278 and at mom6.py:224. With netCDF4 the header and all metadata are on disk before the data. A write that is interrupted therefore leaves a file that passes the check and even opens cleanly, but every value reads back as the fill value (NaN). On the next process_forcings run it is skipped and used as if complete. A truncated raw chunk is regridded to a boundary of zeros (T=0, S=0, u=v=eta=0). A truncated merged OBC file or IC file is kept as all-NaN. In both cases process_forcings exits 0. The failure surfaces only when MOM6 runs, or the run silently uses wrong forcing. If the kill lands before the metadata is flushed, the rerun instead dies in REGRID with 'NetCDF: HDF error: <path>'. The REGRID step (obc.py:368-418) and BGC split step 3 already write to a scratch name and os.replace it, so they are not affected. BGC split step 2 (the per-tracer files) is affected; the finder said the BGC split was already safe, which holds only for step 3. The _all_written docstring assumes 'a run killed partway leaves only some of them', which is false for the file being written.

**Who hits it.** process_forcings / crocodash process is interrupted while it writes a raw chunk, a merged OBC file, an IC file or a BGC per-tracer file. Causes include a PBS walltime kill, the OOM killer, Ctrl-C or a kernel interrupt, or an exception mid-write such as a disk-quota error or a source read error during the lazy GLORYS RDA write. The user then reruns process_forcings to resume, as the docs advertise (3b_process_forcings.md: 'Resume a partially-completed run'; obc.py docstring: 'Re-running after a partial failure resumes from the last completed file'). The GLORYS RDA GET write (glorys.py:106) streams lazily from campaign storage and the merge write streams from open_mfdataset. These are long writes on big domains, so they are the likeliest places for a kill to land.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/configure_process-a5 && timeout 900 $PY -u setup_case.py && timeout 900 $PY -u kill_and_resume.py   (output in kill_and_resume.log, run_*.log in the same directory). setup_case.py creates a tiny case: 8x8 cells, 10 levels, NYF compset, reference_ocean / get_reference_ocean_data, 2020-01-01..05. proc.py runs CrocoDash.forcing.driver.run_workflow(config, ic=True, bc=True), the same call that `crocodash process` makes. Given one target path, it slows only that file's xarray to_netcdf: each dask block sleeps 0.3 s under the synchronous scheduler. kill_and_resume.py first does one clean run and keeps good copies of every file. For each target it deletes the target, starts proc.py in a new session, waits 3 s after 'SLOW WRITE STARTED', runs os.killpg(pid, SIGKILL) (no processes left in the group), then reruns proc.py unpatched in a fresh process. It then reads the file the rerun kept and compares it with the good copy.

- Expected: A file left by an interrupted write is never taken as finished. The rerun regenerates it, or at least refuses it with a clear error, and process_forcings does not exit 0 with NaN or zero forcing.
- Observed: A (raw chunk): "left on disk -> east_unprocessed.2020-01-01_2020-01-05.nc: 13783 bytes, magic=b'\x89HDF', is_valid_netcdf=True | good copy: 111789 bytes". The rerun logged "east_unprocessed.2020-01-01_2020-01-05.nc already exists. Skipping." and ended with "resume run exit 0 | returned normally: True". The kept raw file reads "temp(5, 10, 12, 5) nan=3000"; resulting ocn/forcing_obc_segment_004.nc (east): "temp_segment_004 non-fill values: min=0.0 max=0.0; good: 2.001..25.947", "salt_segment_004 non-fill values: min=0.0 max=0.0; good: 34.851..34.867" (u, v and eta also all zero). B (merged OBC): "forcing_obc_segment_001.nc: 29943 bytes, magic=b'\x89HDF', is_valid_netcdf=True | good copy: 116047 bytes". The rerun logged "Merged file forcing_obc_segment_001.nc already exists. Skipping." and exited 0; the kept file reads "u_segment_001(5, 10, 1, 17) nan=850 ... temp_segment_001 nan=850" (all NaN). C (IC): "init_tracers_filled.nc: 11837 bytes, magic=b'\x89HDF', is_valid_netcdf=True | good copy: 21912 bytes". The rerun logged "Initial condition filled files already exist. They will be skipped." and exited 0; the kept file reads "temp(10, 8, 8) nan=640; salt(10, 8, 8) nan=640" (all NaN).

**Root cause.** The skip checks are existence plus a magic-byte check, which says nothing about completeness. The outputs are written directly to their final names instead of to a temp name renamed into place when done. HDF5/netCDF4 puts the signature and metadata on disk first, so a partial file passes the check and even opens cleanly, reading back as fill values. Downstream NaN filling then turns a NaN raw chunk into a boundary of zeros.

**Smallest fix.** Write each of these outputs to a temp name in the same directory and os.replace it into place only after the write returns. REGRID (obc.py:418) and BGC step 3 (mom6.py:247-249) already do this. (1) fetch_raw_chunk: for in-process access functions (data_access_fn._type == "python"), pass output_filename=f"{name}.part", then os.replace(part, output_file) and remove any leftover .part first. Keep the final name for type="script" functions, whose download runs later. (2) _merge_boundary: to_netcdf to output_path + ".tmp", then os.replace. (3) _fill_missing_and_write: the same. (4) _regrid_ic: run setup_initial_condition with expt.mom_input_dir set to a temp subdirectory and move the three init_*.nc files into output_dir afterwards. (5) BGC split step 2: the same tmp + replace. The finder's optional fix, validating by opening the file, would NOT catch this: the killed files open fine and read as NaN.

### C3. BGC river nutrients: DON and SiO3 fluxes come out 100x too small, DOP and Fe 100x too large

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `configure_process-a1`)
- **Confidence:** high
- **Location:** CrocoDash/forcing/bgc.py:269-283 (units label also at CrocoDash/forcing/bgc.py:334)
- **Already fixed on main:** No (target is main). origin/main = b8991c89 still has the duplicated list at CrocoDash/forcing/bgc.py:269-279. Open PR #297 (BGC fixes) edits this function (time reference, READ_RIV_FLUXES) but not the conversion list or the units.
- **Related:** Open PR #297 (same function, does not fix this). TRIAGE A#5 / visualCaseGen #55 (multi-modifier MARBL long names; standard aliases avoid it). Closed issues #216 and #99 are about river nutrients but unrelated.

**What's wrong.** BGCRiverNutrientsConfigurator.process scales the river fluxes by 0.01 to convert nmol/cm^2/s to mmol/m^2/s. Its list of variables to convert names don_riv_flux and dsi_riv_flux twice and leaves out dop_riv_flux and dfe_riv_flux. As a result:
- DON and SiO3 are scaled twice and come out 100x too small.
- DOP and dissolved Fe are never converted and come out 100x too large.
- DIN, DIP, DIC, ALK and DOC are correct.

MOM6's MARBL_tracers.F90 reads all nine fluxes as mmol/m^2/s and applies them directly, so the river supply of these four tracers is silently wrong by two orders of magnitude. Nothing errors or warns. The file also labels the converted variables "mmol/cm^2/s", which is wrong. DOP and Fe get no units attribute at all, because the regridder drops attributes and the units loop only covers the same list.

**Who hits it.** Any MARBL case with DROF where configure_forcings gets global_river_nutrients_filepath, as the gallery configure_forcings.ipynb does with /glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/rof/river_nutrients/river_nutrients.GNEWS_GNM.glofas.20250916.64bit.nc. A standard alias such as CR1850MARBL_JRA works. The bug fires when process_forcings runs the bgcrivernutrients component. It needs no particular calendar or domain.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh && cd dev/crocodash_1_0_x/audit_repros/verify/configure_process-a1 && timeout 900 $PY -u riv_nut_units.py

What the script does (no mocks):
1. Writes a 4-degree global source with the GLADE file's layout: din/don/dip/dop/dsi/dfe/dic/alk/doc_riv_flux, each = 1.0 "nmol/cm^2/s" over 2 noleap times, plus LAT/LON/xc/yc/xv/yv/area.
2. Builds Grid(lenx=2, leny=2, resolution=0.5, xstart=300, ystart=30).
3. Saves real xesmf bilinear weights as the "runoff map" (ctx.config["runoff"]["outputs"]["ROF2OCN_LIQ_RMAPNAME"]).
4. Runs BGCRiverNutrientsConfigurator(..., calendar=NOLEAP).process(ctx) and prints each output variable.

riv_nut_units_fixed.py in the same directory reruns it with the corrected list monkeypatched in.

- Expected: Every *_riv_flux in the output file = 0.01 mmol/m^2/s (1 nmol/cm^2/s x 0.01), with units "mmol/m^2/s", matching CESM's own riv_nut.gnews_gnm.* files.
- Observed: din_riv_flux   values=[0.01]    units attr='mmol/cm^2/s'
don_riv_flux   values=[0.0001]  units attr='mmol/cm^2/s'
dip_riv_flux   values=[0.01]    units attr='mmol/cm^2/s'
dop_riv_flux   values=[1.]      units attr=None
dsi_riv_flux   values=[0.0001]  units attr='mmol/cm^2/s'
dfe_riv_flux   values=[1.]      units attr=None
dic_riv_flux   values=[0.01]    units attr='mmol/cm^2/s'
alk_riv_flux   values=[0.01]    units attr='mmol/cm^2/s'
doc_riv_flux   values=[0.01]    units attr='mmol/cm^2/s'

With the fixed list monkeypatched in, all nine are 0.01 with units 'mmol/m^2/s'.

**Root cause.** The list is mistyped: vars = ["din_riv_flux", "dip_riv_flux", "don_riv_flux", "don_riv_flux", "dsi_riv_flux", "dsi_riv_flux", "dic_riv_flux", "alk_riv_flux", "doc_riv_flux"]. It should hold the nine fluxes MOM6 reads, each once. The loop `global_river_nutrients[v] = global_river_nutrients[v] * 0.01` therefore runs twice on don and dsi and never on dop and dfe. The same list drives the units label at line 334, which also has the wrong value "mmol/cm^2/s".

**Smallest fix.** Set vars = ["din_riv_flux", "dip_riv_flux", "don_riv_flux", "dop_riv_flux", "dsi_riv_flux", "dfe_riv_flux", "dic_riv_flux", "alk_riv_flux", "doc_riv_flux"], so each is converted exactly once. Write units "mmol/m^2/s" at lines 283 and 334. Then extend the mocked test in tests/forcing/test_bgc.py:
- Add dop and dfe to its synthetic source.
- Have its fake regridder pass the input values through.
- Assert that output = 0.01 x input for all nine variables.
Open PR #297 does not touch this list.

### C4. Tides configurator applies interior (body) tidal forcing for M2 only, whatever tidal_constituents is

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `configure_process-a2`)
- **Confidence:** high
- **Location:** CrocoDash/forcing/tides.py:86 (set_output_param("TIDE_M2", "True") in configure); static param declared at CrocoDash/forcing/tides.py:36
- **Already fixed on main:** No (target is main). The audited worktree is main at b8991c89, and none of the open CrocoDash PRs (#351, #327, #326, #320, #307, #297, #295, #279) touches CrocoDash/forcing/tides.py.
- **Related:** Possibly CrocoDash #344 "OBC Tide Params are Changing!" (empty body; listed under TRIAGE.md "needs details"). The 1.1 queue item Q9 (forcing-param-specs) only fixes the tides comments, not this. regional-mom6 reference behaviour is at regional_mom6.py:1936-1937.

**What's wrong.** When tides are configured, TidesConfigurator writes TIDES = True, which turns on MOM6's interior astronomical tidal forcing, plus a fixed TIDE_M2 = True. It never writes TIDE_<c> for the constituents the user asked for. MOM6 applies body-tide forcing only to constituents whose TIDE_<c> is true, and each one defaults to false. The open boundaries get every requested constituent (OBC_TIDE_CONSTITUENTS), but the interior always gets M2 only. With ["M2","S2","K1","O1"], S2, K1 and O1 have no body forcing. With ["K1","O1"], the interior is forced at M2, a constituent the boundaries don't carry, and gets no K1/O1 body forcing. The case still builds and runs, so nothing warns the user. regional-mom6's own setup, which this configurator mirrors, sets TIDE_<c> = True for each requested constituent (CrocoDash/rm6/regional_mom6/regional_mom6.py:1936-1937).

**Who hits it.** Case.configure_forcings(...) with tpxo_elevation_filepath / tpxo_velocity_filepath and any tidal_constituents other than exactly ["M2"]. The same happens through the CLI/YAML path. The user docs use ["M2", "K1"] (docs/source/for_users/3a_configure_forcings.md:39) and ["M2", "S2"] (docs/source/for_users/cli.md:91).

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; D=dev/crocodash_1_0_x/audit_repros/verify/configure_process-a2; cd $D && timeout 900 $PY -u repro_tide_flags.py $D. The script builds a 4x4 deg, 0.5 deg grid with flat topo, 10 levels and the NYF compset (case audit_cp_a2_1). It then calls case.configure_forcings(date_range=["2020-01-01 00:00:00","2020-01-05 00:00:00"], product_name="reference_ocean", function_name="get_reference_ocean_data", tpxo_elevation_filepath=<empty dummy>, tpxo_velocity_filepath=<empty dummy>, tidal_constituents=consts) for consts = ["K1","O1"] and then ["M2","S2","K1","O1"], and after each call greps TIDES/TIDE_*/OBC_TIDE_* from caseroot/user_nl_mom. Configure only, no process_forcings and no TPXO data needed.

- Expected: user_nl_mom has TIDE_<c> = True for exactly the requested constituents: TIDE_K1 = True and TIDE_O1 = True for ["K1","O1"], with no TIDE_M2; TIDE_M2/S2/K1/O1 = True for ["M2","S2","K1","O1"]. This matches OBC_TIDE_CONSTITUENTS and what regional-mom6 writes.
- Observed: For tidal_constituents=['K1', 'O1']: "TIDES = True", "TIDE_M2 = True", "OBC_TIDE_N_CONSTITUENTS = 2", "OBC_TIDE_CONSTITUENTS = \"K1, O1\"", and no TIDE_K1 or TIDE_O1, so the interior is forced with ['M2'] against OBC ['K1', 'O1']. For ['M2', 'S2', 'K1', 'O1']: "TIDES = True", "TIDE_M2 = True", "OBC_TIDE_CONSTITUENTS = \"M2, S2, K1, O1\"", and no TIDE_S2/K1/O1, so the interior is forced with ['M2'] against OBC ['M2', 'S2', 'K1', 'O1']. MOM6 (CESM_crocodash components/mom/MOM6/src/parameterizations/lateral/MOM_tidal_forcing.F90:298-337) reads every TIDE_<c> with default=.false., so only M2 body forcing is applied.

**Root cause.** TIDE_M2 is a static UserNLConfigParam (tides.py:36) set to "True" in configure() (tides.py:86), left over from the M2-only demos (case.expt still defaults to ["M2"], case.py:772-774). Nothing derives TIDE_<c> from the tidal_constituents input, while OBC_TIDE_CONSTITUENTS and OBC_TIDE_N_CONSTITUENTS are derived from it.

**Smallest fix.** In TidesConfigurator, drop the static TIDE_M2 output param. In configure(), append one UserNLConfigParam(f"TIDE_{c.upper()}", comment="Enable tidal constituent") set to "True" for each entry of tidal_constituents, before super().configure(), the way ConditionsConfigurator appends its dynamic OBC_SEGMENT_* params (CrocoDash/forcing/mom6.py:620-692). Override deserialize to rebuild any TIDE_<c> keys found in data["outputs"], as ConditionsConfigurator.deserialize does (mom6.py:705-724). The accepted constituent set (rm6's TPXO map: M2,S2,N2,K2,K1,O1,P1,Q1,MM,MF) is exactly MOM6's TIDE_<c> set, so every accepted constituent maps to a valid MOM6 flag. At least one constituent is always written, so MOM6's "TIDES are defined, but no tidal constituents are used" FATAL cannot be hit.

### C5. configure_forcings deletes all of extract_forcings (raw downloads, regridded chunks) on every call for cases created with override=True

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `configure_process-a6`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:654-655
- **Already fixed on main:** No (target is main). No open PR fixes it. The unmerged 1.1 branch case-from-caseroot (Q4 / issue #329, commit 7fc0c524) removes these lines, but it has no open PR.
- **Related:** #294 (added stale_outputs and kept the old wipe); 1.1 Q4 / #329 (branch case-from-caseroot, 7fc0c524, drops the lines); #336 (skip finished forcing steps, a related resume and idempotency item)

**What's wrong.** When the Case was created with override=True, which the gallery tutorials use, every configure_forcings() call runs shutil.rmtree(inputdir/extract_forcings). This happens after stale_outputs() has already decided what to remove, so it runs even when the configuration is unchanged and nothing is stale. It removes raw_data (downloaded or fetched forcing, including GLORYS files the user downloaded by hand with the get_glorys_data.sh script made by get_glorys_data_script_for_cli), regridded_data with its ESMF weights, and any other staging folders under extract_forcings. The docstring says a rerun removes only "files process_forcings() made for a different configuration". The next process_forcings() fetches and regrids everything again. In the script workflow, the user has to run the download script again. MERGE and the IC still skip because ocn/ was not touched, so the final forcing files come out right. The damage is lost data and repeated download and regrid work, not wrong model inputs. Cases created with override=False keep everything, as documented.

**Who hits it.** Python or notebook flow: Case(..., override=True), configure_forcings(...), process_forcings(), then configure_forcings(...) again on the same Case object. The second call can use identical arguments (a notebook cell rerun) or a change that leaves the conditions alone, such as adding tides. Then call process_forcings(). The CLI `crocodash create --override` is not affected: it calls configure_forcings only once, and recreating the case wipes inputdir anyway.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/configure_process-a6 && timeout 900 $PY -u v_a6.py   (script: dev/crocodash_1_0_x/audit_repros/verify/configure_process-a6/v_a6.py; log: run1.log in that folder). Key lines: an 8x8, 10-level NYF Case(..., override=True); ARGS = dict(date_range=["2020-01-01 00:00:00","2020-01-03 00:00:00"], product_name="reference_ocean", function_name="get_reference_ocean_data"); case.configure_forcings(**ARGS); case.process_forcings(); write a sentinel file extract_forcings/raw_data/user_downloaded_by_script.nc to stand in for script-downloaded data; case.configure_forcings(**ARGS) (identical); list extract_forcings; case.process_forcings(); compare mtimes. Control on the same Case: case.override = False; case.configure_forcings(**ARGS); case.process_forcings().

- Expected: An identical second configure_forcings() call removes nothing. stale_outputs() returns [], so raw_data, regridded_data and any user-downloaded files stay. The next process_forcings() skips GET and REGRID, which is what happens for override=False cases.
- Observed: After configure #1 and process #1, extract_forcings holds 14 files: config.json, raw_data/{east,north,south,west}_unprocessed.2020-01-01_2020-01-03.nc, raw_data/ic_unprocessed.nc, regridded_data/forcing_obc_segment_00{1-4}_2020-01-01_2020-01-03.nc and weights/bilinear_tracer_weights_segment_00{1-4}.nc. After an identical configure #2 (case.override = True), the output is "--- after identical configure #2 (override=True): 17 files under extract_forcings/ + ocn/ / extract_forcings/config.json", so only config.json is left, and "sentinel survived: False". process #2 then shows "REWRITTEN by process #2: [... raw_data/*_unprocessed..., raw_data/ic_unprocessed.nc, regridded_data/forcing_obc_segment_00N_..., weights/...]" and "UNCHANGED (skipped) by process #2: ['ocn/forcing_obc_segment_001.nc', ..., 'ocn/init_eta.nc', ...]". In the control on the same Case with case.override=False, the identical configure #3 keeps all 14 files plus the sentinel ("sentinel survived: True"), and process #3 rewrites only ['ocn/vcoord.nc'].

**Root cause.** Before #294 (1ac8395a), configure_forcings began with `if self.override is True: rmtree(extract_forcings)`. #294 added stale_outputs(), which removes exactly the files made for another configuration, but kept the old override wipe inside the new try block (case.py:654-655). The flag passed at creation, which means "replace the existing caseroot/inputdir", is therefore applied again on every configure call for the life of the Case object. The wipe is not needed even on the first call, because Case.__init__ already removes inputdir when override=True (case.py:210-212).

**Smallest fix.** Delete the two lines `if self.override is True and self.extract_forcings_path.exists(): shutil.rmtree(self.extract_forcings_path)` at CrocoDash/case.py:654-655. Case(override=True) already wipes inputdir at creation (case.py:210-212), and stale_outputs() handles a changed configuration. The 1.1 commit 7fc0c524 (branch case-from-caseroot) makes exactly this deletion.

### C6. Case(override=True) deletes the whole `<CIME_OUTPUT_ROOT>`/`<case name>` directory, not just the old case's bld/ and run/ (a case named 'archive' wipes every case's short-term archive)

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `vcg-a2`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:208 (case_dirs entry Path(self.cime.cime_output_root) / self.caseroot.name; removed at case.py:210-212 via _remove_previous, case.py:34-38)
- **Already fixed on main:** No (target is main; the worktree HEAD b8991c89 equals origin/main, and no open CrocoDash PR touches this code; #326 is unrelated)
- **Related:** none (code dates from the first Case class, 928a3ebf; last reworked in 29a35610 'delete the previous case first again')

**What's wrong.** When override=True, Case.__init__ builds case_dirs = [inputdir, caseroot, Path(cime.cime_output_root)/caseroot.name] and calls shutil.rmtree on each one that exists. It never checks that the third directory holds only the old case's build and run dirs. On Derecho and Casper, CIME_OUTPUT_ROOT is $SCRATCH (/glade/derecho/scratch/$USER). That same directory holds archive/ (DOUT_S_ROOT=$CIME_OUTPUT_ROOT/archive/$CASE, so every case's short-term archive), tmp/, croc_input/ and any project folders the user keeps there. If the case's basename matches one of those, the whole shared tree is deleted. Any extra content under <root>/<name> is deleted too, even when it is not part of the old case. Neither the override docstring ('override existing caseroot and inputdir directories') nor docs/source/for_users/2_case_setup.md mentions that this third directory is deleted.

**Who hits it.** Case(..., caseroot='<anything>/archive' (or 'tmp', 'croc_input', or a name matching a project folder the user keeps in $SCRATCH), override=True), or `crocodash create --override` / MCP create_case with such a case name. A typical case: re-running a throwaway case called 'tmp' or 'archive', or naming a case 'panama' while keeping unrelated material in $SCRATCH/panama.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a2 && timeout 900 $PY -u repro.py   (script: dev/crocodash_1_0_x/audit_repros/verify/vcg-a2/repro.py). Key lines: D = Path('/glade/derecho/scratch/manishrv')/'audit_vvcga2_1'. Create D/bld/old_build.o, D/run/old_run.nc, D/othercase/hist/othercase.mom6.h.0001.nc and D/keep.txt. Then Case(caseroot=S/'cases'/NAME, inputdir=S/'input'/NAME, compset='1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV', 4x4 deg 0.5-deg grid, flat topo, 5-level vgrid, atm_grid_name='T62', machine='derecho', override=True). Finally check whether othercase/... and keep.txt still exist.

- Expected: Override should remove only what would make create_newcase abort, which is the old case's EXEROOT and RUNDIR (<root>/<name>/bld and <root>/<name>/run), along with caseroot and inputdir. Anything else under <root>/<name> should survive, or override should refuse with a clear error. This matches CIME's own --handle-preexisting-dirs r, which runs shutil.rmtree only on EXEROOT and RUNDIR (cime/CIME/case/case.py:1572-1591).
- Observed: BEFORE: ['bld', 'bld/old_build.o', 'keep.txt', 'othercase', 'othercase/hist', 'othercase/hist/othercase.mom6.h.0001.nc', 'run', 'run/old_run.nc']
Removing previous case files: /glade/derecho/scratch/manishrv/audit_vvcga2_1
cime_output_root = /glade/derecho/scratch/manishrv
AFTER:  ['bld', 'bld/CASEROOT', 'bld/atm', ... 'run', 'run/CASEROOT']
  othercase/hist/othercase.mom6.h.0001.nc: DELETED
  keep.txt: DELETED

**Root cause.** The override cleanup assumes <CIME_OUTPUT_ROOT>/<CASE> belongs only to the case being replaced, and deletes it whole. visualCaseGen's CaseCreator runs create_newcase with --handle-preexisting-dirs a (case_creator.py:524). CIME then aborts only if EXEROOT or RUNDIR exists, and those are <root>/<CASE>/bld and <root>/<CASE>/run. CrocoDash pre-deletes their parent directory instead of those two directories. Its contents are unknown: on HPC machines that parent is a user-shared scratch root, which can hold any directory, including archive/ (DOUT_S_ROOT's parent).

**Smallest fix.** In case.py:205-209, replace the third entry with the two directories CIME actually checks: root/name/'bld' and root/name/'run'. A more accurate option is to read EXEROOT and RUNDIR from the old caseroot's env_build.xml and env_run.xml before deleting the caseroot, when it exists. After removing them, call rmdir on <root>/<name> only if it is empty. Use the same list in _remove_failed_attempt. Alternatively, have visualCaseGen pass --handle-preexisting-dirs r when override is set and drop the CrocoDash-side deletion of the output-root directory. Either way, the override docstring should state what gets deleted.

### C7. Case() accepts MOM6 compsets without %REGIONAL, and its docstring suggests them, so regional cases silently get MOM6_DOMAIN_TYPE=GLOBAL and lose the regional MOM_input defaults

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `vcg-a3`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:318-320 (init_args_check only asserts "MOM6" in compset_lname); CrocoDash/case.py:98-99 (docstring examples "G_JRA" and "1850_DATM%JRA_SLND_SICE_MOM6_SROF_SGLC_SWAV_SESP")
- **Already fixed on main:** No (target is main). No open CrocoDash or visualCaseGen PR touches the compset check or the docstring.
- **Related:** CrocoDash #248 ("MOM Runs (Gustavo G Compsets)": empty body, filed by TRIAGE as a feature/tracking item, not this bug). visualCaseGen #55 / CrocoDash PR #279 (custom long names with MOM6%REGIONAL%MARBL-BIO break the solver; if REGIONAL becomes mandatory, custom regional MARBL long names depend on that fix, though the CR1850MARBL_* aliases work). No 1.1 queue item.

**What's wrong.** The compset check in init_args_check only asserts that "MOM6" appears in the long name. It never checks for the REGIONAL modifier, which is the only thing that sets MOM6_DOMAIN_TYPE=REGIONAL (components/mom/cime_config/config_component.xml: `<value compset="_MOM6%[^_]*REGIONAL">REGIONAL</value>`, default GLOBAL). Both compset examples in the Case docstring lack %REGIONAL, and so do CrocoDash's own test fixture default and the embedded gallery's mom6_cice_antarctica notebook. A regional case built this way gets MOM6_DOMAIN_TYPE=GLOBAL. Every MOM_input.yaml default keyed on REGIONAL is lost unless CrocoDash or visualCaseGen writes that parameter explicitly, and 63 are not written. Examples:
- USE_KPP is unset, and ENERGETICS_SFC_PBL is unset too, so neither KPP nor ePBL is turned on.
- MAXTRUNC is 0 instead of 100000, so the run stops at the first velocity truncation.
- KD is 2e-5 instead of 1e-6, and KV is 1e-4 instead of 1e-6.
- DO_GEOTHERMAL is False instead of True.
- DTBT, DIABATIC_FIRST, ENERGYSAVEDAYS, OBC_RAMP_TIMESCALE and PARALLEL_RESTARTFILES also lose their regional values.

Nothing warns. Correction to the original finding: the OBC vorticity/strain/biharmonic/reservoir settings and DEPRESS_INITIAL_SURFACE are NOT lost, because CrocoDash's MOM6 configurator writes them. REENTRANT_X, TRIPOLAR_N, COORD_CONFIG and REGRIDDING_COORDINATE_MODE are not lost either, because visualCaseGen's case_creator writes them.

**Who hits it.** The user passes any MOM6 compset alias or long name without %REGIONAL. Examples: the docstring's G_JRA, or "1850_DATM%JRA_SLND_SICE_MOM6_SROF_SGLC_SWAV_SESP", or the long name used in gallery/crocodash/use_cases/mom6_cice_antarctica.ipynb ("1850_DATM%JRA_SLND_CICE_MOM6_SROF_SGLC_SWAV"). This applies whether the case is made through the Python API or a CLI/YAML config, since both go through Case().

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a3 && timeout 900 $PY -u repro.py

Script: dev/crocodash_1_0_x/audit_repros/verify/vcg-a3/repro.py. It sets up an 8x8 flat grid with 5 levels and calls `Case(compset="1850_DATM%JRA_SLND_SICE_MOM6_SROF_SGLC_SWAV_SESP", atm_grid_name="TL319", machine="derecho", override=True)`, which is the docstring example verbatim. It then runs `case.configure_forcings(..., product_name="reference_ocean", function_name="get_reference_ocean_data")`. Finally it reads MOM6_DOMAIN_TYPE from env_*.xml and compares the REGIONAL-keyed entries in components/mom/param_templates/MOM_input.yaml against user_nl_mom.

- Expected: Case() should refuse a MOM6 compset without %REGIONAL, or at least warn, and point to CR_JRA, GR_JRA or CWR_JRA (or a %REGIONAL long name). The docstring should give a regional compset as its example.
- Observed: From the repro run:
"configure_forcings OK"
"warnings mentioning REGIONAL/compset/domain: []"
"COMPSET = 1850_DATM%JRA_SLND_SICE_MOM6_SROF_SGLC_SWAV_SESP"
"MOM6_DOMAIN_TYPE = GLOBAL"
"63 REGIONAL-keyed params not overridden in user_nl_mom", including:
"USE_KPP: REGIONAL=True GLOBAL='<MOM6 default>'"
"MAXTRUNC: REGIONAL=100000 GLOBAL=0"
"DO_GEOTHERMAL: REGIONAL=True GLOBAL=False"
"KD: REGIONAL=1e-06 GLOBAL=2e-05"
"KV: REGIONAL=1e-06 GLOBAL=0.0001"
"DTBT: REGIONAL=-0.9 GLOBAL=-0.95"
"ENERGETICS_SFC_PBL in user_nl_mom: False | USE_KPP in user_nl_mom: False"

**Root cause.** init_args_check (case.py:318-320) validates the ocean model (MOM6) but not the REGIONAL option. In the crocodash CESM branch that option is the only switch for MOM_interface's regional parameter set: MOM6_DOMAIN_TYPE defaults to GLOBAL and becomes REGIONAL only for compsets matching "_MOM6%[^_]*REGIONAL". The docstring examples (case.py:98-99) predate the REGIONAL compsets. The test fixture default (tests/fixtures/objects.py:76) and tests/test_configure_forcings_rerun.py:15 also use non-REGIONAL long names, so the tests never notice.

**Smallest fix.** 1. In init_args_check, add `if not re.search(r"_MOM6%[^_]*REGIONAL", compset_lname): raise ValueError(...)`. The message should say that %REGIONAL sets MOM6_DOMAIN_TYPE=REGIONAL and name the CR_/GR_/CWR_/GWR_ aliases. If an escape hatch for deliberately global-physics setups is wanted, issue a warnings.warn instead of raising.
2. Change the docstring examples to "CR_JRA" and "1850_DATM%JRA_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV".
3. Update the non-REGIONAL compsets in tests/fixtures/objects.py:76 and tests/test_configure_forcings_rerun.py:15. The gallery antarctica notebook would also need %REGIONAL (a gallery change, tracked separately).

### C8. configure_forcings (and crocodash create YAML) silently ignores misspelled forcing keys: tides dropped, boundaries fall back to all four

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `creation_cli-a9`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:613 (kwargs merged into inputs unchecked; signature at case.py:489-497); CrocoDash/forcing/base.py:259-262 (instantiate_configurator drops non-ctor keys) and base.py:289-292 (optional configurator skipped at INFO); CrocoDash/recipe.py:44-82 (validate_config_structure has no unknown-key check) and recipe.py:167
- **Already fixed on main:** No (target is main). Nothing open fixes it. The 1.1 queue item Q9 (#330, branch forcing-param-specs, Sprint 4) only adds a logged warning for unknown kwargs, not an error, and 1.0.x users still hit the silent drop on main.
- **Related:** #330 (Q9 forcing-param-specs: 'unknown kwargs log a warning', which also covers a partially given optional configurator); QUEUE.md merge hazard 'Q9 vs Q11' (the warning must survive Q11's forcing_inputs() rewrite); #341 (Q14 forcing walkthrough, same configure_forcings input surface). No TRIAGE.md item.

**What's wrong.** Any key passed to Case.configure_forcings() that is not one of its named parameters goes into **kwargs and is merged into the configurator inputs without a check. Keys that match no configurator constructor are dropped. So a misspelled optional key silently changes what the case gets. With 'tidal_constituent' (instead of tidal_constituents), the tides configurator is skipped and no TIDES/OBC_TIDE_* lines are written. With 'boundary' (instead of boundaries), the default ['south','north','west','east'] is used and OBC_NUMBER_OF_SEGMENTS = 4. Case creation and configuration finish with exit code 0. The only trace is one INFO line, '[SKIP] tides missing args: ['tidal_constituents']', among about ten similar [SKIP] lines. The YAML pre-flight validate_config_structure only checks the correctly spelled 'boundaries' and 'tidal_constituents', so it does not catch this either.

**Who hits it.** `crocodash create --config case.yaml` (with or without --configure-only), or case.configure_forcings(...) from Python, with a misspelled optional forcing key. Examples: tidal_constituent, boundary, chl_processed_file (instead of chl_processed_filepath), fucntion_overrides.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; D=dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a9; cd $D && timeout 900 $PY -u repro.py $D   (log: $D/repro.log). The forcings section of $D/case.yaml: date_range [2020-01-01, 2020-01-03], product_name reference_ocean, function_name get_reference_ocean_data, tpxo_elevation_filepath / tpxo_velocity_filepath (dummy paths), `tidal_constituent: [M2, S2]`, `boundary: [north]`. The compset is 1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV on a 4x4 deg, 0.5 deg grid. repro.py runs `config = load_config(case.yaml); case = create_case_from_yaml(config, override=True, configure_only=True)`, which is exactly cli._create. It then reads extract_forcings/config.json and user_nl_mom. As a control it calls case.configure_forcings(**fc) again with the keys renamed to tidal_constituents and boundaries.

- Expected: configure_forcings / load_config raises an error that names the unknown keys ('tidal_constituent', 'boundary') and the valid choices, before any case is configured.
- Observed: rc=0. Typo run: "load_config OK; forcings keys: ['boundary', 'date_range', 'function_name', 'product_name', 'tidal_constituent', ...]", "INFO:CrocoDash.forcing.base:[SKIP] tides missing args: ['tidal_constituents']", "[typo] config.json entries: ['schema_version', 'streamyears', 'conditions']", "[typo] boundaries used: ['south', 'north', 'west', 'east']", "[typo] user_nl_mom tide lines: []", "[typo] user_nl_mom ['OBC_NUMBER_OF_SEGMENTS = 4']". Control with correct spelling: "[OPTIONAL] Activating tides", "[correct] config.json entries: [..., 'conditions', 'tides']", "[correct] boundaries used: ['north']", "[correct] user_nl_mom tide lines: ['TIDES = True', 'OBC_TIDE_CONSTITUENTS = \"M2, S2\"']", "OBC_NUMBER_OF_SEGMENTS = 1".

**Root cause.** Unknown keys are never checked against anything. configure_forcings takes **kwargs and does `inputs = kwargs | {...}` (case.py:613). ForcingConfigRegistry.instantiate_configurator builds each configurator from `{arg: inputs[arg] for arg in ctor_args if arg in inputs}` (base.py:259-262), so keys that match no constructor are dropped. find_active_configurators then treats an optional configurator with a missing required arg as not requested and only INFO-logs '[SKIP] ... missing args' (base.py:289-292). A misspelled named parameter such as 'boundary' is likewise swallowed, while 'boundaries' silently keeps its default. recipe.validate_config_structure (recipe.py:44-82) checks the presence of correctly spelled keys only and has no allow-list.

**Smallest fix.** At the top of Case.configure_forcings, compute the allowed set: the union of ForcingConfigRegistry.get_ctor_signature(cls)[0] over registered_types, minus case_* args and the keys configure_forcings sets itself. Raise ValueError naming any key in kwargs outside that set, e.g. "Unknown configure_forcings argument(s) ['boundary', 'tidal_constituent']; did you mean ...". Do this before any user_nl or xml writes. Because recipe.py:167 passes the YAML forcings section straight through, this one check covers both the CLI/YAML path and the Python path. Optionally, a partial set for an optional configurator (some but not all of its required args given, e.g. tidal_constituents without the TPXO paths from Python) should also raise instead of logging [SKIP] at INFO.

### C9. Case() with a relative inputdir writes cwd-relative paths into user_nl_mom INPUTDIR, the OCN/MASK mesh xml vars and the case state

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `creation_cli-a2`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:171 (also :170 for caseroot); paths reach the case through CrocoDash/case.py:903 (CUSTOM_GRID_PATH) and CrocoDash/case.py:1078-1083 (_write_state); they are read back at CrocoDash/forcing/driver.py:54-63 and CrocoDash/cli.py:46-48
- **Already fixed on main:** No (target is main). No open CrocoDash PR adds resolve()/expanduser() for these paths: I checked the diffs of #326, #327 and #351. No 1.1 queue item covers it.
- **Related:** - Lead finding (creation_cli): Case() fails when the parent of inputdir or caseroot doesn't exist yet. Same function; the fix should go in the same place.
- CrocoDash #286 / TRIAGE A4 (refuse inputdir == caseroot in init_args_check): that comparison also needs resolved paths to be reliable.
- 1.1 Q4 case-from-caseroot reads the same state paths.
- No other match in the issue, PR or queue lists.

**What's wrong.** Case(inputdir='rel/x') succeeds, but the path is stored as Path(inputdir) and never resolved. Everything downstream gets the cwd-relative string:
- visualCaseGen writes `INPUTDIR = rel/x/ocn` into user_nl_mom (case_creator.py:735).
- It sets OCN_DOMAIN_MESH and MASK_MESH in env_run.xml to `rel/x/ocn/ESMF_mesh_*.nc` (case_creator.py:950, 958).
- _crocodash_state.json stores inputdir, supergrid_path, topo_path and vgrid_path as relative paths.

MOM6 and CMEPS open these paths from RUNDIR, where they don't exist. The forcing driver rebuilds every path from the state file, so `crocodash process` only works when run from the original cwd. It fails with misleading messages when run with --caseroot from elsewhere (for example a PBS job that starts in $HOME), and when run from inside extract_forcings/, which is the CLI's own suggested usage.

**Who hits it.** Pass a relative inputdir to Case(), from a notebook or script (for example inputdir='input/mycase') or as case.inputdir in a YAML for `crocodash create`. Then run the model, or run `crocodash process` / the forcing driver from any other directory.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a2 && timeout 900 $PY -u rel_inputdir.py   (log: run1.log)

Key lines of the script:
- os.chdir(V/'wd'), with wd/rel already created.
- Case(cesmroot=$CESMROOT, caseroot=V/'cases/audit_vca2_1' (absolute), inputdir='rel/audit_vca2_1', compset='1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV', 4x4 deg grid at 0.5 deg, flat topo, 10 levels, atm_grid_name='T62', machine='derecho', override=True).
- Print the state json, the user_nl_mom INPUTDIR line and the env_run.xml OCN_DOMAIN_MESH/MASK_MESH values.
- configure_forcings(date_range=['2020-01-01 00:00:00','2020-01-03 00:00:00'], product_name='reference_ocean', function_name='get_reference_ocean_data').
- Run `crocodash process --caseroot <abs caseroot> --ic` with cwd=V/'elsewhere'.
- Run `crocodash process --ic` with cwd=<inputdir>/extract_forcings.

The fix check is rel_inputdir_fixed.py (log: run2.log). It is the same script with Case.__init__ monkeypatched to Path(x).expanduser().resolve() its cesmroot, caseroot and inputdir.

- Expected: Case() resolves inputdir (and caseroot and cesmroot) to absolute paths. user_nl_mom INPUTDIR, OCN_DOMAIN_MESH/MASK_MESH and the state file then hold absolute paths, and `crocodash process` works from any cwd. With the resolve() monkeypatch in run2.log, all of these values are absolute, both CLI runs exit with rc=0, and ocn/init_*.nc is written.
- Observed: From run1.log:
- `CASE CREATED; case.inputdir = 'rel/audit_vca2_1'`
- `STATE inputdir = 'rel/audit_vca2_1'`
- `STATE vgrid_path = 'rel/audit_vca2_1/ocn/ocean_vgrid_vca2_e256ae.nc'` (supergrid_path and topo_path are relative the same way)
- `user_nl_mom: INPUTDIR = rel/audit_vca2_1/ocn`
- `env_run.xml: OCN_DOMAIN_MESH = 'rel/audit_vca2_1/ocn/ESMF_mesh_vca2_e256ae.nc'`
- `env_run.xml: MASK_MESH = 'rel/audit_vca2_1/ocn/ESMF_mesh_vca2_e256ae.nc'`
- `INPUTDIR resolved against RUNDIR exists: False /glade/derecho/scratch/manishrv/audit_vca2_1/run/rel/audit_vca2_1/ocn`
- `crocodash process --caseroot <abs> --ic` from another cwd exits rc=1 with `Forcing configuration not found at rel/audit_vca2_1/extract_forcings/config.json` / `Run case.configure_forcings() before calling 'crocodash process'.` configure_forcings had already run and config.json exists.
- `crocodash process --ic` from inside extract_forcings/ exits rc=1 with `FileNotFoundError: Vgrid file must exist if run_initial_condition is set to true` (mom6.py:854). The vgrid file exists; the state's relative vgrid_path is resolved against the wrong cwd.

**Root cause.** Case.__init__ stores `self.inputdir = Path(inputdir)` and `self.caseroot = Path(caseroot)` (case.py:170-171) without expanduser() or resolve(), and init_args_check only tests exists(). The relative inputdir then reaches the case in two ways:
- _configure_custom_grid passes it unchanged as CUSTOM_GRID_PATH (case.py:903). visualCaseGen's CaseCreator uses that to write user_nl_mom INPUTDIR and the {OCN,ICE}_DOMAIN_MESH/MASK_MESH xmlchanges. The GUI file chooser always gives absolute paths, so visualCaseGen assumes one.
- _write_state stores it, and the grid file paths built from it, in _crocodash_state.json (case.py:1078-1083).

The forcing driver (_load/_build_context, driver.py:54-63) and the CLI (cli.py:46-48) rebuild inputdir, the grid paths and output_path from that state file. So everything resolves against whatever the process cwd is at the time.

**Smallest fix.** In Case.__init__, normalize the three paths after the _init_args capture (case.py:133) and before init_args_check (case.py:150):

  cesmroot = Path(cesmroot).expanduser().resolve(); caseroot = Path(caseroot).expanduser().resolve(); inputdir = Path(inputdir).expanduser().resolve()

case.py:169-171 then store absolute paths, and CUSTOM_GRID_PATH, user_nl_mom, the mesh xml vars, the state file and config.json all follow. A monkeypatch with exactly this change is verified to fix every symptom above. The same line also handles '~' paths and a relative caseroot. Optionally, case_state.read could resolve stored paths against caseroot for cases created before the fix.

**Run-time check (added by hand, 2026-11-06 late).** A keepexe clone of a working Derecho case (`audit_rE`) had its INPUTDIR and its OCN/ICE/WAV/MASK mesh paths set to the relative form this finding produces (`i/rA/ocn/...`). `case.submit` never reached the queue. CIME's input-data check resolved the relative mesh paths against DIN_LOC_ROOT, tried to download `inputdata/i/rA/ocn/ESMF_mesh_rA_*.nc` from every inputdata server (16 × 404), and stopped with `ERROR: Could not find all inputdata on any server`. That message doesn't mention the relative path. Along the way it **created empty directories in the shared CESM inputdata tree**: `/glade/campaign/cesm/cesmdata/inputdata/i/rA/ocn`, owned by the submitting user. So on GLADE, any user with write access to inputdata who hits C9 leaves junk directories there.

### C10. Case() fails with "Path `<dir>` doesn't exist" when the parent of caseroot or inputdir is missing, so CrocoDash's own parent mkdirs never run

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `creation_cli-a1`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:197 (the _configure_case call, which runs before the folders exist); CrocoDash/case.py:903 and CrocoDash/case.py:1060 (the values that reach the widgets); dead code at CrocoDash/case.py:383 (parents=True) and CrocoDash/case.py:476-477; raised at CrocoDash/visualCaseGen/external/ipyfilechooser/ipyfilechooser/filechooser.py:400
- **Already fixed on main:** No (target is main, b8991c89). No open CrocoDash PR fixes it. The visualCaseGen pin 0eb6fd6 is the same as ESMCI main, and its check is correct for the GUI, so it needs no change.
- **Related:** Same area as CrocoDash #286 (inputdir == caseroot gives an unclear error, TRIAGE item 4); it is a different bug, but both are path checks in init_args_check that could be fixed together. vCG #21 (confusing case-creation errors) is related only loosely. This is the creation_cli lead finding; no TRIAGE.md, QUEUE.md or open issue or PR covers it.

**What's wrong.** Case() raises "RuntimeError: Case configuration failed: Path <parent> doesn't exist" whenever the parent folder of inputdir or caseroot does not exist yet. No case is created. CrocoDash's own code is meant to create those parents: inputdir.mkdir(parents=True) at case.py:383 and caseroot.parent.mkdir at case.py:476-477. Neither line ever runs for a missing parent, because the check fails earlier. The same check also gives a misleading error in two more cases. A bare relative caseroot or inputdir ('my_case' or './my_case') gives "Path  doesn't exist" with an empty path. A '~/...' path, which CrocoDash never expands, gives "Path ~ doesn't exist". The workaround is to create the parent folder yourself, or to pass an absolute path, before calling Case().

**Who hits it.** Any new case whose folder's parent does not exist yet, or whose caseroot or inputdir is a bare relative name or a '~' path. All of these routes pass the user's paths straight to Case(): Case(...) in Python, `crocodash create` with a YAML config (recipe.create_case_from_yaml; nothing in cli.py or recipe.py creates folders), `crocodash duplicate --case/--inputdir`, and `crocodash fork --caseroot/--inputdir`. One example is the gallery starter_case.yaml (`inputdir: <inputdir>/my_case`) pointed at a scratch subfolder that does not exist yet. The internal temporary cases (identify_non_standard_case_info) are not affected, because they live in an existing tempdir.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a1 && timeout 900 $PY -u v_parent.py fail   (log fail.log; `v_parent.py fix` monkeypatches the fix, log fix.log). The script builds Grid(lenx=2, leny=2, resolution=0.5), a flat Topo and a 5-level VGrid, then calls Case(cesmroot=$CESMROOT, compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV", atm_grid_name="T62", machine="derecho", project="ncgd0011") with: (A) caseroot=<D>/cases/audit_cca1_a (parent exists) and inputdir=<D>/newin/sub/audit_cca1_a (parent missing); (B) caseroot=<D>/newcase/sub/audit_cca1_b (parent missing) and inputdir=<D>/input/audit_cca1_b; (C) caseroot="audit_cca1_c" (relative, cwd=<D>); (E) inputdir="~/audit_cca1_e_never_created".

- Expected: CrocoDash creates the missing parent folders, as case.py:383 and case.py:476-477 intend, and creates the case. Relative paths are resolved against the current folder and '~' is expanded.
- Observed: A: "RuntimeError: Case configuration failed: Path .../creation_cli-a1/newin/sub doesn't exist", raised at .../ipyfilechooser/filechooser.py:400 in _check_selection. B: "RuntimeError: Case configuration failed: Path .../creation_cli-a1/newcase/sub doesn't exist", same location. C: "RuntimeError: Case configuration failed: Path  doesn't exist" (empty path). E: "RuntimeError: Case configuration failed: Path ~ doesn't exist". After each failure neither the caseroot nor the inputdir exists. FIX run: I wrapped Case._configure_case so it first does expanduser().resolve() on both paths and mkdir(parents=True, exist_ok=True) on both parents. With both parents missing, the case was created: "RESULT FIX_both_parents_missing: OK caseroot=.../fixcase/sub/audit_cca1_fix exists=True inputdir=.../fixin/sub/audit_cca1_fix exists=True".

**Root cause.** Case.__init__ calls _configure_case (case.py:197) before any folder is created. _configure_case sets cvars["CUSTOM_GRID_PATH"].value = inputdir (case.py:903) and cvars["CASEROOT"].value = caseroot (case.py:1060). The ConfigVar then copies each value into its widget (ConfigVar._post_value_change, then ConfigVarStr._update_widget_value, sets widget.value). visualCaseGen.initialize, which Case() calls at case.py:138, makes those widgets ipyfilechooser FileChooser objects with new_only=True (grid_widgets.py:53 and launcher_widgets.py:23). Their `@validate`("value") hook (filechooser.py:183-189) runs os.path.split(value) and then _check_selection, which raises RuntimeError when os.path.exists(parent) is False (filechooser.py:399-400). For a bare relative name the parent from os.path.split is '' (pathlib also drops a leading './'). For '~/x' it is the literal '~'. case.py:202-203 wraps the error. The parent mkdirs in _create_grid_input_files (case.py:383) and _create_newcase (case.py:476-477) run only after this point, so they cannot help. The FileChooser check is right for the GUI, so the bug is in CrocoDash's ordering and path handling.

**Smallest fix.** In CrocoDash/case.py Case.__init__, normalise the paths right after init_args_check and before _configure_case: self.caseroot = Path(caseroot).expanduser().resolve() and self.inputdir = Path(inputdir).expanduser().resolve(). Then call self.caseroot.parent.mkdir(parents=True, exist_ok=True) and self.inputdir.parent.mkdir(parents=True, exist_ok=True). Remove the dead check-and-mkdir at case.py:476-477. Doing this after init_args_check means a bad argument does not leave empty parent folders behind. I verified this change by monkeypatch: the case is created. Ideally, also expanduser/resolve before init_args_check, so that the exists checks and the saved state use the same absolute path.

### C11. Relative caseroot is created under $HOME but configured under cwd: Case() crashes, leaves a stray case in $HOME, and override=True cannot clear it

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `creation_cli-a3`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:170 (self.caseroot = Path(caseroot), never made absolute; it reaches cvars CASEROOT at CrocoDash/case.py:1060); inconsistency in CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_creator.py:123-125 (Path.home()/caseroot only for create_newcase) vs case_tools.py:34 and :144 (xmlchange and case.setup use cwd=cvars CASEROOT as given) and case_creator.py:87 (_final_checks against cwd)
- **Already fixed on main:** No (target is main). No open CrocoDash or visualCaseGen PR changes this path handling: I scanned all open PR diffs for resolve/expanduser/Path.home, and the only hit is PR #320, an unrelated __file__ resolve. The visualCaseGen pin 0eb6fd6 is ESMCI main.
- **Related:** Lead finding (Case() fails when the parent of caseroot or inputdir is missing; case.py:383/476-477 dead mkdir), which is in the same path-validation block. The creation_cli relative-inputdir finding (r2a: relative inputdir breaks process_forcings after chdir) shares the same normalization fix. CrocoDash #286 (inputdir == caseroot, unclear error) is also in init_args_check. 1.1 items #329/#340 (read or create a case from caseroot) touch caseroot handling but do not fix this. Not in TRIAGE.md or QUEUE.md.

**What's wrong.** Case() never resolves caseroot. With a relative caseroot that has a folder part, e.g. 'cases/mycase', CrocoDash's checks run against the process cwd: init_args_check (case.py:299), the ipyfilechooser path check, and _final_checks (case_creator.py:87). visualCaseGen's CaseCreator.create_case then rewrites a non-absolute CASEROOT as Path.home()/caseroot and runs create_newcase there. The next step, _update_grids_via_xmlchange, calls ./xmlchange with cwd set to the original relative CASEROOT, which resolves against the cwd and does not exist, so Case() raises. Case's cleanup (_remove_failed_attempt) removes the inputdir and the cwd-relative caseroot (which never existed) but not the real case under $HOME. A retry, even with override=True, fails with 'ERROR: Case directory $HOME/cases/mycase already exists', because _remove_previous also targets the cwd path. If $HOME/cases does not exist, the first attempt fails instead with 'Cannot write to $HOME/cases/mycase. Please choose another directory.', although the user named a writable folder under cwd. Related, lower priority: '~' is never expanded in cesmroot, caseroot or inputdir. For example, cesmroot='~/work/installs/X' raises 'Given CESM root directory doesn't exist!' (visualCaseGen cime_interface.py:97), and a YAML recipe passes these strings through unchanged (recipe.py).

**Who hits it.** Case(caseroot='some_dir/mycase', ...) where cwd != $HOME, e.g. a notebook in a subfolder or a script run from a project directory. The same happens with 'crocodash create' and a YAML recipe whose case.caseroot is relative. It works only by accident when cwd == $HOME.

**Repro.**

D=dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a3; source .../scratchpad/audit/env.sh; mkdir -p $D/fakehome/rel_cases $D/wd/rel_cases $D/inputs; cd $D/wd && HOME=$D/fakehome timeout 900 $PY -u $D/scripts/v_relcase.py $D audit_v3a_1   (log v1.log). Key lines of v_relcase.py: a 2x2 deg, 0.5 deg flat Grid/Topo, VGrid.uniform(nk=5), then Case(cesmroot=$CESMROOT, caseroot='rel_cases/audit_v3a_1', inputdir=$D/inputs/audit_v3a_1, compset='1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV', atm_grid_name='T62', machine='derecho', project='ncgd0011'). Variants: scripts/v_relcase_override.py, the same rerun with override=True (log v2_retry_override.log); scripts/v_relcase_nohomedir.py, caseroot='only_cwd/<name>' where only $D/wd/only_cwd exists (log v3_nohomedir.log).

- Expected: The case is created at <cwd>/rel_cases/audit_v3a_1, the same directory the checks, xmlchange, case.setup and later CrocoDash calls use. Failing that, a relative caseroot is refused up front with a clear error. A failed attempt leaves nothing behind, and override=True clears the previous attempt.
- Observed: v1.log: 'create_newcase ... --case .../creation_cli-a3/fakehome/rel_cases/audit_v3a_1 ... The create_newcase command was successful.' then './xmlchange OCN_GRID=v3a --non-local', 'Removing files from the failed attempt: .../inputs/audit_v3a_1', 'RuntimeError Error running ./xmlchange OCN_GRID=v3a --non-local in rel_cases/audit_v3a_1: [Errno 2] No such file or directory: 'rel_cases/audit_v3a_1''. Afterwards the cwd case exists: False; the home case exists: True, holding Buildconf, LockedFiles, case.build and so on. v2_retry_override.log (override=True): 'ERROR: Case directory .../fakehome/rel_cases/audit_v3a_1 already exists' / 'RuntimeError Error creating case.'. v3_nohomedir.log: 'RuntimeError Cannot write to .../fakehome/only_cwd/audit_v3a_2. Please choose another directory.' (the directory exists under cwd).

**Root cause.** CrocoDash stores caseroot as given (case.py:170) and sets cvars['CASEROOT'] to that relative string (case.py:1060). Its own existence and override handling resolve the string against cwd (case.py:206-213, 299). In visualCaseGen, CaseCreator.create_case resolves a non-absolute CASEROOT against Path.home(), but only into a local variable that is passed to create_newcase (case_creator.py:123-125). The other CASEROOT readers use cvars['CASEROOT'] unchanged: xmlchange (case_tools.py:144, subprocess cwd=caseroot), run_case_setup (case_tools.py:34), append_user_nl (case_tools.py:92) and _final_checks (case_creator.py:87). These resolve against cwd, so the two halves of case creation target different directories. The visualCaseGen GUI always produces absolute paths from its FileChooser, so only CrocoDash's programmatic path reaches this.

**Smallest fix.** CrocoDash: at the top of Case.__init__, before init_args_check and initialize_visualCaseGen, normalize all three paths: cesmroot, caseroot and inputdir = Path(x).expanduser().resolve(). This fixes the crash and the stray case, and gives '~' support. This is the same normalization the relative-inputdir finding needs. visualCaseGen (secondary, for consistency): at case_creator.py:124-125, resolve a relative CASEROOT against cwd (or keep home) and write the absolute path back into cvars['CASEROOT'], so that _final_checks, xmlchange, case.setup and append_user_nl all use the same directory.

### C12. CESM output products are NO_LEAP, but CrocoDash does Gregorian date math (3 bugs)

All three come from one gap: CESM output (POP, MOM6) uses a 365-day calendar, but run length, chunk bounds and the nested-case calendar are computed in Gregorian dates. One PR that does the date arithmetic in the product's calendar can fix all three. File them as one issue, or as three that link to each other. Related: TRIAGE item 1 / #353 (CESM output time not cut to the window), and 1.1 Q5 / #335 (TimeRequest).

#### C12.1 STOP_N counts Gregorian days for NO_LEAP (CESM output) products, so the run goes past its last OBC record when the dates span Feb 29

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `configure_process-a3`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:684-688
- **Already fixed on main:** No (target is main). Open PR #326 carries the same expression unchanged. Queue item Q8 (time-windows, #333) pads the OBC window by the record spacing, which would hide a 1-day overshoot for daily data, but its note says the run length still "counts end − start days, the same as STOP_N". The day count itself is not fixed anywhere.
- **Related:** #353 (CESM_POP_OUTPUT boundaries crash earlier today, so POP users reach this only after it is fixed); #326 (moves the STOP_N line unchanged); 1.1 Q8/#333 (time-windows padding; run length = end − start) and Q5/#335 (calendar-safe TimeRequest); closed #35 (Feb 29 records with a NO_LEAP calendar, a different symptom). Sibling bug found while verifying, not part of this finding: with CESM_MOM_OUTPUT and date_range 2020-02-01 to 2020-03-01, the 7-day GET chunking (obc.py _make_date_pairs, Gregorian) makes a chunk that starts on 2020-02-29. get_mom6_output_data (cesm_ocean_output.py:245, cftime.date2num with calendar noleap) then crashes with "ValueError: invalid day number provided in cftime.DatetimeNoLeap(2020, 2, 29...)". Log: dev/crocodash_1_0_x/audit_repros/verify/configure_process-a3/repro.log

**What's wrong.** configure_forcings sets CALENDAR from the forcing product. That is NO_LEAP for CESM_POP_OUTPUT and CESM_MOM_OUTPUT. It then sets STOP_OPTION=ndays and STOP_N=(date_range[1] - date_range[0]).days, which pandas counts on the proleptic Gregorian calendar. Every Feb 29 inside date_range adds a day that the NO_LEAP model does not have, so the model stops k days after date_range[1] (k = number of leap days in the range). The OBC files that process_forcings writes cover exactly [date_range[0], date_range[1]] in the noleap calendar, with no modulo attribute. Once model time passes the last record, FMS time_interp_external has no record to interpolate to and stops the run with a FATAL error. If the data did reach further, the run would still be k days longer than the user asked for.

**Who hits it.** Conditions from a NO_LEAP product (CESM_MOM_OUTPUT today; CESM_POP_OUTPUT too once #353 is fixed), with a date_range containing Feb 29 of a leap year. Examples: ['2020-02-20','2020-03-05'] (STOP_N 14 instead of 13), ['2020-01-01','2021-01-01'] (1 extra day), or 2000-2010 (3 extra days).

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/configure_process-a3 && $PY make_src.py src && timeout 900 $PY -u repro.py audit_v_cpa3_2 "2020-02-20 00:00:00" "2020-03-05 00:00:00" && $PY inspect_obc.py input/audit_v_cpa3_2/ocn 2020-02-20 14
What the scripts do:
- make_src.py writes synthetic native MOM6 daily-mean output: xh/yh/xq/yq/z_l, time on a noleap calendar from 2020-01-25 to 2020-03-10.
- repro.py builds a 4x4 deg, 0.5 deg grid case with the NYF compset and calls case.configure_forcings(date_range=[...], product_name="CESM_MOM_OUTPUT", function_name="get_mom6_output_data", function_overrides={"dataset_path": src, "file_glob": "*.nc"}). It reads CALENDAR, RUN_STARTDATE and STOP_N from env_*.xml, then calls case.process_forcings().
- inspect_obc.py compares the time span of each ocn/forcing_obc_segment_*.nc with RUN_STARTDATE + STOP_N counted in the noleap calendar.

- Expected: STOP_N=13 (2020-02-20 to 2020-03-05 is 13 days in the NO_LEAP calendar the case runs on), so the model stops at 2020-03-05 00:00, which is the last OBC record. For ['2020-02-01','2020-03-01'] STOP_N should be 28, and for 2000-01-01 to 2010-01-01 it should be 3650.
- Observed: Observed output:
"CALENDAR=NO_LEAP RUN_STARTDATE=2020-02-20 STOP_OPTION=ndays STOP_N=14"
"model stop time in NO_LEAP calendar: 2020-03-06 00:00:00 | user date_range end: 2020-03-05 00:00:00"
"forcing_obc_segment_001.nc | units: days since 2020-02-20 | calendar: noleap | first: 2020-02-20 00:00:00 | last: 2020-03-05 00:00:00 | n: 14 | model stop (NO_LEAP): 2020-03-06 00:00:00 | model passes last record: True" (segments 002-004 are the same).
The OBC time variable has no modulo attribute. FMS time_interp.F90:821-828 (mtime == NONE) then raises "time ... is after range of list", which time_interp_external2 turns into an mpp_error FATAL. MOM6 reaches that code through MOM_open_boundary.F90:4495 on the first step after 2020-03-05 00:00. This last step is from reading; I did not run CESM.

**Root cause.** (self.date_range[1] - self.date_range[0]).days subtracts pandas Timestamps, which are always proleptic Gregorian. It ignores self.forcing_product.calendar, the calendar that the CALENDAR xmlchange just above sets for the model.

**Smallest fix.** Count the run days in the product's calendar:
cal = self.forcing_product.calendar.cf
s, e = (cftime.datetime(d.year, d.month, d.day, d.hour, d.minute, calendar=cal) for d in self.date_range)
STOP_N = (e - s).days
For noleap, a Feb 29 endpoint should get a clear ValueError at configure time; cftime already raises "invalid day number". Open PR #326 moves this line unchanged into its own configurator, so the fix has to be carried there as well.

#### C12.2 OBC/IC date bounds are Gregorian, so a Feb 29 chunk bound crashes process_forcings for NO_LEAP products (CESM_MOM_OUTPUT, CESM_POP_OUTPUT)

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `configure_process-a4`)
- **Confidence:** high
- **Location:** CrocoDash/forcing/obc.py:405 (REGRID slice). Also CrocoDash/forcing/obc.py:53-66 (_make_date_pairs: Gregorian bounds), CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:245-249 (get_mom6_output_data date2num on GET bounds), CrocoDash/forcing/ic.py:61 (IC end = start + 1 day)
- **Already fixed on main:** No; the target is main, and no open PR fixes it. PR #358 only picks the IC record at or before the start, and #327 does not touch calendars. The 1.1 time-request branch (Q5/#335, not yet a PR) plans calendar-safe REGRID and IC slices.
- **Related:** 1.1 queue Q5 / CrocoDash #335 (TimeRequest: "REGRID and IC slices are calendar-safe", noleap Feb 29 handling); CrocoDash #353 (CESM output timing; its boundary half hides this for the tseries readers under default chunking) and PR #358 (#353's IC half; does not fix this); #333 (chunk sizing)

**What's wrong.** process_obc_conditions turns the date range into Python (Gregorian) datetimes. _make_date_pairs cuts GET and REGRID chunks from them, so a chunk can start or end on Feb 29 of a leap year. Two places then build a date in the product's own calendar from those bounds:
(1) _regrid_one_chunk slices the decoded raw data with ds_full.sel(time=slice(start_str, end_str)) (obc.py:405). For a NO_LEAP product the time index is a noleap CFTimeIndex, and the string '2020-02-29' raises ValueError.
(2) CESM_MOM_OUTPUT.get_mom6_output_data converts the request dates with cftime.date2num(..., calendar='noleap') (cesm_ocean_output.py:245), which raises on Feb 29. The OBC engine (7-day GET chunks) and the IC engine (start + 1 day, ic.py:61) both pass it such dates.
Both NO_LEAP products, CESM_MOM_OUTPUT and CESM_POP_OUTPUT, decode to noleap in REGRID, because convert_cftime_to_numeric writes calendar='noleap' on the raw files.
With the defaults (get_step_days=7, regrid_step_days=30), a case is hit if:
- it starts Jan 1 of a leap year and runs past Feb 29 (REGRID chunk 2 is Jan 31 to Feb 29);
- any REGRID chunk starts or ends on Feb 29;
- any 7-day GET chunk starts or ends on Feb 29 (about 2 in 7 start dates for runs that span Feb 29 of a leap year);
- it starts Feb 28 of a leap year (IC request Feb 28 to Feb 29).

**Who hits it.** A nested or CESM-output case: configure_forcings(product_name="CESM_MOM_OUTPUT", function_name="get_mom6_output_data", function_overrides={"dataset_path": <parent MOM6 output dir>}) with date_range 2020-01-01 to 2020-03-05, then process_forcings(). Variants:
- start 2020-02-02: the GET chunk Feb 23 to Feb 29 crashes;
- start 2020-02-28: the IC GET crashes.
For CESM_POP_OUTPUT and the *_single_variable_data readers, the same REGRID slice fails, but with default chunking #353's non-unique-time crash usually comes first.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/configure_process-a4
1. timeout 300 $PY -u make_parent.py parent
   Writes a tiny noleap daily MOM6-style history file (thetao/so/uo/vo/zos on xh/yh/xq/yq/z_l, 2020-01-01 to 2020-03-10).
2. timeout 900 $PY -u case_noleap.py
   Steps: 4x4 deg 0.5 deg Grid, flat Topo, 5-level VGrid; Case(..., compset 1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV, override=True); case.configure_forcings(date_range=["2020-01-01 00:00:00","2020-03-05 00:00:00"], product_name="CESM_MOM_OUTPUT", function_name="get_mom6_output_data", function_overrides={"dataset_path": <scratch>/parent, "file_glob": "*.nc"}); case.process_forcings(process_ic=False).
3. timeout 600 $PY -u get_feb29.py
   Calls CESM_MOM_OUTPUT.get_mom6_output_data with dates ["2020-02-28","2020-02-29"] (the IC request for a Feb 28 start) and ["2020-02-23","2020-02-29"] (the GET chunk for a Feb 2 start).

- Expected: Chunk bounds should map onto the product's calendar. A noleap product has no Feb 29, so a Gregorian window [Jan 31, Feb 29] should select Jan 31 to Feb 28, and a window starting Feb 29 should start Mar 1. process_forcings should then produce forcing_obc_segment_NNN.nc for the whole range, and the IC fetch for a Feb 28 start should succeed.
- Observed: case_noleap.py:
- GET wrote all 40 raw chunks.
- REGRID wrote forcing_obc_segment_001_2020-01-01_2020-01-30.nc and forcing_obc_segment_001_2020-03-01_2020-03-05.nc. The worker on [2020-01-31, 2020-02-29] raised from obc.py:831 (_regrid_boundary), with this stack:
  obc.py:405 ds_full.sel(time=slice(...)) -> xarray cftimeindex._maybe_cast_slice_bound -> "ValueError: invalid day number provided in cftime.DatetimeNoLeap(2020, 2, 29, 0, 0, 0, 0, has_year_zero=True)"
- process_forcings aborted.
get_feb29.py:
- "['2020-02-28', '2020-02-29'] RAISED ValueError invalid day number provided in cftime.DatetimeNoLeap(2020, 2, 29, 23, 59, 59, 0, has_year_zero=True)"
- The same error for ['2020-02-23', '2020-02-29'].
- _make_date_pairs for a 2020-02-02 start gives ('02-23','02-29') as a GET chunk.
Probe: on a noleap index, slice('2020-01-31','2020-02-28') returns 29 records, but slice('2020-01-31','2020-02-29') and slice('2020-02-29', ...) both raise. Versions: xarray 2026.2.0, cftime 1.6.6, pandas 3.0.6.

**Root cause.** Date bounds are built and formatted in the Gregorian calendar in three places: obc._make_date_pairs (Python datetime + timedelta), ic.process_initial_condition (start + timedelta(days=1)) and the filename-based strings. They are then used against data in the product's own calendar, either a noleap CFTimeIndex slice (obc.py:405) or cftime.date2num(calendar='noleap') (cesm_ocean_output.py:245). Neither the OBC nor the IC engine reads dataset_varnames['calendar'] (the product's Calendar), so Feb 29 is never mapped to a valid noleap date.

**Smallest fix.** Clamp bounds to the target calendar where they meet the data:
- In _regrid_one_chunk, when ds_full.indexes['time'] is a CFTimeIndex whose calendar lacks the date, slice with an end of Feb 29 -> '…-02-28' and a start of Feb 29 -> '…-03-01'. A Gregorian window [s, Feb 29] covers exactly the noleap records up to Feb 28.
- In get_mom6_output_data, build sel_dates with the same clamp before cftime.date2num, or compare against an exclusive next-day bound.
A fuller alternative is to generate the pairs with xr.date_range(..., calendar=product calendar.cf, use_cftime=True). The 1.1 plan does this through TimeRequest.select (Q5/#335; SPACE_TIME.md: "a Feb 29 date becomes Mar 1 there"). Filenames and coverage checks can stay Gregorian.

#### C12.3 CESM_MOM_OUTPUT hard-codes the NOLEAP calendar, so a child nested in a GREGORIAN parent (e.g. a CrocoDash GLORYS run) is set to NO_LEAP and its OBC regrid crashes on Feb 29

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `raw_data-a2`)
- **Confidence:** high
- **Location:** CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:184 (calendar = NOLEAP; also used at :222 in convert_cftime_to_numeric), CrocoDash/case.py:669-673 (CALENDAR xmlchange from self.forcing_product.calendar.cesm), CrocoDash/forcing/mom6.py:136 (calendar=dataset_varnames["calendar"]["mom6"] passed to rm6); crash raised at CrocoDash/rm6/regional_mom6/segment.py:932 (encode_cf_datetime)
- **Already fixed on main:** No (target is CrocoDash main b8991c89). No open PR fixes it: #327 only touches convert_cftime_to_numeric's signature and sample_dates, and #326 only moves where the CALENDAR xmlchange is written. rm6 origin/main (e349363) does not change segment.py, but rm6 is not at fault.
- **Related:** The user flow is gallery/crocodash/advanced/nesting_demo.ipynb: the parent is forced by GLORYS (GREGORIAN), the children use CESM_MOM_OUTPUT (NO_LEAP), and the demo's January 2000 window happens to avoid Feb 29. Merged PR #220 (Flexible Calendar Assignment based on ForcingProduct) introduced per-product calendars. Closed issues #246 (GLORYS dataset is Gregorian) and #35 (CESM case fails with leap years) are related history. 1.1 queue Q5 / #335 (TimeRequest makes slices calendar-safe in the data's own calendar) does not fix the product-level calendar. Nesting PR #249 was abandoned. The product's other access method, get_mom6_single_variable_data, shares the same class calendar.

**What's wrong.** CESM_MOM_OUTPUT is the product for nesting a child domain inside a parent MOM6 run, and it declares calendar = NOLEAP as fixed class metadata. configure_forcings therefore always runs './xmlchange CALENDAR=NO_LEAP' on the child. The product metadata written to config.json also carries calendar noleap, and the OBC regrid uses it to encode the segment times, whatever calendar the parent actually ran. Any CrocoDash case forced by GLORYS, the reference products, ERA5 and so on runs GREGORIAN. That includes the parent in the gallery nesting demo. When such a run is the parent, its output holds real Feb 29 records. Any child window that contains Feb 29 of a leap year then crashes in the OBC regrid with a cftime 'invalid day number' error that does not name the cause. Windows without Feb 29 work, but the child silently runs NO_LEAP while its parent runs GREGORIAN.

**Who hits it.** Nest a child as in gallery/crocodash/advanced/nesting_demo.ipynb. Force the parent with GLORYS, so it gets CALENDAR=GREGORIAN. Then call configure_forcings on the child with product_name='cesm_mom_output', function_name='get_mom6_output_data', function_overrides={'dataset_path': <parent history dir>}, and a date_range that spans Feb 29 of a leap year (e.g. 2020-02-27 to 2020-03-02, or a whole year such as 2000). Then run process_forcings (the bc step).

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/raw_data-a2 && timeout 900 $PY -u repro_nest_gregorian.py (log: out_nest.log). What the script does:
1. It writes a synthetic parent file parent.mom6.h.native.nc: zos/thetao/so/uo/vo on xh/yh/xq/yq/z_l, daily from 2020-02-20 to 2020-03-08, saved with encoding={'time': {'units': 'days since 2020-01-01', 'calendar': 'gregorian'}}.
2. It builds Grid(lenx=2, leny=2, resolution=0.5, xstart=-59, ystart=31), a flat Topo and VGrid.uniform(nk=5), then Case(..., compset='1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV', machine='derecho', override=True).
3. It calls case.configure_forcings(date_range=['2020-02-27 00:00:00', '2020-03-02 00:00:00'], product_name='CESM_MOM_OUTPUT', function_name='get_mom6_output_data', function_overrides={'dataset_path': <parent dir>}) and then case.process_forcings().
Follow-up scripts in the same directory: tb.py prints the CrocoDash and rm6 traceback frames. control.py runs two controls: a window without Feb 29, and the Feb 29 window with the product calendar swapped for GREGORIAN.

- Expected: The child should use the parent's own calendar: GREGORIAN here, both for CALENDAR and for the OBC time encoding. The OBC files for 2020-02-27 to 2020-03-02 should then be written with 5 records. Failing that, configure_forcings should refuse with a clear message that the parent output is not noleap.
- Observed: configure_forcings ran './xmlchange CALENDAR=NO_LEAP --non-local' and env_run.xml then held CALENDAR NO_LEAP. The product calendar was "Calendar(cf='noleap', cesm='NO_LEAP', mom6='noleap')", and config.json stored calendar {'cf': 'noleap', 'cesm': 'NO_LEAP', 'mom6': 'noleap'}. The raw south chunk held times 2020-02-27T12 to 2020-03-02T12, including 2020-02-29T12:00, with calendar gregorian. The IC step succeeded. The OBC REGRID [south] step failed with "process_forcings FAILED: ValueError invalid day number provided in cftime.DatetimeNoLeap(2020, 2, 29, 12, 0, 0, 0, has_year_zero=True)", raised from CrocoDash/forcing/mom6.py:126 (_regrid_obc_chunk) into CrocoDash/rm6/regional_mom6/segment.py:932 (regrid_velocity_tracers, encode_cf_datetime). Controls: the same data and calendar with a 2020-03-01 to 03-02 window gave "OK time [0. 1.] {'calendar': 'noleap', ...}". The Feb 27 to Mar 2 window with the calendar swapped for gregorian gave "OK time [0. 1. 2. 3. 4.] {'calendar': 'gregorian', 'units': 'days since 2020-02-27 00:00:00'}".

**Root cause.** The calendar is product-level class metadata (MOM6ForcingProduct.calendar). For CESM_MOM_OUTPUT the right calendar depends on the parent run the user points dataset_path at, and CrocoDash's own regional runs are GREGORIAN unless the product is a CESM one. The value is never read from the files' time:calendar. It is used three ways: for the child's CALENDAR xmlchange (case.py:671), for the product metadata block in config.json that mom6.py:136 passes to rm6 as the encoding calendar, and in convert_cftime_to_numeric (cesm_ocean_output.py:222). get_mom6_output_data keeps the parent's gregorian times as they are. rm6 decodes the raw chunk with the file's own calendar (segment.py:140) and then re-encodes it in the noleap calendar it was given (segment.py:932). A real Feb 29 has no noleap equivalent, so the encode raises.

**Smallest fix.** In configure_forcings, or in the MOM6 conditions configurator where product.write_metadata() is stored (mom6.py:563-566), work out CESM_MOM_OUTPUT's calendar from the data:
- open the first file matching file_glob under dataset_path with decode_times=False and read time:calendar;
- map noleap/365_day to NOLEAP and gregorian/standard/proleptic_gregorian to GREGORIAN, and raise on anything else;
- use that Calendar for the CALENDAR xmlchange (case.py:669-673), for the 'calendar' entry in the config.json product metadata (read by mom6.py:136), and in convert_cftime_to_numeric (cesm_ocean_output.py:222).
Do not mutate the class attribute: it is shared global state across Cases. Pass the detected Calendar instead. A minimal stopgap is to refuse at configure time, with a clear message, when the parent files' calendar is not noleap.

### C13. Sharing (bundle / duplicate / fork) on 1.0.x: 8 confirmed bugs in shareable.py

These are all on main. In 1.1, #340 (Q13) replaces fork and duplicate with `crocodash create --from`, and #342 (Q15) deletes shareable.py. For 1.0.x, either file one tracking issue with these 8 items, or fix only the ones that lose data or settings without saying so: .1 (deletes existing dirs), .2 (resets user-changed values) and .3 (drops the runoff map and CICE forcing). The rest fail loudly.

#### C13.1 crocodash duplicate and fork always run with override=True: they silently delete an existing target inputdir/caseroot and, when the case name is reused, the source case's bld/run dir

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `creation_cli-a4`)
- **Confidence:** high
- **Location:** CrocoDash/shareable.py:402 (duplicate_case), CrocoDash/shareable.py:553 (ForkBundle.fork), CrocoDash/case.py:205-212 (override rmtree of inputdir, caseroot, CIME_OUTPUT_ROOT/<caseroot.name>), CrocoDash/cli.py:269 and :296 (duplicate/fork subparsers have no --override)
- **Already fixed on main:** No (target is main). It is not fixed on main at b8991c89. 1.1 removes fork/duplicate: issue #340 (branch bundle-and-create-from, where `crocodash create --from` passes args.override, default False) and issue #342 (drop shareable.py). Neither is merged.
- **Related:** CrocoDash #340 (create --from replaces fork/duplicate; 1.1 queue Q13), CrocoDash #342 (delete shareable.py). This is related to, but separate from, the creation_cli lead finding that Case() fails when the parent of caseroot/inputdir does not exist.

**What's wrong.** duplicate_case() (also reached as CaseBundle.duplicate_case and `crocodash duplicate`) and ForkBundle.fork() (`crocodash fork`) call create_case_from_yaml(config, override=True, configure_only=True) unconditionally. Neither CLI subcommand has an --override flag, and neither docs/source/for_users/shareable.md nor cli.md says anything is deleted. Case.__init__ with override=True runs shutil.rmtree on three paths without any prompt: the new inputdir, the new caseroot and CIME_OUTPUT_ROOT/<new case name>. This has two consequences. (1) If --inputdir or --case points at an existing folder, that folder is deleted whole. If that folder holds the source case's inputdir (e.g. --inputdir set to the parent folder of the source inputdir), the source case loses its grid and processed forcing files. (2) duplicate is documented as copying a case "to a new location within the same user context", so CIME_OUTPUT_ROOT is the same for both cases. Duplicating /A/mycase to /B/mycase, the natural way to copy a case to a new folder, therefore deletes $CIME_OUTPUT_ROOT/mycase. That is the source case's own bld/ and run/ directory, with its model output and restart files. fork does the same when a user forks their own bundle on the same machine under the same case name. fork's interactive "Proceed with this configuration?" prompt does not say that existing directories will be deleted.

**Who hits it.** `crocodash duplicate --source /A/mycase --case /B/mycase --inputdir <anything>` deletes /A/mycase's bld/run dir. Passing an existing folder as `--inputdir` or `--case` to `crocodash duplicate` or `crocodash fork` deletes that folder. The same happens from Python through duplicate_case(...), CaseBundle(...).duplicate_case(...) and ForkBundle(...).fork(...).

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a4 && timeout 900 $PY -u v1_dup_cli.py > v1b.log 2>&1

What the script does:
1. Builds a 8x8, 5-level NYF source case: caseroot=V/src_b/audit_v4b, inputdir=V/inputs_b/audit_v4b_in, configure_forcings with reference_ocean/get_reference_ocean_data.
2. Writes stand-in files V/inputs_b/audit_v4b_in/ocn/forcing_obc_segment_001_PROCESSED.nc and $CIME_OUTPUT_ROOT/audit_v4b/run/audit_v4b.mom6.r.0001-01-01-00000.nc.
3. Wraps CrocoDash.case._remove_previous: paths inside the scratch dir are really deleted; paths outside it are only logged.
4. Runs the real CLI: sys.argv=["crocodash","duplicate","--source",V/src_b/audit_v4b,"--case",V/dst_b/audit_v4b,"--inputdir",V/inputs_b]; CrocoDash.cli.main().
The script also puts CESM's MOM_RPS dir on sys.path to work around the known param_file_reader env artifact.

- Expected: duplicate/fork should refuse when the target inputdir or caseroot already exists, and when CIME_OUTPUT_ROOT/<new name> belongs to another case (e.g. the new name equals the source name). That is what Case(override=False) already does. Deleting should happen only when the user explicitly asks for it (an --override flag).
- Observed: From v1b.log:
"[8s] source case built; CIME bld/run dir = /glade/derecho/scratch/manishrv/audit_v4b exists=True"
"markers: True True"
"REMOVE (real, inside scratch): .../creation_cli-a4/inputs_b exists=True"
"REMOVE (real, inside scratch): .../creation_cli-a4/dst_b/audit_v4b exists=False"
"WOULD REMOVE (outside scratch, skipped): /glade/derecho/scratch/manishrv/audit_v4b exists=True contains=['bld', 'bld/CASEROOT', 'bld/atm', ...]"
"after duplicate: source caseroot exists: True / source inputdir exists: False / source processed-forcing marker exists: False"
"/glade/derecho/scratch/manishrv/audit_v4b (existed=True) same_as_source_rundir_parent=True"

Because my guard skipped the bld/run delete, create_newcase then refused with "Error creating case: a previous case with the same name left its build/run directories behind". This shows that override=False would have stopped cleanly here, while the unguarded override=True path deletes the source's bld/run dir and carries on.

**Root cause.** override=True is hard-coded in duplicate_case (shareable.py:402) and ForkBundle.fork (shareable.py:553), and the CLI subcommands (cli.py:269, :296) do not expose the flag. With override=True, Case.__init__ (case.py:205-212) calls _remove_previous (case.py:34-38, shutil.rmtree) on inputdir, caseroot and Path(cime.cime_output_root)/caseroot.name. It does not check whether those dirs belong to another case. For the bld/run dir, CIME's default naming means the same case name maps to the same directory as the source case.

**Smallest fix.** Change shareable.py:402 and :553 to pass override=False. Optionally add a `--override` store_true flag (default False) to the duplicate and fork subparsers and thread it through duplicate_case/fork, as `crocodash create` already does at cli.py:183. With override=False, Case.init_args_check rejects an existing caseroot/inputdir and create_newcase rejects a leftover same-name bld/run dir. duplicate_case could also refuse up front when Path(new_caseroot).name == Path(caseroot).name, since in the same user context that always collides with the source's bld/run dir. The bundle-time temp case at shareable.py:285 uses a uuid name in a TemporaryDirectory and can keep override=True.

#### C13.2 duplicate/bundle/fork silently reset a user-changed value of any parameter CrocoDash also sets (e.g. DT in user_nl_mom, STOP_N)

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `creation_cli-a7`)
- **Confidence:** high
- **Location:** CrocoDash/shareable.py:248 (and :254). Also CrocoDash/shareable.py:240-257 (CaseBundle.diff), :68-80 (copy_user_nl_params_from_case), :94-105 (apply_xmlchanges_to_case), :383-443 (duplicate_case), :690-712 (ForkBundle.apply_copy_plan)
- **Already fixed on main:** No (target is main). No open PR fixes it. Q13 (#340, branch bundle-and-create-from) and Q15 (#342, drop-shareable) replace and then delete shareable.py in 1.1.
- **Related:** CrocoDash #340 (Q13 bundle / create --from, replaces fork and duplicate), #342 (Q15 delete shareable.py). The separate finding that apply_xmlchanges_to_case passes "VALUE --non-local" as the xml value (seen when DOUT_S is replayed) blocks any xmlchange part of this fix.

**What's wrong.** CaseBundle.diff() checks only whether a user_nl parameter name or xmlchange variable name exists in the freshly created reference case. It never compares values. Any parameter the reference case also writes therefore counts as "standard", even when the user changed its value. For user_nl_mom that includes DT, DT_THERM, MINIMUM_DEPTH/MAXIMUM_DEPTH, the OBC_* settings and the OBC_SEGMENT_*_VELOCITY_NUDGING_TIMESCALES. For xml it includes STOP_N, STOP_OPTION, RUN_STARTDATE and CALENDAR. duplicate_case() and ForkBundle.fork() rebuild the case from the recipe and replay only the parameters diff() listed, so the new case silently gets the CrocoDash default back. bundle() writes a non_standard_case_info.json that does not mention the change. The bundle's copy of user_nl_mom does hold the user's value, but fork never reads that value. No warning is printed at any step.

**Who hits it.** After a CFL crash, the user edits `DT = 1800.0` to `DT = 900.0` in user_nl_mom (and/or runs `./xmlchange STOP_N=1`). They then run `crocodash duplicate`, or `crocodash bundle` followed by `crocodash fork`, or the Python duplicate_case / CaseBundle.bundle / ForkBundle.fork.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a7 && timeout 900 $PY -u make_src.py && timeout 900 $PY -u dup.py < /dev/null
make_src.py: builds a 4x4-degree, 0.5-degree, 5-level flat NYF Case (audit_v7_src), runs configure_forcings(reference_ocean, 2020-01-01..04), changes the user_nl_mom line `DT = 1800.0` to `DT = 900.0` in place, then calls xmlchange("STOP_N","1", caseroot=A, is_non_local=True).
dup.py: duplicate_case(A, B, IB, bundle_dir=V/"bundles"), then ForkBundle(bundle).fork(..., plan={"xml_files":True,"user_nl":True,"source_mods":True,"xmlchanges":True}). It prints the DT lines from user_nl_mom and STOP_N from env_run.xml for the source, the duplicate and the fork. dup.py puts CESM_crocodash/components/mom/cime_config/MOM_RPS on sys.path only to get past the known local param_file_reader environment artifact.

- Expected: The duplicate and the forked case should keep the source's `DT = 900.0` and STOP_N=1. At minimum, non_standard_case_info should list DT and STOP_N as non-standard so that fork can offer to carry them over.
- Observed: RESULT non_standard_case_info: {"xml_files_missing_in_new": [], "user_nl_missing_params": {"cpl": [], "datm": [], "mom": []}, "source_mods_missing_files": [], "xmlchanges_missing": []}
RESULT SRC  DT: ['DT = 900.0']  STOP_N: 1
RESULT DUP  DT: ['DT = 1800.0']  STOP_N: 3
RESULT BUNDLE user_nl_mom DT: ['DT = 900.0']
RESULT FORK DT: ['DT = 1800.0']  STOP_N: 3
Exit code was 0 and no warning was printed.

**Root cause.** diff() tests `subsubkey not in other_case.user_nl_objs[key][subkey]` (shareable.py:248) and `k not in other_case.xmlchanges` (:254). Both are name-membership tests; the values are read (self.user_nl_objs[...][...]["value"], self.xmlchanges[k]) but never compared. copy_user_nl_params_from_case and apply_xmlchanges_to_case replay only the names in that diff. A changed value of a parameter the recipe also writes is therefore never captured, and create_case_from_yaml rewrites the CrocoDash default.

**Smallest fix.** 1. In diff(), also flag a user_nl parameter whose ['value'] differs from the reference's value, and an xmlchange whose last value differs from the reference's.
2. Before comparing, skip or normalise values the recipe rederives per case, or the "fix" will copy the old case's paths into the new one: INPUTDIR, GRID_FILE, TOPO_FILE and ALE_COORDINATE_CONFIG (their hash-suffixed file names differ between cases), and the *_DOMAIN_MESH / MASK_MESH xml paths. One way is to replace the source and reference inputdir and grid basenames with a placeholder.
3. When replaying, replace the existing line in user_nl_<comp> instead of appending through append_user_nl. MOM_RPS's param_file_reader raises "DT listed more than once" on a duplicated key, which would break buildnml.
4. Replay xmlchanges by their final value. apply_xmlchanges_to_case must also strip the trailing " --non-local" that replay.sh lines carry; otherwise it passes "1 --non-local" as the value.

#### C13.3 fork drops the bundled runoff map (mapping/) and CICE forcing (ice/), duplicate drops mapping/, and validate_case can never report a missing file

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `creation_cli-a8`)
- **Confidence:** high
- **Location:** CrocoDash/shareable.py:556-565 (fork copies only wav/ and ocn/), CrocoDash/shareable.py:407 (duplicate_case copies only ocn/ice/wav), CrocoDash/forcing/base.py:866-881 (get_output_filepaths filters to existing files, so validate_output_filepaths is always True), CrocoDash/case.py:1131-1139 (validate_case)
- **Already fixed on main:** No (target is main). No open PR fixes it. The 1.1 queue removes this code: #340 (Q13, bundle-and-create-from) replaces fork/duplicate with `crocodash create --from`, and #342 (Q15) deletes shareable.py. Both are unmerged, so 1.0.x users still hit this.
- **Related:** CrocoDash #340 (Q13 bundle-and-create-from), #342 (Q15 drop-shareable). Separate lead, not verified: runoff/tides get_output_filepaths return .resolve()d paths, and bundle() calls Path(path).relative_to(Path(ocn_dir).parent) (shareable.py:333). If inputdir was given through a symlink (e.g. ~/scratch -> /glade/derecho/scratch/<user>), that would raise ValueError. Also cosmetic: the runoff map is copied twice because LIQ and ICE share one file.

**What's wrong.** CaseBundle.bundle() copies each configurator's output files and keeps their layout under inputdir (shareable.py:330-335). For a GLOFAS-runoff case that gives mapping/<ROF2OCN map>.nc, and for a CICE-restoring case ice/cice_forcing.nc. ForkBundle.fork() copies only bundle/wav and bundle/ocn into the new inputdir, so the runoff map and the CICE forcing file are silently left out. duplicate_case() copies ocn/, ice/ and wav/ from the old inputdir but not mapping/. The new case's configure_forcings still points at the missing files: ROF2OCN_LIQ/ICE_RMAPNAME = <new inputdir>/mapping/<map>.nc, and with restoring on, ice_ic = <new inputdir>/ice/cice_forcing.nc. fork then calls validate_case(), which cannot flag this. BaseConfigurator.get_output_filepaths returns only paths that already exist (base.py:872), and the runoff, cice, tides and ww3 overrides do the same. So validate_output_filepaths (base.py:876-881) is always True and validate_case prints nothing. Users only find out at case.submit or at run time. Regenerating the GLOFAS map needs a ~200 GB PBS job.

**Who hits it.** A case with DROF%GLOFAS (runoff mapping) and/or CICE restoring, e.g. compset GR_JRA. Run `crocodash bundle` then `crocodash fork` (or ForkBundle(...).fork(...)), or run `crocodash duplicate` (duplicate_case). Neither needs any non-default option.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a8; timeout 900 $PY -u a8_fork.py </dev/null (creates the source case and checks validate_case; log a8_fork_part1.log); then timeout 900 $PY -u a8_fork2.py </dev/null (log a8_fork2.log); then timeout 900 $PY -u a8_dup.py </dev/null (log a8_dup.log). Key lines: Case(compset="GR_JRA", atm_grid_name="TL319", 4x4 deg @0.5 grid, VGrid.uniform(nk=5)); configure_forcings(date_range=[2020-01-01, 2020-01-03], product_name="reference_ocean", function_name="get_reference_ocean_data"); write stand-ins at config.json runoff ROF2OCN_LIQ_RMAPNAME, <inputdir>/ice/cice_forcing.nc, <inputdir>/ocn/init_tracers.nc; bdir = CaseBundle(src_root).bundle(D/"bundles"); ForkBundle(bdir).fork(..., plan={}); duplicate_case(src_root, new_caseroot, new_inputdir). The scripts insert CESM_crocodash's MOM_RPS dir on sys.path to avoid the known param_file_reader environment artifact.

- Expected: fork restores every forcing subfolder the bundle carries (ocn/, wav/, ice/, mapping/) into the new inputdir, and duplicate_case carries mapping/ too. If a configured output file is still missing, validate_case() says so ("<name> is not valid yet ...").
- Observed: BUNDLE files: ['ice/cice_forcing.nc', 'mapping/GLOFAS_to_a8v_map_r200_f400_nnsm.nc', 'ocn/init_tracers.nc'] | FORK printed 'not valid yet': False | FORK ROF2OCN_LIQ_RMAPNAME: .../inputs/audit_a8v_fork/mapping/GLOFAS_to_a8v_map_r200_f400_nnsm.nc exists: False | FORK ice/cice_forcing.nc exists: False | FORK ocn/init_tracers.nc exists: True | FORK inputdir subdirs: ['extract_forcings', 'ice', 'ocn'] | DUP ROF2OCN_LIQ_RMAPNAME: .../inputs/audit_a8v_dup/mapping/GLOFAS_to_a8v_map_r200_f400_nnsm.nc exists: False | DUP ice/cice_forcing.nc exists: True | DUP validate_case output: '' | On a fresh source case before any processing: "SRC validate_case before any processing -> ''" with every configurator (streamyears, cice, conditions, runoff) at get_output_filepaths=[] validate=True.

**Root cause.** The bundle writes files under whatever subfolder each configurator outputs to (ocn/, wav/, ice/, mapping/). fork hard-codes the two subfolders it restores, wav and ocn (shareable.py:556-565). duplicate_case hard-codes ("ice", "wav") next to ocn (shareable.py:407). CICE's ice/ and runoff's mapping/ outputs were added later and never wired into either function. get_output_filepaths was written for bundling, where it should copy only files that exist, and it filters out missing files (base.py:872; same for the runoff/cice/tides/ww3 overrides). validate_output_filepaths reuses it, so it only checks files already known to exist and always returns True.

**Smallest fix.** In ForkBundle.fork, replace the wav/ocn special cases with one loop over bundle subdirectories, skipping xml_files and SourceMods: shutil.copytree(sub, new_inputdir/sub.name, dirs_exist_ok=True), keeping the skip-if-exists rule for ocn/. In duplicate_case, add "mapping" to the tuple at shareable.py:407, or loop over all old inputdir subdirectories except extract_forcings. Make validate_output_filepaths check the configured paths without the exists filter. For example, give get_output_filepaths an existing_only=True flag and have validate call it with False. The runoff override would then check its ROF2OCN_*_RMAPNAME paths, and CICE, with restoring on, would check _forcing_filepath().

#### C13.4 dump/bundle/duplicate/fork rebuild a case from compset_lname instead of the alias it was created with, so cases created from a MARBL alias (e.g. CR1850MARBL_JRA) cannot be recreated

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `creation_cli-a10`)
- **Confidence:** high
- **Location:** CrocoDash/recipe.py:279 (emits state["compset_lname"] as case.compset); CrocoDash/case_state.py:38 ("compset" in INIT_ARGS_EXCLUDE); CrocoDash/case.py:1085 (_write_state stores only compset_lname). Failure surfaces at CrocoDash/case.py:880/893 (_configure_custom_compset); reached from CrocoDash/shareable.py:285 (bundle reference case), :402 (duplicate_case), :553 (fork) and cli.py _dump/_create.
- **Already fixed on main:** No (target is main). No open PR changes the state or recipe handling. CrocoDash PR #279 (changes requested; the reviewer asked for the fix to be made in visualCaseGen instead) and the visualCaseGen #55 fix would both remove the crash indirectly. The 1.1 branch bundle-and-create-from (#340) still emits case.compset_lname (recipe.py:280) and still excludes compset from the state.
- **Related:** visualCaseGen #55 (underlying multi-modifier solver bug; TRIAGE item 5); visualCaseGen #54 (closed) and #40 (duplicate of #55); CrocoDash PR #279 (multi-modifier workaround); CrocoDash #340 (1.1 bundle / create --from, carries the same lname-only recipe)

**What's wrong.** Case.__init__ resolves an alias to its long name, and the state file (_crocodash_state.json) keeps only compset_lname: the compset argument is in INIT_ARGS_EXCLUDE and the alias is not saved anywhere. case_to_yaml therefore always writes the long name. When create_case_from_yaml rebuilds the case, a long name is not a key of cime.compsets, so Case() takes the custom-compset path (_configure_custom_compset) instead of the standard-alias path. That path cannot take a component with two modifiers (MOM6%REGIONAL%MARBL-BIO, visualCaseGen #55). As a result, every case created from a regional MARBL alias (CR1850MARBL_JRA, CWR1850MARBL_JRA, GR1850MARBL_JRA, GWR1850MARBL_JRA) cannot be recreated by any sharing flow, even though the original creation worked. The flows are `crocodash dump` + `crocodash create`, `crocodash bundle` (its temporary reference case), `crocodash duplicate` and the fork of a bundle. The documented MARBL path uses exactly these aliases (gallery projects/marbl.ipynb uses compset="CR1850MARBL_JRA").

**Who hits it.** Case(compset="CR1850MARBL_JRA", ...) (or any *MARBL_JRA regional alias). Then, in a new process, case_to_yaml(caseroot) followed by create_case_from_yaml(config) at a new caseroot/inputdir. The same applies to `crocodash dump` | `crocodash create`, `crocodash bundle`, `crocodash duplicate` and the fork of a bundle.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a10 && timeout 900 $PY -u step1_create_alias.py CR1850MARBL_JRA marbl && timeout 900 $PY -u step2_dump_recreate.py marbl  (control: same with `CR_JRA crjra`; fix check: step3_fix_check.py). step1: 4x4 deg, 0.5 deg grid, flat 1000 m topo, 5-level vgrid; Case(compset=alias, atm_grid_name="TL319", machine="derecho", override=True). step2: cfg = case_to_yaml(orig_caseroot); set new caseroot/inputdir; create_case_from_yaml(cfg, override=True, configure_only=True). No forcings were configured, so a successful Case() is followed by the expected "Cannot recreate a case without a forcings configuration" ValueError.

- Expected: A case dumped from an alias-created MARBL case is recreated the same way as the original: Case() succeeds, and here create_case_from_yaml goes on to the forcings check, as the CR_JRA control does.
- Observed: step1: "STEP1 CREATED from CR1850MARBL_JRA | case.compset_alias = CR1850MARBL_JRA"; state compset keys: {'compset_lname': '1850_DATM%JRA-1p5-2023_SLND_DICE%SSMI_MOM6%REGIONAL%MARBL-BIO_DROF%GLOFAS_SGLC_SWAV'} (alias not stored). step2: "STEP2 dumped case.compset = 1850_DATM%JRA-1p5-2023_SLND_DICE%SSMI_MOM6%REGIONAL%MARBL-BIO_DROF%GLOFAS_SGLC_SWAV" then "STEP2 RESULT: RuntimeError Case configuration failed: Invalid assignment of COMPSET_LNAME to 1850_DATM%JRA-1p5-2023_SLND_DICE%SSMI_MOM6%REGIONAL%MARBL-BIO_DROF_SGLC_SWAV. Reasons:" (empty Reasons). Control CR_JRA: Case() succeeds through the long name and stops at "ValueError Cannot recreate a case without a forcings configuration". Fix check (dumped config with compset set back to "CR1850MARBL_JRA"): reaches the same forcings ValueError, so Case() succeeded.

**Root cause.** case_state.INIT_ARGS_EXCLUDE drops "compset" (case_state.py:38), and Case._write_state saves only the resolved compset_lname (case.py:1085). recipe.case_to_yaml writes state["compset_lname"] as case.compset (recipe.py:279), so a recreated case always goes through _configure_custom_compset. There, case.py:880 assigns the joined "REGIONAL%MARBL-BIO" to COMP_OCN_OPTION, which visualCaseGen's solver rejects (register_assignment vs. register_options, visualCaseGen #55). The standard-alias path (_configure_standard_compset) avoids this, which is why the original creation worked.

**Smallest fix.** Record the alias in the state file, e.g. add "compset_alias": self.compset_alias in _write_state and add it to DERIVED_KEYS. In case_to_yaml, emit "compset": state.get("compset_alias") or state["compset_lname"], which also works for older state files. The proper fix is visualCaseGen #55; once it lands (with a vCG pin bump) the long name recreates fine and this crash disappears even without the CrocoDash change.

#### C13.5 crocodash bundle/duplicate crash with KeyError when user_nl_cpl, user_nl_datm or user_nl_drof has any line, or user_nl_mom has a parameter block (KPP%, MLE%)

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `creation_cli-a5`)
- **Confidence:** high
- **Location:** CrocoDash/shareable.py:248
- **Already fixed on main:** No (target is main; origin/main == b8991c89, and diff() is unchanged). No open PR fixes it: #326 does not touch shareable.py. The 1.1 items #340 (Q13 bundle-and-create-from) and #342 (Q15 drop-shareable) remove shareable.py altogether.
- **Related:** CrocoDash #340 and #342 (1.1 queue Q13/Q15, which replace or delete shareable.py). CrocoDash #321 (closed): on a CESM whose MOM_interface has the param_file_reader split, CaseBundle fails earlier with ModuleNotFoundError, which hides this bug there. Users of the pinned regional_092326/regional_100926 tags reach the KeyError. Not in TRIAGE.md.

**What's wrong.** To find the user's non-standard user_nl settings, CaseBundle.diff() goes through every module of every user_nl file in the source case and indexes `other_case.user_nl_objs[key][subkey]` on the freshly made reference case, with no default. The MOM6 param reader that parses these files creates a module key only when that module holds a parameter. CrocoDash never writes user_nl_cpl, user_nl_datm or user_nl_drof, so in the reference case they parse to {} with no 'Global' key. The reference user_nl_mom has only 'Global'. As a result, any line in user_nl_cpl/datm/drof, or any MOM block parameter (KPP%...%KPP or KPP%N_SMOOTH), raises KeyError. That breaks identify_non_standard_case_info (shareable.py:288), and with it `crocodash bundle` (cli.py:83, CaseBundle.bundle at shareable.py:300) and `crocodash duplicate` / duplicate_case (shareable.py:393). The crash happens before anything is written.

**Who hits it.** On a CrocoDash case with forcings configured, add any setting to user_nl_cpl (e.g. `orb_iyear = 1990`), user_nl_datm or user_nl_drof. Or add a parameter-block setting to user_nl_mom (`KPP%` / `N_SMOOTH = 2` / `%KPP`, or `KPP%N_SMOOTH = 2`). Then run `crocodash bundle <caseroot> ...`, `crocodash duplicate ...`, CaseBundle(caseroot).bundle(...), or duplicate_case(...).

**Repro.**

source .../scratchpad/audit/env.sh; export PYTHONPATH=$PYTHONPATH:$CESMROOT/components/mom/cime_config/MOM_RPS  (the known param_file_reader env artifact). cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a5 && timeout 900 $PY -u make_src.py && timeout 900 $PY -u bundle_diff.py && timeout 900 $PY -u cli_tb.py.
make_src.py: 4x4 deg at 0.5 deg, flat 1000 m, 10 levels, NYF compset, configure_forcings(reference_ocean/get_reference_ocean_data, 2 days) -> cases/audit_v_a5_src.
bundle_diff.py: wraps shareable.create_case_from_yaml only to build the reference case as cases/audit_v_a5_ref, which keeps the audit_ naming rule. It then runs identify_non_standard_case_info on the unedited case (control). Next, it appends `orb_iyear = 1990` to user_nl_cpl, or `KPP%\nN_SMOOTH = 2\n%KPP` to user_nl_mom, and calls CaseBundle(src).diff(CaseBundle(ref)).
cli_tb.py: same user_nl_cpl edit, then cli._bundle(args) for the full traceback. Logs are bundle_diff.log and cli_tb.log.

- Expected: The bundle is written. The user's settings are reported as non-standard, e.g. user_nl_missing_params={'cpl': ['orb_iyear'], 'datm': [], 'mom': [...]}, and duplicate carries them over (inside their KPP% block for block parameters).
- Observed: Control (unedited): OK -> BundleDifferences(..., user_nl_missing_params={'cpl': [], 'datm': [], 'mom': []}). Reference parse: "ref user_nl_cpl parsed: OrderedDict()", "ref user_nl_mom modules: ['Global']". A global user_nl_mom HFREEZE works: {'cpl': [], 'datm': [], 'mom': ['HFREEZE']}.
user_nl_cpl edit: "RAISED KeyError: 'Global'  at shareable.py:248 in diff". KPP% block and KPP%N_SMOOTH: "RAISED KeyError: 'KPP'  at shareable.py:248 in diff".
CLI path traceback: cli.py line 83 in _bundle -> shareable.py line 288 in identify_non_standard_case_info `self.non_standard_case_info = self.diff(CaseBundle(caseroot_tmp))` -> shareable.py line 248 in diff `if subsubkey not in other_case.user_nl_objs[key][subkey]:` -> "KeyError: 'Global'".
The MOM_RPS reader from the pinned regional_100926 tag gives the same keys: an empty user_nl_cpl -> {}, a KPP block -> {'KPP': {...}}.

**Root cause.** diff() assumes every module key in the source case's parsed user_nl also exists in the reference case's (`other_case.user_nl_objs[key][subkey]`). FType_MOM_params.from_MOM_input (both the inline reader in the pinned MOM_interface tags and the newer param_file_reader.read_MOM_params) adds a module to _data only when it reads a parameter in it. An empty file therefore has no 'Global', and a block absent from the reference has no key.

**Smallest fix.** In diff(), look up `other_case.user_nl_objs.get(key, {}).get(subkey, {})`. With that patched in, the repro returns {'cpl': ['orb_iyear'], 'datm': [], 'mom': ['N_SMOOTH']}. The fix also needs to keep the block: record (module, param) in user_nl_missing_params, and have copy_user_nl_params_from_case (shareable.py:68-80) write block parameters back as `KPP%` ... `%KPP` (or `KPP%N_SMOOTH = ...`). Today that function skips the `KPP%` line and appends a bare `N_SMOOTH = 2` at global scope. MOM6 silently ignores that with the pinned MOM_interface tags, and newer MOM_interface buildnml rejects it. It also drops the prefixed `KPP%N_SMOOTH` form altogether, because the name does not match.

#### C13.6 duplicate_case and fork replay './xmlchange VAR=VAL --non-local' with '--non-local' kept in the value: logical and integer variables crash after the new case is created, string variables are silently set to 'VAL --non-local'

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `creation_cli-a6`)
- **Confidence:** high
- **Location:** CrocoDash/shareable.py:101-105 (apply_xmlchanges_to_case); same parsing in CrocoDash/shareable.py:192-196 (CaseBundle._read_xmlchanges); called from CrocoDash/shareable.py:436 (duplicate_case) and CrocoDash/shareable.py:709 (ForkBundle.apply_copy_plan)
- **Already fixed on main:** No (target is main). No open PR fixes shareable.py itself. 1.1 items CrocoDash #340 (Q13, branch bundle-and-create-from) and #342 (Q15, drop-shareable) remove fork/duplicate/shareable.py and replace the parser with a shlex-based case_state.parse_xmlchanges that handles flags. That does not help 1.0.x users.
- **Related:** CrocoDash #340 (Q13 create --from, replaces fork/duplicate); CrocoDash #342 (Q15 delete shareable.py); the MCP duplicate_case_tool and fork_case tools reach the same code (QUEUE.md item 6 and the MCP move); TRIAGE lead finding on Case() parent dirs (same creation_cli area, different bug)

**What's wrong.** To carry user xmlchanges over to a new case, apply_xmlchanges_to_case re-reads the source replay.sh. It parses each line with `_, kv = line.split(None, 1); param, value = kv.split("=", 1)` and calls xmlchange(param, value, is_non_local=True). For the line `./xmlchange DOUT_S=FALSE --non-local` this gives value 'FALSE --non-local', and the command run is `./xmlchange 'DOUT_S=FALSE --non-local' --non-local`.
- **Logical or integer variable:** CIME rejects the value and the RuntimeError propagates out of duplicate_case. By then the new caseroot and inputdir already exist, with its xml files, user_nl and SourceMods already copied. Changes listed later in replay.sh are not applied, and the optional bundle step is skipped.
- **String variable** (DOUT_S_ROOT, for example): CIME accepts 'VAL --non-local' and the new case silently gets a corrupted value.
- **Fork:** ForkBundle.fork with plan xmlchanges=true runs the same function on the bundle's replay.sh.

**Who hits it.** Any case whose user xmlchanges were made with a flag. The common case is a derecho case created or edited from Casper (NCAR JupyterHub). There CIME refuses a plain ./xmlchange ('Current machine casper does not match case machine derecho') and CrocoDash's own is_non_local is True, so every replay.sh line ends in --non-local. When the user has changed a variable that CrocoDash itself does not set (DOUT_S, DOUT_S_ROOT, JOB_PRIORITY, ...), it is flagged as non-standard and replayed by `crocodash duplicate`, by Case/CaseBundle.duplicate_case, or by `crocodash fork` with plan xmlchanges=true. Leading flags break it too. `./xmlchange --force DOUT_S=FALSE` produces the key '--force DOUT_S', which argparse then rejects. The `--id X --val Y` form has no '=' and is silently dropped.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; export PYTHONPATH=$CESMROOT/components/mom/cime_config/MOM_RPS:$PYTHONPATH  # works around the known param_file_reader env artifact only
cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a6 && TMPDIR=$PWD/tmp timeout 900 $PY -u repro.py   (log: repro2.log)
Script dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a6/repro.py does the following:
- Creates a 4x4 deg, 0.5 deg-resolution case audit_a6v_src: NYF compset, machine=derecho, run from Casper.
- Runs configure_forcings(reference_ocean / get_reference_ocean_data, 2 days).
- Runs xmlchange("DOUT_S_ROOT", <dir>, caseroot=A, is_non_local=True) and xmlchange("DOUT_S", "FALSE", caseroot=A, is_non_local=True).
- Runs duplicate_case(A, B, IB).
- Reads DOUT_S_ROOT and DOUT_S from B's env_*.xml.

- Expected: Case B gets DOUT_S_ROOT=<dir> and DOUT_S=FALSE, and duplicate_case returns normally.
- Observed: Source replay.sh tail: './xmlchange DOUT_S_ROOT=<dir> --non-local', './xmlchange DOUT_S=FALSE --non-local'.
Then:
- "./xmlchange 'DOUT_S_ROOT=<dir> --non-local' --non-local" (accepted)
- "./xmlchange 'DOUT_S=FALSE --non-local' --non-local"
- "duplicate_case RAISED RuntimeError ... ERROR: Entry DOUT_S was listed as type logical but had val 'FALSE --non-local' instead of TRUE or FALSE"
- "B exists: True | B has env_run.xml: True | B user_nl_mom: True"
- "B DOUT_S_ROOT = '<dir> --non-local'" (silently corrupted)
B's own replay.sh now records './xmlchange DOUT_S_ROOT="<dir> --non-local" --non-local'. The shlex-based parse in the same script returns the correct {'DOUT_S_ROOT': '<dir>'} and {'DOUT_S': 'FALSE'} from the same lines.

**Root cause.** replay.sh lines are parsed with str.split instead of CIME's xmlchange argument syntax. apply_xmlchanges_to_case (shareable.py:101-102) takes everything after the first '=' as the value, including any trailing flags. It takes everything between 'xmlchange' and '=' as the key, including any leading flags. _read_xmlchanges (shareable.py:192-196) builds the non-standard key list the same way. The existing unit test (tests/shareable/test_apply.py::test_apply_xmlchanges_to_case) only covers flag-free lines.

**Smallest fix.** In apply_xmlchanges_to_case and _read_xmlchanges, parse each line with shlex.split. Skip tokens that start with '-' and tokens without '='. Split each remaining 'K=V[,K2=V2]' token on ',' and then on the first '='. Also pass caseroot= explicitly to xmlchange so it does not depend on cvars["CASEROOT"]. Add a test line such as './xmlchange DOUT_S=FALSE --non-local' to test_apply_xmlchanges_to_case. Optionally, parse and validate the replay before create_case_from_yaml so a bad line cannot leave a half-made case. For reference, case_state.parse_xmlchanges on the 1.1 branch bundle-and-create-from already implements this parsing.

#### C13.7 crocodash duplicate crashes with IsADirectoryError on any case with tides; the tides step leaves ocn/weights, ocn/forcing and a symlink cycle in inputdir

- **Repo:** CrocoDash
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `rm6-a4`)
- **Confidence:** high
- **Location:** CrocoDash/shareable.py:412-415 (crash site); CrocoDash/forcing/tides.py:128-142 (source of the directories and symlinks); side effects at CrocoDash/rm6/regional_mom6/regional_mom6.py:449,496-504 and CrocoDash/rm6/regional_mom6/segment.py:1143
- **Already fixed on main:** No. The target is CrocoDash main, and origin/main is still b8991c89. No open PR fixes it. The 1.1 queue item Q13/#340 (bundle-and-create-from) removes duplicate_case, and its Case.bundle copies only listed is_file() paths, so the crash goes away there. However, tides.py on that branch still builds the experiment with mom_run_dir=ctx.inputdir, so the symlink cycle remains. regional-mom6 origin/main e349363 leaves the constructor side effects unchanged, but they are not an rm6 bug.
- **Related:** CrocoDash #340 (Q13, replaces duplicate with create --from), #342 (Q15, deletes shareable.py). Not the same bug as #344 (OBC tide params changing) or the regional-mom6 #15 tides-seam item in TRIAGE.

**What's wrong.** To call setup_boundary_tides, TidesConfigurator.process builds a full regional-mom6 experiment with mom_run_dir=inputdir and mom_input_dir=inputdir/ocn. The experiment constructor's standalone run-directory side effects then land in the case inputdir:
- it writes ocn/hgrid.nc (regional_mom6.py:449)
- it creates ocn/weights/ and ocn/forcing/ (:496-497)
- it creates the symlinks inputdir/inputdir -> inputdir/ocn and ocn/rundir -> inputdir (:499-504). Together they form a cycle, so ocn/rundir/ocn/rundir/... resolves forever.
Segment.regrid_tides also writes its tidal weights into ocn/weights/ (segment.py:1143).

duplicate_case (shareable.py:412-415) calls shutil.copy on every entry of the old inputdir/ocn. The first directory or directory symlink it reaches raises IsADirectoryError, and iterdir order decides which one that is. By then create_case_from_yaml has already created the new caseroot and inputdir. The result is a half-built duplicate: some forcing files are copied, and the non-standard xml, user_nl, SourceMods and xmlchange state is never transferred. Any tool that follows symlinks (cp -rL, rsync -L, find -L) also loops on the cycle.

CaseBundle.bundle is not affected, because it filters files by prefix.

**Who hits it.** Configure forcings with tides (tpxo_elevation_filepath, tpxo_velocity_filepath, tidal_constituents) and run process_forcings. Then run `crocodash duplicate` (cli.py _duplicate_case), shareable.duplicate_case or CaseBundle.duplicate_case on that case.

**Repro.**

D=dev/crocodash_1_0_x/audit_repros/verify/rm6-a4; source .../scratchpad/audit/env.sh; cd $D
timeout 900 $PY -u make_src.py $D   # Grid(lenx=3, leny=3, resolution=0.5, xstart=-60, ystart=30), flat topo, VGrid.uniform(nk=5); Case audit_va4_src with NYF compset; configure_forcings(date_range=2020-01-01..01-03, product_name="reference_ocean", function_name="get_reference_ocean_data", tpxo_elevation_filepath=.../crocogallerydata/tpxo/h_tpxo9.v1.nc, tpxo_velocity_filepath=.../u_tpxo9.v1.nc, tidal_constituents=["M2"]); process_forcings(); then lists inputdir and inputdir/ocn
timeout 900 $PY -u dup.py $D plain  # CrocoDash.shareable.duplicate_case(cases/audit_va4_src, cases/audit_va4_dup, input/audit_va4_dup)
timeout 900 $PY -u dup.py $D fix    # same call with shareable.shutil.copy monkeypatched to skip directories
(dup.py puts MOM_RPS on sys.path only to get past the known param_file_reader environment artifact.) Logs: $D/make_src.log, $D/dup_plain.log, $D/dup_fix.log

- Expected: duplicate_case finishes and the new inputdir/ocn holds every regular file of the source case, including tu_segment_*.nc and tz_segment_*.nc. Processing forcings leaves no directories, no stray hgrid.nc and no self-referencing symlinks in the case inputdir.
- Observed: After process_forcings (tides 105 s):
  DIR ocn/forcing (empty)
  DIR ocn/weights (12 bilinear_tidal_*_weights_segment_00N.nc)
  file ocn/hgrid.nc
  SYMLINK audit_va4_src/inputdir -> .../input/audit_va4_src/ocn
  SYMLINK ocn/rundir -> .../input/audit_va4_src
  "cycle: realpath(ocn/rundir) == inputdir: True"
  "deep path resolves: True" (ocn/rundir/ocn/rundir/ocn/rundir/inputdir/rundir/ocn)

duplicate_case:
  File ".../CrocoDash/shareable.py", line 415, in duplicate_case
    shutil.copy(src, dst)
  IsADirectoryError: [Errno 21] Is a directory: '.../input/audit_va4_src/ocn/weights'
The new ocn held only 8 entries, 3 of them from the source (forcing_obc_segment_004.nc, init_tracers_filled.nc, tz_segment_003.nc). 22 source files were missing, including tu_segment_001-004 and forcing_obc_segment_001-003.

With copy patched to skip directories, it skipped ocn/weights, ocn/forcing and ocn/rundir and printed "DUPLICATE OK". All 8 tu/tz files were carried over, with "missing regular files vs source: []".

**Root cause.** CrocoDash reuses the regional-mom6 experiment object only to reach setup_boundary_tides, and points it at the case inputdir. The constructor's filesystem side effects, meant for a standalone rm6 run directory, then pollute inputdir: the weights and forcing directories, hgrid.nc, and the two cross-linking symlinks. Segment.regrid_tides independently creates outfolder/weights. duplicate_case assumes inputdir/ocn (and ice/, wav/) contain only regular files, and it calls shutil.copy on every entry without checking.

**Smallest fix.** Required fix, in duplicate_case (shareable.py:412-415): skip anything that is not a regular file, with `if not src.is_file(): continue` before shutil.copy. is_file() follows symlinks, so the rundir symlink to a directory is skipped and a symlink to a file is still copied. I verified this by monkeypatch.

Hygiene fix, in tides.py:128-146: stop constructing rmom6.experiment against the case inputdir. Call rmom6.prepare_tpxo_tidal_forcing, then for each boundary call Segment.cardinal(hgrid, b, f"segment_{n:03d}").regrid_tides(..., outfolder=ctx.output_path, ...) directly. This removes the symlink cycle, ocn/forcing and ocn/hgrid.nc. ocn/weights would still be created by Segment.regrid_tides, so the duplicate_case guard is still needed.

#### C13.8 crocodash bundle/duplicate leave the hidden reference case's bld/run dirs under CIME_OUTPUT_ROOT

- **Repo:** CrocoDash
- **Severity:** cosmetic
- **Evidence:** confirmed by repro (audit id `creation_cli-a13`)
- **Confidence:** high
- **Location:** CrocoDash/shareable.py:269
- **Already fixed on main:** No (target is main). No open PR fixes it. In 1.1, Q15 drop-shareable (and #340/Q13 bundle-and-create-from) removes shareable.py and the fork/duplicate CLI, but the bundle-and-create-from branch still has the same TemporaryDirectory code (shareable.py:252) until Q15 lands.
- **Related:** CrocoDash #340 (bundle + create --from, replaces this code in 1.1); 1.1 queue Q13 (bundle-and-create-from) and Q15 (drop-shareable); QUEUE.md merge-hazard 6 (move MCP bundle_case/duplicate_case_tool off shareable.py). Finder's own runs r5/r6a/r6b/r7/r10 in audit/creation_cli. Leftover from this verification, not deleted because it is outside my scratch dir: /glade/derecho/scratch/manishrv/temp_case-e128d20f135d419dbbc9e3a00fe9962b.

**What's wrong.** CaseBundle.identify_non_standard_case_info (shareable.py:259-289) builds a hidden reference case so it can diff against it. It calls create_case_from_yaml(..., override=True, configure_only=True) at line 285, with caseroot=<TemporaryDirectory>/temp_case-<uuid> and the inputdir inside the same temp directory. On exit, TemporaryDirectory deletes only the caseroot and the inputdir. CIME put the reference case's EXEROOT and RUNDIR at $CIME_OUTPUT_ROOT/temp_case-<uuid>/{bld,run}, and these stay behind. Each `crocodash bundle`, `crocodash duplicate`, CaseBundle.bundle() or duplicate_case() call leaves one more randomly named directory in the user's CIME output root (about 129K each). The bld/CASEROOT and run/CASEROOT files inside point at a caseroot that no longer exists. The same thing happens when the reference case creation fails partway, because no try/finally does any cleanup.

**Who hits it.** Any `crocodash bundle --caseroot ...`, `crocodash duplicate ...`, CaseBundle(caseroot).bundle(out_dir), CaseBundle(caseroot).identify_non_standard_case_info(...) or shareable.duplicate_case(...) on an existing CrocoDash case.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a13 && timeout 900 $PY -u repro.py   (script dev/crocodash_1_0_x/audit_repros/verify/creation_cli-a13/repro.py; log repro2.log). Key lines: the script builds a tiny NYF case (4x4 deg, 0.5 deg, 10 levels, flat 1000 m, machine=derecho) and runs configure_forcings with reference_ocean/get_reference_ocean_data. It snapshots glob('/glade/derecho/scratch/manishrv/temp_case-*'), then calls CaseBundle(caseroot).identify_non_standard_case_info(CESMROOT, 'derecho', 'ncgd0011') and diffs the glob. The MOM_RPS directory is put on sys.path only to work around the known local param_file_reader artifact. The fix check is fixcheck.py in the same dir: it monkeypatches the proposed try/finally rmtree and the leftover goes away.

- Expected: Once the diff is taken, nothing of the throwaway reference case is left on disk: no new /glade/derecho/scratch/manishrv/temp_case-* directory.
- Observed: "INFO [CrocoDash.shareable] Create temporary case for comparison in /glade/derecho/scratch/manishrv/tmp/tmpnp_oivd4" / "TemporaryDirectory used: ['/glade/derecho/scratch/manishrv/tmp/tmpnp_oivd4'] exists after call: [False]" / "NEW leftover dirs under CIME_OUTPUT_ROOT: ['/glade/derecho/scratch/manishrv/temp_case-e128d20f135d419dbbc9e3a00fe9962b']" / "... ['bld', 'run'] 129K"; bld holds CASEROOT, atm, cpl, esp, glc, ice, lib, lnd, ocn, rof; run holds CASEROOT. There are 12 such temp_case-* dirs in /glade/derecho/scratch/manishrv right now from audit runs. With the monkeypatched fix (fixcheck.log) the result is "NEW leftover dirs with fix: []" and the diff result is unchanged.

**Root cause.** CIME sets EXEROOT and RUNDIR to $CIME_OUTPUT_ROOT/$CASE/{bld,run} (machine default /glade/derecho/scratch/$USER), not under CASEROOT. Using TemporaryDirectory for the caseroot therefore cleans up only part of the reference case. identify_non_standard_case_info never removes the output-root directory, on success or on failure.

**Smallest fix.** In identify_non_standard_case_info, wrap create_case_from_yaml and the diff in try/finally. Before the TemporaryDirectory exits, read the reference case's output root (for example ref = CaseBundle(caseroot_tmp); out_root = ref._case.get_value("CIME_OUTPUT_ROOT")) and call shutil.rmtree(Path(out_root) / caseroot_tmp.name, ignore_errors=True). If case creation failed before ref existed, fall back to reading CIME_OUTPUT_ROOT via xmlquery in caseroot_tmp. The uuid case name means nothing else can live in that directory. I checked this with a monkeypatch: no leftover, and the diff result is identical.

### C14. Case() with machine omitted (documented default None) always raises "Couldn't determine machine", even though visualCaseGen detected it; the auto-detect fallback is dead code

- **Repo:** CrocoDash
- **Severity:** misleading error
- **Evidence:** confirmed by repro (audit id `vcg-a9`)
- **Confidence:** high
- **Location:** CrocoDash/case.py:356 (raise in init_args_check); CrocoDash/case.py:160 (raw machine passed to init_args_check); CrocoDash/case.py:178 (dead fallback `machine or self.cime.machine`)
- **Already fixed on main:** No (target is main). origin/main is b8991c89, the same as the audited worktree, and still has the check at case.py:356-358 and the fallback at :178. None of the open CrocoDash PRs (#326, #327, #320, #279 diffs checked) changes it.
- **Related:** CrocoDash #240 (empty body, "CIME_MACHINE env needed when creating a case on local computer"; TRIAGE "needs details"). It is about machine detection on unported hosts. It is related but not the same bug. With this fix, a user on an unported host who omits machine= would fall back to CESM_NOT_PORTED.

**What's wrong.** Case.__init__ documents `machine: str | None = None` ("Default is None"). It also has a fallback, `self.machine = machine or self.cime.machine`, that should use the machine visualCaseGen detected. But __init__ calls Case.init_args_check(machine=machine) with the raw argument first, and that check raises ValueError when machine is None. So the fallback can never run, and leaving out machine= always fails. The error says "Couldn't determine machine", which is false: visualCaseGen's cime.machine is always set, either to the detected machine or to CESM_NOT_PORTED. CrocoDash never tries to determine the machine before it raises.

**Who hits it.** Python API: Case(cesmroot=..., caseroot=..., inputdir=..., compset=..., ocn_grid=..., ocn_topo=..., ocn_vgrid=..., project=...) without machine=, on any host. On Casper and Derecho CIME detects the machine. The CLI (--machine required) and YAML recipes (case.machine required) are not affected.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a9 && timeout 900 $PY -u repro_machine_none.py [fix]
Script dev/crocodash_1_0_x/audit_repros/verify/vcg-a9/repro_machine_none.py:
  grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="auda9"); topo.set_flat(1000.0); vgrid = VGrid.uniform(nk=5, depth=1000.0, name="auda9")
  cime = initialize_visualCaseGen(CESMROOT); print(cime.machine, cime.machine in cime.machines)
  Case(caseroot=..., inputdir=..., compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV", ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62", project="ncgd0011", override=True)   # no machine=
  With the argument "fix", it monkeypatches Case.init_args_check to receive machine=machine or cime.machine, then creates a second case.

- Expected: Following the docstring default and case.py:178, Case() should fall back to the machine visualCaseGen detected ('casper' here) and create the case. It should raise only if no usable machine exists, with a message that names the detected value.
- Observed: visualCaseGen detected cime.machine = 'casper' | in cime.machines: True
1) machine omitted -> RAISED ValueError: Couldn't determine machine. Please provide the machine argument.
   caseroot created? False
With the fix monkeypatched: "Case created successfully at .../cases/audit_vcga9_2", "2) with fix: Case created, case.machine = 'casper'", and env_case.xml has <entry id="MACH" value="casper">.

**Root cause.** The order of operations in Case.__init__ is wrong. Case.init_args_check(..., machine=machine, ...) at case.py:147-165 validates the raw argument, and the `machine or self.cime.machine` fallback is applied only later, at case.py:178. The None check at case.py:356 was meant for the result of that fallback. That result can never be None, because visualCaseGen always sets cime.machine to the detected machine or to "CESM_NOT_PORTED".

**Smallest fix.** In Case.__init__, right after `self.cime = initialize_visualCaseGen(cesmroot)` (case.py:138), resolve `machine = machine or self.cime.machine`. That resolved value then flows into init_args_check, so the project_required check also uses it, and line 178 can become `self.machine = machine`. State serialization already excludes the raw machine from _init_args (case_state.py:39) and writes self.machine (case.py:1086), so nothing else needs to change. Optionally reword the error message. If machine detection should not be supported at all, the alternative is to make machine a required argument and drop the dead fallback and the misleading docstring.

### C15. GLOFAS.get_global_data_with_python saves a zip archive as glofas_data.nc and requests every year x month x day combination

- **Repo:** CrocoDash
- **Severity:** wrong result
- **Evidence:** from reading (verifier), then confirmed by repro (second check) (audit id `raw_data-a5`)
- **Confidence:** high
- **Location:** CrocoDash/raw_data_access/datasets/glofas.py:52 (download_format 'zip'), CrocoDash/raw_data_access/datasets/glofas.py:56 (writes to the .nc name), CrocoDash/raw_data_access/datasets/glofas.py:39-41 (hyear/hmonth/hday built as sets)
- **Already fixed on main:** No (target is main). No open PR fixes it. The 1.1 branch drop-loose-access-args (issue #348, Q23) changes the signature to when: TimeRequest but keeps "download_format": "zip" and the set-based hyear/hmonth/hday unchanged.
- **Related:** #348 (Q23, Fetch ERA5 and GLOFAS by Region and TimeRequest): rewrites this method but carries both defects over. #242 (earlier Path() fix to the same line). tests/raw_data_access/test_dates_inclusive.py:31 allowlists this method with incorrect reasoning. tests/raw_data_access/test_glofas.py:16 (slow test only checks that the file exists).

**What's wrong.** get_global_data_with_python sends "download_format": "zip" but passes client.retrieve a target of Path(output_folder)/output_filename (default glofas_data.nc) and returns that path. The client writes the server's payload unchanged, so the returned ".nc" is a zip archive, and xr.open_dataset on it fails with xarray's generic "did not find a match in any of xarray's currently installed IO backends". The dates are expanded with pd.date_range and then reduced to three independent sorted sets (hyear, hmonth, hday). CDS/EWDS take the Cartesian product of these, so any window that crosses a month or year boundary pulls in days outside [start, end]. The docstring says "every day in the range is requested", which hides this. Examples: 2019-12-30..2020-01-02 (4 days) selects 16 days, including Jan 2019 and Dec 2020. 2020-01-30..02-02 (4 days) selects 6. 2020-01-15..03-15 (61 days) selects 91. A June-to-May year selects about 2 full years.

**Who hits it.** A user fetches raw GLOFAS discharge directly through the raw-data access API (not the forcing path, which uses the processed CESM inputdata file), e.g. GLOFAS.get_global_data_with_python(dates=['2019-12-30','2020-01-02'], output_folder=...) or ProductRegistry.get_access_function('glofas','get_global_data_with_python'), then opens the returned path with xarray. Any date window crossing a month boundary also gets extra days.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/raw_data-a5 && timeout 900 $PY -u repro_glofas.py. The script (dev/crocodash_1_0_x/audit_repros/verify/raw_data-a5/repro_glofas.py) replaces gl.cdsapi.Client with a FakeClient. Its retrieve() records the request, expands itertools.product(hyear, hmonth, hday) and drops invalid dates, then writes a zip containing a netCDF when download_format=='zip' (otherwise the bare netCDF), as the datastores do. It then calls GLOFAS.get_global_data_with_python(dates=window, output_folder=out) for three windows and runs xr.open_dataset on the returned path. No network is used.

- Expected: The returned path is a netCDF file that xarray can open, holding exactly the days from start to end inclusive (4 days for 2019-12-30..2020-01-02).
- Observed: Request captured from the audited code (no mocking of CrocoDash): "window ['2019-12-30', '2020-01-02']: hyear ['2019', '2020'] hmonth ['01', '12'] hday ['01', '02', '30', '31'] download_format zip; requested 4 days, request selects 16 days, 12 outside window (first few outside: ['2019-01-01', '2019-01-02', '2019-01-30', '2019-01-31'])". Also: "window ['2020-01-30','2020-02-02']: requested 4 days, request selects 6 days, 2 outside" and "window ['2020-01-15','2020-03-15']: requested 61 days, request selects 91 days, 30 outside". Returned path: .../out/glofas_2019-12-30.nc. With the server modelled as returning a zip for download_format='zip': "is zip archive: True" and "xr.open_dataset FAILED: ValueError: did not find a match in any of xarray's currently installed IO backends ['netcdf4', 'h5netcdf', 'scipy', 'zarr']". The installed ecmwf.datastores Results.download (processing.py:654-681) writes the asset bytes to the target unchanged, with no extraction.

**Second check (reproduced).** I found nothing that refutes it. The method has no caller anywhere in CrocoDash: configure_forcings/process_forcings never use it, and the gallery only demonstrates the _script_for_cli variant. Nothing unzips the download or trims its dates, and the only test (tests/raw_data_access/test_glofas.py:16, slow) asserts os.path.exists and nothing more. It is still a public, registered access method that users can reach with ProductRegistry.get_access_function('glofas','get_global_data_with_python'). The verifier faked cdsapi.Client. I did not: my repro runs the real installed stack (cdsapi 0.7.7, which dispatches to ecmwf.datastores LegacyClient 0.5.3) over real HTTP against a stub of the EWDS retrieve API on 127.0.0.1. CrocoDash and the client libraries are not patched. The stub models only two server behaviours I cannot check offline. First, download_format='zip' returns a zip archive; this is the field's documented meaning, and the installed ecmwf-datastores README uses 'unarchived' to get a raw file. Second, hyear x hmonth x hday is taken as a Cartesian product, which is the standard CDS/EWDS form semantics. The client writes the asset bytes unchanged to the target named .nc (bytes on disk == server bytes: True), so the returned path is a zip that xarray cannot open. The request the audited code sends is captured verbatim, and its date sets cover more days than the window whenever the window crosses a month boundary. Monkeypatching download_format='unarchived' makes the returned file open. Caveat on that fix: EWDS may still zip a multi-file result even with 'unarchived', so extracting the zip or checking zipfile.is_zipfile is the safer fix. Clipping to [start, end] is still needed either way. Severity 'wrong result' is fair and not inflated: the function returns a non-netCDF file under a .nc name, with up to about 2x the requested days. It does not crash itself, and the path is off the main forcing workflow. Observed: The client resolves to ecmwf.datastores.legacy_client (real cdsapi path). Output for window ['2019-12-30','2020-01-02']: "sent: hyear=['2019', '2020'] hmonth=['01', '12'] hday(len)=4 download_format='zip'", "bytes on disk == server asset bytes: True; is zip: True", "xr.open_dataset FAILED: ValueError: did not find a match in any of xarray's currently installed IO backends ['netcdf4', 'h5netcdf', 'scipy', 'zarr']". After a manual unzip: "4 days requested, file holds 16 days, 12 outside; first outside ['2019-01-01', '2019-01-02', '2019-01-30', '2019-01-31']". Window ['2020-01-30','2020-02-02']: 4 requested, 6 held, 2 outside (2020-01-01, 2020-01-02). Window ['2020-06-01','2021-05-31']: hmonth = all 12 months, hday = 31 values, 365 requested, 731 held, 366 outside. With download_format monkeypatched to 'unarchived', the same call gives "xr.open_dataset OK, days: 3". Source lines: CrocoDash/raw_data_access/datasets/glofas.py:39-41 (independent sets), :52 ("download_format": "zip"), :56-58 (target <output_folder>/glofas_data.nc, path returned).

**Root cause.** The request dict was copied from the EWDS web form, which defaults to a zip download, and it is paired with a .nc target name. The per-day dates are collapsed into three independent sets (glofas.py:39-41), which the API combines as a Cartesian product, not as the list of requested days.

**Live-service check (added by hand, 2026-11-06 late).** The verifier used a local stub. Against the real EWDS, `get_global_data_with_python` now fails before any of the above: every request is rejected with `400 Bad Request … Request has not produced a valid combination of values`, even a single day (`audit_repros/extra/glofas_live.py`, `glofas_live1.py`). The service log says why: "[2026-07-30] Due to changes in the data structure of the cems-glofas-historical dataset, previous API requests may no longer work." The current schema (`/api/retrieve/v1/processes/cems-glofas-historical`) wants:
- `year`/`month`/`day` instead of `hyear`/`hmonth`/`hday`;
- the variable `average_river_discharge_in_the_last_24_hours`;
- a `timespan` key, and offers `version_5_0` too.

A request with those keys, `timespan: ["time_mean"]` and `download_format: "unarchived"` succeeds and returns plain netCDF with `avg_dis` (m³ s⁻¹) (`glofas_fixed.py`). It also accepts `area`, so the global download isn't needed. The request is the same on main and on the 1.1 branch `drop-loose-access-args` (#348). So severity is now crash: the method can't fetch anything.

**Smallest fix.** Move the request to the current schema (keys above, plus `area` from the domain). Then: set "download_format": "unarchived" (a single netCDF file is then written as-is to the .nc target), or keep 'zip' but extract the .nc into output_folder and return the extracted path. For dates, after download open the file and select the time coordinate to [start, end], then rewrite it. The alternative is one request per (year, month) with only that month's requested days, then merge. Remove ('glofas', 'get_global_data_with_python') from KNOWN_INCLUSIVE_WITHOUT_HELPER, or correct its comment, in tests/raw_data_access/test_dates_inclusive.py:31.

### CrocoDash: lower severity (misleading errors), confirmed

Same evidence standard as above, written up briefly. Full fields are in the verifier results (see *Sources* at the top).

- **C-short-1.** **configure_forcings accepts a date_range whose end is not after its start: writes STOP_N <= 0, then fails late with errors that do not mention the dates** (misleading error; confirmed by repro; `configure_process-a7`). CrocoDash/case.py:586 (no ordering check after the shape checks at 574-580); STOP_N written at CrocoDash/case.py:684-688; same gap in CrocoDash/recipe.py:67-71 for YAML/CLI/MCP. configure_forcings checks only that date_range is a list of two strings. It never checks that the end comes after the start. A reversed range is written to the case as RUN_STARTDATE=<the later date> and STOP_N=-4. A range with the same start and end gets STOP_N=0, and so does any range shorter than one day, because .days truncates. In both cases configure_forcings succeeds. With a reversed range, process_forcings asks the OBC GET phase for "2020-01-05 → 2020-01-01" and then fails in obc.py:205 with "No files for [south] — preceding phase produced no output.", which does not mention the dates. With equal dates, process_forcings succeeds. The error only shows up when CESM runs, after a build and a queue wait: alarmInit in share/src/nuopc_shr_methods.F90:575-576 aborts with "invalid opt_n" for STOP_N <= 0. The YAML/CLI path has the same gap (recipe.py validate_config checks only the length). *Fix:* In configure_forcings, right after `self.date_range = pd.to_datetime(date_range)` (case.py:586) and before any state is set or written: `if (self.date_range[1] - self.date_range[0]).days < 1: raise ValueError(f"date_range end ({date_range[1]}) must be at least one day after its start ({date_range[0]})")`. Checking whole days, not just end <= start, also catches same-day ranges that would give STOP_N=0. Optionally add the same check in recipe.validate_config so YAML/CLI configs fail early. *Repro:* source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/configure_process-a7 && timeout 900 $PY -u repro.py $PWD "2020-01-05 00:00:00" "2020-01-01 00:00:00" audit_a7v_swap   (and again with "2020-01-01 00:00:00" "2020-01-01 00:00:00" audit_a7v_same). Script dev/crocodash_1_0_x/audit_repros/verify/configure_process-a7/repro.py: Grid(lenx=4, leny=4, resolution=0.5), flat Topo, VGrid.uniform(nk=10); Case(compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV", ...); case.configure_forcings(date_range=dr, product_name="reference_ocean", function_name="get_reference_ocean_data"); it parses STOP_N from env_run.xml, then runs case.process_forcings(). Logs: swap.log and same.log in the same directory. *Fixed on main:* No (target is main; origin/main == b8991c89 has no ordering check). Open PR #326 moves the STOP_N xmlchange ahead of the configurators (DATM/Runoff then read it via xmlquery), but it keeps the uncheck *Related:* PR #326 (moves the RUN_STARTDATE/STOP_N writes); issue #335 / 1.1 queue TimeRequest work (SPACE_TIME.md), which will replace the date handling but has no ordering check in this release; TRIAGE A#7 / issue #213 (stale _cime_case STOP_N), not the same bug
- **C-short-2.** **configure_forcings accepts tidal_constituents="M2" as a string and writes OBC_TIDE_CONSTITUENTS = "M, 2" (no validation, despite the documented TypeError)** (misleading error; confirmed by repro; `configure_process-a8`). CrocoDash/forcing/tides.py:96 and CrocoDash/forcing/tides.py:100 (TidesConfigurator, class at line 9, has no validate_args; __init__ at 56-81). The broken promise is at CrocoDash/case.py:529-530.. The configure_forcings docstring says it raises a TypeError when tidal_constituents is not a list of strings, but nothing checks this. BaseConfigurator.validate_args only compares argument names, and TidesConfigurator does not override it. So a plain string such as "M2" is accepted and stored as is. configure() then calls len() and ", ".join() on it, which treats it character by character, and writes OBC_TIDE_N_CONSTITUENTS = 2 and OBC_TIDE_CONSTITUENTS = "M, 2" into the case's user_nl_mom. config.json keeps the string. The mistake only shows up at process_forcings time, when regional-mom6's TPXO lookup raises "ValueError: Invalid tidal constituent: M", which does not point back at the configure_forcings argument. Unsupported or lowercase names (e.g. "M4", "m2") pass the same way and also fail only at process time. *Fix:* Override validate_args in TidesConfigurator: call super().validate_args(**kwargs), then require tidal_constituents to be a non-empty list or tuple of str. Raise TypeError otherwise, or wrap a lone str into [str] if that is preferred. Also check each name against the TPXO-supported set (M2, S2, N2, K2, K1, O1, P1, Q1, MM, MF) and raise ValueError on unknown ones, so the error comes at configure time. Keep in mind that BaseConfigurator.inspect() builds configurators with "" placeholders, so the check must allow that path, or inspect must skip it. *Repro:* source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/configure_process-a8 && timeout 900 $PY -u repro.py > repro.log 2>&1. The script (repro.py there) builds a 4x4 deg, 0.5 deg grid with flat 1000 m topo, a 10-level VGrid and the NYF compset, as case audit_cpa8_1. It creates two empty dummy TPXO files, then calls case.configure_forcings(date_range=["2020-01-01 00:00:00","2020-01-05 00:00:00"], product_name="reference_ocean", function_name="get_reference_ocean_data", tidal_constituents=TC, tpxo_elevation_filepath=..., tpxo_velocity_filepath=...) twice on the same case, with TC="M2" and then TC=["M2"], and prints the OBC_TIDE_* lines of user_nl_mom after each call. Finally it calls regional_mom6.regional_mom6.convert_to_tpxo_tidal_constituents("M2"), which is what process_tides reaches with the stored value. *Fixed on main:* No (target is main; the worktree HEAD equals origin/main b8991c8, and no open CrocoDash PR changes forcing/tides.py) *Related:* Loosely related to 1.1 queue item Q9 (forcing-param-specs: ParamSpec choices and the tides comment fix). Not the same as CrocoDash #344 (empty body, "OBC Tide Params are Changing!") or #133 (non-TPXO tidal data).
- **C-short-3.** **CESM tseries readers return normally when requested variables have no files; IC/OBC then fail with an unrelated error, and a partial raw file is reused after the archive is fixed** (misleading error; confirmed by repro; `raw_data-a4`). CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:666 (subset_dataset skips a variable with no files), CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:449-457 (read_single_variable_tseries_data merges what exists, or skips the merge), CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:255 (get_mom6_output_data only warns), CrocoDash/forcing/utils.py:145-157 (fetch_raw_chunk ignores the result; its skip check at :137-143 reuses any valid NetCDF). Three readers can find no files for a requested variable and still return normally: CESM_POP_OUTPUT.get_cesm_single_variable_data, CESM_MOM_OUTPUT.get_mom6_single_variable_data (both through read_single_variable_tseries_data and subset_dataset) and CESM_MOM_OUTPUT.get_mom6_output_data. When a variable has no files they only print "0 file(s) found" / "No files found for variable: X" (or log a warning in get_mom6_output_data). If no variable matches, they print "No subset files to merge into <output>; skipping merge." and write no output file. If some variables match, they merge only those into the raw file. fetch_raw_chunk ignores the return value and does not check that the file was written, so the IC/OBC step fails later with a message that does not name the cause. A raw file missing variables is also a valid NetCDF, so on a rerun fetch_raw_chunk skips the fetch ("already exists. Skipping.") and keeps failing even after the user fixes the archive. *Fix:* In read_single_variable_tseries_data, right after the member filter (cesm_ocean_output.py:~398), compute missing = [v for v, f in variable_info.items() if not f]. If missing is non-empty, raise FileNotFoundError naming missing, dataset_path, member, the start/end dates and regex. This runs before anything is subset or merged, so no partial raw file is written. In get_mom6_output_data (:255), raise instead of logger.warning. As a backstop, have fetch_raw_chunk (utils.py:~157) raise if output_file does not exist after data_access_fn returns. Users who already have a partial raw file still need to delete it once. *Repro:* source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/raw_data-a4 && timeout 900 $PY -u v_e2e.py a (likewise "b"), then timeout 900 $PY -u v_e2e2.py c (likewise "d"). Scripts: dev/crocodash_1_0_x/audit_repros/verify/raw_data-a4/v_e2e.py and dev/crocodash_1_0_x/audit_repros/verify/raw_data-a4/v_e2e2.py. Setup: a synthetic POP archive with one file per variable, named g.e22.test.pop.h.<VAR>.200001-200012.nc (TLAT/TLONG, z_t, noleap monthly time), and a 4x4 deg, 0.5 deg Grid at (-60, 30). The case is Case(..., compset=1850_DATM%NYF_..._MOM6%REGIONAL_...); then case.configure_forcings(date_range=[...], product_name="CESM_POP_OUTPUT", function_name="get_cesm_single_variable_data", function_overrides={"dataset_path": str(archive)}) and case.process_forcings(). Scenarios: (a) dates 2005-01-01..03; (b) SSH files absent, dates 2000-03-01..03; (c) as (a) but process_ic=False; (d) as (b), then the SSH file is copied into the archive and process_forcings(process_bc=False) is rerun on the same case. *Fixed on main:* No (target is main). No open PR fixes it. The 1.1 branches time-request (#335), cesm-cice-ww3jra-windows (#347) and time-sampling (#327) still have the same 'No files found for variable' / 'No subset  *Related:* #353 / TRIAGE item 1 (CESM output time not cut to the window; a different bug in the same readers); #347 / Q22 (a YYYYMM file end read as the 1st of the month gives 0 matches late in a month, which triggers this); #335 / Q5 (configure-time date-coverage check; does not cover missing variables); #327
- **C-short-4.** **configure_forcings: unknown product or access method gives "Product / Data Path is not supported quite yet" or a bare KeyError, with no list of valid choices** (misleading error; confirmed by repro; `raw_data-a7`). CrocoDash/case.py:593 (product check, lines 589-593), CrocoDash/case.py:596 (call), CrocoDash/raw_data_access/registry.py:75 (bare dict lookup), CrocoDash/case.py:494 (default function_name). case.configure_forcings checks product_name itself (case.py:589-593). Two kinds of bad name both raise ValueError("Product / Data Path is not supported quite yet"), with no list of valid products: a misspelled name, and a registered product that is not a ForcingProduct (e.g. 'gebco'). ConditionsConfigurator.validate_args (forcing/mom6.py:530-534) has an "Unknown forcing product ... Known products: [...]" message, but that branch is dead because case.py rejects unknown products first. Its MOM6ForcingProduct type check is still reached, e.g. for WW3/CICE products. function_name is never checked against the product's access methods. ProductRegistry.get_function_default_args (registry.py:75) does product._access_methods[function_name], so a wrong name raises a bare KeyError that only repeats the name, e.g. KeyError: 'get_glorys_data_from_rdaa'. The default function_name is 'get_glorys_data_script_for_cli' (case.py:494). So the most likely trigger is a user who changes product_name to any non-GLORYS product (reference_ocean, cesm_pop_output, ...) and leaves function_name at its default. They get KeyError: 'get_glorys_data_script_for_cli', which does not say the function name is wrong for that product. recipe.py:206 calls the same registry method. *Fix:* 1) registry.py get_function_default_args: before line 75, add `if function_name not in product._access_methods: raise ValueError(f"{function_name!r} is not an access method of {product.product_name}; choose one of {sorted(product._access_methods)}")`. This also covers recipe.py:206. 2) case.py:589-593: replace the vague message with `ValueError(f"Unknown forcing product {product_name!r}; forcing products: {sorted(n for n, c in ProductRegistry.products.items() if issubclass(c, ForcingProduct))}")`. Alternatively, drop the case.py check and let ConditionsConfigurator.validate_args report it, but that needs the function-args lookup moved after configurator validation. A docstring or error hint that function_name must match the product (the default is GLORYS-only) would also help. *Repro:* source dev/crocodash_1_0_x/audit_repros/env.sh && cd dev/crocodash_1_0_x/audit_repros/verify/raw_data-a7 && timeout 900 $PY -u repro.py $PWD   (script: dev/crocodash_1_0_x/audit_repros/verify/raw_data-a7/repro.py; log: run.log in the same dir). It builds a 4x4-degree 0.5-degree flat Grid/Topo/VGrid(10) Case audit_rd_a7_1 (NYF compset, derecho). It then calls case.configure_forcings(date_range=["2020-01-01 00:00:00","2020-01-05 00:00:00"], **kw) for kw in: {product_name:'glorys12', function_name:'get_glorys_data_from_rda'}, {product_name:'gebco', function_name:'get_gebco_data_script'}, {product_name:'GLORYS', function_name:'get_glorys_data_from_rdaa'}, {product_name:'reference_ocean'}, {product_name:'reference_waves', function_name:'get_reference_wave_spectra'}. Last, a valid reference_ocean call shows the case itself is fine. *Fixed on main:* No (the target is main b8991c89). No open PR or remote branch fixes it: every remote branch except gh-pages and Jofia_Pacific_Cold_Tongue keeps the "not supported quite yet" message, and none adds a f *Related:* #330 (1.1, describe each configure_forcings argument once: related, does not fix it); #341 (1.1, ask for the forcings when creating or configuring); #286 (another unclear-error issue, different cause); no TRIAGE item
- **C-short-5.** **Case() accepts an ocn_topo built on a different Grid than ocn_grid; the failure only shows up later (process_forcings or MOM6 start) and never names the mismatch** (misleading error; confirmed by repro; `vcg-a5`). CrocoDash/case.py:333 (init_args_check, only an isinstance check); CrocoDash/case.py:394-421 (_create_grid_input_files: supergrid from ocn_grid, but topo/SCRIP/ESMF mesh/CICE grid/WW3 inputs from ocn_topo's own grid); CrocoDash/case.py:942-943 (OCN_NX/OCN_NY from ocn_grid). init_args_check validates ocn_topo only with isinstance(ocn_topo, Topo). A Topo carries its own grid (Topo._grid), and nothing checks that it matches ocn_grid. Several files then come from two different grids. From ocn_grid: OCN_NX/OCN_NY, NIGLOBAL/NJGLOBAL, the MOM6 supergrid, the rm6 experiment's hgrid and the forcings. From the topo's own grid: the topography file, the SCRIP grid, the ESMF mesh (OCN_DOMAIN_MESH), the CICE grid and the WW3 inputs (also the WW3 time steps and the PE-tier ocean point count). Case() succeeds either way. If the shapes differ, process_forcings later fails with an AssertionError about geolat/geolon in the topog file. If the shapes match but the coordinates differ, CrocoDash reports "Case is ready to be built", and the run aborts at MOM6 initialization once built and queued, because the mesh and grid coordinates differ. *Fix:* In Case.init_args_check, after the isinstance check (case.py:333), add:
  tg = ocn_topo._grid
  if tg is not ocn_grid and not ((tg.ny, tg.nx) == (ocn_grid.ny, ocn_grid.nx) and np.allclose(tg.tlon, ocn_grid.tlon) and np.allclose(tg.tlat, ocn_grid.tlat)):
      raise ValueError("ocn_topo was built on a different grid than ocn_grid; rebuild the Topo on ocn_grid.")
A standalone check (check_fix.py in the same dir) accepts the same object and an identical re-created Grid, and rejects both the finer and the shifted grid. A shape-only check (the finder's proposal) would miss the same-shape shifted case. *Repro:* source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a5 && timeout 900 $PY -u repro.py res ; timeout 900 $PY -u repro.py shift *Fixed on main:* No. The target is main, and origin/main = b8991c89 has only the isinstance check at case.py:333. No open CrocoDash PR adds this check. *Related:* TRIAGE A#4 / CrocoDash #286 (same class: init_args_check misses a consistency check, so the error comes later and is unclear). 1.1 Q19 / #343 (branch yaml-grid-paths): the YAML config will name ocn_grid and ocn_topo files separately, and read_grids() loads them with Topo.from_topo_file. That path al
- **C-short-6.** **configure_forcings() on an earlier case raises a bare TypeError/KeyError instead of the guard's RuntimeError after a later Case() call fails** (misleading error; confirmed by repro; `vcg-a7`). CrocoDash/case.py:623. The multi-case guard in Case.configure_forcings (case.py:623, `active_caseroot = Path(cvars["CASEROOT"].value)`) assumes visualCaseGen's global cvars always holds a CASEROOT string. Case.__init__ resets that global state first: initialize_visualCaseGen(cesmroot) at case.py:138 runs ConfigVar.reboot (visualCaseGen/initialize.py:31), which pops every cvar. It does this before Case.init_args_check (case.py:147) and before _configure_launch sets CASEROOT (case.py:1060). So when a second Case() fails, it leaves CASEROOT in one of two states:
- None, if the failure is in argument validation or in _configure_case before the launch stage.
- Missing entirely, if the failure is inside initialize_visualCaseGen, e.g. a bad cesmroot.

After that, configure_forcings() on the earlier, valid case crashes inside the guard with a bare `TypeError: expected str, bytes or os.PathLike object, not NoneType` or `KeyError: 'CASEROOT'`. The docstring promises a RuntimeError that explains the case can no longer be configured in this session. Rerunning configure_forcings on that case, which the docs say is supported, fails the same way. *Fix:* In case.py:623, replace the dereference with a check that tolerates a None or missing CASEROOT:

    active = cvars["CASEROOT"].value if "CASEROOT" in cvars else None
    if active is None or Path(active) != self.caseroot:
        raise RuntimeError(
            f"configure_forcings() was called on {self.caseroot.name}, but a later Case() call in this session "
            "(even one that failed) reset visualCaseGen's global state, and the namelist and xml changes "
            "would not go into this case. Call configure_forcings() on each case right after creating it.")

Keep the existing message, which names the other case, for the case where `active` is set to a different caseroot. The wording "even one that failed" also covers a later Case() that failed after CASEROOT was set, e.g. in create_newcase. The current message then says that case "was created after it", although the failed attempt's directories were removed. *Repro:* source dev/crocodash_1_0_x/audit_repros/env.sh && cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a7 && timeout 900 $PY -u repro.py *Fixed on main:* No (target is main). Open draft PR #326 (1.1 queue item Q2, waiting on ESMCI #52 and CDEPS#3) deletes the CASEROOT guard and writes user_nl/xml changes into each case's own caseroot, which would remov *Related:* #250 (configure on several cases; TRIAGE says main handles it with this guard), #326 / 1.1 Q2 (writes-name-caseroot, removes the guard)
- **C-short-7.** **A grid named after a CESM grid (e.g. tx2_3v2) is refused with a false "previous case was deleted" reason, and the advised override=True builds a regional case on that global grid's MOM6 defaults** (misleading error; confirmed by repro; `vcg-a10`). CrocoDash/case.py:348. init_args_check refuses an ocn_grid whose name is in cime.domains["ocnice"] unless override=True (case.py:348-353). The message says this "happens when a previous case with this grid was deleted without using override=True" and tells the user to pass override=True. But CrocoDash creates cases with add_grids_to_ccs_config=False (case.py:479-481), so it never registers a grid in ccs_config. For a CrocoDash user, the check can only fire when the name matches one of CESM's own grids (tx2_3v2, tx2_3v3, tx0.25v1, tx1v1, gx1v7, gx3v7, ...), or a name left in ccs_config by pre-#252 CrocoDash or by the vCG GUI. The reason given is false, and the advice is harmful. With override=True the check is skipped and visualCaseGen runs `xmlchange OCN_GRID=<name>`. MOM_interface's MOM_input.yaml and input_data_list.yaml key their defaults on OCN_GRID, so the regional case silently gets the global grid's physics and file settings. CrocoDash's user_nl_mom only overrides grid/topo/vgrid, NIGLOBAL/NJGLOBAL, TRIPOLAR_N, DT, IC and OBC. Anyone who already passes override=True, as the tutorials do, gets no message at all. *Fix:* In init_args_check (case.py:348), drop `and not override` and replace the message with something like: f"ocn_grid name '{ocn_grid.name}' is already a CESM grid name; MOM6 picks defaults by grid name, so choose a different name." A name left in ccs_config by older CrocoDash or the vCG GUI would also be refused, which is fine, since renaming the grid is trivial. *Repro:* source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a10 *Fixed on main:* No (target is main). No open CrocoDash or visualCaseGen PR touches this check. *Related:* none. History: e34cbac6 (#223) wrote the message, and 0cf5efee (#252/#215) switched to add_grids_to_ccs_config=False. The 1.1 item Q19 (yaml-grid-paths, grid name read from the grid files) changes how names are set but does not fix this.

## regional-mom6

CROCODILE-CESM/regional-mom6, the fork pinned at CrocoDash/rm6 (3ca8b9b). File on the fork, not on COSIMA. **R1 contradicts TRIAGE.md section B:** regional-mom6 #15 (tides across the seam) is *not* fixed on the pin. Keep #15 open and add R1's repro to it, rather than closing it or opening a new issue.

### R1. Tidal OBCs come out as zero on an east/west boundary within 1/6 deg of 0 deg longitude: TPXO regridders are non-periodic and TPXO is (nx, ny)-ordered

- **Repo:** regional-mom6
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `rm6-a2`)
- **Confidence:** high
- **Location:** CrocoDash/rm6/regional_mom6/segment.py:1147 (also 1155, 1163: the three rgd.create_regridder calls in Segment.regrid_tides, all without periodic); CrocoDash/rm6/regional_mom6/regional_mom6.py:122-151 (prepare_tpxo_tidal_forcing leaves TPXO in (nc, nx, ny) order); CrocoDash/rm6/regional_mom6/regridding.py:109 (periodic=False default) and :522 (fillna(0) when segment.mask is None); reached from CrocoDash/forcing/tides.py:143
- **Already fixed on main:** No. The rm6 origin/main (e349363, 7 commits ahead of the pin 3ca8b9b) changes regional_mom6.py only in the IC/npes/vgrid code. segment.py and regridding.py are unchanged. There is no periodic= or TPXO transpose in the tides path there, and no open rm6 PR touches tides.
- **Related:** regional-mom6 #15 (open, same trigger, older slicing mechanism). TRIAGE.md section B lists #15 as "likely fixed, confirm with a tides case across 0 deg then close". This repro shows it is not fixed, so keep #15 open and add these details there rather than opening a new issue. Also CrocoDash/forcing/tides.py:143: no bathymetry_path is passed, so the mask is None and every NaN is filled with 0. No 1.1 queue item covers tides.

**What's wrong.** Segment.regrid_tides builds its elevation, u and v xESMF regridders from the global TPXO fields with periodic=False, and create_regridder sets unmapped_to_nan=True. The TPXO9.v1 longitude ranges are: h (lon_z) 0.1667..360.0, u (lon_u) 0.0833..359.9167, v (lon_v) 0.1667..360.0. Each grid therefore has a 1/6 deg gap at the 0/360 seam, and segment points inside a gap come back NaN. fill_missing_data only ffills/bfills along the segment, so an east or west segment entirely inside a gap stays all-NaN. ap2ep mixes u and v, so a NaN in either one makes uamp, vamp, uphase and vphase all NaN. CrocoDash passes no bathymetry, so mask_dataset then replaces every NaN with 0. Results:
- East/west boundary at a lon in (359.917, 0.167): zero tidal velocity along its whole length.
- East/west boundary at a lon in (0, 0.167): zero tidal elevation too.
- Exactly lon 0.0: velocities zero, elevation fine.
The only message is "All NaNs filled b/c no ocean/land mask was available", and it is printed for every boundary, healthy ones included, so it gives no signal. North/south boundaries crossing 0 deg get the gap points copied from the nearest mapped neighbour. That error is small: up to ~0.016 m on a 0.3 m-varying field.

**Who hits it.** Any CrocoDash case with tides (configure_forcings(..., tpxo_elevation_filepath=..., tpxo_velocity_filepath=..., tidal_constituents=[...]) then process_forcings) whose west or east open boundary lies within about 1/6 deg of the prime meridian. Examples: Grid(xstart=0.0, ...), xstart=0.1, or a domain whose east edge ends at 0 deg. Longitude convention does not matter: -0.05 and 359.95 behave the same.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh
cd dev/crocodash_1_0_x/audit_repros/verify/rm6-a2

(1) Full CrocoDash flow:
  $PY gen_tpxo.py tpxo   # synthetic TPXO9.v1-shaped (nx, ny) files; uniform ha=0.5 m, ua=10 cm/s, va=6 cm/s
  timeout 900 $PY -u case_tides.py x0p1 0.1
  case_tides.py does:
    Grid(lenx=1.0, leny=1.0, resolution=0.1, xstart=0.1, ystart=-4.0)
    Topo.set_flat(1000)
    Case(..., compset 1850_DATM%NYF_..._MOM6%REGIONAL_...)
    case.configure_forcings(date_range=[2020-01-01, 2020-01-03], product_name="reference_ocean", function_name="get_reference_ocean_data", tpxo_elevation_filepath=tpxo/h_synth.nc, tpxo_velocity_filepath=tpxo/u_synth.nc, tidal_constituents=["M2"])
    case.process_forcings()
    then reads ocn/tu_*.nc and ocn/tz_*.nc

(2) rm6-level band scan plus fix check (smooth lon-varying synthetic data, analytic expected values):
  $PY gen_tpxo_var.py tpxo_var
  timeout 900 $PY -u scan.py -0.1 0.0 0.05 0.1 0.15 0.2 1.0
  timeout 900 $PY -u south.py

- Expected: With uniform TPXO input, every boundary should get zamp=0.5 m, uamp=0.10 m/s and vamp=0.06 m/s. With smoothly varying input, the values should be interpolated across the seam (for example zamp at lon 0.10 = 0.5157), exactly as at any other longitude.
- Observed: (1) Full CrocoDash flow, west edge at lon 0.1:
  tu_segment_003.nc: lon 0.100..0.100 | uamp min=0.0000 max=0.0000 zeros=21/21 | vamp min=0.0000 max=0.0000 zeros=21/21 | zamp min=0.0000 max=0.0000 zeros=21/21
  tu_segment_004.nc: lon 1.100..1.100 | uamp min=0.1000 max=0.1000 zeros=0/21 | vamp min=0.0600 ... | zamp min=0.5000 ...
  South and north were also correct. The log only shows the generic "All NaNs filled b/c no ocean/land mask was available" warning, printed for all four boundaries.

(2) Pinned code, west boundary:
  lon -0.10: correct (zamp 0.4843, uamp 0.0984)
  lon -0.05: uamp zeros 21/21
  lon 0.00: zamp 0.5000 (ok), but uamp 0.0000 (exp 0.1000) and vamp 0.0000 (exp 0.0800), zeros 21/21
  lon 0.05, 0.10, 0.15: zamp 0.0000 (exp 0.5079/0.5157/0.5235), uamp 0 and vamp 0, all 21/21
  lon 0.20 and 1.00: correct
  With periodic=True alone, the output is identical to pinned at every longitude.
  With TPXO transposed to (constituent, ny, nx) plus periodic=True, every point matches the analytic value (lon 0.10: zamp 0.5157, uamp 0.1016), and lon 1.00 is unchanged (0.6500/0.1150/0.0773).

South segment crossing 0 (pinned): gap points copy their neighbour. For example, at lon 0.05 zamp is 0.5000 (exp 0.5079), and at lon 359.95 uamp is 0.0984 (exp 0.0992).

**Root cause.** The tidal regridders have no periodicity across TPXO's 0/360 seam. create_regridder defaults to periodic=False and regrid_tides never overrides it, so ESMF leaves points between the last and first TPXO columns unmapped (NaN). Two downstream steps turn this into zeros. First, fill_missing_data can only fill along the segment, so a north/south-running (east/west) segment that sits entirely in the gap stays all-NaN. Second, mask_dataset with no mask fills NaN with 0 (CrocoDash/forcing/tides.py never passes bathymetry_path). Passing periodic=True alone does not help: prepare_tpxo_tidal_forcing keeps TPXO's native (nx, ny) ordering, and xESMF assumes the last horizontal dim is x and makes the ESMF dim built from it periodic, i.e. latitude here (verified: periodic-only output is identical to pinned). This is the remaining form of regional-mom6 #15. The slicing problem that issue describes is gone, but the seam gap remains.

**Smallest fix.** 1. In prepare_tpxo_tidal_forcing (regional_mom6.py:122-149), transpose each of tpxo_h, tpxo_u and tpxo_v to ("constituent", "ny", "nx") after the rename/isel.
2. In Segment.regrid_tides (segment.py:1147, 1155, 1163), pass periodic=True to the three rgd.create_regridder calls.

Verified by monkeypatch in scan.py: correct values across the seam, and unchanged output away from it. Optionally, also raise or log a specific warning when a tidal segment is entirely NaN after regridding, instead of silently zero-filling it.

### R2. GLORYS CLI download script breaks when the inputdir path contains a space (-o path is not quoted)

- **Repo:** regional-mom6
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `raw_data-a6`)
- **Confidence:** high
- **Location:** CrocoDash/rm6/regional_mom6/regional_mom6.py:213
- **Already fixed on main:** No. regional-mom6 origin/main e349363 still has the unquoted `-o {str(path)} -f {segment_name}.nc` at regional_mom6.py:213, and none of the 7 commits ahead of the pin (3ca8b9b) touch it. The 1.1 Q21 branch (CrocoDash #346) reimplements the line in CrocoDash, also unquoted.
- **Related:** CrocoDash #356 (TRIAGE A9, GLORYS CLI script takes three rounds; same flow, different bug). 1.1 Q21 / #346 (glorys-reference-requests) rewrites this script generator and keeps it unquoted. Separate bug seen in the same repro, not part of this finding: on main the generated script keeps only the last request. glorys.py:166 checks for get_glorys_data.sh, but rm6 writes get_glorys_data.pbs, so modify_existing is always False and each call overwrites the file. My run's script had one copernicusmarine line (east) after all four boundaries were requested. Q21's acceptance check "Two CLI calls keep both requests" covers this on 1.1; it is not in TRIAGE for 1.0.x.

**What's wrong.** rm6.get_glorys_data builds each copernicusmarine command with an f-string ending in `-o {str(path)} -f {segment_name}.nc`, with no shell quoting. CrocoDash's default access method, GLORYS.get_glorys_data_script_for_cli (CrocoDash/raw_data_access/datasets/glorys.py:168), calls it with output_folder = <inputdir>/extract_forcings/raw_data. When the inputdir path contains a space, bash splits the -o value. copernicusmarine then receives a truncated output directory plus a stray positional argument and exits with a usage error, so no request in the script downloads anything.

**Who hits it.** Create a CrocoDash Case whose inputdir path contains a space (for example '~/My Cases/run1', which is common on laptops). Call configure_forcings() with its defaults (product_name="GLORYS", function_name="get_glorys_data_script_for_cli", case.py:493-494), then process_forcings(), then run the generated get_glorys_data script as instructed.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; D=dev/crocodash_1_0_x/audit_repros/verify/raw_data-a6; cd $D && timeout 900 $PY -u repro.py $D && timeout 300 $PY -u parse_cli.py "$D/my inputs/audit_rda6_1/extract_forcings/raw_data/get_glorys_data.pbs"
Key lines of repro.py:
  inputdir = S / "my inputs" / "audit_rda6_1"   # caseroot has no space
  Case(..., caseroot=S/"cases"/"audit_rda6_1", inputdir=inputdir, compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV", 2x2 deg grid at 0.5 deg, flat topo, 5 levels, override=True)
  case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"])   # defaults: GLORYS + get_glorys_data_script_for_cli
  case.process_forcings()   # writes the script, then raises FileNotFoundError as expected because nothing is downloaded yet
parse_cli.py runs the generated line once through bash with copernicusmarine stubbed to print its args, and once through the real copernicusmarine CLI with network blocked by a dead proxy (it fails at argument parsing, before any network call).

- Expected: The script passes the output directory as one argument, i.e. `-o '/.../my inputs/audit_rda6_1/extract_forcings/raw_data'`, and copernicusmarine parses the command.
- Observed: The script line ends `-o /.../raw_data-a6/my inputs/audit_rda6_1/extract_forcings/raw_data -f east_unprocessed.2020-01-01_2020-01-03.nc`. Bash word-splitting gives `-o = [/.../raw_data-a6/my]` and `stray positional = [inputs/audit_rda6_1/extract_forcings/raw_data]`. The real copernicusmarine 2.0.1 exits 2 with: "Usage: copernicusmarine subset [OPTIONS] ... Error: Got unexpected extra argument (inputs/audit_rda6_1/extract_forcings/raw_data)". After applying shlex.quote to -o and -f (monkeypatched line), it parses to `-o = [/.../my inputs/audit_rda6_1/extract_forcings/raw_data]` and `-f = [east_unprocessed...nc]`.

**Root cause.** regional_mom6.py:213 puts str(path) and segment_name into a shell command line through an f-string without shlex.quote, so any whitespace (or other shell metacharacter) in the output folder breaks the command. The bug is the same on rm6 origin/main (e349363, same line 213). The 1.1 rewrite (Q21, CrocoDash #346, branch glorys-reference-requests) moves the line into CrocoDash glorys.py as `f" -o {output_folder} -f {output_filename}"`, still unquoted.

**Smallest fix.** In rm6 get_glorys_data, add `import shlex` and write `-o {shlex.quote(str(path))} -f {shlex.quote(segment_name + '.nc')}`. Apply the same quoting to the Q21 version in CrocoDash glorys.py. Note that this alone may not make spaced inputdirs usable end to end: the inputdir also lands unquoted in env_run.xml mesh paths (OCN/ICE/WAV_DOMAIN_MESH, MASK_MESH, which go to nuopc.runconfig) and in user_nl_mom INPUTDIR. Whether the CESM run breaks there is not verified, since it needs a build and run. CrocoDash's init_args_check may also want to refuse whitespace in inputdir with a clear error.

## mom6_forge

NCAR/mom6_forge, pinned at CrocoDash/visualCaseGen/external/mom6_forge (d74c851 = 0.9.3). None of the 12 is fixed on mom6_forge main (83d7692), so a pin bump alone fixes none of them. Paths are worktree paths; on mom6_forge main #155 renamed some file readers (e.g. from_supergrid -> from_supergrid_file), and line numbers moved by a few lines.

### M1. Runoff map: the map_overlap mask in generate_ESMF_map_via_xesmf fails for domains that cross 0° longitude, have an edge at 0°, or cross the equator, so the domain receives runoff from the whole latitude band or longitude column

- **Repo:** mom6_forge
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `mom6_forge-a1`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:643-659 (643-644 normalize destination lon and lat, 645-646 min/max, 649-650 normalize source lon and lat, 652-659 mask). Reached via CrocoDash/forcing/runoff.py:180 → mapping.py:1161 (gen_rof_maps → generate_ESMF_map_via_xesmf, map_overlap=True by default)
- **Already fixed on main:** No. mom6_forge origin/main (83d7692) still has the same code at mapping.py:643-650, and neither of the 2 commits after the pin (#126 tarea fix, #155 file I/O) touches it. The only fix was PR #128, which was closed without merging on 2026-09-13; it was stacked on #127, which was merged.
- **Related:** mom6_forge PR #128 (closed, unmerged; the fix). mom6_forge PR #125 (closed; its description first raised the latitude half). mom6_forge PR #127 (merged; the base #128 was stacked on). CrocoDash issue #187 (runoff mapping speed; not the same bug). Not in TRIAGE.md or QUEUE.md.

**What's wrong.** With map_overlap=True, which gen_rof_maps always uses, generate_ESMF_map_via_xesmf builds a box from the destination mesh. It takes normalize_deg() (mod 360) of every node longitude and latitude and then the plain min and max. Any source runoff cell outside that box is masked out.

There are three failure cases:
1. **Domain crosses 0°**, e.g. -5..5E. The node longitudes become 355..360 and 0..5, so the box is 0..~360 and no longitude is masked.
2. **Domain has an edge exactly at 0°**, e.g. -10..0E, or 350..360 in 0-360 convention. The node at 0 or 360 becomes 0 and is the minimum, so the box is again 0..~360.
3. **Domain crosses the equator**, e.g. -5..5N. The latitudes become 0..5 and 355..360, so the latitude box is 0..~360 and no latitude is masked. Source latitudes go through the same mod.

Because the method is nearest_d2s, every unmasked source cell sends its runoff to its nearest coastline cell in the domain. The regional ocean therefore receives the river runoff of the whole latitude band (cases 1 and 2) or the whole longitude column (case 3). _check_runoff_conserved still passes, because the extra runoff is conserved, only placed in the wrong ocean.

**Who hits it.** A CrocoDash case with a DROF compset, so that RunoffConfigurator runs in process_forcings, plus a domain that does any of these:
- crosses 0° longitude, e.g. North Sea, English Channel, Bay of Biscay, Gulf of Guinea, western Mediterranean;
- has its east or west edge exactly at 0° or 360°;
- crosses the equator, e.g. Amazon or Congo plume, Galapagos, equatorial Pacific or Atlantic.

The visualCaseGen runoff mapping widget (runoff_mapping_generator.py:200) calls the same gen_rof_maps.

**Repro.**

cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a1 && source ../../env.sh && timeout 900 $PY -u v1_overlap.py

Script: dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a1/v1_overlap.py
- Source: a near-global 3° all-ocean rof mesh, from Grid(lenx=357, leny=150, resolution=3, xstart=-180, ystart=-75), Topo.set_flat and write_esmf_mesh.
- Destination: 10x10° domains at 2°, with the west 2 columns set to land.
- Each domain: mapping.gen_rof_maps(rof_mesh_path=rof_mesh, ocn_mesh_path=ocn, output_dir=out, mapping_file_prefix=..., rmax=None, fold=None). The script then lists the source cells that have S>0 in the nn map.

Fix check: dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a1/v2_fixcheck.py runs the same script with the overlap block patched to compare latitude raw and use a circular longitude window.

- Expected: Only source cells inside the domain's lon/lat box get a weight: about 12 to 16 cells per 10x10° domain with 3° source cells. This is what the patched run gives:
- [pm] -5..5E: 16 cells, lon -4.5..4.5
- [edge0] -10..0E: 12 cells, lon -7.5..-1.5
- [eq] -5..5N: 12 cells, lat -4.5..4.5
- Observed: Unpatched audited code:
- RESULT [east] domain lon 5..15 lat 40..50: 12 src cells mapped; their lon 7.5..13.5, lat 40.5..49.5 (correct)
- RESULT [pm] domain lon -5..5 lat 40..50: 476 src cells mapped; their lon -178.5..175.5, lat 40.5..49.5 (all 119 longitudes in the band)
- RESULT [edge0] domain lon -10..0 lat 40..50: 472 src cells mapped; their lon -178.5..175.5, lat 40.5..49.5
- RESULT [eq] domain lon 5..15 lat -5..5: 150 src cells mapped; their lon 7.5..13.5, lat -73.5..73.5 (all 50 latitudes)
- RESULT [south] domain lon 5..15 lat -50..-40: 12 src cells mapped (correct; a domain entirely in the southern hemisphere is fine)

gen_rof_maps' conservation check passes in every case.

**Root cause.** The bounding-box test treats both coordinates as linear [0,360) ranges:
1. normalize_deg (np.mod(x+360, 360)) is applied to latitude (lines 644 and 650), so a latitude range that crosses 0 splits into 0..a and 360-b..360.
2. min/max over normalized longitudes (line 645) cannot describe an arc that contains the 0/360 cut. A node at exactly 0° or 360° maps to 0 and becomes the minimum, which also produces a near-global box.

**Smallest fix.** In generate_ESMF_map_via_xesmf, change the overlap test:
- **Latitude:** compare raw latitudes; drop normalize_deg on lines 644 and 650.
- **Longitude:** use a circular window. Take the sorted unique normalized node longitudes. The window starts after the largest circular gap and its width is 360 minus that gap. A source cell is inside when mod(src_lon - start, 360) <= width.
- Mask the source wherever the cell is not inside in both longitude and latitude.

This is what closed, unmerged mom6_forge PR #128 (_lon_window, commit 1812c4d on branch fix-map-overlap-seam-latitude-masking) implements. It can be re-landed with its tests. A patched copy of this logic gives the expected counts for all five domains in v2_fixcheck.py.

### M2. get_mesh_dimensions swaps nx/ny on rotated or polar-offset grids, so runoff maps send river water to interior ocean cells and Grid/Topo.from_esmf_mesh return a scrambled grid

- **Repo:** mom6_forge
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `mom6_forge-a2`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/utils.py:224-225 (consumers: mapping.py:52-56 grid_from_esmf_mesh, mapping.py:837-845 compute_smoothing_weights, mapping.py:316-317 write_mapping_file, utils.py:298-302 get_avg_resolution_km, _supergrid.py:844 reconstruct_from_esmf_mesh)
- **Already fixed on main:** No. mom6_forge origin/main 83d7692 (also checked on GitHub NCAR/mom6_forge main) still has the swap, at utils.py:226-227. Neither #126 nor #155 touches it. A pin bump would not fix it.
- **Related:** No matching issue or PR. These separate findings showed up in the same repro and are not part of this one:
- mapping.py:122: extract_coastline_mask pads with np.pad(mode="wrap") on non-cyclic grids, so ocean cells on the edge opposite a land edge get runoff (column 19 above).
- get_avg_resolution_km gives wrong values on rotated grids even without the swap (angle 30: 4.33 km, angle 45: 3.54 km, true 5 km) and negative ones for westward rows: angle 120 suggests rmax=-100, fold=-200, which compute_smoothing_weights then rejects.
- Grid.from_center(angle_deg=90) fails with "cyclic_x is only supported for 360 degree domains".
Loosely related: mom6_forge PR #145 (haversine dx/dy for rotated grids, a different function); CrocoDash PR #295 (CICE rotation, unrelated code).

**What's wrong.** get_mesh_dimensions first gets nx exactly from element connectivity: nx is the index of the first element that shares an edge with element 0, which is the row stride. It then swaps nx and ny whenever mod(lon[nx//2]-lon[0], 360) < |lat[nx//2]-lat[0]| along the first row. Every caller reshapes the flat mesh arrays in C order as (ny, nx), so after the swap the 2D layout is scrambled. Not just transposed: consecutive elements of one true row are wrapped onto several short rows. Effects:
- grid_from_esmf_mesh returns a scrambled mask/lon/lat.
- extract_coastline_mask flags interior ocean cells as coast, so generate_ESMF_map_via_xesmf sends runoff to them.
- compute_smoothing_weights builds left/right/top/bottom neighbours from the wrong stride.
- get_avg_resolution_km returns a tiny value, so get_suggested_smoothing_params suggests rmax=1 km, fold=2 km instead of 20/40 km. CrocoDash RunoffConfigurator.configure uses this when rmax is not given, so smoothing is effectively turned off.
- write_mapping_file writes swapped nj_b/ni_b.
- Grid.from_esmf_mesh and Topo.from_esmf_mesh (via reconstruct_from_esmf_mesh) return a grid with the wrong shape and wrong coordinates.
No error is raised.

**Who hits it.** Any mom6_forge-written ocean mesh with nx != ny whose first grid row runs more north-south than eastward in degree space. Two ways to get one:
- Grid.from_center(..., angle_deg=A) with roughly atan(1/cos(lat)) < |A| < 90. That is |A| above about 49° at 30N; 60 and -60 both trigger. Rows that run westward (|A| > 90, e.g. 120) do not trigger, because of the mod 360.
- Grid.from_projection("EPSG:3995", ...) domains offset along the projection x axis, e.g. x in [1500, 2500] km or [-2500, -1500] km.
User paths:
- A CrocoDash Case with a DROF compset (RunoffConfigurator is required for DROF): configure_forcings computes the rmax/fold suggestion and process_forcings calls gen_rof_maps.
- The visualCaseGen runoff_mapping_generator GUI.
- Grid.from_esmf_mesh / Topo.from_esmf_mesh on such a mesh.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a2

(a) timeout 900 $PY -u v4_case.py 60   (and `v4_case.py 0` as control) — CrocoDash end to end:
  grid = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=60, name="vma2")   # true (ny,nx)=(12,20)
  d = np.full((12,20),1000.); d[:, :3] = 0; topo.depth = d                        # real coast = column i=3
  Case(..., compset="1850_DATM%JRA_SLND_SICE_MOM6%REGIONAL_DROF%JRA_SGLC_SWAV", atm_grid_name="TL319", ...)
  case.configure_forcings(date_range=[...], product_name="reference_ocean", function_name="get_reference_ocean_data")
  case.process_forcings(process_ic=False, process_bc=False)   # runoff only
  then count the dst rows with S != 0 in inputdir/mapping/*.nc

(b) timeout 900 $PY -u v2_rofmap.py 60   — mapping.gen_rof_maps against a synthetic 0.1° rof mesh, as-is and with get_mesh_dimensions monkeypatched to keep the connectivity nx

(c) timeout 900 $PY -u v1_meshdims.py   — get_mesh_dimensions / grid_from_esmf_mesh / Grid.from_esmf_mesh for angles 0, 30, 45, 60. The script then stops at angle 90 on a separate from_center assertion.

(d) timeout 900 $PY -u v3_proj.py   — from_projection polar grids

- Expected: get_mesh_dimensions returns (20, 12) for a 20x12 grid at any rotation. The JRA025->ocean nn/nnsm maps deliver runoff only to ocean cells next to land (column i=3 here). The suggested rmax/fold is about 20/40 km, as for the unrotated grid. Grid.from_esmf_mesh returns a (12, 20) grid matching the original tlon.
- Observed: (a) angle 60 through CrocoDash:
  "Destination: nlat=20, nlon=12" (true 12x20); "rmax = 1 km, fold = 2 km"; ROF2OCN_LIQ_RMAPNAME=.../JRA025_to_vma2_map_r1_f2_nnsm.nc
  "JRA025_to_vma2_map_r1_f2_nnsm.nc: nj_b,ni_b=20,12 (true ny,nx=12,20); ocean cells receiving runoff=16, of which next to land=4; per true column: [0, 0, 0, 4, 0, 0, 0, 0, 4, 0, 2, 0, 0, 2, 2, 0, 0, 0, 0, 2]"
Control, angle 0: "Destination: nlat=12, nlon=20", "rmax = 20 km, fold = 40 km", nn map per true column [0,0,0,2,0,...,0,2]. Column 19 is the separate wrap-padding artifact.

(b) angle 60:
  as-is: "[AS-IS] nn map: ocean cells receiving runoff=61 (not adjacent to land: 49); nj_b,ni_b in file = 20,12"; receiving columns 3, 8-14 and 19
  patched: "[PATCHED] nn map: ocean cells receiving runoff=24 (not adjacent to land: 12)"; columns 3 and 19 only, the 12 being the wrap artifact
  angle -60: identical to 60. Angles 0 and 120: not swapped.

(c) "angle=  60 true(nx,ny)=(20,12) get_mesh_dimensions=(12,20) grid_from_esmf_mesh shape=(20, 12) | coast flagged=96 true coast=12 ... | avg_res_km=0.22 | from_esmf_mesh shape=(20, 12) tlon matches=False". Angles 0, 30 and 45 give (20,12) and tlon matches=True.

(d) "arctic_offset_x+ true (nx,ny)=(20,12) get_mesh_dimensions=(12, 20) SWAPPED" and the same for arctic_offset_x-. Centred Arctic, y-offset Arctic and Antarctic x-offset are ok.

**Root cause.** A lon/lat orientation heuristic (utils.py:220-225) overrides the exact, connectivity-derived nx. That nx is always the fast-varying stride that all callers' reshape(ny, nx) and row-neighbour arithmetic depend on. On rotated or offset-projection grids the rows are not zonal, so the heuristic fires and the counts no longer match the storage order. The swap is also inconsistent for a genuinely column-major mesh: there, swapping the counts without transposing the data scrambles the reshape too. So the swap is never what the reshape consumers need.

**Smallest fix.** Remove the swap in get_mesh_dimensions (utils.py:214-225) and return the connectivity-derived (nx, len//nx). The narrowest version: skip the swap when the mesh has the "grid_topology" attr that to_esmf_mesh always writes, since mom6_forge meshes are always row-major. The repro's monkeypatch does this and restores coast-only runoff mapping. If orientation ever matters for a foreign column-major mesh, transpose the reshaped arrays in grid_from_esmf_mesh/flatten_to_mesh instead of swapping the counts. A follow-up for get_avg_resolution_km: compute great-circle dx/dy rather than dlon*cos(lat)/dlat, which is also wrong on rotated grids.

### M3. Topo.from_version_control reloads every version-controlled bathymetry with min_depth=0.0, so cells shallower than the saved min_depth become ocean

- **Repo:** mom6_forge
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `mom6_forge-a3`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/topo.py:278-288 (also topo.py:183-188 and 219-220; edit_command.py:371-374; command_manager.py:249-269)
- **Already fixed on main:** No. origin/main 83d7692 has the same from_version_control (topo.py:283-293 there); the only change is Grid.from_supergrid -> Grid.from_supergrid_file. Neither #126 nor #155 touches MinDepthEditCommand or TopoCommandManager.undo, so a pin bump would not fix it.
- **Related:** none (no matching issue or PR in NCAR/mom6_forge in any state; not in TRIAGE.md or QUEUE.md). The existing test test_topo_from_version_control (tests/test_topo.py:8) misses it because its fixture uses min_depth=0.

**What's wrong.** from_version_control builds a placeholder Topo(grid, 0.0, git=True). Topo.__init__ sets self._min_depth = 0.0 first and then commits MinDepthEditCommand(new_value=0.0) to the existing git history. MinDepthEditCommand.__call__ records old_value as the current value, so the commit stores old=0.0 and new=0.0. reapply_changes() replays the saved history and then this new command last. tcm.undo() then reverses it with old_value 0.0, so min_depth stays 0.0. The code comment at topo.py:288 says the undo leaves the correct min_depth, but it does not. As a result tmask, masked_depth, the written topog depth and its min_depth attribute are all computed against 0 instead of the saved min_depth. CrocoDash Case also passes minimum_depth=ocn_topo.min_depth, so the case gets MINIMUM_DEPTH = 0.0. Each reload also adds two commits (COMMAND + UNDO) to the bathymetry's history and leaves the min_depth=0 command on the redo stack. Raw depth is reloaded correctly. A min_depth changed later in TopoEditor is lost the same way.

**Who hits it.** Build a bathymetry with version control (Topo(..., git=True), as TopoEditor requires) and a nonzero min_depth. In a later session, reload it with Topo.from_version_control(domain_dir), which is the documented way back to an edited bathymetry, then write it or pass it to a CrocoDash Case.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a3 && timeout 900 $PY -u repro.py   (and case_repro.py for the Case path). Key lines: grid = Grid(lenx=4.0, leny=3.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a3"); topo = Topo(grid, min_depth=10.0, version_control_dir=lib, git=True); d = np.full((ny,nx),500.); d[0,:] = 5.0; topo.depth = d; re = Topo.from_version_control(topo.domain_dir); print(re.min_depth, re.tmask.sum()). case_repro.py passes the reloaded Topo to Case(..., compset 1850_DATM%NYF_..., override=True) and reads the inputdir topog and user_nl_mom.

- Expected: The reloaded Topo has min_depth=10.0 and the same 8 ocean cells as the original. Row 0 (5 m) stays land with depth 0 in the topog, and MINIMUM_DEPTH = 10.0 in the case. Loading does not change the git history.
- Observed: ORIGINAL : min_depth= 10.0  ocean cells= 8  masked_depth row0= [0.0, 0.0, 0.0, 0.0]
RELOADED : min_depth= 0.0  ocean cells= 12  masked_depth row0= [5.0, 5.0, 5.0, 5.0]
raw depth equal: True
git commits before/after reload: 2 4   (newest: "UNDO-a90eed99...", "COMMAND-Min Depth Edit")
written topog depth row0: [5.0, 5.0, 5.0, 5.0]
RELOAD#2 : min_depth= 0.0  commits= 6
Case path: inputdir ocean_topog_a3c_7ebd5a.nc attr min_depth= 0.0 depth row0= [5.0, 5.0, 5.0, 5.0]; user_nl_mom line 56: MINIMUM_DEPTH = 0.0

**Root cause.** The placeholder MinDepthEditCommand that Topo.__init__ commits during from_version_control has old_value captured at construction time. That value is the placeholder 0.0, not the min_depth the replay restores, because __init__ assigns self._min_depth = min_depth before running the command. Replay applies the placeholder command last, and undoing it restores its old_value of 0.0. The undo cannot recover the replayed min_depth, contrary to the comment at topo.py:288.

**Smallest fix.** In from_version_control, swap the two calls: undo the placeholder command first, then replay (topo.tcm.undo(); topo.tcm.reapply_changes()). The undone placeholder is skipped during replay, so the saved min_depth wins. I verified this by monkeypatching it in repro.py: min_depth=10.0 and 8 ocean cells. A cleaner fix is to not commit the placeholder at all when the domain already has a history (for example, a flag on __init__ that makes from_version_control apply it with skip_version_control=True) and drop the undo. That also stops the two extra commits per load and the stale redo entry. Also change the test fixture get_rect_topo_with_vc (tests/conftest.py:352) to a nonzero min_depth so test_topo_from_version_control catches this.

### M4. Cressman fallback fill (iterative_fill) turns unfilled coastal ocean cells into NaN, which the TOPO_FILE writes as min_depth+0.1

- **Repo:** mom6_forge
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `mom6_forge-a7`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/utils.py:488-505 (filled_f at 488, unweighted d_nbr at 493-495); NaN input comes from CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/topo.py:1653 (dst_ds["mask"] = self.tmask) via mapping.py regrid_dataset_via_xesmf; NaN is turned into min_depth+0.1 at topo.py:382-391 (masked_depth)
- **Already fixed on main:** No. mom6_forge origin/main 83d7692 has the same iterative_fill (filled_f / d_pad / d_nbr at utils.py:490-497) and the same direct_cressman_interp (dst_ds["mask"] = self.tmask, then iterative_fill). No open mom6_forge PR touches it (#146, #150 and #145 checked).
- **Related:** none (no matching issue, PR, TRIAGE or QUEUE item). Cressman depth path came in with mom6_forge #144 (in the pin).

**What's wrong.** direct_cressman_interp regrids with xESMF onto a dst_ds that contains a "mask" variable. xESMF therefore sets unmapped_to_nan=True (xesmf/frontend.py, any version >= 0.8), so every land cell and every "unfilled" ocean cell (no source ocean point within L) is NaN in the Cressman output. The docstring of regrid_dataset_via_cressman (mapping.py:1695) says unfilled cells are 0, which is wrong.

iterative_fill makes this worse in two ways:
- It counts every land cell as a donor: filled_f = ~unfilled_2d.
- It builds the numerator d_nbr from the raw depth of all four neighbours, not just the donors.

As a result, any unfilled cell that has a land neighbour or a still-unfilled neighbour is "filled" with NaN on the first pass. NaN then spreads to the remaining unfilled cells on later passes. Topo.masked_depth turns NaN ocean cells into min_depth+0.1 (NaN > min_depth is False), and write_topo writes that value into the MOM6 TOPO_FILE "depth" variable, while depth_raw stays NaN.

So the fallback almost never produces a neighbour average. The cells it should fill silently become min_depth+0.1-deep shelves. With land at 0 (iterative_fill called directly), the land-donor bias the finder described also exists, giving 50 m instead of 100 m.

**Who hits it.** Topo.set_from_dataset with depth_method="cressman", or with the automatic Cressman choice (resolution ratio >= 12x), or a direct topo.direct_cressman_interp() call, where the active mask marks as ocean a cell that has no source ocean point (depth > 0) within L = smooth_scl*sqrt(tarea). Typical cases:
- a mask_method="naturalearth" coastline that disagrees with the source dataset;
- a manual or TopoEditor mask edit that opens water, after which Cressman is rerun (the set_from_dataset warning tells users to do this).

Reachable from CrocoDash YAML/CLI as well, because recipe.build_topo passes topo.source kwargs straight to set_from_dataset (CrocoDash/recipe.py:109).

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a7 && timeout 900 $PY -u repro_a7.py

The script is dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a7/repro_a7.py. Key lines:
- Grid(lenx=10, leny=10, resolution=1.0, xstart=-60, ystart=30)
- synthetic 0.05 deg source (ratio ~21x): elevation -100 m west of lon -55, +100 m east of it
- topo = Topo(grid, min_depth=10.0); topo.user_mask = mask with columns 0..7 ocean
- topo.set_from_dataset(src, "lon", "lat", "elevation", is_input_positive_below_msl=False, mask_method="manual", depth_method="cressman"); topo.write_topo(...)

Column 7 (lon -52.5) is the only column flagged unfilled. The script then reruns with the finder's fix and with a NaN-safe fix monkeypatched into mom6_forge.topo.iterative_fill.

- Expected: Column 7 is masked ocean, and its only ocean neighbour (column 6) is 100 m deep, so neighbour averaging should give about 100 m in the TOPO_FILE "depth" variable. Land cells should never act as donors.
- Observed: Cressman output row 5: [100 100 100 100 100 100 100 nan nan nan] (land and unfilled cells are NaN, not 0). Unfilled row 5: [0 0 0 0 0 0 0 1 0 0].

As shipped:
- raw _depth col 7: all nan
- masked_depth row 5: [100 100 100 100 100 100 100 10.1 0 0]
- written topo file "depth" col 7: [10.1 10.1 10.1 10.1 10.1 10.1 10.1 10.1 10.1 10.1] (depth_raw col 7: all nan)

Finder's fix (filled_f = ~unfilled & mask): identical, still nan, giving 10.1.

NaN-safe fix: col 7 = 100.0 everywhere.

Calling iterative_fill directly: land=0 gives centre 50.0 (expected 100); land=NaN gives centre nan.

**Root cause.** iterative_fill does not restrict its donors to finite, filled ocean cells:
- filled_f = (~unfilled_2d) counts land as filled.
- d_nbr sums np.pad(depth, mode="edge") over all four neighbours without weighting by filled_f, so land cells and still-unfilled cells feed the numerator.

In the Cressman pipeline those cells are NaN, because dst_ds has a "mask" variable and xESMF therefore maps unmapped cells to NaN. Every fill touching land or another unfilled cell becomes NaN, and Topo.masked_depth then turns it into min_depth+0.1.

**Smallest fix.** In iterative_fill, compute on each pass:

```python
donor = (~unfilled_2d) & mask_2d & np.isfinite(depth)  # mask_2d = all True when mask is None
d_pad = np.pad(np.where(donor, depth, 0.0), 1)
f_pad = np.pad(donor.astype(float), 1)
```

Then use d_nbr / f_nbr as now. Verified by monkeypatch: column 7 becomes 100 m.

Masking filled_f alone (the finder's fix) is not enough, because the numerator still sums NaN. Optionally also correct the "Unfilled ocean cells are 0" docstring at mapping.py:1695.

### M5. Topo slicing (topo[j0:j1, i0:i1]) drops the user mask and land_fillval, so the sub-topo writes a different land/sea mask and depth

- **Repo:** mom6_forge
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `mom6_forge-a8`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/topo.py:252
- **Already fixed on main:** No. On NCAR/mom6_forge origin/main 83d7692, Topo.__getitem__ (topo.py:232-259) is unchanged and still copies only _depth. Neither of the 2 commits ahead of the pin (#126 tarea, #155 file read/write) touches it.
- **Related:** none (mom6_forge #123 "Masking Operation switch to 2D Array Mask" is a separate performance issue; no TRIAGE, QUEUE or open PR covers Topo slicing)

**What's wrong.** Topo.__getitem__ (topo.py:227-254) builds a new Topo on the sliced grid and copies only the raw depth (new_topo._depth = self._depth[slices]). It does not copy:
- _user_mask, which holds the mask from set_from_dataset (naturalearth or ocean_frac, the default), fill_inland_lakes_and_channels, TopoEditor edits or a manual user_mask;
- land_fillval.
So the sliced topo's tmask comes back from raw depth > min_depth:
- cells the user masked as land become ocean at their raw depth;
- shallow cells the user kept as ocean (written as min_depth+0.1) become land;
- land cells get 0 instead of the user's land_fillval.
Everything Case writes from that topo picks this up silently: the topog, SCRIP, ESMF mesh, CICE grid and WW3 input (case.py:398-421), and the active-point count behind the PE layout (case.py:1045). A related problem at the same line: the sliced _depth is a view of the parent array, so edit_depth on the slice also changes the parent topo.

**Who hits it.** A user cuts a smaller domain from a finished bathymetry with sub = topo[j0:j1, i0:i1] and passes sub (with grid[j0:j1, i0:i1]) to Case() or calls sub.write_topo() / write_esmf_mesh(). This applies to any parent topo with a user mask, which includes every topo built with set_from_dataset defaults, or with a land_fillval other than 0.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a8 && timeout 900 $PY -u repro_slice.py ./out

Key lines of repro_slice.py:
g = Grid(lenx=6, leny=4, resolution=1, xstart=-60, ystart=30, name="a8")
t = Topo(g, min_depth=10.0); t.set_flat(500.0)
t.edit_depth([(0,0)], [5.0])
m = np.ones((4,6), int); m[1,1] = 0; m[2,3] = 0
t.user_mask = m
t.land_fillval = 2.0
sub = t[0:3, 0:4]
Then compare sub.tmask / sub.masked_depth with t's [0:3,0:4] window, and write both topogs plus the sliced ESMF mesh.

repro_alias.py, in the same dir, shows that sub.edit_depth changes the parent.

- Expected: The sliced topo keeps the parent's mask and land fill value. For window [0:3,0:4], tmask should be [[1,1,1,1],[1,0,1,1],[1,1,1,0]] and masked_depth [[10.1,500,500,500],[500,2,500,500],[500,500,500,2]], identical to the parent's window. The written topog and ESMF elementMask should match the parent's window.
- Observed: parent user_mask set: True  sliced user_mask: None
land_fillval parent/sliced: 2.0 0.0
sliced tmask: [[0 1 1 1] [1 1 1 1] [1 1 1 1]]
sliced masked_depth: [[0. 500. 500. 500.] [500. 500. 500. 500.] [500. 500. 500. 500.]]
topog depth differs at (j,i): (0,0), (1,1), (2,3)
sliced ESMF mesh elementMask: [[0, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
with fix: tmask equal: True  masked_depth equal: True

Aliasing (repro_alias.py): "parent depth[0,0] after editing the SLICED topo: 123.0", "shares memory: True"

**Root cause.** __getitem__ predates the user-mask / land_fillval layer and still copies only raw depth. tmask returns _user_mask when one is set and otherwise derives from raw depth (topo.py:533-536), and masked_depth uses tmask and _land_fillval (topo.py:382-391). Dropping _user_mask therefore changes the mask and depth the slice writes. self._depth[slices] is a view, not a copy, so in-place DepthEditCommand edits (edit_command.py:94) on the slice reach the parent's array.

**Smallest fix.** In Topo.__getitem__, after the new Topo is created:
new_topo._depth = self._depth[slices].copy()
if self._user_mask is not None:
    new_topo._user_mask = self._user_mask[slices].copy()
new_topo._land_fillval = self._land_fillval
Optionally carry over _src. Add one test: slicing a topo that has a user mask and a non-default land_fillval preserves tmask and masked_depth.

### M6. Grid.from_center with angle_deg=±90 fails for small or equatorial domains: the rotated grid is taken for a cyclic one ("cyclic_x is only supported for 360 degree domains")

- **Repo:** mom6_forge
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `mom6_forge-a4`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/grid.py:392-406 (Grid.is_cyclic_x), CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/grid.py:691 (from_supergrid_ds passes cyclic_x=Grid.is_cyclic_x(ds)), CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/grid.py:175-177 (assert that fires), CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/_supergrid.py:37-43 (SupergridBase.is_cyclic_x, same logic); entry point grid.py:573-611 (Grid.from_center)
- **Already fixed on main:** No. mom6_forge origin/main 83d7692 (2 ahead of the d74c851 pin: #126 and #155) has the same is_cyclic_x code in grid.py:393-406 and _supergrid.py:38-43. Open PR #153 changes only how get_bounding_boxes uses is_cyclic_x, not the detection itself.
- **Related:** None is a duplicate. Same code area: mom6_forge PR #153 (cyclic bounding boxes) and closed issue #132, CrocoDash issue #339 (cyclic-x grids with an open WW3 boundary), and 1.1 queue item Q17 (cyclic-grid chain). These all treat genuinely cyclic grids. Once #153/Q17 let cyclic grids reach the OBC and WW3 code, a misdetected grid that slipped through would be handled as periodic there, so this fix should land first.

**What's wrong.** Grid.is_cyclic_x and SupergridBase.is_cyclic_x decide that a grid is periodic in x when the longitudes of supergrid columns 0 and -1 match within rtol=1e-5 (np.allclose on normalize_deg(lon)). They never compare latitudes, and they use a relative tolerance on a longitude, so the tolerance is about 3.6e-3 deg near 360E and close to 0 near 0E. A grid rotated 90 deg (or -90/270) has i running north-south, so its first and last columns span almost the same longitudes at different latitudes. For small domains, and for any domain at the equator, the difference falls inside the tolerance. Grid.from_supergrid_ds then passes cyclic_x=True to Grid(), and the 'lenx == 360' assertion stops grid creation. The user never asked for a cyclic grid, so the error message is misleading too. The same path is reached through the GridCreator widget's 'From Center' mode, which prints 'Failed to create grid from centre: cyclic_x is only supported for 360 degree domains.', and through Grid.from_supergrid on any hgrid file whose i axis runs north-south.

**Who hits it.** Creating an estuary- or coast-aligned regional grid with a quarter-turn rotation, which is the use case the from_center docstring and quickstart.md describe: Grid.from_center(lat, lon, width_m, height_m, res_m, angle_deg=90) (also -90 or 270). Examples that fail: Chesapeake mouth (37, -76, 40 km x 20 km, 2 km), Delaware (39, -75, 30x20 km, 1.5 km), Rio de la Plata (-35, -57, 40x20 km), Ganges (21, 89, 40x20 km), and Amazon (0, -50, 200x100 km; at the equator every size fails). angle_deg=0, 89, 89.9 and 180 work, and larger mid-latitude ±90 domains, e.g. (45, -70, 200x100 km), happen to escape.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh && cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a4 && timeout 900 $PY -u repro.py   (and sweep_and_fix.py in the same dir for the size/latitude sweep and the monkeypatched fix). Key lines: from mom6_forge.grid import Grid; Grid.from_center(30, -60, 100e3, 60e3, 5e3, angle_deg=90)  # -> AssertionError; sg = ProjectedSupergrid.from_center(30, -60, 100e3, 60e3, 5e3, 90); compare sg.x[:,0] vs sg.x[:,-1] and sg.y[:,0] vs sg.y[:,-1].

- Expected: A non-cyclic regional Grid with nx=20, ny=12 and cyclic_x=False, the same as angle_deg=0 or 89 gives for this domain.
- Observed: File ".../mom6_forge/grid.py", line 686, in from_supergrid_ds: obj = cls(  ->  File ".../mom6_forge/grid.py", line 176, in __init__: not cyclic_x or lenx == 360.0  ->  AssertionError: cyclic_x is only supported for 360 degree domains. Diagnostics: col 0 lon -60.3123..-59.6877, lat 30.4507..30.4510; col -1 lon -60.3095..-59.6905, lat 29.5486..29.5489; max |lon0-lon-1| = 2.81e-03 deg; max |lat0-lat-1| = 0.902 deg; SupergridBase.is_cyclic_x -> True; Grid.is_cyclic_x -> True; lenx = 0.62 deg. Same failure for angle_deg=-90 and 270, and for (0,-150,100x100 km,90). angle_deg=89 gives 'OK cyclic_x=False nx=20 ny=12'. Sweep at lon -60 (width=2*height, 20 cells): lat 0 fails at every height from 10 to 200 km; lat 30 fails at h<=30 km.

**Root cause.** The cyclic test is np.allclose(normalize_deg(x[:,0]), normalize_deg(x[:,-1]), rtol=1e-5). It checks only longitude, ignores latitude, and uses a relative tolerance on longitude, which gives a 1e-5*lon tolerance of up to 3.6e-3 deg near 360E. So any grid whose first and last i-columns sweep the same longitudes counts as periodic, e.g. a 90-deg-rotated or transposed grid. That includes a from_center domain rotated by ±90 deg when meridian convergence across it is below the tolerance. from_supergrid_ds trusts this flag for cyclic_x, and Grid.__init__ rejects cyclic_x when lenx != 360.

**Smallest fix.** Make both Grid.is_cyclic_x (grid.py:392-406) and SupergridBase.is_cyclic_x (_supergrid.py:37-43) require matching latitudes and use an absolute tolerance on the wrapped longitude difference. For example: dlon = (x[:,0] - x[:,-1] + 180) % 360 - 180; return np.all(np.abs(dlon) < atol) and np.allclose(y[:,0], y[:,-1], rtol=0, atol=atol), with atol of about 1e-6 deg. Monkeypatched this way, both rotated cases build with cyclic_x=False, a global 360-deg Grid still round-trips through from_supergrid_ds with cyclic_x=True, and a plain 4x2-deg regional grid stays non-cyclic. A follow-up test would be from_center(..., angle_deg=90) on a small domain.

### M7. Replaying a 'Clear manual mask' edit crashes: ClearMaskCommand.deserialize passes old_mask= that __init__ does not accept

- **Repo:** mom6_forge
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `mom6_forge-a5`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/edit_command.py:433 (deserialize factory); constructor at CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/edit_command.py:407; reached from CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/command_manager.py:227 (reapply_changes) and :281 (redo)
- **Already fixed on main:** No. mom6_forge origin/main (83d7692) has the identical ClearMaskCommand, and the two commits ahead of the pin (#126, #155) do not touch edit_command.py. None of the open mom6_forge PRs change ClearMaskCommand.
- **Related:** none (mom6_forge #123 'Masking Operation switch to 2D Array Mask' is about mask-edit performance, not this bug)

**What's wrong.** ClearMaskCommand.deserialize builds cls(topo, old_mask=old_mask), but ClearMaskCommand.__init__(self, topo, message="Clear Manual Mask") has no old_mask parameter. Clearing the mask works and is committed to the version-control history. Every later replay of that history then raises TypeError.
- TopoCommandManager.reapply_changes fails, so Topo.from_version_control(domain_dir) and tcm.checkout(branch) fail.
- TopoCommandManager.redo fails after the clear has been undone.
The error is stored in the domain's git history, so from_version_control fails on that domain dir from then on. Topog files written earlier with write_topo/save can still be read with from_topo_file.
The trigger does not need a user mask to exist. On a git=True Topo, set_from_dataset(mask_method="dataset") calls clear_user_mask() (topo.py:1384) and records a ClearMaskCommand with old_mask=None. That entry fails the same way on replay.

**Who hits it.** Run any of these on a Topo(..., git=True), as TopoEditor requires:
- topo.clear_user_mask()
- topo.user_mask = None
- the TopoEditor "Clear user mask" button
- topo.set_from_dataset(..., mask_method="dataset")

Then do any of these:
- Topo.from_version_control(topo.domain_dir)
- topo.tcm.checkout(<branch whose history contains the clear>)
- topo.tcm.undo() followed by topo.tcm.redo() (or TopoEditor undo/redo)

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a5 && timeout 900 $PY -u repro_clear_mask.py

Script: dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a5/repro_clear_mask.py. Key lines:
  grid = Grid(lenx=5.0, leny=5.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a5A")
  t = Topo(grid, min_depth=10.0, version_control_dir=<scratch>/vc_A, git=True); t.set_flat(1000.0)
  m = np.ones((ny, nx), int); m[0,0] = 0; t.user_mask = m
  t.clear_user_mask()
  Topo.from_version_control(t.domain_dir)      # scenario A
  # B: clear, t.tcm.undo(), t.tcm.redo()
  # C: clear_user_mask() with no prior mask, then from_version_control
  # D: create_branch('b'), checkout('b'), mask + clear, checkout(main), checkout('b')
  # F: same as A with __init__(self, topo, old_mask=None, message=...) monkeypatched in

- Expected: The topo reloads, or the branch checkout replays, with the user mask cleared (_user_mask None and tmask taken from the raw depth again). Redo of an undone clear clears the mask again.
- Observed: [A from_version_control after clear] RAISED TypeError: ClearMaskCommand.__init__() got an unexpected keyword argument 'old_mask'  (topo.py:287 from_version_control -> command_manager.py:227 reapply_changes -> edit_command.py:433 factory)
[B undo then redo of clear] RAISED TypeError: ... 'old_mask'  (command_manager.py:281 redo -> edit_command.py:433)
[C clear with no prior mask, then from_version_control] RAISED TypeError: ... 'old_mask'
[D branch checkout replay] RAISED TypeError: ... 'old_mask'  (command_manager.py:216 checkout -> :227 reapply_changes). The git checkout has already happened, so the topo is left half-replayed.
[F with fix] reloaded with fix; _user_mask is None tmask[0,0] = 1; undo after reload: tmask[0,0] = 0; redo after reload: _user_mask is None; OK, no exception

**Root cause.** The deserialize factory and the constructor no longer agree. deserialize rebuilds old_mask from the serialized payload and passes it as a keyword, but __init__ always reads old_mask from topo._user_mask and does not accept it as an argument. The tests only cover reverse_deserialize (tests/test_edit_commands.py:94-108), so the forward replay path (deserialize) is never run.

**Smallest fix.** Change the constructor to `def __init__(self, topo, old_mask=None, message="Clear Manual Mask")` with `self.old_mask = old_mask if old_mask is not None else topo._user_mask`. Verified by monkeypatch: reload, undo and redo all succeed. Alternatively, build `cls(topo)` in deserialize and set `.old_mask` afterwards. Add one test that round-trips ClearMaskCommand.deserialize(cmd.serialize())(topo)().

### M8. Runoff rmax/fold suggestion is 0 or negative on polar-stereographic, rotated and sub-200 m grids, so process_forcings crashes with 'rmax must be > 0 km'

- **Repo:** mom6_forge
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `mom6_forge-a6`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/utils.py:311-319 (signed dx_deg/dy_deg mean in get_avg_resolution_km); CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:174-180 (get_suggested_smoothing_params, no floor); raised at CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:807 via gen_rof_maps mapping.py:1206; reached from CrocoDash/forcing/runoff.py:105-110 (configure) and runoff.py:179-186 (process)
- **Already fixed on main:** No. origin/main 83d7692 has get_avg_resolution_km (utils.py) and get_suggested_smoothing_params (mapping.py) unchanged, and no open mom6_forge PR touches them (#145 changes only _supergrid.py dx/dy).
- **Related:** visualCaseGen #44 (GUI suggests an absurd 5000 km RMAX from the same get_suggested_smoothing_params heuristic; possibly the same root cause, different symptom); TRIAGE item 6 / mom6_forge #146 (polar-stereographic grids, unrelated fix); CrocoDash #187 (runoff mapping performance, unrelated). Separate bug seen while testing: Grid.from_center(angle_deg=90) with a non-square domain raises "cyclic_x is only supported for 360 degree domains" (grid.py:176 via Grid.is_cyclic_x).

**What's wrong.** get_avg_resolution_km averages the signed differences of center longitude along i and of latitude along j. It assumes i points east and j points north. When they don't, the signed steps cancel or turn negative:
- angle_deg=90 or 270 averages about 0;
- angle_deg=100 to 260 is negative (180 gives -5.0 km for a 5 km grid);
- 45 and 60 are 30-50% too small.
The same happens to polar-stereographic Grid.from_projection domains away from lon 0. In EPSG:3995 near lon 180, +x points west and +y points south. Beaufort/Bering domains give -7.8 / -10.1 km for a 10 km grid, and a pole-centred cap gives 4.3 km. get_suggested_smoothing_params then truncates int(5*res) with no floor, returning (0, 0) or (-100, -200). It also returns (0, 0) for any grid finer than 200 m, such as the estuary grids from_center is documented for. When rmax/fold are omitted, CrocoDash's RunoffConfigurator stores these values at configure_forcings: the map name becomes ..._r-100_f-200_nnsm.nc and goes into ROF2OCN_LIQ/ICE_RMAPNAME. process_forcings' runoff step then writes the NN map and raises ValueError in compute_smoothing_weights. Secondary effect: when a user supplies rmax on such a grid, the check at mapping.py:1196 compares it with the bogus negative resolution and prints a misleading "rmax significantly larger than the average resolution" warning.

**Who hits it.** A CrocoDash case with a DROF%GLOFAS compset (e.g. GR_JRA_GLOFAS / CR_JRA_GLOFAS), rmax/fold not given to configure_forcings, and an ocean grid whose i/j axes are not roughly east/north. Examples:
- a polar Grid.from_projection("EPSG:3995"/"EPSG:3031", ...) domain in the Pacific/Beaufort/Bering sector or the Ross Sea side;
- Grid.from_center with angle_deg roughly between 89 and 271;
- any grid with mean cell size under 200 m.
Workaround: pass rmax and fold explicitly.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a6 && timeout 900 $PY -u v_runoff_e2e.py beaufort   (also: estuary150m, rot0_5km control; v_rmax.py, v_sweep.py, v_seam.py for the suggestion table; v_fix.py for the monkeypatched fix).

Key lines of v_runoff_e2e.py:
grid = Grid.from_projection("EPSG:3995", -1000e3, -800e3, 1000e3, 1200e3, 10e3); topo.set_flat(1000) with a land strip; topo.write_esmf_mesh(ocn_mesh)   # same call Case() uses
cfg = RunoffConfigurator(..., case_compset_lname="..._DROF%GLOFAS_...", case_esmf_mesh_path=ocn_mesh, rmax=None, fold=None, rof_esmf_mesh_filepath=<tiny 0.5deg stand-in mesh>)
cfg.configure()   # xmlchange patched out
cfg.process(WorkflowContext(inputdir=...))

- Expected: A positive smoothing radius of a few grid cells, regardless of grid orientation (for example (20,40) for every 5 km grid and (50,100) for a 10 km polar grid), and a runoff map that generates.
- Observed: beaufort: "configure(): rmax = -100  fold = -200"; "xmlchange ROF2OCN_LIQ_RMAPNAME = r05_to_audit_beaufort_map_r-100_f-200_nnsm.nc"; "process(): ValueError: rmax must be > 0 km."; mapping/ holds only the _nn.nc file.
estuary150m: "rmax = 0  fold = 0" then "process(): ValueError: rmax must be > 0 km."
Control rot0_5km: rmax=20 fold=40, process OK.
Suggestion sweep (5 km from_center, 20x20): angle 0 gives 5.003 km and (20,40); 45 gives 3.538 and (10,20); 89 gives 0.087 and (0,0); 90 gives 0.000 and (0,0); 100 gives -0.869 and (-10,-20); 180 gives -5.003 and (-100,-200).
Fine grids: 199 m and 100 m give (0,0).
Polar 10 km: EPSG:3995 pole-centred gives 4.272 and (20,40); 3995 x0=0,y0=0 gives -6.668 and (-100,-200); 3995 Bering gives -10.065 and (-100,-200); 3031 x0=0,y0=-200e3 gives -6.668 and (-100,-200).
Unaffected: lat-lon domains across the antimeridian (lon unwrapped to 178-182, 9.976 km).

**Root cause.** get_avg_resolution_km measures resolution as the mean of signed lon steps along axis 1 and signed lat steps along axis 0. That is a valid measure only for north-up grids whose i axis points east. For rotated or polar-stereographic grids, the steps cancel or are negative. get_suggested_smoothing_params then truncates int(5*res) and rounds down to the leading digit with no lower bound, so it returns 0 or a negative value. compute_smoothing_weights correctly rejects that.

**Smallest fix.** In get_avg_resolution_km, use orientation-independent magnitudes: the great-circle (haversine) distance between i-neighbour and j-neighbour centers, or simply mean(sqrt(elementArea)) for meshes mom6_forge writes in m2. Then clamp the suggestion to rmax = max(rmax, 1) and fold = 2*rmax, because CrocoDash int()-casts both. A monkeypatched version (v_fix.py) gives 5.003 km and (20,40) for every rotation angle, 10.07-10.23 km and (50,100) for every polar domain including Beaufort and Bering, and (1,1) or (1,2) for grids under 250 m.

### M9. Topo.set_from_dataset fails with a bare IndexError when the source bathymetry latitude is descending (north to south)

- **Repo:** mom6_forge
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `mom6_forge-a9`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/_source_bathy.py:141-143 (lat label slice); error raised at CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/topo.py:1180 (diagnose_resolution, called from set_from_dataset at topo.py:1341)
- **Already fixed on main:** No. mom6_forge origin/main 83d7692 (2 commits ahead of pin d74c851: #126, #155) still has the same slice at _source_bathy.py:142 and the same src.lat[1] access at topo.py:1185. Open PR #146 (polar bathymetry seam) edits _slice_to_domain but keeps the ascending-only lat slice, so it does not fix this either.
- **Related:** none (closest: mom6_forge PR #146, which touches the same _slice_to_domain function but not the latitude order; reached from CrocoDash via recipe.py:109 build_topo)

**What's wrong.** SourceBathy._slice_to_domain clips the source with self._ds.sel(lat=slice(lat_min - buf, lat_max + buf)). That label slice is only correct for an ascending lat coordinate. When the file stores latitude north to south, which is common for DEMs converted from GeoTIFF and is valid CF data, the slice silently returns 0 latitude rows. set_from_dataset then fails in diagnose_resolution with "IndexError: index 1 is out of bounds for axis 0 with size 0" on src.lat[1]. The message says nothing about latitude order or an empty domain slice. set_src succeeds but leaves an empty src.ds. mpi_set_depth_from_xesmf goes through the same set_src, so it gets the same empty source (from reading the code, not run).

**Who hits it.** Call Topo.set_from_dataset (public API, or a CrocoDash YAML/CLI recipe with topo.source.type: dataset via recipe.py:109) on a bathymetry netCDF whose lat coordinate decreases with index. Topo.set_src and Topo.mpi_set_depth_from_xesmf hit the same slice.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a9 && timeout 900 $PY -u repro.py
Key lines (repro.py): build a global 0.5° dataset with elevation = -(1000 + 10*lat). Write it as src_asc.nc and also reversed, asc.isel(lat=slice(None,None,-1)), as src_desc.nc. Then:
  grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a9")
  topo = Topo(grid, min_depth=10.0)
  topo.set_from_dataset(bathymetry_path=path, longitude_coordinate_name="lon", latitude_coordinate_name="lat", vertical_coordinate_name="elevation", mask_method="dataset", depth_method="xesmf")
A third run monkeypatches SourceBathy._slice_to_domain to do self._ds = self._ds.sortby(self.lat_name) first.

- Expected: The descending file should give the same bathymetry as the ascending one, since it holds the same data in reverse order. If mom6_forge chooses not to support descending lat, it should at least raise a clear error, such as "source latitude must be ascending" or "source bathymetry does not cover the grid's latitude range".
- Observed: Ascending: "OK depth min/max = 1302.50 / 1337.50", "max |depth - expected| = 0.0000".
Descending: "Slicing source bathymetry to domain: (-60.0, -56.0) x (30.0, 34.0) with buffer 0.5", then "EXCEPTION: IndexError index 1 is out of bounds for axis 0 with size 0", raised at mom6_forge/topo.py:1180 `dlat_deg = float(abs(src.lat[1] - src.lat[0]))`, with "src.ds sizes after slicing: {'lat': 0, 'lon': 10}".
Descending plus sortby patch: "OK depth min/max = 1302.50 / 1337.50", "max |depth - expected| = 0.0000".

**Root cause.** _slice_to_domain assumes the source lat coordinate is ascending. xarray's .sel(slice(lo, hi)) on a decreasing index returns an empty selection rather than raising. The code never checks the latitude order or whether the slice is empty, so the first index access (diagnose_resolution's src.lat[1]) fails far from the cause. longitude_slicer handles longitude conventions, but nothing handles latitude order.

**Smallest fix.** In SourceBathy._slice_to_domain, before the lat .sel, add self._ds = self._ds.sortby(self.lat_name), or reverse the slice bounds when lat[0] > lat[-1]. After slicing, raise a ValueError naming the file and the requested lat range if self._ds.sizes[self.lat_name] < 2 (and likewise for lon). A monkeypatch with sortby was checked to give exact results on the repro.

### M10. Topo.generate_mask_from_landfrac_file always reads ds.landfrac and ignores landfrac_name, xcoord_name and ycoord_name

- **Repo:** mom6_forge
- **Severity:** crash
- **Evidence:** confirmed by repro (audit id `mom6_forge-a11`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/topo.py:1969 (hardcoded ds.landfrac); topo.py:1966-1968 (Regridder built from the whole ds, without using xcoord_name/ycoord_name, which are checked at topo.py:1939-1942)
- **Already fixed on main:** No. mom6_forge origin/main 83d7692 (2 commits ahead of pin d74c851: #126, #155) still has `mask_mapped = regridder(ds.landfrac)` at topo.py:1974 and the same unused xcoord_name/ycoord_name.
- **Related:** none (mom6_forge #123 "Masking Operation switch to 2D Array Mask" is an unrelated masking performance issue; not in TRIAGE.md or QUEUE.md)

**What's wrong.** generate_mask_from_landfrac_file(landfrac_filepath, landfrac_name, xcoord_name, ycoord_name, ...) checks that landfrac_name, xcoord_name and ycoord_name exist in the file, then ignores all three. (1) It regrids ds.landfrac, so the data variable must be named literally 'landfrac'. Any other name, such as CAM/CLM's LANDFRAC, raises AttributeError: 'Dataset' object has no attribute 'landfrac'. (2) If the file has a 'landfrac' variable and the caller asks for a different field, the method silently builds the mask from 'landfrac' (wrong mask, no error). (3) xcoord_name and ycoord_name are never used. xe.Regridder(ds, ...) looks up 'lon'/'lat' itself or falls back to CF attributes, so coordinates with other names and no CF units fail with xESMF's ValueError 'dataset must include lon/lat or be CF-compliant'. This happens even though the caller named the coordinates and the method's asserts passed.

**Who hits it.** The public Topo API (mom6_forge.topo.Topo, re-exported as CrocoDash.topo.Topo): topo.generate_mask_from_landfrac_file(path, 'LANDFRAC', 'lon', 'lat'), or any landfrac_name other than 'landfrac'. Also any file whose lon/lat coordinates have other names (e.g. 'x'/'y') and no CF units attributes. No CrocoDash Case/forcing flow calls this method; users call it directly, as in the mom6_forge docs notebook 4_ingest_landmask.ipynb.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a11 && timeout 900 $PY -u repro.py
Script: dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a11/repro.py. It builds a 10x10, 1-degree Grid at (-60, 30), runs Topo(grid, min_depth=10.0).set_flat(1000.0), and writes a synthetic 0.5-degree land-fraction file (land west of -55, ocean east). Then:
  t.generate_mask_from_landfrac_file(path_with_var_LANDFRAC, 'LANDFRAC', 'lon', 'lat')
  t.generate_mask_from_landfrac_file(path_with_landfrac_zeros_and_frac, 'frac', 'lon', 'lat')
  t.generate_mask_from_landfrac_file(path_with_coords_x_y, 'landfrac', 'x', 'y')

- Expected: The method regrids the variable named by landfrac_name, using the coordinates named by xcoord_name/ycoord_name. In the repro every case should give the same mask as the baseline file (variable 'landfrac', coords lon/lat): 50/100 ocean cells, first row [0,0,0,0,0,1,1,1,1,1].
- Observed: Baseline (var 'landfrac', coords lon/lat): OK, ocean cells=50/100.
var 'LANDFRAC': "FAIL AttributeError: 'Dataset' object has no attribute 'landfrac'" at topo.py line 1969, `mask_mapped = regridder(ds.landfrac)`.
File with 'landfrac' (all zeros) plus 'frac' (west half land), asking for 'frac': no error, but "ocean cells=100/100 first row=[1,1,1,1,1,1,1,1,1,1]". The 'landfrac' field was used, so the mask is wrong.
coords x/y with no CF attributes: "FAIL ValueError: dataset must include lon/lat or be CF-compliant" (from xesmf _get_lon_lat).
coords longitude/latitude with units degrees_east/degrees_north: OK (cf_xarray finds them), so only non-CF coordinate names fail.
With a monkeypatched fix (select ds[landfrac_name] and rename the coords to lon/lat), all three failing cases give the expected 50/100 mask.

**Root cause.** The field name is hardcoded as the attribute access ds.landfrac at topo.py:1969, not ds[landfrac_name]. The whole Dataset goes to xe.Regridder (topo.py:1966-1968) without renaming xcoord_name/ycoord_name to the lon/lat names xESMF looks for, so those two arguments are only checked, never used.

**Smallest fix.** In topo.py, after the asserts: `src = ds[[landfrac_name]].rename({xcoord_name: "lon", ycoord_name: "lat"})` (skip renaming any name that is already lon/lat), then `regridder = xe.Regridder(src, ds_mapped, method, periodic=...)` and `mask_mapped = regridder(src[landfrac_name])`. Closing ds afterwards (or opening it with a `with` block) also avoids leaving the file handle open.

### M11. Grid.from_supergrid rejects FRE make_hgrid files (x "degree_east", y "degree_north") with "Only degrees units are supported", even though check_supergrid accepts them

- **Repo:** mom6_forge
- **Severity:** misleading error
- **Evidence:** confirmed by repro (audit id `mom6_forge-a10`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/grid.py:677
- **Already fixed on main:** No. On mom6_forge origin/main (83d7692) the same assertion is still in from_supergrid_ds (grid.py:679-681). #155 renamed from_supergrid to from_supergrid_file and kept from_supergrid as an alias, but did not change the units check. A fix is needed upstream, then a pin bump.
- **Related:** none. No matching open issue or PR in NCAR/mom6_forge, CrocoDash, visualCaseGen or regional-mom6, and nothing in TRIAGE.md or QUEUE.md. CrocoDash #343 (1.1: name grid files in the create config) will make loading existing hgrid files through from_supergrid a main path, which raises the impact of this bug.

**What's wrong.** Grid.from_supergrid_ds starts with `assert ds.x.units == ds.y.units and "degree" in ds.x.units, "Only degrees units are supported in supergrid files"`. Every degree hgrid whose x and y unit strings differ fails this check. That includes the standard FRE-NCtools make_hgrid output (x "degree_east", y "degree_north"). Such a file cannot be loaded, and the error says it is not in degrees when it is. The Grid.check_supergrid call two lines later explicitly allows different strings as long as both contain "degree", so the two checks disagree.

**Who hits it.** Loading any FRE-NCtools make_hgrid ocean_hgrid.nc (or any hgrid whose x/y units differ but are both degrees) through:
- Grid.from_supergrid(path)
- Grid.subgrid_from_supergrid(path, llc, urc, name)
- a CrocoDash create YAML with grid: {supergrid_path: ...} (CrocoDash/recipe.py:88 build_grid)
- the mom6_forge GridCreator "load from file" widget (grid_creator.py:1167)
CrocoDash's own Case-written hgrids use "degrees" and are not affected.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a10 && timeout 900 $PY -u repro_units.py

Key lines of the script:
g0 = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a10")
ds = g0.supergrid.to_ds()
ds["x"].attrs["units"] = "degree_east"   # FRE make_hgrid strings
ds["y"].attrs["units"] = "degree_north"
ds.to_netcdf("fre_style_hgrid.nc")
Grid.check_supergrid(xr.open_dataset("fre_style_hgrid.nc"))   # passes
Grid.from_supergrid("fre_style_hgrid.nc")                       # AssertionError
build_grid({"supergrid_path": "fre_style_hgrid.nc"})            # CrocoDash.recipe, same AssertionError

- Expected: A supergrid whose x and y coordinates are both in degrees (degree_east/degree_north, the CF and FRE-NCtools convention) loads as a Grid, as check_supergrid's own rule already allows.
- Observed: mom6_forge writes x/y units: degrees degrees
check_supergrid accepts degree_east/degree_north: OK
[FRE-style from_supergrid] AssertionError: Only degrees units are supported in supergrid files
[FRE-style CrocoDash recipe build_grid] AssertionError: Only degrees units are supported in supergrid files
[FRE-style from_supergrid (patched)] OK: nx=8 ny=8 tlon.units='degrees_east' tlat.units='degrees_north'
  tlon/tlat identical to original: True  tarea identical: True

**Root cause.** from_supergrid_ds checks units more strictly than check_supergrid: it requires identical x/y unit strings instead of "degree" in both. A second problem sits behind it. SupergridBase.from_ds keeps ds.x.units as the single axis_units label (_supergrid.py:1074). That label is reused for latitudes in _compute_MOM6_grid_metrics (grid.py:786-834, which only maps the exact string "degrees"), in to_ds/write_supergrid and in Topo.write_scrip_grid. So relaxing only the assertion would label latitudes "degree_east" in written files.

**Smallest fix.** In Grid.from_supergrid_ds:
1. Replace the assertion with `assert "degree" in ds.x.units and "degree" in ds.y.units` (keeping the message, or naming the units actually found).
2. Normalise the labels before building the supergrid: `ds = ds.copy(); ds.x.attrs["units"] = ds.y.attrs["units"] = "degrees"`. Without this, axis_units becomes "degree_east" and latitudes are mislabelled in written grid and SCRIP files.
Verified by monkeypatch: the grid loads with tlon/tlat/tarea identical to the source.

### M12. mom6_forge grid files carry wrong units attributes: CICE grid tlat/tlon are radians labelled degrees_north/degrees_east, and hgrid angle_dx is degrees labelled radians

- **Repo:** mom6_forge
- **Severity:** cosmetic
- **Evidence:** confirmed by repro (audit id `mom6_forge-a12`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/topo.py:2179 (tlat 'degrees_north') and :2189 (tlon 'degrees_east') in Topo.write_cice_grid; CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/_supergrid.py:389 (angle_dx 'radians') in SupergridBase.to_ds
- **Already fixed on main:** No. mom6_forge origin/main (83d7692, 2 commits ahead of the d74c851 pin: #126 and #155) still has angle_dx attrs={'units': 'radians'} in _supergrid.py and tlat/tlon 'degrees_north'/'degrees_east' in topo.py write_cice_grid (lines 2195/2205 there).
- **Related:** none (CrocoDash #189 'Self-describing output from mom6_bathy' is about provenance metadata and is not this bug)

**What's wrong.** Topo.write_cice_grid writes tlat = np.deg2rad(grid.tlat) and tlon = np.deg2rad(grid.tlon) but labels them units='degrees_north' and 'degrees_east'. The other angle variables in the same file (ulat, ulon, angle, anglet) are correctly labelled 'radians'. SupergridBase.to_ds, which Grid.write_supergrid uses to write ocean_hgrid, stores angle_dx in degrees but labels it units='radians'. mom6_forge's own Grid.angle and Grid.angle_q hold the same values and label them 'degrees', and degrees is also the FRE-NCtools hgrid convention. The models are unaffected: CICE reads ulat/ulon/angle and, because anglet is present, also anglet/tlon/tlat, all as radians without checking the attribute; MOM6 never reads angle_dx; rm6 applies np.radians to angle_dx. Any tool that trusts the units attribute (cf_xarray, pint, plotting or user scripts) is off by a factor of about 57.3.

**Who hits it.** Any CrocoDash case: Case() always writes ocean_hgrid through Grid.write_supergrid (case.py:394). Any compset with CICE also writes cice_grid_*.nc through Topo.write_cice_grid (case.py:415). The same happens when a user calls grid.write_supergrid() or topo.write_cice_grid() directly. The wrong values appear only when a units-aware tool or user reads the files.

**Repro.**

source .../scratchpad/audit/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/mom6_forge-a12 && timeout 900 $PY -u units_attrs.py && timeout 300 $PY -u consumer.py
Key lines of units_attrs.py:
  g = Grid.from_center(center_lat=32.0, center_lon=-60.0, width_m=200e3, height_m=200e3, resolution_m=20e3, angle_deg=30.0, name="a12"); g.write_supergrid("hgrid.nc")
  g2 = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="a12b"); t = Topo(g2, min_depth=10.0); t.set_flat(1000.0); t.write_cice_grid("cice_grid.nc")
  then print the units attribute and min/max of hgrid angle_dx and of cice ulat/ulon/tlat/tlon/angle/anglet.
consumer.py: cf_xarray c.cf["latitude"] on cice_grid.nc; pint Quantity(angle_dx[0,0], angle_dx.attrs["units"]).to("degree").

- Expected: Each units attribute matches the stored values. cice_grid tlat/tlon should say 'radians', like ulat/ulon in the same file. hgrid angle_dx should say 'degrees', which matches the FRE-NCtools convention and mom6_forge's own Grid.angle. A CF/units-aware reader then gets latitudes of 30.25..33.75 deg and an angle_dx of about -30 deg.
- Observed: hgrid angle_dx attrs: {'units': 'radians'}; angle_dx min/max: -30.62 -29.15 (degrees). Grid.angle holds the same values with units 'degrees'.
cice ulat: units='radians' min=0.5323 max=0.5934
cice tlat: units='degrees_north' min=0.5280 max=0.5890   (source g2.tlat is 30.25..33.75 deg)
cice tlon: units='degrees_east' min=-1.0428 max=-0.9817
cf_xarray picks latitude = tlat units degrees_north range 0.528 0.589
pint reading angle_dx[0,0] via its units attr -> -1671.07 degree

**Root cause.** The writers set the units attributes by hand and do not match the conversions applied to the values. In write_cice_grid, tlat/tlon go through np.deg2rad like ulat/ulon, but they kept the CF degree labels. In to_ds, angle_dx comes from mom6_angle_calculation_method, which returns degrees (np.rad2deg at _supergrid.py:1685), but it is labelled 'radians'.

**Smallest fix.** Change only the attributes. In topo.py write_cice_grid, set the tlat and tlon units to 'radians', matching ulat/ulon. In _supergrid.py SupergridBase.to_ds, set the angle_dx units to 'degrees'. Do not change the stored values: CICE popgrid_nc reads tlat/tlon/anglet as radians, and rm6 applies np.radians to angle_dx.

## visualCaseGen

ESMCI/visualCaseGen, pinned at CrocoDash/visualCaseGen (0eb6fd6, the same commit as ESMCI main).

### V1. A second Case() in the same Python process with a different cesmroot reads the first CESM's compsets, grids and machines

- **Repo:** visualCaseGen
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `vcg-a4`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/visualCaseGen/cime_interface.py:54 (sys.path.append) and :149-152 (from CIME.XML.files import Files; Files(...)); reached from CrocoDash/case.py:138-143
- **Already fixed on main:** No (target is main). The vCG pin 0eb6fd6 is ESMCI main, and origin/main's cime_interface.py still has the bare sys.path.append at line 54. There are no open visualCaseGen PRs, and no CrocoDash PR touches this.
- **Related:** Different bug, same multiple-Cases-per-process pattern: CrocoDash #250 (CASEROOT singleton, TRIAGE "needs details" row; real fix #326). The same sys.path.append-then-import pattern appears in CrocoDash/shareable.py:754-755 (_get_case_obj; shareable is deleted in 1.1 #342) and CrocoDash/forcing/cdeps_streams.py:28-50 (_ensure_cime, and the loose stream_cdeps module, which also stays cached from the first CESM). vCG CaseCreator prints "To create another case, restart the notebook." in GUI mode, but CrocoDash's Case API reboots vCG on every Case and does not tell users this.

**What's wrong.** CIME_interface.__init__ appends <cesmroot>/cime to the end of sys.path and then imports CIME (cime_interface.py:149, plus the later CIME imports in _retrieve_*). CIME's Files() locates its config through get_cime_root(), which takes the path from CIME/utils.py's own __file__. After the first CESM tree's CIME package is in sys.modules, every later CIME_interface(cesmroot=B) uses tree A for compsets (COMPSETS_SPEC_FILE), component config, grids and meshes (config_grids, domains), machines (MACHINES_SPEC_FILE) and CLM data. Only cimeroot/srcroot point at B, so B's create_newcase script and B's ccs_config are the ones that get used and edited. CrocoDash creates a new CIME_interface for every Case (case.py:138) and resolves aliases with self.cime.compsets (case.py:141-143). For a Case against B this has three effects. (a) An alias that exists only in B is refused. (b) An alias defined differently in the two trees resolves to A's long name. CrocoDash's compset-derived logic (runoff_in_compset, the ForcingConfigRegistry, the ROF grid xmlchanges) then follows A, while B's create_newcase builds the case from B's definition. (c) _max_tasks_per_node (case.py:1009-1012), get_mesh_path and get_case all use A's CIME and XML.

**Who hits it.** Any one Python process (a notebook, a script, a pytest session or the long-lived CrocoDash MCP server, which calls Case() in-process) that creates a CrocoDash Case against one CESM checkout and then another Case against a different checkout. Example: CESM_crocodash, then CESM_wu2r05. The two MOM_interface versions differ: CR_JRA is ..._DROF%GLOFAS_... in CESM_crocodash and ..._SROF_... in CESM_wu2r05, and CR_JRA_GLOFAS exists only in CESM_wu2r05.

**Repro.**

source .../scratchpad/audit/env.sh; unset CESMROOT; cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a4
(1) timeout 900 $PY -u two_roots.py ~/work/installs/CESM_crocodash ~/work/installs/CESM_wu2r05   # CIME_interface(A) then CIME_interface(B); compare with: two_roots.py ~/work/installs/CESM_wu2r05 (fresh)
(2) timeout 900 $PY -u case_repro.py after_A   # real tiny NYF Case(cesmroot=CESM_crocodash), then Case(cesmroot=CESM_wu2r05, compset='CR_JRA_GLOFAS' / 'CR_JRA', atm_grid_name='TL319'); init_args_check is wrapped to print compset_lname and stop. Control: case_repro.py fresh
(3) timeout 900 $PY -u case_full_b.py after_A   # same, but lets Case B (CR_JRA) run to completion; control: case_full_b.py fresh
(4) fix_check.py: monkeypatched guard that refuses B once CIME was loaded from A

- Expected: Case(cesmroot=B) should use B's CIME and XML config, exactly as in a fresh process (CR_JRA_GLOFAS accepted, CR_JRA -> 1850_DATM%JRA-1p5-2023_SLND_DICE%SSMI_MOM6%REGIONAL_SROF_SGLC_SWAV, no ROF_GRID xmlchange). If that is impossible, it should refuse with a clear message that CIME is already loaded from A and the process must be restarted.
- Observed: (1) Second object, cesmroot=CESM_wu2r05: "ci.cimeroot = .../CESM_wu2r05/cime", but "CIME.__file__ = .../CESM_crocodash/cime/CIME/__init__.py", "MACHINES_SPEC_FILE = /glade/work/manishrv/installs/CESM_crocodash/ccs_config/machines/config_machines.xml", "COMPSETS_SPEC_FILE mom= .../CESM_crocodash/components/mom//cime_config/config_compsets.xml", "n compsets = 325", "'CR_JRA_GLOFAS' in compsets = False". In a fresh process B has 332 compsets and CR_JRA_GLOFAS = True.
(2) After case A: "== Case(cesmroot=CESM_wu2r05, compset='CR_JRA_GLOFAS') ... WARNING [CIME.XML.grids] Schema validity test fails for /glade/work/manishrv/installs/CESM_crocodash/ccs_config/config_grids_nuopc.xml ... AssertionError: compset must be a valid CESM compset long name or alias." and "compset='CR_JRA' ... compset_lname used by CrocoDash = 1850_DATM%JRA-1p5-2023_SLND_DICE%SSMI_MOM6%REGIONAL_DROF%GLOFAS_SGLC_SWAV". Fresh: CR_JRA_GLOFAS passes, and CR_JRA -> "..._MOM6%REGIONAL_SROF_SGLC_SWAV".
(3) After case A, CrocoDash runs "/glade/u/home/manishrv/work/installs/CESM_wu2r05/cime/scripts/create_newcase --compset CR_JRA ..." (an SROF compset in B), then writes "./xmlchange ROF_GRID=GLOFAS" and "./xmlchange ROF_DOMAIN_MESH=.../GLOFAS.v4.dis24.ESMFmesh_20260501.nc" into that case. The fresh-process run of the same call issues no ROF xmlchanges. In both modes case.setup on CESM_wu2r05 then fails for an unrelated environment reason, so the run never got further.
(4) With the guard patched in, A, A again: ok; B: "CIME is already loaded from /glade/work/manishrv/installs/CESM_crocodash/cime in this Python process; cannot switch to .../CESM_wu2r05/cime."

**Root cause.** Python caches the CIME package in sys.modules on first import. Appending another cimeroot to sys.path (at the end, too) never re-imports it. CIME's get_cime_root(), get_config_path() and get_schema_path() derive every config path from the loaded module's __file__, so Files() and everything built on it describe the first tree. Nothing checks that the imported CIME is the one under self.cimeroot. CrocoDash creates a new CIME_interface per Case (case.py:138) on the assumption that this gives a clean per-cesmroot view, and it does not.

**Smallest fix.** In CIME_interface.__init__, after _set_cimeroot: if 'CIME' is in sys.modules and Path(sys.modules['CIME'].__file__).resolve().parent.parent != self.cimeroot.resolve(), raise RuntimeError("visualCaseGen already loaded CIME from <A> in this process; restart the kernel/process to use <B>"). Compare resolved paths: ~/work is a symlink to /glade/work, so unresolved paths differ even for the same tree. Append the root to sys.path only if it is not already there. This was verified by monkeypatch (fix_check.py). Purging and re-importing CIME is not recommended because CIME keeps module-level state.

### V2. Custom-grid cases keep create_newcase's USER_RES placeholder ROF_NX/ROF_NY (rx1 360x180 for GLOFAS) and ATM/LND_NX/NY=0, so the coupler restart truncates runoff fields

- **Repo:** visualCaseGen
- **Severity:** wrong result
- **Evidence:** confirmed by repro (audit id `vcg-a8`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_creator.py:960 (ATM_GRID), :962 (LND_GRID), :968-970 (ROF_GRID); also :955-956 (standard WAV_GRID). Missing NX/NY xmlchanges in _update_component_grids_xml.
- **Already fixed on main:** No (target is ESMCI/visualCaseGen main; pin 0eb6fd6 == ESMCI main, and no open visualCaseGen PR or local branch adds the NX/NY xmlchanges)
- **Related:** none (visualCaseGen #47 covers other case_creator.py defects; TRIAGE item 13 / CrocoDash #232 is a different grid constraint)

**What's wrong.** CrocoDash builds CaseCreator with add_grids_to_ccs_config=False (CrocoDash/case.py:480), so create_newcase runs with --res USER_RES. The USER_RES alias is empty, so the ATM and LND grids start as null (NX/NY=0) and the ROF grid gets the model_grid_defaults value for DROF, rx1 (360x180). _update_component_grids_xml then xmlchanges ATM_GRID, LND_GRID and ROF_GRID and their DOMAIN_MESH, but not their NX/NY. It does set NX/NY for OCN, ICE and WAV. The result for any DROF%GLOFAS compset is ROF_GRID=GLOFAS with the GLOFAS mesh (7200x3000 = 21.6M elements) but ROF_NX=360 and ROF_NY=180, plus ATM_NX/NY=0 and LND_NX/NY=0. GRID keeps the stale long name a%null_l%null_oi%null_r%rx1_.... DROF's namelist takes nx_global/ny_global from $ROF_NX/$ROF_NY (namelist_definition_drof.xml), and the generated drof_in has nx_global = 360 and ny_global = 180. DROF exports these to the mediator. med_phases_restart_write passes them to med_io_write, which only logs a 'grid2d size not consistent' warning, defines rofImp_nx=360 and rofImp_ny=180, and writes the rof import and fraction fields into those 64,800 slots. The cpl.r file therefore holds only the first 64,800 GLOFAS points (lat -59.975..-59.575) and drops the other 99.7%. On a continue run, med_io_read_init_iodesc reads with the file's 360x180 dims and only warns when ng > grid size, so it does not warn here. ATM_NX/NY=0 is harmless (the mediator falls back to a 1-D layout: atmImp_nx=204800, atmImp_ny=1). The run does not crash, and I found nothing showing the ocean solution changes. On a restart the truncated rofImp should reach only med_phases_diag_rof before DROF refreshes it; that is reasoned from nuopc.runseq, not run.

**Who hits it.** Any CrocoDash case with a data runoff component: CR_JRA, CWR_JRA, CR_JRA_RYF, CWR_JRA_RYF, GR_JRA, GWR_JRA, CR1850MARBL_JRA, GR1850MARBL_JRA (all DROF%GLOFAS), created through Case(), the CLI or YAML. ATM/LND_NX/NY=0 and the stale GRID long name affect every CrocoDash case but are only cosmetic.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; cd dev/crocodash_1_0_x/audit_repros/verify/vcg-a8 && timeout 900 $PY -u repro.py
Key lines: Grid(lenx=4, leny=4, resolution=0.5, xstart=-60, ystart=30); Topo.set_flat(1000); VGrid.uniform(nk=5, depth=1000); Case(compset="CR_JRA", atm_grid_name="TL319", machine="derecho", override=True). The script then parses env_build.xml with ElementTree (no xmlquery). Fix check: fixtest.py, in the same dir, monkeypatches CaseCreator._update_component_grids_xml to also xmlchange <COMP>_NX/NY from self._cime.domains[comp][grid]. Runtime corroboration (existing CrocoDash CLI SMS run, read-only): ncdump -h /glade/derecho/scratch/manishrv/SMS_D_Ld2.USER_RES.CR_JRA_GLOFAS.derecho_intel.crocodash.20261106_140157/run/*.cpl.r.2020-01-03-00000.nc, plus grep nx_global run/drof_in.

- Expected: ROF_NX=7200 and ROF_NY=3000 (component_grids_nuopc.xml, domain GLOFAS), ATM_NX/LND_NX=640 and ATM_NY/LND_NY=320 for TL319. drof_in should have nx_global=7200 and ny_global=3000, and the cpl.r rof fields should cover all 21.6M GLOFAS points.
- Observed: repro.py: GRID = a%null_l%null_oi%null_r%rx1_g%null_w%null_z%null_m%null; ATM_GRID = TL319, ATM_NX = 0, ATM_NY = 0; LND_NX = 0, LND_NY = 0; OCN_NX = 8, ICE_NX = 8 (correct); ROF_GRID = GLOFAS, ROF_NX = 360, ROF_NY = 180, ROF_DOMAIN_MESH = .../GLOFAS.v4.dis24.ESMFmesh_20260501.nc. The real CrocoDash SMS run (TestStatus: PASS RUN) has the same XML, with drof_in 'nx_global = 360', 'ny_global = 180'. Its cpl.r has dimensions 'rofImp_nx = 360 ; rofImp_ny = 180', and rofImp_lat spans only -59.975..-59.575, i.e. the first 9 of 3000 GLOFAS rows. Also 'atmImp_nx = 204800 ; atmImp_ny = 1'. With the fix monkeypatched: ATM_NX = 640, ATM_NY = 320, LND_NX = 640, LND_NY = 320, ROF_NX = 7200, ROF_NY = 3000.

**Root cause.** In the xmlchange grid path (add_grids_to_ccs_config=False), create_newcase uses the empty USER_RES alias, so NX/NY are filled from null grids or model_grid_defaults (DROF -> rx1). _update_component_grids_xml later swaps ATM_GRID, LND_GRID and ROF_GRID (and, for a standard wave grid, WAV_GRID) plus their meshes, but copies NX/NY only for the components that share the custom ocean grid. CDEPS takes nx_global/ny_global from <COMP>_NX/NY, and CMEPS uses them as the 2-D dims for restart and history I/O.

**Smallest fix.** In _update_component_grids_xml, after each ATM_GRID, LND_GRID, ROF_GRID and standard-WAV_GRID xmlchange, add xmlchange("<COMP>_NX", self._cime.domains[comp][grid].nx) and the same for _NY. The ComponentGrid namedtuple in cime_interface.py:18 already carries nx and ny. Verified by monkeypatch: this gives ATM 640x320, LND 640x320 and ROF 7200x3000. Optionally also set GRID to a consistent long name, which is cosmetic.

### V3. A failing case.setup inside Case() raises only "Error running ./case.setup." and the caseroot with CaseStatus is then deleted, so the reason is lost

- **Repo:** visualCaseGen
- **Severity:** misleading error
- **Evidence:** confirmed by repro (audit id `vcg-a6`)
- **Confidence:** high
- **Location:** CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_tools.py:48 (subprocess.run with capture_output=True), CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_tools.py:50 (raise without output). Reached from CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_creator.py:166 <- CrocoDash/case.py:483 (cc.create_case) <- CrocoDash/case.py:220. The deletion is at CrocoDash/case.py:238-239 -> CrocoDash/case.py:41-49 (_remove_failed_attempt).
- **Already fixed on main:** No. The pin 0eb6fd6 equals ESMCI/visualCaseGen main (checked with gh api: main sha 0eb6fd62, same run_case_setup code), and no open PR in ESMCI/visualCaseGen fixes it. CrocoDash PR #357 adds a separate case.setup --reset that does include stderr but leaves run_case_setup unchanged.
- **Related:** visualCaseGen #25 (create_newcase output capture; that path now prints stderr). visualCaseGen #21 / TRIAGE item 12 (double misleading error from a failed CaseCreator; different bug). CrocoDash PR #357 / #354 / TRIAGE item 2 (adds its own case.setup --reset with stderr in the message; the pattern to copy). visualCaseGen #47 (other small case_creator defects).

**What's wrong.** run_case_setup runs `./case.setup [--non-local]` with capture_output=True. On a nonzero exit it raises RuntimeError(f"Error running {cmd}.") and drops both runout.stdout and runout.stderr, where CIME writes its "ERROR: ..." line. When this runs inside CrocoDash's Case(), the RuntimeError reaches case.py's `except BaseException`, and _remove_failed_attempt deletes the new caseroot and inputdir. That also removes CaseStatus, the only other place CIME recorded the error. The user sees "Error running ./case.setup --non-local." with no cause and no case directory left to inspect. The create_newcase call next to it prints runout.stderr, and xmlchange puts stderr in its exception message; only case.setup loses it.

**Who hits it.** Any nonzero exit of ./case.setup during Case() construction, for example a PE-layout or machine-environment problem, a permissions problem in the caseroot, or a setup problem specific to non-local cases. The repro uses a read-only LockedFiles/ dir, which makes the real CIME case.setup fail at its lock-file copy step.

**Repro.**

source dev/crocodash_1_0_x/audit_repros/env.sh; D=dev/crocodash_1_0_x/audit_repros/verify/vcg-a6; cd $D && timeout 900 $PY -u repro_setup_fail.py $D   (script: $D/repro_setup_fail.py, log: $D/run1.log). Key lines: subprocess.run is wrapped so that, for a str cmd starting with "./case.setup", it first runs os.chmod(Path(kw['cwd'])/'LockedFiles', 0o555), then calls the REAL subprocess.run and records rc/stdout/stderr/CaseStatus. Then a tiny Case(): Grid(lenx=2, leny=2, resolution=0.5, xstart=-60, ystart=30) with flat 1000 m topo, VGrid.uniform(nk=5), compset 1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV, atm_grid_name="T62", machine="derecho", override=True, case name audit_vcga6_1. The script prints the exception, the captured case.setup stderr, and caseroot.exists().

- Expected: The exception raised from Case() includes case.setup's error output, here "ERROR: Command: '/usr/bin/cp -f -r .../env_mach_pes.xml .../LockedFiles/env_mach_pes.xml' failed with error '... Permission denied'". Alternatively, the CaseStatus record survives somewhere the user can read it.
- Observed: What the user gets: "RuntimeError: RuntimeError('Error running ./case.setup --non-local.')", "__cause__: None", preceded by "Removing files from the failed attempt: .../input/audit_vcga6_1" and "Removing files from the failed attempt: .../cases/audit_vcga6_1". Finally "caseroot exists now: False". The wrapper shows that case.setup itself exited rc=1 with stderr "ERROR: Command: '/usr/bin/cp -f -r .../cases/audit_vcga6_1/env_mach_pes.xml .../LockedFiles/env_mach_pes.xml' failed with error '/usr/bin/cp: cannot create regular file ...: Permission denied'". The same text was in CaseStatus ("case.setup error / ERROR: Command: ..."), and both were discarded or deleted.

**Root cause.** case_tools.run_case_setup captures case.setup's stdout and stderr but never prints them and never puts them in the RuntimeError (and uses no text=True). CrocoDash's Case() treats any exception as a failed attempt and rmtree's the caseroot, deliberately so that a retry is not refused. That removes CaseStatus, the only on-disk copy of the CIME error. Together they leave no trace of why setup failed.

**Smallest fix.** In visualCaseGen case_tools.run_case_setup, run with capture_output=True, text=True. On a nonzero exit, raise RuntimeError(f"Error running {cmd} in {caseroot}:\n{runout.stderr}"), optionally with the tail of runout.stdout. This matches xmlchange in the same file and the `case.setup --reset` call in CrocoDash PR #357. No change is needed in CrocoDash's cleanup once the message carries the reason.

## Added after the audit: 13 findings checked by hand (2026-11-06 evening and night)

Found while checking the *Not covered* items directly, without agents. H1–H4, H6–H9, H11 and H12 were confirmed by a repro. H5 and H10 were confirmed by real model runs on Derecho (develop queue, 1 task). H13 was confirmed against a live CDS download. H5 is from reading the MOM6 source, and the weekly CESM tests saw it fail. None had a separate verifier. Repros are in `audit_repros/extra/`.

### H1. `crocodash dump > file.yaml`, as the docs show, writes log lines into the YAML, so `crocodash create --config file.yaml` fails

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

### H2. Runoff coastline mask wraps around on non-cyclic grids, so the edge opposite a land edge counts as coast and receives runoff

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

### H3. Runoff mapping fails with "nearest neighbor map maps no runoff at all" for every domain south of 60°S (the GLOFAS grid stops there) and for all-ocean domains

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

### H4. `VGrid.from_file` crashes with AttributeError when given a `pathlib.Path`

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

### H5. MOM6 silently drops the end of INPUTDIR paths of 128 characters or more, and CrocoDash doesn't check, so runs fail with "Unable to open OBC file .../ocnforcing_obc_..."

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

### H6. A time of day in date_range is silently dropped: the run starts at 00:00 (START_TOD=0)

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

### H7. Case(override=True) can't recreate a case made for another machine (e.g. ubuntu-latest from Casper): it cleans the host's CIME_OUTPUT_ROOT, so create_newcase aborts on the old bld/run dirs

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

### H8. chl processing refuses every grid except a plain lat-lon `Grid()`: process_forcings fails late with "This function currently only supports rectangular grids"

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

### H9. `Grid.subgrid_from_supergrid` fails with "Lower left corner must be to the left of upper right corner" for valid boxes across the parent grid's x-seam or inside its tripolar cap

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

### H10. An inputdir containing a space makes the model abort during initialisation, with no message naming the path

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

### H11. A MARBL compset with GLORYS (the default product) fails in configure_forcings with "This product does not have marbl tracer var names", which doesn't say what to use instead

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

### H12. CESM_MOM_OUTPUT reads MOM6 output from a Gregorian-calendar run 2 days early, so nested boundary data is shifted by 2 days, or comes back empty near the end of the record

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

### H13. ERA5 2D wave spectra are already "going to", but CrocoDash treats them as "coming from" and flips them 180°, so ERA5-forced WW3 boundaries send waves the wrong way

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

## Not filed

- **Cross-area duplicates (merged above, not verified twice):**
  - rm6-a1 → C1 (POP velocities);
  - rm6-a3 → C4 (TIDE_M2);
  - creation_cli-a12 → C14 (machine=None);
  - vcg-a1 → C9/C10/C11 (paths);
  - raw_data-a3 → C2 (truncated files on resume).
- **Already known:** `creation_cli-a11`, which gives every domain at least the 2-node S PE tier (128 MOM6 ranks, never XS), is CrocoDash #350 (1.1 `pe-layout`). It is real and reproduced. Consider pulling #350 into 1.0.x, together with TRIAGE item 2.
- **Already known, seen again by hand:** polar IC/OBC currents come out with the wrong rotation sign (they correlate 0.86 with east/north rotated by −angle and −0.28 with +angle, while hgrid angle_dx is geometrically right). That is regional-mom6 PR #74 (open, "Fix IC/OBC velocity rotation sign"). On a polar grid it affects every current, so #74 matters for any polar case. The GLORYS CLI script's .sh/.pbs mismatch is TRIAGE (line 25) and noted under R2.
- **CrocoGallery (outside the four audited repos):** `known_paths.json` TX2_3V3_GRID points at `/glade/campaign/cesm/community/omwg/grids/tx2_3v3_grid.nc`. That file doesn't exist (`community/omwg` is gone), so `crocodash/projects/cice.ipynb` would fail in `get_cice_restart_subset` with "Provided grid_path ... does not exist". A matching grid is in inputdata at `ocn/mom/tx2_3v3/cice_grid_tx2_3v3_260305_cdf5.nc`: the same 480x540 as the restart, with coordinates in radians (tlat/tlon mislabelled degrees, as in M12). The hand check used that file.
- **Not reachable from CrocoDash:** `rm6-a5`. regional-mom6 `MOM_parameter_tools.change_MOM_parameter(delete=True)` crashes on uncommented parameters and deletes other parameters whose lines contain the name and value. It reproduces, but no CrocoDash flow calls it, because CrocoDash configures MOM6 through user_nl_mom. It is optional to file on the fork; details are in verifier_results.json.

## Cleanup

The audit's CIME bld/run dirs (`/glade/derecho/scratch/manishrv/audit_*`) and the `temp_case-*` dirs leaked by bundle runs (that is C13.8) were removed afterwards. The audit worktree `regional_mom_workflows/CrocoDash-worktrees/audit` is kept for reruns.

After the hand checks, the run-test cases and their CIME, archive and input directories (`audit_rA`–`audit_rE`, `audit_gwre`, `audit_marbl*`, `/glade/derecho/scratch/manishrv/ar`) were removed too. **One side effect was not cleaned:** submitting `audit_rE` (C9's run-time check) made CIME create three empty directories in the shared inputdata tree, `/glade/campaign/cesm/cesmdata/inputdata/i/rA/ocn`. They were left alone because inputdata is off-limits for the audit. They can be removed with `rmdir -p /glade/campaign/cesm/cesmdata/inputdata/i/rA/ocn`.

## Areas checked and found fine

From the six reviewers' own lists, each with how it was checked. Nothing here was independently re-verified.

### CrocoDash creation, CLI and recipes

- Case() for NYF, GWR_JRA (CICE+WW3), GR_JRA, CR1850MARBL_JRA (alias): created OK. hgrid/topog/vgrid/ESMF mesh/SCRIP and ice/cice_grid, wav/*.inp are written with the <grid>_<session> suffix. user_nl_ww3 dtmax/dtcfl/dtcfli/dtmin and user_nl_cice ndtd/grid_file are set (repros r3a, r9, r10, r8).
- Two Cases in one process (GWR_JRA then NYF): no ice/wav files or user_nl leak into the second, and the first case's _cime_case still points at its own caseroot (r9).
- Retry in the same process after a failed Case() (missing parent) succeeds; visualCaseGen state is re-initialised (r1 R1c).
- override=True over an existing case removes caseroot, inputdir and CIME_OUTPUT_ROOT/<name> and recreates with the correct CUSTOM_GRID_PATH/INPUTDIR (r11).
- _remove_failed_attempt with override=False never deletes pre-existing dirs: preexisting is computed after the override removal, and init_args_check forbids an existing caseroot/inputdir (reading, plus r2d cleanup removed only the new inputdir).
- State/config round trip case_to_yaml -> YAML text -> create_case_from_yaml: grid file, topo depth and min_depth attr, vgrid, atm_grid_name, project, job_queue, job_wallclock_time (PyYAML quotes it), boundaries order and function_overrides are all preserved (r4).
- case_state schema 1.1.0 is unchanged since tags v1.0.0/v1.0.1, so cases created by the released 1.0.x read back (git show of tags).
- CLI dump and process resolve --caseroot against cwd and read inputdir from the state; exit codes are 0 on success (cli1-3 logs).
- configure_forcings multi-case CASEROOT guard (#250) is active and runs before any configurator (reading case.py:623-631).
- StreamYears: a stale start_date/end_date in a dumped YAML is overridden by date_range (reading forcing/atm.py:56-74).
- _set_ww3_timesteps / _set_cice_ndtd coupling-interval math and NCPL_BASE_PERIOD handling (reading, plus values in r3a).
- logging.setup_logger / quiet_visualcasegen_info (reading).

### CrocoDash configure and process

- Partial boundaries ['north','east'] (repro r1_basic.py): OBC_NUMBER_OF_SEGMENTS=2; 001 = 'J=N,I=N:0', 002 = 'I=N,J=0:N'; the _DATA files match forcing_obc_segment_001/002.nc as written.
- Tidal file numbering (tu_/tz_segment_NNN) uses the same boundaries order as the conditions numbering (from reading rm6 find_MOM6_rectangular_orientation and _get_segment).
- Gregorian OBC time axis across Feb 29 (r1): 5 records at 0..4 'days since 2020-02-27', calendar gregorian; all chunks share the run-start epoch, and the merge is monotonic.
- CALENDAR/RUN_STARTDATE/STOP_OPTION/STOP_N for a gregorian product (r1): GREGORIAN, 2020-02-27, ndays, 4.
- Identical reconfigure on an override=False case (r2 nooverride): no files removed; raw data reused, not fetched again.
- A changed date_range removes stale IC/OBC/raw/regridded files (r3 'Removed forcing files...') and the WW3 staging folder; reprocessing produces new-window spectra (r10).
- user_nl blocks after 6 configure calls on one case: one CrocoDash block, the removed tides lines are gone, no duplicate OBC lines (r3).
- StreamYears for DATM%JRA + DROF%JRA (r6): year_first/last/align = start-2..end+1 and narrowed datafiles in user_nl_datm_streams/drof_streams; NYF is skipped as a climatology.
- Runoff configure (r6): ROF2OCN_LIQ/ICE_RMAPNAME xmlchanged to the mapping/..._r200_f400_nnsm.nc path with the suggested rmax/fold; configure and process build the same file name (mom6_forge ints both).
- CICE + WW3 end to end with reference_ice/reference_waves (r10): ice_ic absolute path, restore_* params, 10x10 expanded restart for the 8x8 grid, 5 deduplicated stations, spec.list, ww3_bounc.nml, time in gregorian seconds since 1990.
- Grid.supergrid = supergrid.expand() refreshes tlon/qlon/nx/ny, as CICE.process needs.
- River nutrients time axis with NOLEAP and GREGORIAN case calendars (r4/r4g): consistent units and calendar attributes.
- Setting both TIDE_REF_DATE and OBC_TIDE_REF_DATE (and the EQ_PHASE pair) to equal values is accepted by MOM6's old_name handling (from reading).
- driver.run_workflow dependency auto-enable and topological order (runoff before bgcrivernutrients), from reading.

### Raw data products

- GLORYS RDA reader on real local files (two days, tiny boxes): a 0..360 box (280..280.5) and a Greenwich box (-0.3..0.3) both give monotonic longitude labels in the request's convention, buf padding on lat, and hours-since-1950 times. RDA holds exactly one file per date for 1993-2026, and a missing date raises a clear FileNotFoundError. Repro: r1_rda.py.
- copernicusmarine 2.0.1 transposes min/max longitude into [-180, 360), so 0..360 OBC boxes and antimeridian IC boxes (lon_max > 180) from get_bounding_boxes are accepted by get_glorys_data_from_cds_api. Checked by reading the installed package.
- POP cm-based units: z_t/z_t_150m (centimeters), UVEL/VVEL (centimeter/s) and SSH (centimeter) are all converted to m by regional-mom6's pint path. Repro log r3.log shows 'Converted ...' for each.
- reference_ocean: depth is layer centres (positive down), temp/salt/u/v/ssh have the expected dims and daily records include the end day, and the variables filter works. A polar-box output regrids exactly with xESMF despite lat > 90. Repro: r5_misc.py (e), r6_polar_ref.py.
- Idempotency across configurations: ConditionsConfigurator.stale_outputs removes extract_forcings/raw_data and regridded_data when dates, product, function_args or chunking change. So the undated ic_unprocessed.nc and the CESM per-variable subset caches are not reused for a changed configuration. WW3 staging has an equivalent check. Checked by reading mom6.py:723-760 and ww3.py:590-607.
- bbox_mask handles both 0..360 and -180..180 sources and antimeridian arcs (offset modulo 360). Checked by reading.
- CESM-WW3-JRA: whole-day inclusive 6-hourly stamps, the Feb 29 -> Feb 28 mapping, cyclic seam windows (_axis_indices/_window_runs), and refusal of out-of-range requests. Checked by reading.
- make_dates_end_inclusive is used by the CDS API and CLI-script paths. The RDA, reference and ERA5 paths are whole-day inclusive by construction. Checked by reading.
- ProductRegistry: case-insensitive lookup, required_args enforcement in __init_subclass__, and get_function_default_args excluding required args and **kwargs. write_metadata drops marbl_var_names unless include_marbl_tracers is set. Checked by reading.
- _ERA5 cdsapi client env juggling restores CDSAPI_RC, and GET workers are processes, so the env change is not shared. Checked by reading.

### regional-mom6

- OBC segment geometry and numbering, by repro (obc_seg.py via CrocoDash _regrid_obc_chunk): south, west, north and east values match analytic linear fields at every wet supergrid point; parallel index 0 is the west/south end; OBC_SEGMENT strings J=0,I=0:N / J=N,I=N:0 / I=0,J=N:0 / I=N,J=0:N are consistent with rm6's ordering.
- OBC land masking at q/u/v/t supergrid points and per-point dz thinning, by repro: dz column sums are 120/120/400/400/1000, corners take the shallower neighbour, land is masked and domain corners are land.
- OBC dims/encoding, by repro: (time, nz, ny, nx), int32 nx/ny/nz, double time with 'days since <start>' and the product's mom6 calendar.
- Absolute-time OBC path (CESM_POP_OUTPUT, noleap), by repro: times come out as 54750.5 'days since 1850-01-01' noleap = 2000-01-01 12:00, correct.
- pint unit conversion for centimeters, cm/s, centimeter/s, K->degC and degC, by repro; temp K->C fallback by reading.
- IC staggering and values, by repro (ic_test.py via CrocoDash _regrid_ic): u at (odd y, even x) and v at (even y, odd x) match analytic values; eta and tracers on T-points; vertical interp onto vgrid.zl; land and below-floor source NaNs are filled.
- IC on a pole-centred EPSG:3995 grid from a GLORYS-like source ending exactly at lat 90, by repro (polar_ic.py): no ESMF degenerate-element crash and no NaNs.
- TPXO9.v1 constituent index map (M2,S2,N2,K2,K1,O1,P1,Q1,MM,MF = 0..9) matches the file's con variable; ua/va cm/s -> m/s; ha*exp(-i hp) convention and zphase = hp; checked by reading the file and the code.
- Tidal ellipse earth-to-grid rotation sign (INC -= angle_dx), by reading: correct, unlike the known velocity sign in PR #74.
- Constituent order in tu/tz files follows the user's tidal_constituents order, the same as OBC_TIDE_CONSTITUENTS (reading); tides and conditions segment numbering use the same boundaries list (reading plus user_nl from tides_case).
- chl SeaWiFS input: the GLADE climatology is N->S with lon -179.875..179.875, matching chl.py's lat flip and lon reconstruction (file header plus reading).
- rm6 origin/main (+7 commits): no changes to segment.py, regridding.py, utils.py or chl.py; #331 only changes IC NaN filling. None of the findings above are fixed on main.
- _make_date_pairs chunks do not overlap, so rm6's per-chunk time anchoring merges monotonically (reading; the noon flooring is the known PR #77).

### mom6_forge

- write_supergrid -> Grid.from_supergrid round trip: tlon bit-identical, tarea equal (r3_writers.py)
- ESMF mesh write -> Grid.from_esmf_mesh round trip for an unrotated grid: tlon/qlat match (r3_writers.py)
- Mask consistency: topog mask, SCRIP grid_imask, ESMF elementMask and CICE kmt all 45 ocean cells; a 5 m cell under min_depth=10 is land everywhere (r3_writers.py)
- CICE htn/hte match independent spherical edge lengths exactly (cm); ulat/ulon/angle/anglet in radians; CICE reads only ulat/ulon/angle/anglet/htn/hte (checked against ice_grid.F90 popgrid_nc)
- SCRIP grid_area vs supergrid quadrant areas: 4e-6 relative; mesh elementArea equals the supergrid block sum exactly (r3_writers.py); Grid.tarea is off by 1.6e-3 (known #126)
- VGrid uniform/hyperbolic: sum(dz)==depth, all positive, write/from_file round trip, from cell_center and cell_interface reconstruct dz exactly (r3_writers.py)
- angle_dx sign and magnitude on from_center grids (0, 30, -45°) within 0.25° of an independent bearing calculation; polar EPSG:3995 grid agrees except within about 1° of the pole (r2_angles.py, r2b.py)
- Topo.set_from_dataset (xesmf, mask_method='dataset') against an analytic bathymetry: exact for source -180..180 or 0..360 with grids at 355..365, 170..180, -60..-50 (r4_topo_lon.py)
- generate_mask_from_naturalearth gives identical masks for xstart -10/350/710 (r6_ne.py, cached Natural Earth data, no download)
- WW3 inputs: mapsta 2 on the requested edges, 0 on land; bottom written as positive depth with SBF -1 and ZLIM -0.1, consistent with masked_depth >= min_depth+0.1 (r3_writers.py + reading)
- ww3_timesteps_from_spacing divisor logic and CIME dtmax rule (reading)
- Runoff NN and smoothed maps conserve runoff (the _check_runoff_conserved check passes in r1/r13); compute_smoothing_weights adjacency correct for unrotated grids (reading)
- get_bounding_boxes anchoring for a 350..370 grid gives -10..10 with crosses False (reading)
- Grid.__getitem__ supergrid slicing with steps keeps q/t staggering consistent and rebuilds metrics with the parent's R and dx_dy_calc_type (reading)
- Topo masked_depth/tmask logic with and without user_mask, and fill_inland_lakes_and_channels writing through user_mask (reading)

### visualCaseGen

- NYF (smoke) and GWR_JRA (t_gwr.py) cases: OCN/ICE/WAV_GRID, NX/NY, OCN/ICE/WAV_DOMAIN_MESH and MASK_MESH point at the written ESMF mesh; ATM/LND/ROF meshes resolve to inputdata paths (repro).
- user_nl_mom from vCG: INPUTDIR, GRID_FILE, TOPO_FILE, ALE_COORDINATE_CONFIG file names and NIGLOBAL/NJGLOBAL match the files CrocoDash writes; NK matches the vgrid; MINIMUM/MAXIMUM_DEPTH come from the topo attrs (repro).
- user_nl_cice grid_file/kmt_file match CrocoDash's ice/cice_grid_<name>_<id>.nc; WW3 *.inp copied into RUNDIR/ww3_moddef_create (GWR_JRA repro).
- _coupling_interval/_set_ww3_timesteps/_set_cice_ndtd resolve $ATM_NCPL and write sane values (user_nl_ww3 dtmax=3600 = coupling interval; ndtd=1) (repro).
- create_newcase command: --res USER_RES, --run-unsupported, --handle-preexisting-dirs a, --pecount, --project, --non-local when running on Casper for machine=derecho (t_relcase2 log); create_newcase now uses stdin=DEVNULL and prints stderr (the vCG #25 hang is addressed at the pin).
- case_tools.xmlchange passes var=val as one argv element (no shell) and includes stderr in its error (reading).
- ConfigVar.reboot/Stage.reboot/csp.reboot fully reset solver state on each initialize(); a successful second Case() is caught by the CASEROOT guard (known #250) (reading).
- Antimeridian grids (xstart=178 or -182) give continuous tlon, so OCN_LENX=3.5; polar projected grids give LENX<=360 and LENY<180, within the relational constraints (t_lenx.py, t_polar_lenx.py).
- CIME compatibility check passes for CESM_crocodash, CESM_wu2r05 and CESM_cdeps_years (all cime6.4.1).
- ninst>1: vCG append_user_nl and CrocoDash user_nl_blocks._files both write user_nl_<model>_NNNN (reading).
- MOM6_MEMORY_MODE xmlchange after case.setup is env_build (not locked at setup), so it is fine (reading + CaseStatus).

### Checked afterwards by hand (2026-11-06 evening)

These were run as small scripts, with no separate verifier. Repros are in `audit_repros/extra/`.

- **Multi-instance cases (ninst=2):** both user_nl_mom_0001 and user_nl_mom_0002 get INPUTDIR, TOPO_FILE and all four OBC segments (`ninst.py`, configure only).
- **Antimeridian-crossing domain (178E–182E) end to end:** IC and OBC files are written with no NaNs and look like a control case at 62W. Caveat: reference_ocean generates data for any box, so this doesn't test that the right box is fetched (`am.py 178.0`).
- **CICE + WW3 (GWR_JRA) end to end with reference_ice / reference_waves:** the CICE forcing is written on the expanded 10x10 grid, plus the CICE grid, the WW3 grid inputs and 8 point spectra, with no all-NaN variables. Every path in user_nl_cice exists (`gwr2.py`).
- **Changing date_range on an existing case:** configure_forcings removes the stale outputs, and process_forcings regenerates the IC raw data for the new start, the OBC time axis and STOP_N (`redate.py`).
- **4x4-cell domain end to end, with job_queue / job_wallclock_time:** works. The queue settings land on every job in env_workflow.xml. A 2x2 grid is refused with a clear "MOM6 grid dimensions too small" (`tiny.py`).
- **chl with the real SeaWiFS file:** 12 monthly fields, no NaNs, 0.04–0.18 mg/m^3, a modulo time axis, and the case calendar (`chl.py`).
- **`crocodash process --caseroot X --ic`:** runs only the IC step, skips existing outputs and exits 0.
- **mom6_forge:**
  - a 0..360 bathymetry source on a negative-longitude domain gives the exact depths;
  - a grid whose length isn't a multiple of its resolution keeps the requested extent and rounds the cell count (no warning);
  - VGrid uniform/hyperbolic thicknesses sum exactly to the depth (`mf_checks.py`).

- **Real GLORYS from the RDA archive, 3 days:** at 60W and on a 179E–183E seam domain. The fields are physical: SST about 17–20 C, salinity 34–36.8, |u| up to 0.3 m/s. The seam's raw data runs from 178E to 183.9E with no gap, and SST is smooth across 180 (`glorys_rda.py`).
- **Tides end to end through CrocoDash with the local TPXO files (M2, S2, K1, O1):** all 12 referenced OBC and tidal files exist, SSH amplitudes are 0.04–0.34 m, phases are in radians within ±pi, and the OBC_TIDE_* settings agree with each other. TIDE_M2-only is the known C4 (`tides_e2e.py`).
- **Some boundaries open (east and south) on a 4x8 grid:** OBC_NUMBER_OF_SEGMENTS = 2, and segment 001 = I=N lies on the east edge and segment 002 = J=0 on the south edge in the files too (`subset.py`).
- **Rotated grid (from_center, 30 degrees):** processes with no NaNs, each segment file lies on its edge, and angle_dx matches the geometric rotation (clockwise, as documented). The degrees/radians label is the known M12 (`rot.py`).
- **Dates:** a range across a year boundary (Dec 30 → Jan 2) and across Feb 29 (Gregorian) give continuous daily OBC records and the right STOP_N (`dates.py`).
- **Arctic polar case end to end, as in the gallery's `projects/cice.ipynb`:** EPSG:3995, ±1000 km at 50 km (40x40), GEBCO_LOWRES, hyperbolic 30 levels, GR_JRA, GLORYS from RDA, CICE restart restoring. It processes in 131 s:
  - topo is 88% ocean with a max of 4594 m;
  - IC temperature matches raw GLORYS (r = 0.991), with no NaNs on wet cells;
  - the 4 OBC segments have 3 records each;
  - the runoff map conserves to 5.6e-16;
  - CICE restoring is on the expanded 42x42 grid, with per-category concentration up to 0.99;
  - hgrid angle_dx matches the grid's geometric x direction to 0.01°.

  The current rotation sign is the known regional-mom6 PR #74 (see *Not filed*) (`polar.py`, `polar_check.py`, `angle_check.py`).
- **Antarctic (Weddell Sea, EPSG:3031) IC, OBC and CICE with runoff skipped:**
  - IC temperature is −1.8 to 0.8 °C (r = 0.95 vs raw GLORYS);
  - OBC values are −2.4 to 1.2 °C (ice-shelf water);
  - the CICE subset from the southern restart rows works.

  Runoff is H3.
- **Full-resolution GEBCO (7.5 GB) on a small domain:** sliced lazily, using 6 s and 0.95 GB peak RSS for a 2°x2°, 0.05° Gulf of Maine grid (`gebco_full.py`).
- **Non-local creation for ubuntu-latest (the crocontainer machine) from Casper:**
  - create, configure and process all work;
  - NTASKS 4 = MAX_TASKS_PER_NODE, BATCH_SYSTEM none, JOB_QUEUE empty;
  - CALENDAR and STOP_N are right (`nonlocal.py`).

  Recreating the case is H7.
- **CESM_POP_OUTPUT on real data:** not rerun, because C1, #353 and #298 already cover it.
- **GLORYS RDA archive edges:** files run from 1993 to 2026-09-22, with one per day and no duplicate days in any year (file names only). A date_range past the end fails with `FileNotFoundError: No GLORYS file found for 20260925 at .../2026/*_20260925_*.nc`, after the IC is written: clear enough (`glorys_end.py`).
- **CESM-WW3-JRA boundary spectra from the real GLADE database on a GWR_JRA case:** the output has:
  - 63 boundary points with 16 six-hourly records each (June 5 00:00 to June 8 18:00, inclusive);
  - Hs 1.1–3.5 m, with mean direction toward the NE;
  - no NaNs (`gwr_jra.py`).
- **Tidal currents on rotated and polar grids:** the ellipse inclination is reduced by angle_dx (segment.py:1241), which is the correct earth-to-grid sign. PR #74's fix is needed only for IC/OBC currents (from reading).
- **Pinned GEBCO seam on the Arctic case:** cells near 180° match raw GEBCO as well as the rest (0.3% median difference, no land/sea mismatches). The seam bug that mf PR #146 fixes doesn't show here.
- **A full-year range (2020-01-01 → 2021-01-01) with reference_ocean:** the case gets STOP_N 366. Each segment has 367 daily records, monotonic with no duplicates across the merged 30-day chunks. It took 32 s (`year.py`).
- **Runoff map on a real coast:** a Gulf of Mexico 0.25° CR_JRA case with GEBCO topo builds its map in 20 s, and it conserves. Every destination is an ocean cell. Each GLOFAS outlet cell spreads within about 110 km, consistent with rmax = 100 km:
  - Mississippi Southwest Pass: 42 cells, weighted mean distance 67 km;
  - Atchafalaya: 25 cells; Rio Grande: 29 cells; Mobile Bay: 24 cells.

  Some links run 400–530 km from inland GLOFAS cells, but the DROF stream (`GLOFAS.v4.dis24.%y.nc`, kg m⁻² s⁻¹) is nonzero only at river mouths: 213 of 93,600 cells in the box, and zero at Baton Rouge and Natchez. So nothing is double-counted (`gom_runoff.py`).
- **Real model runs on Derecho (develop queue, 1 task, `audit_repros/extra/run_tests/`):**
  - The control case `audit_rA` (4°×4°, reference_ocean, 2 days) builds and runs.
  - Its keepexe clones settle H5 (B), H10 (C) and the run-time side of C9 (E).
  - **Corner fill values (lead closed):** in the control run, `tos` and `zos` are finite everywhere. Corner cells stay within 0.1–0.37 °C and 2–5 cm of their diagonal neighbours, the usual spread next to an open boundary, and nothing grows. So the −1e20 corner points in the segment files are not used as data (`corner_check.py`).
  - **Tides at run time:** `audit_rD` has the same domain with M2-only TPXO tides, run 3 days with 2-hourly absolute SSH. Fitting M2 to days 2–3 gives 0.951–0.961 of the TPXO amplitude at all four boundary midpoints and the centre. That is the sin(x)/x = 0.958 expected from 2-hour averaging, so the amplitude is right to about 1%. The phase is within 0.7–1.4° of an independent prediction from TPXO's Greenwich phase and standard astronomical arguments (`tide_check.py`). So TPXO regridding, the radians phase convention, TIDE_REF_DATE and the equilibrium phase all work end to end. This closes the "tidal phase units as MOM6 reads them" and "1850-dated tidal files" items under *Not covered*. Whether OBC nodal corrections are applied is within the prediction's error (1° vs 3°) and stays open. The domain is at 58°W, so this doesn't touch R1. Note for anyone repeating it: MOM6's `zos` removes the area-mean sea level, and with it nearly all of a small domain's tide, so check `SSH`.
- **MARBL BGC end to end (CR1850MARBL_JRA, reference_ocean, gallery MARBL IC):** case creation (visualCaseGen #55 doesn't block the alias), configure and process all work:
  - per-tracer OBC files for all 32 BGC tracers, each one referenced from user_nl_mom and present;
  - a 39-tracer IC with no all-NaN fields;
  - iron sediment and vent forcing on the model grid.

  The BGC values are reference_ocean's documented 1e-6 placeholders, so this checks the plumbing, not the chemistry. GLORYS + MARBL is H11 (`marbl_e2e.py`).
- **machine="CESM_NOT_PORTED":** on a ported host it is refused with the machine list. It is reachable only where CIME can't identify the host, so it can't be tested on GLADE.
- **Dump → create for the polar case (`case_to_yaml` → `create_case_from_yaml`):** the grid rebuilds from the supergrid file exactly, and the topo is identical. config.json differs only in paths and session IDs, and the CICE restart arguments are kept (`polar_roundtrip.py`).

## Not covered

What each reviewer said it did not reach. Nobody ran a gap pass (see Method).

**CrocoDash creation, CLI and recipes**

- `crocodash template` beyond the parser (the renderer is gallery-owned and out of scope).
- `crocodash bundle`/`fork`/`duplicate` through the console script itself: the same code paths were run through the Python API, and CaseBundle needs the MOM_RPS dir on PYTHONPATH here (known env artifact).
- Machines other than derecho (ubuntu-latest, CESM_NOT_PORTED, batch-less) and cases created locally on Derecho rather than non-locally from Casper.
- ninst > 1 cases (user_nl_*_NNNN) through creation and sharing.
- WW3/CICE/MARBL forcing configuration with real products; only creation-time settings were checked.
- Actually running a CESM case to confirm the runtime failures (relative mesh paths, 128 ranks on an 8x8 grid); building and submitting were out of bounds.
- Upstream MOM_interface param_file_reader vs the local CESM_crocodash copy: the KeyError('Global') path does not depend on it, but block handling might.

**CrocoDash configure and process**

- Real TPXO tides processing (only configure was run; process was read, not run).
- A MARBL/BGC end-to-end case (BGCIC/iron/OBC tracer split); blocked by visualCaseGen #55 and pending PR #297.
- Real CESM_POP_OUTPUT/CESM_MOM_OUTPUT fetches (#353 known); the Feb 29 and STOP_N findings used a fake noleap product and configure only.
- Real GLORYS (RDA/CDS/CLI script) fetches; chl processing with real SeaWiFS; runoff map generation (OOM risk on login nodes).
- Rotated, polar, antimeridian and cyclic grids (known items #74, #345, Q17), and tiny 1-2 cell domains.
- Multi-instance (ninst>1) user_nl files, non-local cases, and a relative inputdir (blocked at Case creation).
- The CLI 'crocodash process' path end to end (read only), plus bundle/fork flows.

**Raw data products**

- Real downloads: GLORYS via the Copernicus API or CLI script, ERA5 2D spectra GRIB decode, and GLOFAS cdsapi (no network allowed), so the ERA5 longitude-axis convention and the GLOFAS zip payload are unverified against live services.
- CICE_RESTART subsetting on real tripole grid files (#347 territory), and the CICE regrid of reference_ice for polar boxes.
- CESM_MOM_OUTPUT.get_mom6_single_variable_data and the LENS2 member filter on real archives (one LENS2 and one FOSI header read only).
- Full end-to-end process_forcings with CESM_POP_OUTPUT on real FOSI/LENS2 data (TRIAGE item 1 territory). The rotation finding was shown with synthetic POP files plus real ANGLE values.
- GEBCO/SRTM/SeaWiFS script and python methods beyond reading (#349 covers their defaults).

**regional-mom6**

- MOM6 runtime checks (no build/run allowed): tidal phase units as MOM6 reads them, FMS behaviour with the single-record 1850-dated tidal files, and gregorian-vs-noleap calendar on tidal files for NOLEAP cases.
- Rotated/curvilinear-grid OBC and IC end to end beyond the known rotation-sign PR #74.
- MARBL/BGC OBC end to end (depth_coord list, z_t_150m tracers, _split_bgc_tracers_into_files).
- chl end-to-end run through process_forcings (only read the code and inspected the input file header).
- rm6 config.py save/load and validate.py beyond observing their warnings.
- LENS2 (gx1v7) ANGLE magnitudes for the POP finding: only the HR grid was measured.
- Tides with a bathymetry mask (rm6's own setup_boundary_tides(bathymetry_path=...)), which CrocoDash never passes.

**mom6_forge**

- ESMF mesh pole-row collapse/expansion and tripolar/cyclic global meshes (reconstruct_from_esmf_mesh on tx2_3-like meshes)
- compute_stats / ocean_frac mask path and Cressman weights on real high-resolution data (only the iterative_fill fallback was unit-tested)
- mpi_set_depth_from_xesmf and the mapping.py main() CLI / esmpy map path (generate_ESMF_map_via_esmpy)
- Antimeridian-crossing sources for Cressman (KD-tree on xyz should be fine; not run)
- Channel width files as applied by MOM6 (only read the writer/loader)
- An end-to-end CrocoDash Case() run through mom6_forge writers; the writers were exercised directly instead, to keep load low
- WW3 grid files validated by ww3_grid itself (no model run)
- GUI modules (grid_creator, topo_editor UI, vgrid_creator widgets), excluded by scope

**visualCaseGen**

- MARBL compsets (known vCG #55) and custom long-name JRA compsets with DROF options were not created end to end (only aliases GWR_JRA and NYF long names were).
- ntasks_ocn / job_queue / job_wallclock_time paths of _apply_final_xmlchanges (ntasks_ocn is known #354).
- Running on Derecho itself (local, not non-local) and on the crocontainer ubuntu-latest machine; CESM_NOT_PORTED path.
- Runtime confirmation of the ROF_NX/NY effect on the mediator restart (needs a GLOFAS run), and of relative-INPUTDIR failure at MOM6 start (needs a build/run).
- visualCaseGen user_nl_blocks.py (not reached by CrocoDash main), runoff_mapping_generator, clm_modifier and the GUI-only stages/widgets; 'Modify Existing' ocean grid mode.
- Dubious-ownership git failure for other users' CESM trees (could not reproduce; the one tree tried worked).

## Unverified leads

**From the hand checks (2026-11-06 evening)**

- **CESM_MOM_OUTPUT on real CESM-MOM6 output:** the product hard-codes `z_l` and `zos`, and offers no override. The one real CESM MOM6 run checked, the gallery's CARIB12_RUN, doesn't match:
  - its z-space 3D fields are on `z1_l`;
  - its SSH is `SSH`, not `zos`;
  - its 3D fields exist only as monthly means;
  - its time axis is Gregorian, while the product sets the case to NO_LEAP.

  Not run end to end, because monthly parent data also hits the known #353/Q8 chunking. Worth checking against a standard CESM3 `h.z` file before filing.
- **ERA5 request volume:** the WW3 GET step makes one CDS request per boundary per 7-day chunk (`get_step_days`), and each spent about 10 minutes queued and running in this test (4 requests for a 1-day, 4-boundary case). A year-long case would be about 200 requests, which means hours to days unless they run in parallel. I didn't check how many run at once. Worth measuring before recommending ERA5 for long runs.
- **Non-local ubuntu-latest case mesh paths:** ATM_DOMAIN_MESH and LND_DOMAIN_MESH are absolute GLADE paths (`/glade/campaign/cesm/cesmdata/inputdata/share/meshes/T62_040121_ESMFmesh.nc`), while DIN_LOC_ROOT is `$HOME/cesm/inputdata`. That works inside Apptainer on Derecho, where /glade is bind-mounted, but would break on a laptop unless CaseBundle rewrites the paths (not checked).

Lower-value candidates the reviewers noticed but did not write up or verify. Check each before filing.

**CrocoDash creation, CLI and recipes**

- config.json stores conditions dates as %Y%m%d (CrocoDash/forcing/mom6.py:419), so dump/duplicate/fork turn date_range '2020-01-01 12:00:00' into midnight. STOP_N changes from 2 to 3 days in the recreated case (seen in r4.log).
- case_to_yaml upper-cases product_name ('REFERENCE_OCEAN', recipe.py:198). The recreated config.json differs from the original; harmless because registry lookups are case-insensitive.
- The dumped forcings section repeats StreamYears' start_date/end_date next to date_range (recipe.py:216-238). It is harmless because date_range wins in the constructor, but misleading to edit.
- `crocodash dump --caseroot <relative>` writes caseroot relative while inputdir is absolute (recipe.py:277).
- Case() creation message lists 'compset' (injected automatically, base.py:197) and the defaulted boundaries/product_name/function_name as arguments the user must pass to configure_forcings (case.py:246-254).
- `crocodash process --caseroot X` without component flags prints help and exits 0 (cli.py:67-70). Unknown --skip names (e.g. 'tide') are silently ignored (driver.py:153).
- recipe has no type coercion: YAML 1.1 reads `job_wallclock_time: 12:00:00` as int 43200 and unquoted dates as datetime.date. Both are rejected with errors asking for the format the user typed. A missing topo.source gives KeyError 'depth' (recipe.py:97-107), and `override:` in the case section gives a duplicate-kwarg TypeError (recipe.py:154-160).
- job_queue validity is checked only after override=True has already deleted the old caseroot/inputdir and built the new case (case.py:1117-1122), so a typo'd queue wipes the user's existing case first.
- cli.py:348 imports crocogallery while building the parser, so every crocodash subcommand fails if the gallery package is not installed. setup.py declares no install_requires.
- shareable._get_case_obj appends cimeroot to sys.path on every call (shareable.py:754). It also imports CIME from the case's CIMEROOT, while visualCaseGen already imported CIME from cesmroot.
- fork/duplicate copy the source case's grid files (old session id) into the new inputdir/ocn next to the regenerated ones (clutter only).
- Forcings kwargs typos through the Python configure_forcings API behave like the YAML finding (base.py:259-262); that body belongs to the configure_forcings reviewer.
- _remove_failed_attempt removes only inputdir itself, so parents created by inputdir.mkdir(parents=True) are left behind on failure (minor).
- Not a bug: these runs left files outside the scratch dir that the rules did not let me delete. They are /glade/derecho/scratch/manishrv/temp_case-* (6, from the bundle leak) and /glade/derecho/scratch/manishrv/audit_ccl_* (12 CIME bld/run dirs). There is also a half-made case at dev/crocodash_1_0_x/audit_repros/creation_cli/fakehome/cases_rel/audit_ccl_r2d, which is inside scratch.

**CrocoDash configure and process**

- CrocoDash/forcing/mom6.py:657-671: boundaries must be lower-case full names. ['N','S'] (the form the tides.py/ww3.py param comments suggest) fails with 'Unknown segment OBC_SEGMENT_001', which names the segment, not the bad boundary. The comments are known and fixed in Q9 (#330).
- CrocoDash/forcing/mom6.py:443-460: duplicate boundaries (['south','south']) are accepted and write OBC_SEGMENT_002 twice with no 001 (repro r3 step 5). MOM_interface then rejects the duplicated user_nl entry at build.
- CrocoDash/case.py:675-688: a time of day in date_range is dropped. RUN_STARTDATE keeps the date only and STOP_N floors whole days, so ['2020-01-01 12:00','2020-01-03 00:00'] runs Jan 1 00:00 to Jan 2 00:00 (repro r3 step 6).
- CrocoDash/forcing/bgc.py:282,323: river nutrient fluxes are labelled 'mmol/cm^2/s' although the values are mmol/m^2/s (CESM's file says mmol/m^2/s).
- CrocoDash/forcing/runoff.py:21,57: rmax/fold are documented 'in meters', but mom6_forge treats them as km. Known (Q9 'runoff km').
- CrocoDash/forcing/base.py:861-881: get_output_filepaths returns only files that exist, so validate_output_filepaths is always True. Case.validate_case (case.py:1131, used by the shareable fork) therefore never reports missing forcing files.
- CrocoDash/forcing/tides.py:129-143: tides.process builds an rm6 experiment with mom_run_dir=inputdir. It leaves hgrid.nc, weights/ and forcing/ in ocn, plus a symlink loop (inputdir/inputdir -> ocn, ocn/rundir -> inputdir).
- CrocoDash/forcing/base.py:732-735 + case.py:638-660: XML outputs (runoff ROF2OCN_*_RMAPNAME, WW3_GRID_INP_DIR) are xmlchanged inside run_configurators and not rolled back when a later configurator raises. user_nl files are restored; xml is not.
- configure_forcings ignores unknown or misspelled kwargs; a forcing missing an argument is only logged '[SKIP] X missing args'. Known: Q9 adds an unknown-kwarg warning.
- obc.py coverage check: hand-editing get_step_days in config.json (mom6.py:615 says power users can) after a processed run leaves overlapping raw chunk names and fails with 'Overlapping files', because stale_outputs only runs inside configure_forcings.
- obc.py:575: WW3 logs 'REGRID [south]: None-day slices' when regrid_step_days is None (cosmetic).
- Unclosed datasets: ic.py:74 hgrid, mom6.py:281 (_fill_missing_and_write input), mom6.py:330 vgrid, cice.py:530/554 hgrid_ds/subset, bgc.py:233 source.
- mom6.py:283 final_cleanliness_fill turns every exact 0.0 in the IC fields into NaN and interpolates over it.
- For the creation_cli reviewer: a relative caseroot is resolved against $HOME by visualCaseGen. Case(caseroot='cases/x') fails with 'Cannot write to /glade/u/home/<user>/cases/x' (repro r9_relative.py).

**Raw data products**

- reference_waves spectrum integrates to Hs ~3.1 m, while the comment says 'a 2m/8s swell (Hs=2, Tp=8)'. The hs variable is unused and alpha is fixed (CrocoDash/raw_data_access/datasets/reference.py:446). Cosmetic, but misleading for anyone checking WW3 boundary amplitudes.
- reference_ocean / reference_ice produce latitudes beyond +/-90 (up to 91.0) and overlapping longitudes (-181..181, 725 columns) for polar or encircling boxes (reference.py:129-130, 331-332). xESMF warns 'Latitude is outside of [-90, 90]', but a test regrid stayed exact. Cosmetic.
- GLORYS RDA raw files keep the first day's time valid_min=valid_max (613620), so every later record is outside the declared valid range. netCDF4-python, NCO and ncview-style readers would mask them. xarray ignores it (glorys.py:94-106).
- mom6_forge longitude_slicer returns up to ~1.6 GLORYS cells short of the requested east edge. Asking for -1.3..1.3 gave -1.25..1.167. This is harmless with buf=1, but a function_override of buf near 0 would leave the domain edge uncovered (mom6_forge/utils.py:119-126).
- CESM_POP_OUTPUT maps UVEL/VVEL to TLAT/TLONG although they sit at ULAT/ULONG, a half-cell placement offset (~0.5 deg on gx1v7) (cesm_ocean_output.py:45-48). Fix together with the rotation finding.
- ERA5 build_era5_spectra_request: a non-crossing box that ends exactly at 180 (170..180) raises 'crossing 180E', and an encircling box (-180..180) becomes the area -181..-179, a 2-degree sliver (era5.py:140-142). #348 (1.1) territory.
- ERA5 decode rebuilds longitudes with linspace(first, last). If MARS returns unsigned (GRIB2-style) longitudes for a box across 0 deg (354..6), the axis would come out wrong. Unverified, needs a real pull (era5.py:196-199).
- datasets/utils.write_bash_curl_script: 'mkdir -p {output_folder}' is unquoted, so it breaks on paths with spaces (utils.py:47). This is separate from #349's open-before-mkdir.
- get_mom6_output_data: a request that includes Feb 29 against its NOLEAP product calendar fails with a cftime ValueError from date2num rather than a clear message (cesm_ocean_output.py:245).
- GLORYS has no data south of 80S. Antarctic boxes below -80 are clipped silently by the latitude slice (glorys.py:101), with no warning.
- parse_dataset falls back to os.walk over the whole dataset_path for any variable without its own subdirectory (e.g. LENS2 MARBL variables), which is very slow on GDEX (cesm_ocean_output.py:534). Performance only.
- ProductRegistry.load assigns a local 'loaded' (no-op) (registry.py:87). cice.py:524 and ic.py:87 never close the datasets they open. Minor leaks.
- CESM_MOM_OUTPUT velocities have the same grid-relative problem as POP on tripolar/rotated parents (covered in finding 1, no separate repro).

**regional-mom6**

- CrocoDash/raw_data_access/datasets/cesm_ocean_output.py:155-185 CESM_MOM_OUTPUT assumes a rectilinear parent (1-D xq/yh as lon/lat) and earth-relative uo/vo; nesting from a tripole or rotated MOM6 parent would need geolon/geolat and angle rotation (same class of problem as the POP finding).
- CrocoDash/rm6/regional_mom6/segment.py:1172-1175 + regional_mom6.py:122-146: TPXO land is stored as 0 (not NaN), so zeros enter the bilinear interpolation, which damps coastal boundary tide amplitudes; model-ocean points that are TPXO land get 0 tides instead of an extrapolated value.
- CrocoDash/rm6/regional_mom6/regridding.py:466 vs 528-542: segment land points are written as -1e20 while _FillValue is +1e20 (cosmetic; MOM6 masks land OBC points). dz on land is -1e20 as well.
- CrocoDash/rm6/regional_mom6/regional_mom6.py:1178-1180: vel_out.yh.attrs is set twice, the second time to ic_raw_v.lon.attrs, so init_vel's yh gets longitude attributes (cosmetic).
- CrocoDash/rm6/regional_mom6/regional_mom6.py:1187-1191: setup_initial_condition(vcoord_type='thickness') references the nonexistent self.z (AttributeError); off CrocoDash's path.
- CrocoDash/rm6/regional_mom6/chl.py:136: unlinks 'bilin_weights.nc' in the caller's current working directory.
- CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:1921-1926: regrid_with_subsampling uses periodic=False, so for global SeaWiFS chl a 0.25-deg strip at the antimeridian is unmapped and filled from neighbours (minor).
- CrocoDash/rm6/regional_mom6/regridding.py:487-499: mask_dataset only looks at time 0 / level 0 when deciding whether NaNs lie over ocean.
- CrocoDash/rm6/regional_mom6/MOM_parameter_tools.py:136-140: value changes use str.replace on the whole line, so a value string that also appears in the name or comment is replaced there too.
- rm6 helpers leave stray files in inputdir/ocn: vcoord.nc (_regrid_ic -> expt._make_vgrid, regional_mom6.py:896) and hgrid.nc (tides experiment, regional_mom6.py:449).
- Tides processing builds 12 regridders from the full global TPXO grid (2160x1081) for a 4x4 domain: 106 s. A TPXO10 1/30-deg atlas would be about 25x larger (performance and memory risk).
- rm6 never closes datasets it opens (prepare_tpxo_tidal_forcing opens 3, setup_initial_condition ic_raw, Segment rawseg). They are closed at GC; CrocoDash deletes the tmp segment file while rawseg still holds it (minor).
- CrocoDash/forcing/mom6.py:283 final_cleanliness_fill turns every exact 0.0 into NaN before filling, so genuine zero ocean values are re-interpolated (only matters for synthetic or idealised inputs).
- Path handling (creation_cli area): a relative caseroot ('tcase/cases/x') was resolved by visualCaseGen against $HOME ('Cannot write to /glade/u/home/manishrv/tcase/cases/...'), while CrocoDash's failure cleanup removed the relative inputdir under cwd. Relative paths are resolved inconsistently.
- duplicate_case copies the source case's ESMF_mesh_<oldhash>.nc into the new ocn next to the new case's own mesh (two meshes after duplicate; seen in tides_dup run).
- rm6 Segment absolute-time path (CESM_POP_OUTPUT time_units='days since 1850-01-01') labels the raw numbers with the product's declared units and ignores the file's own units attribute. It is correct today only because CrocoDash's GET writes 'days since 1850-01-01' (fragile).

**mom6_forge**

- mapping.py:122 extract_coastline_mask pads with mode='wrap' in both axes, so on regional grids the open-boundary row or column opposite a land edge is flagged as coastline (r13 at angle 30: 12 east-column cells). Low impact today because only ocean source cells (zero runoff) reach those cells.
- utils.py longitude_slicer (around lines 118-129) drops the east end: longitude_slicer(ds,[10,20]) on 1° data returns 10..19. Every current caller pads by 0.5-1.5°, so it is masked.
- The known longitude_slicer seam-midpoint ValueError (QUEUE) is also reached from Topo.set_from_dataset: a 0..360 bathymetry with a grid centred on 0° (-5..5) raises 'The longitude of the data doesn't seem to include the longitude of the grid' (r4_topo_lon.py x-5_src360). GEBCO with a domain centred on 180° is the mirror case.
- topo.py qmask forces the four corner q-points to land even on cyclic grids.
- grid.py ~828-848: dxCu/dyCv use np.roll, so the last column/row wraps on non-cyclic grids; angle_q is labelled dims (ny,nx) but has shape (nyp,nxp). Nothing downstream reads them.
- Topo.max_depth uses raw depth including cells masked to land, so the MAXIMUM_DEPTH CrocoDash puts in MOM_input (case.py:785) can exceed the deepest written depth (harmless).
- utils.py get_avg_resolution_km calls xr.open_dataset(mesh) unconditionally, so passing an xr.Dataset fails.
- grid.py:632-636 Grid.from_supergrid ignores the name argument for files whose names do not end in .nc (operator precedence); write_supergrid(path=None) raises TypeError on os.path.basename(None).
- CrocoDash/forcing/runoff.py:21,58 documents rmax as meters, but mom6_forge takes km (a user passing 50000 gets a 50000 km radius).
- _supergrid.py from_center docstring says angle_deg=45 points the x-axis NE. The code (correctly) makes the y-axis point NE and the x-axis SE, angle_dx=-45.
- vgrid.py VGrid.hyperbolic docstring calls ratio 'top to bottom'; the code uses dzbot = ratio*dz0 (bottom/top).
- Topo.from_version_control adds two commits (MinDepth + UNDO) to the library history on every load.
- set_spoon/set_bowl use the first T-point as the domain origin instead of the west/south edge (half-cell offset from MOM6's TOPO_CONFIG).
- CrocoDash case.py:421 writes ww3_grid.inp with the default cpl_dt=1800, while _set_ww3_timesteps puts the real WAV interval in user_nl_ww3 (which overrides it).
- mapping.py _cached_cell_areas is a process-global cache keyed by file path, so a mesh rewritten at the same path in the same process gets stale areas (unlikely in CrocoDash because session ids differ).
- topo.py diagnose_resolution measures source dx at the slice's southernmost latitude; its docstring says 1e6 source points while the code uses 2e6.
- Topo.from_topo_file defaults min_depth=0.0 instead of reading the file's min_depth attribute.
- fill_inland_lakes_and_channels uses xarray .shift (no wrap), so channels across a cyclic seam are not filled.

**visualCaseGen**

- visualCaseGen case_creator.py:621: _apply_ocn_grid_xmlchanges tests OCN_GRID_MODE == 'Custom', but the only options are Standard/Create New (grid_options.py:141), so the NTASKS_OCN sizing never runs (dead code; CrocoDash uses PECOUNT instead).
- visualCaseGen case_creator.py:943-950: _wav_uses_custom_ocn_grid() is True for SWAV too, so stub-wave cases get WAV_GRID/WAV_NX/NY/WAV_DOMAIN_MESH set to the ocean grid (seen in the smoke and audit_vcg_relin cases); probably harmless (cosmetic).
- visualCaseGen case_creator.py:517-525: create_newcase is built as an unquoted shell string (shell=True), so a caseroot/project containing spaces or shell metacharacters breaks the command (laptop paths).
- Leak: every Case() calls initialize(), which leaves ~1,670 ipywidgets alive (6,731 after 4 initializes, ~5 MB RSS each; t_leak.py) and appends cimeroot to sys.path again (cime_interface.py:54); matters for long-lived processes (MCP server).
- visualCaseGen cime_interface.py:122-124: the CIME version check shells out to `git describe --tags`. A cime tree with no git metadata or reachable tags gives an opaque CalledProcessError (git's stderr goes to the Jupyter server log, not the notebook; t_cimecheck.py). It is pinned to cime 6.4.x (all three local roots are cime6.4.1).
- visualCaseGen cime_interface.py:859-870/761-769: expand_env_vars leaves '$ENV{SCRATCH}' literal when SCRATCH is unset (Derecho CIME_OUTPUT_ROOT=$ENV{SCRATCH}) and os.makedirs then creates a dir literally named '$ENV{SCRATCH}' in cwd; CrocoDash would use it as cime_output_root (reading only).
- visualCaseGen case_creator.py:722-729: the DT heuristic assumes an 1800 s coupling interval and degree spacing from tlon/tlat ranges (OCN_LENX). Its comment says a 1-deg grid gets ~600 s, but the formula gives 7200 -> 1800 s; DT_THERM never exceeds 1800 even with OCN_NCPL=24. Conservative, no unsafe case found (t_lenx.py, t_polar_lenx.py).
- CrocoDash case.py:1046-1050: _compute_pecount never returns None for a non-empty domain (ceil >= 1), so '--pecount S' is always passed, contradicting its docstring (PE-layout area, related #350/#288).
- CrocoDash case.py:76/335: atm_grid_name defaults to 'TL319', so any DATM%NYF compset (T62) fails unless atm_grid_name is passed. init_args_check's message dumps hundreds of grid keys, and the friendlier 'valid options' branch at case.py:917-921 is unreachable.
- CrocoDash case.py:208: the override/failed-attempt cleanup uses the LOCAL machine's CIME_OUTPUT_ROOT for a non-local case; identical on NCAR (casper is forced to /glade/derecho/scratch/$USER), may differ elsewhere.
- The GRID xml long name stays 'a%null_l%null_oi%null_...' after the xmlchange grid path (cosmetic; only CIME tooling that reads GRID would be misled).
