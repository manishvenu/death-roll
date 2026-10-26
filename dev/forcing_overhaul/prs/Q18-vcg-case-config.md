# Use visualCaseGen's user_nl blocks, stream-year planner and xmlchange

## Why

Three pieces of CESM-case configuration that CrocoDash carried now live in
visualCaseGen, where they are tested in its CI:
- the tagged `user_nl` blocks that `configure_forcings()` rewrites on every call (ESMCI
  #52);
- the CDEPS stream lookups and the stream-year plan behind StreamYears (ESMCI #53);
- an `xmlchange` that takes the caseroot (ESMCI #51).

CrocoDash's own copies can go.

## What

- **The visualCaseGen pin moves to ESMCI main**, which has #51–#53.
- **`forcing/base.py` and `case.py` use `visualCaseGen.user_nl_blocks`.**
  - CrocoDash passes its tag, `USER_NL_TAG = "CrocoDash configure_forcings"`. That is
    the text existing cases' blocks already carry.
  - Both files call visualCaseGen's `xmlchange(..., caseroot=)`. The local `xmlchange`
    helper is deleted.
  - The local `xmlquery` stays, since visualCaseGen has none.
- **StreamYears is a shim.**
  - `configure()` calls `plan_stream_years(...)` with the case's CESM root, mode, run
    years, padding and narrowing.
  - `_apply` writes the plan into CrocoDash's block in `user_nl_<comp>_streams`, as
    before.
- **Deleted:**
  - `forcing/user_nl_blocks.py`;
  - `forcing/cdeps_streams.py`;
  - `tests/forcing/test_user_nl_blocks.py`;
  - the stream-planning tests in `tests/forcing/test_atm.py`;
  - both modules' API-doc entries.

## Tests

- `test_atm.py` has one test, with the planner mocked. A configured component's plan
  lands in `user_nl_datm_streams`, inside the block the next `configure_forcings()`
  replaces. The padding and narrowing inputs reach the planner, and a skipped component
  writes nothing.
- Tests that stubbed `CrocoDash.forcing.user_nl_blocks.write` now stub visualCaseGen's.

## Notes for reviewers

- **Existing cases keep working.** The block format and tag are unchanged; ESMCI #52
  moved the module with its format byte-for-byte. Blocks written by earlier CrocoDash
  versions are found and replaced as before.
- **The stream settings are unchanged.** `plan_stream_years` is the code that was in
  StreamYears' `_plan`, moved to visualCaseGen.
- **Importing `CrocoDash.forcing` now imports visualCaseGen again.** visualCaseGen's
  package `__init__` builds its GUI, and `case.py` already imported it, so a session that
  creates or reads a case sees no difference. A lazy `__init__` in visualCaseGen would
  remove that cost.
- **One message is more generic.** A malformed block's error now ends "try again"
  instead of naming `configure_forcings()`.
- **A configurator with no case passes `caseroot=None`.** This only happens in tests,
  through direct construction. visualCaseGen's `xmlchange` then falls back to its
  `CASEROOT` config variable, as it does for its own callers. Every real path passes the
  case's caseroot.
- **Real-case check, by hand:** configure a `DATM%JRA` case on main and on this branch.
  `user_nl_datm_streams` and `user_nl_drof_streams` must be byte-identical.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
