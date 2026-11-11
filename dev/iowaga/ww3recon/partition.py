"""
Watershed partitioning of a 2D spectrum.

Why this exists. Validating the reconstruction needs partition parameters AND
the truth spectrum. Those come from different IOWAGA products (gridded vs point
output), so pairing them introduces a spatial sampling mismatch on top of the
reconstruction error you actually want to measure.

Partitioning the truth spectrum directly gives you partition parameters that
are exactly co-located with it. That isolates METHOD error from SAMPLING error.

The two modes answer different questions, and you want both:

  self_partition  -> "how much shape information is lost by compressing a
                      spectrum to partition bulk parameters and expanding it
                      again?" This is the method's intrinsic ceiling.

  archive         -> "how well does this work on the data I will actually
                      ship?" Includes grid-sampling mismatch and whatever
                      IOWAGA's own partitioning does differently from this.

A gap between them is informative rather than alarming: it sizes the sampling
penalty. This implementation is NOT a reproduction of WW3's internal
partitioner -- do not expect partition-for-partition agreement with the
archive.
"""

from __future__ import annotations

import numpy as np

__all__ = ["partition_spectrum", "partition_to_arrays"]


def _neighbour_offsets():
    off = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0)]
    return off


def partition_spectrum(E: np.ndarray, f: np.ndarray, theta_rad: np.ndarray,
                       u10: float = None, wind_dir_rad: float = None,
                       n_max: int = 4, min_energy_frac: float = 0.01,
                       wind_sea_factor: float = 1.2) -> list:
    """Steepest-ascent watershed partition of one 2D spectrum.

    Follows the inverse-catchment approach of Hasselmann et al. (1996) as
    implemented by Hanson & Phillips (2001): every bin climbs to a local
    maximum, and bins sharing a maximum form a partition. Direction is periodic;
    frequency is not.

    Wind-sea identification uses the standard inverse wave age criterion,
    ``wind_sea_factor * u10/c * cos(theta - wind_dir) > 1``, applied per bin.
    Without wind, PWS is returned as NaN and the caller must supply it.

    Returns a list of dicts with phs, ptp, pdir (deg), pspr (deg), pws, m0.
    """
    nf, nd = E.shape
    flat = E.ravel()
    order = np.argsort(-flat)

    # Steepest ascent to a local maximum, memoised.
    label = np.full(nf * nd, -1, int)
    offs = _neighbour_offsets()

    def climb(idx):
        path = []
        while True:
            if label[idx] >= 0:
                for p in path:
                    label[p] = label[idx]
                return label[idx]
            path.append(idx)
            i, j = divmod(idx, nd)
            best, best_v = idx, flat[idx]
            for di, dj in offs:
                ii, jj = i + di, (j + dj) % nd
                if 0 <= ii < nf:
                    k = ii * nd + jj
                    if flat[k] > best_v:
                        best, best_v = k, flat[k]
            if best == idx:                       # local maximum
                new = climb.counter
                climb.counter += 1
                for p in path:
                    label[p] = new
                return new
            idx = best
    climb.counter = 0

    for idx in order:
        if flat[idx] <= 0:
            continue
        climb(int(idx))

    lab = label.reshape(nf, nd)
    df = f * ((f[1] / f[0]) - (f[0] / f[1])) / 2.0
    dth = float(theta_rad[1] - theta_rad[0])
    w = df[:, None] * dth

    parts = []
    for L in range(climb.counter):
        mask = lab == L
        m0 = float((E * w)[mask].sum())
        if m0 <= 0:
            continue
        Em = np.where(mask, E, 0.0)
        Ef = (Em * dth).sum(axis=1)
        pk = int(np.argmax(Ef))
        # Parabolic refinement of the peak, matching what WW3 does; without it
        # PTP is quantised to the frequency bins.
        if 0 < pk < nf - 1:
            y0, y1, y2 = Ef[pk - 1], Ef[pk], Ef[pk + 1]
            den = y0 - 2 * y1 + y2
            shift = 0.5 * (y0 - y2) / den if den != 0 else 0.0
            shift = float(np.clip(shift, -0.5, 0.5))
            fp = f[pk] * (f[1] / f[0]) ** shift
        else:
            fp = f[pk]

        a1 = float((Em * w * np.cos(theta_rad)[None, :]).sum() / m0)
        b1 = float((Em * w * np.sin(theta_rad)[None, :]).sum() / m0)
        thb = np.arctan2(b1, a1) % (2 * np.pi)
        spr = np.sqrt(max(2.0 * (1.0 - np.hypot(a1, b1)), 0.0))

        if u10 is not None and wind_dir_rad is not None:
            c = 9.80665 / (2 * np.pi * f)[:, None]
            crit = (wind_sea_factor * u10 / c *
                    np.cos(theta_rad[None, :] - wind_dir_rad)) > 1.0
            pws = float((Em * w)[mask & crit].sum() / m0)
        else:
            pws = np.nan

        parts.append({"m0": m0, "phs": 4.0 * np.sqrt(m0), "ptp": 1.0 / fp,
                      "pdir": float(np.rad2deg(thb)), "pspr": float(np.rad2deg(spr)),
                      "pws": pws, "label": L})

    parts.sort(key=lambda d: -d["m0"])
    total = sum(p["m0"] for p in parts)
    parts = [p for p in parts if p["m0"] >= min_energy_frac * total]
    return parts[:n_max]


def partition_to_arrays(part_lists: list, n_partitions: int = 4) -> dict:
    """Pack per-time partition lists into (n_time, n_partitions) arrays."""
    n = len(part_lists)
    out = {k: np.full((n, n_partitions), np.nan)
           for k in ("phs", "ptp", "pdir", "pspr", "pws")}
    for i, parts in enumerate(part_lists):
        for k, p in enumerate(parts[:n_partitions]):
            for key in out:
                out[key][i, k] = p[key]
    return out
