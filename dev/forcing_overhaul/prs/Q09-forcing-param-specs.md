# Describe each configure_forcings argument once (ParamSpec)

## Why

Nothing tells a front-end which `configure_forcings()` arguments a compset needs, so
each one guesses:
- **The printout in `Case.__init__` is wrong.** For a MOM6 compset it says conditions
  needs `boundaries, product_name, function_name, compset`. `configure_forcings()`
  defaults the first three, and the registry fills in `compset`. It never mentions
  `date_range`, the one argument you have to give. For WW3 it leaves out
  `ww3_obc_product_name`, which `validate_args` requires.
- **The MCP server keeps its own lists.** It has `_SET_BY_CONFIGURE_FORCINGS` and a
  hand-written list of every configurator kwarg. Fork prompts hard-code `date_range` and
  `boundaries`. None of these show defaults, descriptions or allowed values.
- **Derived inputs look like user arguments.** `start_date`, `end_date`, `calendar` and
  `function_args` are computed by the constructors, but they show up as arguments and
  `generate_configure_forcing_args` hands them back. That means a forked case keeps its
  source's calendar even after the product changes.
- **Typos are silently dropped.** A kwarg that no configurator takes is discarded without
  a message. So is one tides path given without the other two.
- **Some comments are wrong.** The tides and WW3 boundary examples use `'N'`/`'S'`, and
  the runoff `rmax` comment says metres where mom6_forge uses km.

## What

- **`InputParam(..., derived=True)`** marks inputs the constructor computes:
  - start/end dates (conditions, tides, StreamYears);
  - `calendar` (Chl, BGCRiverNutrients);
  - conditions' `function_args` and its registry-injected `compset`.

  `InputParam` also takes `choices=`, a function of the other inputs' values. Two helpers
  build it: `product_choices(product_type)` and `access_method_choices(product_input)`.
  `InputValueParam` and `InputFileParam` share one implementation.
- **`ParamSpec(name, configurator, required, default, comment, is_path, choices)`** and
  **`ForcingConfigRegistry.param_specs(compset, config=None)`** describe every argument
  of the configurators that the compset requires or allows:
  - case_* and derived inputs are left out;
  - `required` means the compset requires the configurator and the argument has no default;
  - `default` is the constructor default or, given a config.json dict, that case's value;
  - `comment` comes from the Param, and `is_path` from `InputFileParam`;
  - `choices` covers the product names of the right type and the chosen product's
    access methods (conditions, CICE, WW3);
  - a name several configurators take (`boundaries`) is listed once.
- **Conditions' extra specs** come from a `param_specs` override on the configurator:
  - `date_range`, required, with a config's dates as its default;
  - one `function_overrides.<key>` per defaulted argument of the chosen access method,
    with a config's resolved value as its default.
- **Required arguments are now reported correctly:**
  - Conditions' constructor takes `configure_forcings()`'s defaults for `boundaries`,
    `product_name` and `function_name`, from constants that `configure_forcings()` also
    uses.
  - WW3's constructor now requires `ww3_obc_product_name`.
- **`serialize()` rejects values JSON can't hold.** It raises a `TypeError` that names the
  configurator and param, where before `json.dump` failed later without saying which one.
  The unused `is_serializable` helper is removed.
- **Unknown kwargs log a warning** listing every kwarg that no active configurator takes.
- **The creation printout comes from the specs:** one line per required argument, with
  its configurator and comment.
- **`generate_configure_forcing_args` no longer hands back derived inputs.**
- **Comments fixed:** the boundary examples (tides, WW3, conditions), runoff `rmax`/`fold`
  in km, and tides' `start_date`.
- **Docs:** the case-setup printout, "How to Check What's Required" (now uses
  `param_specs`), and the developer page's Param section (`derived`, `choices`, and
  `InputFileParam` no longer documented as checking that the file exists).

## Tests

- `param_specs` for a MOM6 compset and a MARBL compset lists exactly the required inputs
  (`date_range`; plus `marbl_ic_filepath`). It lists no case_* input, no `compset`, and
  none of the dates, `calendar` or `function_args`.
- Adapted: a WW3 configurator without a product now fails in the constructor (TypeError).
- Checked by hand, outside pytest:
  - `param_specs` over the three golden configs gives each case's dates, product,
    function and overrides as defaults;
  - every configurator from the configurator smoke test still serializes under the new
    JSON check;
  - a typo'd kwarg, and a single tides path, each log the warning.

## Notes for reviewers

- Builds on #325.
- **ParamSpec has no `derived` field.** `param_specs` leaves derived inputs out, so the
  field would always be False.
- **An optional configurator's arguments are never `required`.** Tides, Chl and
  BGCRiverNutrients are active only when all of their arguments without a default are
  given. A front-end can group the specs by `configurator`.
- **Conditions' constructor defaults:** with #325's tolerant reading, a config.json
  missing `boundaries`, `product_name` or `function_name` would now read as the
  defaults. Every config.json has always stored all three.
- **Shared names:** the first declaration wins. Conditions registers before tides and
  WW3, so `boundaries` keeps its default.
- **Only conditions' overrides are expanded per key.** CICE's `cice_function_args` and
  WW3's `ww3_obc_function_overrides` stay single dict specs; unifying the three
  conventions is out of scope. Override keys have `is_path=False`, even `dataset_path`,
  because nothing declares their type.
- **Choices are the registered product names** (`glorys`, `CESM-WW3-JRA`). Product
  names match case-insensitively, so the default `GLORYS` isn't literally in the list.
- **The warning also covers a configurator that wasn't activated:** one tides path
  without the others is reported too, which was the silent failure.
- **`get_user_args` stays for now.** The MCP's `list_forcing_configs` still calls it
  until its follow-up commit switches to `param_specs` (and drops
  `_SET_BY_CONFIGURE_FORCINGS`). Then it can go.
- WW3's `validate_args` still rejects a `null` product, which can only come from a
  config.json.

Closes #330

🤖 Generated with [Claude Code](https://claude.com/claude-code)
