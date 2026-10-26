# Configurator parameter model, and prompting for each forcing input

Branch shorthand: **T** = `origin/skip-finished-forcing-steps` (tip of the output-file stack), **Tm** = `origin/bgc-fe-interior-source` (tip of the timing stack), **M** = `origin/main`, **CSV** = the uncommitted config-schema-version worktree, **MCP** = `/glade/u/home/manishrv/documents/croc/dev/MCP_CrocoDash` at d097e1f, **G** = the gallery submodule at d6597af. Paths are relative to `CrocoDash/` unless they start with `tests/` or `docs/`.

## FACTS

### 1. How the model works (T)

- **Parameter classes.**
  - `Param(name, comment)` is the base (forcing/base.py:375-390).
  - `InputValueParam` and `InputFileParam` behave identically: both just hold a value (base.py:397-420).
  - Output types: `UserNLConfigParam` (445-482), `XMLConfigParam` (485-521), and `ConfigOutputParam`, which only goes into config.json (524-539).
  - No code outside `forcing/` reads `input_params` or any input `comment`, and the MCP doesn't either (grep over CrocoDash/ and MCP). Output comments are only used to group user_nl lines (base.py:672-684).
- **Two sources of truth.**
  - `input_params` drive `validate_args`, `serialize` and `deserialize` (base.py:638-649, 714-740).
  - The `__init__` signature drives which args are required, their defaults, and activation: `get_ctor_signature` (206-216), `get_user_args` (218-222), `return_missing_inputs` (224-228), `instantiate_configurator` (230-234).
  - `check_input_params_synced` only checks that input_params is a subset of the ctor args, and allows extras (619-636). That gap is how ctor-only adapter args exist: `date_range`, `case_cime`, `case_forcing_product`.
- **Activation** (`find_active_configurators`, 236-269):
  - A configurator is required if any `required_for_compsets` substring is in the compset (768-770). If one of its ctor-required args is missing, it raises (244-249).
  - Otherwise it must pass the allowed/forbidden substring tests (772-776) and have every ctor-required arg present. If not, it logs `[SKIP] … missing args` at INFO (261-264).
  - Unknown kwargs are dropped silently (233).
- **One flat namespace for all inputs.**
  - `inputs = kwargs | {date_range, boundaries, product_name, function_name, function_args}` (case.py:610-616).
  - The registry adds `case_<attr>` for every public attribute of the live Case, and these win over user kwargs (base.py:165-171).
  - It also adds an unprefixed `compset` (172).
- **function_overrides becomes function_args.**
  - Defaults come from `ProductRegistry.get_function_default_args`: every non-required access-method parameter that has a default (raw_data_access/registry.py:64-74).
  - Override keys are checked against those defaults, and Path values are converted to strings (case.py:590-608).
  - The result is stored as a conditions input and copied to an output (mom6.py:432-435, 486-489, 584). Process merges it last (mom6.py:59-64, 810, 858).
  - Tm also calls `resolve_time_sampling(…, function_args.get("freq"))` at configure time (Tm case.py:603).
- **`deserialize` is strict.** Every declared input and output must be present in config.json (base.py:714-727; same on Tm base.py:677-689).

### 2. Every configurator and its inputs (T)

Kind codes:
- **U**: user-facing.
- **S**: user-facing and shared by several configurators.
- **C**: `case_*`, filled from the live Case.
- **R**: injected by the registry.
- **D**: derived, then stored as an input.
- **X**: ctor-only, never serialized.

"Req" means the `__init__` arg has no default. No configurator `__init__` has type annotations, so the types below are inferred from the code.

