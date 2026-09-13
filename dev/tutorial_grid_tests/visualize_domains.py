"""Visualise alaska_big: corners pinned, southern edge steered by a third point.

Specification
-------------
    SW corner   top of the Kamchatka peninsula
    SE corner   North America near Washington
    north edge  high enough to clear the Bering Strait
    plus        a huge open section under Alaska

Why the corners alone are not enough
------------------------------------
Two corners fix the ends of the southern edge but say nothing about the curve
between them, and at these latitudes that curve is the whole domain. The
geodesic joining the anchors bulges poleward to 59.2 N, 154.3 W -- on the Alaska
Peninsula -- so a southern edge along it runs hard against the Alaskan coast,
putting Kodiak and Adak outside the domain and leaving no open water underneath.

Steering the edge
-----------------
In an oblique Mercator, lines of constant y are small circles sharing an axis
with the central great circle, so the southern edge is always a small circle
through the two anchors. Three points determine a circle, so add a third control
point out in the North Pacific under the Alaska Peninsula and the edge is fully
determined -- no rotation or offset knob to grope at:

    n = norm((B - A) x (T - A))        axis of the circle through A, B, T
    central line = the great circle with pole n
    d = R * asin(n . A)                common distance of A, B, T from it

Because A, B and T are all equidistant from the central line, they land on one
line of constant y, which becomes the southern edge exactly. The knob is then
the one that actually matters: how far south the edge dips under Alaska.

The central line, where the oblique Mercator's scale factor is exactly 1, sits
inside the domain, so distortion grows outward from it and stays bounded.

Projection traps, both found the hard way
-----------------------------------------
  `+no_rot`  puts the anchors on the axis but makes pyproj's get_factors return
             inf almost everywhere. mom6_forge's from_projection divides the
             projected-plane spacing by that scale factor, so dx and dy come out
             exactly zero over ~90% of the grid -- silently: no NaN, no warning,
             and cell area still looks right because area is derived from
             lon/lat rather than from the metrics.
  gamma      controls the rectification rotation, and `gamma = alpha` only
             happens to put the anchors on the x-axis when alpha is near 90; at
             alpha = 109 it left them 2000 km off it. So gamma is solved for
             numerically instead: changing it rotates the projected plane about
             the origin, so measuring the anchors' tilt once gives it directly.

Run
---
    python visualize_domains.py            # writes domain_candidates.png
"""

import os

import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pyproj import Proj, Transformer
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.prepared import prep

R_EARTH = 6_371_008.8
OUT_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "domain_candidates.png")

# ---------------------------------------------------------------- land mask
_p = shpreader.natural_earth(resolution="10m", category="physical", name="land")
LAND = prep(unary_union(list(shpreader.Reader(_p).geometries())))


def is_land(lon, lat):
    return LAND.contains(Point(((float(lon) + 180) % 360) - 180, float(lat)))


# ------------------------------------------------------- anchors and control
SW_ANCHOR = (51.00, 156.80)     # southern tip of Kamchatka
STRAIT = (65.80, -169.00)
NORTH_MARGIN_M = 500e3          # how far past the strait the north edge sits

# The third point steering the southern edge, out in the open Pacific beneath
# the Alaska Peninsula. Held fixed here so the only thing varying is the SE
# corner.
CONTROL = (48.0, -160.0)

# How far the SE corner runs down the North American coast. Each is a land point
# just inland of the shoreline at that latitude.
SE_OPTIONS = {
    "N Washington 47.6N": (47.60, -124.20),
    "S Washington 46.3N": (46.30, -123.60),   # Columbia River, the state line
    "Oregon 45.0N": (45.00, -123.85),
    "Cape Blanco 42.8N": (42.80, -124.35),
    "C Mendocino 40.4N": (40.40, -124.20),
    "Point Reyes 38.0N": (38.00, -122.85),
}

CHECKS = {
    "Bering Strait": STRAIT,
    "Anchorage": (61.22, -149.90),
    "GoA: Prince William Sd": (60.30, -147.00),
    "GoA: Yakutat": (59.55, -139.73),
    "GoA: Kodiak": (57.79, -152.41),
    "Aleutians: Adak": (51.88, -176.65),
    "Vancouver BC": (49.28, -123.12),
}

