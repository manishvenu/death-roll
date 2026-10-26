# Add a planner that aligns CDEPS stream years with the run dates

## Why

- **JRA cases read the wrong data years.** The CDEPS stream definitions for JRA forcing
  (DATM `CORE_IAF_JRA*`, DROF `IAF_JRA`) hardcode `year_align=1` and the dataset's full
  year span. The `DATM_YR_ALIGN`/`_START`/`_END` xml variables are read only by the
  land-forcing and CPLHIST streams. So a JRA case reads data years unrelated to
  `RUN_STARTDATE`, and no xmlchange can fix it. The only lever CDEPS offers is
  `user_nl_datm_streams`/`user_nl_drof_streams`.
- **Every year's file is listed.** `<datafiles>` is expanded from the stream definition's
  own years before user mods are merged. Retagging the years alone still lists every year
  of the dataset (59 files per `CORE_IAF_JRA` stream), and CDEPS reads the time axis of
  each file in turn until it reaches the year it needs.
- **The right settings take CDEPS knowledge:**
  - which streams a mode activates (regex-matched in `namelist_definition_datm.xml`);
  - each stream's coverage;
  - the exact file paths for a year range. JRA v1.5 spreads its years over four
    `<file>` entries, each with a different datestamp.

  That is CESM case configuration, which is visualCaseGen's job. CrocoDash carries this
  code today. It would call visualCaseGen instead and keep only the step that writes the
  user_nl lines.

## What

- **`visualCaseGen/cdeps_streams.py`** is a set of thin wrappers over CIME's
  `NamelistDefinition` and CDEPS's `StreamCDEPS`, so names and paths match what
  buildnml generates:
  - `stream_names(cesmroot, component, mode)`
  - `coverage(cesmroot, component, stream_name, case)`
  - `datafiles(cesmroot, component, stream_name, year_first, year_last, case)`
- **`visualCaseGen/stream_years.py`** adds
  `plan_stream_years(cesmroot, component, mode, case, start_year, end_year, *, padding=1, narrow=True)`.
  It returns a plan and writes nothing.
  - For each stream of the mode, it sets:
    - `year_first = max(first available year, start_year - 1 - padding)`; the extra
      leading year lets CDEPS interpolate at the run start;
    - `year_last = min(last available year, end_year + padding)`;
    - `year_align = year_first`, so the data year equals the model year;
    - if `narrow`, the stream's `datafiles` for those years.
  - If any stream is a single-year climatology (NYF, RYF) or does not cover the run
    years, it returns `{"status": "skipped", "reason": ...}` instead, and the caller
    leaves the component at its CDEPS defaults.
  - `case` only needs `get_value`, to expand `$DIN_LOC_ROOT`, so a CIME `Case` works.
    Nothing reads config variables or touches the GUI.
- **Applying a plan** takes one line per setting in `user_nl_<comp>_streams`. For a
  2021 run:
  ```
  CORE_IAF_JRA_1p5_2023.GCGCS.PREC:year_first = 2019
  CORE_IAF_JRA_1p5_2023.GCGCS.PREC:year_last = 2022
  CORE_IAF_JRA_1p5_2023.GCGCS.PREC:year_align = 2019
  CORE_IAF_JRA_1p5_2023.GCGCS.PREC:datafiles = <the four files, comma-separated>
  ```
- Nothing in visualCaseGen calls these yet, and the GUI is unchanged.

## Tests

New `tests/2_integration/test_stream_years.py` has 2 tests (3 cases). They read the real
CDEPS stream definitions from the CI's CESM tree, which they find through
`CIME_interface().srcroot` like the other integration tests. No inputdata is needed.
- A 2021 run on `CORE_IAF_JRA_1p5_2023` is aligned to 2019-2022 for all 8 streams. The
  PREC stream's files carry each year's own datestamp (210504, 210504, 220505, 230718).
- `CORE2_NYF` (one repeating year) is skipped, and so is a 2020 run on `CORE_IAF_JRA`,
  which ends in 2016.

The expected values were checked by calling `plan_stream_years` directly against the
`cdeps1.0.101` stream definitions.

## Notes for reviewers

- **Private CDEPS methods.** `coverage` and `datafiles` call
  `StreamCDEPS._get_stream_first_and_last_dates`, `_resolve_values` and `_sub_paths`,
  so the expansion matches buildnml exactly. Reimplementing it would risk emitting paths
  that do not exist. All these calls are in `cdeps_streams.py`, and the test's exact-path
  assertion is there to catch a CDEPS update that changes them.
- **sys.path.** `cdeps_streams` appends `<cesmroot>/cime` and CDEPS's `cime_config`
  directory to `sys.path`, because `stream_cdeps.py` is a loose module, not a package.
  That lets it work without a `CIME_interface`.
- **The run years are arguments**, not read from the case's `RUN_STARTDATE`/`STOP_N`,
  so streams can be planned before those are set.
- **The plan is the dict CrocoDash already stores** in its saved forcing configuration,
  which keeps those files readable.
- The new files are black-formatted.

## Possible follow-ups in visualCaseGen

- **Align stream years in the launch stage.** visualCaseGen offers multi-year DATM and
  DROF options (e.g. the JRA compsets), but never looks at the run dates. When a case uses
  one, the launch stage could call `plan_stream_years` for the run's years and either:
  - write the plan into `user_nl_datm_streams` / `user_nl_drof_streams`, as tagged blocks
    with `user_nl_blocks`; or
  - at least warn when the run period falls outside a stream's coverage, where CDEPS would
    otherwise silently cycle the wrong years.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
