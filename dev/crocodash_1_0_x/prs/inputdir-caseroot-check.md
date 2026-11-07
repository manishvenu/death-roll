# Refuse an inputdir at or inside the caseroot

## Why

`Case()` writes the grid files into `inputdir` before `create_newcase` runs, and `create_newcase` refuses a caseroot that already exists. So an inputdir equal to the caseroot, or inside it, failed later with an unclear "already exists" error from CIME.

## What

- `Case.init_args_check` refuses both layouts up front, with a message that says to put the inputdir beside the caseroot.
- A caseroot inside the inputdir still works, so it's still allowed.

## Tests

- `test_an_inputdir_in_the_caseroot_is_refused_up_front`: parametrized over "the same directory" and "inside the caseroot".

Closes #286

🤖 Generated with [Claude Code](https://claude.com/claude-code)
