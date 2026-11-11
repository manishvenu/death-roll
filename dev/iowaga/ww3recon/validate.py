"""
Validation of reconstructed spectra against the archived 2D virtual-buoy spectra.

The comparison is reconstruction-vs-truth from the SAME model run, so any
disagreement is reconstruction error alone. Do not substitute buoy observations
here -- that folds in model error and you lose the ability to attribute the
residual.
"""

from __future__ import annotations

import numpy as np

from .core import (SpectralGrid, bulk_parameters, directional_moments,
                   moments, spread_to_s)

__all__ = ["compare", "stratify", "check_spread_convention",
           "check_direction_convention", "summarise"]


def _stats(rec: np.ndarray, tru: np.ndarray) -> dict:
    rec, tru = np.asarray(rec, float), np.asarray(tru, float)
    ok = np.isfinite(rec) & np.isfinite(tru)
    if not ok.any():
        return {k: np.nan for k in ("bias", "rmse", "si", "rel_bias", "n")}
    r, t = rec[ok], tru[ok]
    d = r - t
    mt = np.mean(t)
    return {
        "bias": float(np.mean(d)),
        "rmse": float(np.sqrt(np.mean(d ** 2))),
        "si": float(np.std(d) / mt) if mt else np.nan,
        "rel_bias": float(np.mean(d) / mt) if mt else np.nan,
        "n": int(ok.sum()),
    }


def compare(E_rec: np.ndarray, E_true: np.ndarray, grid: SpectralGrid) -> dict:
    """Integral, shape and directional metrics.

    Integral metrics should be near-exact by construction -- they test the code,
    not the method. The shape and directional metrics are the real test.
    """
    br = bulk_parameters(E_rec, grid)
    bt = bulk_parameters(E_true, grid)

    out = {"integral": {k: _stats(br[k], bt[k])
                        for k in ("hs", "tm10", "tm01", "tm02")}}

    # Physical invariants: should follow from the moments, reported separately
    # because they are what downstream applications actually consume.
    out["invariants"] = {k: _stats(br[k], bt[k]) for k in
                         ("energy_over_rho", "action_over_rho", "momentum_over_rho")}

    # Spectral correlation and normalised L2, per point.
    df, dth = grid.df, grid.dtheta
    w = (df[:, None] * dth)
    num = (E_rec * E_true * w).sum(axis=(1, 2))
    den = np.sqrt((E_rec ** 2 * w).sum(axis=(1, 2)) *
                  (E_true ** 2 * w).sum(axis=(1, 2)))
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.where(den > 0, num / den, np.nan)
        l2 = np.sqrt((((E_rec - E_true) ** 2) * w).sum(axis=(1, 2)) /
                     np.maximum((E_true ** 2 * w).sum(axis=(1, 2)), 1e-30))

    out["shape"] = {
        "spectral_correlation": {
            "mean": float(np.nanmean(corr)),
            "p10": float(np.nanpercentile(corr, 10)),
            "p50": float(np.nanpercentile(corr, 50)),
        },
        "normalised_l2": {
            "mean": float(np.nanmean(l2)),
            "p90": float(np.nanpercentile(l2, 90)),
        },
    }
    out["_per_point"] = {"corr": corr, "l2": l2}

    # Directional coefficients as functions of frequency -- the most diagnostic
    # single comparison. a2/b2 exposes a wrong directional family.
    dr = directional_moments(E_rec, grid)
    dt_ = directional_moments(E_true, grid)
    energetic = dt_["e"] > 0.02 * dt_["e"].max(axis=-1, keepdims=True)
    out["directional"] = {}
    for k in ("a1", "b1", "a2", "b2"):
        d = np.where(energetic, dr[k] - dt_[k], np.nan)
        out["directional"][k] = {
            "bias": float(np.nanmean(d)),
            "rmse": float(np.sqrt(np.nanmean(d ** 2))),
        }
    return out


def stratify(p, E_rec, E_true, grid, min_count: int = 20) -> dict:
    """Metrics per stratum.

    Uniform sampling flatters the result: most of the ocean is moderate
    unimodal swell, and a global mean hides exactly the cases the method
    struggles with. Report the worst stratum, not the mean.
    """
    active = p.active
    npart = active.sum(axis=1)
    hs_t = bulk_parameters(E_true, grid)["hs"]

    # Crossing seas: two comparably energetic partitions >60 deg apart.
    m0 = p.m0
    order = np.argsort(-m0, axis=1)
    i0, i1 = order[:, 0], order[:, 1] if m0.shape[1] > 1 else order[:, 0]
    r = np.arange(p.n_points)
    dth = np.abs(np.rad2deg(np.angle(np.exp(1j * np.deg2rad(
        p.pdir[r, i0] - p.pdir[r, i1])))))
    ratio = np.divide(m0[r, i1], np.maximum(m0[r, i0], 1e-12))
    crossing = (npart >= 2) & (dth > 60) & (ratio > 0.3)

    tws = np.nan_to_num((m0 * np.nan_to_num(p.pws)).sum(axis=1) /
                        np.maximum(m0.sum(axis=1), 1e-12))

    q = np.nanpercentile(hs_t, [25, 50, 75])
    strata = {
        "all": np.ones(p.n_points, bool),
        "unimodal": npart == 1,
        "two_partitions": npart == 2,
        "three_plus": npart >= 3,
        "crossing_seas": crossing,
        "pure_swell": tws < 0.15,
        "pure_windsea": tws > 0.85,
        "mixed": (tws >= 0.15) & (tws <= 0.85),
        "hs_q1": hs_t <= q[0],
        "hs_q4": hs_t > q[2],
    }
    res = {}
    for name, sel in strata.items():
        if sel.sum() < min_count:
            continue
        res[name] = compare(E_rec[sel], E_true[sel], grid)
        res[name]["count"] = int(sel.sum())
    return res


