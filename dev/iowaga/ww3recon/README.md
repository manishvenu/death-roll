# ww3recon

Reconstruct 2D wave spectra `E(f, θ)` from WW3 partition output.
Target dataset: IOWAGA / Ifremer `GLOBMULTI_ERA5_GLOBCUR_01`.

Pure NumPy, no compiled dependencies. SciPy is not required.

## Install / use

Drop the `ww3recon/` directory on your `PYTHONPATH`.

```python
from ww3recon import SpectralGrid, PartitionSet, Reconstructor

grid = SpectralGrid.iowaga()          # 36 freqs × 24 dirs, native IOWAGA grid
rec  = Reconstructor(grid)            # builds shape tables once, ~0.01 s

p = PartitionSet(
    phs=phs, ptp=ptp, pdir=pdir,      # (n_points, n_partitions), degrees for dirs
    pspr=pspr, pws=pws,
    hs=hs, t0m1=t0m1, t02=t02,        # (n_points,) whole-spectrum fields
)

out = rec.reconstruct(p)
E = out["spectrum"]                   # (n_points, n_freq, n_dir), m² s rad⁻¹
```

`t0m1` is **required** — it is the constraint that determines peakedness.
`t02` is optional; without it the tail exponent stays at the JONSWAP default of 5.
`hs` is optional and used only for the energy-closure diagnostic.

## Shape families

The frequency shape is pluggable:

```python
from ww3recon import ReconstructionConfig, Reconstructor
cfg = ReconstructionConfig(windsea_family="jonswap", swell_family="gaussian")
rec = Reconstructor(grid, cfg)
```

| Family | Kind | Fitted parameter | Notes |
|---|---|---|---|
| `jonswap` | wind sea | `gamma` (1–7) | Fittable tail exponent. |
| `donelan` | wind sea | `gamma` (1–7) | f⁻⁴ equilibrium range; width tied to gamma. |
| `elfouhaily` | wind sea | `omega_c` (0.84–5) | **Default.** Long-wave branch of the unified spectrum, parameterised by inverse wave age. Intrinsic tail — no tail stage. |
| `pierson_moskowitz` | wind sea | none | Null hypothesis: if PM matches fitted JONSWAP on your data, the peakedness fit is not earning its complexity. |
| `gaussian` | swell | `q` (0.01–0.12) | Relative width. Fails on real data (spiky comb between partitions). |
| `ochi_hubble` | swell | `lambda` (1–12) | **Default.** Retains asymmetry; power-law tails fill inter-partition gaps. |

Defaults were set from the four-site real-data sweep (Jan 1993, see
`../HANDOFF.md` section 4): Elfouhaily + Ochi-Hubble scores 0.901 mean spectral
correlation; every Gaussian-swell combination scores ~0.69. The mathematical
description is in `doc/technical_note.pdf`.

Prior penalties are normalised by each parameter's own range, so `lambda_ws`
and `lambda_sw` are dimensionless and need no retuning when you swap families.

Synthetic self-test sweep (300 points, seed 1; note the synthetic truth is
built from JONSWAP + Gaussian components, so those families are favoured here
and the package default scores 0.938 on this test):

| Wind sea | Swell | Corr | p10 |
|---|---|---|---|
| jonswap | gaussian | 0.972 | 0.921 |
| elfouhaily | gaussian | 0.965 | 0.916 |
| pierson_moskowitz | gaussian | 0.943 | 0.866 |
| donelan | gaussian | 0.936 | 0.857 |
| jonswap | ochi_hubble | 0.941 | 0.832 |

**Read this table with care.** The synthetic truth is built from JONSWAP wind
sea, so JONSWAP winning is partly tautological. The informative result is that
Elfouhaily lands within 0.007 of the family that *generated* the data — which
is the expected outcome, because inside the resolved band the two are close.
Rank families on your real data, not on this table.

### On the "unified spectrum"

Three honest caveats before reaching for `elfouhaily` as the wind-sea family:

1. It is wind-sea only. It has no concept of swell.
2. It is parameterised by U₁₀ and inverse wave age, not by (Hs, Tp). Here it is
   renormalised to `PHS` and re-peaked to `PTP`, which discards its amplitude
   prediction — the shape survives, the physics of the amplitude does not.
3. **On the native grid almost none of it is present.** The grid stops at
   0.95 Hz ≈ k = 3.6 rad/m; Elfouhaily's capillary peak is at k = 370 rad/m,
   roughly 96 Hz. Within the resolved band you are using a JONSWAP-like form
   with wave-age-dependent peak enhancement, not a fundamentally different
   spectrum.

Where it genuinely earns its place is the tail extension below.

## Tail extension beyond the native grid

