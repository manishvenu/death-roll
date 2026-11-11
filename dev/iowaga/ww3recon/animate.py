"""
Side-by-side truth vs reconstructed 2D spectra, as stills or as an animation.

Design notes, because the defaults here are deliberate:

* Colour scale is LOG and SHARED between the two panels and across all frames.
  Wave spectra span several decades within a single snapshot, and Hs at a storm
  site varies by a factor of ~6 over a month. A per-frame linear scale would
  make every frame look equally energetic and hide the storm entirely; a shared
  log scale shows the energy evolution that is the point of watching a month go
  by. The trade-off is that low-energy frames look sparse, which is honest.

* Polar axes use compass orientation (N at top, clockwise). The IOWAGA spec
  direction axis is "sea surface wave TO direction" in nautical degrees, so
  these plots read as "where the waves are going". Arrows for wind and mean
  direction are drawn in the same frame.

* The bottom strip carries Hs and per-frame spectral correlation with a moving
  cursor, so a bad frame can be placed in its context rather than judged alone.
"""

from __future__ import annotations

import os

import numpy as np

from .core import SpectralGrid, bulk_parameters

__all__ = ["plot_spectrum_pair", "animate_month"]

_FLOOR_DECADES = 4.0          # decades below the month maximum to show


def _reflow(label, width=100):
    """Re-pack a ' | '-separated config label into lines of at most ``width``."""
    pieces = [p.strip() for line in label.split("\n") for p in line.split("|")]
    lines, cur = [], ""
    for p in pieces:
        if not p:
            continue
        cand = p if not cur else cur + "  |  " + p
        if len(cand) <= width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = p
    if cur:
        lines.append(cur)
    return lines


def _levels(vmax, n=14):
    top = np.log10(max(vmax, 1e-12))
    return np.linspace(top - _FLOOR_DECADES, top, n)


def _polar(ax, grid, E, levels, title, cmap="viridis"):
    # Wrap the first direction column round to theta + 2pi, otherwise contourf
    # leaves an un-filled wedge between the last and first bin.
    th = np.concatenate([grid.theta, grid.theta[:1] + 2 * np.pi])
    Ew = np.concatenate([E, E[:, :1]], axis=1)
    TH, F = np.meshgrid(th, grid.f)
    with np.errstate(divide="ignore"):
        Z = np.log10(np.maximum(Ew, 1e-30))
    cs = ax.contourf(TH, F, Z, levels=levels, cmap=cmap, extend="both")
    ax.contour(TH, F, Z, levels=levels[::3], colors="k", linewidths=0.35,
               alpha=0.5)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 0.32)
    ax.set_yticks([0.1, 0.2, 0.3])
    ax.set_yticklabels(["10s", "5s", "3.3s"], fontsize=7, color="0.25")
    ax.set_xticks(np.deg2rad([0, 90, 180, 270]))
    ax.set_xticklabels(["N", "E", "S", "W"], fontsize=9)
    ax.grid(color="0.6", lw=0.4, alpha=0.7)
    ax.set_title(title, fontsize=11, pad=12)
    return cs


def _arrows(ax, mean_dir_rad, wind_dir_rad=None):
    ax.annotate("", xy=(mean_dir_rad, 0.30), xytext=(mean_dir_rad, 0.0),
                arrowprops=dict(arrowstyle="->", color="crimson", lw=1.8,
                                alpha=0.9))
    if wind_dir_rad is not None:
        ax.annotate("", xy=(wind_dir_rad, 0.30), xytext=(wind_dir_rad, 0.0),
                    arrowprops=dict(arrowstyle="->", color="white", lw=1.4,
                                    alpha=0.85, linestyle=(0, (3, 2))))


