# Take the CESM-output IC from the start date's record

## Why

CESM tseries files hold whole years of monthly means, and the IC fetch keeps every record in them. regional-mom6's `setup_initial_condition` uses the first record, so a case starting 2000-07-01 got its initial condition from **January**.

Checked on a FOSI `month_1` case in the Gulf of Mexico. Main's IC matches the January 2000 mean at 50, 150 and 250 m: 24.11 / 22.76 / 17.22 °C.

## What

`_record_at_start` (mom6.py) keeps the last record at or before the start date, or the first record when none is. It writes that single record next to the raw file, and the IC is set up from it. This is #306's commit 2ac2823f, which applies cleanly to main.

## Tests

- `test_ic_takes_the_record_at_or_before_the_start`: a year of noleap monthly records. July 15 and July 1 give July; a start before the data gives the first record.
- By hand, the same FOSI case on this branch: the IC is 26.69 / 21.27 / 16.42 °C, the July mean.

## Not in this PR

The boundary half of #353, where each weekly fetch holds the whole year and the regrid crashes. Fixing it needs chunk windows sized and padded to the data's cadence, which is #333's work.

Part of #353

🤖 Generated with [Claude Code](https://claude.com/claude-code)
