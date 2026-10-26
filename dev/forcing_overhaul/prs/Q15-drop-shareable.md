# Delete shareable.py

## Why

Everything `shareable.py` did now goes through the `Case` and `crocodash create`:
- `Case.bundle()` writes the bundle;
- `Case.from_caseroot()` reads a caseroot or a bundle;
- `Case.user_changes()` / `apply_user_changes()` find and carry the user's own changes;
- `Case.copy_forcing_files()` copies the forcing files that still match;
- `crocodash create --from` creates a case from another, asking for its fields and
  forcings.

No command imports `shareable.py` any more. Keeping it means two bundle formats and two
copy paths that drift apart.

## What

Pure deletion:
- `CrocoDash/shareable.py` (`CaseBundle`, `ForkBundle`, `duplicate_case`, the
  reference-case diff and its replay helpers);
- `tests/shareable/` and the `get_shareable_CrocoDash_case` fixture only those tests used;
- the `CrocoDash.shareable` entry in the API docs and its two rows in
  `submodule_api_usage.md`. visualCaseGen's `xmlchange` is no longer used anywhere.

## Tests

None added. Bundling and creating a case from another are covered by the tests in
`tests/test_case.py`, `tests/test_recipe_functions.py` and `tests/test_cli.py` that came
with the bundle-and-create-from PR.

## Notes for reviewers

- **External callers must move first.** The MCP server's `bundle_case`, `fork_case` and
  `duplicate_case_tool` still import `CaseBundle`/`ForkBundle`. They need to move to
  `Case.bundle()` and `create_case_from_yaml(source=)` (or `crocodash create --from`)
  before this merges.
- Bundles written by `CaseBundle` (`crocodash_case.yaml` + `non_standard_case_info.json`)
  are refused by `Case.from_caseroot()` with a message to bundle again, or to
  `crocodash create` from the yaml.

Closes #342

🤖 Generated with [Claude Code](https://claude.com/claude-code)
