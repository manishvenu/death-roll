# Reset case.setup after setting ntasks_ocn

## Why

`Case(ntasks_ocn=N)` xmlchanges `NTASKS_OCN` after visualCaseGen has already run `case.setup`. That step locked the PE layout, and nothing resets it, so CIME's locked-file check stops `case.build` with "For your changes to take effect, run: ./case.setup --reset".

## What

- After the `NTASKS_OCN` xmlchange, `_apply_final_xmlchanges` runs `./case.setup --reset`, adding `--non-local` for a non-local case.
- A failed reset raises with CIME's own message.
- `job_queue` and `job_wallclock_time` don't need a reset. Checked: a case with only those set passes both the build and submit checks.

## Tests

- `test_ntasks_ocn_is_followed_by_a_case_setup_reset`: setting `NTASKS_OCN` is followed by exactly one reset, and the job settings alone trigger none. It uses the file's existing stubbed case.
- By hand on Casper, with a tiny NYF case and `ntasks_ocn=1`, `job_queue="develop"`, `job_wallclock_time="00:30:00"`:
  - main fails CIME's build check (`NTASKS_OCN has changed from 384 to 1`);
  - this branch passes both the build and submit checks.

Closes #354

🤖 Generated with [Claude Code](https://claude.com/claude-code)
