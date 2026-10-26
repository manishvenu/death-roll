# Moving StreamYears and user_nl_blocks into visualCaseGen: what the code shows

**Refs used.** CrocoDash: **M** = origin/main 510139f9, **S** = origin/skip-finished-forcing-steps 72226b94, **B** = origin/bgc-fe-interior-source 0a66b7ee. visualCaseGen: **V** = c553683, which M, S and B all pin, and which `gh api` reports as the current ESMCI/visualCaseGen main. CESM = /glade/work/manishrv/installs/CESM_crocodash (CDEPS cdeps1.0.101-10). Line numbers are from M unless a branch is named.

## FACTS

### 1. CrocoDash side

**How the branches differ.**
- `forcing/atm.py`, `forcing/cdeps_streams.py`, `forcing/user_nl_blocks.py` and their three test files are identical on M, S and B.
- S only changes base.py and case.py:
  - It adds `ReadCrocoDashCase` (S base.py:108-148). It reads `_crocodash_state.json` and `extract_forcings/config.json`, builds a `WorkflowContext` and deserializes the configurators. It uses neither CIME nor cvars.
  - It adds `output_files` and `process_fingerprint`, and drops `is_file`.
  - `XMLConfigParam.apply` moves to S base.py:501-510.
- B only adds `resolve_time_sampling` to `configure_forcings`. That moves the CASEROOT guard to B case.py:627 (it is at 620 on M and S).
- S is the tip of a PR stack: #312 → #310 → #313 → #315 → #316 → #317. Only #312 targets main.
- B is PR #297, stacked on #306 → #305 → #303 → #302 → main.

**atm.py (183 lines).**
- **Imports:** `base *`, `cdeps_streams`, `user_nl_blocks`, `setup_logger` (16-18).
- **Activation:** `@register`, `name="StreamYears"`, `required_for_compsets=["DATM%JRA"]`, `allowed_compsets=["DATM"]` (27-31). Matching is by substring (base.py:731-738).
- **Inputs** (35-47, 57-75): `case_cesmroot`, `start_date`, `end_date`, `stream_year_padding=1`, `narrow_stream_files=True`.
  - The constructor also takes `date_range`, which is not a declared input. It turns it into `%Y%m%d` strings (66-68).
  - `case_cesmroot` is filled in automatically: the registry prefixes every public Case attribute with `case_` (base.py:124-130).
  - `date_range` is the same pd.DatetimeIndex that `configure_forcings` hands to every configurator (case.py:610-616).
  - So the user passes nothing (2_case_setup.md:102,122).
- **Outputs:** two `ConfigOutputParam`s, `datm_streams` and `drof_streams` (48-55). Each holds a plan dict, stored in config.json under `"streamyears"`.
- **Nothing happens in `process_forcings`.** There are no `process_components` (the base default is `{}`, base.py:522). driver.py never mentions streams, user_nl or xmlchange on M, S or B.
- **`configure()`** (150-183):
  - It gets the CIME case through `self.registry.case._cime_case` (158-159). That is a private Case attribute, set from vCG's `get_case` (case.py:217-218).
  - It reads `DATM_MODE` and `DROF_MODE` (24, 162).
  - `_plan` (77-128) skips the whole component if any one stream is single-year or doesn't cover the run (100-112).
  - Otherwise it sets `year_first = max(avail_first, start-1-pad)`, `year_last = min(avail_last, end+pad)` and `year_align = year_first` (117-123), and optionally narrows `datafiles` (124-127).
  - `_apply` writes `stream:key = val` lines via `user_nl_blocks.write("StreamYears", f"{component}_streams", …)` (138-148).
  - With no registry or case (deserialize, inspect), every component is reported "skipped" (163-167).

