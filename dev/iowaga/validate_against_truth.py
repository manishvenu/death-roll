"""Score the CrocoDash IOWAGA reconstruction against IOWAGA's own 2D spectra.

The archive publishes true WW3 2D spectra at ~10,800 virtual buoys. This takes
the nearest GRIDDED cell to a buoy, reconstructs it from the partitions the
same way `get_iowaga_2d_spectra` does, and scores it against the buoy's own
spectrum -- so it measures reconstruction error plus the buoy-to-cell sampling
mismatch, and cannot separate them. `ww3recon.partition` can, by re-partitioning
the truth spectra directly; that is in `dev/iowaga/ww3recon/` and is not
vendored into CrocoDash.

Two conventions have to be reconciled before any of this means anything, and
both are silent failure modes -- everything runs and the plots look plausible:

  * the point spectra carry a going-TO direction axis while the gridded fields
    (and CrocoDash's output) are coming-FROM, so the axis is rotated 180
    degrees here, not just reordered;
  * the mirrored comparison is computed alongside as a control. If the mirrored
    score is the higher one, the rotation is backwards.

Needs the 1993 pull under ~/scratch/ice/croc/iowaga (see its README) and
PYTHONPATH pointed at the CrocoDash checkout under test.
"""
import glob
import numpy as np
import xarray as xr
from CrocoDash.raw_data_access.datasets.iowaga import (
    spectra_from_partitions, partition_variable_names, iowaga_spectral_grid,
    significant_height_from_efth)

SITES = {
    "extratropics_open_natl": (-30.0, 52.0),
    "tropics_eq_pacific":     (-140.0, 0.0),
    "southern_ocean_deep":    (-90.0, -58.0),
}
GRID = "/glade/u/home/manishrv/scratch/ice/croc/iowaga/GLOB-30M/1993/LOPS_WW3-GLOB-30M_199301.nc"
POINTS = "/glade/u/home/manishrv/scratch/ice/croc/iowaga/POINTS/1993"

grid = iowaga_spectral_grid()
our_dir = np.rad2deg(grid.theta)                      # coming-FROM, 0..345
gds = xr.open_dataset(GRID)[partition_variable_names()]

for site, (lon, lat) in SITES.items():
    truth = xr.open_dataset(sorted(glob.glob(f"{POINTS}/{site}/*199301_spec.nc"))[0])
    # Truth direction axis is going-TO; ours is coming-FROM. Rotate by 180 and
    # reorder onto our axis. Compared raw, a correct reconstruction looks exactly
    # backwards -- this is the trap the module docstring calls out.
    to_dir = np.asarray(truth.direction.values, dtype=float)
    order = [int(np.argmin(np.abs(((to_dir - (d - 180.0)) + 180.0) % 360.0 - 180.0)))
             for d in our_dir]
    E_true = truth.efth.isel(station=0).values[:, :, order]        # (t, f, dir)

    sub = gds.sel(longitude=lon, latitude=lat, method="nearest")
    got_lon = float(sub.longitude); got_lat = float(sub.latitude)
    sub = sub.expand_dims(latitude=[got_lat], longitude=[got_lon]).load()
    out = spectra_from_partitions(sub, check_hs=False)
    E_rec = out.efth.isel(latitude=0, longitude=0).values.astype(np.float64)

    n = min(E_true.shape[0], E_rec.shape[0])
    E_true, E_rec = E_true[:n], E_rec[:n]
    hs_t = significant_height_from_efth(E_true, grid)
    hs_r = significant_height_from_efth(E_rec, grid)
    keep = np.isfinite(hs_t) & (hs_t > 0.5) & np.isfinite(hs_r)

    a = E_rec[keep].reshape(keep.sum(), -1)
    b = E_true[keep].reshape(keep.sum(), -1)
    a = a - a.mean(1, keepdims=True); b = b - b.mean(1, keepdims=True)
    corr = (a * b).sum(1) / np.sqrt((a * a).sum(1) * (b * b).sum(1))

    # 180-degree sanity: the unrotated comparison must score WORSE.
    c = E_true[keep][:, :, ::-1].reshape(keep.sum(), -1)
    c = c - c.mean(1, keepdims=True)
    corr_flipped = ((a * c).sum(1) / np.sqrt((a * a).sum(1) * (c * c).sum(1))).mean()

    bias = np.median((hs_r[keep] - hs_t[keep]) / hs_t[keep])
    print(f"{site:26s} grid pt ({got_lon:.1f}E,{got_lat:.1f}N)  n={keep.sum():3d}")
    print(f"    spectral corr  mean={corr.mean():.3f}  p10={np.percentile(corr,10):.3f}"
          f"   [mirrored axis: {corr_flipped:.3f}]")
    print(f"    Hs median bias {bias:+.2%}   (truth mean Hs {hs_t[keep].mean():.2f} m)")
