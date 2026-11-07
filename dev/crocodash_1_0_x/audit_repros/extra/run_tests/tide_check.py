"""Compare a CrocoDash M2-tide run's SSH with an independent TPXO prediction.

usage: tide_check.py <rundir> <hgrid.nc> <h_tpxo.nc>
Fits mean + M2 to hourly SSH (days 2-3) at cells next to each boundary midpoint and at the centre,
and compares amplitude and Greenwich phase with TPXO M2 at the same points, predicted with
standard astronomical arguments (Meeus mean longitudes; nodal f/u reported separately).
"""
import sys, glob
import numpy as np, xarray as xr, pandas as pd

rundir, hgrid_path, tpxo_path = sys.argv[1:4]
files = sorted(glob.glob(f"{rundir}/*.mom6.h.sfc*.nc"))
ds = xr.open_mfdataset(files, decode_times=False)
ssh = ds["SSH"].load()
import cftime; times = pd.to_datetime([t.isoformat() for t in cftime.num2date(ssh.time.values, ds.time.attrs["units"], calendar="proleptic_gregorian")], format="ISO8601")
H = (times - pd.Timestamp("2020-01-01")).total_seconds().values / 3600.0
print("hourly records", len(H), "from", times[0], "to", times[-1])

hg = xr.open_dataset(hgrid_path)
tlon = hg.x.values[1::2, 1::2]; tlat = hg.y.values[1::2, 1::2]
ny, nx = tlon.shape
pts = {"south mid": (0, nx // 2), "north mid": (ny - 1, nx // 2), "west mid": (ny // 2, 0),
       "east mid": (ny // 2, nx - 1), "centre": (ny // 2, nx // 2)}

tp = xr.open_dataset(tpxo_path)
cons = [c.decode().strip() if isinstance(c, bytes) else str(c).strip() for c in tp["con"].values]
k = [c.lower() for c in cons].index("m2")
lonz = tp["lon_z"].values; latz = tp["lat_z"].values
ha = tp["ha"].values[k]; hp = tp["hp"].values[k]  # (nx, ny) in TPXO9 v1

# astronomical arguments (degrees), Tc = Julian centuries since J2000.0
Tc = ((times - pd.Timestamp("2000-01-01 12:00")).total_seconds().values / 86400.0) / 36525.0
s = 218.3164477 + 481267.88123421 * Tc
h = 280.46646 + 36000.76983 * Tc
N = 125.04452 - 1934.136261 * Tc
V = (30.0 * H + 2 * h - 2 * s) % 360.0
f = 1.0007 - 0.0373 * np.cos(np.deg2rad(N)); u = -2.14 * np.sin(np.deg2rad(N))
print(f"nodal factors over the run: f={f.mean():.4f}, u={u.mean():.2f} deg")

w = 28.9841042 * np.pi / 180.0
sel = H >= 24.0
for name, (j, i) in pts.items():
    y = ssh.values[:, j, i]
    A = np.column_stack([np.ones(sel.sum()), np.cos(w * H[sel]), np.sin(w * H[sel])])
    c, *_ = np.linalg.lstsq(A, y[sel], rcond=None)
    amp_m = np.hypot(c[1], c[2])
    # model phase as Greenwich lag G: y = amp*cos(V+u-G) -> compare via fitted series
    lo = tlon[j, i] % 360.0; la = tlat[j, i]
    ii = np.abs(lonz - lo).argmin() if lonz.ndim == 1 else None
    if lonz.ndim == 1:
        jj = np.abs(latz - la).argmin(); A_t, G_t = ha[ii, jj], hp[ii, jj]
    else:
        d = (lonz - lo) ** 2 + (latz - la) ** 2; ii, jj = np.unravel_index(d.argmin(), d.shape); A_t, G_t = ha[ii, jj], hp[ii, jj]
    pred_nodal = f * A_t * np.cos(np.deg2rad(V + u - G_t))
    pred_plain = A_t * np.cos(np.deg2rad(V - G_t))
    model = c[0] + c[1] * np.cos(w * H) + c[2] * np.sin(w * H)
    def lag_deg(a, b):  # phase of b relative to a, deg (positive = b lags a)
        xa = np.linalg.lstsq(np.column_stack([np.cos(w * H), np.sin(w * H)]), a, rcond=None)[0]
        xb = np.linalg.lstsq(np.column_stack([np.cos(w * H), np.sin(w * H)]), b, rcond=None)[0]
        return (np.rad2deg(np.arctan2(xb[1], xb[0]) - np.arctan2(xa[1], xa[0])) + 180) % 360 - 180
    print(f"{name:9s} ({la:.2f},{lo - 360:.2f}) TPXO A={A_t:.3f} m G={G_t:.1f} | model amp={amp_m:.3f} m "
          f"ratio={amp_m / A_t:.3f} | model lag vs TPXO prediction: {lag_deg(pred_plain, model - c[0]):+.1f} deg "
          f"(with nodal {lag_deg(pred_nodal, model - c[0]):+.1f})")
