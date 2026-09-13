"""Design regional MOM6 domains by projection and distance, with fast previews.

The idea
--------
A MOM6 supergrid is curvilinear: it stores lon/lat at every node, so any smooth
mesh is legal. You never draw the curve by hand. You pick a projection whose
coordinate lines already bend the way you want, lay a plain rectangle on it, and
the curve appears when the rectangle is mapped back to lon/lat.

That makes domain design three steps:

  1. `landmark_xy()` - put the places you care about into the projected frame,
     where they become plain x/y numbers in kilometres.
  2. read the box straight off those numbers, and `preview()` it. A preview
     traces only the four edges, not the full mesh, so it renders in about a
     second and you can iterate.
  3. `build()` the real Grid once the preview looks right.

Choosing a projection
---------------------
    oblique Mercator  `omerc(lat_0, lonc, alpha)`
        Conformal. The `alpha` bearing aims the domain's "straight" axis along
        any great circle, so a swath can follow the Aleutian arc or a
        Kamchatka -> British Columbia track. Lowest distortion of the options
        tried for the North Pacific (~1.01x cell-area spread over 50-72 N).
    Lambert conformal conic  `lcc(lat_1, lat_2, lon_0)`
        Conformal. Standard parallels should bracket the domain's latitude
        range; edges curve concave toward the pole. Good for wide zonal domains.
    azimuthal equidistant, via `Grid.from_center`
        Not conformal, but nearly isotropic near its centre and it is the only
        constructor exposing a rotation angle, so it is the one to use when the
        corners have to land on particular coastlines.
    polar stereographic (EPSG:3995 / 3031)
        Conformal, pole-centred, and has no antimeridian seam - the natural
        choice for anything spanning the pole or the dateline at high latitude.

Two traps this module checks for
--------------------------------
    handedness  MOM6 wants j increasing north and i increasing east. Reverse
                either and every dx or dy comes out negative and the grid is
                unusable. `validate()` reports the sign census.
    the seam    Differencing reprojected longitudes across +-180 gives a
                ~360-degree jump, so dx blows up to thousands of km at one
                column. Only some mom6_forge checkouts carry the fix, so
                `validate()` looks for it explicitly.
"""

from dataclasses import dataclass

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
import numpy as np
from pyproj import CRS, Proj, Transformer
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.prepared import prep

__all__ = ["omerc", "lcc", "landmark_xy", "preview", "preview_center",
           "build", "build_center", "validate"]

_LAND = None


def _land():
    """Prepared Natural Earth 10 m land polygons, loaded once.

    Natural Earth rather than GEBCO on purpose: the 7.5 GB global bathymetry has
    to be windowed and loaded before a single point can be tested, which
    dominates the runtime of any search. This loads in under a second and a
    prepared point test is essentially free.
    """
    global _LAND
    if _LAND is None:
        path = shpreader.natural_earth(resolution="10m", category="physical",
                                       name="land")
        _LAND = prep(unary_union(list(shpreader.Reader(path).geometries())))
    return _LAND


def is_land(lon, lat):
    return _land().contains(Point(((float(lon) + 180) % 360) - 180, float(lat)))


# --------------------------------------------------------------------------
# projection builders
# --------------------------------------------------------------------------
def omerc(lat_0, lonc, alpha, gamma=0.0):
    """Oblique Mercator whose straight axis runs at bearing `alpha` through
    (lat_0, lonc). Conformal."""
    return (f"+proj=omerc +lat_0={lat_0} +lonc={lonc} +alpha={alpha} "
            f"+gamma={gamma} +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")


def lcc(lat_1, lat_2, lon_0, lat_0=None):
    """Lambert conformal conic. Standard parallels should bracket the domain."""
    lat_0 = (lat_1 + lat_2) / 2 if lat_0 is None else lat_0
    return (f"+proj=lcc +lat_0={lat_0} +lon_0={lon_0} +lat_1={lat_1} "
            f"+lat_2={lat_2} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")


