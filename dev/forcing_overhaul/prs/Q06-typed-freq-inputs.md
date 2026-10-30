# Replace the freq overrides with typed data_freq and subsample_freq inputs

## Why

The data cadence for the initial and boundary conditions is set with two untyped
`function_overrides` keys:
- `freq` thins a method's data to a coarser cadence (GLORYS from RDA, reference_ocean,
  the CESM readers);
- `data_freq` says what cadence the data at a given path holds (the CESM-POP and
  CESM-MOM readers).

Whether it is required, refused or optional depends on the product and the method, and
only `resolve_time_sampling` knows. `Case.configure_forcings` runs that check, but a
config.json that is read back never gets it. So a CESM-MOM case configured without a
cadence (every one configured on main) only fails in the GET step of `process_forcings`.

## What

- **Two conditions inputs** replace the `freq` override. They are passed to
  `configure_forcings` as plain kwargs, like any other configurator input, default to
  `None`, and are stored in the conditions `inputs` of config.json:
  - `data_freq`: the cadence of the data a method reads from a path the user gives
    (`@accessmethod(data_freq=True)`). Required for a `USER_SPECIFIED` product (CESM-MOM
    output).
  - `subsample_freq`: thins a method's data to a coarser cadence
    (`@accessmethod(subsample=True)`).
- **Validation** moves from `Case.configure_forcings` into
  `ConditionsConfigurator.validate_args`.
  - Passing an input the method doesn't take raises a `ValueError`. The message
    defines both inputs and says which ones the method takes.
  - `resolve_time_sampling` then checks the cadence: required for `USER_SPECIFIED`, a
    valid alias, never finer than native. Its `USER_SPECIFIED` error now names
    `data_freq`, and its finer-than-native error no longer says `freq=`.
  - `validate_args` also runs when config.json is read back. So a `USER_SPECIFIED`
    product with no `data_freq` raises `ReconfigureRequired` ("rerun
    configure_forcings()") before anything runs.
- **`freq` and `data_freq` are no longer function arguments.**
  `ProductRegistry.get_function_default_args` leaves them out, so `function_args` never
  stores them. Passing either in `function_overrides` raises an error that names the two
  new inputs.
- **Process:** `_function_args()` passes the access method `data_freq` and
  `freq=subsample_freq`, when set.
- **Round trip:** `generate_configure_forcing_args` hands back `data_freq` and
  `subsample_freq` when set, so dump, duplicate, bundle and fork keep them.
- **Docs:** `adding_data_access.md`, a short "Data Cadence" example on the
  configure-forcings user page, and the `configure_forcings` docstring.

## Tests

- New: `data_freq` is required for a `USER_SPECIFIED` product, and the configure-time
  error names it. The test builds the conditions configurator directly, with no CIME.
- Adapted, with no new guarantees:
  - the configurator tests give the CESM readers their own access methods, and CESM-MOM
    a `data_freq`;
  - the all-configurators smoke test passes a real `function_name` and no cadences;
  - the `USER_SPECIFIED` test of `resolve_time_sampling` expects `data_freq` in the
    message.

## Notes for reviewers

- **No backwards compatibility** with config.json written by branches that had the
  untyped `freq`. A stored `function_args["freq"]` is dropped, because the method no
  longer accepts it as a function argument. For example, a GLORYS case set to `"MS"`
  that way goes back to daily data until it is configured again.
- **Configs from main:**
  - they load unchanged, so no schema bump is needed (new inputs with defaults read
    tolerantly);
  - a CESM-MOM config asks for `configure_forcings()` again, as decided;
  - re-running `configure_forcings` on an existing case marks its IC/OBC stale once,
    because the fingerprint covers every conditions input. The `time_sampling` metadata
    already does this.
- **Not covered by a test** (test budget): the round trip of the two inputs through
  `generate_configure_forcing_args`, and the "not allowed" errors. Both were checked by
  hand with a throwaway script. That script also checked that old GLORYS configs load,
  and that old CESM-MOM configs raise `ReconfigureRequired`.
- **Registry change:** `get_function_default_args` drops `freq` and `data_freq` for all
  three callers:
  `configure_forcings`, the recipe and the process step.
- **Unenforced assumption:** a `USER_SPECIFIED` product whose method doesn't take
  `data_freq` could not be configured, because `data_freq` would be both required and
  refused. No such product exists, and registration doesn't check for it.
- **WW3 is untouched:** `ww3_obc_function_overrides` is still unchecked at configure
  time.

Closes #331

🤖 Generated with [Claude Code](https://claude.com/claude-code)
