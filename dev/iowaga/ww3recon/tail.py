"""
High-frequency extension beyond the model's native grid.

Why this exists. The WW3 native grid stops at 0.95 Hz. Several quantities you
might want from a reconstructed spectrum are weighted toward higher frequencies
than that and are therefore biased low if you simply truncate:

  - Surface Stokes drift weights the spectrum as f^3
  - Mean square slope weights it as f^4 and is dominated by the range the grid
    does not resolve at all
  - Wave-supported stress partitioning depends on the short-gravity range

The Elfouhaily et al. (1997) unified spectrum was built precisely to span
gravity through capillary waves, which makes it the natural way to close the
gap. This is the part of "the unified spectrum" that genuinely buys you
something here -- inside the resolved band it is close to JONSWAP, but outside
it there is no alternative in the partition data.

Scope and honesty
-----------------
The extension is a WIND-SEA construct. It is anchored on the reconstructed
spectrum at the grid edge and driven by U10, so it needs a wind field. It says
nothing about swell, which contributes nothing above ~0.2 Hz anyway.

The matching is a continuity constraint at the grid edge, not a physical
derivation: the extended tail is scaled so it joins the reconstruction
continuously. If the reconstruction's own tail slope disagrees strongly with
Elfouhaily's at the join, that scaling absorbs the discrepancy and the absolute
level of the extension inherits your Stage 2 tail-exponent error. Check
``join_ratio`` in the output -- values far from 1 mean the two disagree and the
extension should be treated as indicative only.
"""

from __future__ import annotations

import numpy as np

from .core import SpectralGrid, cos2s
from .families import C_M, G, K_M

__all__ = ["extended_grid", "elfouhaily_tail", "attach_tail",
           "surface_stokes_drift", "mean_square_slope"]


def extended_grid(grid: SpectralGrid, f_max: float = 20.0,
                  ratio: float = None) -> SpectralGrid:
    """Extend the frequency ladder past the native edge, same geometric ratio."""
    r = ratio or float(grid.f[1] / grid.f[0])
    n_extra = int(np.ceil(np.log(f_max / grid.f[-1]) / np.log(r)))
    extra = grid.f[-1] * r ** np.arange(1, n_extra + 1)
    return SpectralGrid(f=np.concatenate([grid.f, extra]), theta=grid.theta,
                        direction_convention=grid.direction_convention)


def elfouhaily_curvature(k: np.ndarray, u10: np.ndarray, omega_c: np.ndarray):
    """Full Elfouhaily B(k) = B_l + B_h, long plus short wave branches.

    Returns the curvature spectrum; S(k) = B(k)/k^3.
    """
    u10 = np.asarray(u10, float)
    omega_c = np.clip(np.asarray(omega_c, float), 0.84, 5.0)

    kp = G * omega_c ** 2 / np.maximum(u10, 0.1) ** 2
    c = np.sqrt(G / k * (1.0 + (k / K_M) ** 2))
    cp = np.sqrt(G / kp * (1.0 + (kp / K_M) ** 2))

    sk = np.sqrt(k / kp)
    L_pm = np.exp(-1.25 * (kp / k) ** 2)
    sigma = 0.08 * (1.0 + 4.0 / omega_c ** 3)
    Gam = np.exp(-((sk - 1.0) ** 2) / (2.0 * sigma ** 2))
    gam = np.where(omega_c <= 1.0, 1.7,
                   1.7 + 6.0 * np.log10(np.maximum(omega_c, 1e-3)))
    J_p = gam ** Gam
    F_p = L_pm * J_p * np.exp(-omega_c / np.sqrt(10.0) * (sk - 1.0))
    alpha_p = 0.006 * np.sqrt(omega_c)
    B_l = 0.5 * alpha_p * (cp / c) * F_p

    # Friction velocity via the Charnock-free drag law used in the paper.
    cd10 = 1e-3 * (0.8 + 0.065 * u10)
    ustar = np.sqrt(cd10) * u10
    alpha_m = np.where(ustar <= C_M,
                       1e-2 * (1.0 + np.log(np.maximum(ustar / C_M, 1e-6))),
                       1e-2 * (1.0 + 3.0 * np.log(np.maximum(ustar / C_M, 1e-6))))
    alpha_m = np.maximum(alpha_m, 0.0)
    F_m = L_pm * J_p * np.exp(-0.25 * (k / K_M - 1.0) ** 2)
    B_h = 0.5 * alpha_m * (C_M / c) * F_m

    return B_l + B_h


def elfouhaily_tail(f: np.ndarray, u10, omega_c):
    """Elfouhaily spectrum as a frequency spectrum, deep-water Jacobian."""
    k = (2.0 * np.pi * f) ** 2 / G
    S_k = elfouhaily_curvature(k, u10, omega_c) / k ** 3
    return S_k * (8.0 * np.pi ** 2 * f / G)


