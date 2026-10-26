# Let xmlchange and append_user_nl take an explicit caseroot

## Why

`case_tools.xmlchange` and `case_tools.append_user_nl` find the case only through the
`CASEROOT` and `NINST` config variables. That suits the GUI, which configures one case
per session, but not code that drives visualCaseGen from a script:
- **Only the last case is reachable.** `cvars` is process-global, and `initialize()`
  resets it. A script that sets up two cases in one Python process can apply xmlchanges
  and user_nl edits only to whichever case was configured last. Tools built on
  `CaseCreator` (CrocoDash is one) keep changing a case after creating it, so they need
  to say which case they mean.
- **Values go through a shell.** `xmlchange` builds `./xmlchange VAR=val` as a string and
  runs it with `shell=True`. A value with a space is split into two arguments, and the
  shell expands a `$VAR` reference (usually to an empty string) before CIME sees it.
- **Failures lose CIME's message.** The `RuntimeError` says only
  "Error running ./xmlchange ...", not what CIME reported.

## What

- **New keyword-only arguments:**
  - `xmlchange(var, val, do_exec=True, is_non_local=False, out=None, *, caseroot=None)`
  - `append_user_nl(model, var_val_pairs, do_exec, comment=None, log_title=True, out=None, *, caseroot=None, ninst=None)`

  Each falls back to its config variable when not given. Every existing call (all of
  `CaseCreator`'s are positional) behaves as before.
- **`xmlchange` runs without a shell.** It runs `["./xmlchange", f"{var}={val}"]`, plus
  `--non-local` when asked, with `cwd=caseroot`.
  - The printed command uses `shlex.join`. It is unchanged for ordinary values and
    quoted when a value needs it, so the *Show Commands* output can still be pasted
    into a shell.
- **Errors name the caseroot and include CIME's stderr.**
- No other function changes. `run_case_setup` still reads `CASEROOT`.

## Tests

- New `tests/1_unit/test_case_tools.py` has one test, which needs no CESM tree:
  - a stub `xmlchange` script in `tmp_path` records its arguments;
  - with the `CASEROOT`/`NINST` config variables removed,
    `xmlchange(..., caseroot=tmp_path)` runs in `tmp_path` and receives
    `CASE_DESC=two words` as one argument;
  - `append_user_nl(..., caseroot=tmp_path, ninst=2)` writes `user_nl_mom_0002`.
- `tests/1_unit/test_cores_case_creator.py` already imports `case_creator`, and with it
  `case_tools`, so this import adds no CESM requirement to 1_unit.
- The success, *Show Commands* and failure paths were also checked by hand against a
  stub `./xmlchange`.

## Notes for reviewers

- **Values now reach CIME verbatim.** Spaces, quotes and `$` are no longer interpreted,
  so a caller that pre-quoted a value for the shell would now pass the quotes through.
  `CaseCreator` passes only paths, grid names and integers, so its calls are unaffected.
  Commas are still `xmlchange`'s own separator between settings, as before.
- **A caseroot without `./xmlchange`** now raises `FileNotFoundError` instead of
  `RuntimeError`.
- **The two fallbacks are independent.** Passing `caseroot` without `ninst` still reads
  `NINST` from the config variables, and raises a `KeyError` if it is undefined. The
  alternative, assuming one instance, would silently write a `user_nl_<model>` file that
  a multi-instance case ignores.
- `case_tools.py` is not black-formatted upstream. Only the changed lines are, to keep
  the diff small.

## Possible follow-ups in visualCaseGen

- **Pass `caseroot=` from CaseCreator.** `CaseCreator` makes all 22 of its `xmlchange` and
  `append_user_nl` calls through the global CASEROOT. Passing the caseroot explicitly
  would keep those writes pointed at the case being created, even if the GUI's
  configuration variables change while it runs.
- **A scripted way to edit existing cases.** With `caseroot=`, a small non-GUI function
  could apply visualCaseGen's grid, namelist and xml settings to an existing case, or to
  several cases in one process.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
