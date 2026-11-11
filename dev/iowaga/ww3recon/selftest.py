"""
Synthetic end-to-end self-test.

Builds "truth" spectra from known partition components, derives exactly the
inputs the archive would provide (PHS/PTP/PDIR/PSPR/PWS plus HS/T0M1/T02),
runs the reconstruction, and reports recovery.

The truth uses shape parameters drawn from a range WIDER than the priors, and
in the swell case a shape family that is not exactly the one the reconstructor
assumes, so this is a fair test of the method rather than a tautology.
"""

from __future__ import annotations

import numpy as np

from .core import (PartitionSet, Reconstructor, SpectralGrid, bulk_parameters,
                   cos2s, directional_moments, gaussian_shape, jonswap_shape)
from .validate import compare, stratify, summarise


def _component(grid, fp, hs, theta_deg, spread_deg, kind, gamma=3.3, q=0.04):
    f = grid.f[None, :]
    if kind == "windsea":
        S = jonswap_shape(f, np.array([[fp]]), np.array([[gamma]]))
    else:
        # Slightly skewed Gaussian: deliberately NOT the reconstructor's family,
        # so recovery is not tautological.
        S = gaussian_shape(f, np.array([[fp]]), np.array([[q]]))
        S = S * (1.0 + 0.25 * np.tanh((grid.f[None, :] - fp) / (q * fp)))
        S = np.maximum(S, 0.0)
    S = S / np.maximum((S * grid.df).sum(axis=-1, keepdims=True), 1e-30)
    Ef = (hs ** 2 / 16.0) * S

    s = 2.0 / np.deg2rad(spread_deg) ** 2 - 1.0
    D = cos2s(grid.theta[None, :], np.deg2rad(np.array([[theta_deg]]))[0],
              np.array([[s]])[0], grid.dtheta)
    return Ef[0][:, None] * D[0][None, :]


def build_case(grid, rng):
    """One synthetic point: 1-3 partitions with randomised properties."""
    npart = rng.integers(1, 4)
    comps, meta = [], []

    has_ws = rng.random() < 0.7
    for k in range(npart):
        if k == 0 and has_ws:
            kind = "windsea"
            fp = rng.uniform(0.12, 0.28)
            hs = rng.uniform(0.5, 5.0)
            spread = rng.uniform(20.0, 42.0)
            gamma = rng.uniform(1.2, 6.0)
            q = 0.04
            pws = 1.0
        else:
            kind = "swell"
            fp = rng.uniform(0.045, 0.11)
            hs = rng.uniform(0.4, 4.0)
            spread = rng.uniform(8.0, 26.0)
            gamma = 3.3
            q = rng.uniform(0.015, 0.09)
            pws = 0.0
        theta = rng.uniform(0.0, 360.0)
        comps.append(_component(grid, fp, hs, theta, spread, kind, gamma, q))
        meta.append(dict(phs=hs, ptp=1.0 / fp, pdir=theta, pspr=spread, pws=pws))
    return np.sum(comps, axis=0), meta


def run(n_points: int = 600, seed: int = 0, verbose: bool = True):
    grid = SpectralGrid.iowaga()
    rng = np.random.default_rng(seed)

    truths, metas = [], []
    for _ in range(n_points):
        E, meta = build_case(grid, rng)
        truths.append(E)
        metas.append(meta)
    E_true = np.stack(truths)

    max_part = max(len(m) for m in metas)
    shape = (n_points, max_part)
    phs = np.full(shape, np.nan)
    ptp = np.full(shape, np.nan)
    pdir = np.full(shape, np.nan)
    pspr = np.full(shape, np.nan)
    pws = np.full(shape, np.nan)
    for i, m in enumerate(metas):
        for k, d in enumerate(m):
            phs[i, k], ptp[i, k] = d["phs"], d["ptp"]
            pdir[i, k], pspr[i, k] = d["pdir"], d["pspr"]
            pws[i, k] = d["pws"]

    # Whole-spectrum fields exactly as the archive would carry them.
    b = bulk_parameters(E_true, grid)
    p = PartitionSet(phs=phs, ptp=ptp, pdir=pdir, pspr=pspr, pws=pws,
                     hs=b["hs"], t0m1=b["tm10"], t02=b["tm02"])

    rec = Reconstructor(grid)
    res = rec.reconstruct(p)
    E_rec = res["spectrum"]

    metrics = compare(E_rec, E_true, grid)
    strata = stratify(p, E_rec, E_true, grid)

    if verbose:
        print(summarise(metrics, "ALL"))
        print()
        for name in ("unimodal", "two_partitions", "three_plus",
                     "crossing_seas", "pure_swell", "pure_windsea", "hs_q4"):
            if name in strata:
                print(summarise(strata[name], name))
                print()
        print("fitted %-7s: mean %.2f  range [%.2f, %.2f]" %
              (res["ws_param_name"], res["ws_param"].mean(),
               res["ws_param"].min(), res["ws_param"].max()))
        print("fitted %-7s: mean %.3f range [%.3f, %.3f]" %
              (res["sw_param_name"], res["sw_param"].mean(),
               res["sw_param"].min(), res["sw_param"].max()))
        print("tail exponent : mean %.2f" % res["tail_exponent"].mean())
        print("energy closure: mean %.4f" % res["energy_closure"].mean())

    return {"metrics": metrics, "strata": strata, "result": res,
            "E_true": E_true, "E_rec": E_rec, "partitions": p, "grid": grid}


if __name__ == "__main__":
    run()