| Configurator (activation; flags; outputs) | Input | Req | Default | Kind | Type / notes |
|---|---|---|---|---|---|
| **conditions** (mom6.py:405). Required if "MOM6" (416). Flags ic, bc. Outputs: 23 static user_nl_mom params (438-469); per-boundary OBC_SEGMENT_NNN{,_VELOCITY_NUDGING_TIMESCALES,_DATA} and OBC_DATA_&lt;tracer&gt; added during configure (619-690); config-only date_format, information, get_step_days=7, regrid_step_days=30, boundary_number_conversion, function_args (472-489, 578-579). Tm adds min_chunk_days, obc_start/end_date, ic_lookback_days (Tm mom6.py:500-510). | date_range | no (configure_forcings always passes it) | None | S,X | 2 Timestamps; becomes start/end as "%Y%m%d" (503-505); no InputParam |
| | start_date, end_date | no | None | D | str |
| | boundaries | yes | configure_forcings default [south,north,west,east] (case.py:486) | S | list[str]; type-checked 519-523; names hard-coded 624-633 |
| | product_name | yes | configure_forcings default "GLORYS" | U | must be a MOM6ForcingProduct (525-537) |
| | function_name | yes | configure_forcings default "get_glorys_data_script_for_cli" | U | access-method name |
| | compset | yes | – | R | compset long name |
| | function_args | no | None→{} | D | dict, resolved from configure_forcings' function_overrides |
| **tides** (tides.py). No compset rules. Active only when the three user args below are given. Flag tides. 9 user_nl_mom outputs (34-54). | tpxo_elevation_filepath, tpxo_velocity_filepath | yes | – | U (File) | paths |
| | tidal_constituents | yes | – | U | list[str] |
| | boundaries | yes | – | S | comment's example "['N','S','E','W']" is wrong (31) |
| | date_range / start_date | no | None | X / D | stored as "%Y, %m, %d" (71); comment is just "start_date" |
| **Chl** (chl.py). Forbidden with MARBL (13). Active when the file is given. Flag chl. Outputs CHL_FILE, CHL_FROM_FILE, VAR_PEN_SW, PEN_SW_NBANDS. | chl_processed_filepath | yes | – | U (File) | existence checked (65-69) |
| | case_grid_name, case_session_id | yes | – | C | str |
| | case_forcing_product / calendar | no | None (calendar falls back to product.calendar, 55-56) | X / D | Calendar dict |
| **Runoff** (runoff.py). Required and allowed for {"DROF"} (16-17). Its only required args are `case_*`, so it is always active with DROF. Flag runoff. XML outputs ROF2OCN_{LIQ,ICE}_RMAPNAME. | case_grid_name, case_session_id, case_compset_lname, case_inputdir, case_esmf_mesh_path | yes | – | C | esmf path is an InputFileParam |
| | case_cime | no | None | C,X | CIME interface object |
| | rmax, fold | no | None, then a suggested value written back with `set_input_param` (106-111) | U→D | must be given together (124-125); comments say metres (24, 61), mom6_forge says km |
| | rof_grid_name | no | None, then cvars CUSTOM_ROF_GRID (72-73) | U/D | str |
| | rof_esmf_mesh_filepath | no | None, then `case_cime.get_mesh_path` (68-71) | U/D (File) | absolute path on the original machine |
| **BGC** (bgc.py:14). Required and allowed for MARBL. No inputs. Output MAX_FIELDS; Tm adds READ_RIV_FLUXES and lvariable_NtoC (Tm bgc.py:29-56). | – | | | | |
| **BGCIC**. Required and allowed for MARBL. Flag bgcic. | marbl_ic_filepath | yes | – | U (File) | path |
| **BGCIronForcing**. Required and allowed for MARBL. Flag bgcironforcing. Three file outputs (93-109); Tm replaces them with a single MARBL_FE_INTERIOR_SOURCE_FILE (Tm bgc.py:111). | case_session_id, case_grid_name | yes | – | C | |
| **BGCRiverNutrients**. Allowed only with both MARBL and DROF (178); never required. `depends_on_outputs` runoff (177). Flag bgcrivernutrients. | global_river_nutrients_filepath | yes | – | U (File) | existence checked (223-227) |
| | case_session_id, case_grid_name | yes | – | C | |
| | case_forcing_product / calendar | no | None | X / D | same as Chl |
| **CICE**. Required and allowed for CICE (cice.py:181-182). Every arg is optional. Flag cice. 23 user_nl_cice outputs (238-262), plus 6 restore params added during configure/deserialize (438-457). | cice_product_name | no | None | U | must be a CICEForcingProduct (309-322) |
| | cice_function_name | no | None | U | not validated |
| | cice_function_args | no | None→{} | U | dict that holds paths; not validated |
| | restore_ice | no | False | U | bool; the restore_ice/product/function trio is all-or-none (293-307) |
| | case_inputdir | no | None | C | path |
| **WW3**. Required and allowed for WW3 (ww3.py:430-431). Flag ww3. XML output WW3_GRID_INP_DIR. | case_inputdir | yes | – | C | |
| | boundaries | yes | – | S | comment's example is wrong (436) |
| | ww3_obc_product_name | **no (default None), but `validate_args` requires it** (522-531) | None | U | a WW3ForcingProduct, or the string "none" |
| | ww3_obc_function_name | no | None | U | required when the product is not "none" (532-555) |
| | ww3_obc_function_overrides | no | None | U | dict, passed through unvalidated (694) |
| | get_step_days, regrid_step_days | no | None | U | int, days |
| **StreamYears** (atm.py). Required for "DATM%JRA", allowed for "DATM" (30-31). No process step. Declares config-only outputs datm/drof_streams (48-55) but also writes user_nl_{datm,drof}_streams directly (130-148). | case_cesmroot | yes | – | C | |
| | date_range / start_date, end_date | no | None | X / D | "%Y%m%d" |
| | stream_year_padding | no | 1 | U | int, years |
| | narrow_stream_files | no | True | U | bool |

