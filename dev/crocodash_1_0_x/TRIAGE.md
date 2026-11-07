# CrocoDash 1.0.x triage (2026-11-06)

Sources:
- every bug-labelled item on project #9;
- every open issue in CROCODILE-CESM/CrocoDash, ESMCI/visualCaseGen, NCAR/mom6_forge and
  CROCODILE-CESM/regional-mom6;
- last week's hand checks (`/glade/derecho/scratch/manishrv/hc1030/`).

"On main" means checked against CrocoDash main b8991c89 and its pinned submodules: by reading
the code, by a hand check, or not checked.

**Done 2026-11-06 (approved):** the four new issues are #353–#356. All 14 section A items
are on project #10 in their sprints, and #344 is in its Backlog with no sprint.
Labels were added and the moved items are off #9. #288 and visualCaseGen #40 were closed
as duplicates (OK'd).

**Bugs 1 PRs (2026-11-06):** #357 (#354) and #358 (#353's IC half) are open, on #10 as
In progress. #349 and #286 are pushed with drafted bodies in `prs/`; open them as these
merge. #353 moved to #9's Sprint 3: its boundary half is a known issue for 1.0.x.

**Bugs 2, built ahead (2026-11-06; pushed, no PRs, bodies in `prs/`):**
- CrocoDash `cime-case-refresh` (#213), `cds-overwrite` (#355) and `glorys-script-one-pass`
  (#356). Each new test fails on main and passes on the branch; #355's ran against the real
  Copernicus service. #356 was worse on main than filed: regional_mom6 writes
  `get_glorys_data.pbs` while CrocoDash checked for `.sh`, so every request replaced the last
  and only the final boundary chunk was ever in the script.
- visualCaseGen (ESMCI) `misc-review-fixes` (#47) and `docn-custom-grid` (CrocoDash #232).
  For #47 the dead assert is removed rather than made to call the function: calling it would
  refuse every CaseCreator on a read-only CESM, including standard grids and the GUI widget.
- CrocoDash `pe-layout` (#350), moved from 1.1 on 2026-11-06 (the audit found every domain gets
  at least 128 MOM6 ranks). Opens after #357 merges; it replaces #357's reset.
- mom6_forge (NCAR) `split-install-pins` (#124): runtime-only `install_requires`, tools as
  extras, the old pins kept in environment.yml.
- **Already fixed on main, closed 2026-11-06 (OK'd), each with a comment citing #49:** visualCaseGen #25 (`stdin=DEVNULL` and the
  abort message, ESMCI #49) and #21 (repro 2026-11-06: a failed create_newcase through
  CrocoDash gives one clear error and no "empty read-only file").

What approval covered:
- open the NEW issues;
- add everything in section A to project #10 with its sprint;
- add the `bug` label where it's missing;
- move #344, #349, visualCaseGen #55 and mom6_forge #146 off #9.

## A. Proposed for 1.0.x

| # | Item | What's wrong | On main | Severity | Size | Fix | Sprint |
|---|---|---|---|---|---|---|---|
| 1 | CrocoDash #353: CESM output timing | `subset_dataset` (cesm_ocean_output.py:606) opens a variable's whole source file and never cuts time to the window. The IC takes January for any start month, and the merged boundary data repeats records and crashes ("non-unique label"). | Yes, hand check: a FOSI case starting 2000-07-01 got a January IC and its boundaries crashed | wrong result + crash | S | IC half: PR #358 (#306's 2ac2823f, branch `cesm-ic-start-record`). Boundary half: a known issue in 1.0.x, since 73377858 needs Q8's window sizing and padding; fixed by Q6 + Q8 (#331, #333) in #9's Sprint 3 | Bugs 1 (IC); #9 Sprint 3 (boundaries) |
| 2 | CrocoDash #354: `Case(ntasks_ocn=N)` won't build | NTASKS_OCN is xmlchanged after visualCaseGen's case.setup and nothing resets. CIME's locked-file check then fails case.build / case.submit with "run ./case.setup --reset". | Yes, from reading (case.py `_apply_final_xmlchanges`; CIME locked_files.py `expect(False, …)`) | crash at build | XS | PR #357: run `case.setup --reset` after that xmlchange. #350 (1.1) replaces it later | Bugs 1 |
| 3 | CrocoDash #349: static download script methods | SeaWiFS and GEBCO script methods call `Path(None)`; GEBCO's python method returns `None`; `write_bash_curl_script` opens the script before its folder exists | Yes, from reading (filed from main) | crash (off the forcing path) | S | As in the issue (branch `static-download-defaults`, pushed; PR not opened yet) | Bugs 1 |
| 4 | CrocoDash #286: inputdir == caseroot | No check, so the error comes later and is unclear | Yes, from reading (`init_args_check` has no such check) | misleading error | XS | Refuse an inputdir at or inside the caseroot in `init_args_check` (branch `inputdir-caseroot-check`, pushed; PR not opened yet) | Bugs 1 |
| 5 | visualCaseGen #55: multi-modifier compsets | `MOM6%REGIONAL%MARBL-BIO` breaks the solver, so regional MARBL cases need a workaround (CrocoDash #279) | Yes (#54 was closed; this issue replaces it) | crash (blocks MARBL cases) | M | New ESMCI PR, then a vCG pin bump in CrocoDash; close #279 after | Bugs 1 |
| 6 | mom6_forge #146: polar-stereographic bathymetry seam | Bug-fix PR, already Ready | Fixed in the PR, not in the pin | wrong result | — | Merge, then bump the pin | Bugs 1 |
| 7 | CrocoDash #213: `case._cime_case` is stale after configure | It's opened once (case.py:223), and configure's xmlchanges go through `./xmlchange`, so `get_value("RUN_STARTDATE")` / `STOP_N` return old values | Yes, from reading | wrong value | XS | Re-read the CIME case at the end of `configure_forcings` (or document `CIME.case.Case(caseroot)`) | Bugs 2 |
| 8 | CrocoDash #355: `get_glorys_data_from_cds_api` returns a stale file after a retry | copernicusmarine won't overwrite: it writes `glorys_(1).nc` and the method returns the requested path, which is the old or partial file | Yes, hand check (a killed first download, then a retry) | crash / wrong file | XS | Pass `overwrite=True`, or return the response's path | Bugs 2 |
| 9 | CrocoDash #356: GLORYS CLI script takes three rounds | Processing writes the IC request, then fails on the missing file; the next round writes the boundary requests, then fails again. So it's process, script, process, script, process, and a rerun of the script downloads the IC again. | Yes, hand check | confusing workflow | S–M | Write every request (IC and all boundary chunks) in the first pass, then stop with "run get_glorys_data.sh" | Bugs 2 |
| 10 | visualCaseGen #47: three small defects | `assert is_ccs_config_writeable or …` never fails (the function isn't called); two datasets never closed in `_apply_mom_namelist_changes`; the WW3 Generate button stays disabled | Yes (from the issue; the first two are on CrocoDash's path) | missing check / leak | XS | As in the issue | Bugs 2 |
| 11 | visualCaseGen #25: create_newcase prompt hangs | `subprocess.run(..., capture_output=True)` hides an interactive prompt, so the call hangs | Yes, from the issue | hang | S | Don't capture (or pass `stdin=DEVNULL` and report the output) | Bugs 2 |
| 12 | visualCaseGen #21: double, misleading error | A failed case creation through CaseCreator also prints "empty read-only file…" | Needs a repro | misleading error | S | Find where the second error comes from | Bugs 2 |
| 13 | CrocoDash #232 (a visualCaseGen fix): DOCN/CICE-only compsets refused | Constraints allow custom grids only with MOM6 or CLM; the reporter's fix adds `docn` | Yes, from the issue | refused config | XS | ESMCI PR with the reporter's change | Bugs 2 |
| 14 | mom6_forge #124: pins break installs outside NCAR | Strict upper pins (matplotlib, jupyterlab, …) conflict elsewhere (NCI) | Yes | install failure | S | Move system-specific pins out of `install_requires` | Bugs 2 |

**Needs details from you before it can be scheduled:**
- **CrocoDash #344 "OBC Tide Params are Changing!":** the body is empty. What changes, and when?
- **CrocoDash #240 "CIME_MACHINE env needed when creating a case on local computer":** the body
  is empty, and CrocoDash itself never reads CIME_MACHINE. Is it CIME or visualCaseGen?
- **CrocoDash #298 "RGD.mask_dataset … CESM POP OUTPUT":** the body is empty. `mask_dataset`
  assumes a variable's last two dims are the segment's. POP boundary data passed through it in
  last week's hand checks on the 1.1 branches, so retest on main after item 1 lands.

## B. Not for 1.0.x

| Item | Why |
|---|---|
| CrocoDash #250 (configure on several cases) | main already refuses with a clear error (the CASEROOT guard); the real fix is #326 (1.1) |
| CrocoDash #132 (Great Lakes BGC) | The regridding that crashed is gone (the BGC IC is now a file you supply); what's left is a data request |
| CrocoDash #288 (PE layouts) | Duplicate of #350 (1.1). Close it, pointing to #350 |
| regional-mom6 #15 (tides across the TPXO seam) | The pinned rm6 regrids from the whole TPXO field, without slicing, so it's likely fixed. Confirm with one tides case across 0°, then close |
| regional-mom6 #61 (setup_bathymetry attrs) | Not on CrocoDash's path (bathymetry comes from mom6_forge) |
| visualCaseGen #40 | Duplicate of #55 |
| mom6_forge #153 (cyclic bounding boxes) | Part of the cyclic-grid chain (Q17); stays with 1.1 |
| #9's 1.1 stack issues labelled bug (#333, #345–#347) | Stay in 1.1 |
| Features, tracking, docs and GUI-only items | CrocoDash #123, #133, #137, #155, #160, #187, #189, #193, #196, #212, #241, #247 (covered by 1.1's subsample_freq), #248, #251, #290; visualCaseGen #33, #43, #44; mom6_forge #6, #19, #29, #68, #108, #123, #141, #154; regional-mom6 #27, #49 |

COSIMA/regional-mom6 upstream issues were not checked one by one. CrocoDash pins the
CROCODILE-CESM fork, and the audit covers its regridding code.

## Sprint load

- **Bugs 1 (Nov 10):** items 1–6. CrocoDash: three small PRs plus #349. visualCaseGen: one PR.
  mom6_forge: merge #146.
- **Bugs 2 (Nov 17):** items 7–14. CrocoDash: three PRs. visualCaseGen: three or four small
  PRs. mom6_forge: one. Plus whatever the details on #344, #240 and #298 turn up.
- **Audit (Nov 24):** the findings in AUDIT.md.

## C. Audit findings (AUDIT.md, 2026-11-06): filed

**Filed 2026-11-06 (approved), each placed and checked from the project side:**
- **Audit (#10, Nov 24):** CrocoDash #359 (C1), #360 (C2), #361 (C3), #362 (C4), #363 (C5),
  #364 (C6), #365 (C7), #367 (C9–C11), #369 (C13.1).
- **Audit 2 (#10, Dec 1, new week):** CrocoDash #371 (C15); mom6_forge #156–#160 (M1–M5);
  visualCaseGen #56 (V1), #57 (V2); regional-mom6 #15 (R1 comment, `bug` label added).
- **#10 Backlog:** CrocoDash #366 (C8), #372 (clearer errors: C14 + C-short-1/2/4/5/6/7),
  #373 (C-short-3); mom6_forge #161–#167 (M6–M12); visualCaseGen #58 (V3).
- **#9:** CrocoDash #368 (C12 calendars) in Sprint 6 with #335; #370 (C13.2–13.8 sharing) in
  Sprint 10 with #340.
- #9's Sprints 3–13 moved one more week (Sprint 3 = Dec 8 … 13 = Feb 16) for Audit 2.

The plan as written before filing:

48 confirmed findings, grouped into 30 issues plus one comment. Bodies are the audit's own
sections, with cross-repo links written as owner/repo#N. Script and bodies:
`/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/4dbe039a-6c11-455b-bddb-0c09a996c41b/scratchpad/audit_file/` (`plan.json`, one `.md` per issue, `file.py` files them, puts each
on its board and records the URLs in `filed.json`; it skips anything already filed).

**Audit sprint (#10, Nov 24): data loss and silent wrong results**
- CrocoDash: C1 POP velocities not rotated from the POP grid; C2 resume keeps half-written
  files; C3 BGC river nutrients 100x off (don/dsi listed twice, dop/dfe never converted); C4
  body tides M2 only; C5 configure_forcings wipes extract_forcings for override=True cases
  (XS: two lines); C6 override=True deletes `<CIME_OUTPUT_ROOT>/<case name>` whole; C7 MOM6
  compsets without %REGIONAL accepted; C9–C11 relative paths and missing parents (one
  issue); C13.1 duplicate/fork always override=True; C15 GLOFAS saves a zip as .nc.
- mom6_forge: M1 runoff map overlap mask across 0°/the equator (fix was closed PR #128);
  M2 nx/ny swap on rotated grids; M3 from_version_control min_depth=0; M4 Cressman fill NaNs;
  M5 Topo slicing drops the mask.
- visualCaseGen: V1 a second Case() with another cesmroot reads the first CESM; V2 custom
  grids keep USER_RES ROF_NX/NY and ATM/LND NX/NY=0.
- regional-mom6 (fork) #15: comment with R1 (tidal OBCs zero within 1/6° of 0°); keep #15 open
  (section B's "likely fixed" was wrong).

**#10 Backlog, no sprint (crashes and misleading errors; an "Audit 2" week if wanted)**
- CrocoDash: C8 misspelled forcing keys ignored (1.1 Q9 only warns); one "clearer errors"
  issue (C14 machine=None, C-short-1/2/4/5/6/7); C-short-3 CESM readers with missing variables.
- mom6_forge: M6–M12. visualCaseGen: V3 (case.setup failure reason lost).

**On #9 with the 1.1 work that replaces it (known issues in 1.0.x)**
- C12 NO_LEAP calendar (3 bugs): Sprint 6, with #335 (Q5 TimeRequest).
- C13.2–13.8 shareable.py (7 bugs): Sprint 10, with #340 (Q13 create --from). Q13 must not
  carry C13.4 (rebuild from alias, not lname) or C13.5 (user_nl blocks).

**Already handled:** R2 (unquoted script paths) is fixed on `glorys-script-one-pass`
(85c91e1d, pushed). rm6-a5 isn't reachable from CrocoDash: not filed.
**For the user:** #344 may be C4 or C-short-2; #240 relates to C14. #350 (pe-layout), which the
audit suggested pulling in, is now in Bugs 2.

### Audit wrap-up: 13 findings checked by hand (H1–H13), filed 2026-11-06 late

The audit's final pass added H1–H13 (AUDIT.md, "Added after the audit"; drafts in
`hand_findings_issue_drafts.md`) and run-time checks of C9 and C15. Filed the same way
(bodies and `filed.json` in the scratchpad's `audit_v2/h/`), each checked from the project side:
- **Audit (#10, Nov 24):** CrocoDash #376 (H5 + H10: an inputdir of 128+ characters or with a
  space fails at model start; same `init_args_check` as #367, can share its PR).
- **Audit 2 (#10, Dec 1):** CrocoDash #374 (H1 `dump > file.yaml` gets log lines), #375 (H3
  runoff fails for every domain south of 60°S and all-ocean boxes), #379 (H13 ERA5 spectra
  flipped 180°, a one-line fix); mom6_forge #168 (H2 coastline mask wraps on regional grids;
  same code as #156/#157); regional-mom6 #79 (H8 chl asserts a rectangular grid).
- **#10 Backlog:** CrocoDash #377 (H6 time of day dropped; the refuse fix sits next to #372's
  date check); mom6_forge #169 (H4 `VGrid.from_file(Path)`), #170 (H9 `subgrid_from_supergrid`
  across the parent's seam or in the tripolar cap).
- **#9 Sprint 6, with #368 and #335:** CrocoDash #378 (H12 CESM_MOM_OUTPUT decodes a Gregorian
  MOM6 parent 2 days early).
- **Notes on filed issues:** #364 (H7: override=True can't recreate a non-local case; C6's fix
  covers it), #372 (H11: MARBL + GLORYS error), #367 (C9 run-time check: case.submit tries to
  download the relative mesh paths and makes empty dirs in inputdata).
- **#371 (C15) updated:** EWDS has rejected every request from this method since its 2026-07-30
  schema change, so it is now a crash. Its body also had the C-short section pasted in by
  mistake (a gen.py section-boundary bug); that is removed, and the same bug's stray
  "visualCaseGen" heading is removed from mom6_forge #167.

**Not filed, for the user:**
- `/glade/campaign/cesm/cesmdata/inputdata/i/rA/ocn`: three empty dirs left in inputdata by the
  C9 run check. Remove with `rmdir -p /glade/campaign/cesm/cesmdata/inputdata/i/rA/ocn`.
- CrocoGallery `known_paths.json` TX2_3V3_GRID points at a deleted file
  (`/glade/campaign/cesm/community/omwg/grids/tx2_3v3_grid.nc`), so `projects/cice.ipynb` fails.
  The inputdata grid `ocn/mom/tx2_3v3/cice_grid_tx2_3v3_260305_cdf5.nc` matches and worked in
  the hand check.
- Polar IC/OBC currents have the wrong rotation sign: regional-mom6 PR #74 (open), which every
  polar case needs.
- AUDIT.md's *Unverified leads* gained three items (CESM_MOM_OUTPUT hard-codes `z_l`/`zos`;
  ERA5 makes one ~10-minute CDS request per boundary per week; non-local ubuntu-latest cases
  keep absolute GLADE ATM/LND mesh paths). Check before filing.