```python
from ww3recon import attach_tail, surface_stokes_drift, mean_square_slope

ext = attach_tail(E, grid, u10=u10, wind_dir_deg=wdir, tp=tp)   # to 20 Hz
us  = surface_stokes_drift(ext["spectrum"], ext["grid"])
```

Surface Stokes drift weights the spectrum as f³ and MSS as f⁴, so both are
biased low by truncation at 0.95 Hz. On the synthetic self-test the native grid
captured ~82% of surface Stokes magnitude and ~25% of MSS.

**Do not cite those numbers.** They come from synthetic spectra paired with
RANDOM U₁₀ in 5–18 m/s, so the wind and the wind sea were not physically
consistent with each other. They indicate the order of magnitude of the
truncation effect — Stokes drift biased low by something like tens of percent,
MSS essentially unavailable from the native grid — and nothing more. Re-measure
on real spectra with the matching ERA5 winds before putting a number in a paper.

`mode="auto"` (default) uses continuity matching at the join where that is well
conditioned and falls back to Elfouhaily's own wind-driven amplitude elsewhere.
The fallback exists because a pure-swell point has near-zero energy at 0.95 Hz,
and continuity matching would scale the tail to zero — but a real ocean under
10 m/s wind carries short waves regardless of swell. Points using the fallback
are flagged in `used_absolute`; in the self-test that was 120/200.

The extension is **anchored, not derived**: it needs a wind field, and its
absolute level inherits your Stage 2 tail-exponent error where continuity
matching is used. Check `join_ratio` — values far from 1 mean the
reconstruction's tail and Elfouhaily's disagree at the join.

## Method

Per partition: JONSWAP (wind sea) or Gaussian (swell) in frequency, blended by
`PWS`, times a cos-2s directional distribution with the exponent derived
analytically from `PSPR`. Each partition is renormalised to its own `PHS`, so Hs
closure is exact by construction. Partitions are summed — the assembly is
label-invariant, so partition index swapping between neighbouring cells is
harmless.

Two shape parameters remain free: `γ` (wind sea) and `q` (swell relative width).
They are fitted by matching the archived `T0M1`:

- **m₋₁ (action)** is weighted toward the low-frequency flank where peakedness
  lives. This is the constraint that does the work.
- **m₂ (via `T02`)** is tail-dominated, so it calibrates the high-frequency
  exponent in a separate second stage.
- **m₁ (momentum)** is nearly determined once m₀ and f_p are fixed and moves
  very little with γ. It is computed and reported, but deliberately kept out of
  the objective — it carries almost no information about peak shape.

Only one constraint is available for two unknowns, so weak priors
(γ→3.3, q→0.04) break the degeneracy. Where a point contains only one family
the fit is exactly determined and the absent family's prior is irrelevant;
those cells are flagged `underconstrained_ws` / `underconstrained_sw`.

The shape integrals depend only on `(f_p, shape parameter)` and are tabulated
once at construction. That turns a per-gridpoint nonlinear optimisation into a
table lookup plus a vectorised grid search.

## Validation

```python
from ww3recon.validate import (compare, stratify, summarise,
                               check_spread_convention,
                               check_direction_convention)

print(summarise(compare(E_rec, E_true, grid), "all"))
strata = stratify(p, E_rec, E_true, grid)   # reports per-stratum, incl. crossing seas
```

### Run these two first, before trusting anything

```python
check_direction_convention(E_true, pdir, grid)   # coming-from vs going-to
check_spread_convention(E_true, pspr, grid)      # a1-based vs a2-based PSPR
```

Both are silent failure modes: everything runs, results look plausible, the
directional field is wrong. Each returns a `verdict` key. Run them on a few
hundred unimodal truth spectra.

## Self-test

```bash
python -m ww3recon.selftest
```

Builds synthetic truth from known components — using a deliberately skewed
swell shape that is *not* the reconstructor's family, so recovery is not
tautological — and reports recovery by stratum.

Representative output (300 points, seed 1). **These are synthetic numbers from
data this package generated itself — they test the code, not the method.** See
"Validation status" below.

| Stratum | Hs SI | Tm₋₁₀ SI | Spectral corr (mean) | Corr p10 |
|---|---|---|---|---|
| all | 0.00% | 0.74% | 0.966 | 0.905 |
| unimodal | 0.00% | 1.03% | 0.990 | 0.966 |
| pure wind sea | 0.00% | 0.07% | 0.998 | 0.990 |
| pure swell | 0.00% | 0.69% | 0.955 | 0.899 |
| three+ partitions | 0.00% | 0.61% | 0.946 | 0.857 |
| **crossing seas** | 0.00% | 0.68% | **0.948** | **0.872** |