PROBE_LONS = [175.0, -175.0, -165.0, -155.0, -145.0, -135.0]

# Longitude at which "how much open water is there under Alaska" is measured.
GAP_LON = -155.0


def southern_coast_lat(lon, lo=40.0, hi=63.0, step=0.05):
    """Southernmost latitude of land at this longitude -- Alaska's outer edge."""
    lats = np.arange(hi, lo, -step)
    land = [la for la in lats if is_land(lon, la)]
    return float(min(land)) if land else float("nan")


# ------------------------------------------------------------ sphere helpers
def to_xyz(lat, lon):
    p, l = np.deg2rad(lat), np.deg2rad(lon)
    return np.array([np.cos(p) * np.cos(l), np.cos(p) * np.sin(l), np.sin(p)])


def to_ll(v):
    v = v / np.linalg.norm(v)
    return (float(np.rad2deg(np.arcsin(v[2]))),
            float(np.rad2deg(np.arctan2(v[1], v[0]))))


def norm(v):
    return v / np.linalg.norm(v)


def azimuth_of(direction, lat, lon):
    """Azimuth (deg clockwise from north) of a tangent vector at (lat, lon)."""
    p, l = np.deg2rad(lat), np.deg2rad(lon)
    east = np.array([-np.sin(l), np.cos(l), 0.0])
    north = np.array([-np.sin(p) * np.cos(l), -np.sin(p) * np.sin(l), np.cos(p)])
    return float(np.rad2deg(np.arctan2(direction @ east, direction @ north)))


def omerc_crs(lat_0, lonc, alpha, gamma):
    return (f"+proj=omerc +lat_0={lat_0} +lonc={lonc} +alpha={alpha} "
            f"+gamma={gamma} +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")


def solve_gamma(lat_0, lonc, alpha, A_ll, B_ll):
    """gamma that puts both anchors on a common line of constant y.

    Changing gamma rotates the projected plane about the origin, so measuring
    the anchors' tilt at one gamma gives the correction directly. Both signs are
    tried because the direction of that rotation is a PROJ convention.
    """
    def tilt(g):
        f = Transformer.from_crs("EPSG:4326", omerc_crs(lat_0, lonc, alpha, g),
                                 always_xy=True)
        xa, ya = f.transform(A_ll[1], A_ll[0])
        xb, yb = f.transform(B_ll[1], B_ll[0])
        if not np.isfinite([xa, ya, xb, yb]).all():
            return None, None
        return float(np.rad2deg(np.arctan2(yb - ya, xb - xa))), abs(yb - ya)

    t0, _ = tilt(alpha)
    if t0 is None:
        return None
    best = None
    for sign in (-1.0, 1.0):
        gi = alpha + sign * t0
        for _ in range(5):
            ti, resid = tilt(gi)
            if ti is None:
                break
            if best is None or resid < best[1]:
                best = (gi, resid)
            if resid < 1.0:
                break
            gi = gi + sign * ti
    return None if best is None else best[0]


def frame_through(A_ll, B_ll, T_ll):
    """Oblique Mercator whose constant-y line through A also passes B and T."""
    A, B, T = to_xyz(*A_ll), to_xyz(*B_ll), to_xyz(*T_ll)
    n = np.cross(B - A, T - A)
    if np.linalg.norm(n) < 1e-12:
        return None
    n = norm(n)
    if n @ A < 0:                       # orient the axis so the anchors sit south
        n = -n
    d = R_EARTH * float(np.arcsin(np.clip(n @ A, -1, 1)))
    C = norm(T - (n @ T) * n)           # point on the central line above the control
    lat_c, lon_c = to_ll(C)
    tang = norm(np.cross(n, C))
    if tang @ (B - A) < 0:              # aim it from A toward B
        tang = -tang
    alpha = azimuth_of(tang, lat_c, lon_c)
    gamma = solve_gamma(lat_c, lon_c, alpha, A_ll, B_ll)
    if gamma is None:
        return None
    return d, lat_c, lon_c, alpha, gamma


