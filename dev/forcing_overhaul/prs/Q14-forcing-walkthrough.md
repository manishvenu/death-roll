# Ask for the forcings when creating or configuring a case

## Why

`configure_forcings()` takes a different set of arguments for each compset, and nothing
walks a user through them. You read the creation printout or the docs, write a YAML
`forcings:` section or a Python call, and find a missing or misspelt argument when it
fails. Each forcing configurator now describes its inputs (the `forcing-param-specs` PR,
#330): whether they're required, their defaults, descriptions and choices. So CrocoDash
can ask for them.

## What

- **`CrocoDash/prompts.py`, `ask_forcings(compset, current=None)`:**
  1. lists the forcings that are on for the compset and the optional ones. "On" means
     the compset requires them, or allows them and they need no input (StreamYears for
     an NYF compset, say). Optional ones need an input from the user (tides,
     chlorophyll, BGC files);
  2. asks which optional forcings to add;
  3. asks each input of the chosen set, with its description and choices, offering the
     current value or the default. Conditions' function overrides follow the product and
     function answered.

  Enter keeps the value offered, a required input without one has to be given, and
  answers are read as YAML. The end of input (Ctrl-D, or a script's last line) keeps
  the rest. It returns `configure_forcings()` arguments, without the inputs of an
  optional forcing that was dropped.
- **`case.configure_forcings(ask=True)`** runs it, offering the arguments given, else the
  case's current ones.
- **CLI:**
  - `crocodash configure` on a terminal, without `--config` or `--set`, asks.
  - `crocodash create` asks when the YAML has no `forcings:` section, which is now
    optional.
  - `--no-input` turns asking off for both.
  - Off a terminal, a create config without forcings is refused before anything is
    created.
- **Docs:** "Being asked for the forcings" in `cli.md`, a pointer in
  `3a_configure_forcings.md`, and the API page.

## Tests

- A chosen optional forcing is asked for and configured, and one not chosen isn't
  (`test_prompts.py`).
- The end of input configures a case again unchanged, keeping its optional forcings
  (`test_prompts.py`).
- A create config without forcings creates nothing off a terminal (`test_cli.py`).

## Notes for reviewers

- Built on #330 and #334 through a local merge; it gets one rebase once they merge.
- `date_range` is now optional in `configure_forcings()`'s signature, so `ask=True` can
  be called alone. Without `ask`, a missing `date_range` still raises the same
  `TypeError`.
- With `ask=True`, `boundaries`, `product_name` and `function_name` left at their
  defaults can't be told apart from not given, so they don't replace the case's current
  values.

Closes #341

🤖 Generated with [Claude Code](https://claude.com/claude-code)
