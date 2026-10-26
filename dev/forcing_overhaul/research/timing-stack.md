# Timing-awareness stack (#302 → #303 → #305 → #306 → #297): investigation report

**Where things are**
- Repo: `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash`. Paths below are relative to the repo and read from remote branches with `git show`.
- **T** = `origin/bgc-fe-interior-source`, the timing-stack tip. It contains all five PRs.
- **O** = `origin/skip-finished-forcing-steps`, the output-file stack tip.
- **W** = the uncommitted worktree `/glade/u/home/manishrv/documents/croc/regional_mom_workflows/CrocoDash-worktrees/config-schema-version`.
- Line numbers are on T unless marked otherwise.

## 0. Stack status (FACTS)

**Base and conflicts with main**
- #302 is based on an old main commit, 507f2d6b (#277).
- Main has only gained CI and docs commits since then (#308, #323, #324).
- `git merge-tree` finds no conflicts between T and the current main (510139f9).

**CI, drafts and reviews**
- CI is green on all five PRs. #306 is a draft. Its GLADE-only assertion in `test_get_cesm_single_variable_data_fosi` has never been run (the PR body says so).
- #302, #303, #305 and #306 have no human comments or inline review threads, only codecov and docs bots.
- #297 has one approval, from mnlevy1981 on 2026-10-12, on commit 0a66b7ee: "CrocoDash-generated `CR1850MARBL_JRA` case that was failing at the 2026 workshop runs successfully with this branch".
  - 0a66b7ee has all of #302–#306 as ancestors (checked with `merge-base --is-ancestor`).
  - This is the only end-to-end evidence for the stack.

**#297 is not really part of the stack**
- It was opened against main on 10-01 and re-based onto #306 on 10-09 (`base_ref_changed` in its timeline).
- Its code does not depend on #302–#306. The only overlap is one import-context line in `mom6.py`.

## 1. Per-PR map (FACTS)

### #302 Declare a TimeSampling on every dated product (metadata only)

**New API**
- `TimeSampling(frequency, cell_method="mean", anchor="center")`, a frozen dataclass validated in `__post_init__`: `raw_data_access/base.py:66-109`.
  - `max_period_days` (`:94`) measures generated stamps from 2001–2005.
  - `describe()` is at `:105`.
- `USER_SPECIFIED = "user_specified"` is a string sentinel (`:112`).
- `@accessmethod(time_sampling=...)` lets a method override its product's value (`:174-194`).
- `DatedBaseProduct.required_metadata` gains `"time_sampling"` (`:338`).
- `__init_subclass__` checks the declaration with `assert` (`:343-370`). The tests expect `AssertionError` (`tests/raw_data_access/test_base_registry.py:227-248`).

**Declarations**

| product | time_sampling |
|---|---|
| glorys (`glorys.py:43`), glofas | `D`, mean, center |
| reference_ocean | `D`, mean, start |
| cesm_pop_output (`cesm_ocean_output.py:57`) | `MS`, mean, end |
| cesm_mom_output (`:194`) | `USER_SPECIFIED` |
| era5 | `h`, point, start |
| CESM-WW3-JRA, reference_waves | `6h`, point, start |
| cice_restart, reference_ice | `None` (static) |

**config.json side effect**
- `BaseProduct.write_metadata` expands dataclasses (`base.py:309-310`).
- So `conditions.outputs.information.time_sampling` now appears in config.json (asserted at `test_base_registry.py:281`).
- `information` is part of the conditions fingerprint (`mom6.py:763-773`).

### #303 Optional `freq` on every dated access method

**New functions and decorator argument**
- `frequency_step(freq)` (`base.py:115`).
- `sample_dates(start, end, freq)` (`:122`). It falls back to `[start]` when the window holds no stamp.
- `resolve_time_sampling(product, method_name, freq)` (`:130-171`).
- `@accessmethod(freq_handling=None | "subsample" | "declare")` (`:181`, `:194`).

**Registration now requires `freq=None`**
- Every access method of every dated product must accept `freq=None`, or the class fails to register (`base.py:352-361`).
- Every method calls `resolve_time_sampling` first (e.g. `glorys.py:77`, `:135`, `:173`).

**Which methods do what with `freq`**
- `"subsample"`: GLORYS-RDA (`glorys.py:46`, `:77-78`), GLOFAS cdsapi (`glofas.py:15`, `:39-44`), reference_ocean (`reference.py:103`).
- `"declare"`: the three CESM readers (`cesm_ocean_output.py:102`, `:198`, `:315`).
- All other methods accept only their native cadence.

**Case and config.json**
- The `Case.configure_forcings` signature is unchanged. It calls `resolve_time_sampling` after merging the overrides (`case.py:601-607`).
- The user-facing knob is `function_overrides={"freq": ...}`.
- `function_args` now always includes `"freq"`, in both `inputs` and `outputs` (`test_case_integration.py:44` expects `{"freq": None}`).

**Interim behaviour (from the PR body):** until #305 lands, `freq="MS"` gives roughly weekly records, because the GET chunks are still 7 days.

### #305 Size chunks and fetch windows to the product's sampling

**New module `forcing/time_windows.py`**
- `native_sampling` (`:30-36`) re-implements the subsample rule from `resolve_time_sampling`.
- `chunk_days` (`:44-53`): GET is max(7, p), REGRID is max(30, 2p), minimum chunk is p, where p is the record spacing in days.
- `obc_window` (`:56-62`): pads the boundary window by p on each side.
- `ic_lookback_days` (`:65-68`): p−1.
- `describe` (`:71-94`) returns the `[info]`/`[warn]` lines, which `configure()` prints.

**`ConditionsConfigurator` (`mom6.py`)**
- Four new `ConfigOutputParam`s: `min_chunk_days`, `obc_start_date`, `obc_end_date`, `ic_lookback_days` (`:500-509`).
- They are computed and printed in `configure()` (`:596-616`) and added to `_PROCESS_OUTPUTS` (`:763-773`).
- They are read through fallbacks: `_obc_dates()` (`:819-826`), `min_chunk_days or 1` (`:855`, `:884`), `lookback_days or 0` (`:945`).

**Engines**
- `obc._make_date_pairs(..., min_days)` merges a short trailing chunk into the one before it (`obc.py:53-70`).
- REGRID raises a clear error on an empty chunk (`:410-416`).
- `min_chunk_days` is passed through `:512`, `:576` and `:729`.
- `ic.py` adds `lookback_days` (`:33`, `:68-70`, `:101`).

**CI change:** the smoke-test case dates moved to 2020-01-02..04 "so a Jan 2-4 run reads exactly the Jan 1-5 raw files staged from S3" (`.github/workflows/testing.yml:136-147` on `origin/time-aware-forcing-steps`).

**WW3 is unchanged.** It still takes user-set `get_step_days`/`regrid_step_days` input params (`ww3.py:468-482`).

### #306 Keep only the requested time range in CESM tseries subsets (draft)
- New `select_time_range(ds, start, end, apply_month_shift)` (`cesm_ocean_output.py:766-787`) and `_to_cftime` (`:790`).
- `subset_dataset` takes `time_range=` (`:636`, `:693-694`), passed from `read_single_variable_tseries_data` (`:451`).
- This affects both the CESM-POP and the CESM-MOM single-variable readers.

### #297 Fix BGC forcing for current MOM6 MARBL

**Namelist changes**
- `BGCConfigurator` now sets `READ_RIV_FLUXES`: True only when `registry.is_active("bgcrivernutrients")`.
- It also writes `lvariable_NtoC=.false.` to `user_nl_marbl` (`bgc.py:29-35`, `:45-56`).

**Iron forcing**
- The three iron outputs are replaced by one `MARBL_FE_INTERIOR_SOURCE_FILE` (`bgc.py:111-126`).
- The writer still uses `ctx.inputdir/"ocn"` (`:128-180`).

**Other changes**
- River nutrient times now use "days since 1900-01-01" (`bgc.py:358`).
- BGC boundary tracers are clipped at 0, keeping the -1e20 land fill (`mom6.py:41`, `:225-236`).
- rm6 is bumped to 12194c7, which is the head of CROCODILE-CESM/regional-mom6 **#76. That rm6 PR is still OPEN.**

**Known break (PR body):** a config.json from before #297 raises `KeyError` on deserialize.

## 2. Overlap with the output-file stack (#312..#317)

`git merge-tree` of O and T (base 507f2d6b) gives conflict hunks in:
- `mom6.py` (3), `obc.py` (2), `ic.py` (2), `bgc.py` (2), `tests/forcing/test_bgc.py` (1).
- `case.py` and the other shared tests merge automatically.

**FACTS**
1. **Preview deletion.** #316 deletes the ic/bc preview code paths. #305's new arguments sit inside the same conflict hunks:
   - `min_chunk_days=…` and `lookback_days=…` next to `preview=False` in `mom6.py`;
   - `min_chunk_days: int = 1` and `lookback_days: int = 0` next to `preview: bool = False` in the `obc.py` and `ic.py` signatures.

   #316's body says "Whichever merges second should keep the deletion."
2. **Chunk plan disappears from the dry run.** #316's dry run prints only declared files (`driver.py:175` on O). The get/regrid chunk-pair preview that #305 extended (`obc.py:777-786`) goes away.
3. **#297 against #310.** On O, `BGCIronForcingConfigurator.output_files` (`bgc.py:123-133`) lists the three iron params that #297 removes.
   - Its body merges without a conflict, so it would point at params that no longer exist.
   - The `is_file` removal resolves on its own.
   - The writer path conflicts: O uses `ctx.output_path`, T uses `ctx.inputdir/"ocn"`.
4. **Fingerprints line up.** On O, `ConditionsConfigurator.process_fingerprint` (`mom6.py:799`) reuses `_fingerprint`, which reads `_PROCESS_OUTPUTS` (`:725`). So #317's `process_record.json` will pick up #305's window and chunk keys, and #302's `information.time_sampling`, without extra work.
5. **Chunk file names don't clash with `output_files(ctx)`.**
   - #310 declares only the final IC/OBC files (`mom6.py:775` on O).
   - The dated raw and regridded chunk names (`obc.py:260`, `:370`) are not declared.
   - `stale_outputs` deletes the raw and regridded directories as a whole.
6. **WW3 and CICE fingerprints** add the conditions run dates (`ww3.py:585-591`, `cice.py:467-473` on O), not `obc_*`. That is consistent with WW3 not using time windows.
7. **Old config.json files fail to load.**
   - `BaseConfigurator.deserialize` raises `KeyError` for any declared output missing from the file (`base.py:685-688`).
   - So a config.json written before #305 fails to load, and the `or` fallbacks (`mom6.py:823-826`, `:855`, `:884`, `:945`) can never be reached for it.
   - No test covers that path.
   - **#305's body claim that an older config.json "falls back to the old behaviour" is false.**
   - #297 (renamed iron outputs) and #269 (new `custom_segments` output and `case_supergrid_path` input) have the same problem.
   - #316 removing `preview` is harmless, because extra keys in the file are ignored.
8. **Clash with W.** W uses `CONFIG_SCHEMA_VERSION="1.0.0"` and `read_config` (W `base.py:25-44`). Its `case.py` import block (W `case.py:11-18`) overlaps #303's import line (`case.py:14`).

**RISKS / OPINIONS**
- **R1:** Following #316's "keep the deletion" while resolving conflicts would silently drop `min_chunk_days` and `lookback_days`. That brings back the monthly empty-chunk crash #305 fixed. No integration-level test would catch it.
- **R2:** Putting #297 on top of #310 breaks bundling, `validate_case`, the dry run and the skip logic for every MARBL case, unless `output_files` is updated.
- **R3:** #305, #297 and #269 each need either a minor schema bump under W's rules (1.1) or a deserialize that tolerates missing outputs (`ConfigOutputParam` defaulting to None). #305's fallbacks already assume the second.
- **R4:** Fork lets the user change `forcings.date_range` (`shareable.py:613` on O). It then copies the bundle's outputs unconditionally (`:374`, `:559`), and the engines skip finals that already exist (`obc.py:654-660`, `mom6.py:336-342` on O).
  - The result: new data is downloaded, but the stale merged OBC and filled IC files are kept.
  - Once windows depend on date and product, that copy should only happen when the fingerprints match.
- **R5:** IC and BC share one fingerprint, so changing `end_date` re-fetches the IC. This is pre-existing. The windows now make a per-flag IC fingerprint (start date, lookback, product, args) easy.
- **R6:** Fixing a product's declared TimeSampling in code changes `information`, which marks every existing case's ic/bc as stale.

## 3. New configuration surface and round-trip (FACTS)

| item | stored in config.json at | set by | survives `case_to_yaml` (dump/duplicate/fork)? |
|---|---|---|---|
| `freq` | `conditions.inputs.function_args` and `.outputs.function_args` | `function_overrides` | **No** |
| `ww3_obc_function_overrides.freq` | WW3 inputs | user | Yes, but never checked at configure time (no `resolve_time_sampling` call in `ww3.py`) |
| `get/regrid/min_chunk_days`, `obc_start/end_date`, `ic_lookback_days` | `conditions.outputs` | derived | Recomputed every time; hand edits are lost |
| `information.time_sampling` | `conditions.outputs.information` | product class | Recomputed |

**Why `freq` is dropped**
- `generate_configure_forcing_args` emits only `date_range`, `boundaries`, `product_name` and `function_name` from the conditions block, and skips the block in its generic loop (`recipe.py:175-195`).
- No mention of `function_overrides` or `function_args` exists in `recipe.py`, `shareable.py` or `cli.py` on main, O, T or W.

**Consequences**
- Bundling builds a reference case through `create_case_from_yaml` (`shareable.py:268` on O), and duplicate does the same (`:398`).
- **cesm_mom_output cases:** configure now raises "must be given: pass function_overrides={'freq': ...}" (`base.py:148-154`), so bundle, duplicate and fork all fail.
- **GLORYS with `freq="MS"`:** the copy silently goes back to daily data, with different chunks, windows and OBC content.
- Dropping `dataset_path` and `member` overrides is an older problem. #303 turns it into a hard failure at configure time.

**What config.json can't tell you:** it stores only the merged defaults plus overrides (`case.py:590-600`, `:612-623`). You can't tell which values were user overrides.

**Obstacles to a per-input-param fork prompt**
- `InputValueParam` holds only a name and a comment (`forcing/base.py:356-366`). It has no type, required flag or choices.
- `function_args` is one opaque dict input (`mom6.py:450-453`).
- For forcings, fork asks only about `date_range` and `boundaries` (`shareable.py:613-614` on O).
- Whether `freq` is required, forbidden, limited to native-or-coarser, or free depends on the product and method. The only way to find out is to call `resolve_time_sampling`.

**Other gaps**
- The comment "Power users can override the chunk sizes in config.json" (`mom6.py:596-597`) has no input behind it.
- The user docs never mention `freq`.

## 4. Critique (OPINIONS backed by the evidence above)

**What is solid**
- It fixes real failures:
  - empty REGRID windows for monthly data (`test_time_windows.py:46-58` sweeps start dates);
  - a clear error for an empty chunk;
  - the IC lookback for monthly data;
  - the tseries reader re-reading whole decade files and producing duplicate, non-monotonic times (#306).

  The approved MARBL run is real evidence that this works.
- The product is the right place to declare sampling. When fork changes `product_name`, chunking adapts by itself. The registry enforces it, with a test that every dated product declares it (`test_base_registry.py:289-293`).
- Bad settings fail at configure time instead of deep inside `process_forcings`.
- All derived state goes into config.json and the fingerprint. No new `Case` attributes are added, which suits building a Case from an existing caseroot.

**Over-engineered or leaky**
- **Three overlapping switches:** the product's `time_sampling` (a TimeSampling, a string sentinel or None), the method-level override, and `freq_handling`.
  - The method-level override has no uses in production code.
  - `freq_handling` strings aren't validated, so a typo silently means "native only".
  - The rules are duplicated in `time_windows.native_sampling` (`:30-36`), and validation runs in three places (`case.py:603`, `mom6.py:600`, inside each access method).
- **`freq` has two meanings:** "thin the data to this cadence" for subsample methods, and "the archive's cadence is this" for declare methods. It is one untyped dict key, which makes it a poor fit for a prompt.
- **`anchor` and `cell_method` don't change any behaviour.**
  - `anchor` only appears in `describe()` text. `cell_method` only triggers one warning (`time_windows.py:88`).
  - A `USER_SPECIFIED` product silently becomes mean/center (`base.py:155`).
  - CESM-POP declares `anchor="end"`, but `subtract_month` writes start-of-month stamps. So "stamped at interval end" describes something MOM6 never sees.
- **`freq=None` boilerplate everywhere.** Static and script-only methods must accept it too, including the GLOFAS processed-data script that takes `dates="UNUSED"`. Any product defined outside the repo now fails at import until it adds `freq=None` and `time_sampling`.
- **`configure()` uses `print()`** rather than returning structured information, so the dry run and the MCP server can't use it.
- **GLOFAS subsampling can't be reached** from any configurator. No runoff, chl, tides or bgc code calls a GLOFAS access method.

**Bugs and gaps**
- **CESM-POP with `freq="D"` gives wrong dates.** #303's body suggests this for `day_1` archives.
  - `get_cesm_single_variable_data` always sets `apply_month_shift=True` (`cesm_ocean_output.py:160`).
  - `subtract_month` clamps the day to 28 (`:807`).
  - So every daily record is moved back a month, and days 29–31 land on the same date. No test covers POP with `freq`.
- **Padding fails at archive edges.**
  - The GLORYS RDA archive starts in 1993 (checked by `ls`).
  - A run starting 1993-01-01 now also requests 1992-12-31, and `glorys.py:95` raises `FileNotFoundError`. The same happens at the archive's end.
  - CESM-POP pads ±31 days beyond the tseries span, with no clear error.
- **Run length off by one.** `describe()` counts end−start+1 days (`time_windows.py:74`), while `STOP_N` is end−start (`case.py:690-691`).
- **rm6 pins.**
  - The floor-to-midnight line is still in the pinned rm6 (`regional_mom6/segment.py:939` at 12194c7).
  - The companion rm6 PR #77 ("Keep segment records at their source times") is open and not pinned.
  - #297 pins the unmerged rm6 #76.
- **The resolved sampling is never stored.** Only the declared sampling (in `information`) and the raw `freq` are kept, so anything reading config.json later has to resolve it again.

**Should TimeSampling be part of the configurable-forcing model?** My view:
- Keep the declaration internal, as product metadata.
- Turn only the part the user decides into typed configurator inputs, instead of a key inside `function_args`:
  - the source cadence, required for `USER_SPECIFIED` products and optional for the declare readers;
  - an optional thinning cadence for subsample methods.
- Benefits:
  - Typed inputs would round-trip through recipe's existing generic constructor-argument loop (`recipe.py:195-215`).
  - Fork prompts could get required/choices from `resolve_time_sampling`.
  - The double meaning of `freq` would go away.
- Keep windows and chunk sizes as derived outputs.
  - Record the resolved sampling in config.json.
  - Either add optional override inputs, as WW3 already has, or delete the "power users" comment.
- Either make `anchor` drive the timestamp correction or remove it. Driving it would replace the hard-coded month shift and fix the POP `day_1` bug.
- Either apply the windows to WW3, whose products already declare 6h/1h sampling, or stop requiring WW3 products to declare sampling.