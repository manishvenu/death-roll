# Re-read the CIME case at the end of configure_forcings

## Why

`Case()` opens the CIME case once, as `case._cime_case`. `configure_forcings()` then sets `RUN_STARTDATE`, `STOP_N` and the rest through `./xmlchange`, which that open object doesn't see. So after configuring a case from 2020-01-01 for 8 days, `case._cime_case.get_value("RUN_STARTDATE")` still gave `0001-01-01` and `STOP_N` gave 5.

## What

The last step of `configure_forcings()` opens the CIME case again. Every forcing case runs `configure_forcings()`, so the reopen also picks up the xml changes `Case()` makes (`NTASKS_OCN`, `JOB_QUEUE`, `JOB_WALLCLOCK_TIME`).

## Tests

- `test_configure_forcings` now also checks that `_cime_case` returns the configured `RUN_STARTDATE` and `STOP_N`. That check fails on main.

Closes #213

🤖 Generated with [Claude Code](https://claude.com/claude-code)