def plot_spectrum_pair(E_true, E_rec, grid: SpectralGrid, i: int, outpath=None,
                       site="", stamp="", wind=None, wind_dir_rad=None,
                       vmax=None, fig=None, config_label=None, result=None):
    """One frame: truth and reconstruction side by side, plus E(f) and context.

    Returns the matplotlib figure. Pass ``fig`` to reuse one across frames.

    ``config_label`` (str, see ``report.describe_config``) is printed in the
    bottom-right so every still and every video frame records which shape
    families and constraints produced it. ``result`` (the dict returned by
    ``Reconstructor.reconstruct``) adds this frame's fitted parameters.
    """
    import matplotlib
    if outpath is not None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    vmax = vmax if vmax is not None else max(E_true.max(), E_rec.max())
    lv = _levels(vmax)

    if fig is None:
        fig = plt.figure(figsize=(13, 6.2))
    else:
        fig.clf()

    gs = fig.add_gridspec(2, 3, height_ratios=[3.0, 1.0],
                          width_ratios=[1, 1, 0.95],
                          hspace=0.34, wspace=0.28,
                          left=0.05, right=0.97, top=0.80, bottom=0.165)

    bt = bulk_parameters(E_true[None, i], grid)
    br = bulk_parameters(E_rec[None, i], grid)
    a = E_true[i] * grid.df[:, None] * grid.dtheta
    thb = np.arctan2((a * np.sin(grid.theta)).sum(), (a * np.cos(grid.theta)).sum())

    ax1 = fig.add_subplot(gs[0, 0], projection="polar")
    cs = _polar(ax1, grid, E_true[i], lv, "IOWAGA virtual station")
    _arrows(ax1, thb, wind_dir_rad)

    ax2 = fig.add_subplot(gs[0, 1], projection="polar")
    _polar(ax2, grid, E_rec[i], lv, "Reconstructed from partitions")
    _arrows(ax2, thb, wind_dir_rad)

    # 1D spectra
    ax3 = fig.add_subplot(gs[0, 2])
    et = E_true[i].sum(axis=-1) * grid.dtheta
    er = E_rec[i].sum(axis=-1) * grid.dtheta
    ax3.loglog(grid.f, et, "k-", lw=2, label="station")
    ax3.loglog(grid.f, er, "r--", lw=2, label="reconstructed")
    top = max(et.max(), er.max())
    ax3.set_ylim(top * 10 ** -_FLOOR_DECADES, top * 3)
    ax3.set_xlabel("f [Hz]", fontsize=9)
    ax3.set_ylabel("E(f) [m² s]", fontsize=9)
    ax3.tick_params(labelsize=8)
    ax3.legend(fontsize=8, loc="lower left")
    ax3.grid(alpha=0.3, which="both", lw=0.4)
    ax3.set_title("1D spectrum", fontsize=10)

    # context strip
    ax4 = fig.add_subplot(gs[1, :])
    hs_t = 4 * np.sqrt(np.maximum(
        (E_true * grid.df[None, :, None]).sum(axis=(1, 2)) * grid.dtheta, 0))
    t = np.arange(hs_t.size)
    ax4.plot(t, hs_t, color="0.3", lw=1.2)
    ax4.fill_between(t, 0, hs_t, color="0.8", alpha=0.6)
    ax4.axvline(i, color="crimson", lw=1.8)
    ax4.set_xlim(0, hs_t.size - 1)
    ax4.set_ylim(0, hs_t.max() * 1.12)
    ax4.set_ylabel("Hs [m]", fontsize=9)
    # No xlabel: the colourbar sits directly below this axis and the two collide.
    ax4.tick_params(labelsize=8)
    ax4.annotate("3-hourly steps", xy=(0.995, 0.88), xycoords="axes fraction",
                 ha="right", va="top", fontsize=8, color="0.35")
    ax4.grid(alpha=0.3, lw=0.4)

    if wind is not None:
        axw = ax4.twinx()
        axw.plot(t, wind, color="steelblue", lw=0.9, alpha=0.75)
        axw.set_ylabel("U10 [m/s]", fontsize=9, color="steelblue")
        axw.tick_params(labelsize=8, colors="steelblue")
        axw.set_ylim(0, max(np.nanmax(wind) * 1.15, 1))

    w = grid.df[:, None] * grid.dtheta
    num = (E_true[i] * E_rec[i] * w).sum()
    den = np.sqrt((E_true[i] ** 2 * w).sum() * (E_rec[i] ** 2 * w).sum())
    corr = num / den if den > 0 else np.nan

    fig.suptitle(
        f"{site}   {stamp}\n"
        f"Hs {bt['hs'][0]:.2f} m (recon {br['hs'][0]:.2f})   "
        f"Tm-10 {bt['tm10'][0]:.1f} s (recon {br['tm10'][0]:.1f})   "
        f"spectral corr {corr:.3f}",
        fontsize=12, y=0.975)

    cax = fig.add_axes([0.05, 0.075, 0.40, 0.016])
    cb = fig.colorbar(cs, cax=cax, orientation="horizontal")
    cb.set_label("log10 E(f, theta)  [m2 s rad-1]", fontsize=8)
    cb.set_ticks(lv[::3])
    cb.ax.set_xticklabels([f"{v:.1f}" for v in lv[::3]], fontsize=7)

    foot = []
    if result is not None:
        te = result["tail_exponent"][i]
        foot.append(
            f"this frame: {result['ws_param_name']}={result['ws_param'][i]:.2f}  "
            f"{result['sw_param_name']}={result['sw_param'][i]:.2f}  "
            f"tail n={'intrinsic' if np.isnan(te) else f'{te:.1f}'}  "
            f"partitions={int(result['n_partitions'][i])}")
    if config_label:
        foot += _reflow(config_label)
    if foot:
        # Right half only: the colourbar owns the bottom-left corner.
        fig.text(0.50, 0.012, "\n".join(foot), fontsize=6.4, color="0.3",
                 ha="left", va="bottom", family="monospace", linespacing=1.3)

    if outpath:
        fig.savefig(outpath, dpi=120)
    return fig


def animate_month(E_true, E_rec, grid: SpectralGrid, outpath, site="",
                  times=None, wind=None, wind_dir_rad=None, fps=8,
                  dpi=100, stride=1, verbose=True, config_label=None,
                  result=None):
    """Write an mp4 (or .gif) stepping through every timestep.

    ``vmax`` is taken once over the whole month so frames are comparable -- see
    the module docstring for why that matters.

    Needs ffmpeg on PATH for mp4. If it is missing, pass an outpath ending in
    .gif and PillowWriter is used instead (bigger file, no external dependency).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter, PillowWriter

    idx = np.arange(0, E_true.shape[0], stride)
    vmax = float(max(E_true.max(), E_rec.max()))

    if str(outpath).lower().endswith(".gif"):
        writer = PillowWriter(fps=fps)
    else:
        writer = FFMpegWriter(fps=fps, bitrate=2600,
                              metadata={"title": f"{site} spectrum reconstruction"})

    fig = plt.figure(figsize=(13, 6.2))
    os.makedirs(os.path.dirname(os.path.abspath(outpath)) or ".", exist_ok=True)
    with writer.saving(fig, str(outpath), dpi):
        for n, i in enumerate(idx):
            stamp = times[i] if times is not None else f"step {i:3d}"
            plot_spectrum_pair(E_true, E_rec, grid, int(i), outpath=None,
                               site=site, stamp=str(stamp),
                               wind=wind, wind_dir_rad=(
                                   None if wind_dir_rad is None
                                   else float(wind_dir_rad[i])),
                               vmax=vmax, fig=fig, config_label=config_label,
                               result=result)
            writer.grab_frame()
            if verbose and n % 40 == 0:
                print(f"    frame {n+1}/{idx.size}")
    plt.close(fig)
    return outpath
