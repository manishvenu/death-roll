# Can a `Case` be built from an existing caseroot? Feasibility report

**Short answer:** yes, it's feasible. A case created earlier already has every input that `configure_forcings`, `process_forcings` and the configurators need, either in its state files or in CIME's env xml. The one real blocker is visualCaseGen's process-wide global state (`cvars`). Every write to `user_nl` or xml goes through it, and that is about ten call sites.

**Sources and tags used below:**
- Repo: `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash`.
- **[S]** = `origin/skip-finished-forcing-steps`, **[M]** = `origin/main`, **[T]** = `origin/bgc-fe-interior-source`, **[CSV]** = the uncommitted `config-schema-version` worktree.
- `case.py` on [M] is identical to [S] up to L662.
- **VCG** = `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash/CrocoDash/visualCaseGen`, at the same commit (c553683) on every branch I read.
- **M6F** = `VCG/external/mom6_forge/mom6_forge`.
- **CIME** = `/glade/work/manishrv/installs/CESM_crocodash/cime/CIME`.
- I ran nothing that executes CrocoDash, visualCaseGen or CIME. Anything marked "unverified" is reasoned from reading the code.

---

## 1. What `Case.__init__` does [S] (FACTS)

1. **Captures its arguments.** It stores the scalar arguments from `locals()`, minus `INIT_ARGS_EXCLUDE` (case.py:126-129). The excluded names are grid/topo/vgrid, compset, machine, cesmroot, caseroot, inputdir and override (case_state.py:32-45). **`override` is never saved.**
2. **Initializes visualCaseGen:** `self.cime = initialize_visualCaseGen(cesmroot)` (132).
3. **Validates arguments** in `init_args_check` (143-160).
   - It raises if caseroot or inputdir exists and `override` is false (293-302).
   - It checks grid names against `cime.domains`, machine against `cime.machines`, and `project_required` (329-362).
4. **Sets attributes** (163-186): cesmroot, caseroot, inputdir, ocn_grid/topo/vgrid, atm_grid_name, rof_grid_name, ninst, machine (falls back to `self.cime.machine`), project, override, ntasks_ocn, job_queue, job_wallclock_time, compset_alias, compset_lname, ProductRegistry, `forcing_product_name=None` and `_configure_forcings_called=False`.
5. **Drives the visualCaseGen Stage machine** in `_configure_case` (190-197, body 802-1075) through `cvars`:
   - compset (819-898);
   - grid (900-1005), including `MB_ATTEMPT_ID = uuid1()[:6]` at 956;
   - launch (1061-1075): CASEROOT, MACHINE, PROJECT, NINST, PECOUNT.
6. **`override=True` deletes** inputdir, caseroot and `cime_output_root/<name>` (199-206).
7. **Writes grid files** in `_create_grid_input_files` (370-415):
   - `inputdir/ocn/{ocean_hgrid,ocean_topog,ocean_vgrid,scrip,ESMF_mesh}_{grid}_{session}.nc`;
   - `ice/cice_grid_*` if the compset has CICE, and `wav/*.inp` if it has WW3;
   - it sets `supergrid_path`, `topo_path`, `vgrid_path` and `esmf_mesh_path`.
8. **Creates the CIME case** in `_create_newcase` (468-481) via `CaseCreator(add_grids_to_ccs_config=False).create_case(do_exec=True)`. That runs:
   - `create_newcase --res USER_RES` (VCG/visualCaseGen/custom_widget_types/case_creator.py:493-569);
   - the grid xmlchanges (904-971, including ROF_GRID and ROF_DOMAIN_MESH at 968-970);
   - **`case.setup`** (166);
   - the `user_nl_mom` grid/DT block (696-806) and the `user_nl_cice` grid file (808-828).
9. **Opens a read-only CIME case:** `self._cime_case = self.cime.get_case(caseroot, non_local=cc._is_non_local())` (217-219).
10. **Finishes the case:**
    - WW3 time steps and CICE `ndtd` go into `user_nl` (222-225, 435-466);
    - `self.is_non_local` is set (227);
    - `_apply_final_xmlchanges` sets MOM6_MEMORY_MODE, NTASKS_OCN, JOB_QUEUE and JOB_WALLCLOCK_TIME (1097-1120);
    - `_write_state` writes `_crocodash_state.json` (1077-1095).

