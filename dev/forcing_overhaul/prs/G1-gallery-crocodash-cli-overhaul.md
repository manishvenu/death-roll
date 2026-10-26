# Update the CLI page and starter config for CrocoDash's new create

## Why

CrocoDash's CLI changed (the PRs for CROCODILE-CESM/CrocoDash#340, CROCODILE-CESM/CrocoDash#341 and
CROCODILE-CESM/CrocoDash#343):
- `crocodash create --from <caseroot or bundle>` replaces `fork` and `duplicate`;
- `crocodash configure` configures an existing case's forcings again;
- `create` asks for the forcings on a terminal when the config has none;
- the create config names the grid files instead of describing the grid.

## What

- **`starter_case.yaml`** (what `crocodash template --output x.yaml` writes) names the
  grid files in `case:`, with a commented snippet that writes them. `<GEBCO>` in it is
  still filled in for `--machine glade`.
- **`cli_workflow.md`:** the grid files and the forcing prompts, `create --from` and
  `configure`, and the subcommand table without `fork` and `duplicate`.
- **The three tutorials** link to CrocoDash's `sharing` page, which replaces `shareable`.

## Notes for reviewers

- Merge once those CrocoDash PRs are on main: the page describes them as merged, and
  the `sharing.html` link only exists after CROCODILE-CESM/CrocoDash#340's PR.

Closes #63

🤖 Generated with [Claude Code](https://claude.com/claude-code)
