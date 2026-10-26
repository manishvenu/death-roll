# Keep only the requested time range in CESM tseries subsets

## Why

The CESM tseries readers (`CESM_POP_OUTPUT.get_cesm_single_variable_data` and
`CESM_MOM_OUTPUT.get_mom6_single_variable_data`) subset in space only. Every request
carries every record of its source files: a year for FOSI, a decade for LENS2.

- **OBC:** GET fetches 7-day chunks, so every raw chunk holds the same records. REGRID
  concatenates them into a duplicated, non-monotonic time axis and stops with
  `KeyError: Cannot get left slice bound for non-unique label`.
- **IC:** regional-mom6 takes the raw file's first record, which is the first month of the
  source file, not the month the run starts in. A FOSI run starting 2000-07-01 got
  January 2000.

## What

Replaces #306. It sits on the time-windows PR (the re-cut of #305), which sizes the OBC
chunks and the IC request to the product's record spacing, so monthly windows always hold
a record once they are sliced.

- `subset_dataset(time_range=)` keeps only the records from the request's start through
  the end of its last day. `read_single_variable_tseries_data` passes the request dates,
  so both the POP and the MOM tseries readers slice.
- Records are compared in the frame they are written in. For POP that is after the month
  shift, which puts each monthly mean at the start of its month.
- Request dates use the real calendar and CESM data is noleap, so a bound on Feb 29 rolls
  to Mar 1.
- A window that holds no record raises a `ValueError` naming the variable and the dates.
  #306 failed there with an `IndexError` from `convert_cftime_to_numeric`.
- The IC uses the last record at or before the start date. The IC request reaches back one
  record spacing, so monthly data can return two records, and regional-mom6 takes the
  first: a run starting Mar 1 would otherwise get February's mean.

## Tests

- A POP tseries subset keeps only the requested months. A request ending Feb 28, 2000
  returns January's and February's records, which covers the month shift and noleap's
  missing Feb 29.

## Notes for reviewers

- **Stale raw files.** GET skips raw files that already exist, so files fetched before this
  change still hold every record. Delete `<inputdir>/extract_forcings/raw_data` before
  reprocessing a case that uses CESM output.
- **Tests cut from #306.**
  - Its GLADE-only time assertion in `test_get_cesm_single_variable_data_fosi` was never
    run, so it is dropped and that test keeps only its spatial checks. Main's old time
    assertion there (the request's start and end lie inside the returned records) no
    longer holds once subsets are sliced.
  - Its five unit tests are now the one test above. The daily branch still runs in
    `test_get_mom6_single_variable_data`.
- **Checked by hand on GLADE.** The FOSI month_1 file for 2000 stamps January's mean at
  2000-02-01 00:00 (`time_bound` Jan 1 to Feb 1). On that file, the FOSI test's Jan 1–5
  window keeps only January's record, and Jan 1 to Feb 28 keeps January and February.
- The IC record choice is checked by hand on synthetic monthly (noleap) and daily data,
  not by a new test.

Closes #335

🤖 Generated with [Claude Code](https://claude.com/claude-code)