## 2. What the code after creation reads from `self` [S] (FACTS)

**`configure_forcings`** (483-692) reads:
- inputdir, caseroot, compset_lname and `ocn_grid.name` (631);
- `override` — if true it `rmtree`s the whole `extract_forcings`, including `raw_data` (651-652);
- the `cvars["CASEROOT"]` guard (618-628);
- `cvars["MB_ATTEMPT_ID"]` → `self.session_id` (630);
- `self.cc._is_non_local()` for four xmlchanges (668-687);
- `_print_forcing_files`, which uses `ReadCrocoDashCase` (1122-1140).

It sets extract_forcings_path, forcing_product(_name), boundaries, date_range, session_id, grid_name and fcr.

**Other methods:**
- **`process_forcings`** (694-758) needs only `_configure_forcings_called` and `extract_forcings_path`. `run_workflow` itself needs no Case (driver.py:125-128), and `crocodash process --caseroot` already runs with no Case (cli.py:34-75).
- **`validate_case`** (1142-1151) needs `self.fcr`.
- **`expt`** (764-800) needs `_cime_case.get_value("RUNDIR")` (791), the topo min/max depth, the grid and vgrid objects, and `inputdir/"ocn"` (792).
- **The `*_in_compset` properties** (250-268) use `compset_lname` only.

**How configurators get Case values.** `ForcingConfigRegistry.__init__` turns every key in `case.__dict__` that doesn't start with `_` into an input named `case_<key>` (forcing/base.py:165-171). Properties are not in `__dict__`, so they are not passed. A required configurator missing one of these raises `ValueError` (base.py:244-249).

| `case_*` input | Used by (file:line [S]) | Required? |
|---|---|---|
| `case_cesmroot` | atm.py:36,59 (StreamYears, required for `DATM%JRA`) | yes |
| `case_session_id`, `case_grid_name` | bgc.py:90-91,184-185; chl.py:19-20; runoff.py:19-20 | yes |
| `case_inputdir` | cice.py:231,270; runoff.py:22; ww3.py:433 | yes (runoff, ww3) |
| `case_compset_lname` | runoff.py:21 | yes |
| `case_esmf_mesh_path` | runoff.py:33,52 | **yes, no default** |
| `case_cime` | runoff.py:53,67-73 — also reads `cvars["CUSTOM_ROF_GRID"]` | optional |
| `case_forcing_product` | bgc.py:209, chl.py:52 | optional |
| `case_cyclic_x` | open PR #311, cice; set in configure_forcings from `self.ocn_grid.supergrid.is_cyclic_x` | — |
| `case_supergrid_path` | open PR #269, mom6.py | — |

The timing stack [T] adds no new Case dependency; its only change is `resolve_time_sampling` inside configure_forcings.

**Configurators that reach into the Case object directly:**
- atm.py:158-159 reads `registry.case._cime_case` for DATM_MODE/DROF_MODE and for stream `$DIN_LOC_ROOT` resolution (cdeps_streams.py:91-118).
- base.py:651-662 reads `registry.case.is_non_local`.

## 3. visualCaseGen's global state (FACTS unless marked)

**What `initialize()` does and costs** (VCG/visualCaseGen/initialize.py:16-41):
- It calls `ConfigVar.reboot()` and `Stage.reboot()`, builds `CIME_interface`, then all ConfigVars, ipywidgets, the Stage tree and option specs, then `csp.initialize`. That last step is a z3 rank solve plus `Optimize.minimize` (ProConPy/csp_solver.py:107-118, 211-216).
- `CIME_interface` runs `git describe --tags` and asserts CIME 6.4.x (cime_interface.py:111-130).
- It appends cimeroot to `sys.path` (54) and parses all the component, grid, compset, machine and CLM XML (71-80).
- It probes the host machine, with a casper hostname patch (717-736).
- It creates CIME_OUTPUT_ROOT if it is missing (767-772).
- I did not measure the cost (not executed). It is clearly the most expensive step that doesn't involve CIME subprocesses.