def check_spread_convention(E_true: np.ndarray, pspr_deg: np.ndarray,
                            grid: SpectralGrid) -> dict:
    """Determine empirically which directional coefficient defines PSPR.

    WW3 can define spread from the first (a1,b1) or second (a2,b2) directional
    coefficients. The cos-2s mapping differs between them, and getting it wrong
    is silent: everything runs, results look plausible, directions are wrong.

    Run this once on a few hundred truth spectra before trusting anything.
    """
    d = directional_moments(E_true, grid)
    e, df = d["e"], grid.df
    m0 = (e * df).sum(axis=-1)
    a1 = (d["a1"] * e * df).sum(axis=-1) / m0
    b1 = (d["b1"] * e * df).sum(axis=-1) / m0
    a2 = (d["a2"] * e * df).sum(axis=-1) / m0
    b2 = (d["b2"] * e * df).sum(axis=-1) / m0

    sp1 = np.sqrt(np.maximum(2.0 * (1.0 - np.hypot(a1, b1)), 0.0))
    sp2 = np.sqrt(np.maximum(0.5 * (1.0 - np.hypot(a2, b2)), 0.0))
    obs = np.deg2rad(np.asarray(pspr_deg, float))

    r = {}
    for name, cand in (("first_moment_kuik", sp1), ("second_moment", sp2)):
        ok = np.isfinite(cand) & np.isfinite(obs)
        r[name] = {
            "rmse_deg": float(np.rad2deg(np.sqrt(np.nanmean((cand[ok] - obs[ok]) ** 2)))),
            "corr": float(np.corrcoef(cand[ok], obs[ok])[0, 1]) if ok.sum() > 2 else np.nan,
        }
    r["verdict"] = min(("first_moment_kuik", "second_moment"),
                       key=lambda k: r[k]["rmse_deg"])
    return r


def check_direction_convention(E_true: np.ndarray, pdir_deg: np.ndarray,
                               grid: SpectralGrid) -> dict:
    """Test the four plausible direction conventions by mean-direction offset.

    Returns the rotation/reflection that best aligns the truth spectra's mean
    direction with the archived PDIR. Anything other than a near-zero offset
    for ``as_is`` means the assembly needs adjusting.
    """
    d = directional_moments(E_true, grid)
    e, df = d["e"], grid.df
    m0 = (e * df).sum(axis=-1)
    a1 = (d["a1"] * e * df).sum(axis=-1) / m0
    b1 = (d["b1"] * e * df).sum(axis=-1) / m0
    th = np.rad2deg(np.arctan2(b1, a1)) % 360.0
    obs = np.asarray(pdir_deg, float) % 360.0

    def circ_rmse(x, y):
        d_ = np.angle(np.exp(1j * np.deg2rad(x - y)), deg=True)
        return float(np.sqrt(np.nanmean(d_ ** 2)))

    cands = {
        "as_is": th,
        "flipped_180": (th + 180.0) % 360.0,
        "nautical_from_math": (90.0 - th) % 360.0,
        "nautical_from_math_flipped": (270.0 - th) % 360.0,
    }
    out = {k: {"rmse_deg": circ_rmse(v, obs)} for k, v in cands.items()}
    out["verdict"] = min(cands, key=lambda k: out[k]["rmse_deg"])
    return out


def summarise(metrics: dict, name: str = "") -> str:
    lines = [f"--- {name} (n={metrics.get('count', '?')}) ---"]
    for k, v in metrics["integral"].items():
        lines.append(f"  {k:6s} bias={v['rel_bias']*100:+7.2f}%  "
                     f"si={v['si']*100:6.2f}%")
    sc = metrics["shape"]["spectral_correlation"]
    l2 = metrics["shape"]["normalised_l2"]
    lines.append(f"  corr   mean={sc['mean']:.4f}  p10={sc['p10']:.4f}")
    lines.append(f"  L2     mean={l2['mean']:.4f}  p90={l2['p90']:.4f}")
    for k, v in metrics["directional"].items():
        lines.append(f"  {k:6s} rmse={v['rmse']:.4f}")
    return "\n".join(lines)