### 3. What front-ends consume today

- **Case printout.** `Case.__init__` prints `get_user_args` for each required configurator (case.py:236-248). For a MOM6 compset this lists `boundaries, product_name, function_name, compset`: three of those have configure_forcings defaults and `compset` is injected. For WW3 it omits `ww3_obc_product_name`.
- **MCP `list_forcing_configs`** (MCP tools/discovery.py:21-49; also the resource at resources.py:23-28).
  - Returns compset lists, `user_args` (from `get_user_args`), `optional_args`, and process_flags.
  - `optional_args` excludes `case_*` args and a hand-maintained `_SET_BY_CONFIGURE_FORCINGS = {date_range, start_date, end_date, function_args}` (:18).
  - It returns no defaults, types or comments.
- **MCP `validate_case_config`** (tools/status.py:134-154) only wraps `recipe.validate_config_structure` (recipe.py:39-77). That covers section names, date_range shape, boundary names and the tides trio. It does no configurator- or compset-aware validation.
- **MCP `create_case`** chooses `function_name` from the machine (tools/case.py:200-208), a context-dependent default that CrocoDash itself doesn't have (case.py:488).
- **MCP `create_direct_case`** repeats configure_forcings' named args and adds a free-form `forcing_kwargs` (447), documented by a hand-written list of every configurator kwarg (490-498).
- **`crocodash template` and MCP `write_template`** delegate to crocogallery (cli.py:102-149; MCP tools/template.py:25-63). The YAML template's forcings block is static text covering only conditions, tides and `marbl_ic_filepath` (G crocodash/advanced/starter_case.yaml:67-79).
- **CLI process flags** are the only surface generated from the registry (cli.py:224-232).

### 4. Round-trip and fork

- **`generate_configure_forcing_args`** (recipe.py:169-217).
  - Conditions is special-cased: dates are rebuilt using `outputs.date_format`, boundaries come from the `boundary_number_conversion` keys, and product_name is upper-cased (175-193).
  - For every other configurator, each non-`case_` ctor arg found in the stored inputs becomes a flat kwarg. On a name collision the first one wins (201-210).
- **`function_args` is never emitted**, so function_overrides are lost on dump, bundle and fork. No test covers this (tests/test_recipe_functions.py:468-538).
  - config.json keeps only the merged dict, e.g. `{"buf": 1.0, "freq": null}` in `/glade/derecho/scratch/manishrv/croc_input/ctnp/extract_forcings/config.json`, so nothing records which keys were overrides.
  - On Tm, `cesm_mom_output` is `USER_SPECIFIED` (Tm raw_data_access/datasets/cesm_ocean_output.py:194). Its `freq` must come through function_overrides (Tm raw_data_access/base.py:130-152), so such a case cannot be recreated from its dump.
