# Runoff mapping scaling / optimization notes

Goal: characterize and optimize the cost of generating GLOFAS-to-ocean runoff
regrid mapping files in CrocoDash, ahead of a scaling sweep across case sizes.

## Where the mapping step lives

- `CrocoDash/extract_forcings/runoff.py::generate_rof_ocn_map()` is the entry
  point, called from `extract_forcings/driver.py::run_workflow(runoff=True)`.
- It delegates to `mom6_forge.mapping.gen_rof_maps()`
  (`CrocoDash/visualCaseGen/external/mom6_forge/mom6_forge/mapping.py:837-953`).
- Pure Python - **no `ESMF_RegridWeightGen` subprocess anywhere**. Two steps:
  1. Nearest-neighbor map via `xesmf.Regridder` (`mapping.py:530-620`,
     `method="nearest_d2s"`). Cost scales with **both** the GLOFAS source mesh
     size and the ocean destination mesh size (source mesh is always fully
     loaded/indexed even though `map_overlap=True` masks non-overlapping
     cells).
  2. Gaussian/Cressman-style smoothing (`compute_smoothing_weights`,
     `mapping.py:713-786`) via `cKDTree.query_ball_tree` **on the ocean mesh
     only** - independent of GLOFAS source mesh size, driven by `rmax`/`fold`.
  3. `"nnsm"` in output filenames = **nearest-neighbor + smoothed** (the two
     steps combined).
- **Net scaling takeaway**: shrinking the ocean grid speeds up both steps;
  shrinking the GLOFAS source mesh (global -> regional) only speeds up step 1
  (source-mesh indexing/regrid), not the smoothing step.

## The regional-mesh override (undocumented but functional)

The GLOFAS source mesh path (`rof_esmf_mesh_filepath`) normally defaults to
whatever CIME's grid/domain XML registry has on file
(`visualCaseGen/cime_interface.py::get_mesh_path()`), which is what's pulling
in the huge global production mesh
(`/glade/campaign/cesm/cesmdata/inputdata/lnd/dlnd7/GLOFAS/GLOFAS.v4.dis24.ESMFmesh_20260501.nc`).
It's not exposed in `list_forcing_configs`'s reported "required args" (only
ctor params *without* a default are reported there), but
`Case.configure_forcings(**kwargs)` forwards arbitrary kwargs straight through
to the Runoff configurator's constructor. So adding an extra
`rof_esmf_mesh_filepath: <path>` key under `forcings:` in a case YAML (or
passing it directly to `configure_forcings()`) swaps in a custom mesh. No
code changes needed - see `tiny_gulf01.yaml`.

There is **no function anywhere in CrocoDash/rm6/mom6_forge that builds an
ESMF mesh from a raw lat/lon gridded file** (e.g. a raw GLOFAS discharge
netCDF) - `Topo.write_esmf_mesh()` only works from an already-built MOM6
Grid/Topo object. ajanney's `GLOFAS_CARIB12_mesh.nc` was built externally
(its `inputFile` global attr says `GLOFAS_CARIB12_SCRIP_230403.nc`, i.e. some
SCRIP-to-unstructured conversion outside this codebase - not reproduced here).

## Reference files from ajanney (carib12_vgrid_comparison)

Source: `/glade/work/ajanney/CrocoDash_Input/carib12_vgrid_comparison/ocnice/runoff_mapping/`

Copied/linked into `~/scratch/croc_input/runoff_mapping_scaling/reference_files/`
(scratch, not git - see below for why):

| File | Size | How brought in | What it is |
|---|---|---|---|
| `GLOFAS_CARIB12_mesh.nc` | 20 MB | copied | Regional (CARIB12-domain) ESMF mesh built from GLOFAS discharge grid. 319,200 elements total, only **270 active** (unmasked) - most of the mesh is land/inactive. |
| `map_glofas_to_carib_012_nnsm.nc` | 69 MB | copied | ajanney's final nnsm mapping, CARIB12 ocean grid <- this mesh. Reference output for comparison. |
| `GloFAS_2000_2020_cesm_time_bounds_from_gio.nc` | 8.7 GB | **symlinked**, not copied | Raw GLOFAS discharge timeseries (2000-2020, CESM time bounds), a subset Gio gave ajanney. Not actually needed for the mapping-generation timing itself (only the mesh is) - only needed later for real DROF runtime forcing. Symlinked to avoid burning ~9GB of scratch quota; convert to a real copy if `/glade/work/ajanney` access becomes unavailable. |

Large binaries are kept out of this git-tracked `dev/runoff_mapping_scaling/`
folder entirely - only code + YAML configs live here.

## Active GLOFAS source points (why the tiny test domain is where it is)

Of the 270 unmasked points in `GLOFAS_CARIB12_mesh.nc`, there's a dense
cluster of ~16 in the northern Gulf of Mexico (Mississippi Delta / Gulf
Coast rivers), roughly lon [-91.5, -85], lat [28.9, 30.6]. `tiny_gulf01`'s
2x2 deg domain (lon [-91, -89], lat [28.5, 30.5]) was sited there
specifically so the mapping isn't computing against an empty/trivial
region.

## Case-creation gotcha: nested caseroot paths need pre-created parents

