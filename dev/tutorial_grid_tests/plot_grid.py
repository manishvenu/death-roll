"""Quick-look plot of a CrocoDash/mom6_forge Grid over coastlines."""

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def plot_grid(grid, resolution="10m", gridlines=20, zoom=0.4, figsize=(9, 6)):
    lon0 = float(grid.tlon.values.mean())
    crs = ccrs.PlateCarree(central_longitude=lon0)

    # shift lons into [-180, 180) about lon0 so [0, 360] / dateline domains stay contiguous
    x = ((np.asarray(grid.qlon) - lon0 + 180.0) % 360.0) - 180.0
    y = np.asarray(grid.qlat)

    ax = plt.figure(figsize=figsize).add_subplot(1, 1, 1, projection=crs)
    ax.add_feature(cfeature.LAND.with_scale(resolution), facecolor="0.85")
    ax.add_feature(cfeature.OCEAN.with_scale(resolution), facecolor="#dff0f7")
    ax.coastlines(resolution=resolution, lw=0.8)

    if gridlines:
        for j in range(0, x.shape[0], gridlines):
            ax.plot(x[j, :], y[j, :], transform=crs, color="k", lw=0.3, alpha=0.5)
        for i in range(0, x.shape[1], gridlines):
            ax.plot(x[:, i], y[:, i], transform=crs, color="k", lw=0.3, alpha=0.5)

    perim_x = np.concatenate([x[0, :], x[:, -1], x[-1, ::-1], x[::-1, 0]])
    perim_y = np.concatenate([y[0, :], y[:, -1], y[-1, ::-1], y[::-1, 0]])
    ax.plot(perim_x, perim_y, transform=crs, color="red", lw=2)

    # explicit ticks: cartopy's auto-locator drops labels when central_longitude != 0
    def _ticks(lo, hi):
        raw = (hi - lo) / 6
        step = min([0.1, 0.2, 0.5, 1, 2, 5, 10, 20], key=lambda s: abs(s - raw))
        return np.arange(np.floor(lo / step) * step, hi + step, step)

    tlon = ((np.asarray(grid.tlon) + 180.0) % 360.0) - 180.0  # true lon in [-180, 180)
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        xlocs=_ticks(tlon.min(), tlon.max()),
        ylocs=_ticks(y.min(), y.max()),
        lw=0.5,
        color="gray",
        alpha=0.5,
        linestyle="--",
    )
    gl.top_labels = gl.right_labels = False

    padx, pady = zoom * np.ptp(x), zoom * np.ptp(y)
    ax.set_extent(
        [x.min() - padx, x.max() + padx, y.min() - pady, y.max() + pady], crs=crs
    )
    ax.set_title(f"{grid.name}  ({grid.nx} x {grid.ny})")
    return ax
