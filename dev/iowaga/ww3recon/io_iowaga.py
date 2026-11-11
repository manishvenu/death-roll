"""
Loading IOWAGA / WW3 output.

NOTHING IN THIS MODULE HAS BEEN RUN AGAINST A REAL IOWAGA FILE. It was written
and tested against synthetic NetCDF files that mimic the documented WW3 point
and gridded output schemas. The variable-name detection is deliberately
tolerant, and every loader reports what it found so you can check it matched
the right thing on the first real file.

Two data sources are needed and they live in different places:

  * 2D spectra  -> POINT output, ww3.YYYYMM_spec.nc, at the 12,490 stations
  * partitions  -> GRIDDED output, in the ``partitions`` folder

The gridded partition fields must be sampled at the station position, which
introduces an interpolation mismatch: the station sits inside a grid cell, and
the partition field is a cell value. For a 0.5 deg global grid that is a real
source of disagreement independent of reconstruction error. Use
``self_partition`` mode (see partition.py) to separate the two.
"""

from __future__ import annotations

import glob
import os
import warnings

import numpy as np

__all__ = ["open_dataset", "load_point_spectra", "load_gridded_partitions",
           "find_nearest_station", "SUGGESTED_STATIONS"]


# Candidate validation sites. Verify these exist in the station list -- IOWAGA
# station coverage is not guaranteed to include any particular buoy.
SUGGESTED_STATIONS = {
    "extratropical": [
        ("Station Papa (NDBC 46246)", 50.03, -145.28,
         "NE Pacific, strong seasonal wind sea plus long swell; the classic "
         "wave-model validation site and the best-instrumented extratropical option"),
        ("NDBC 46006 SE Papa", 40.75, -137.40,
         "Storm-track mid-latitude Pacific, frequent crossing seas"),
        ("K1 / OWS Mike (Norwegian Sea)", 66.00, 2.00,
         "NE Atlantic storm track, useful if you want a second extratropical basin"),
    ],
    "tropical": [
        ("TAO 0N 140W", 0.00, -140.00,
         "Equatorial Pacific; persistent remote swell with weak local wind sea, "
         "so the swell family and the partition split are stressed rather than "
         "the wind-sea tail"),
        ("PIRATA 0N 23W", 0.00, -23.00,
         "Equatorial Atlantic, similar regime, shorter swell fetch"),
        ("NDBC 51004 Hawaii", 17.60, -152.40,
         "Subtropical, trade wind sea crossing with N Pacific swell -- a good "
         "crossing-sea stress case if you want one deliberately hard site"),
    ],
}


def open_dataset(path: str):
    """Open a NetCDF file with whichever backend is installed.

    Returns an object exposing ``.variables`` (mapping to array-likes with
    ``[:]``) and ``.close()``. Tries netCDF4, then h5netcdf, then xarray.
    """
    try:
        import netCDF4
        return netCDF4.Dataset(path)
    except ImportError:
        pass
    try:
        import xarray as xr
        ds = xr.open_dataset(path)

        class _Wrap:
            variables = ds.variables

            def close(self):
                ds.close()
        return _Wrap()
    except ImportError:
        raise ImportError(
            "need netCDF4 or xarray to read IOWAGA files:\n"
            "    pip install netCDF4      # or\n"
            "    pip install xarray h5netcdf")


def _find_var(variables, candidates, what: str):
    lower = {k.lower(): k for k in variables}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    raise KeyError(
        f"could not find {what} in file; tried {candidates}, "
        f"file has {sorted(variables)}")


def load_point_spectra(path: str, station_index=None, verbose: bool = True) -> dict:
    """Load 2D spectra from a WW3 point-output file.

    Returns dict with ``efth`` (n_time, n_station, n_freq, n_dir), ``frequency``,
    ``direction`` (degrees, as stored), ``latitude``, ``longitude``, ``time``.

    IMPORTANT: the direction axis is returned exactly as stored, with no
    reinterpretation. WW3 spec files and the gridded PDIR field do not
    necessarily share a convention. Resolve this with
    ``validate.check_direction_convention`` before drawing conclusions.
    """
    ds = open_dataset(path)
    try:
        v = ds.variables
        k_e = _find_var(v, ["efth", "Efth", "E", "spectral_density",
                            "sea_surface_wave_directional_variance_spectral_density"],
                        "2D spectrum")
        k_f = _find_var(v, ["frequency", "f", "freq"], "frequency axis")
        k_d = _find_var(v, ["direction", "theta", "dir"], "direction axis")

        efth = np.asarray(v[k_e][:], float)
        freq = np.asarray(v[k_f][:], float).ravel()
        drc = np.asarray(v[k_d][:], float).ravel()

        lat = np.asarray(v[_find_var(v, ["latitude", "lat"], "latitude")][:], float)
        lon = np.asarray(v[_find_var(v, ["longitude", "lon"], "longitude")][:], float)
        try:
            time = np.asarray(v[_find_var(v, ["time"], "time")][:], float)
        except KeyError:
            time = np.arange(efth.shape[0], dtype=float)

        # Station coordinates may be (station,) or (time, station).
        if lat.ndim > 1:
            lat, lon = lat[0], lon[0]

        if efth.ndim == 3:            # single station, dims dropped
            efth = efth[:, None, :, :]

        if station_index is not None:
            idx = np.atleast_1d(station_index)
            efth = efth[:, idx]
            lat, lon = np.atleast_1d(lat)[idx], np.atleast_1d(lon)[idx]

        if verbose:
            print(f"[spectra] {os.path.basename(path)}")
            print(f"          var={k_e} shape={efth.shape} "
                  f"nf={freq.size} nd={drc.size}")
            print(f"          f: {freq.min():.4f}-{freq.max():.4f} Hz, "
                  f"ratio~{freq[1]/freq[0]:.3f}")
            print(f"          dir: {drc.min():.1f}-{drc.max():.1f} deg, "
                  f"step {np.diff(np.sort(drc))[0]:.1f}")
            print(f"          NOTE units assumed m2 s rad-1; if the file says "
                  f"deg-1, multiply by 180/pi")

        return {"efth": efth, "frequency": freq, "direction": drc,
                "latitude": np.atleast_1d(lat), "longitude": np.atleast_1d(lon),
                "time": time, "source": path, "spectrum_var": k_e}
    finally:
        ds.close()


