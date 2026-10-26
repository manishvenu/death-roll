# Forcing overhaul: review queue

## Queue (scope, tests, needs)

All PRs are in CrocoDash unless marked. Each is at most ~700 changed lines and one concept
(pure-deletion PRs are uncapped). Each is black-formatted, with imports at the top, and
follows the testing policy. The **Tests** column is the whole test budget for that PR.
Q numbers are the review order. Already open: #309, #297.

| Q | Stack | Branch | Scope | Tests | Needs | ~Δ |
|---|---|---|---|---|---|---|
| Q1 | C | `config-read` | <ul><li>**Tolerant reading:** tolerant `deserialize`, `ReconfigureRequired` (`require_output_param` is added by the first step that needs it). Chl, BGCRiverNutrients and Runoff call `super().validate_args()`; their file checks warn at configure and raise at process. Delete the dead `run_configurators(config_path)` branch.</li><li>**Versioning** (re-cut of the config-schema-version worktree): `read_config`/`write_config`/`CONFIG_*` in base.py; every reader and writer goes through them; `CONFIG_META_KEYS` in every filter; `check_version(..., supported, migrations)` imported by name; newer files refused.</li><li>**Lossless round trip:** `function_overrides` (args that differ from the access method's defaults) is emitted.</li><li>Dev doc `config_compatibility.md`.</li></ul> | <ul><li>Missing input → default / `ReconfigureRequired`.</li><li>Missing output → `None`.</li><li>Unversioned = 1.0, newer refused.</li><li>The 3 golden configs load.</li><li>A config with overrides dumps and recreates unchanged.</li><li>One source-scan guard against `json.load` of config.json.</li></ul> | main | ~630 |
| Q2 | — | `writes-name-caseroot` | <ul><li>`user_nl_blocks.write(owner, model, groups, *, caseroot, ninst, tag=)` with its own log formatter (`upsert()` comes with `Case.set_user_nl` in Q12).</li><li>**Delete the CASEROOT guard.**</li><li>`session_id`/`grid_name` captured at creation; `is_non_local` computed once; every xmlchange passes the caseroot through a 10-line local helper (`./xmlchange` in the caseroot, argument list), which Q18 swaps for E1; Runoff reads ROF_GRID/ROF_DOMAIN_MESH from `_cime_case`.</li></ul> | Two cases in one process each write to their own caseroot | main | ~560 |
| Q3 | T | `time-sampling` | #302 + #303, amended: <ul><li>drop `anchor` and the unused per-method override;</li><li>`TypeError` instead of `assert`;</li><li>validate `freq_handling`;</li><li>drop the `freq=None` boilerplate (process passes only accepted arguments);</li><li>POP shifts months only for monthly cadence.</li></ul> | Existing tests trimmed to the kept behaviour, plus POP daily dates | main | ~450 |
| Q4 | C | `case-from-caseroot` | <ul><li>State 1.2.0: record `esmf_mesh_path`; write the `created` snapshot at the end of `__init__`; refuse older state.</li><li>`Case.from_caseroot(path, cesmroot=)` and `_bind`.</li><li>Lazy grids, `_cime_case` and `forcing_config`; `configurators()`, `workflow_context()`.</li><li>`run_workflow(case, …)`; `cli process` uses `from_caseroot`.</li></ul> | <ul><li>A fake 1.2 caseroot reads back.</li><li>A 1.1 caseroot is refused.</li></ul> | Q1 | ~480 |
| Q5 | T | `tseries-time-slice` | #306, plus a clear error when a requested window holds no records. Last step of stack T (decided: no window where monthly data regresses on main) | One synthetic slice test (replaces the GLADE-only one) | Q8 | ~80 |
| Q6 | T | `typed-freq-inputs` | Conditions inputs `data_freq` (required for `USER_SPECIFIED`) and `subsample_freq`, validated with `resolve_time_sampling`; they replace `function_overrides["freq"]`; recipe's conditions round trip carries them | `data_freq` is required for a `USER_SPECIFIED` product | Q1, Q3 | ~250 |
| Q7 | C | `declared-output-files` | #310 + #316: <ul><li>`output_files(ctx)` on `Case.configurators()`;</li><li>meta keys filtered;</li><li>iron file declared;</li><li>`--preview` dry run, removing the ic/bc `preview` arguments (if Q8 landed first, keep its `min_chunk_days`/`lookback_days`).</li></ul> | Every configurator's declared files are unique and under the inputdir | Q4 | ~560 |
| Q8 | T | `time-windows` | #305, amended, plus: <ul><li>clamp padded windows to archive coverage;</li><li>run days = end − start.</li></ul> If Q7 landed first, don't bring back the `preview` arguments it removed. | #305's window sweep; one wiring test that the engines get `min_chunk_days`/`lookback_days` | Q1, Q6 | ~480 |
| Q9 | — | `forcing-param-specs` | <ul><li>`derived=True` on dates, calendar and function_args.</li><li>`ParamSpec(name, configurator, required, default, comment, is_path, choices, derived)` and `param_specs(compset, config)`.</li><li>Per-key function_overrides specs.</li><li>WW3's product becomes required.</li><li>Fix the comments (tides, WW3, runoff km).</li><li>`serialize` rejects values that aren't JSON; unknown kwargs warn.</li><li>The creation printout comes from the specs.</li></ul> | `param_specs` for one MOM6 compset and one MARBL compset lists the right required params | Q1 | ~340 |
| Q10 | C | `finished-steps` | #317, renamed and finished: <ul><li>`finished_steps.json` (versioned, read as a cache);</li><li>portable `step_settings` with `process_version`;</li><li>`clean(ctx, step)` on `--force` or changed settings;</li><li>steps that declare no files are never recorded.</li></ul> | <ul><li>A finished step is skipped.</li><li>`--force` rewrites its files.</li><li>Settings are equal across two inputdirs.</li></ul> | Q7 | ~420 |
| Q11 | S | `configure-existing-case` | <ul><li>Explicit `Case.forcing_inputs()` replaces the `__dict__` scan.</li><li>`crocodash configure --caseroot X [--config Y] [--set k=v]`.</li><li>`Case.forcing_args()` (moved from recipe); `ReconfigureRequired` names the command.</li><li>Delete `remove_configs`.</li></ul> | Configure on a read-back case writes the same blocks as on the created case | Q2, Q4 | ~400 |
| Q12 | S | `case-changes` | `Case.xmlchange`, `Case.set_user_nl`; `user_changes()`/`apply_user_changes(plan)`; one replay.sh parser; the CrocoDash-owned and machine-specific filters | A user change made after creation is found with its value; a machine change drops PE/JOB | Q11 | ~520 |
| Q14 | S | `forcing-walkthrough` | <ul><li>`CrocoDash/prompts.py` `ask_forcings(compset, current)`: list the forcings on for the compset (required, or allowed and needing no input) and the optional ones; ask which optional ones to add; then ask each input of the chosen set, offering current values or defaults (end of input keeps the rest).</li><li>`case.configure_forcings(ask=True)`; `crocodash configure` asks on a terminal without `--config`/`--set`; `crocodash create` asks when the YAML has no `forcings:` (now optional); `--no-input`.</li></ul> | <ul><li>A chosen optional forcing is asked for, an unchosen one isn't.</li><li>End of input reconfigures a case unchanged.</li><li>A create config without forcings off a terminal creates nothing.</li></ul> | Q9, Q11 | ~400 |
| Q13 | S | `bundle-and-create-from` | <ul><li>`Case.bundle()` (2.0.0 layout); `from_caseroot(bundle_dir)`; old bundles refused.</li><li>`crocodash create --from <caseroot or bundle>`: the source as a create config (`case_to_yaml` reads bundles), case-field flags/prompts, forcing walkthrough offering the source's.</li><li>`create_case_from_yaml(source=)`: guards, source session id, machine settings dropped on another machine, user changes carried, matching forcing files copied (`Case.copy_forcing_files`).</li><li>Remove `fork` and `duplicate`; `shareable.md` → `sharing.md`.</li></ul> | <ul><li>A bundle reads back like its caseroot.</li><li>Only matching forcing steps are copied.</li><li>A case from another on a new machine keeps the session id and drops PE/job settings.</li></ul> | Q14, Q10, Q12 | ~670 |
| Q15 | S | `drop-shareable` | Pure deletion: shareable.py, `tests/shareable/`; regenerate API docs | — | Q13 | deletion |
| Q16 | — | `interior-obc-segments` | #269, re-cut: <ul><li>restore `ignore_degenerate=True`;</li><li>store boundaries as JSON segment specs (dump/fork round-trip them);</li><li>`case_supergrid_path` from `forcing_inputs()`.</li></ul> | #269's own tests, trimmed; one `ignore_degenerate` check | Q7, Q8, Q11 | ~560 |
| Q17 | — | `cyclic-grid` | #311: pin ESMCI main; `case_cyclic_x` from `forcing_inputs()` | #311's own | Q7, Q11, ESMCI #50 | ~150 |
| Q19 | S | `yaml-grid-paths` | <ul><li>A create config is `Case()`'s arguments plus `configure_forcings()`'s: `case:` names the grid files (`ocn_grid`, `ocn_topo`, `ocn_vgrid`); the `grid:`/`topo:`/`vgrid:` sections and `build_grid`/`build_topo`/`build_vgrid` go.</li><li>`read_grids()` takes the grid's name and `min_depth` from the files, so `create --from` keeps the source's grid name.</li><li>Old sections refused with how to write grid files; `case_to_yaml` names the files; `cli.md` schema + how to write grid files.</li></ul> | The grid files read back with the grid's own name, `min_depth` and levels (replaces the 11 builder tests) | Q15 | ~430 (mostly removals) |
| Q18 | — | `vcg-case-config` | Pin ESMCI main (`submodule-bump`); StreamYears becomes the shim (`plan_stream_years` + `user_nl_blocks.write`); Q2's local xmlchange helper is replaced by E1; delete `forcing/user_nl_blocks.py`, `cdeps_streams.py` and their moved tests | One shim test | E1–E3 merged | ~550 |

**ESMCI PRs**, opened together once Q2 is built (each against main, none depending on another):
- **E1** `case-tools-caseroot`: keyword-only `caseroot=`/`ninst=`, argument lists, stderr in errors. One unit test.
- **E2** `user-nl-blocks`: Q2's refactored module and its existing tests, moved verbatim, with `tag=` required. Changes from Q2's review are mirrored into it.
- **E3** `stream-years`: `cdeps_streams` + `plan_stream_years` (pure: returns the plan, writes nothing), moving the existing stream tests (they actually run in vCG CI). The CrocoDash shim writes the plan with E2's `user_nl_blocks.write`, so E3 doesn't depend on E2.

If ESMCI declines E3, `cdeps_streams` stays in CrocoDash.

**MCP commits:**
- after Q1: `read_config` + `CONFIG_META_KEYS`;
- after Q9: `list_forcing_configs` returns `param_specs`;
- before Q15: bundle on `Case.bundle()`, fork/duplicate tools on `create_case_from_yaml(source=)`;
- after Q19: `create_case` writes the grid files (its `_build_*` helpers) and names them in `case:`.

**crocontainer:** #17 merged (`run_case.sh` uses `crocodash create --from`); Q13 moves
testing.yml's image tag to an image built after it. C2 (`grid-files`) merges right after
Q19, then the CrocoDash submodule is bumped past Q19.

**CrocoGallery:** G1 (`crocodash-cli-overhaul`) opens once #340, #341 and Q19 are on main.

**Total: 18 CrocoDash queue PRs (Q18 folded into Q2; Q19 added 2026-10-26), never more
than 2 open at once, plus 3 ESMCI PRs opened together.**


## Verification

CI runs the small tests listed in each row. Each stack also gets one round of real-case
checks, run by hand and not turned into CI tests:

- **Q1:** a read-only sweep of `resolve_process_targets(read_config(p))` over all 69
  `croc_input` configs. Expect 69/69 (main: 16/69).
- **Stack T and #297:** on Derecho, a GLORYS case starting 1993-01-01, a monthly CESM-POP
  case, and CR1850MARBL_JRA.
- **Q2, Q4, Q11:** on Derecho, create two cases in one notebook and configure both;
  `from_caseroot` on a new case (a 1.1 case is refused); `crocodash configure`;
  `crocodash process`; a 1-day run.
- **Q7, Q10:** on Casper, process a case:
  1. a rerun prints `[skip]`;
  2. `--force --bc` rewrites the files (check mtimes);
  3. `--preview` lists every step's files.
- **Q5:** process a monthly CESM-POP case starting on the 1st of a month. The IC must come
  from that month's record, not the month before.
- **Q14:** on a terminal, `crocodash configure` a live case (Enter through every question
  must leave config.json unchanged), and `crocodash create` a YAML without `forcings:`.
- **Stack S:** run testing.yml through workflow_dispatch before Q13 merges. On Derecho,
  `crocodash create --from` a case with no changes, and from its bundle, and run each for
  a day.
- **Q19:** on Derecho, write grid files with `cli.md`'s snippet and `crocodash create`
  a config naming them; `crocodash create --from` a case's bundle and check the new
  case's grid files keep the source's grid name (`ocean_hgrid_<name>_<session>.nc`).
  For C2: the container end-to-end job (Panama demo) once the submodule is bumped, and
  the next weekly tests run.
- **Q16:** on Derecho, process a case with an interior OBC segment and run it for a day.
- **Q17:** after re-pinning visualCaseGen to ESMCI main, redo #311's cyclic GWR_JRA run on
  Derecho.
- **Q18:** vCG CI. In CrocoDash, `user_nl_datm_streams` must be byte-identical before and
  after.