Hs is exact by construction — that row tests the code, not the method. The
correlation column is the real result, and crossing seas are the worst stratum
as expected. These are synthetic-truth numbers and should be treated as an
upper bound; real WW3 partitions are noisier than clean parametric components.

## Running the two-site validation

```bash
python run_validation.py --demo            # synthetic, no data needed
```

produces the same figures and tables you will get on real data, so you can
check the output format first. Then:

```bash
python run_validation.py \
    --spec-tropical  /data/iowaga/spec/ww3.202001_spec.nc \
    --spec-extratrop /data/iowaga/spec/ww3.202001_spec.nc \
    --lat-tropical 0.0    --lon-tropical -140.0 \
    --lat-extratrop 50.03 --lon-extratrop -145.28 \
    --partition-dir /data/iowaga/partitions --outdir ./validation
```

Requires `netCDF4` or `xarray`, plus `matplotlib` and `scipy`.

### Two modes

`--self-partition` partitions the truth spectra directly (watershed, in
`partition.py`) instead of reading the gridded fields. That removes the
grid-to-station sampling mismatch and measures the method's intrinsic ceiling:
how much shape survives compressing a spectrum to partition parameters and
expanding it again.

The default mode reads the archive's own partitions, which is what you will
ship. **Run both.** The gap between them separates method error from sampling
error, and you cannot interpret the second number without the first.

### Suggested sites

`io_iowaga.SUGGESTED_STATIONS` lists candidates with rationale. Defaults are
TAO 0N 140W (equatorial Pacific — persistent remote swell, weak local wind sea,
so it stresses the swell family and the partition split) and Station Papa
50.03N 145.28W (NE Pacific storm track — strong wind sea with long swell, the
classic validation site). Add NDBC 51004 near Hawaii if you want a deliberate
crossing-sea stress case.

Verify these stations exist in the file: `find_nearest_station` warns past
150 km, because silently validating 600 km from where you meant would not look
wrong in any plot.

## Validation status

**This package has never been run on real WW3 output.** Every number in this
README comes from `selftest.py`, which builds truth by summing clean parametric
components and derives the partition inputs exactly from them.

Ways that is easier than reality, roughly in order of how much they matter:

1. Truth is an exact additive sum of parametric components — the reconstructor's
   own assumption. Real partitions come from watershed segmentation of a
   source-term-balance spectrum, with boundaries cutting through energy.
2. Partition inputs are exact. Real ones carry algorithm noise and grid
   quantisation.
3. `PWS` is exactly 0 or 1. Real values are continuous, and the intermediate
   range is precisely where family blending is exercised.
4. `HS`/`T0M1`/`T02` are computed from the same truth, so closure is identically
   1. Real archives truncate partitions, making the residual genuine.
5. Wind sea uses JONSWAP, the reconstructor's own default family, so the family
   ranking is partly circular.
6. No sea ice, no shallow water, no current-modified spectra.

What the self-test does establish: the code runs, moments integrate correctly,
energy closure is exact, the fit converges, and the convention checkers
discriminate correctly on a known case. It is a unit test. Treat every skill
number as an upper bound until it has been run against the 12,490-point
virtual-buoy spectra.

## Performance

~5,800 points/s single-core, so roughly **31 s per global 0.5° timestep**
(~180k ocean points). Embarrassingly parallel over timesteps.

**Do not store the output.** A global reconstructed field is ~1.2 GB per
timestep in float64, which is ~3.5 TB/year — that defeats the entire reason for
using partitions. Reconstruct in memory and reduce immediately to whatever you
actually need (Stokes drift, flux terms, band-integrated energy). Cast to
float32 if you must hold several timesteps at once.

## Diagnostics emitted

`gamma`, `q`, `tail_exponent`, `fit_residual`, `energy_closure`,
`n_partitions`, `underconstrained_ws`, `underconstrained_sw`, `low_closure`.

Map `gamma` and `q` early: they should be spatially coherent. Salt-and-pepper
structure means the optimiser is fitting noise rather than signal.

## Known limitations

- `PTP` is quantised to the native frequency bins, which sets a floor on
  accuracy for narrow swell and shows up as stepping in time series.
- The tail-exponent stage uses the chunk-modal exponent when re-fitting γ,
  rather than a per-point value. The coupling is weak; `n_outer_iterations=2`
  settles it. Raise it if `fit_residual` maps look structured.
- Partition truncation in the archive loses low-energy residual. Watch
  `energy_closure` and decide explicitly whether to redistribute or document
  the low bias.
- If gridded `EF` (1D frequency spectrum) turns out to be archived, most of
  this machinery is unnecessary — you would know `E(f)` exactly and need only
  the directional fit. Check the archive listing before investing further.