`Case.__init__` catches any exception from `_configure_case()` and returns
silently (prints "Case Configuration Error", no raised exception) - see
`CrocoDash/case.py:163-168`. If the caseroot's *parent* directory doesn't
exist (e.g. `~/croc_cases/runoff_mapping_scaling/tiny_gulf01` when
`~/croc_cases/runoff_mapping_scaling/` itself doesn't exist yet), this fails
silently deep inside CIME config validation, and the returned `Case` object
is left half-built (missing `esmf_mesh_path`, `is_non_local`, etc.) - it then
fails later and confusingly in `configure_forcings()` with
`Required configurator Runoff missing args: ['case_is_non_local', 'case_esmf_mesh_path']`,
which looks like a Runoff-specific bug but isn't. **Always `mkdir -p` the
caseroot/inputdir parent directories before creating a case with a nested
path.**

## `crocodash create` CLI always auto-chains into `process_forcings`

`cli.py::_create()` calls `create_case_from_yaml(config, override=...)` with
`configure_only` left at its default (`False`) - unlike the CrocoDash MCP
server's `create_case` tool, which explicitly does *not* run
`process_forcings`. There's no `--configure-only` CLI flag. Use
`create_configure_only.py` in this folder (calls `create_case_from_yaml(...,
configure_only=True)` directly) when you want a case created and forcings
configured without immediately kicking off the full (slow, every-component)
`process_forcings`.

## MCP `process_forcings` tool bug (found + fixed here, needs server restart)

`dev/MCP_CrocoDash/tools/case.py` (foreground path) and
`dev/MCP_CrocoDash/tools/_bg_worker.py` (background/PBS path) both pass
`cice=...`/`ww3=...` kwargs to `CrocoDash.extract_forcings.driver.run_workflow()`,
which has never had those parameters (only `ic, bc, bgcic, bgcironforcing,
tides, chl_, runoff, bgcrivernutrients`). This means **every** call to the
MCP `process_forcings` tool currently throws
`run_workflow() got an unexpected keyword argument 'cice'`, regardless of
compset. Fixed in both files (kwargs removed) but the fix needs the MCP
server process restarted to take effect - haven't restarted it yet, so for
now use `time_runoff_step.py` (calls `run_workflow()` directly) instead.

## First scaling data point

Case: `tiny_gulf01` - 2x2 deg, 1/12 deg resolution (24x24 = 576 ocean cells),
flat 2000m bathymetry, `1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_DROF%GLOFAS_SGLC_SWAV`,
`rof_esmf_mesh_filepath` overridden to ajanney's regional CARIB12 mesh
(319,200 source elements, 270 active).

```
Source:        nlat=420, nlon=760  (319,200 points)  [6.39 MB]
Destination:   nlat=24, nlon=24  (576 points)  [0.01 MB]
Nearest-neighbor map:  13.3 s
Smoothing (rmax=50km, fold=100km):  8.5 s
Total runoff step:  21.8 s
```

Well under the 10 min target. Ready to scale up ocean-grid size (and later,
compare regional vs global source mesh) from here.

## Scaling improvement effort: branch `runoff-mapping-scaling` (mom6_forge)

Starting a slow, iterative effort to actually speed up `gen_rof_maps()`, on a new
`runoff-mapping-scaling` branch in `regional_mom_workflows/mom6_forge` (off
`origin/main`, deliberately generic name since more than one change is planned).
Process: one small isolated change at a time, re-measured the same way after each
change, explained here before moving to the next.

### Step 1 — baseline (before any code change)

New harness: `time_gen_rof_maps_direct.py` in this folder. Unlike
`time_runoff_step.py` (which goes through `CrocoDash.extract_forcings.driver.run_workflow`),
this calls `mom6_forge.mapping.gen_rof_maps()` directly with the same two mesh
files as the original data point above (ajanney's `GLOFAS_CARIB12_mesh.nc` as ROF
mesh, tiny_gulf01's ocean ESMF mesh as destination, `rmax=50`, `fold=100`) — this
isolates `gen_rof_maps()` itself from any CrocoDash/DROF pipeline overhead, so
later changes are measured against a cleaner number.

Ran twice on unmodified `origin/main` mom6_forge code (commit `14e0656`) to check
for run-to-run noise on the login node, timing with plain wall-clock only:

```
Run 1: NN map 18.47 s, smoothing 9.66 s,  total (wall) 28.14 s
Run 2: NN map 18.63 s, smoothing 10.79 s, total (wall) 29.42 s
```

That ~1.3 s gap between the two runs is small, but wall-clock alone can't say
*why* it moved — Derecho login nodes are shared, so wall time also reflects
whatever CPU contention happened to exist at that moment, not just the actual
regridding work. Checked this directly with `/usr/bin/time -v` around the whole
`conda run` invocation: only **32% CPU utilization** (21.6 s of CPU time across
66.4 s of wall time) — most of that gap is `conda run`/Python-import startup
overhead outside `gen_rof_maps()` itself, which is constant cost unrelated to any
future code change and shouldn't be compared run-to-run.

So the harness now also tracks CPU time (`time.process_time()`) around just the
`gen_rof_maps()` call itself, not the whole program. Re-run twice with that
instrumentation:

```
Run 3: wall 25.56 s, CPU 18.53 s, utilization 72%
Run 4: wall 27.10 s, CPU 19.27 s, utilization 71%
```

CPU time is far tighter across runs (18.53 s vs 19.27 s, ~4% apart) than wall time
was, and utilization is stable at ~71-72% — i.e. even isolated to just this one
call, roughly a third of wall-clock is non-CPU wait (I/O reading the mesh
files/writing the mapping netCDFs, most likely), which is exactly the kind of
noise that would otherwise be misread as a code-driven speedup or regression.

**Reference baseline for every subsequent change in this effort: CPU time
~18.5-19.3 s** (wall ~25.5-27 s, ~72% utilization), not the ~21.8 s figure in the
"First scaling data point" section above, which was wall-clock only, measured
through the full `time_runoff_step.py`/CrocoDash path, at an earlier point in
mom6_forge's history.

Separately: today's direct-call wall time (~28-29 s from Runs 1-2) is *higher*
than that older ~21.8 s full-pipeline figure, even though it should have *less*
overhead. Likely explanation: mom6_forge's `main` moved forward (PR #92, "ESMF to
& from grid options", merged after the original data point was recorded) and
changed `write_mapping_file()` to reconstruct a full `Topo` via
`Topo.from_esmf_mesh()` (`SupergridBase.reconstruct_from_esmf_mesh`) for both the
source and destination mesh, instead of the older, lighter `grid_from_esmf_mesh()`
— the `"The manual mask is not initialized..."` messages in the run output are
that new reconstruction path talking. That reconstruction step scales with the
*full* source mesh size (319,200 elements) even though only 270 are ever active —
this is exactly the cost the mesh-cropping change (next step) targets.

### Step 1b — tried the true global GLOFAS mesh instead of Aidan's regional one

Added a `--mesh {regional,global}` flag to `time_gen_rof_maps_direct.py`. The
global mesh is CIME's registered production ROF mesh:
`/glade/campaign/cesm/cesmdata/inputdata/lnd/dlnd7/GLOFAS/GLOFAS.v4.dis24.ESMFmesh_20260501.nc`
(1.3 GB, symlinked from a GDEX collection path) — **21,600,000 elements, all
flagged active** in `elementMask` (unlike Aidan's regional mesh, this one has no
land/ocean masking baked in at all, so `map_overlap`'s zeroing step has real work
to do). ~68x more elements than the regional mesh.

**It doesn't complete.** `gen_rof_maps(rof_mesh_path=<global mesh>, ...)` was
killed (exit 137) both as a background job and in the foreground. Bisected with
`/usr/bin/time -v` on progressively smaller pieces of the call:
- Just opening the mesh with `xr.open_dataset()` (lazy): fine, 166 MB peak RSS,
  ~35 s wall (mostly the network-filesystem stat/open).
- `Topo.from_esmf_mesh(<global mesh path>)` alone — the full-mesh reconstruction
  that `write_mapping_file()` now does for the source mesh on every call
  (`SupergridBase.reconstruct_from_esmf_mesh`, see PR #92 note above) — **OOM
  killed after 4:04 wall / ~29.1 GB peak RSS**, without ever returning. This
  reconstruction was killed *before* `gen_rof_maps()` even reaches the regridder
  or smoothing code - i.e. today's code cannot process the true global mesh in
  this dev environment at all, not just slowly.

This is stronger motivation for the cropping change than a timing number: it's
not "the global mesh is slow," it's "the global mesh cannot be processed here at
all" with the current full-reconstruction-regardless-of-masking approach. After
Step 2 (crop before any `Topo.from_esmf_mesh` call touches the full mesh), the
expectation is that the global-mesh case becomes completable at all, since
reconstruction would then only touch the small cropped region - so Step 2's
global-mesh comparison will likely be "OOM/DNF" vs. "completes in ~N seconds,"
not a percentage change. The regional-mesh CPU-time numbers above (~18.5-19.3 s)
remain the baseline for the *speed* comparison, since that's the only one of the
two that currently finishes.

### Why crop and not just mask

`generate_ESMF_map_via_xesmf()`'s `map_overlap` (`mapping.py:564-594`) already
masks: it zeroes `elementMask` for source points outside the destination bbox,
and that's exactly what `xe.Regridder`/ESMF use to exclude cells from the actual
interpolation - so masking-for-regridding is already in place, not a new idea.
But masking a cell doesn't shrink the array holding it, and the OOM above happens
in `Topo.from_esmf_mesh()` -> `reconstruct_from_esmf_mesh()`, which reshapes
`nodeCoords`/`centerCoords` into the mesh's full `(ny, nx)` shape and computes
`dx`/`dy`/`area`/`angle_dx` over that full shape *without ever consulting
`elementMask`* - masked or not, every element's geometry gets reconstructed. A
masked-but-uncropped global mesh would hit the same wall. Cropping (physically
reducing `ny`/`nx` before reconstruction runs) is the only lever that reduces the
array size; the existing masking still does its normal job on the smaller array
afterward.

### Step 1c — profiled the regional-mesh case with scalene

Installed `scalene` (`pip install scalene`) into the `mom6_forge` conda env and
ran it on the completing regional-mesh case:
`python -m scalene run -o out.json time_gen_rof_maps_direct.py --- --mesh regional --clean`.

**Memory profiling worked and is informative.** Peak footprint for this small
case: ~2.4 GB, concentrated almost entirely in two places, both inside the
full-mesh reconstruction path (`Topo.from_esmf_mesh` -> `reconstruct_from_esmf_mesh`,
run for *both* the source and destination mesh regardless of masking):
- `_supergrid.py:864-881` -
  `calc_supergrid_rotation_angles_using_expanded_supergrid_method` (`vecdot`,
  `np.cross`) - the single biggest line, ~2.4 GB peak by itself, computing
  `angle_dx` from several full-supergrid-shaped 3-vector temporary arrays.
- `grid.py:763-835` - `_compute_MOM6_grid_metrics` assembling `dx`/`dy`/`area`
  from the supergrid.

This corroborates the manual OOM finding above with much more precision: it's
not "the mesh in general," it's specifically this reconstruction path, and
specifically the rotation-angle computation is the worst offender. One
consequence worth flagging: naively scaling this case's 2.4 GB peak by the
global mesh's ~68x element-count ratio would suggest ~163 GB - much more than
the ~29 GB the global-mesh run actually reached before being killed. That means
the global-mesh reconstruction likely died at an earlier, cheaper stage (basic
coordinate reshaping) *before* it even reached the expensive rotation-angle
step - so 29 GB is a lower bound on what full reconstruction would need, not the
real number.

**CPU-time profiling did not work in this environment.** Every single line
across all files reported 0% CPU time - including lines like `xe.Regridder(...)`
that clearly take multiple seconds. That's not a real "nothing costs CPU"
finding; it's scalene's signal-based CPU sampler failing silently on this
HPC/sandboxed setup. Tried running with the conda env activated directly instead
of via `conda run` in case that wrapper was the cause - hit an unrelated
pre-existing issue instead (`ESMFMKFILE` isn't set correctly outside `conda
run`'s activation hooks, so `esmpy` import fails) - not pursued further. For
time hotspots, keep relying on the manual wall/CPU timing already in
`time_gen_rof_maps_direct.py` rather than scalene's CPU numbers here.

### Step 2 — stop reconstructing full mesh geometry just to read a shape

Checked exactly what `write_mapping_file()` (`mapping.py`) used `src_topo`/
`dst_topo` for, after building them via `Topo.from_esmf_mesh()`. Answer:
**only `.tmask.shape`** - i.e. `(ny, nx)` - nowhere else in the function; every
other field (`xc_a`, `yc_a`, `mask_a`, vertex coords, ...) is read straight from
the raw mesh Dataset. So the entire `Topo.from_esmf_mesh()` call - including the
`_supergrid.py` rotation-angle computation identified above as the #1 memory
cost, plus a second, redundant grid-metric recomputation inside
`Grid.from_supergrid_ds()` (`grid.py:763-835`, the #2 memory cost), plus `Topo`/
version-control construction overhead - was being paid just to read a shape
tuple.

Considered two fixes: call `mom6_forge._supergrid.SupergridBase.reconstruct_from_esmf_mesh()`
directly (skips the `Topo`/redundant-metric overhead, but still pays the #1
rotation-angle cost, since that function computes it unconditionally), or use
`get_mesh_dimensions()` (`utils.py`, already imported in `mapping.py`) - which
gets `(nx, ny)` straight from `elementConn` pattern-matching, no geometry
reconstruction at all. Went with `get_mesh_dimensions()`, since it eliminates
both memory hotspots, not just the smaller one.

Change: replaced the `Topo.from_esmf_mesh(src_mesh)`/`Topo.from_esmf_mesh(dst_mesh)`
calls and every downstream `.tmask.shape` reference with
`get_mesh_dimensions(src_mesh)`/`get_mesh_dimensions(dst_mesh)` (`mapping.py`,
`write_mapping_file()`).

**Verified numerically identical**: saved the pre-fix `_nn.nc`/`_nnsm.nc` output
(from the Step 1c scalene run) aside, re-ran with the fix, and diffed every data
variable in both files with `np.allclose` (`rtol=atol=1e-12`) - byte-for-byte
identical in both files. This change only removes wasted computation; it
doesn't touch any value that ends up in the output.

**Re-measured on the regional mesh** (2 runs):

```
Run A: NN map 9.38 s,  smoothing 7.15 s, wall 16.53 s, CPU 13.60 s, util 82%
Run B: NN map 7.43 s,  smoothing 7.43 s, wall 14.86 s, CPU 13.18 s, util 89%
```

vs. the Step 1 baseline (CPU 18.53-19.27 s): **CPU time down ~30%** (13.2-13.6 s),
and NN-map wall time roughly halved. Bigger than expected for what looked like
"just a metadata lookup" - a good reminder that the profiled hotspot really was
being paid twice (once for src, once again for dst) on every single
`write_mapping_file()` call, and `gen_rof_maps()` calls it twice (once for the
`_nn.nc` map, once again for the `_nnsm.nc` map).

**Global-mesh retry — this alone was enough to make it completable.** Previously
(Step 1b) the global mesh OOM'd at ~29 GB after 4:04, dying inside
`Topo.from_esmf_mesh()` before `gen_rof_maps()` ever reached the regridder. With
just this shape-lookup fix (no cropping yet), it now **completes**:

```
NN map: 1037.1 s   smoothing: 1087.7 s
wall: 2124.8 s (35.4 min)   CPU: 825.4 s (13.8 min)   utilization: 39%
peak RSS: 12.98 GB   (vs. OOM at ~29 GB before)
```

Not fast - 35 minutes and a peak of ~13 GB is far outside the "well under 10
min" target for a real scaling sweep - but it is a completely different
category of problem than "cannot run at all." The `_construct_vertex_coords()`
loop (`mapping.py:160-194`, still a pure Python `for` loop over every one of the
21.6M elements) and the still-uncropped `xe.Regridder()` call over the full
21.6M-point source grid are the likely remaining costs, both scaling with the
*full* source mesh regardless of masking - exactly what mesh-cropping (next)
targets.

### Step 3 — vectorize `_construct_vertex_coords()` (numpy, not numba)

Before doing any more fixes, checked whether the remaining Python `for` loop in
`_construct_vertex_coords()` (`mapping.py:160-194`, iterates every element to
build the 4-vertex `xv`/`yv` arrays used for `area_a`/`area_b`) could be sped up
with numba/JIT as asked. Looked at what the loop actually does per element:
gather 4 node coordinates by index, and if the 4th connectivity slot is `NaN`
(a triangular element), duplicate vertex 2 into slot 3 instead. That's a static
gather-with-a-conditional-duplicate - no per-element branching complexity or
sequential dependency between elements - which numpy's fancy indexing already
executes at C speed. Numba would add a real dependency (LLVM backend, JIT
warm-up cost on every fresh process, version-compatibility surface across every
conda env in this repo) for no additional speed over plain vectorization, so
vectorized instead of reaching for numba.

Replacement: build the whole `(n_elem, 4)` gather in one shot via
`node_coords[conn_safe, :]` (NaNs replaced with a placeholder index of 0), then
overwrite the placeholder column for triangular rows only, via a boolean mask -
`mapping.py:176-194`.

**Verified correctness two ways** before touching the real file:
1. Isolated the loop vs. vectorized implementations and ran both directly
   against ajanney's real regional mesh (`GLOFAS_CARIB12_mesh.nc`, all-quad,
   no triangles present) - bit-identical output, loop 1.068 s vs. vectorized
   0.011 s (~93x on this piece alone at 319,200 elements).
2. Built a small synthetic mesh mixing quads and triangles (to exercise the
   NaN-4th-slot branch the real mesh never hits) - bit-identical output there
   too.
3. Ran the full `gen_rof_maps()` regional case again and diffed both output
   files against the very first pre-Step-2 baseline (`mapping_before_fix/`) -
   still byte-for-byte identical, confirming Step 2 + Step 3 together haven't
   changed the result.

**Regional-mesh timing**: wall 18.75 s, CPU 12.07 s, util 64% - a modest further
drop from Step 2's ~13.2-13.6 s CPU (expected: 319,200 elements isn't where this
loop hurts most). The real test is the global mesh (21.6M elements, where Step 2
alone took 13.8 min CPU) - retest queued, to be recorded once it finishes.

**Revisited and reverted after Step 4.** Once the global-mesh retest came back
(32.8 min / 13.0 GB - barely different from Step 2's 35.4 min / 13.0 GB alone,
see the results table below), and once Step 4's crop was in place, it became
clear this change wasn't earning its complexity: `crop_source_mesh=True` is the
default, so `_construct_vertex_coords()` only ever runs on the *cropped* mesh
(a few thousand elements) in normal use - a plain Python loop is fine at that
size, vectorized or not. The vectorized version only would have mattered for
the `crop_source_mesh=False` debugging path against a huge mesh, which isn't a
real use case. Reverted `_construct_vertex_coords()` back to the original loop
- one less nontrivial piece of code (NaN-placeholder gather-and-overwrite) to
maintain for a win that cropping already makes moot. Re-ran the Step 2+4
(no Step 3) regional case afterward and confirmed it's still byte-identical to
the original `mapping_before_fix/` baseline.

### Step 4 — crop the ROF source mesh to the ocean domain's bbox

Implemented the mesh-cropping step from the original plan, but **not** using
`Topo.from_esmf_mesh()`/`Grid.__getitem__` as originally designed - we now know
that reconstruction is itself what OOM'd the global mesh (Step 1b), so using it
inside the crop step would just move the OOM into cropping instead of fixing it.
Instead, `crop_esmf_mesh_to_bbox()` (`mapping.py`) works directly on the ESMF
mesh's own fields - `centerCoords`/`elementMask`/`nodeCoords` reshaped to
`(ny, nx)` and sliced to an index window (`get_mesh_dimensions()`, no geometry
reconstruction at all) - and rebuilds `elementConn` fresh for the cropped
rectangle via vectorized quad connectivity, since a rectangular grid's
connectivity is fully determined by its shape and doesn't need to be remapped
from the original. Also extracted `_get_mesh_bbox()` out of
`generate_ESMF_map_via_xesmf()`'s inline bbox logic so cropping and the existing
`map_overlap` masking share one implementation. Wired into `gen_rof_maps()`: the
ROF mesh is cropped to the ocean mesh's bbox (+ buffer) before anything else
runs, with a new `crop_source_mesh=True` / `crop_buffer_deg=0.5` kwarg pair to
keep the uncropped path reachable.

**Found and fixed a real (pre-existing) bug while testing**: `_get_mesh_bbox()`
was applying `normalize_deg()` (mod-360 wrap) to *latitude*, not just longitude
- inherited verbatim from the original inline code. Latitude has no 0/360
ambiguity; wrapping it corrupts any negative latitude (e.g. `-6.95` ->
`353.05`), and ajanney's regional mesh's real latitude range (`-6.95` to
`34.95`) hit exactly that. This didn't break the *existing* `map_overlap`
masking for tiny_gulf01 (its own bbox is `28.5`-`30.5`, both positive, so the
bug was latent there) but would have silently mis-masked (or, per this crop's
assertion, crashed) for any destination domain straddling the equator. Fixed by
leaving latitude unwrapped in both `_get_mesh_bbox()` and
`crop_esmf_mesh_to_bbox()`; re-ran the full Step 2 + Step 3 regression
(byte-identical vs. the original baseline) again afterward to confirm this
didn't change anything for the existing test case.

**Verified correctness properly** - cropping changes `n_a`/array sizes on
purpose, so a byte-diff doesn't apply here. Instead compared the *physical*
mapping: for every nonzero entry, resolved `(dst_lon, dst_lat) -> (src_lon,
src_lat)` via each file's own `xc_a`/`yc_a`/`xc_b`/`yc_b`, and compared those
physical-coordinate mappings (not raw indices) between cropped and uncropped
runs. Identical sets of mapped coordinate pairs, identical weights (max diff
0.0), for both `_nn.nc` (6 entries) and `_nnsm.nc` (595 entries).

**Regional-mesh timing (900-element cropped mesh vs. 319,200 uncropped)**:

```
NN map: 0.85 s   smoothing: 0.07 s   total: 0.92 s
```

vs. Step 3's 12.07 s CPU / 18.75 s wall uncropped - over an order of magnitude
faster even on the *regional* mesh, which was never the main target.

**Global-mesh result - the real target:**

```
NN map: 3.58 s   smoothing: 0.12 s
wall (whole command): 7.28 s   CPU: 3.59 s   peak RSS: 1.45 GB
```

Cropped down to 3,600 elements (60x60) regardless of starting from 21.6M - the
crop makes the global mesh's size irrelevant, exactly as expected. Compare the
full arc for the global mesh across every step so far:

| | wall | peak RSS |
|---|---|---|
| Step 1 (`main`, no fixes) | OOM, never completes | ~29 GB (killed) |
| Step 2 (shape-lookup fix) | 35.4 min | 13.0 GB |
| Step 2+3 (+ vectorized vertex coords) | 32.8 min | 13.0 GB |
| Step 2+3+4 (+ crop) | **7.3 s** | **1.45 GB** |

From "cannot run at all" to 7 seconds. Note Step 2+3 barely moved the needle
past Step 2 alone (35.4 -> 32.8 min, 13.0 GB either way) - confirms what Step
3's own reasoning predicted: vectorizing `_construct_vertex_coords()` helps
per-element gather cost, but at 21.6M elements it was never the dominant term
next to the regridder call and the `_nn.nc`/`_nnsm.nc` file writes; cropping
first is what actually changes the asymptotics, by removing the full source
mesh from every downstream step entirely.

**One genuine (non-crop) finding surfaced by this run**: the global mesh's
cropped output has **all 3,600 elements active** (`mask_a` all nonzero),
whereas the equivalent regional-mesh crop has only 9 of 900 active. This isn't
a cropping bug - `crop_esmf_mesh_to_bbox()` preserves whatever `elementMask`
values the source file already has, and separately verified (above) that
cropping doesn't change *which* points are active for the same mesh. It means
the global production GLOFAS mesh doesn't carry real land/ocean or
river-location masking the way ajanney's curated regional mesh does - every
grid cell reads as an active runoff source. Fine for measuring crop
performance, but **whoever eventually uses the global mesh directly for a real
case needs to sort out masking separately** - this crop step doesn't (and
can't) fix that, it only reduces array size.

### Step 5 — tests, final before/after verification, black, and PR

Added permanent pytest coverage for every change made in this effort, in
`mom6_forge/tests/test_mapping.py` (all against small synthetic ESMF meshes
built via `Grid(...).supergrid.to_esmf_mesh(...)`, not the large real files,
so the suite stays fast):

- `test_get_mesh_bbox_preserves_negative_latitude` - regression guard for the
  latitude-`normalize_deg` bug fixed in Step 4; fails loudly if it's ever
  reintroduced.
- `test_crop_esmf_mesh_to_bbox_shrinks_to_expected_window` - crops a known
  10x10 mesh and checks the result lands on the exact expected 5x5 window.
- `test_crop_esmf_mesh_to_bbox_rejects_nonmonotonic_mesh` - the
  non-cyclic/non-tripolar guard rejects a deliberately-broken mesh.
- `test_write_mapping_file_uses_shape_lookup_not_full_reconstruction` -
  monkeypatches `Topo.from_esmf_mesh` to raise, then calls `write_mapping_file`
  and asserts it doesn't raise - proves Step 2's fix isn't just "gives the
  right shape" but "never touches `Topo` at all" going forward.
- `test_gen_rof_maps_crop_matches_uncropped_physical_mapping` - a permanent,
  end-to-end version of the crop-vs-uncrop physical-mapping-equivalence check
  from Step 4, run automatically on every future change to this file. Uses a
  destination domain shifted to all-positive latitude specifically to avoid
  the *separate, still-unfixed* `normalize_deg(src_lat)` bug in
  `generate_ESMF_map_via_xesmf`'s `map_overlap` masking (see caveat below) -
  that bug is real but out of scope for this branch, and shouldn't make this
  crop-correctness test flaky depending on which latitudes it happens to pick.

(No test for `_construct_vertex_coords()` - see the Step 3 revert note above;
it's back to the original, already-untested loop.)

All 5 new tests pass, plus all 7 pre-existing tests in `test_mapping.py`
(201 of 202 tests pass across the full `mom6_forge` suite; the one failure,
`test_grid.py::test_is_tripolar`, was confirmed to fail identically on
unmodified `main` - pre-existing, unrelated to this branch).

**Final consolidated before/after verification** (beyond the per-step checks
already recorded above), run once more end-to-end on the real regional mesh
right before opening the PR, using `time_gen_rof_maps_direct.py`'s new
`--no-crop` flag:

1. Branch code with `crop_source_mesh=False` (isolates Step 2's shape-lookup
   change only, now that Step 3 is reverted) vs. the saved `mapping_before_fix/`
   output from unmodified `main` - **byte-identical across all 19 variables in
   both `_nn.nc` and `_nnsm.nc`** (`np.allclose`, `rtol=atol=1e-12`). Re-checked
   again after reverting Step 3, still identical.
2. Branch code with `crop_source_mesh=True` (the default, full fix) vs.
   `crop_source_mesh=False` - compared by physical `(dst_lon, dst_lat) ->
   (src_lon, src_lat)` mapping rather than raw index, since cropping
   intentionally changes `n_a` (319,200 -> 900). **Identical key sets, 0.0 max
   weight difference**, for both the 6-entry `_nn.nc` and 595-entry
   `_nnsm.nc` mappings.

So: turning off cropping reproduces `main`'s output exactly; turning cropping
on reproduces the same physical mapping in a fraction of the time. Together
with the earlier per-step checks, every change in this branch has now been
verified correctness-preserving at least twice, through two different methods
(byte-diff and physical-mapping equivalence).

Ran `black mom6_forge/ tests/` before committing - reformatted only
`mapping.py` and `test_mapping.py` (the two files touched), no other files
affected.

**Known remaining issue, explicitly out of scope for this branch**: the
`normalize_deg(src_lat)` call inside `generate_ESMF_map_via_xesmf`'s
`map_overlap` masking (not touched by this branch - only `_get_mesh_bbox`'s
and `crop_esmf_mesh_to_bbox`'s own internal latitude handling were fixed) can
still wrap negative latitudes and silently mis-mask a destination domain that
straddles the equator. Flagging here so it isn't lost; a follow-up fix should
remove that `normalize_deg` call from the latitude line the same way it was
removed from `_get_mesh_bbox`, then re-verify against a real cross-equator
case.

### Step 6 — dropped the vectorization, simplified the tests

After Step 5, reconsidered whether Step 3 (vectorizing
`_construct_vertex_coords()`) was worth keeping at all, given how little it
moved the global-mesh number (35.4 -> 32.8 min) and how much NaN-placeholder
gather/overwrite logic it added. Decided no - see the "revisited and reverted"
note under Step 3 above. Net effect on the branch: two changes instead of
three (shape lookup + crop), less code, same end-state performance (crop was
already doing the real work).

Simplified `test_mapping.py` to match:
- Dropped the two vectorization-specific tests entirely (nothing left to test
  once the loop reverted).
- Dropped the separate `crop_rof_grid_pos_lat`/`crop_ocn_grid_pos_lat`
  fixtures - the one test that needed positive latitude now builds its two
  small grids inline instead of via named fixtures shared with nothing else.
- Dropped the checkerboard mask setup in the crop-equivalence test - an
  all-active source mesh plus the existing `map_overlap` bbox masking already
  produces a small, non-degenerate set of active cells (9, from the 3x3
  lon/lat overlap window), so the extra masking step wasn't buying anything.
- Dropped the `_nnsm.nc` comparison in that same test - smoothing weights are
  computed from the ocean mesh alone, independent of the (possibly cropped)
  ROF mesh, so once the `_nn.nc` map is shown physically identical, the
  smoothed map is not meaningfully separate coverage.
- Kept every test that guards an actual bug or an actual behavioral contract:
  the negative-latitude regression, the crop window/index-math correctness,
  the non-monotonic-mesh rejection, the "no more `Topo.from_esmf_mesh`" guard,
  and - explicitly asked to keep this one - the crop-vs-uncropped physical
  mapping equivalence check. That one can't be a literal byte-for-byte diff
  (cropping changes `n_a` on purpose), but it is the closest equivalent: every
  weight is required to land on the exact same physical `(dst_lon, dst_lat) ->
  (src_lon, src_lat)` pair with the exact same value.

Net: 5 new tests instead of 8. Re-ran the full before/after verification from
Step 5 after the revert - still byte-identical with cropping off, still
physically identical with cropping on.

### Step 7 — real CrocoDash/CIME integration test, against the real global mesh

All verification up to this point called `mom6_forge.gen_rof_maps()` directly.
To check the fix actually works through the real integration point - a
`Case` built via CrocoDash, going through CIME's own `create_newcase`, with
`configure_forcings()`/`process_forcings()` exactly as a user would call
them, and critically **no `rof_esmf_mesh_filepath` override** - ran a fresh
test case (`crop_fix_global_test`, same 2x2 deg Gulf domain as `tiny_gulf01`,
`1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_DROF%GLOFAS_SGLC_SWAV`).

Two things had to line up first:
- CrocoDash's conda env imports its own nested copy of `mom6_forge`
  (`CrocoDash/CrocoDash/visualCaseGen/external/mom6_forge/`, a separate git
  checkout currently on branch `expand-and-calendar-arg` - not this repo's
  `main`/`runoff-mapping-scaling`). Confirmed it, its `utils.py` already has
  every helper (`get_mesh_dimensions`, `normalize_deg`, etc.) this branch's
  `mapping.py` needs, and diffing the two `mapping.py` files showed the only
  differences were exactly this branch's changes - so copied the branch's
  `mapping.py` over the nested copy's, temporarily and locally (never
  committed), to actually exercise the fix through CrocoDash. Reverted via
  `git checkout -- mom6_forge/mapping.py` immediately after the test - the
  submodule's own branch/history is untouched.
- Confirmed via `component_grids_nuopc.xml` that this CESM install's
  registered `GLOFAS` domain mesh is the same 21.6M-element global file used
  throughout this investigation - so *not* overriding
  `rof_esmf_mesh_filepath` is the real test of the fix, not a formality.

Ran `configure_forcings()` normally, then `process_forcings()` with only
`process_runoff=True` (everything else `False`) - isolates the code path this
branch touches from an unrelated, slow GLORYS ocean IC/BC download that has
nothing to do with this fix.

**Result: success.** `create_newcase` succeeded; `configure_forcings()` wired
`ROF2OCN_LIQ_RMAPNAME`/`ROF2OCN_ICE_RMAPNAME` in `env_run.xml` to the
not-yet-generated mapping file path; `process_forcings(process_runoff=True)`
called CrocoDash's real `Runoff` configurator, which called this branch's
`gen_rof_maps()` against the real global mesh, cropped it, and finished:

```
Cropping ROF source mesh to ocean mesh bounding box...
Source: nlat=60, nlon=60 (3,600 points) [0.07 MB]
Generated nearest mapping file in 2.50 seconds
Generated smoothed mapping file in 0.19 seconds
[timing] runoff: 2.7s  total: 2.7s
Case is ready to be built.
```

Both mapping files landed exactly where `env_run.xml` already pointed
(confirmed by re-reading the XML after the fact). This is the same behavior
verified synthetically in Step 4/6, now confirmed through the actual
production entry point with the actual production mesh, not a stand-in.

**Where this test stops - machine mismatch, not a fix problem.** Tried
`case.setup` next; failed immediately: `Current machine casper does not match
case machine derecho`. This sandbox runs on Casper (`NCAR_HOST=casper`); the
case targets Derecho's compilers/PBS queue, which this session can't reach.
Actually building and submitting the model needs to happen from a real
Derecho login node - a known, pre-existing constraint of this sandbox, not
something specific to this branch. Nothing
about this is specific to the crop fix; it's the same constraint that's
applied to every case-build/submit attempt from this environment. Forcing
generation - the part this branch actually changes - is fully verified;
build/submit verification is a follow-up for whoever has Derecho access.

### Step 8 — found and fixed a real correctness bug: cropping broke DROF domain consistency

While explaining how cropping works, got asked a sharp question: if the ROF
mesh is cropped before computing weights, how does the resulting mapping
file's weights still work against the *real* (uncropped) global mesh at
runtime? Answer: **it didn't.** Traced the actual code (not guessed) and
confirmed a real bug:

- `ROF_DOMAIN_MESH` - the CIME XML variable that tells DROF what its own
  runtime grid is - gets set once, at case-creation time
  (`CrocoDash/visualCaseGen/visualCaseGen/custom_widget_types/case_creator.py:970-971`),
  from CIME's registered GLOFAS mesh path. It is **never** re-pointed at
  anything else afterward.
- `gen_rof_maps()`'s `rof_mesh_path` (via `RunoffConfigurator`,
  `CrocoDash/forcing_configurations/configurations.py:380-384`) is looked up
  the exact same way - normally identical to `ROF_DOMAIN_MESH` - until
  Step 4's crop reassigns it internally to a cropped subset before computing
  weights.
- Nothing anywhere reports the cropped path back out. `write_mapping_file()`
  wrote `xc_a`/`yc_a`/`mask_a`/`area_a`/`src_grid_dims`/`n_a` describing the
  *cropped* mesh (e.g. 3,600 elements), while `ROF_DOMAIN_MESH` (and DROF's
  actual discharge data stream, confirmed untouched by any CrocoDash code)
  still describe the *full* mesh (e.g. 21.6M elements).

At runtime, CMEPS's sparse-matrix remap requires the field DROF hands off to
have exactly `n_a` elements, indexed the way the map file's `row`/`col` say.
A map built from a 3,600-element index space cannot be correctly applied to
a 21.6M-element field - this is a dimensional inconsistency, not a
performance question, and it should either abort at coupler init or (worse)
silently misindex discharge onto the wrong ocean cells.

**Not entirely new**: the pre-existing "regional mesh override"
(`rof_esmf_mesh_filepath`, e.g. ajanney's CARIB12 mesh) has the same
disconnect - `ROF_DOMAIN_MESH` never picks up that override either. As far as
this investigation can tell, nobody has actually run this pipeline through
an actual model step to confirm runoff mapping works at runtime; every check
so far (including the Step 7 CrocoDash integration test) only confirmed the
mapping *file* writes successfully, not that it's consistent with whatever
domain the runtime component believes it has. Step 4's crop default just
made the mismatch appear even when no override is given, since that case
used to be self-consistent (both `ROF_DOMAIN_MESH` and the map's `n_a` at
21.6M) even though it was too slow/OOM to ever finish.

**The fix**: keep cropping as a pure internal speed-up for computing
*weights*, but make the *written file* always describe the full, original
mesh - so `n_a` matches whatever `ROF_DOMAIN_MESH` actually is, regardless of
whether cropping ran.

- `crop_esmf_mesh_to_bbox()`'s window-finding logic extracted into a shared
  `_mesh_index_window()` helper, so both the crop step and the new
  index-remap step agree on the exact same window.
- `write_mapping_file()` gains `src_full_mesh`/`src_crop_window` params. When
  given, every source-domain field (`xc_a`, `yc_a`, `xv_a`/`yv_a` via
  `_construct_vertex_coords`, `mask_a`, `area_a`, `frac_a`, `src_grid_dims`,
  `nj_a`, `ni_a`) is built from the FULL mesh instead of the cropped one, and
  the xESMF weights' `col` indices (which are positions in the cropped
  mesh's flat raster) are translated back into the full mesh's flat raster
  via simple offset arithmetic (`global_i = local_i + imin`, etc.) before
  anything else touches them - including area normalization, which must
  index into the full-mesh `area_a`.
- The smoothing (`_nnsm.nc`) write needed no separate remap: its weights
  (`S_smooth`) are built from `S_coo`, which is constructed directly from the
  *already-corrected* `_nn.nc` file's own `row`/`col`/`ni_a`/`nj_a` - so once
  the nn map is fixed, the smoothed map's indices are automatically already
  in full-mesh space. It only needed the same `src_full_mesh` for its
  descriptive fields, to stay consistent with the nn map.
- Re-vectorized `_construct_vertex_coords()` (undoing Step 6's revert) - now
  genuinely justified again, since this loop must run over the FULL mesh
  (tens of millions of elements for the production case) to build the
  correct-sized `xv_a`/`yv_a`, not just the small cropped window.

**Why this doesn't reintroduce the original OOM**: the expensive part that
actually caused the OOM (Step 1) was `Topo.from_esmf_mesh()`'s full supergrid
reconstruction (`dx`/`dy`/`area`/`angle_dx` via rotation-angle computation) -
that was already eliminated in Step 2 and stays eliminated. The *actual*
`xe.Regridder()` call - the other expensive part - still only ever runs on
the small cropped grid; cropping still does that job. What comes back is
only the cheap parts: reading/reshaping the full mesh's raw arrays,
vectorized vertex-coord construction, and a larger (~300MB) netCDF write -
all O(n) array operations, not the reconstruction that scales badly.

**Verified real production mesh, both directions:**

- Regional mesh (`GLOFAS_CARIB12_mesh.nc`, 319,200 elements), crop enabled:
  **12.49 s wall, 11.01 s CPU** (up from the previous, incorrect crop's
  0.92 s - expected, now doing real work over the full mesh again - but
  still much faster than the ~18.75 s/12.07 s CPU of the fully-uncropped
  Step 2+3 path). Diffed against the original `mapping_before_fix/main`
  baseline: **byte-identical across all variables in both `_nn.nc` and
  `_nnsm.nc`**, and critically, **`n_a` = 319,200 in both** - cropping no
  longer changes what the file claims to describe at all.
- Global mesh (21.6M elements): retest complete. `n_a` correctly comes back
  as 21,600,000 (not 3,600) in both `_nn.nc` and `_nnsm.nc`. Timing:
  **NN map 1060.73 s, smoothed map 1128.44 s, total wall 2189.17 s
  (36.49 min), CPU 640.60 s (10.68 min, 29% utilization), peak RSS
  12,235,516 KB (~12.24 GB)**. This is essentially the *same* as Step 2's
  original shape-lookup-only number (35.4 min, 13.0 GB) - i.e. once
  correctness requires the written file to be full-mesh-sized regardless of
  cropping, **cropping's speed benefit at global scale is close to zero**.
  It still helps meaningfully at regional scale (12.5 s cropped vs 18.75 s
  uncropped, Step 2+3's number - about a 35% cut), just not at the scale
  that originally motivated this effort. See Step 9 for why, and for a fix
  that recovers the speed cropping was supposed to provide, without its
  correctness risk.

Added a regression test for the actual bug:
`test_gen_rof_maps_crop_matches_uncropped_physical_mapping` now explicitly
asserts `n_a` is identical between `crop_source_mesh=True` and `=False`
(previously it only checked physical-mapping equivalence, which doesn't
catch a shrunk-`n_a` bug since a smaller self-consistent map still "maps
correctly" between the source and destination points it does include - it
just doesn't match the runtime domain).

**Not yet done**: fixing the same disconnect for `rof_esmf_mesh_filepath`
overrides (ROF_DOMAIN_MESH still doesn't pick those up either) - that's a
CrocoDash-side fix (in `case_creator.py`/`RunoffConfigurator`), not a
mom6_forge one, and out of scope for this branch. Flagging it here so it
isn't lost, since it's the same class of bug in a different code path.

Implemented, tested, and pushed to PR #125 (commit `55582e1`).

### Step 9 — profiled with scalene + strace, found the *real* global-mesh cost, fixed it (~29x)

Step 8's global-mesh retest (36.5 min, 12.24 GB) landed right back around Step
2's original number, meaning cropping wasn't buying anything at that scale
anymore. Rather than guess why, profiled it properly instead of continuing to
reason from wall-clock numbers alone.

**Scalene** (`scalene run --profile-all`) on the regional case showed
`mapping.py`'s own Python code (including the vertex-construction loop) at
~0% of total time - confirming the bottleneck isn't our code's compute at
all. Most time was buried inside a generic thread-dispatch frame
(`threading.py:995`), not resolvable further at the Python-line level.

**strace**, attached directly to the live production job regenerating a real
case's mapping files, was far more informative: while writing `_nnsm.nc`, the
process was doing a **backward-seeking, doubled-read, 8 KB-chunk
read-then-write loop** - `lseek` to a decreasing offset, `read` the same 8 KB
twice, `write` it back - instead of a single sequential forward write. That
pattern is the signature of `ds.to_netcdf(..., format="NETCDF3_64BIT")`
(`write_mapping_file()`, `mapping.py:562-566` as of Step 8): CESM's mapping
files must be in NETCDF3_64BIT (64-bit offset classic) format for
compatibility, but writing large fixed-size variables directly in that format
through netCDF4-python's classic-format writer is pathologically slow.

**Isolated and quantified the write cost** with a standalone benchmark
(synthetic dataset shaped exactly like the real output, `n_a=21,600,000`),
comparing three ways to end up with a NETCDF3_64BIT file:

```
(a) xarray -> to_netcdf(format="NETCDF3_64BIT") directly (current code):  289.37 s
(b) xarray -> to_netcdf(format="NETCDF4"):                                  2.16 s
    then `nccopy -6` convert NETCDF4 -> 64-bit-offset:                    14.77 s
    (b) TOTAL:                                                            16.93 s
(c) low-level netCDF4.Dataset API direct -> NETCDF3_64BIT (bypass xarray): 239.14 s
```

(c) rules out an xarray-specific inefficiency - the low-level netCDF4-python
API is just as slow, so the backward-RMW behavior is inherent to `libnetcdf`'s
classic-format writer itself when writing large arrays directly, not
something xarray does wrong on top of it. (b) - write NetCDF4 (HDF5, which
has no such problem), then convert with the `nccopy -6` CLI tool - is ~17x
faster than the current direct approach, confirmed via `strace` to no longer
exhibit the backward-seek pattern, and confirmed via `ncdump -h` diff to
produce a header-identical file (same dims/vars/attrs, same
`NETCDF3_64BIT_OFFSET` data model).

**Implemented** in `write_mapping_file()`: write to a temp NETCDF4 file (same
directory as the final output, so `nccopy` isn't crossing filesystems), then
`subprocess.run(["nccopy", "-6", tmp_path, final_path], check=True)`.
`nccopy` is part of the standard netCDF-C distribution and confirmed present
in both the `mom6_forge` and `CrocoDash` conda envs; `shutil.which("nccopy")`
raises a clear error if it's ever missing rather than failing silently.

**One real bug found while implementing**: `nj_a`/`ni_a`/`nj_b`/`ni_b` are
built from plain Python int lists, which numpy/xarray defaults to int64 -
and because a `DataArray`'s name matching its sole dimension name makes
xarray auto-promote it to a coordinate variable, an encoding loop scoped to
`ds.data_vars` silently skips them. NETCDF4/HDF5 supports int64 so the
intermediate write succeeds either way, but classic/64-bit-offset format has
*no* int64 type at all, so `nccopy -6` failed loudly (`Not a valid data type
or _FillValue type mismatch`) converting them. The old direct-to-classic path
never hit this because xarray's netCDF3 backend unconditionally downcasts
unsupported dtypes for *every* variable (coords included) when the target
format is classic - a safety net that doesn't exist for NETCDF4. Fixed by
scoping the int32-downcast encoding loop to `ds.variables` (all variables,
including coordinates), not just `ds.data_vars`.

**Verified thoroughly**:
- All 12 existing `test_mapping.py` tests still pass.
- Regional mesh: output numerically identical (`np.allclose`/`array_equal`
  per variable) to the pre-Step-9 baseline; wall time dropped 14.8 s -> 2.53 s
  (NN map 8-11 s -> 1.47 s, smoothed 7-8 s -> 1.06 s).
- Global mesh (21.6M elements, real production GLOFAS mesh): output
  numerically identical to Step 8's verified-correct baseline (`n_a` still
  21,600,000, every variable identical), wall time dropped **36.49 min ->
  74.55 s - a ~29x speedup** (NN map: 1060.73 s -> 37.42 s; smoothed:
  1128.44 s -> 37.13 s; CPU utilization went from 29% - I/O-wait-dominated -
  up to 58%, consistent with the fix removing the I/O bottleneck).
- Real-world case: re-ran `basic_rof_mapping_call.ipynb`'s actual call
  (real global GLOFAS source mesh x ajanney's real
  `CrocIndoPacific_112` ocean mesh, 2,649,600 destination elements,
  `crop_source_mesh=False`, `rmax=fold=20`). The notebook's stale output
  showed 3565 s for the NN map alone, with the smoothing step never
  finishing. With this fix: **NN map 208.0 s, smoothed map 103.1 s, total
  5:15 (311.07 s)** - both steps complete, unattended, in about 1/17th the
  time the NN step alone previously took (and it hadn't even gotten to
  smoothing).

**Implication for cropping**: this result was obtained with
`crop_source_mesh=False` - no cropping at all - on a real, large,
production-scale case, and still finished in ~5 minutes. Combined with the
global-mesh number above (74.55 s, cropping doesn't even change `n_a` in the
output anymore since Step 8, so cropping now only affects internal
weight-computation cost, not output size), the write-path fix alone recovers
essentially all the speed cropping was originally meant to provide - without
cropping's history of correctness bugs (Step 8) or its added code complexity
(`crop_esmf_mesh_to_bbox`, `_mesh_index_window`, the `src_crop_window` index
remap in `write_mapping_file`). Worth a follow-up decision: keep
`crop_source_mesh` as a config knob for the regional-mesh case where it still
helps (~35%), or drop it entirely now that it's no longer load-bearing for
the global-mesh case it was built for.

### Step 10 — dropped cropping entirely; kept vectorization

Followed up on Step 9's open question. Before deciding, measured the one
number that actually mattered: with cropping on (current default) vs. off,
current (vectorized + nccopy-fixed) code, both on the standard tiny_gulf01
global-mesh benchmark:

```
crop=True (default):  74.55 s
crop=False:            79.65 s
```

A ~5 s difference - noise-level on a shared login node. Cropping's speed
benefit at the scale it was built for is not just "diminished," it's gone.
Decided to remove it entirely rather than keep it as a config knob nobody
needs: one fewer correctness-bug surface (Step 8's whole bug class doesn't
exist if there's no cropped/full-mesh distinction to keep consistent),
`write_mapping_file()`/`generate_ESMF_map_via_xesmf()`/`gen_rof_maps()` back
to single code paths with no crop-window index bookkeeping, and
`crop_esmf_mesh_to_bbox()`/`_mesh_index_window()` deleted outright (the
`_get_mesh_bbox()` bbox helper stays - it's also used by the separate,
pre-existing `map_overlap` masking in `generate_ESMF_map_via_xesmf()`, which
this step doesn't touch).

**Checked the interaction with vectorization before removing anything**,
since the two are coupled: without cropping, `_construct_vertex_coords()`
always runs on the FULL source mesh (21.6M elements for the production
mesh), not a cropped few-thousand-element window - so whether the loop or
the vectorized version is used stops being "barely a difference" the moment
cropping goes away. Measured directly on the real global mesh, comparing the
current vectorized implementation against the actual pre-Step-3 loop pulled
from git history (commit `d927e5b`), not a reinvented one:

```
Vectorized: 2.76 s
Looped:     71.71 s   (25.9x slower)
```

`gen_rof_maps()` calls `write_mapping_file()` twice (nn + smoothed), so
reverting to the loop would add ~138 s per run once cropping no longer
shrinks the mesh this runs over - taking the ~75-90 s current total up to
~215-230 s. Conclusion: **keep vectorization, remove cropping** - the loop's
cost only looked negligible in Step 6 because cropping was hiding it by
keeping the mesh tiny; remove that crutch and the vectorized version is
clearly worth its (modest) added complexity.

**Changes**: `_construct_vertex_coords()` untouched (already vectorized from
Step 8). Removed from `mapping.py`: `crop_esmf_mesh_to_bbox()`,
`_mesh_index_window()`, `write_mapping_file()`'s `src_full_mesh`/
`src_crop_window` params (and the index-remap block that used them),
`generate_ESMF_map_via_xesmf()`'s `src_full_mesh_path`/`src_crop_window`
params, and `gen_rof_maps()`'s `crop_source_mesh`/`crop_buffer_deg` params
and the cropping block. `src_domain_mesh` renamed back to `src_mesh`
throughout `write_mapping_file()` now that there's only one source mesh
concept again.

**Verified**: full test suite updated to match - removed
`test_crop_esmf_mesh_to_bbox_shrinks_to_expected_window`,
`test_crop_esmf_mesh_to_bbox_rejects_nonmonotonic_mesh`, and
`test_gen_rof_maps_crop_matches_uncropped_physical_mapping` (and the
now-unused `crop_ocn_grid` fixture and `_physical_mapping` helper); added
`test_gen_rof_maps_end_to_end` as a plain smoke test for the simplified
function. `test_get_mesh_bbox_preserves_negative_latitude` and both
`write_mapping_file` classic-format/shape-lookup tests kept unchanged (none
of them touch cropping). 11/11 tests pass. Re-ran both benchmark scales with
the final simplified code: regional 2.14 s, global 87.86 s - consistent with
the crop=False numbers measured just above, confirming the removal didn't
change behavior. Also re-ran `basic_rof_mapping_call.ipynb`'s real
production-scale case (`CrocIndoPacific_112`) end-to-end with the simplified
call signature: NN map 221.2 s, smoothed 103.1 s - consistent with the
Step 9 real-world numbers.

Also cleaned up two loose ends found along the way: reverted a temporary,
never-committed patch to the nested `CrocoDash/CrocoDash/visualCaseGen/
external/mom6_forge/mom6_forge/mapping.py` copy (left over from Step 7's
integration test) via `git checkout --`, and removed `time_gen_rof_maps_
direct.py`'s now-nonfunctional `--no-crop` flag.

**Where this leaves the overall effort**: `main` (OOM, never completes) ->
now ~75-90 s at global-mesh scale, ~2 s at regional scale, via exactly two
changes: the shape-lookup fix (Step 2, eliminates the OOM) and the nccopy
write-path fix (Step 9, eliminates the actual remaining bottleneck).
Cropping (Steps 4, 6, 8) and its associated correctness-bug history turned
out to be unnecessary once the real bottleneck was found and fixed - a
reminder that an optimization aimed at the wrong hotspot can look load-
bearing right up until the actual hotspot gets fixed.

### Step 11 — fixed the `normalize_deg(src_lat)` bug flagged in Step 5

Step 5 flagged this as a known-remaining, out-of-scope issue; picked it up here
because the SeaSloth scaling sweep needs domains that reach below the equator
(Indo-Pacific, Caribbean) and could not measure them honestly otherwise.

`generate_ESMF_map_via_xesmf()`'s `map_overlap` masking ran the **source** mesh's
latitudes through `normalize_deg()` (`mapping.py:629`), wrapping every negative
latitude into a large positive one (-5 -> 355) so it compared as "north of
lat_max" and got masked out. Only the source line was affected - `_get_mesh_bbox()`
was already fixed in Step 4.

Measured the real impact against ajanney's regional CARIB12 mesh before touching
anything (masking arithmetic reproduced directly in numpy):

| Destination domain | Active source points, buggy | correct |
|---|---|---|
| Northern (lat 18..31) | 149 | 149 |
| Straddling equator (lat -5..31) | 240 | 267 |
| Purely southern (lat -5..0) | **0** | 27 |

So the bug was genuinely latent for northern-hemisphere domains (which is why
every earlier test here missed it), dropped ~10% of source rivers for an
equator-straddling domain, and masked out *every* source point for a purely
southern one - yielding an empty mapping file rather than an error.

**Fix**: one line - stop normalizing latitude, matching `_get_mesh_bbox()`'s
existing treatment, with a comment explaining why latitude must not be wrapped.

**Verified on real data, both directions**, over the Amazon-mouth region (the
regional mesh's 29 southern active points sit at lon 309-324, lat -5..0; an
earlier attempt at lon 280-290 returned 0 entries for the unrelated reason that
there are no rivers there - worth noting as an easy way to fool yourself here):

| Destination domain | nn entries, buggy | fixed |
|---|---|---|
| Purely southern (Amazon) | 0 | 24 |
| Straddling equator (Amazon) | 8 | 37 |

The Amazon - the largest freshwater discharge on Earth - was contributing
*nothing* to a southern-hemisphere domain.

**Regression test**: `test_map_overlap_masking_is_hemisphere_symmetric` in
`tests/test_mapping.py`. Builds a source mesh symmetric about the equator and two
mirror-image destination domains (lat 2..8 and lat -8..-2), and asserts both map
the same number of source cells. Confirmed it fails on the pre-fix code (southern
count 0) and passes after - i.e. it really guards the bug rather than just
passing. 12/12 tests in `test_mapping.py` pass; `black` clean.

Not yet committed - part of the same `runoff-mapping-scaling` branch / PR #125.

### Step 12 - the "basin-scale cliff" was a 0/360 seam bug in `_get_mesh_bbox`

The SeaSloth sweep reported North Atlantic (576K cells) and Indo-Pacific (2.4M)
as intractable: >1 hr at ~98% CPU inside ESMF's `ESMP_FieldRegridStore`, no
completion, ~1 GB RSS. I had written that up as a cost cliff somewhere between
100K and 600K destination cells, with `mask="all_unmasked"` as the leading
suspect. Both of those were wrong.

Two things falsified the cliff:

1. The production `CrocIndoPacific_112` mesh is 2,649,600 elements with
   **1,909,530 active** after land masking (72.1% - masking removes only 28%,
   not the order of magnitude I had assumed). That is **3.3x more active
   destination cells than the stalling North Atlantic case**, and it writes its
   nn map in ~210 s. So destination count cannot be the cause, and masking is
   not the explanation either.
2. Of the eight rungs, exactly one touches the 0/360 periodic seam, and it is
   exactly the one that hangs:

   | rung | lon range | seam? | result |
   |---|---|---|---|
   | box_1deg .. caribbean | 262..305 | no | 74-81 s |
   | north_atlantic | **280..360** | **yes** | **>1 hr, no finish** |
   | indo_pacific | 30..190 | no | never actually run |

   `north_atlantic` was `(xstart=280, lenx=80)`; 280 + 80 = 360.

Decisive test: the same 80x50 deg footprint, same 576,000 cells, shifted 5 deg
west to lon 275..355. It finished in **106.3 s** (47.2 s for the nn map). Then
`indo_pacific` at its full 2,419,200 cells - never actually attempted before,
its "intractable" status having been inferred from north_atlantic - finished in
**188.9 s**, consistent with the real case's ~210 s.

Root cause, confirmed directly:

```
seam    280..360: bbox lon   0.0000 .. 359.9167   lon span=359.92 deg   <-- wrong
shifted 275..355: bbox lon 275.0000 .. 355.0000   lon span= 80.00 deg
```

`_get_mesh_bbox()` does `normalize_deg(nodeCoords[:,0])` then plain `min()`/`max()`.
`normalize_deg` is `mod(x+360, 360)`, so the 601 nodes sitting on exactly lon 360
become 0.0 - which then *is* the minimum, while 359.9167 is the maximum. The
function returns a near-global longitude box for a mesh that spans 80 degrees.

`generate_ESMF_map_via_xesmf` feeds that bbox straight into the `map_overlap`
masking, so the `(src_lon < lon_min) | (src_lon > lon_max)` test excludes almost
nothing: instead of masking the source down to the domain's 80 deg window, the
regrid runs against the entire global 20-70N band. Hence the blow-up.

This is the same class of bug as Step 11's `normalize_deg(src_lat)` - a naive
`mod 360` applied where the wrap has to be reasoned about rather than normalized
away. Step 11 was latitude; this is longitude, on the other side of the same
function pair.

Not a benchmarking artifact: a user can legitimately configure a regional domain
whose eastern edge is lon 360, and they got a silent hang - no error, no memory
growth, one core pinned. SeaSloth's `DOMAINS` now asserts at import that no box
touches the seam, so the benchmark can't silently regress into this again.

### Step 12b - fixed it (commit 57775d5 on `runoff-mapping-scaling`, PR #125)

Two private helpers in `mapping.py`:

- `_lon_bbox(lon)` finds the largest angular *gap* between successive normalized
  longitudes and returns the interval outside it. That interval may wrap, i.e.
  `lon_min > lon_max`, which is the honest way to express a seam-crossing domain.
  For a fully periodic mesh every gap equals the grid spacing, so the tie falls
  through to `(lon[0], lon[-1])` - the full range, which is what a global mesh
  wants. `_get_mesh_bbox()` now delegates to it.
- `_lon_outside(lon, lon_min, lon_max)` is the companion membership test, flipping
  the `|` to `&` when the interval wraps, and replaces the inline comparison in
  the `map_overlap` block.

Truth table after the fix (built with `linspace`, see the warning below):

| input | bbox | width | wrapped |
|---|---|---|---|
| 280..360 (the failing case) | 280.0000 .. 0.0000 | 80.00 | yes |
| 350..360 | 350.0000 .. 0.0000 | 10.00 | yes |
| 275..355 | 275.0000 .. 355.0000 | 80.00 | no |
| 30..190 | 30.0000 .. 190.0000 | 160.00 | no |
| 0..360 (global) | 0.0000 .. 359.9167 | 359.92 | no |
| -10..10 (prime meridian) | 350.0000 .. 10.0000 | 20.00 | yes |
| single point | 42.0 .. 42.0 | 0.00 | no |

The prime-meridian row is a second bug this fixes that nobody had noticed: a mesh
spanning -10..10 previously reported a 350 deg bbox, for the same reason.

**End-to-end proof.** The exact domain that hung - lon 280..360, lat 20..70,
576,000 cells, against the production 21.6M-element GLOFAS mesh - now reports an
80.00 deg bbox and completes in **67.7 s** (31.4 s nn map + 36.2 s smoothed).

Faster than the 105.7 s the shifted 275..355 box takes, which is not a
discrepancy: the two 80 deg windows sit over different river density. 275..355
includes the Mississippi/Gulf outflow, 280..360 trades that for the quieter east
Atlantic, so it has fewer active source cells.

Two regression tests in `tests/test_mapping.py`, both confirmed to fail before the
change by reverting the fix and re-running:

- `test_get_mesh_bbox_handles_0_360_seam` - asserts the bbox *width* for a mesh
  ending on exactly lon 360. Pre-fix: "bbox spans 359.00 deg for a 10 deg mesh".
  Width rather than an ordered pair, because a wrapped interval is the correct
  answer for that domain and pinning the pair would encode the wrong invariant.
- `test_map_overlap_masking_is_rotation_invariant` - the longitude counterpart to
  Step 11's hemisphere-symmetry test. Over a source mesh uniform in longitude, two
  equal-width destination windows must map equally many source cells wherever they
  sit. Pre-fix the seam window mapped 3x as many, having masked nothing.

14/14 in `test_mapping.py`; `test_utils`/`test_supergrid`/`test_grid` clean apart
from `test_grid.py::test_is_tripolar`, which fails on stashed changes too
(pre-existing, unrelated). `black` clean.

**Trap for anyone extending these tests: build the seam case with `linspace`, not
`arange`.** `np.arange(280, 360, 1/12)` stops at `359.99999999998181`, never
reaches 360, and so never triggers the wrap - a test written that way passes
against the *unfixed* code. My first prototype did exactly this and gave a false
pass; `np.linspace(280, 360, 961)` lands on 360 exactly, which is what
`to_esmf_mesh` actually produces (601 nodes at exactly 360.0 in the real mesh).

Still open: once PR #125 merges, SeaSloth's `CLAUDE.md` and its runoff page both
say the bug is "open in mom6_forge" and want updating, and the `north_atlantic`
box could optionally move back to 280..360 so the sweep exercises the seam path.
Left off-seam for now - a benchmark shouldn't depend on an unmerged fix, and the
import-time assertion still protects anyone running it against an older
mom6_forge.

## SeaSloth scaling sweep (run)

Moved out of the "planned" section below, since it now exists as a permanent
benchmark rather than a one-off script: `benchmarks/mom6_forge/test_mapping.py`
in the SeaSloth repo, with its own report page, `report/runoff_mapping.html`
(generated by `scripts/generate_runoff_report.py`, linked from the SeaSloth Pages
nav and landing page). See SeaSloth's `CLAUDE.md` for how to run it - note it
needs the `mom6_forge` conda env, not `CrocoDash`, since CrocoDash's nested
mom6_forge checkout lacks the write-path fix.

Two sweeps:

- **Domain ladder** - an ascending ladder of destination sizes at fixed 1/12 deg,
  ~4x per rung: 1/2/4/8 deg boxes anchored at the Gulf of Mexico's southwest
  corner (so they nest inside the Gulf rung), then the real domains - Gulf of
  Mexico (34K cells), Caribbean (116K), North Atlantic (576K), Indo-Pacific
  (2.42M). Starting well below any real configuration is deliberate: it shows
  where the curve starts before the rungs get expensive.
- **Resolution** - the same call over a fixed Gulf of Mexico footprint at 1/4,
  1/8, 1/12, 1/25 deg, so only the destination cell count changes.

Both run against the production ROF mesh only (21.6M elements, what CIME
registers as `ROF_DOMAIN_MESH`). An earlier version also carried a series for
ajanney's regional CARIB12 mesh; dropped, since no real case uses a regional
source mesh - the regional-vs-global speedup is already quantified in Step 1b
above and doesn't need a permanent benchmark.

Measured (production mesh, 1/12 deg, rmax=fold=20 km):

| Rung | Ocean cells | Time | Peak RSS |
|---|---|---|---|
| 1 deg box | 144 | 77.7 s | 12.5 GB |
| 2 deg box | 576 | 73.7 s | 13.0 GB |
| 4 deg box | 2304 | 76.5 s | 13.4 GB |
| 8 deg box | 9216 | 74.2 s | 13.4 GB |
| Gulf of Mexico | 33696 | 80.7 s | 12.6 GB |
| Caribbean | 115920 | 78.9 s | 12.7 GB |

The headline result: wall time is flat. The destination grid grows **805x** from
the 1 deg box to the Caribbean and wall time grows **1.02x**, non-monotonically -
the whole spread is run-to-run noise. Peak RSS is flat too, ~12.5-13.4 GB
throughout. Essentially all of the cost is the fixed source-mesh read/re-write:
every source-domain field is ~2.2 GB and goes into both output files. Optimizing
the ocean side of this call has almost nothing left to win; the write path does
(which is exactly what Step 9 fixed).

Same story on the resolution axis: 39x more ocean cells at a fixed Gulf footprint
moves wall time 1.02x (79.7 -> 81.2 s), and 1/8 deg came back *faster* than
1/4 deg. Two independent axes both saying the destination grid is not the cost.

All eight rungs now complete - see Step 12, which is where the "North Atlantic
and Indo-Pacific don't finish" claim turned out to be a bug in `_get_mesh_bbox`
rather than a scaling wall.

## Original scaling-sweep plan (superseded by Step 11's SeaSloth suite)

- Vary ocean grid size (e.g. 2, 4, 8, 16 deg boxes at fixed 1/12 deg
  resolution, or fixed extent at increasing resolution) - expect this to
  dominate both NN-map and smoothing cost.
- At one grid size, compare `rof_esmf_mesh_filepath` = ajanney's regional
  CARIB12 mesh vs the full global production mesh, to quantify the actual
  speedup from regional-cropping the source mesh (source-mesh size only
  affects the NN-map step, per the code-path analysis above - so the
  speedup should show up entirely there, not in the smoothing step).
- Record: ocean cell count, source mesh element count, NN-map time,
  smoothing time, total time, for each combination.

## Files in this folder

- `tiny_gulf01.yaml` - case config for the first tiny test case
- `create_configure_only.py` - creates a case + configures forcings without
  auto-running process_forcings (works around the CLI's lack of a
  `--configure-only` flag)
- `time_runoff_step.py` - times just the runoff-mapping step in isolation
  (works around the MCP server's `cice`/`ww3` bug above)
- `time_gen_rof_maps_direct.py` - calls `mom6_forge.mapping.gen_rof_maps()`
  directly (no CrocoDash), used as the before/after harness for the
  `runoff-mapping-scaling` mom6_forge branch effort above