# --------------------------------------------------------------------------
# step 1: landmarks -> projected coordinates
# --------------------------------------------------------------------------
def landmark_xy(crs, landmarks, verbose=True):
    """Project {name: (lat, lon)} into `crs`. Returns {name: (x_km, y_km)}.

    This is the step that turns domain design into arithmetic: once your
    landmarks are x/y in kilometres, the box you need is just their min/max
    plus whatever margin you want.
    """
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    out = {}
    for nm, (la, lo) in landmarks.items():
        x, y = t.transform(lo, la)
        out[nm] = (x / 1e3, y / 1e3)
        if verbose:
            print(f"   {nm:28s} x={x / 1e3:9.0f} km  y={y / 1e3:9.0f} km")
    if verbose and out:
        xs = [v[0] for v in out.values()]
        ys = [v[1] for v in out.values()]
        print(f"   {'-> bounding box':28s} x=[{min(xs):.0f},{max(xs):.0f}] "
              f"y=[{min(ys):.0f},{max(ys):.0f}] km")
    return out


# --------------------------------------------------------------------------
# step 2: preview
# --------------------------------------------------------------------------
@dataclass
class DomainSpec:
    crs: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    resolution_m: float

    @property
    def nx(self):
        return int((self.x_max - self.x_min) / self.resolution_m)

    @property
    def ny(self):
        return int((self.y_max - self.y_min) / self.resolution_m)


def _outline(spec, n=200):
    """Lon/lat of the domain's four edges. Traces the rim only, so it is fast
    even for a domain that would be millions of nodes when fully built."""
    xs = np.linspace(spec.x_min, spec.x_max, n)
    ys = np.linspace(spec.y_min, spec.y_max, n)
    x = np.concatenate([xs, np.full(n, spec.x_max), xs[::-1], np.full(n, spec.x_min)])
    y = np.concatenate([np.full(n, spec.y_min), ys, np.full(n, spec.y_max), ys[::-1]])
    inv = Transformer.from_crs(spec.crs, "EPSG:4326", always_xy=True)
    lon, lat = inv.transform(x, y)
    corners_xy = [(spec.x_min, spec.y_min), (spec.x_max, spec.y_min),
                  (spec.x_min, spec.y_max), (spec.x_max, spec.y_max)]
    clon, clat = inv.transform([c[0] for c in corners_xy], [c[1] for c in corners_xy])
    return lon, lat, list(zip(clon, clat))


