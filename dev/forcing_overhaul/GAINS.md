# Forcing overhaul: what users and developers gain

### For users (people running CrocoDash cases)

1. **Existing forcing configs load again.** 53 of the 69 config.json files on disk fail
   on main today; tolerant reading makes them process. When a config truly needs
   redoing, the error names the fix (`crocodash configure --caseroot …`).
2. **Cases are reversible.** `Case.from_caseroot(path)` in Python, or
   `crocodash configure --caseroot` on the CLI. Change dates, product, boundaries or BGC
   inputs on an existing case without recreating it: no create_newcase, no case.setup,
   no regridding of grids.
3. **Several cases in one notebook or session just work.** No more "configure_forcings
   writes into the last case created" error.
4. **Direct case edits:** `case.xmlchange("STOP_N", 30)` and
   `case.set_user_nl("mom", {...})` on any case, created or read back.
5. **process_forcings is resumable and honest:**
   - finished steps are skipped automatically;
   - `--force` really regenerates files (today it reruns but keeps the old ones);
   - changed settings regenerate only the affected steps;
   - `--preview` lists every step's files as present or missing.
6. **`crocodash create --from` replaces fork and duplicate, and does more:**
   - `create` and `configure` ask for the forcings on a terminal: which optional ones to
     add, then every input (required ones flagged, defaults and descriptions shown);
     a YAML or `--no-input` gives the same answers without prompts;
   - changing the compset recomputes which forcings are needed;
   - it reuses forcing files **only when they still match**, so there are no silently
     wrong OBCs after a boundary reorder or date change;
   - it carries your own xml/user_nl/SourceMods changes **with their values**, including
     overrides of forcing params, `user_nl_datm_streams` and multi-instance files (today
     only names, and some are dropped).
7. **Bundling is fast and clean.** No throwaway CIME case: no create_newcase, no leftover
   bld/run dirs, no MOM_RPS import breakage. A bundle carries the whole case, including
   which forcing steps are finished.
8. **Lossless round trips.** dump and `create --from` keep `function_overrides` (freq, dataset_path,
   member) and custom OBC segments. cesm_mom_output cases can be copied and bundled, which
   is impossible today.
8a. **A stable create config.** It is `Case()`'s and `configure_forcings()`'s arguments,
   with the grids named as files, so a config doesn't break when mom6_forge's grid API
   changes, and `dump`, bundles and `create --from` all pass the same files around.
9. **Timing works and is explicit:**
   - typed `data_freq` / `subsample_freq` inputs instead of a hidden function_args key;
   - monthly products no longer make empty chunks;
   - a run starting near the GLORYS archive start (1993) no longer asks for missing data;
   - POP daily data is dated correctly;
   - the run-length off-by-one is fixed.
10. **The MARBL BGC fixes (#297) land:** the workshop CR1850MARBL_JRA case runs.
11. **Version safety.** A case or config written by a newer CrocoDash is refused with
    "upgrade CrocoDash" instead of being misread.
12. **DATM stream-year alignment is actually tested** (in vCG CI; it skips everywhere today).
13. **MCP/agents:** `list_forcing_configs` returns full param specs (required, defaults,
    descriptions, choices), so agents build cases correctly.

### For developers

1. **One model of a case on disk: `Case`.** Removed: `ReadCrocoDashCase`, `CaseBundle`,
   shareable.py (~760 lines) and `generate_configure_forcing_args`. config.json is read
   once per process, not three times.
2. **No visualCaseGen global state after creation.** Every write names its caseroot, the
   singleton guard is gone, and the MCP lock is only needed around creation.
3. **Changing a forcing param is safe.** Tolerant reading means adding a param no longer
   breaks every existing case; three golden configs from real cases catch the changes
   that would; a version gate plus a migration hook exist for real renames.
4. **Each forcing input is declared once (`ParamSpec`).** That one declaration drives
   validation, the creation printout, prompts, annotated YAML and the MCP listing. No
   hand-kept lists (`_SET_BY_CONFIGURE_FORCINGS`, recipe's tides rule, fork's hard-coded
   fields).
5. **Each configurator declares its output files.** Bundle, fork, dry run and skip are
   all derived from that, with no filename-prefix globs.
6. **Clear names:** step settings, `finished_steps.json`, the `created` snapshot.
7. **The forcing package is only about forcing.** user_nl blocks and stream years live
   in visualCaseGen with real CI.
8. **Simpler timing model:** inert `anchor`, the unused per-method override and the
   `freq=None` boilerplate are gone, so products defined outside the repo don't break
   at import.
9. **Less, better test code:**
   - ~950 lines of CESM-dependent shareable tests are deleted;
   - the replacements are a few focused tests on real guarantees, run in CI.
10. **Bugs caught on the way:**
    - #269's `ignore_degenerate` regression;
    - #315's stale-file restore;
    - the no-op `--force`;
    - Chl/BGC file checks breaking unrelated steps;
    - an import cycle avoided by design.
11. **Reviewable process:** 18 queued PRs in 3 stacks plus singles, at most 2 open, and
    independent tracks reviewed side by side.

