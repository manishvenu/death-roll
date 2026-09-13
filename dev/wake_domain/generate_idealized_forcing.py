"""Build synthetic "raw GLORYS-shaped" forcing files for the wake domain.

CrocoDash's GET phase is idempotent by filename (see extract_forcings/utils.py
fetch_raw_chunk) -- if the expected raw file already exists, it skips calling
the real data-access function entirely. So instead of touching CrocoDash/
regional-mom6 code, we just pre-write files in GLORYS's own variable/coordinate
convention (time, latitude, longitude, depth; uo, vo, thetao, so, zos) at the
exact paths/filenames the normal pipeline expects, and let the real REGRID/
MERGE/IC-remap machinery run unmodified against them.

Physics: a west-to-east jet, uniform in the interior of the domain but
tapering to ~0 within JET_EDGE_TAPER_ROWS T-rows of the true north/south
edges -- so only the west/east cardinal segments actually carry the current,
while north/south/interior segments passively radiate whatever's there.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def _taper(lat, lat_lo_full, lat_hi_full, lat_lo_ramp, lat_hi_ramp):
    """1 inside [lat_lo_full, lat_hi_full], smoothly ramping to 0 by
    [lat_lo_ramp, lat_hi_ramp], 0 beyond."""
    t = np.ones_like(lat)
    # South ramp
    south = (lat < lat_lo_full) & (lat >= lat_lo_ramp)
    frac = (lat[south] - lat_lo_ramp) / (lat_lo_full - lat_lo_ramp)
    t[south] = 0.5 - 0.5 * np.cos(np.pi * frac)
    t[lat < lat_lo_ramp] = 0.0
    # North ramp
    north = (lat > lat_hi_full) & (lat <= lat_hi_ramp)
    frac = (lat_hi_ramp - lat[north]) / (lat_hi_ramp - lat_hi_full)
    t[north] = 0.5 - 0.5 * np.cos(np.pi * frac)
    t[lat > lat_hi_ramp] = 0.0
    return t


def build_idealized_dataset(
    lon_min,
    lon_max,
    lat_min,
    lat_max,
    start_date,
    end_date,
    jet_speed,
    jet_taper_lat_lo_full,
    jet_taper_lat_hi_full,
    lon_res=0.25,
    lat_res=0.25,
    margin=2.0,
    salinity_anomaly=0.0,
):
    """A steady, spatially-varying-only-in-latitude zonal jet, uniform over
    the full requested date range (one field repeated daily), covering
    [lon_min-margin, lon_max+margin] x [lat_min-margin, lat_max+margin].

    `salinity_anomaly` is added on top of the 35.0 PSU background -- a cheap
    per-boundary visualization tracer so inflow from each OBC segment is
    distinguishable in the salinity field, with no MOM6 config changes."""
    lon = np.arange(lon_min - margin, lon_max + margin + lon_res, lon_res)
    lat = np.arange(lat_min - margin, lat_max + margin + lat_res, lat_res)
    depth = np.array([0, 10, 25, 50, 75, 100, 150, 200, 300, 400, 500, 700, 1000.0])
    dates = pd.date_range(start_date, end_date, freq="D")

    u1d = jet_speed * _taper(
        lat,
        jet_taper_lat_lo_full,
        jet_taper_lat_hi_full,
        lat_min - margin,
        lat_max + margin,
    )

    nt, nz, ny, nx = len(dates), len(depth), len(lat), len(lon)
    uo = np.broadcast_to(u1d[None, None, :, None], (nt, nz, ny, nx)).astype("float32")
    vo = np.zeros((nt, nz, ny, nx), dtype="float32")

    temp_profile = np.interp(depth, [0, 1000], [20.0, 6.0]).astype("float32")
    thetao = np.broadcast_to(temp_profile[None, :, None, None], (nt, nz, ny, nx)).astype(
        "float32"
    )
    so = np.full((nt, nz, ny, nx), 35.0 + salinity_anomaly, dtype="float32")
    zos = np.zeros((nt, ny, nx), dtype="float32")

    ds = xr.Dataset(
        {
            "uo": (("time", "depth", "latitude", "longitude"), uo),
            "vo": (("time", "depth", "latitude", "longitude"), vo),
            "thetao": (("time", "depth", "latitude", "longitude"), thetao),
            "so": (("time", "depth", "latitude", "longitude"), so),
            "zos": (("time", "latitude", "longitude"), zos),
        },
        coords={
            "time": dates,
            "depth": depth,
            "latitude": lat,
            "longitude": lon,
        },
    )
    for v in ("uo", "vo", "thetao", "so", "zos"):
        ds[v].attrs["units"] = {
            "uo": "m s-1",
            "vo": "m s-1",
            "thetao": "degC",
            "so": "PSU",
            "zos": "m",
        }[v]
    ds["depth"].attrs["units"] = "m"
    return ds


def write_raw_file(ds: xr.Dataset, path: Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(path)
    print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")
