# Edit a case and find what the user changed after creating it

## Why

Bundle and fork carry a user's own changes to a case (xmlchanges, user_nl lines,
SourceMods, extra xml files) over to the new case. Today they find these changes by
building a throwaway reference case and diffing it by *name*. That approach:
- loses changed values, and user overrides of forcing parameters;
- skips `user_nl_*_streams` and `_NNNN` instance files;
- uses two replay.sh parsers with different rules.

The `case-from-caseroot` PR records a `created` snapshot in the state file at the end
of `Case.__init__`: the replay.sh line count, the text of each user_nl file, and the
xml file names. With that snapshot, the user's changes are simply what lies beyond it.
No reference case or CIME is needed.

A case read back with `from_caseroot` (the `configure-existing-case` PR) also had no way
to make these edits itself: visualCaseGen's helpers write to the case created last in
the process.

## What

- **`Case.xmlchange(var, value)`**: runs `./xmlchange` in this case's caseroot, with its
  `is_non_local`, through the local helper in `forcing/base.py`. CIME records it in
  replay.sh, as usual.
- **`Case.set_user_nl(model, {name: value})`**:
  - writes `name = value` into user_nl_<model>, or into every `_NNNN` file of a
    multi-instance case, outside configure_forcings()'s blocks;
  - an existing line for that name is replaced; otherwise the line is appended;
  - a name one of the blocks sets is refused, with a message to pass it to
    configure_forcings() instead. Setting it outside the block too would list it twice,
    which stops the MOM6 build;
  - every file is checked before any is written;
  - the editing is a private helper in case.py. `forcing/user_nl_blocks.py` is only read
    (`_parse`, `_key`, `_files`), nothing is added to it.
- **One replay.sh parser, `case_state.parse_xmlchanges(lines)`** → `{var: last value}`.
  It handles:
  - `./xmlchange`, or any path to it (the absolute `CIME/Tools/xmlchange`, `"${CASEDIR}"/xmlchange`);
  - `K=V`, comma lists, `--delimiter`;
  - `--id K --val V` and `--id=K --val=V`;
  - quoted values, trailing `# comments`, and flags (`--force`, `-N`, `--file F`, `--subgroup G`, ...).

  `--dryrun` and `--append` lines are skipped. shareable.py's two parsers
  (`CaseBundle._read_xmlchanges`, `apply_xmlchanges_to_case`) now call it. Nothing else
  in shareable changes.
