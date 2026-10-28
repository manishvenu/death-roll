# Replies to the #325 review (2026-10-28)

The changes are in 7e5e55bb on `config-read`. The input-file check at processing is in
`declared-output-files-v2` (e1556bdb), the PR tracked in #332. Each reply goes on its
comment: `https://github.com/CROCODILE-CESM/CrocoDash/pull/325#discussion_r<id>`.

## r4394941839 (base.py:733, None defaults)

Done in 7e5e55bb. A `None` default turned out to mean three different things:
- a placeholder that `configure_forcings()` fills in: `calendar`, the dates,
  `case_inputdir`, and Runoff's `rmax`, `fold`, grid and mesh;
- a value the constructor resolves itself (`function_args` becomes `{}`);
- a real "none" (CICE's product and function names, WW3's overrides and step days).

Inputs of the last kind are now declared `optional=True`. `deserialize` records the
outputs missing from the entry, and the missing inputs left `None` that aren't optional.
`get_input_param`/`get_output_param` raise `ReconfigureRequired` for those, as you
suggested, so old configs still load and only the step that needs the value stops. Your
case now raises `ReconfigureRequired` when the step reads `calendar` (checked with a
bgcrivernutrients entry, which stores its calendar the same way).

## r4394945156 (base.py:745, TypeError and AssertionError)

Done: `deserialize` converts `TypeError` too, and Runoff's assert is now a `ValueError`
(an assert also disappears under `python -O`).

## r4394950151 (base.py:751, missing outputs)

Covered by the same change: an output missing from the entry raises
`ReconfigureRequired` when it's read. A conditions entry without `get_step_days` loads,
and reading it raises `ReconfigureRequired` instead of the `TypeError` at mom6.py:806.

## r4394953910 (base.py:328, removed configurators)

`get_configurator_from_name` now raises `ReconfigureRequired`, naming the entry. It's
only called for config.json entries, which covers all four places. I chose raising over
skipping: skipping would quietly drop a forcing the case was configured with.

## r4394961005 (case_state.py:101, the message for config.json)

`check_version` takes a `remedy` now. `read_config` passes "Rerun configure_forcings()
to rewrite it.", and the state file keeps "Recreate the case".

## r4394985172 (recipe.py:207, the Path conversion)

Added `json_safe()` in `raw_data_access/registry.py` and
`get_function_default_args(..., serializable=True)`. `configure_forcings` and the
recipe both use them now, so the two can't drift apart.

## r4394988773 (chl.py:72, warn or raise)

The check moved into `BaseConfigurator.configure()`. It warns for every `InputFileParam`
whose file is missing, Runoff's mesh paths included, and the Chl and BGCRiverNutrients
copies are gone.

I kept it a warning, because a case is sometimes configured where it won't be
processed. crocontainer runs `crocodash create --from <bundle> --configure-only`, and
the bundle's GLADE chl and runoff paths don't exist in the container; raising there
would break it.

The hard check goes into processing instead, in the declared-output-files PR (tracked in
#332). Before running anything, `process` checks the input files of every step that
would run, and raises once, naming all the missing ones. A batch job then fails in
seconds, not when it reaches chl. `--preview` lists each step's input files too.

## r4394991040 (bgc.py:222)

Same change as chl.py:72.

## r4394999998 (shareable.py:40, duplicate import)

Kept the explicit list (`CONFIG_FILENAME`, `ForcingConfigRegistry`,
`iter_configurator_entries`, `read_config`) and dropped the star import.

## r4395002491 (shareable.py:323, the meta-key filter)

Added `iter_configurator_entries(config)` in base.py. The registry (both loops), the
recipe and bundle use it, and nothing filters `CONFIG_META_KEYS` by hand any more.

## r4395049727 (config_compatibility.md:5, the 66 of 69)

That's intended: this series doesn't keep older state files working. They're refused
with "Recreate the case", and the next PR (case-from-caseroot) moves the state file to
1.2 and refuses 1.1 the same way. Tolerant reading is for the config.json of cases the
state check accepts, as configurators gain params over time.

The page now says so, and the description now says the 66 of 69 is config.json read on
its own. I also dropped the golden configs: the cases they came from are refused before
their config.json is read, and the tests cover the reading rules directly.