def find_nearest_station(lat_target: float, lon_target: float,
                         lats: np.ndarray, lons: np.ndarray,
                         max_distance_km: float = 150.0) -> dict:
    """Great-circle nearest station, with a distance guard.

    The guard matters: IOWAGA stations are not uniformly distributed, and
    silently validating at a point 600 km from where you meant would not be
    obviously wrong in any plot.
    """
    lat1, lon1 = np.deg2rad(lat_target), np.deg2rad(lon_target)
    lat2, lon2 = np.deg2rad(np.asarray(lats)), np.deg2rad(np.asarray(lons))
    d = 2 * np.arcsin(np.sqrt(
        np.sin((lat2 - lat1) / 2) ** 2 +
        np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2))
    km = 6371.0 * d
    i = int(np.argmin(km))
    if km[i] > max_distance_km:
        warnings.warn(
            f"nearest station is {km[i]:.0f} km from "
            f"({lat_target:.2f}, {lon_target:.2f}) -- exceeds "
            f"{max_distance_km} km guard. Check the station list.")
    return {"index": i, "distance_km": float(km[i]),
            "latitude": float(np.asarray(lats)[i]),
            "longitude": float(np.asarray(lons)[i])}


def load_gridded_partitions(directory: str, lat: float, lon: float,
                            n_partitions: int = 4, pattern: str = "*.nc",
                            verbose: bool = True) -> dict:
    """Sample gridded partition fields at one location.

    Looks for files whose names contain phs/ptp/pdir/pspr/pws followed by a
    partition index, plus the whole-spectrum hs/t0m1/t02 fields.

    Nearest-neighbour sampling, deliberately not bilinear: partition fields are
    piecewise by construction (labels swap between cells), so interpolating
    them mixes different wave systems and produces values that correspond to no
    physical partition at all.
    """
    found, fields = {}, ["phs", "ptp", "pdir", "pspr", "pws"]
    files = sorted(glob.glob(os.path.join(directory, pattern)))
    if not files:
        raise FileNotFoundError(f"no NetCDF files matching {pattern} in {directory}")

    def _sample(path, varname=None):
        ds = open_dataset(path)
        try:
            v = ds.variables
            la = np.asarray(v[_find_var(v, ["latitude", "lat"], "lat")][:], float)
            lo = np.asarray(v[_find_var(v, ["longitude", "lon"], "lon")][:], float)
            if varname is None:
                skip = {"latitude", "lat", "longitude", "lon", "time"}
                cand = [k for k in v if k.lower() not in skip
                        and np.asarray(v[k]).ndim >= 2]
                varname = cand[0]
            j = int(np.argmin(np.abs(la - lat)))
            i = int(np.argmin(np.abs(((lo - lon + 180) % 360) - 180)))
            arr = np.asarray(v[varname][..., j, i], float)
            return np.where(np.abs(arr) > 1e19, np.nan, arr), varname
        finally:
            ds.close()

    for f in files:
        base = os.path.basename(f).lower()
        for fld in fields:
            for k in range(n_partitions):
                if f"{fld}{k}" in base:
                    found[f"{fld}{k}"], _ = _sample(f)
        for tot in ("hs", "t0m1", "t02"):
            if f"_{tot}." in base or base.endswith(f"_{tot}.nc"):
                found[tot], _ = _sample(f)

    if verbose:
        print(f"[partitions] {directory}")
        print(f"             matched {len(found)} fields: {sorted(found)}")
        missing = [f"{fl}{k}" for fl in fields for k in range(n_partitions)
                   if f"{fl}{k}" not in found]
        if missing:
            print(f"             MISSING: {missing}")
            print("             -> check the archive naming; adjust `pattern` "
                  "or use self_partition mode")

    def stack(fld):
        cols = [found.get(f"{fld}{k}") for k in range(n_partitions)]
        cols = [c for c in cols if c is not None]
        return np.stack(cols, axis=-1) if cols else None

    return {"phs": stack("phs"), "ptp": stack("ptp"), "pdir": stack("pdir"),
            "pspr": stack("pspr"), "pws": stack("pws"),
            "hs": found.get("hs"), "t0m1": found.get("t0m1"),
            "t02": found.get("t02"), "raw": found}