def preview(crs, x_min, x_max, y_min, y_max, resolution_m,
            landmarks=None, title=None, pad=6.0, ax=None):
    """Draw a domain outline over coastlines and report its properties.

    Traces only the rim, so this is a fast design loop: adjust numbers, look,
    repeat. Nothing is built or written.
    """
    spec = DomainSpec(crs, x_min, x_max, y_min, y_max, resolution_m)
    lon, lat, corners = _outline(spec)

    lon360 = np.asarray(lon) % 360.0
    clon = np.mean(lon360)
    if ax is None:
        proj = ccrs.NorthPolarStereo(central_longitude=((clon + 180) % 360) - 180)
        _, ax = plt.subplots(figsize=(11, 8), subplot_kw={"projection": proj})
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "land", "10m"),
                   facecolor="0.85", edgecolor="none", zorder=0)
    ax.coastlines(resolution="10m", linewidth=0.6, zorder=3)
    ax.gridlines()
    ax.set_extent([lon360.min() - pad, lon360.max() + pad,
                   np.min(lat) - pad / 2, np.max(lat) + pad / 2],
                  crs=ccrs.PlateCarree())
    ax.plot(lon, lat, transform=ccrs.Geodetic(), color="crimson", lw=2, zorder=4)

    print(f"grid      : {spec.nx} x {spec.ny} cells at {resolution_m / 1e3:.2f} km")
    print(f"extent    : {(x_max - x_min) / 1e3:.0f} x {(y_max - y_min) / 1e3:.0f} km")
    print("corners   :")
    for nm, (lo, la) in zip(["SW", "SE", "NW", "NE"], corners):
        lo180 = ((lo + 180) % 360) - 180
        land = is_land(lo180, la)
        print(f"   {nm} ({lo180:9.3f},{la:8.3f})  {'LAND ' if land else 'ocean'}")
        ax.plot(lo180, la, transform=ccrs.PlateCarree(), marker="o", ms=9,
                mfc="red" if not land else "lime", mec="black", zorder=6)

    # conformal scale spread, a proxy for how uniform the cells will be
    try:
        k = np.asarray(Proj(crs).get_factors(np.asarray(lon), np.asarray(lat))
                       .parallel_scale)
        k = k[np.isfinite(k)]
        print(f"scale k   : [{k.min():.4f}, {k.max():.4f}]  "
              f"spread {k.max() / k.min():.3f}x")
    except Exception:
        pass

    if lon360.max() - lon360.min() > 180 or (np.min(lon) < -170 and np.max(lon) > 170):
        print("note      : domain crosses the antimeridian -- build it with a "
              "mom6_forge that has the dx seam fix")

    if landmarks:
        inv = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        print("landmarks :")
        for nm, (la, lo) in landmarks.items():
            px, py = inv.transform(lo, la)
            inside = x_min <= px <= x_max and y_min <= py <= y_max
            print(f"   {nm:28s} {'inside ' if inside else 'OUTSIDE'}")
            ax.plot(lo, la, transform=ccrs.PlateCarree(), marker="*", ms=12,
                    color="magenta", mec="black", mew=0.4, zorder=7)
    ax.set_title(title or "domain preview", fontsize=11)
    return spec


def preview_center(center_lat, center_lon, width_m, height_m, resolution_m,
                   angle_deg=0.0, landmarks=None, title=None, pad=4.0):
    """Preview a `Grid.from_center` domain: a rotated box on an azimuthal
    equidistant projection centred at the given point.

    Use this when the corners must land on particular coastlines - `angle_deg`
    is the only rotation knob any of the constructors expose.
    """
    crs = (f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} "
           f"+x_0=0 +y_0=0 +datum=WGS84 +units=m")
    hw, hh = width_m / 2, height_m / 2
    th = np.deg2rad(angle_deg)
    n = 200
    xs = np.linspace(-hw, hw, n)
    ys = np.linspace(-hh, hh, n)
    x = np.concatenate([xs, np.full(n, hw), xs[::-1], np.full(n, -hw)])
    y = np.concatenate([np.full(n, -hh), ys, np.full(n, hh), ys[::-1]])
    xr = x * np.cos(th) + y * np.sin(th)
    yr = -x * np.sin(th) + y * np.cos(th)
    inv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = inv.transform(xr, yr)

    cxy = [(-hw, -hh), (hw, -hh), (-hw, hh), (hw, hh)]
    cxr = [c[0] * np.cos(th) + c[1] * np.sin(th) for c in cxy]
    cyr = [-c[0] * np.sin(th) + c[1] * np.cos(th) for c in cxy]
    clon, clat = inv.transform(cxr, cyr)

    lon360 = np.asarray(lon) % 360.0
    proj = ccrs.NorthPolarStereo(
        central_longitude=((np.mean(lon360) + 180) % 360) - 180)
    _, ax = plt.subplots(figsize=(11, 8), subplot_kw={"projection": proj})
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "land", "10m"),
                   facecolor="0.85", edgecolor="none", zorder=0)
    ax.coastlines(resolution="10m", linewidth=0.6, zorder=3)
    ax.gridlines()
    ax.set_extent([lon360.min() - pad, lon360.max() + pad,
                   np.min(lat) - pad / 2, np.max(lat) + pad / 2],
                  crs=ccrs.PlateCarree())
    ax.plot(lon, lat, transform=ccrs.Geodetic(), color="crimson", lw=2, zorder=4)

    print(f"grid      : {int(width_m / resolution_m)} x "
          f"{int(height_m / resolution_m)} cells at {resolution_m / 1e3:.2f} km")
    print(f"centre    : ({center_lat:.2f} N, {center_lon:.2f} E)  angle "
          f"{angle_deg:+.1f} deg")
    print("corners   :")
    for nm, lo, la in zip(["SW", "SE", "NW", "NE"], clon, clat):
        land = is_land(lo, la)
        print(f"   {nm} ({lo:9.3f},{la:8.3f})  {'LAND ' if land else 'ocean'}")
        ax.plot(lo, la, transform=ccrs.PlateCarree(), marker="o", ms=9,
                mfc="lime" if land else "red", mec="black", zorder=6)

    if landmarks:
        fwd = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        print("landmarks :")
        for nm, (la, lo) in landmarks.items():
            px, py = fwd.transform(lo, la)
            ux = px * np.cos(th) - py * np.sin(th)
            uy = px * np.sin(th) + py * np.cos(th)
            inside = abs(ux) <= hw and abs(uy) <= hh
            print(f"   {nm:28s} {'inside ' if inside else 'OUTSIDE'}")
            ax.plot(lo, la, transform=ccrs.PlateCarree(), marker="*", ms=12,
                    color="magenta", mec="black", mew=0.4, zorder=7)
    ax.set_title(title or "domain preview (from_center)", fontsize=11)
    return dict(center_lat=center_lat, center_lon=center_lon, width_m=width_m,
                height_m=height_m, resolution_m=resolution_m, angle_deg=angle_deg)