**What `cvars` is.** `cvars` is the class-level dict `ConfigVar.vdict` (ProConPy/config_var.py:33, 471).
- Every `.value =` assignment goes through the traitlets `@validate` hook, then `csp.check_assignment`, which asserts the solver is initialized (config_var.py:437-450; csp_solver.py:296). It then goes through `register_assignment` (config_var.py:134-147).
- There is no way to set a value that skips this.

**Every `cvars` read after creation** (full grep of [S]):
- CASEROOT: case.py:620 and user_nl_blocks.py:156.
- NINST: user_nl_blocks.py:157.
- MB_ATTEMPT_ID: case.py:630.
- CUSTOM_ROF_GRID: runoff.py:70,73.
- Indirectly, visualCaseGen's `xmlchange`/`append_user_nl` read CASEROOT and NINST (case_tools.py:76-77,121), and `cc._is_non_local()` reads MACHINE (case_creator.py:74-80).

**The singleton problem.** Every `Case()` call re-runs `initialize`, so the previous case's `cvars` are gone.
- The guard at case.py:618-628 (documented at 544-546) catches this.
- Without the guard, MB_ATTEMPT_ID and `_is_non_local()` would silently use the newer case's values, because they are read at call time.

**Can these `cvars` be set without walking the Stage tree?**
- CASEROOT is a string var in the Launch stage (launcher_vars.py:15; launcher_stages.py:17-21).
- NINST and MB_ATTEMPT_ID belong to no stage (launcher_vars.py:24-27; grid_vars.py:56).
- MACHINE's options are `cime.machines` (specs/launcher_options.py:10-11).
- Stage observers only advance a stage that is enabled (ProConPy/stage.py:362-369).
- **Opinion, unverified:** after `initialize()`, assigning these four directly should pass the CSP checks without going through the stages. Without `initialize()` it is impossible.
- Tests already work around ConfigVar entirely with `cvars["CASEROOT"] = SimpleNamespace(value=…)` (tests/forcing/test_configurators.py:169-173; tests/forcing/test_output_files.py:55-56). So the forcing code only ever needs `.value`.

**Can `xmlchange`/`append_user_nl` target an arbitrary caseroot?** Not as written: neither takes a caseroot, and both read `cvars` before they even check `do_exec`.
- What they actually do is small: run `./xmlchange V=X [--non-local]` with `cwd=caseroot` (case_tools.py:123-136), or append lines to `user_nl_<model>[_NNNN]` (93-105).
- CIME's xmlchange accepts `--caseroot` (CIME/Tools/xmlchange:86-87).
- CrocoDash already makes caseroot-explicit CIME calls in two places: `XMLConfigParam.inspect` (base.py:512-521) and `_run_xmlquery` (shareable.py:754-762).

**Every write that goes through `cvars`** [S]:
- case.py:440, 457, 668-687, 1103-1120;
- base.py:505 (`XMLConfigParam.apply`, used by runoff.py:36,40 and ww3.py:485) and 684;
- atm.py:148;
- user_nl_blocks.py:156-157, 176;
- shareable.py:73, 98.

## 4. Rebuilding grid objects and CIME access (FACTS)

**Grid, topo and vgrid APIs** (these signatures match the copy the active conda env loads, `/glade/work/manishrv/crocodile2026/.../mom6_forge`):
- `Grid.from_supergrid(path, name=None)` (M6F/grid.py:614-636). The name defaults to the file stem, so pass `name=state["grid_name"]`.
- `Topo.from_topo_file(grid, topo_file_path, min_depth=0.0, varname="depth", version_control_dir="TopoLibrary", git=False, channel_widths=None)` (topo.py:293-334). With `git=False` it has no filesystem side effects.
- `VGrid.from_file(filename: str, variable_name="dz", variable_type="layer_thickness", name=None)` (vgrid.py:117-168). It asserts `filename.endswith(".nc")` (143), so it needs a `str`, not a `Path`.
- Existing code already rebuilds them this way: recipe.py:80-127, and `WorkflowContext.grid`/`ocn_topo` with `read_min_depth` (base.py:89-105).

