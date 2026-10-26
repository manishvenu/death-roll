# Add user_nl_blocks, for tools that rewrite their own user_nl entries

## Why

`append_user_nl` appends. That suits case creation, which runs once. A tool that
configures a case *after* creation is different. Forcing or boundary setup that writes
parameters into `user_nl_mom` or `user_nl_datm_streams` gets run again on the same case:
a notebook cell is rerun, or the settings change. If each run appends:

- every variable ends up listed twice;
- MOM_interface's user_nl parser stops the build on the duplicate;
- CIME's namelist parser and CDEPS quietly take whichever line comes last.

Deleting lines by variable name would also delete the user's own edits. A tool like this
needs to own its entries: put them in a marked block it can find, remove and rewrite on
every run, and leave everything else alone.

`append_user_nl` also reads CASEROOT and NINST from the global `cvars`, which belong to
whichever case was set up last. A tool working on a case read back from its caseroot,
or on two cases in one process, can't rely on that.

This module is the rewritable counterpart of `append_user_nl`. It writes the same files
(including the per-instance `user_nl_<model>_NNNN` ones) in the same layout. It takes the
caseroot and instance count as arguments and uses only the standard library: no `cvars`,
widgets or CIME. Keeping it in visualCaseGen means tools built on vCG share one
implementation and one marker format. CrocoDash, which creates its cases through vCG's
CaseCreator, is the first user.

## What

New module `visualCaseGen/user_nl_blocks.py`. Nothing in vCG calls it yet, so existing
behavior is unchanged.

A block looks like this. `tag` names the tool and `owner` the part of it that wrote the
block:

```
! >>> my_tool setup: conditions [sha:1a2b3c4d] (rewritten on every call; set your own values outside this block)

! Open boundary conditions
OBC_NUMBER_OF_SEGMENTS = 4
! <<< my_tool setup: conditions
```

The marker lines are `!` comments, which MOM_interface's user_nl parser, CIME's namelist
parser and CDEPS's stream-mod parser all skip. The sha records the block's contents as
written.

- **`write(owner, model, groups, *, caseroot, ninst, tag)`** appends `owner`'s block to
  `user_nl_<model>`, or to each instance's file.
  - `groups` is `[(comment or None, [(var, val), ...]), ...]`. It is written and printed
    the way consecutive `append_user_nl` calls would.
  - A variable the file already sets outside the tag's blocks is left out, and the log
    says so. The comparison ignores case and whitespace, so CDEPS's `stream : key` and
    `stream:key` count as the same variable.
- **`strip(caseroot, tag)`** removes every block with that tag from the case's user_nl
  files. It returns the blocks whose contents no longer match their sha, i.e. ones that
  were edited by hand.
- **`report_edits(caseroot, edited, tag)`** runs after the rewrite. For each hand-edited
  block, it prints the lines that were discarded and the ones written back.
- **`snapshot(caseroot)` / `restore(caseroot, contents)`** put the user_nl files back if a
  run fails part-way. That includes deleting any file the run created.

A run is: `snapshot`, `strip`, one `write` per owner and file, `report_edits`; and
`restore` on an exception. The result is the same as if only the latest run had happened.

## Tests

`tests/1_unit/test_user_nl_blocks.py`: five tests using `tmp_path` only, with no CESM or
CIME.

- A rerun leaves the file byte-identical, and `strip` reports no hand edit. A rerun that
  drops a group removes its lines.
- A variable set outside the blocks is left out of the block, whatever its case or spacing.
- `strip` removes only its own tag's blocks. Another tag's block and the creation lines
  stay. The tag's block is given as literal text, which pins the layout that existing
  files hold.
- With `ninst=2`, each instance file gets its own block and keeps its own overrides.
- `restore` undoes `write`s, including deleting a file they created.

## Notes for reviewers

- **Moved from CrocoDash with the code unchanged.** There are only two differences:
  - `tag` is required, so vCG holds no CrocoDash default.
  - Docstrings and messages are generic. Where they named CrocoDash, they now name the tag.

  The block format and parsing are byte-for-byte the same, so blocks CrocoDash has already
  written into existing cases keep parsing. CrocoDash will switch to this module in a
  follow-up, passing its existing tag.
- **Hand edits inside a block are not kept.** A block belongs to its tool. `strip` spots
  edits through the sha, and `report_edits` warns about them. Users set their own values
  outside the blocks, where they are kept and take precedence.
- **`write` alone appends.** Replacing a block takes a `strip` first. One `strip` per run
  removes all of the tag's blocks, so a block the tool no longer writes disappears too.
- **Malformed blocks raise.** A block whose end line is missing raises a RuntimeError
  instead of deleting to the end of the file. `write` parses every instance file before it
  writes any, so a malformed file changes nothing.
- **Output differs a little from `append_user_nl`.** The log goes through plain `print`,
  with no ANSI color and no `out` widget, since there is no GUI here.
- **Placement.** It sits at the top level of `visualCaseGen/` rather than in
  `custom_widget_types/case_tools.py`, because it isn't a widget helper and doesn't touch
  `cvars`. Happy to move it.
- **Untested here:** `report_edits`' wording and the malformed-block error.

## Possible follow-ups in visualCaseGen

- **Write CaseCreator's own user_nl entries as tagged blocks.**
  - `CaseCreator._apply_user_nl_changes` appends visualCaseGen's entries: the MOM6 grid
    and timestep parameters, the CICE grid file, and CLM's `fsurdat`. Appended lines
    duplicate whenever the step runs again, and MOM6's buildnml exits on a duplicate
    parameter.
  - Writing them through `user_nl_blocks.write(..., tag="visualCaseGen")` would make
    reapplying idempotent.
  - It would also make visualCaseGen's own entries distinguishable from the user's edits,
    so a later "what did the user change" view could compare against them.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