# --------------------------------------------------------------------------
# step 3: build, then always validate
# --------------------------------------------------------------------------
def build(spec, name):
    from CrocoDash.grid import Grid
    g = Grid.from_projection(crs=spec.crs, x_min=spec.x_min, x_max=spec.x_max,
                             y_min=spec.y_min, y_max=spec.y_max,
                             resolution_m=spec.resolution_m, name=name)
    validate(g, name)
    return g


def build_center(params, name):
    from CrocoDash.grid import Grid
    g = Grid.from_center(name=name, **params)
    validate(g, name)
    return g


def validate(grid, name="grid"):
    """Report the two failure modes that make a grid unusable in MOM6.

    Negative metrics mean the grid is flipped (j running south or i running
    west); MOM6 wants a right-handed grid. Huge dx at a single column means the
    antimeridian seam was differenced without wrapping.
    """
    sg = grid._supergrid
    dx, dy = np.asarray(sg.dx), np.asarray(sg.dy)
    area = np.asarray(grid.tarea)
    ok = True
    print(f"validate {name}: {grid.nx} x {grid.ny}")
    if (dy < 0).any():
        ok = False
        print(f"   FAIL dy negative in {int((dy < 0).sum())}/{dy.size} "
              f"-- j runs south, grid is flipped")
    if (dx < 0).any():
        ok = False
        print(f"   FAIL dx negative in {int((dx < 0).sum())}/{dx.size} "
              f"-- i runs west, grid is flipped")
    big = np.abs(dx) > 1e6
    if big.any():
        ok = False
        cols = np.unique(np.where(big)[1])
        print(f"   FAIL |dx| > 1000 km in {int(big.sum())} cells at column(s) "
              f"{cols[:5]} -- antimeridian seam not wrapped")
    print(f"   dx   [{dx.min():10.1f}, {dx.max():10.1f}] m")
    print(f"   dy   [{dy.min():10.1f}, {dy.max():10.1f}] m")
    print(f"   area spread {area.max() / area.min():.3f}x")
    print("   OK" if ok else "   NOT USABLE as-is")
    return ok