**The CIME Case object doesn't need `create_newcase` to be re-run.**
- `_get_case_obj` (shareable.py:746-751) runs `./xmlquery CIMEROOT`, appends it to `sys.path`, then calls `CIME.case.Case(caseroot, read_only=True, non_local=True)`. visualCaseGen's `get_case` (cime_interface.py:918-924) is the same.
- CIME's `Case.__init__` needs `env_case.xml` (CIME/case/case.py:106-112) and loads the SRCROOT customize directory (130-140).
- With `non_local=False` on NCAR hosts it asserts that the probed host equals the case's MACH (190-205).

**Gaps in what the state file records**, checked against `/glade/u/home/manishrv/croc_cases/streamyr_v15`:
- `esmf_mesh_path` is not recorded (case.py:1077-1095). CaseBundle finds it by globbing `ESMF_mesh_*.nc` (shareable.py:157).
- The env xml COMPSET ends in `_SESP`, while `state.compset_lname` does not.
- RUNDIR is stored unexpanded (`$CIME_OUTPUT_ROOT/$CASE/run`).
- `state.rof_grid_name` may be null (visualCaseGen resolved it automatically). The real value is only in env xml ROF_GRID / ROF_DOMAIN_MESH.
- `compset_alias` is not stored.

## 5. Required state → where it lives → how to read it → cost