- **Derived inputs come back out as user kwargs.**
  - `start_date`/`end_date` are emitted from whichever of tides or StreamYears comes first, in different formats. They have no effect, because every ctor prefers `date_range` (mom6.py:503-505, tides.py:65-71, atm.py:66-68).
  - `calendar` is emitted as a dict and stays fixed even if product_name is changed.
  - Runoff's `rmax`, `fold`, `rof_grid_name` and `rof_esmf_mesh_filepath` are emitted, including absolute paths resolved on the original machine.
  - `remove_configs` has no production caller (recipe.py:269; only tests use it).
- **Fork.**
  - `_configure_yaml_for_forked_case_args` re-points only the grid, topo and vgrid paths (shareable.py:568-594).
  - `_guide_yaml_review` prompts for case fields plus `forcings.date_range` and `forcings.boundaries` only, and turns those two from strings into lists with `yaml.safe_load` (596-627). Everything else goes through $EDITOR (629-639).
  - `case.compset` can be changed at the prompt (609), but nothing recomputes the forcing set. Missing args then fail only after create_newcase (recipe.py:149-162 → base.py:244-249).
  - MCP `fork_case` turns prompting off by monkeypatching `_guide_yaml_review` (MCP tools/shareable.py:153).
  - The CLI `--plan` JSON only controls the copy plan (cli.py:324-328).
- **Bundle** builds its reference case through the same round-trip (shareable.py:242-272), so every loss above also shows up in the bundle's diff.

### 5. Metadata: what exists and what is missing

**Exists:**
- A name and free-text comment per param, and a File/Value marker that nothing reads.
- Required/default information, but only through the ctor and only as static defaults.
- The user/case split, but only as the `case_` name prefix.
- Compset rules (three substring lists) plus `find_required_configurators`/`find_valid_configurators` (base.py:188-204).
- Imperative `validate_args` per configurator.
- Current values: config.json inputs per configurator, and `ReadCrocoDashCase.forcing_config` (base.py:119-124).
- Product-side metadata:
  - `product_is_of_type`, `list_access_methods`, `get_function_default_args` (registry.py:26-74).
  - The `accessmethod` decorator's description, type and how_to_use (raw_data_access/base.py:64-70).
  - On Tm, `TimeSampling`, `freq_handling` and `resolve_time_sampling` (Tm raw_data_access/base.py:66-181). This is a declarative "required only if…" rule: freq is required exactly when the product is `USER_SPECIFIED`.

**Missing:**
- **Types.** The smoke test guesses them from names ("filepath", "dir", "cime", "forcing_product", "calendar") (tests/forcing/test_configurators.py:216-245).
- **Choices.**
  - Boundary names are hard-coded in two places (recipe.py:68, mom6.py:624-633).
  - Product choices could be computed from ProductRegistry but are not attached to the param.
- **Units.** Runoff's comment says metres (runoff.py:24) but the installed mom6_forge says km (visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:167-170, in /glade/work/manishrv/crocodile2026/CrocoDash; the `km` is also in docs/source/for_users/3a_configure_forcings.md:59).
- **Defaults that depend on context:** rmax/fold, calendar, runoff paths, and the MCP's machine-dependent function_name.
- **Rules that tie params together:**
  - The tides trio is only implicit in activation.
  - The CICE trio and the WW3 product/function pair live in `validate_args`.
  - Runoff's rmax/fold pair is in `validate_args`.
  - recipe.py:72-77 re-implements the tides rule by hand.
- **Kind beyond the prefix:** `compset`, `function_args`, `start_date` and `calendar` are reported as user args.
- **Shared versus per-configurator scope.**
- **A "machine-specific path" flag:**
  - `case_inputdir` is a Value param.
  - Paths nested in dicts (`cice_function_args`, `function_args.dataset_path`) are invisible.
