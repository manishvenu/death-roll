"""Build an oblique-Mercator swath domain from three points on its southern edge.

The problem this solves
-----------------------
A regional domain over the North Pacific wants to follow the arc of the Aleutian
chain rather than sit as a lat/lon box, and the natural way to say what it
should cover is by naming places: start on Kamchatka, end on the North American
coast, keep this much open ocean underneath. But two corners do not determine a
domain. At these latitudes the curve between them is the whole design: the
geodesic joining southern Kamchatka to Washington bulges poleward onto the
Alaska Peninsula, while a rhumb line between the same two points passes some six
degrees further south. Everything the domain is meant to contain lives in that
gap.

The construction
----------------
In an oblique Mercator, lines of constant y are small circles sharing an axis
with the central great circle. So the southern edge is always a small circle
through the two corner anchors -- and three points determine a circle. Add a
control point out in the open Pacific and the edge is pinned exactly, with no
rotation or offset left to grope at:

    n = norm((B - A) x (T - A))     axis of the circle through A, B and T
    central line = the great circle with pole n
    d = R * asin(n . A)             common distance of A, B, T from that line

Because A, B and T are equidistant from the central line they share one line of
constant y, which becomes the southern edge. The knob is then the one that
actually matters -- how far south the edge dips -- rather than an abstract
rotation whose effect has to be discovered by trial.

The central line is where the oblique Mercator's scale factor is exactly 1. It
runs along the southern edge, so distortion grows monotonically northward and is
reported here as `k`, the ratio of largest to smallest scale factor around the
domain boundary. Note that `Grid.from_projection` lays down uniform spacing in
the *projected* plane and divides by that scale factor, so physical cell size
varies across the domain by roughly the same ratio: cells are coarsest on the
central line and finest at the far edges.

Projection traps, both found the hard way
-----------------------------------------
  `+no_rot`  puts the anchors on the frame's axis but makes pyproj's get_factors
             return inf almost everywhere. mom6_forge's from_projection divides
             projected spacing by that scale factor, so dx and dy come out
             exactly zero over ~90% of the grid -- silently: no NaN, no warning,
             and cell area still looks right, because area is derived from
             lon/lat rather than from the metrics. Always check `dx > 0`.
  gamma      sets the rectification rotation. `gamma = alpha` happens to put the
             anchors on the x-axis only when alpha is near 90; at alpha = 109 it
             left them 2000 km off it and the domain came out as a diamond in
             the mid-Pacific. So gamma is solved for numerically below: changing
             it rotates the projected plane about the origin, so one measurement
             of the anchors' tilt gives the correction directly.
"""

import numpy as np
import cartopy.io.shapereader as shpreader
from pyproj import Proj, Transformer
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.prepared import prep

R_EARTH = 6_371_008.8

_LAND = None


def _land():
    """Natural Earth 10 m land, prepared for fast point-in-polygon tests.

    Preferred over GEBCO elevation lookups: the global 7.5 GB array has to be
    windowed and loaded before a single point can be tested, which was enough on
    its own to blow a batch job's walltime. This loads in under a second and
    every subsequent test is essentially free.
    """
    global _LAND
    if _LAND is None:
        path = shpreader.natural_earth(resolution="10m", category="physical",
                                       name="land")
        _LAND = prep(unary_union(list(shpreader.Reader(path).geometries())))
    return _LAND


def is_land(lon, lat):
    """True if (lon, lat) falls on land. lon may be in any convention."""
    return _land().contains(Point(((float(lon) + 180) % 360) - 180, float(lat)))


def southern_coast_lat(lon, lo=40.0, hi=63.0, step=0.05):
    """Southernmost latitude of land at this longitude -- Alaska's outer edge.

    Used to turn "is there open water under Alaska?" into a number measured
    against real coastline instead of a guessed reference latitude.
    """
    land = [la for la in np.arange(hi, lo, -step) if is_land(lon, la)]
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


# ---------------------------------------------------------------- projection
def omerc_crs(lat_0, lonc, alpha, gamma):
    return (f"+proj=omerc +lat_0={lat_0} +lonc={lonc} +alpha={alpha} "
            f"+gamma={gamma} +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")


