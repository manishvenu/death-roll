# Configure the forcings of a case read back from its caseroot

## Why

A case read back with `Case.from_caseroot` (the `case-from-caseroot` PR) could process its
forcings but not configure them. To change the dates or boundaries of an existing case
you had to keep the Python session that created it, or recreate the case through
`crocodash dump` and `crocodash create`.

Three things blocked it:
- configurators got their `case_*` inputs from a scan of `case.__dict__`, so they
  depended on whichever attributes the object happened to have;
- a read-back case had no `is_non_local` or `forcing_product`;
- turning config.json back into `configure_forcings()` arguments lived in `recipe.py`,
  as a free function for `dump`/`fork`.

#326 already makes every write name its caseroot, so configuring is no longer tied to
the case created last in the process.

## What

- **`Case.forcing_inputs()`**: an explicit dict of the 7 `case_*` values configurators
  declare (`cesmroot`, `inputdir`, `compset_lname`, `session_id`, `grid_name`,
  `esmf_mesh_path`, `forcing_product`). `ForcingConfigRegistry` uses it in place of the
  `__dict__` scan. Its other injected inputs are unchanged.
- **`Case.forcing_args(changes=None)`**: the arguments the case's forcings were configured
  with, read back from config.json, with `changes` applied. The logic is moved, not
  rewritten, from `recipe.generate_configure_forcing_args` and keeps the
  `function_overrides` handling from #325. `recipe.case_to_yaml` calls it, so `dump`, and
  `fork`/`duplicate` through `dump`, share the same code. `generate_configure_forcing_args`
  and its `remove_configs` argument are deleted: only tests used them.
- **Configuring a read-back case works:**
  - `_bind` sets `is_non_local` (always True for a read-back case, as shareable already
    assumed; a created case keeps CIME's answer) and `forcing_product = None`;
  - Runoff's `xmlquery` of `ROF_GRID`/`ROF_DOMAIN_MESH` passes `--non-local` too, so a
    case can be configured from another host at the same site.
- **`crocodash configure --caseroot X [--config Y] [--set key=value ...]`** reads the case
  with `from_caseroot` and applies the `forcings:` section of `--config`, then each
  `--set` (its value is parsed as YAML, so lists and numbers work), over
  `forcing_args()`. It then calls `configure_forcings()`. If a case was never configured,
  `--config` or `--set` must give at least `date_range`.
- **`ReconfigureRequired`** takes the caseroot when one is known: it is passed through
  `deserialize`, `case.configurators()` and the driver's `resolve_process_targets`. With
  a caseroot, the message names `crocodash configure --caseroot <caseroot>`; without
  one, it keeps the generic text. The `crocodash process` "not configured" error
  mentions `crocodash configure` too.
- **Docs:**
  - a `crocodash configure` section in cli.md;
  - "Reconfiguring an Existing Case" on the configure-forcings page;
  - `case_*` inputs in the developer guide now come from `forcing_inputs()`.

## Tests

- New: `forcing_inputs()` of a read-back fake case provides every `case_*` input that
  any registered configurator declares. Without CIME.
- Adapted, not added:
  - the `generate_configure_forcing_args` tests call `Case.forcing_args()` on a tiny
    config.json;
  - the `remove_configs` half of one test is deleted along with the argument;
  - the fake 1.2 caseroot in test_case.py became a helper, shared with the new test.
- Real-case check (by hand, read-only), on scratch copies of the 58 cases under
  `croc_cases` (state bumped to 1.2, config.json copied):
  - `from_caseroot(...).forcing_args()` and building the configure-time registry from
    it succeed for 55;
  - the other 3 fail, as they should. Their old CICE entries have `restore_ice=True`
    with no product, which the current CICE constructor rejects. `deserialize` now says
    to run `crocodash configure --caseroot ...`, and `--set restore_ice=false` fixes them;
  - `crocodash configure --config ... --set ...`, with `configure_forcings` stubbed,
    passes the merged arguments through.

## Notes for reviewers

- **`forcing_args(changes)` rather than only `forcing_args() | changes`.** Both work.
  Sometimes a newer CrocoDash adds a required argument that config.json lacks. Then
  `forcing_args()` alone has to raise before `| changes` could supply the argument, so
  `changes` goes in first. The CLI passes `--config`/`--set` this way, and the docs show
  this form.
- **New `case_*` inputs must be added to `forcing_inputs()`.** The new test fails if
  they aren't. The OBC re-cuts that come later (`case_supergrid_path`, `case_cyclic_x`)
  go there.
- **Older configs activate StreamYears.** In the check above, JRA cases configured
  before StreamYears existed get it when they are reconfigured. This is current
  behaviour, not something this PR adds.
- **`--set` values are YAML.** An unquoted date becomes a date object, and
  `configure_forcings()` rejects it, so the docs say to quote dates.
- Not done here: an end-to-end configure on a live case. Per the plan, a by-hand check
  on Derecho covers it: create two cases in one notebook and configure both; then
  `from_caseroot` on a new case, `crocodash configure`, `crocodash process` and a 1-day
  run.

Closes #334

🤖 Generated with [Claude Code](https://claude.com/claude-code)