- **A complete output schema:**
  - Dynamic OBC and restore params are added at runtime.
  - StreamYears' user_nl writes are undeclared.
  - configure_forcings itself issues CALENDAR, RUN_STARTDATE, STOP_OPTION and STOP_N xmlchanges (case.py:668-687) that no configurator owns.
- **Versioning or defaults per configurator** when deserializing.

### 6. Where "JSON-configurable by requirement" fits the existing code

- **The contract.**
  - The docs require inputs to be JSON-serializable (docs/source/for_developers/adding_forcing_configurations.md:86).
  - The `is_serializable` helper is defined but never used (base.py:33-34).
  - `make_serializable` only converts Path (729-732).
  - In practice the only enforcement is `json.dump` (case.py:655-656).
- **The ctor is the adapter** from rich values to JSON inputs:
  - `date_range` → date strings;
  - product → calendar dict;
  - `case_cime` → paths;
  - on #269, a `Segment` → a boundary key plus a `custom_segments` output.
- **config.json is already a per-configurator JSON document.** Each entry is `{name, inputs, outputs}`, and `deserialize` is `cls(**inputs)` (base.py:714-727), which bypasses the flat kwarg namespace entirely.
- **A per-compset schema could be built today from:**
  - `find_required_configurators`/`find_valid_configurators` (which blocks are required or optional);
  - the ctor signature (required args and defaults);
  - `Param.comment` (descriptions);
  - ProductRegistry types (choices for each `*_product_name`, and `function_name` choices that depend on the product);
  - `get_function_default_args` (the keys and defaults of the overrides dict);
  - Tm's `resolve_time_sampling` (whether freq is required).
- **It could not be built for:** types, units and choices of non-product params; the cross-param rules; the U/D/C/R classification.
- **Constraints on a per-param prompt:**
  - Configurators are coupled during configure: conditions reads `registry.is_active("tides")` and `is_active("bgc")` (mom6.py:659, 679), and Tm's BGC reads `is_active("bgcrivernutrients")` (Tm bgc.py:51-54). Toggling one block changes another's outputs, so the whole registry has to re-run.
  - `configure()` needs a live case: XML apply, user_nl writes, StreamYears' `_cime_case` (atm.py:158-159), Runoff's cvars (runoff.py:67-73).
  - `case_*` values come from Case attributes, including `session_id` read from cvars (case.py:630-631).
  - `esmf_mesh_path` is not in the state file (case.py:1077-1095); it has to be rebuilt from the naming at case.py:383-403.
- **An existing reverse-read hook:** `BaseConfigurator.inspect(caseroot)` reads outputs back from user_nl and xmlquery, using empty placeholders for inputs (base.py:702-712, 466-482, 512-521). Only tests use it (tests/forcing/test_configurators.py:263).

### 7. Inconsistencies in the param model

1. **"Required" is reported wrongly**: conditions' `compset` and `date_range`; WW3's product (ww3.py:495 vs 522-531); conditions' "required" args that configure_forcings already defaults.
2. **Prefixes are ad hoc.** `cice_*`, `ww3_obc_*`, `tpxo_*` and `marbl_ic_filepath` are prefixed, but runoff's `rmax`/`fold` are not, and WW3's `get_step_days`/`regrid_step_days` share names with conditions' outputs (mom6.py:476-481). Error messages make up for the flat namespace (mom6.py:536, cice.py:320-321, ww3.py:548-550).
3. **The same value goes by two names**:
   - `compset` (base.py:172) and `case_compset_lname` (runoff.py:21);
   - `boundaries` and `case_boundaries`, because the attribute is set at case.py:579, before the registry is built at 633.
4. **Product-function args follow three conventions**:
   - conditions: overrides, validated and resolved (case.py:590-608);
   - CICE: raw args (cice.py:529);
   - WW3: raw overrides (ww3.py:694).

   Real configs also store an unset value as `{}` for CICE but `null` for WW3 (so1deg_wav config.json). Opting out differs too: CICE uses None/False for its trio, WW3 uses the string "none".