# --------------------------------------------------------------- evaluation
def box_outline(crs, x0, x1, y0, y1, n=400):
    inv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    xs = np.linspace(x0, x1, n)
    ys = np.linspace(y0, y1, n)
    x = np.concatenate([xs, np.full(n, x1), xs[::-1], np.full(n, x0)])
    y = np.concatenate([np.full(n, y0), ys, np.full(n, y1), ys[::-1]])
    lon, lat = inv.transform(x, y)
    slon, slat = inv.transform(xs, np.full(n, y0))
    clon, clat = inv.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
    return lon, lat, (slon, slat), list(zip(clon, clat))


def south_edge_at(slon, slat, want_lon):
    l180 = ((np.asarray(slon) + 180) % 360) - 180
    dl = np.abs(((l180 - want_lon + 180) % 360) - 180)
    i = int(np.argmin(dl))
    return float(slat[i]) if dl[i] < 4.0 else float("nan")


def evaluate(crs, x0, x1, y0, y1, res_m):
    fwd = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    inside = {}
    for nm, (la, lo) in CHECKS.items():
        px, py = fwd.transform(lo, la)
        inside[nm] = bool(x0 <= px <= x1 and y0 <= py <= y1)
    lon, lat, (slon, slat), corners = box_outline(crs, x0, x1, y0, y1)
    south = {wl: south_edge_at(slon, slat, wl) for wl in PROBE_LONS}
    try:
        k = np.asarray(Proj(crs).get_factors(np.asarray(lon), np.asarray(lat))
                       .parallel_scale)
        finite = bool(np.isfinite(k).all() and k.size)
        k = k[np.isfinite(k)]
        spread = float(k.max() / k.min()) if k.size else float("nan")
    except Exception:
        spread, finite = float("nan"), False
    return dict(inside=inside, corners=corners, spread=spread, k_ok=finite,
                lon=lon, lat=lat, south=south,
                nx=int((x1 - x0) / res_m), ny=int((y1 - y0) / res_m))


