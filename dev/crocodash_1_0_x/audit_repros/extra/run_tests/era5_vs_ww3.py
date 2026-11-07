import sys, glob, numpy as np, xarray as xr
S = sys.argv[1]
e = xr.open_dataset(f"{S}/gap3/era5/era5_spectra.nc")
def stats(E, fr, th_deg):
    df = np.gradient(fr); dth = np.deg2rad(360 / len(th_deg))
    m0 = (E * df[:, None] * dth).sum(axis=(-2, -1)); hs = 4 * np.sqrt(m0)
    D = np.deg2rad(th_deg); a = (E * df[:, None]).sum(-2)
    md = np.rad2deg(np.arctan2((a * np.sin(D)).sum(-1), (a * np.cos(D)).sum(-1))) % 360
    return hs, md
rows = []
for f in sorted(glob.glob(f"{S}/gap2/input/audit_gwrj/wav/ww3.point*_spec.nc")):
    w = xr.open_dataset(f); la, lo = float(w.latitude[0]), float(w.longitude[0])
    if not (39 <= la <= 45 and -61 <= lo <= -55): continue
    for tt in ["2019-06-05T00:00", "2019-06-05T06:00", "2019-06-05T12:00", "2019-06-05T18:00"]:
        ww = w.sel(time=np.datetime64(tt))
        hw, mw = stats(ww.efth.values[:, :, 0, 0], w.frequency.values, w.direction.values)
        ee = e.sel(time=np.datetime64(tt), latitude=la, longitude=lo, method="nearest")
        he, me = stats(ee.efth.values, e.frequency.values, e.direction.values)
        rows.append((la, lo, tt, float(hw), float(he), float(mw), float(me)))
r = np.array([x[3:] for x in rows])
d_same = ((r[:, 3] - r[:, 2] + 180) % 360) - 180
d_flip = ((r[:, 3] + 180 - r[:, 2] + 180) % 360) - 180
print("n matched (point,time):", len(rows))
print("Hs WW3-JRA median", round(float(np.median(r[:, 0])), 2), "| Hs ERA5 median", round(float(np.median(r[:, 1])), 2), "| corr", round(float(np.corrcoef(r[:, 0], r[:, 1])[0, 1]), 2))
print("ERA5 raw dir vs WW3 'to' dir: median |diff| as-is", round(float(np.median(np.abs(d_same))), 1), "deg | after +180", round(float(np.median(np.abs(d_flip))), 1), "deg")
for x in rows[:6]: print("  ", x[:3], "Hs w/e", round(x[3], 2), round(x[4], 2), "dir WW3(to)", round(x[5]), "ERA5 raw", round(x[6]))
