# Bundle a case, and create a case from another with create --from

## Why

Copying a case goes through `shareable.py` today:
- `CaseBundle` builds a throwaway CIME case to diff against, and carries the user's
  changes by name only, without their values;
- `crocodash fork` and `crocodash duplicate` each have their own prompts, plan JSON and
  YAML.

A case now reads back from its caseroot (#329), knows the changes its user made (#337)
and records its finished forcing steps (#336). So a copy is just a create that starts
from another case, with the same prompts as any create (#341).

## What

- **`Case.bundle(output_dir)`** writes:
  - `bundle.json` (2.0.0);
  - `caseroot/`: the state file, `replay.sh`, `user_nl_*`, `*.xml` and `SourceMods/`;
  - `inputdir/`: `config.json`, `finished_steps.json`, the grid files and every forcing
    output that exists.

  `Case.from_caseroot()` reads a bundle like a caseroot. Bundles in the old format are
  refused, with what to do instead.
- **`crocodash create --from <caseroot or bundle>`:**
  - The source becomes a create config: `case_to_yaml`, which now reads bundles too.
  - `--caseroot`, `--inputdir`, `--cesmroot`, `--machine`, `--project` and `--compset`
    change the new case's fields. They work with `--config` too.
  - On a terminal it asks for those fields (an existing caseroot or inputdir has to be
    changed), then walks through the forcings, offering the source's.
- **`create_case_from_yaml(config, source=)`:**
  - refuses an inputdir inside the source's, or the source's name on its machine (CIME
    would give both the same build and run directories);
  - keeps the source's session id, so the grid and forcing file names match;
  - drops the source's PE layout and batch job on another machine;
  - carries the user's own xml, user_nl and SourceMods changes. Machine-specific ones
    are left out on another machine, and `CONTINUE_RUN`, `RESUBMIT` and the run
    directories always are;
  - copies the forcing files whose settings still match (`Case.copy_forcing_files()`),
    and records them as finished, so processing makes only the rest;
  - prints what it carried over and copied.
- **Removed:** `crocodash fork` and `crocodash duplicate`. `crocodash bundle` drops its
  unused `--cesmroot`, `--machine` and `--project`.
- **Docs:** `shareable.md` becomes `sharing.md`, covering bundle and `create --from`.

## Tests

- A bundle reads back like its caseroot (`test_case.py`).
- Only the forcing steps whose settings match are copied: swapped boundaries leave the
  OBC files out (`test_case.py`).
- A case made from another on a new machine keeps the source's session id and drops its
  PE layout and queue (`test_recipe_functions.py`).
- `crocodash bundle` writes into the output dir. This test moved from
  `tests/shareable/test_cli.py`, which otherwise tested the removed commands.

## Notes for reviewers

- Built on #341, #336 and #337 through local merges; it gets one rebase once they merge.
- No backwards compatibility: `fork`, `duplicate` and the old bundle format go. The MCP
  server's bundle and fork tools move to these before `shareable.py` is deleted (#342).
- **Container CI:** `run_cesm_crocontainer` runs the pinned image's `run_case.sh`. The
  pinned image (`sha-acfa305`) still calls `crocodash fork`; crocontainer #17 (merged)
  switched it to `crocodash create --from`, so testing.yml's tag moves to an image built
  after that merge.
- About 670 lines added and 510 removed. Most of the removals are the old sharing doc
  and the CLI tests of the removed commands.

Closes #340

🤖 Generated with [Claude Code](https://claude.com/claude-code)