def main():
    dy = 111_320.0 * 0.1
    res_m = float(np.sqrt(np.mean(dy * dy * np.cos(np.deg2rad(
        np.linspace(45, 75, 2001))))))
    print(f"resolution_m = {res_m:.1f}")
    la, lo = SW_ANCHOR
    print(f"SW anchor (S Kamchatka tip): ({la}, {lo})  "
          f"{'LAND' if is_land(lo, la) else 'OCEAN -- move it'}")
    for nm, (la, lo) in SE_OPTIONS.items():
        print(f"SE anchor {nm}: ({la}, {lo})  "
              f"{'LAND' if is_land(lo, la) else 'OCEAN -- move it'}")

    coast = southern_coast_lat(GAP_LON)
    print(f"southernmost Alaskan land at {abs(GAP_LON):.0f} W: {coast:.2f} N")

    results = []
    for se_name, SE_ANCHOR in SE_OPTIONS.items():
        if True:
            t_lat = CONTROL[0]
            fr = frame_through(SW_ANCHOR, SE_ANCHOR, CONTROL)
            if fr is None:
                print(f"control {t_lat} N: no frame, skipped")
                continue
            d, lat_c, lon_c, alpha, gamma = fr
            crs = omerc_crs(lat_c, lon_c, alpha, gamma)
            fwd = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
            xa, ya = fwd.transform(SW_ANCHOR[1], SW_ANCHOR[0])
            xb, yb = fwd.transform(SE_ANCHOR[1], SE_ANCHOR[0])
            xs, ys_ = fwd.transform(STRAIT[1], STRAIT[0])
            if not np.isfinite([xa, ya, xb, yb, xs, ys_]).all():
                print(f"control {t_lat} N: non-finite frame, skipped")
                continue
            x0, x1 = min(xa, xb), max(xa, xb)
            y0 = 0.5 * (ya + yb)
            y1 = ys_ + NORTH_MARGIN_M
            if y1 <= y0:
                print(f"control {t_lat} N: strait falls south of the edge, skipped")
                continue
            r = evaluate(crs, x0, x1, y0, y1, res_m)
            r["resid_km"] = abs(ya - yb) / 1e3
            r["d_km"] = d / 1e3
            label = f"SE {se_name}"
            r["gap_km"] = (coast - r["south"][GAP_LON]) * 111.32
            results.append((label, crs, x0, x1, y0, y1, r))

    probe_hdr = "".join(f"{abs(w):.0f}{'E' if w > 0 else 'W'}".rjust(7)
                        for w in PROBE_LONS)
    hdr = (f"{'candidate':26s} {'cells':>12s} {'Mcell':>6s} {'k':>6s} "
           f"{'gap':>7s}  south edge at{probe_hdr}   outside")
    print("\n" + hdr)
    print("-" * len(hdr))
    for label, _c, _a, _b, _d, _e, r in results:
        probes = "".join(f"{r['south'][w]:7.1f}" for w in PROBE_LONS)
        out = [n for n, v in r["inside"].items() if not v]
        print(f"{label:26s} {r['nx']:5d}x{r['ny']:<6d} "
              f"{r['nx'] * r['ny'] / 1e6:6.2f} {r['spread']:6.3f} "
              f"{r['gap_km']:6.0f}k  {'':13s}{probes}   "
              f"{', '.join(out) if out else '-'}")

    print("\ncorners:")
    for label, _c, _a, _b, _d, _e, r in results:
        cs = "  ".join(
            f"{nm} ({((lo + 180) % 360) - 180:8.2f},{la:6.2f})"
            f"{'L' if is_land(lo, la) else 'o'}"
            for nm, (lo, la) in zip(["SW", "SE", "NW", "NE"], r["corners"]))
        print(f"  {label:26s} {cs}")

    ncol = 3
    nrow = int(np.ceil(len(results) / ncol))
    fig, axes = plt.subplots(
        nrow, ncol, figsize=(7.0 * ncol, 5.6 * nrow),
        subplot_kw={"projection": ccrs.NorthPolarStereo(central_longitude=-175)})
    axes = np.atleast_1d(axes).ravel()
    land10 = cfeature.NaturalEarthFeature("physical", "land", "10m")

    for ax, (label, _c, _a, _b, _d, _e, r) in zip(axes, results):
        ax.add_feature(land10, facecolor="0.86", edgecolor="none", zorder=0)
        ax.coastlines(resolution="10m", linewidth=0.5, zorder=3)
        ax.gridlines(linewidth=0.3)
        ax.set_extent([130, 250, 34, 80], crs=ccrs.PlateCarree())
        ax.plot(r["lon"], r["lat"], transform=ccrs.Geodetic(),
                color="crimson", lw=2.0, zorder=4)
        for nm, (lo, la) in zip(["SW", "SE", "NW", "NE"], r["corners"]):
            ax.plot(((lo + 180) % 360) - 180, la, transform=ccrs.PlateCarree(),
                    marker="o", ms=9, mfc="lime" if is_land(lo, la) else "red",
                    mec="black", mew=0.7, zorder=6)
        for nm, (la, lo) in CHECKS.items():
            goa = nm.startswith("GoA")
            ax.plot(lo, la, transform=ccrs.PlateCarree(),
                    marker="*" if goa else ".", ms=12 if goa else 8,
                    color=("darkgreen" if r["inside"][nm] else "red") if goa
                          else ("navy" if r["inside"][nm] else "grey"),
                    mec="black", mew=0.3, zorder=7)
        ax.set_title(f"{label}\n{r['nx']} x {r['ny']} "
                     f"({r['nx'] * r['ny'] / 1e6:.2f} M cells)  "
                     f"k {r['spread']:.3f}\n"
                     f"open water under Alaska: {r['gap_km']:.0f} km", fontsize=10)
    for ax in axes[len(results):]:
        ax.set_visible(False)

    fig.suptitle("alaska_big — SW corner on the southern tip of Kamchatka, southern "
                 "edge pinned through 48 N at 160 W, north edge past the Bering "
                 "Strait.\nSweeping how far the SE corner runs down the North "
                 "American coast.", fontsize=13)
    fig.savefig(OUT_PNG, dpi=95, bbox_inches="tight")
    print(f"\nwrote {OUT_PNG}")


if __name__ == "__main__":
    main()