- **`Case.user_changes(target_machine=None)`** returns a plain dict:
  - `caseroot`: where apply copies files from;
  - `xmlchanges`: the replay.sh lines after `created.replay_lines`, without the variables
    CrocoDash owns. Those are the run-date variables configure_forcings() sets
    (CALENDAR, RUN_STARTDATE, STOP_OPTION, STOP_N) and every `XMLConfigParam` of the
    configurators in config.json (runoff's `ROF2OCN_*_RMAPNAME`, `WW3_GRID_INP_DIR`).
    When `target_machine` differs from this case's machine, the machine's own variables
    are dropped too:
    - PE layout: `NTASKS*`, `NTHRDS*`, `ROOTPE*`, `PSTRID*`, `MAX_(MPI)TASKS_PER_NODE`;
    - batch jobs and accounting: `JOB_*`, `USER_REQUESTED_*`, `BATCH_SYSTEM`, `PROJECT`,
      `CHARGE_ACCOUNT`;
    - directories: `CIME_OUTPUT_ROOT`, `DIN_LOC_ROOT*`, `DOUT_S_ROOT`, `EXEROOT`, `RUNDIR`;
  - `user_nl`: `{file: [lines]}` for every `user_nl_*` file, including `_streams` and
    `_NNNN` files. These are the non-blank lines outside CrocoDash's blocks that are not
    in `created.user_nl`;
  - `source_mods`: the files under SourceMods/, except CIME's READMEs;
  - `xml_files`: top-level `*.xml` files that are not in `created.xml_files`.
- **`Case.apply_user_changes(changes, plan=None)`**:
  - copies the xml files and SourceMods from `changes["caseroot"]`;
  - writes the user_nl lines the way `set_user_nl` does (a setting line replaces the
    target's line for that name; any other line is appended);
  - xmlchanges each variable.

  `plan` turns kinds of change off (`{"xmlchanges": False}`). All are on by default,
  and an unknown key raises. Call it before configure_forcings(), as fork will: that
  call then leaves the user's variables out of its blocks.
- **Docs:** "Editing a Case from Python" on the Compsets & Inputs page, linked from the
  `created` paragraph.

## Tests

- `user_changes()` finds an xmlchange and a user_nl line made after creation, with
  their values (the last value wins, and a `_streams` file is included). It does not
  report:
  - the creation-time lines;
  - configure_forcings()'s STOP_N;
  - runoff's XMLConfigParam;
  - a line in a configure_forcings block.

  The replay.sh in this test has one line for each parser form.
- With another target machine, `user_changes()` drops the PE and JOB variables, and it
  keeps them for the same machine.
- Adapted, not added: test_case.py's fake-caseroot helper now records a `created`
  snapshot, optionally of files it is given.
- Real-case check (by hand, read-only, on scratch copies under `croc_cases`):
  - **Parser:** run over all 77 `replay.sh` files. Every one of the 1439 xmlchange
    lines yields its settings. This covers comma lists such as
    `NTASKS=48,ROOTPE=0,ATM_NCPL=24`, `--subgroup case.run`, `--force` and trailing
    comments.
  - **so_bgc copy as a 1.2 case:**
    - after `set_user_nl` (twice for the same name), one xmlchange line, a SourceMods
      file and an extra xml file, `user_changes()` reports exactly those;
    - `"ubuntu-latest"` drops `NTASKS_OCN` and `JOB_QUEUE`;
    - `apply_user_changes` into a fresh copy, with xmlchange stubbed, gives the same
      `user_changes()` back;
    - a name in a `conditions` block and an unknown plan key are both refused.

## Notes for reviewers

- **Plan keys match the existing `fork --plan` JSON:** `xml_files`, `user_nl`,
  `source_mods` and `xmlchanges`, the keys that crocontainer's `run_case.sh` and the
  MCP already pass. So they keep working when fork moves onto these methods, which is
  the next PR.
- **The dict carries its `caseroot`.** The bundle in the next PR has a `caseroot/`
  directory, so the dict can point there and `apply_user_changes` needs no extra
  argument.
- **A user's own STOP_N/RUN_STARTDATE after configure is dropped too.** Fork sets the
  run length from `date_range`.
- **Machine variables are dropped only when the machine changes.** On the same machine,
  a user-set `RUNDIR`/`EXEROOT` would point a fork at the source's directories. So
  would `CONTINUE_RUN=TRUE` or `RESUBMIT`, which aren't filtered at all. The fork PR
  should show them in its summary, or filter them.
- **Values only.** `--subgroup` is not kept, so an applied `JOB_WALLCLOCK_TIME` sets
  every job. `--append` lines are skipped, because their result depends on the case
  they ran in.
- **user_nl changes are compared by line text.**
  - An edited creation line shows up as its new text, and apply replaces the target's
    line for that name.
  - A deleted creation line is not reported.
  - Added comment lines are carried and appended.
  - Inside a user's `KPP% … %KPP` group, settings are upserted by name like any other
    line. This is wrong only if the target also sets that name at the top level.
- **`set_user_nl` refuses every name inside a CrocoDash block,** including derived ones
  such as `OBC_SEGMENT_001`. Editing the file by hand still works as before: a value set
  outside a block wins on the next configure_forcings().
- **user_nl_blocks.** case.py uses `user_nl_blocks._parse`, `_key`, `_files` and `_TAG`.
  visualCaseGen's copy (ESMCI/visualCaseGen#52) has the same functions and takes `tag`
  explicitly. The PR that switches to it changes only the import and the tag constant.
- **shareable.py:** its old parsers read `594 --non-local` as a value and missed
  `--id/--val`. Its names-only diff is otherwise unchanged. shareable is deleted later
  in this series.
- configure_forcings()'s own four xmlchanges still call the base helper directly. They
  are left alone to keep this PR to one concept.

Closes #337

🤖 Generated with [Claude Code](https://claude.com/claude-code)
