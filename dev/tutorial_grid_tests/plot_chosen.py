"""Plot the chosen alaska_big design on its own, at a size worth looking at.

Traces only the domain boundary rather than building a mesh, so it renders in
seconds and can be re-run freely while the anchors are still being argued about.
`alaska_small` is drawn from its written supergrid if one exists.
"""

import os

import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xarray as xr

import omerc_swath as osw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(HERE, "alaska_big_chosen.png")
SMALL_NC = os.path.join(HERE, "alaska_grids", "alaska_small", "ocean_hgrid.nc")

SW_ANCHOR = (51.00, 156.80)     # southern tip of Kamchatka
SE_ANCHOR = (45.00, -123.85)    # Oregon coast, just south of Washington
CONTROL = (48.00, -160.00)      # southern edge passes through here
STRAIT = (65.80, -169.00)
NORTH_MARGIN_M = 500e3

LANDMARKS = {
    "Cape Lopatka": (50.86, 156.66),
    "Adak": (51.88, -176.65),
    "Kodiak": (57.79, -152.41),
    "Prince William Sd": (60.30, -147.00),
    "Yakutat": (59.55, -139.73),
    "Vancouver BC": (49.28, -123.12),
    "Anchorage": (61.22, -149.90),
    "Bering Strait": (65.80, -169.00),
}


def main():
    res_m = osw.resolution_m_for(0.1, 45.0, 75.0)
    crs, info = osw.frame_through(SW_ANCHOR, SE_ANCHOR, CONTROL)
    box = osw.box_for(crs, SW_ANCHOR, SE_ANCHOR, STRAIT, NORTH_MARGIN_M)
    lon, lat, (slon, slat), corners = osw.box_outline(
        crs, box["x_min"], box["x_max"], box["y_min"], box["y_max"])
    k, _ = osw.scale_spread(crs, lon, lat)
    nx = int((box["x_max"] - box["x_min"]) / res_m)
    ny = int((box["y_max"] - box["y_min"]) / res_m)
    coast = osw.southern_coast_lat(-155.0)
    gap = (coast - osw.south_edge_at(slon, slat, -155.0)) * 111.32
    print(f"{nx} x {ny} cells, k {k:.3f}, open water under Alaska {gap:.0f} km")

    fig = plt.figure(figsize=(16, 11))
    ax = fig.add_subplot(
        1, 1, 1, projection=ccrs.NorthPolarStereo(central_longitude=-175))
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "land", "10m"),
                   facecolor="0.85", edgecolor="none", zorder=0)
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "ocean", "10m"),
                   facecolor="#dbe9f4", edgecolor="none", zorder=-1)
    ax.coastlines(resolution="10m", linewidth=0.6, zorder=3)
    ax.gridlines(linewidth=0.4, color="0.6")
    ax.set_extent([135, 245, 36, 78], crs=ccrs.PlateCarree())

    ax.plot(lon, lat, transform=ccrs.Geodetic(), color="crimson", lw=3.0,
            zorder=5, label="alaska_big")
    ax.fill(lon, lat, transform=ccrs.Geodetic(), color="crimson", alpha=0.10,
            zorder=1)

    if os.path.exists(SMALL_NC):
        with xr.open_dataset(SMALL_NC) as ds:
            sx = np.asarray(ds.x)
            sy = np.asarray(ds.y)
        edge_lon = np.concatenate([sx[0, :], sx[:, -1], sx[-1, ::-1], sx[::-1, 0]])
        edge_lat = np.concatenate([sy[0, :], sy[:, -1], sy[-1, ::-1], sy[::-1, 0]])
        ax.plot(edge_lon, edge_lat, transform=ccrs.Geodetic(), color="darkblue",
                lw=2.2, zorder=6, label="alaska_small")

    for nm, (lo, la) in zip(["SW", "SE", "NW", "NE"], corners):
        l180 = ((lo + 180) % 360) - 180
        ax.plot(l180, la, transform=ccrs.PlateCarree(), marker="o", ms=13,
                mfc="lime" if osw.is_land(lo, la) else "red", mec="black",
                mew=1.0, zorder=8)
        ax.text(l180, la - 1.4, f"{nm}\n{abs(l180):.1f}{'E' if l180 > 0 else 'W'}, "
                f"{la:.1f}N", transform=ccrs.PlateCarree(), ha="center",
                va="top", fontsize=9, zorder=9,
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.5))

    for nm, (la, lo) in LANDMARKS.items():
        ax.plot(lo, la, transform=ccrs.PlateCarree(), marker="*", ms=13,
                color="darkgreen", mec="black", mew=0.4, zorder=7)
        ax.text(lo, la + 0.6, nm, transform=ccrs.PlateCarree(), ha="center",
                fontsize=8.5, zorder=9,
                bbox=dict(fc="white", ec="none", alpha=0.7, pad=1.2))

    ax.plot(CONTROL[1], CONTROL[0], transform=ccrs.PlateCarree(), marker="X",
            ms=14, color="orangered", mec="black", mew=0.8, zorder=8)
    ax.text(CONTROL[1], CONTROL[0] - 1.4,
            f"control point\n{abs(CONTROL[1]):.0f}W, {CONTROL[0]:.0f}N",
            transform=ccrs.PlateCarree(), ha="center", va="top", fontsize=9,
            zorder=9, bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.5))

    ax.legend(loc="lower left", fontsize=11)
    ax.set_title(
        f"alaska_big — oblique Mercator swath, {nx} x {ny} cells "
        f"({nx * ny / 1e6:.2f} M) at ~1/10 deg\n"
        f"SW southern Kamchatka, SE Oregon coast, north edge past the Bering "
        f"Strait; {gap:.0f} km of open water under Alaska, k spread {k:.3f}",
        fontsize=13)
    fig.savefig(OUT_PNG, dpi=110, bbox_inches="tight")
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