| What's needed | Source on disk | How to read it | Cost |
|---|---|---|---|
| inputdir, cesmroot, compset_lname, machine, grid_name, session_id, supergrid/topo/vgrid paths, project, ninst, atm/rof grid names, ntasks_ocn, job_* | `_crocodash_state.json` | `case_state.read` / `ReadCrocoDashCase.state` (base.py:113-116) | ms |
| esmf_mesh_path (runoff, required) | not stored | derive `<supergrid dir>/ESMF_mesh_{grid}_{session}.nc`, or read OCN_DOMAIN_MESH | ms |
| forcing config, `fcr`, date_range, boundaries, product, `_configure_forcings_called` | `extract_forcings/config.json` | `ReadCrocoDashCase.forcing_config` / `.configurators()` (base.py:119-147) | ms |
| ocn_grid / ocn_topo / ocn_vgrid | state paths | the APIs in §4 (load lazily) | O(nx·ny) |
| `_cime_case` (StreamYears, `expt` RUNDIR, PR #309's BATCH_SYSTEM) | env_*.xml | CIME `Case(read_only=True, non_local=True)` | CIME import plus XML parse (unmeasured) |
| is_non_local | env MACH vs the current host | CIME `Machines().probe_machine_name()` plus the casper patch, or always True | cheap |
| rof grid / mesh (runoff) | env ROF_GRID / ROF_DOMAIN_MESH, or `config.json` runoff inputs | `_cime_case.get_value` | cheap |
| `cime` (only feeds `case_cime`) | CESM XML catalog | full `initialize_visualCaseGen` | expensive |
| cvars CASEROOT / NINST / MACHINE / MB_ATTEMPT_ID | — | `initialize` then direct assignment (unverified) | expensive, and process-global |

## 6. Blockers and risks

1. **Global `cvars`.** Binding a read-back case through `cvars` keeps the "last case created wins" behavior. Example: `a = from_caseroot(A); Case(B…); a.configure_forcings()` either raises or writes into B. Several read-back cases in one process are only safe if writes take the caseroot explicitly.
2. **CIME is process-global too.**
   - `CIME_interface` (cime_interface.py:54) and `_get_case_obj` (shareable.py:748) both *append* to `sys.path`, so whichever CIME is imported first wins.
   - CIME's `config` singleton and `sys.modules["CIME.customize"]` are loaded from the first case's SRCROOT (CIME/config.py:79-102).
   - Two cesmroots in one process would therefore silently share one CIME.
3. **Casper vs Derecho.** A case with MACH=derecho opened on Casper with `non_local=False` raises "Current machine casper does not match case machine derecho" (CIME/case/case.py:199-205).
   - visualCaseGen detects Casper by hostname (cime_interface.py:717-720). A read path that uses CIME alone has to copy that patch, or always use `--non-local` as shareable does (shareable.py:98, 751).
   - Minor side effect: with non_local, CIME skips the case-git interface, so CaseStatus updates aren't committed to the case repo (CIME/case/case.py:206-209; xmlchange:357-365).
4. **cesmroot moved or deleted — this has already happened.** For `/glade/u/home/manishrv/croc_cases/streamyr_v15`:
   - its state cesmroot and env SRCROOT/CIMEROOT point to `full_regional_cesm`, which no longer exists;
   - the caseroot's `xmlquery`/`xmlchange` symlinks are dangling;
   - so `_get_case_obj`, every xmlchange, and StreamYears' reading of CDEPS XML all fail.
   - A read-back needs a `cesmroot=` override and should call `<cimeroot>/CIME/Tools/xmlchange --caseroot`.
   - `initialize_visualCaseGen` also needs a git checkout of CIME 6.4.x.
5. **Inputdir layout drift.** That same case's state (schema 1.1.0) points into `ocnice/`. The split into `ocn/`, `ice/`, `wav/` landed in #266 (2026-09-17, PR #280) without a state schema bump. `ReadCrocoDashCase.ocn_dir` (base.py:118) and `expt` (case.py:792) hardcode `inputdir/"ocn"`. Read-back must use the paths recorded in the state, not rebuild them.
6. **What `override` means.**
   - Today `Case(caseroot=existing)` means either "refuse" (293-297) or, with `override=True`, "delete" (199-206). It can never mean "read".
   - `override` isn't saved, and an override-true Case wipes `extract_forcings` when configure_forcings runs (651-652). A read-back case must force `override=False`.
7. **Read-back attributes must be plain attributes.** The `case_*` inputs only come from `__dict__`. If session_id or esmf_mesh_path are implemented as properties or lazy attributes, Runoff hits the ValueError at base.py:244-249, or the BGC/chl filenames come out wrong.
8. **Merge hazard with config-schema-version.** [CSV] adds a top-level `schema_version` key, plus `CONFIG_META_KEYS` and `read_config` (forcing/base.py:28-39 in the worktree). [S]'s `ReadCrocoDashCase` uses raw `json.load` (base.py:119-124) and only skips `"caseroot"` (146), so its `configurators()` would try to deserialize `"schema_version"`. The driver has the same problem (driver.py:125-126).
9. **Open PRs that change what a read-back must provide:**
   - **#311 (cyclic-grid):** configure_forcings needs `ocn_grid` for `cyclic_x`. It also moves WW3 grid writing into WW3Configurator, rebuilt from files — that part already suits a read-back.
   - **#269 (interior-obc-new):** configure_forcings needs `ocn_topo` to detect boundaries, adds `case_supergrid_path`, and removes `expt`.
   - **#309 (job-queue-no-batch-system):** reads `_cime_case` BATCH_SYSTEM.
   - **#271 (cesm-not-ported-case)** is prior art, but its base `class-merge` is not in main. It generates `session_id` in `__init__` instead of from `cvars`, resolves `is_non_local` once, and adds a `_NoCesmCIME` stand-in for `CIME_interface` and a `_run_dir` fallback.

## 7. Candidate API shapes (OPINIONS)

**A. `Case.from_caseroot(caseroot, *, cesmroot=None)` classmethod.** Builds with `cls.__new__` (tests already do this, tests/test_case.py:95), then a shared `_bind_from_state()`. Plain `case_*` attributes are set up front; grid/topo/vgrid load lazily; nothing is ever deleted.
- *Pros:* no ambiguity with `override`; `__init__` is untouched; the result is a full Case, so configure, process, validate and `expt` all work.
- *Cons:* two construction paths can drift apart. That can be avoided if `__init__` ends by calling the same `_bind_from_state()` (create, then read back).

**B. `Case(caseroot=…)` with every other argument optional.** It reads the case when only caseroot is given and the state file exists.
- *Pros:* one entry point, matching "just give it a caseroot"; YAML and the CLI could take only a caseroot.
- *Cons:*
  - a mode switch inside a 190-line `__init__`;
  - `locals()` would capture `None`s (126-129);
  - creation mode loses Python's missing-argument TypeErrors, so they'd have to be written by hand;
  - `override=True` with an existing caseroot becomes ambiguous (delete or read?) and must be a hard error.

**C. Composition.** Grow `ReadCrocoDashCase` (already shared by the driver, CaseBundle and `_print_forcing_files`) into the "case on disk" model: state, config, lazy CIME env, and writers that take the caseroot. Case would hold one; `__init__` = create then bind, `from_caseroot` = bind only.
- *Pros:* it absorbs shareable's `_get_case_obj`, `_run_xmlquery` and `_load_state_from_crocodash`.
- *Cons:*
  - it's the largest refactor;
  - it must keep `forcing/base.py` free of import cycles (the reason #312 put the reader there);
  - `__dict__` auto-fill can't see delegated attributes, so it would need an explicit `case.forcing_inputs()` contract. That is arguably better anyway: `get_user_args` (base.py:219-222) already defines `case_*` as "not user-facing", which is the line a per-parameter fork prompt needs.

## 8. What `configure_forcings` would need to change for a read-back case

1. **The guard** (618-628): either make writes take the caseroot explicitly (removes the singleton), or re-bind CASEROOT, NINST, MACHINE and MB_ATTEMPT_ID from `self` at the start of each call (needs visualCaseGen already initialized for the same cesmroot).
2. **`session_id`:** take it from state (as #271 does), not from `cvars` (630).
3. **`grid_name`:** take it from state rather than `self.ocn_grid.name` (631), to avoid loading the grid.
4. **Non-local flag:** replace `self.cc._is_non_local()` (671-686) with `self.is_non_local`, which is already set at 227.
5. **Writes that take the caseroot:**
   - `user_nl_blocks.write(owner, model, groups, caseroot, ninst)`, with the logging call at 176 replaced;
   - `BaseConfigurator.configure`, `XMLConfigParam.apply` and atm.py:148 get the caseroot from `self.registry.case.caseroot` (the registry is injected at base.py:174-175);
   - a CrocoDash-owned `xmlchange(caseroot, var, val, non_local, cimeroot=None)`.
6. **Runoff:** replace `case_cime` plus `cvars["CUSTOM_ROF_GRID"]` (67-73) with `_cime_case` ROF_GRID / ROF_DOMAIN_MESH, or with the round-tripped config inputs.
7. **Attributes to provide as plain attributes:** `esmf_mesh_path`, `cesmroot` (overridable), `inputdir`, `compset_lname`, `_cime_case`, `is_non_local`, and `override=False`.
8. **For `process_forcings` and `validate_case` without reconfiguring:** set `extract_forcings_path`, set `_configure_forcings_called` to whether `config.json` exists (737-742), and rebuild `fcr` from `config.json`.

## 9. How much of shareable this removes (OPINION)

- **What read-back removes:**
  - CIME env reading and state reading in CaseBundle.
  - The `case_to_yaml` → `create_case_from_yaml` round trip just to change forcings on an existing case. Today that is a full re-create.
  - The `cvars`-dependent replay helpers (shareable.py:61-98), which would become methods on the case.
- **What it doesn't remove:**
  - fork and duplicate still need `create_newcase` for a new caseroot or machine;
  - `identify_non_standard_case_info` still builds a full temporary reference case (create_newcase + case.setup) just to diff against (shareable.py:252-272).
- **Something to evaluate:** CIME's `create_clone` (CIME/case/case_clone.py:14-24; it copies SourceMods and Buildconf at 159) could replace `duplicate_case`'s diff-and-replay for same-machine copies. Unverified for CrocoDash's INPUTDIR and mesh paths.