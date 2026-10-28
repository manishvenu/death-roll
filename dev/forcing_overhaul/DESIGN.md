# Forcing overhaul: design

Approved 2026-10-23. Research behind it: `research/` (start with `final-synthesis.md`).

## Context

Two open CrocoDash PR stacks plus an uncommitted branch all change how a case's
forcing is configured, processed, recorded and shared:

- **Output files:** #312 → #310 → #313 → #315 → #316 → #317.
- **Timing:** #302 → #303 → #305 → #306 → #297.
- **config-schema-version:** an uncommitted worktree off main.

The goal is one coherent end state:
- forcing is genuinely configurable;
- a `Case` can be read back from just its caseroot and do everything;
- shareable.py is gone;
- fork asks for every forcing input param;
- CESM-case configuration lives in visualCaseGen.

The work is delivered through a short review queue that keeps GitHub uncluttered.

The evidence is in `research/`: 6 read-only reports, 3 designs, 2 critiques and
`final-synthesis.md`.


## Your decisions

1. **Read-back Case does everything:** configure, process, xmlchange and user_nl edits,
   bundle. It never runs create_newcase or case.setup.
2. **visualCaseGen's global `cvars` is bypassed.** Writes name their caseroot, which
   deletes the "writes go to the last case created" guard.
3. **StreamYears, cdeps_streams and user_nl_blocks move to visualCaseGen (ESMCI).**
   CrocoDash refactors in place first and never blocks on ESMCI.
4. **shareable.py and `ReadCrocoDashCase` are deleted.** `Case.from_caseroot` is the one reader.
5. **`crocodash create --from` replaces fork and duplicate** (re-cut 2026-10-26; this
   was "fork replaces duplicate"). A case made from another is a create whose config
   comes from the source (`case_to_yaml`), with the source passed to
   `create_case_from_yaml(source=)`. There is no fork. The bundle stays the transport.
6. **Every forcing input can be asked for** (re-cut 2026-10-26; this was fork's
   prompts): `prompts.ask_forcings` lists the forcings on for the compset and the
   optional ones, asks which optional ones to add, then asks each input. It runs in
   `crocodash create`, `crocodash configure` and `configure_forcings(ask=True)`. A YAML
   or `--no-input` is the same path without prompts, which the MCP uses.
7. **config.json gets a schema_version.** Reading is tolerant, and the version is a gate
   for genuinely incompatible changes.
8. **The timing stack is revised before it merges:** typed `freq` inputs, inert metadata
   cut, bugs fixed. #297 lands on its own.
9. **#321 and #322 are closed.**
10. **No backwards compatibility** for `ocnice/` inputdirs, for state-1.1 cases (they are
    refused: "recreate the case"), or for the crocontainer bundle contract (fixed afterwards).