**cdeps_streams.py (131 lines).**
- These are pure functions of `cesmroot` plus a case-like object: `stream_names` (60-80, via CIME's `NamelistDefinition`), `coverage` (91-94) and `datafiles` (97-131), the last two via CDEPS's `StreamCDEPS`.
- Files read:
  - `components/cdeps/<comp>/cime_config/{stream,namelist}_definition_<comp>.xml`
  - `cdeps/cime_config/stream_definition_v2.0.xsd` (15-20, 38-57)
- It puts `<cesmroot>/cime` and the CDEPS config directory on sys.path itself (23-35, 48).
- It calls private CDEPS methods: `_get_stream_first_and_last_dates` (94), `_resolve_values` (108, 114, 118) and `_sub_paths` (123).
- The case argument only needs a `get_value()` method (CESM stream_cdeps.py:507-523).
- It imports nothing from CrocoDash or vCG.

**user_nl_blocks.py (230 lines).**
- **Imports:** only `cvars` and vCG's `append_user_nl` (29-30). Nothing from CrocoDash, and no logger (it uses `print`).
- **Block format** (32-35, 192-197): a blank line, then
  `! >>> CrocoDash configure_forcings: <owner> [sha:<sha1(body)[:8]>] (rewritten on every call…)`,
  the body, and `! <<< CrocoDash configure_forcings: <owner>`. The owner is the configurator's `name`.
- **Public functions:**
  - `snapshot(caseroot)` 101-107, `restore(caseroot, contents)` 110-117, `strip(caseroot)` 120-145, `report_edits(caseroot, edited)` 200-230. All take the caseroot explicitly and glob `user_nl_*`, so they don't care how many instances there are.
  - `write(owner, model, groups)` 148-197 is the only one without a caseroot:
    - It reads `cvars["CASEROOT"]` and `cvars["NINST"]` (156-157).
    - It picks `user_nl_<model>` or `user_nl_<model>_NNNN` (42-48).
    - It leaves out any variable already set outside a block, ignoring case and spaces (77-94, 162-170).
    - It logs through `append_user_nl(…, do_exec=False)` (175-176), which reads cvars again (V case_tools.py:76-77).
- Everything CrocoDash-specific is text only: the markers (32-34) and the error and warning messages (65-69, 179-181, 218-230).

**base.py write paths.**
- base.py imports vCG's `xmlchange` (5) and `user_nl_blocks` (6).
- `UserNLConfigParam` (405-443) has no `apply`. Its `inspect(caseroot)` reads `user_nl_<name>` directly and only knows the single-instance file name.
- `XMLConfigParam.apply` calls vCG `xmlchange` (463-472). Its `inspect(caseroot)` already runs `./xmlquery` with `cwd=caseroot` (474-483).
- `BaseConfigurator.is_non_local` comes from `registry.case.is_non_local` (613-624).
- `configure()` makes one `user_nl_blocks.write(self.name, …)` call per user_nl file and calls `.apply()` on the other outputs (626-649).
- Only runoff.py:33-42 and ww3.py:485 use `XMLConfigParam`.

**configure_forcings (M case.py).**
- Guard on `cvars["CASEROOT"]`: 618-628.
- `self.session_id = cvars["MB_ATTEMPT_ID"]` (630). This becomes `case_session_id` in BGC, chl and runoff output file names (e.g. bgc.py:113-115, 223).
- snapshot → strip → run_configurators → report_edits, with restore on failure: 638-658.
- After the configurators have run, it calls `xmlchange` for CALENDAR, RUN_STARTDATE, STOP_OPTION and STOP_N (667-686). Each passes `self.cc._is_non_local()`, which compares against `cvars["MACHINE"]` (V case_creator.py:74-80).
- runoff.py:66-72 also reads `cvars["CUSTOM_ROF_GRID"]`.

**Other places that write through vCG helpers.**
- case.py:440 and 457 (`append_user_nl` during `__init__`), and 1097-1113 (`xmlchange`).
- shareable.py:63-76 (`append_user_nl` into whatever case cvars currently points at) and 89-100 (`xmlchange` with `is_non_local=True` hard-coded).
- CrocoDash already reaches CIME without vCG in shareable.py:748-764: `_run_xmlquery`, then `CIME.case.Case(caseroot, read_only=True, non_local=True)`.
- `CaseBundle` reads xmlchanges back from `replay.sh` (shareable.py:179-193).

**Who imports and calls these modules.**
- **atm:** nobody by name; it is loaded by the auto-import in forcing/__init__.py:7-19.
- **cdeps_streams:** atm.py:17 and tests/forcing/test_atm.py:16.
- **user_nl_blocks:** base.py:6, atm.py:17, case.py:21.
- **Tests that patch them:**
  - test_user_nl_blocks.py:10
  - test_mom6_engine.py:7, 398, 483 (monkeypatches `write(owner, model, groups, **kw)`)
  - test_cice.py:102
  - test_atm.py:111-210 (patches `CrocoDash.forcing.user_nl_blocks.write`)
- **Docs:**
  - api-docs/CrocoDash.forcing.rst:7-10, 34, 106
  - 2_case_setup.md:102, 122
  - the case.py:540 docstring
  - for_developers/submodule_api_usage.md:60-62, which is already out of date (it says `append_user_nl` is called from base.py and atm.py)
- **MCP_CrocoDash** (main d097e1f): no imports of these modules. StreamYears appears in:
  - server.py:61-63
  - tools/case.py:497 and 772-773
  - tools/discovery.py:21-31 (`list_forcing_configs` iterates `ForcingConfigRegistry.registered_types`)
  - crocodash_mcp_scope.md:35
  It also holds a `CASE_BUILD_LOCK` because of vCG's global state (tools/case.py:24-28).

**Tests and the fixtures they need.**
- **test_atm.py (227 lines).**
  - Every test uses the `cesmroot` fixture, which requires `skip_if_not_glade` and `get_cesm_root_path` (test_atm.py:48-54).
  - It uses a `FakeCimeCase` (only `get_value`, `get_resolved_value` and DIN_LOC_ROOT) plus a `FakeRegistry`. No real case and no inputdata are needed.
  - **These tests currently skip everywhere.** On GLADE, `get_cesm_root_path` hard-codes `/glade/u/home/manishrv/work/installs/full_regional_cesm` (fixtures/state.py:28-32), and that path no longer exists. GitHub Actions is not GLADE, so they skip there too.
- **test_user_nl_blocks.py (223 lines):**
  - Uses `tmp_path` and replaces `cvars` CASEROOT/NINST with `SimpleNamespace` objects (34-40, 131-133, 166-168).
  - One test (193-223) also needs CESM's CIME and the MOM_interface parser (user_nl_helpers.py:16-26).
- **test_configure_forcings_rerun.py (177 lines):**
  - Builds a real Case with a DATM%JRA compset via `CrocoDash_case_factory` (fixtures/objects.py:62-118).
  - Asserts `user_nl_datm_streams` exists (63) and tests the guard (164-177).
  - It runs in GitHub CI, using the CESMROOT environment variable.
- **Other tests tied to this code:**
  - test_base.py:165-183 (patches `base.xmlchange`).
  - test_base.py:225-249 (patches cvars, and asserts vCG's log line "Adding parameter changes to user_nl_cice").
  - test_configurators.py:10-16 (assigns cvars directly, with no monkeypatch).
  - test_ww3.py:899, shareable/test_apply.py:46 and 108, test_case.py:121-125, test_logging.py:82-86.

### 2. Dependencies that would have to be cut
- **atm.py depends on:**
  - the configurator framework from `base *` (`register`, `BaseConfigurator`, the param classes)
  - `registry.case._cime_case`
  - `Case.cesmroot` (through the `case_` prefixing)
  - the `date_range` that `configure_forcings` passes in
  - the logger and `user_nl_blocks`

  It does **not** depend on `Calendar` or on `ConditionsConfigurator`. It gets the same `date_range` input, not the conditions configurator's outputs.
- **The CDEPS logic itself needs only:** cesmroot, the mode string, something with `get_value`, the start and end years, the padding and the narrow flag.
- **user_nl_blocks depends on:** the two cvars plus the `append_user_nl` log call. Nothing else.
- **Ordering:** RUN_STARTDATE and STOP_N are set *after* the configurators run (638-686). A helper that read the run dates from the case's xml would get the previous call's values. Today the years are passed in as arguments.

### 3. visualCaseGen side (V)

**case_tools.py (136 lines).**
- Functions:
  - `is_ccs_config_writeable` 12-19
  - `run_case_setup(do_exec, is_non_local, out)` 21-49
  - `append_user_nl(model, pairs, do_exec, comment, log_title, out)` 51-105
  - `xmlchange(var, val, do_exec=True, is_non_local=False, out=None)` 107-136
- All of them find the case only through `cvars["CASEROOT"]` (33, 76, 121). `append_user_nl` also reads `cvars["NINST"]` (77, 100-105).
- `xmlchange` builds `f"./xmlchange {var}={val}"` and runs it with `shell=True` (123-134). On failure it raises without including stderr.
- There is no `is_non_local` function. The check is `CaseCreator._is_non_local()`: `cime.machine != cvars["MACHINE"]`.
- vCG has no tests for case_tools.
- Inside vCG, only `CaseCreator` calls these, always positionally: `xmlchange(..., do_exec, self._is_non_local(), self._out)` (605-991), `append_user_nl` (670-672), `run_case_setup` (166).

**Existing caseroot-explicit path.** The only one is `CIME_interface.get_case(caseroot, …)` (cime_interface.py:918-924), and it needs a fully built CIME_interface.

**Global state.**
- `initialize()` wipes every cvar, then builds the CIME interface, widgets, stages and the constraint solver (initialize.py:32-39).
- `cvars` is a plain class-level dict (config_var.py:33, 471). In a process that never built a Case, `cvars["CASEROOT"]` raises KeyError.
- Importing any vCG module runs `visualCaseGen/__init__.py`, which does `gui = GUI()` and builds an ipywidgets tree. CrocoDash already pays this cost whenever it imports `CrocoDash.forcing` (via base.py:5).

**Where CESM-input helpers live today.** The generator modules are ipywidgets `VBox` classes tied to cvars:
- runoff_mapping_generator.py (235 lines; the actual computation is in `mom6_forge.mapping`)
- ww3_input_generator.py (103 lines)
- mom6_forge_launcher.py (442 lines)

There is no plain-function helper module apart from case_tools. A `git grep` finds no DATM, DROF or stream handling anywhere in vCG.

**Layout.**
- Installed packages: `ProConPy` and `visualCaseGen` (pyproject `[tool.setuptools] packages`).
- `external/` holds the mom6_forge and ipyfilechooser submodules.
- `custom_widget_types/` has no `__init__.py`.

**Test tiers.**
- 1_unit (8 files): constraint-solver only, no CESM needed.
- 2_integration (5 files): call `CIME_interface()`, so CESM is needed.
- 3_system (5 files): create real cases.
- 4_static (2 files).

CI (ci-tests.yml):
- runs on push and PR to main, on Python 3.11 and 3.12
- checks out ESCOMP/CESM cesm3_0_alpha09g and runs fleximod
- copies vCG into CESM/visualCaseGen and runs `pytest tests`

The CESM root is found from the argument, then CESMROOT, then two levels above the package (cime_interface.py:94-104). Both that CESM and CROCODILE-CESM/CESM `crocodash` use CDEPS fxtag cdeps1.0.101.

**What a unit test for a moved module would need.**
- The block functions, once given an explicit caseroot and ninst, need only `tmp_path`. That fits 1_unit.
- The stream functions need a CESM tree with CDEPS and CIME. That fits 2_integration, and vCG's CI provides the tree. No inputdata is needed.

**Branches and PRs.**
- **Pin history on CrocoDash main:** f0631202 pinned 1cd2ec3 (the ESMCI `crocodash` branch); 5b086e74 pinned 3977ab6; 84016186 pinned c553683.
- **ESMCI branches:** `crocodash` is now 15 commits ahead of and 5 behind main.
- **Open ESMCI PR:** only #50, a draft (`cyclic-bounding-boxes`, fb8d019) that only bumps mom6_forge. CrocoDash's `cyclic-grid` branch (#311, draft) pins that commit.
- **CROCODILE-CESM/visualCaseGen:** a fork 73 commits behind the pin, with two open PRs from 2025 (#5, #6). CrocoDash's `.gitmodules` points at ESMCI, not this fork.
- **`new_vcg_main`** is a CrocoDash branch, not a vCG branch (it pins cc1195b and is 40 commits behind main).
- **Standalone checkout:** on `bring_in_m6f_new` (b21b03f), clean, 5 commits behind the pin and 0 ahead. Its local `main` is also 5 behind.
- **Embedded copy** in your main CrocoDash checkout: detached at c553683.

### 4. Feasibility and API-sketch facts
- **user_nl_blocks:** four of the five public functions already take the caseroot. `write` would need `(caseroot, ninst)` added, plus a log formatter that doesn't go through `append_user_nl`.
- **Stream alignment:** needs no cvars. Its only live dependency is something that answers `get_value` for DATM_MODE/DROF_MODE and expands `$` variables. That could be CIME's `Case(caseroot, read_only=True)`, the way shareable.py:748-753 already does it, or a small wrapper around `./xmlquery`.
- **Where NINST could come from without cvars.** In nuopc, CIME:
  - creates `user_nl_<comp>_NNNN` files, including the `_streams` ones, from `NINST` (CESM case_setup.py:74-75, 87-97)
  - maps `NINST_<comp>` to `NINST` (env_mach_pes.py:65-69)
  - DATM's buildnml then reads `user_nl_datm_streams_NNNN` (datm buildnml:235, 266-268)

  So any of these would work:
  - running `./xmlquery NINST` in the caseroot
  - the `ninst` value CrocoDash already saves in `_crocodash_state.json` (it is not in `INIT_ARGS_EXCLUDE`, case_state.py:32-45)
  - globbing for the instance files
- **is_non_local** is not saved in the state file (case.py:1071-1089). shareable.py hard-codes `True`.
- **Backward compatibility in vCG:** adding a keyword-only `caseroot=None` (falling back to cvars) to `xmlchange`, and `caseroot=None, ninst=None` to `append_user_nl`, keeps every positional `CaseCreator` call valid.
- **replay.sh:** `./xmlchange` records each change in `replay.sh`, which `CaseBundle` reads. Writing through CIME's `Case.set_value` would not record it.

### 5. Cross-repo sequencing facts
- **Install:** environment.yml:22-30 installs vCG editable from `./CrocoDash/visualCaseGen/` (and mom6_forge and ipyfilechooser from inside it). The editable finders map only `ProConPy` and `visualCaseGen`. New files inside `visualCaseGen/` are picked up automatically. A new top-level package would need a pyproject change and a reinstall in every environment, including the container image.
- **Your environments:**

  | Env | Where it points | Notes |
  |---|---|---|
  | `CrocoDash` (default `python`) | /glade/work/manishrv/crocodile2026/CrocoDash (4d503756, vCG 3926103) | Not your main checkout |
  | `dev_cd` | Your main checkout and its embedded vCG | Also runs the crocodash MCP server (/glade/u/home/manishrv/documents/croc/.mcp.json) |
  | `dev_vcg` (Python 3.12) | The standalone vCG checkout | — |

  There is no `visualCaseGen` environment, even though CLAUDE.md:73 names one.
- **CrocoDash CI:**
  - Checks out submodules recursively (testing.yml:43-45, 196-198; deploy_sphinx_docs.yml:17-19).
  - pytest skips the vCG tree (pytest.ini; testing.yml:119), so vCG's tests never run in CrocoDash CI.
  - The environment cache key includes vCG's pyproject and environment.yml (testing.yml:109).
  - `check_submodule_bumps.yml` fails any PR that moves `CrocoDash/visualCaseGen` unless it has the `submodule-bump` label.
  - The API-docs check (deploy_sphinx_docs.yml:26-52) doesn't cover vCG modules (vCG is passed as an exclude pattern). It will fail if modules are removed from `CrocoDash/forcing/` until CrocoDash.forcing.rst is regenerated.
- **Other branches that move the pin:** `cyclic-grid` needs vCG #50, and it also edits case.py right next to the guard (adds `self.cyclic_x` around line 629).

## OPINIONS / RISKS
1. **Feasible as plain functions in vCG with no cvars.** The real coupling is two lines plus the log call in `write()`, and atm's reach into `_cime_case`.
2. **Keep a thin registered "StreamYears" configurator in CrocoDash.** The `"streamyears"` entry in config.json, MCP's `list_forcing_configs` output and the docs all depend on it being registered. The shim would hand caseroot, cesmroot and the years to vCG and record the plan it gets back.
3. **The block marker is the biggest silent-failure risk.** If a generic ESMCI version renames the marker, the blocks in existing cases stop being recognised. `write()` would then treat their keys as user settings and skip them, so the old values would silently stay. The parser needs to accept the old marker, or the marker prefix needs to be a parameter.
4. **Removing the CASEROOT guard alone isn't enough.** The session id (case.py:630), runoff's `CUSTOM_ROF_GRID`, and `_is_non_local` (via cvars MACHINE) also come from whichever case was created last. They need to come from the state file or `self` first.
5. **Moving the code doesn't remove the dependence on private CDEPS methods.** On the plus side, vCG's CI would actually run the stream tests, which skip everywhere today. The downside is that vCG's CI then depends on CDEPS internals, and ESMCI's maintainers (alperaltuntas authored most recent merges) may push back on that.
6. **Every change takes two steps across repos:** an ESMCI merge, then a CrocoDash PR that bumps the pin, carries the `submodule-bump` label and regenerates the API docs. It also has to be reconciled with the #50/`cyclic-grid` pin.
7. **Keep using `./xmlchange` (to preserve replay.sh) but pass arguments as a list instead of a `shell=True` string,** so values with spaces or commas don't break.
8. **The log text will change.** test_base.py:248-249 asserts vCG's current `append_user_nl` heading, so a new formatter breaks that assertion.