def solve_gamma(lat_0, lonc, alpha, A_ll, B_ll, tol_m=1.0):
    """gamma placing both anchors on a common line of constant y.

    Changing gamma rotates the projected plane about the origin, so the anchors'
    measured tilt at one gamma is the correction. Both signs are tried because
    the direction of that rotation is a PROJ convention rather than something
    worth deriving.
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
            if resid < tol_m:
                break
            gi = gi + sign * ti
    return None if best is None else best[0]


def frame_through(A_ll, B_ll, T_ll):
    """Oblique Mercator whose constant-y line through A also passes B and T.

    A and B are the southwest and southeast corners; T is the control point that
    decides how far south the edge between them dips. All three are (lat, lon).
    Returns (crs, info) or None if the three points are collinear on a great
    circle, which leaves the circle undetermined.
    """
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
    return omerc_crs(lat_c, lon_c, alpha, gamma), dict(
        lat_0=lat_c, lonc=lon_c, alpha=alpha, gamma=gamma, central_offset_m=d)


# ------------------------------------------------------------------- extents
def box_for(crs, A_ll, B_ll, north_of_ll, north_margin_m):
    """Projected extent with A and B as the southern corners.

    The north edge is placed `north_margin_m` beyond `north_of_ll`, which is how
    "high enough to clear the Bering Strait" gets expressed as a number.
    """
    fwd = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xa, ya = fwd.transform(A_ll[1], A_ll[0])
    xb, yb = fwd.transform(B_ll[1], B_ll[0])
    xn, yn = fwd.transform(north_of_ll[1], north_of_ll[0])
    if not np.isfinite([xa, ya, xb, yb, xn, yn]).all():
        return None
    x0, x1 = min(xa, xb), max(xa, xb)
    y0 = 0.5 * (ya + yb)                # they are equal by construction
    y1 = yn + north_margin_m
    if y1 <= y0 or x1 <= x0:
        return None
    return dict(x_min=x0, x_max=x1, y_min=y0, y_max=y1,
                anchor_resid_m=abs(ya - yb))


def box_outline(crs, x0, x1, y0, y1, n=400):
    """Lon/lat around the box, along its south edge, and at its four corners."""
    inv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    xs = np.linspace(x0, x1, n)
    ys = np.linspace(y0, y1, n)
    x = np.concatenate([xs, np.full(n, x1), xs[::-1], np.full(n, x0)])
    y = np.concatenate([np.full(n, y0), ys, np.full(n, y1), ys[::-1]])
    lon, lat = inv.transform(x, y)
    slon, slat = inv.transform(xs, np.full(n, y0))
    clon, clat = inv.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
    return lon, lat, (slon, slat), list(zip(clon, clat))


def south_edge_at(slon, slat, want_lon, tol_deg=4.0):
    """Latitude of the sampled south edge where it crosses `want_lon`, else nan."""
    l180 = ((np.asarray(slon) + 180) % 360) - 180
    dl = np.abs(((l180 - want_lon + 180) % 360) - 180)
    i = int(np.argmin(dl))
    return float(slat[i]) if dl[i] < tol_deg else float("nan")


def scale_spread(crs, lon, lat):
    """max/min of the projection's scale factor around a boundary trace.

    Also the factor by which physical cell size varies, since from_projection
    divides uniform projected spacing by this. Returns (spread, all_finite) --
    a non-finite result is the `+no_rot` failure mode and means the grid would
    come out with zero metrics.
    """
    try:
        k = np.asarray(Proj(crs).get_factors(np.asarray(lon), np.asarray(lat))
                       .parallel_scale)
        finite = bool(np.isfinite(k).all() and k.size)
        k = k[np.isfinite(k)]
        return (float(k.max() / k.min()) if k.size else float("nan")), finite
    except Exception:
        return float("nan"), False


def resolution_m_for(deg, lat_min, lat_max):
    """Isotropic spacing matching the mean cell area of a `deg` lat/lon grid.

    A naive 111_320 * deg describes only meridional spacing and ignores the
    cos(lat) shrinkage of zonal spacing, which badly overstates cell area this
    far north -- at 62 N the zonal spacing is under half the meridional.
    """
    dy = 111_320.0 * deg
    lats = np.linspace(lat_min, lat_max, 2001)
    return float(np.sqrt(np.mean(dy * dy * np.cos(np.deg2rad(lats)))))


def median_scale_factor(crs, box, n=120):
    """Median scale factor over the domain interior, not just its boundary.

    `Grid.from_projection` lays uniform spacing in the projected plane and
    divides by this factor, so physical cell size is `resolution_m / k`. A
    request for "1/10 degree" therefore has to be pre-multiplied by k, or the
    grid comes out finer than asked for by exactly this ratio -- which is how
    alaska_big first landed at ~4 km cells instead of ~7.9 km.
    """
    xs = np.linspace(box["x_min"], box["x_max"], n)
    ys = np.linspace(box["y_min"], box["y_max"], n)
    gx, gy = np.meshgrid(xs, ys)
    inv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = inv.transform(gx.ravel(), gy.ravel())
    k = np.asarray(Proj(crs).get_factors(lon, lat).parallel_scale)
    k = k[np.isfinite(k)]
    return float(np.median(k)) if k.size else float("nan")


def resolution_m_for_physical(crs, box, target_m, n=120):
    """Projected-plane spacing whose *physical* median cell size is target_m."""
    return target_m * median_scale_factor(crs, box, n)
