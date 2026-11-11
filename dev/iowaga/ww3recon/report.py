"""Plots and family-comparison statistics for the reconstruction validation."""

from __future__ import annotations

import numpy as np

from .core import (PartitionSet, ReconstructionConfig, Reconstructor,
                   SpectralGrid, bulk_parameters, directional_moments)
from .families import get_family
from .validate import compare, stratify

__all__ = ["family_sweep", "plot_site_report", "plot_family_comparison",
           "stats_table", "describe_config"]


def describe_config(result: dict, cfg: ReconstructionConfig = None,
                    mode: str = "") -> str:
    """Two-line description of the reconstruction setup, for figure footers.

    Every figure should say what spectral shapes and constraints produced it;
    a polar plot with no provenance is impossible to compare across runs.
    """
    cfg = cfg or ReconstructionConfig(windsea_family=result["ws_family"],
                                      swell_family=result["sw_family"])
    ws, sw = get_family(result["ws_family"]), get_family(result["sw_family"])
    wsp, swp = result["ws_param"], result["sw_param"]
    if ws.n_param > 1:
        ws_txt = (f"{ws.name} ({ws.param_name} fitted to T0M1, "
                  f"median {np.nanmedian(wsp):.2f}, prior {ws.param_prior})")
    else:
        ws_txt = f"{ws.name} (no free parameter)"
    sw_txt = (f"{sw.name} ({sw.param_name} fitted to T0M1, "
              f"median {np.nanmedian(swp):.2f}, prior {sw.param_prior})")
    te = np.asarray(result["tail_exponent"], float)
    if np.all(np.isnan(te)):
        tail = f"intrinsic to {ws.name}"
    elif cfg.fit_tail:
        tail = f"f^-n, n fitted to T02 (median {np.nanmedian(te):.1f})"
    else:
        tail = f"f^-n, n fixed at {np.nanmedian(te):.1f}"
    line1 = f"wind sea: {ws_txt}   |   swell: {sw_txt}   |   tail: {tail}"
    line2 = ("directional: cos-2s per partition, s from PSPR (Kuik a1 mapping), "
             f"wrapped across 0/360   |   PWS blend {cfg.sw_threshold}-{cfg.ws_threshold}"
             "   |   each partition renormalised to PHS, summed")
    if mode:
        line2 += f"   |   partitions: {mode}"
    return line1 + "\n" + line2

WS_FAMILIES = ["jonswap", "donelan", "elfouhaily", "pierson_moskowitz"]
SW_FAMILIES = ["gaussian", "ochi_hubble"]


def family_sweep(p: PartitionSet, E_true: np.ndarray, grid: SpectralGrid,
                 ws_families=None, sw_families=None, verbose: bool = True) -> dict:
    """Reconstruct with every family combination and score each against truth."""
    ws_families = ws_families or WS_FAMILIES
    sw_families = sw_families or SW_FAMILIES
    out = {}
    for ws in ws_families:
        for sw in sw_families:
            cfg = ReconstructionConfig(windsea_family=ws, swell_family=sw)
            rec = Reconstructor(grid, cfg)
            res = rec.reconstruct(p)
            m = compare(res["spectrum"], E_true, grid)
            out[(ws, sw)] = {"metrics": m, "result": res,
                             "spectrum": res["spectrum"],
                             "strata": stratify(p, res["spectrum"], E_true, grid)}
            if verbose:
                sc = m["shape"]["spectral_correlation"]
                print(f"  {ws:<18}{sw:<14}corr={sc['mean']:.4f} "
                      f"p10={sc['p10']:.4f}  "
                      f"Tm10 SI={m['integral']['tm10']['si']*100:5.2f}%")
    return out


def stats_table(sweep: dict, site: str = "") -> str:
    rows = [f"{'wind sea':<18}{'swell':<14}{'corr':>8}{'p10':>8}"
            f"{'L2':>8}{'Hs SI':>8}{'Tm10 SI':>9}{'a1 rmse':>9}"]
    rows.append("-" * 82)
    for (ws, sw), v in sorted(
            sweep.items(), key=lambda kv: -kv[1]["metrics"]["shape"]
            ["spectral_correlation"]["mean"]):
        m = v["metrics"]
        rows.append(
            f"{ws:<18}{sw:<14}"
            f"{m['shape']['spectral_correlation']['mean']:>8.4f}"
            f"{m['shape']['spectral_correlation']['p10']:>8.4f}"
            f"{m['shape']['normalised_l2']['mean']:>8.4f}"
            f"{m['integral']['hs']['si']*100:>7.2f}%"
            f"{m['integral']['tm10']['si']*100:>8.2f}%"
            f"{m['directional']['a1']['rmse']:>9.4f}")
    head = f"=== family sweep{' — ' + site if site else ''} ===\n"
    return head + "\n".join(rows)