11. **Review:**
    - only PRs ready for review are open, at most 2 from the CrocoDash queue;
    - the visualCaseGen PRs open together;
    - queued branches are pushed to origin without PRs;
    - PRs are up to ~700 changed lines each, one concept each (pure-deletion PRs are uncapped);
    - your PRs outside this plan (#279, #289, #307, #320) are left alone.
12. **Tests are few, small and focused.** See the testing policy below.
13. **A create config is `Case()`'s and `configure_forcings()`'s arguments** (decided
    2026-10-26, Q19): `case:` names the grid files (`ocn_grid`, `ocn_topo`,
    `ocn_vgrid`), and CrocoDash's YAML has no grid builders, so it never has to stay
    compatible with mom6_forge's API. Grids are made in Python with mom6_forge (e.g.
    crocontainer's grid scripts) or come from another case.


## Names

| Old | New | What it is |
|---|---|---|
| fingerprint / `process_fingerprint()` | **settings** / `step_settings(config)` | The slice of config.json a step's files depend on, plus the sibling entries it reads. A step is finished when its files exist and were made with the current settings. |
| `process_record.json` | **`extract_forcings/finished_steps.json`** | `{schema_version, steps: {step: {settings, files}}}`. A rerun of process_forcings skips finished steps; `--force` overrides that. |
| "baseline" | a **`created`** section in `_crocodash_state.json` (state 1.2.0) | Taken at the end of `Case.__init__`: `{replay_lines, user_nl, xml_files}`. Anything beyond it is the user's own change, which fork and bundle carry over. It replaces bundle's throwaway reference case. Older state files are refused, so there is no fallback. |


## What drives the design (verified)

- **Old configs already fail today.** 53 of the 69 config.json files under `croc_input`
  fail main's strict `deserialize` (base.py:677-689), because they lack
  `ENABLE_BUGS_BY_DEFAULT`. #305, #297, #269 and #311 add more such breaks.
- **The yaml round trip drops `function_overrides`** (freq, dataset_path, member) and
  custom segments.
- **Bundle builds a throwaway CIME case** (create_newcase + case.setup) and diffs it by
  *name* only, so it loses changed values and user overrides of forcing params.
- **Rerunning a step doesn't actually regenerate files.** `--force` and changed settings
  rerun the step, but the engines skip finals that already exist (obc.py:654,
  mom6.py:336). A `clean` step is needed.
- **#315 restores files without checking them.** It copies whatever the new case declares,
  even when boundaries were reordered or dates changed. Restore must compare settings, and
  the settings must not contain absolute paths (substitute `$INPUTDIR`/`$CESMROOT`).
- **Read-back is feasible.** The only blocker is cvars, at about 10 write sites. Also:
  - `case_*` inputs come from `case.__dict__`, so replace that with an explicit
    `forcing_inputs()`;
  - `esmf_mesh_path` must be recorded in the state file;
  - a moved CESM tree needs a `cesmroot=` override.
- **Import cycle.** `forcing/__init__` imports every module, and case.py imports driver.
  So the driver must **not** import Case: `run_workflow` receives the case object.
- **Branches that silently undo or break things:**
  - #269 deletes `ignore_degenerate=True` (the polar fix);
  - #297 pins unmerged rm6 #76;
  - #305 vs #316: keep `min_chunk_days`/`lookback_days`;
  - #297 vs #310: declare the renamed iron file.
- **ESMCI.** You can push to and self-merge on ESMCI/visualCaseGen after alperaltuntas
  approves. vCG CI runs only on PRs into main.


## Target end state

| Where | Owns |
|---|---|
| `forcing/base.py` | <ul><li>The configurator framework.</li><li>Tolerant `deserialize`, `ReconfigureRequired`, `require_output_param`.</li><li>`ParamSpec` + `registry.param_specs(compset, config)`.</li><li>`read_config`/`write_config`, the `CONFIG_*` constants, `CONFIG_MIGRATIONS`.</li><li>`WorkflowContext`.</li></ul> **No case reader.** |
| `case_state.py` | <ul><li>State I/O at 1.2.0 (`esmf_mesh_path`, `created`); older state is refused.</li><li>One version policy, `check_version(doc, path, supported, migrations)`: same MAJOR.MINOR is accepted; an older MINOR is migrated only if a migration is registered (config.json only); newer or another MAJOR is refused.</li></ul> |
| `forcing/driver.py` | <ul><li>`run_workflow(case, *, preview, force, **flags)`. The case is passed in, never imported.</li><li>`finished_steps.json`.</li><li>`step_settings`, with `$INPUTDIR`/`$CESMROOT` substitution and a per-class `process_version`.</li><li>`clean(ctx, step)` before a forced or out-of-date rerun, never when the step has no entry.</li></ul> |
| `case.py` | `Case`: <ul><li>`__init__` (creation is the only place cvars are used) and `from_caseroot(path, *, cesmroot=None)`. One construction path: `__init__` creates the case, then calls `_bind`.</li><li>Lazy `forcing_config`, `configurators()`, `workflow_context()`, `forcing_inputs()`, `forcing_args()`.</li><li>configure, process, validate.</li><li>`xmlchange`, `set_user_nl`, `user_changes`, `apply_user_changes`.</li><li>`bundle`, `copy_forcing_files`.</li></ul> |
| `recipe.py` | YAML: load and validate, `read_grids` (the grid files a config names), `create_case_from_yaml(config, source=)`, a lossless `case_to_yaml` (of a caseroot or a bundle). |
| `prompts.py` | `ask_forcings` (the forcing walkthrough) and `ask_case` (the new case's fields in `create --from`). |
| `cli.py` | Verbs: create (`--config` or `--from`; asks on a terminal), dump, **configure** (asks on a terminal), process, bundle, template. |
| `forcing/atm.py` | A registered ~40-line StreamYears shim that calls vCG. |
| visualCaseGen (ESMCI) | <ul><li>`case_tools.xmlchange/append_user_nl(..., caseroot=, ninst=)`: keyword-only, falling back to cvars, with argument lists.</li><li>`user_nl_blocks.py` with `tag=`.</li><li>`stream_years.plan_stream_years` (pure) and `cdeps_streams.py`.</li></ul> |
| **Deleted** | <ul><li>`shareable.py`, `tests/shareable/`, `ReadCrocoDashCase`.</li><li>`forcing/user_nl_blocks.py`, `forcing/cdeps_streams.py`.</li><li>The CASEROOT guard.</li><li>`generate_configure_forcing_args`.</li><li>The `fork` and `duplicate` verbs.</li><li>The YAML grid builders (`build_grid`/`build_topo`/`build_vgrid`).</li></ul> |

**config.json reading:**
- a missing input takes its constructor default, otherwise `ReconfigureRequired`;
- a missing output, or a missing input left `None` that isn't `optional=True` (a
  placeholder configure_forcings() fills in), loads but raises `ReconfigureRequired`
  when a step reads it (#325 review, 2026-10-28);
- extra keys are ignored.

config.json is written as 1.0.0, and an unversioned file counts as 1.0.0. Bump MINOR,
with a migration, only when tolerant reading would misread a file. No golden configs
(dropped 2026-10-28, user: bad practice; their cases are refused by the state check
anyway): small inline tests cover the reading rules.

**Bundle:** `bundle.json` (2.0.0) plus `caseroot/` (state, user_nl, replay.sh, xml,
SourceMods) and `inputdir/` (config, finished_steps, grids, declared outputs).
`Case.from_caseroot(bundle_dir)` reads it like a caseroot. Old bundles are refused.

**`create_case_from_yaml(config, source=)`** (what `Case.fork` became in the 2026-10-26
re-cut; `crocodash create --from` builds `config` from `case_to_yaml(source)`):
1. Pre-flight (`check_new_case`): refuse an inputdir inside the source's, or the
   source's caseroot name on the source's machine.
2. Create the case, reusing the source's grid files and `session_id`; drop its PE and
   queue settings on another machine.
3. Apply the source's user changes, minus its run's variables.
4. Configure (from the config, or asking on a terminal).
5. Copy the source's files for each step whose settings match
   (`Case.copy_forcing_files`).
6. Print a summary.

"User changes" are the replay.sh lines and user_nl lines beyond the `created` snapshot
(outside CrocoDash's blocks, in every `user_nl_*` file), all SourceMods, and extra xml
files. Variables set by configure_forcings are filtered out, and so are PE/JOB/PROJECT
when the machine changes.


## Testing policy

AI-written changes tend to over-test. Every PR in this plan follows these rules:
- **One test per guarantee a user or developer relies on**, not one per function,
  branch or parameter combination. Before adding a test, name the bug it would catch.
- **No change-detector tests:** no param snapshots, exact log text, exact error wording,
  or source scans when a behaviour test can do the job.
- **Small and local:**
  - extend the existing test file for that module;
  - tiny inline data, no new fixtures, factories or frameworks;
  - mock CIME rather than building real cases;
  - no `slow` marker for anything that matters.
- **Tests are a minority of each PR's lines.** Each PR body lists what its tests cover,
  in one line per guarantee.
- **Delete tests that only covered deleted code**, rather than porting them.
- **Real-case checks** (Derecho/Casper runs) are listed per stack and run by hand once.
  They don't become CI tests.


## Stacks and what's independent

```
main ─┬─ Q1 config-read ─┬─ Q4 case-from-caseroot ─┬─ Q7 declared-output-files ── Q10 finished-steps ──┐
      │                  │                         │                                                  │
      │                  ├─ Q9 forcing-param-specs ┼──────────────────────────────────────────┐       │
      │                  │                         │                                          │       │
      ├─ Q2 writes-name-caseroot ──────────────────┴─ Q11 configure-existing ── Q12 case-changes ── Q13 bundle-and-fork ── Q14 fork-cli-and-prompts ── Q15 drop-shareable
      │        └─ (E2 is built from it)
      ├─ Q3 time-sampling ── Q6 typed-freq-inputs ── Q8 time-windows ── Q5 tseries-time-slice   (Q6 and Q8 also need Q1)
      ├─ #309, #297 (after rm6 #76)
      └─ ESMCI: E1, E3 now; E2 once Q2 is built  ──►  Q18 vcg-case-config (after E1–E3 merge)

Q16 interior-obc-segments (#269): after Q7, Q8, Q11.   Q17 cyclic-grid (#311): after Q7, Q11, ESMCI #50.
```

- **Independent right now** (each on main, none needs another): Q1, Q2, Q3, #309,
  E1, E3, and #297 once rm6 #76 merges.
- **Stack C, config → case → outputs:** Q1 → Q4 → Q7 → Q10.
- **Stack T, timing:** Q3 → Q6 → Q8 → Q5. Q6 and Q8 add conditions params, so they also wait
  for Q1's tolerant reading. Nothing in the case or sharing work depends on this stack:
  the recipe round-trip fix lives in Q1, not in the typed-freq PR.
- **Stack S, sharing:** Q11 → Q12 → Q13 → Q14 → Q15. It starts once Q2 and Q4 merge;
  Q13 also waits for Q10, and Q14 for Q9.
- **Singles:**
  - Q2 (writes; the root of S and of E2);
  - Q5;
  - Q9 (after Q1 only);
  - Q16, Q17 (OBC re-cuts at the end);
  - Q18 (vCG consume).


## Decision → queue

| Decision | Q |
|---|---|
| 1 Read-back does everything | Q2, Q4, Q11, Q12, Q13 |
| 2 Bypass cvars | Q2, E1 |
| 3 Move to vCG | Q2 → E1–E3 → Q18 |
| 4 No shareable, no ReadCrocoDashCase | Q4, Q7, Q10, Q11–Q15 |
| 5 Fork replaces duplicate | Q13, Q14 |
| 6 Prompts and YAML | Q9, Q14 |
| 7 schema_version | Q1, Q10, Q13 |
| 8 Timing revised | Q3, Q5, Q6, Q8, #297 |
| 9 Close #321/#322 | triage, Q15 |
| 11 Review queue | the queue |
| 12 Focused tests | testing policy, Tests column |


## Risks

- **ESMCI is slow, or declines E3.** ESMCI work only feeds Q18, and Q2 has a local helper.
  Never pin an unmerged head.
- **Q7 and Q8 touch the same engine signatures** (#316 vs #305). Whichever lands second
  keeps `min_chunk_days`/`lookback_days`; Q8's wiring test guards this.
- **Tolerant reading hides real breakage.** Only constructor defaults are filled in,
  and missing outputs and placeholder inputs raise where they are used.
- **Existing (state 1.1) cases must be recreated** to use read-back, configure, bundle or
  fork. Put this in the release notes.
- **Long-lived pushed branches drift from main.** Rebase on every merge. (The plan was
  to build only one step ahead per stack; on 2026-10-23 the user chose to build everything
  ahead instead.)

**Out of scope:** rm6 #77; time windows for WW3; a separate IC settings entry; unifying the
CICE/WW3 function-argument conventions; JSON Schema; CIME `create_clone`; #279, #289, #307, #320.


## Defaults I chose (change any)

- **StreamYears:** a ~40-line shim stays in CrocoDash.
- **Fork copies** only files whose settings match.
- **Old bundles** are refused.
- **#269:** restore `ignore_degenerate`.
- **Typed freq names:** `data_freq` / `subsample_freq`.