5. **Chunking knobs are inconsistent.** WW3 exposes them as user inputs. Conditions keeps them as outputs that "power users" hand-edit in config.json (mom6.py:577), and those edits are lost on dump/fork. Tm derives conditions' chunking from the product's sampling, while WW3's stays manual.
6. **Validation has gaps and duplication.**
   - Chl, Runoff and BGCRiverNutrients override `validate_args` without calling super(), which skips the missing/extra-input check (chl.py:65-69, runoff.py:122-130, bgc.py:223-227).
   - date_range, boundaries and product are validated in three places (recipe.py:61-77, case.py:568-587, mom6.py:516-537).
   - The docs say `InputFileParam` validates that the file exists (adding_forcing_configurations.md:75); it does not.
7. **Runoff writes its suggested values back into its inputs** (runoff.py:106-111), so config.json "inputs" no longer mean "what the user asked for".
8. **A typo in a kwarg is silently ignored** (base.py:233).

### 8. Interactions with open PRs and CSV

- **Timing stack (Tm).**
  - Tm adds outputs to conditions (Tm mom6.py:500-510) and to BGC, and renames BGCIronForcing's (Tm bgc.py:29-34, 111).
  - Because `deserialize` is strict (Tm base.py:677-689), a config.json written before Tm makes `crocodash process` raise KeyError. That makes `_obc_dates`' fallback for "a config.json written before it was recorded" unreachable (Tm mom6.py:819-827).
  - Tm's bgc.py:77 and 114 pass `is_file=True`, a keyword that T removes (T base.py:423-458; it still exists on M).
- **#269** adds a `case_supergrid_path` input and a `custom_segments` output, and lets `boundaries` contain `Segment` objects (gh pr diff 269). recipe.py is unchanged: it emits only boundary keys (188-190) and rejects non-cardinal names (67-71), so interior segments cannot survive dump/fork.
- **#311** adds inputs: `case_cyclic_x` on CICE, and `case_grid_name`/`case_session_id` on WW3. Like #269, these make an older config.json fail to deserialize.
- **#271** is based on class-merge. It adds `do_exec`/`has_cesm` against the old per-param `apply()` path, which no longer matches T's `configure()` (T base.py:664-687).
- **CSV.**
  - It has one global `CONFIG_SCHEMA_VERSION` plus `CONFIG_META_KEYS` (CSV base.py:16-45). The per-configurator param additions above are exactly the changes that version would have to gate.
  - CSV reads config.json inside `CaseBundle` (CSV shareable.py:168-176), but T moved that read into `ReadCrocoDashCase` (T base.py:113-124).

## OPINIONS / RISKS

- **The root cause is using the ctor as the schema.** A declarative Param carrying required, default (or default function), type, choices, units, kind, scope and group could feed every consumer from one source: activation, the Case printout, the MCP list, the recipe round-trip, fork prompts, a JSON Schema and the smoke test. It would also let `deserialize` fill missing keys from defaults, which means fewer CSV version bumps.
- **Prompt on config.json's per-configurator inputs, not the flat kwargs.** That avoids name collisions. It still needs the U/D/C/R kinds, so derived and case values get re-derived instead of being frozen (calendar, runoff paths).
- **Unify product-function args** into one overrides → resolved convention, validated against the access-method signature, and record which keys were overridden. Tm makes `freq` and `dataset_path` required for some products, so they need to be prompts in their own right.
- **Risk: prompting each configurator on its own will give wrong answers** because of the coupling during configure. Validation has to instantiate the whole registry. That is only cheap if configure (computing values) is split from apply (writing to the case).
- **Risk: any plan to shrink shareable that keeps the recipe round-trip inherits its losses**: function_overrides, custom segments, hand-edited chunk sizes.
- **Risk: the compset rules are substring matches.** Keying a schema on them is brittle (e.g. `DATM%JRA` versus JRA-RYF long names) and the rules can't express "either/or".