def attach_tail(E: np.ndarray, grid: SpectralGrid, u10, wind_dir_deg,
                omega_c=None, tp=None, f_join: float = None,
                spread_deg: float = 30.0, f_max: float = 20.0,
                mode: str = "auto", ratio_bounds=(0.2, 5.0)) -> dict:
    """Extend a reconstructed spectrum above the native grid edge.

    Parameters
    ----------
    E : (n_points, n_freq, n_dir) reconstruction on ``grid``
    u10 : (n_points,) wind speed, m/s
    wind_dir_deg : (n_points,) wind direction in the SAME convention as the
        spectrum's theta axis. Getting this wrong tilts the short-wave lobe.
    omega_c : inverse wave age. If None it is derived from ``tp`` and u10.
    tp : (n_points,) peak period, used only when omega_c is None.
    f_join : frequency at which to blend; defaults to the top native bin.
    mode : "continuity" scales Elfouhaily to join the reconstruction at the grid
        edge; "absolute" uses Elfouhaily's own wind-driven amplitude;
        "auto" (default) uses continuity where the join is well conditioned and
        falls back to absolute elsewhere.

    Why "auto" is the default: a pure-swell point has essentially no energy at
    0.95 Hz, so continuity matching scales the tail to zero. That is wrong --
    a real ocean under 10 m/s wind carries short waves whether or not swell is
    present, and those short waves are exactly what the extension is for.
    Points outside ``ratio_bounds`` are therefore given Elfouhaily's own
    amplitude instead, and flagged in ``used_absolute``.

    Returns dict with ``spectrum``, ``grid``, ``join_ratio`` and
    ``used_absolute``.
    """
    ext = extended_grid(grid, f_max=f_max)
    n_native = grid.n_freq
    u10 = np.atleast_1d(np.asarray(u10, float))

    if omega_c is None:
        if tp is None:
            raise ValueError("provide omega_c or tp")
        cp = G * np.asarray(tp, float) / (2.0 * np.pi)
        omega_c = np.clip(u10 / np.maximum(cp, 1e-3), 0.84, 5.0)
    omega_c = np.atleast_1d(np.asarray(omega_c, float))

    f_join = f_join or float(grid.f[-1])
    j = int(np.argmin(np.abs(grid.f - f_join)))

    Sf = elfouhaily_tail(ext.f[None, :], u10[:, None], omega_c[:, None])
    Sf = np.nan_to_num(Sf, nan=0.0, posinf=0.0, neginf=0.0)

    # Continuity scaling at the join. This absorbs any disagreement between the
    # reconstruction's fitted tail and Elfouhaily's -- see module docstring.
    Ef_rec = E.sum(axis=-1) * grid.dtheta
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(Sf[:, j] > 0, Ef_rec[:, j] / Sf[:, j], np.nan)

    lo, hi = ratio_bounds
    if mode == "continuity":
        used_absolute = np.zeros(u10.size, bool)
        scale = np.nan_to_num(ratio, nan=0.0)
    elif mode == "absolute":
        used_absolute = np.ones(u10.size, bool)
        scale = np.ones(u10.size)
    elif mode == "auto":
        ok = np.isfinite(ratio) & (ratio > lo) & (ratio < hi)
        used_absolute = ~ok
        scale = np.where(ok, np.nan_to_num(ratio, nan=1.0), 1.0)
    else:
        raise ValueError("mode must be 'continuity', 'absolute' or 'auto'")
    Sf = Sf * scale[:, None]

    # Short waves align with the wind, not with the swell partitions.
    s_exp = 2.0 / np.deg2rad(spread_deg) ** 2 - 1.0
    D = cos2s(ext.theta[None, :],
              np.deg2rad(np.atleast_1d(wind_dir_deg))[:, None],
              np.full((u10.size, 1), s_exp), ext.dtheta)

    out = np.zeros((E.shape[0], ext.n_freq, ext.n_dir))
    out[:, :n_native, :] = E
    out[:, n_native:, :] = Sf[:, n_native:, None] * D[:, None, :]
    return {"spectrum": out, "grid": ext, "join_ratio": ratio,
            "used_absolute": used_absolute, "omega_c": omega_c,
            "n_native": n_native}


def surface_stokes_drift(E: np.ndarray, grid: SpectralGrid) -> dict:
    """Deep-water surface Stokes drift vector from E(f, theta).

    us = 16 pi^3 / g * int int f^3 E(f,theta) (cos, sin) df dtheta

    The f^3 weighting is why the native-grid truncation matters: run this on
    both the truncated and tail-extended spectra to size the bias.
    """
    f, df, dth = grid.f, grid.df, grid.dtheta
    w = (16.0 * np.pi ** 3 / G) * f ** 3 * df
    ux = np.einsum("pft,f,t->p", E, w, np.cos(grid.theta)) * dth
    uy = np.einsum("pft,f,t->p", E, w, np.sin(grid.theta)) * dth
    return {"u": ux, "v": uy, "magnitude": np.hypot(ux, uy),
            "direction_deg": np.rad2deg(np.arctan2(uy, ux)) % 360.0}


def mean_square_slope(E: np.ndarray, grid: SpectralGrid) -> np.ndarray:
    """Total MSS = int int k^2 E df dtheta, deep water k = (2 pi f)^2 / g.

    Essentially meaningless on the truncated native grid -- MSS lives almost
    entirely above 0.95 Hz. Only use this after attach_tail.
    """
    k = (2.0 * np.pi * grid.f) ** 2 / G
    return np.einsum("pft,f->p", E, k ** 2 * grid.df) * grid.dtheta