def plot_site_report(E_true, E_rec, grid, p, site: str, outpath: str,
                     n_examples: int = 3, seed: int = 0, config_note: str = ""):
    """Six-panel diagnostic figure for one site.

    ``config_note`` (see ``describe_config``) is printed along the bottom so
    the figure records which shape families and constraints produced it.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bt = bulk_parameters(E_true, grid)
    br = bulk_parameters(E_rec, grid)
    dt_ = directional_moments(E_true, grid)
    dr = directional_moments(E_rec, grid)

    fig = plt.figure(figsize=(15, 11))
    fig.suptitle(f"Reconstruction vs IOWAGA truth spectra — {site}",
                 fontsize=13, y=0.98)

    # (1) 1D frequency spectra, mean and envelope
    ax = fig.add_subplot(3, 3, 1)
    et = (E_true.sum(axis=-1) * grid.dtheta)
    er = (E_rec.sum(axis=-1) * grid.dtheta)
    ax.loglog(grid.f, np.nanmean(et, 0), "k-", lw=2, label="truth")
    ax.loglog(grid.f, np.nanmean(er, 0), "r--", lw=2, label="reconstructed")
    ax.fill_between(grid.f, np.nanpercentile(et, 10, 0),
                    np.nanpercentile(et, 90, 0), color="k", alpha=0.15)
    ax.fill_between(grid.f, np.nanpercentile(er, 10, 0),
                    np.nanpercentile(er, 90, 0), color="r", alpha=0.15)
    # Clip the range: parametric shapes underflow to ~1e-300 in their far tails,
    # which otherwise sets the axis limits and flattens everything of interest.
    top = np.nanmax(np.nanmean(et, 0))
    ax.set_ylim(top * 1e-5, top * 3)
    ax.set_xlabel("f [Hz]"); ax.set_ylabel("E(f) [m² s]")
    ax.set_title("mean 1D spectrum (10–90% band)"); ax.legend(fontsize=8)

    # (2) relative error in E(f)
    ax = fig.add_subplot(3, 3, 2)
    # Mask per timestep against THAT timestep's peak, not the global max --
    # otherwise low-energy times are all "100% wrong" in their own tails and
    # the median is dominated by numerically-zero bins.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        thr = 1e-3 * np.nanmax(et, axis=1, keepdims=True)
        rel = np.where(et > thr, (er - et) / np.maximum(et, 1e-30), np.nan)
    rel = np.clip(rel, -1.5, 1.5)
    ax.semilogx(grid.f, np.nanmedian(rel, 0) * 100, "b-", lw=2)
    ax.fill_between(grid.f, np.nanpercentile(rel, 25, 0) * 100,
                    np.nanpercentile(rel, 75, 0) * 100, alpha=0.25)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("f [Hz]"); ax.set_ylabel("relative error [%]")
    ax.set_title("E(f) error by frequency (median, IQR)")

    # (3) bulk parameter scatter
    ax = fig.add_subplot(3, 3, 3)
    for k, c, lab in (("hs", "k", "Hs"), ("tm10", "r", "Tm-10"),
                      ("tm02", "b", "Tm02")):
        x, y = bt[k], br[k]
        ok = np.isfinite(x) & np.isfinite(y)
        ax.scatter(x[ok] / np.nanmean(x[ok]), y[ok] / np.nanmean(x[ok]),
                   s=6, alpha=0.4, c=c, label=lab)
    lim = ax.get_xlim()
    ax.plot(lim, lim, "k--", lw=0.8)
    ax.set_xlabel("truth (normalised)"); ax.set_ylabel("reconstructed")
    ax.set_title("bulk parameters"); ax.legend(fontsize=8)

    # (4,5) directional coefficients vs frequency
    for n, (k1, k2) in enumerate((("a1", "b1"), ("a2", "b2"))):
        ax = fig.add_subplot(3, 3, 4 + n)
        for k, c in ((k1, "C0"), (k2, "C1")):
            ax.semilogx(grid.f, np.nanmean(dt_[k], 0), "-", color=c, lw=2,
                        label=f"{k} truth")
            ax.semilogx(grid.f, np.nanmean(dr[k], 0), "--", color=c, lw=2,
                        label=f"{k} recon")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xlabel("f [Hz]"); ax.set_ylabel("coefficient")
        ax.set_title(f"directional moments {k1}/{k2}")
        ax.legend(fontsize=7)

    # (6) spectral correlation histogram
    ax = fig.add_subplot(3, 3, 6)
    m = compare(E_rec, E_true, grid)
    corr = m["_per_point"]["corr"]
    ax.hist(corr[np.isfinite(corr)], bins=40, color="steelblue")
    ax.axvline(np.nanmedian(corr), color="r", lw=2,
               label=f"median {np.nanmedian(corr):.3f}")
    ax.set_xlabel("spectral correlation"); ax.set_ylabel("count")
    ax.set_title("per-time correlation"); ax.legend(fontsize=8)

    # (7-9) example polar spectra: best, median, worst
    rank = np.argsort(np.nan_to_num(corr, nan=-1))
    picks = [("worst", rank[0]), ("median", rank[len(rank) // 2]),
             ("best", rank[-1])]
    # Wrap the first direction column round to theta + 2pi so the contours
    # close across the 0/360 seam instead of leaving an unfilled wedge.
    thw = np.concatenate([grid.theta, grid.theta[:1] + 2 * np.pi])
    TH, F = np.meshgrid(thw, grid.f)
    wrap = lambda A: np.concatenate([A, A[:, :1]], axis=1)
    for n, (lab, i) in enumerate(picks):
        ax = fig.add_subplot(3, 3, 7 + n, projection="polar")
        vmax = max(E_true[i].max(), E_rec[i].max())
        # Levels as fractions of this case's own peak, so a low-energy "worst"
        # case is as legible as a high-energy "best" one.
        lv = vmax * np.array([0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.9])
        ax.contour(TH, F, wrap(E_true[i]), levels=lv, colors="k", linewidths=1.0)
        ax.contour(TH, F, wrap(E_rec[i]), levels=lv, colors="r", linewidths=1.0,
                   linestyles="--")
        # Radial limit from where the energy actually is.
        ef = E_true[i].sum(axis=1)
        cum = np.cumsum(ef * grid.df) / max((ef * grid.df).sum(), 1e-30)
        fmax = grid.f[min(int(np.searchsorted(cum, 0.98)) + 1, grid.n_freq - 1)]
        ax.set_ylim(0, min(max(fmax, 3 * grid.f[0]), 0.40))
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
        ax.set_title(f"{lab} (corr={corr[i]:.3f})\nblack=truth red=recon",
                     fontsize=8)

    bottom = 0.0
    if config_note:
        fig.text(0.01, 0.006, config_note, fontsize=7.5, color="0.25",
                 ha="left", va="bottom", family="monospace")
        bottom = 0.045
    fig.tight_layout(rect=[0, bottom, 1, 0.96])
    fig.savefig(outpath, dpi=130)
    plt.close(fig)
    return outpath


def plot_family_comparison(sweep: dict, E_true, grid, site: str, outpath: str,
                           config_note: str = ""):
    """Family ranking plus where in frequency each family goes wrong."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    fig.suptitle(f"Shape family comparison — {site}", fontsize=13)

    keys = sorted(sweep, key=lambda k: -sweep[k]["metrics"]["shape"]
                  ["spectral_correlation"]["mean"])
    labels = [f"{a}\n+{b}" for a, b in keys]
    corr = [sweep[k]["metrics"]["shape"]["spectral_correlation"]["mean"] for k in keys]
    p10 = [sweep[k]["metrics"]["shape"]["spectral_correlation"]["p10"] for k in keys]

    ax = axes[0]
    x = np.arange(len(keys))
    ax.bar(x - 0.2, corr, 0.4, label="mean")
    ax.bar(x + 0.2, p10, 0.4, label="p10")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("spectral correlation")
    ax.set_ylim(min(p10) - 0.05, 1.0)
    ax.set_title("overall skill"); ax.legend(fontsize=8)

    ax = axes[1]
    et = E_true.sum(axis=-1) * grid.dtheta
    thr = 1e-3 * np.nanmax(et, axis=1, keepdims=True)
    for k in keys[:4]:
        er = sweep[k]["spectrum"].sum(axis=-1) * grid.dtheta
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            rel = np.where(et > thr, (er - et) / np.maximum(et, 1e-30), np.nan)
        rel = np.clip(rel, -1.5, 1.5)
        ax.semilogx(grid.f, np.nanmedian(rel, 0) * 100, lw=2,
                    label=f"{k[0]}+{k[1]}")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("f [Hz]"); ax.set_ylabel("median relative error [%]")
    ax.set_title("where each family goes wrong"); ax.legend(fontsize=7)

    ax = axes[2]
    strata = ["unimodal", "two_partitions", "three_plus", "crossing_seas",
              "pure_swell", "pure_windsea"]
    for k in keys[:4]:
        s = sweep[k]["strata"]
        vals = [s[n]["shape"]["spectral_correlation"]["mean"] if n in s else np.nan
                for n in strata]
        ax.plot(range(len(strata)), vals, "o-", label=f"{k[0]}+{k[1]}")
    ax.set_xticks(range(len(strata)))
    ax.set_xticklabels(strata, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("spectral correlation")
    ax.set_title("skill by stratum"); ax.legend(fontsize=7)

    bottom = 0.0
    if config_note:
        fig.text(0.01, 0.008, config_note, fontsize=7.5, color="0.25",
                 ha="left", va="bottom", family="monospace")
        bottom = 0.09
    fig.tight_layout(rect=[0, bottom, 1, 0.93])
    fig.savefig(outpath, dpi=130)
    plt.close(fig)
    return outpath
