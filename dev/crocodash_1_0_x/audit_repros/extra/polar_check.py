import sys
from pathlib import Path
import numpy as np, xarray as xr
from scipy.spatial import cKDTree
I = Path(sys.argv[1]); ocn = I/"ocn"
def xyz(lon, lat):
    lo, la = np.deg2rad(lon), np.deg2rad(lat)
    return np.stack([np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)], -1)
hg = xr.open_dataset(next(ocn.glob("ocean_hgrid_*.nc")))
tlon = hg.x.values[1::2, 1::2]; tlat = hg.y.values[1::2, 1::2]; ang = hg.angle_dx.values[1::2, 1::2]
print("angle_dx units attr", hg.angle_dx.attrs.get("units"), "range", float(ang.min()), float(ang.max()))
tr = xr.open_dataset(ocn/"init_tracers.nc", decode_times=False); vel = xr.open_dataset(ocn/"init_vel.nc", decode_times=False)
print("init_tracers vars", list(tr.data_vars), "dims", dict(tr.sizes)); print("init_vel", {k: v.dims for k, v in vel.data_vars.items()})
T = tr["temp"].values[0]; S = tr["salt"].values[0]
topo = xr.open_dataset(next(ocn.glob("ocean_topog_*.nc"))).depth.values
wet = topo > 0
print("IC surf T range (wet)", float(np.nanmin(T[wet])), float(np.nanmax(T[wet])), "S", float(np.nanmin(S[wet])), float(np.nanmax(S[wet])), "nan in wet", int(np.isnan(T[wet]).sum()))
u = vel["u"].values[0]; v = vel["v"].values[0]
print("u shape", u.shape, "v shape", v.shape, "T shape", T.shape)
# average to T points (symmetric: u has nx+1, v has ny+1)
uT = 0.5*(u[:, :-1] + u[:, 1:]) if u.shape[1] == T.shape[1]+1 else u
vT = 0.5*(v[:-1, :] + v[1:, :]) if v.shape[0] == T.shape[0]+1 else v
raw = xr.open_dataset(I/"extract_forcings/raw_data/ic_unprocessed.nc")
r0 = raw.isel(time=0, depth=0) if "depth" in raw.dims else raw.isel(time=0)
LO, LA = np.meshgrid(raw.longitude.values, raw.latitude.values)
tree = cKDTree(xyz(LO.ravel(), LA.ravel()))
_, idx = tree.query(xyz(tlon.ravel(), tlat.ravel()))
ue = r0.uo.values.ravel()[idx].reshape(T.shape); vn = r0.vo.values.ravel()[idx].reshape(T.shape)
Traw = r0.thetao.values.ravel()[idx].reshape(T.shape)
ok = wet & np.isfinite(ue) & np.isfinite(uT) & (np.hypot(ue, vn) > 0.02)
a = np.deg2rad(ang) if np.abs(ang).max() > 2*np.pi else ang
ug = ue*np.cos(a) + vn*np.sin(a); vg = -ue*np.sin(a) + vn*np.cos(a)
def corr(x, y): return float(np.corrcoef(x[ok], y[ok])[0, 1])
print("n pts", int(ok.sum()), "| corr(IC u, raw rotated ug)", round(corr(uT, ug), 3), "corr(IC v, vg)", round(corr(vT, vg), 3),
      "| corr(IC u, raw east)", round(corr(uT, ue), 3), "corr(IC v, raw north)", round(corr(vT, vn), 3))
# opposite rotation sign
ug2 = ue*np.cos(a) - vn*np.sin(a); vg2 = ue*np.sin(a) + vn*np.cos(a)
print("corr with opposite sign rotation", round(corr(uT, ug2), 3), round(corr(vT, vg2), 3))
print("speed ratio IC/raw median", float(np.median(np.hypot(uT, vT)[ok] / np.hypot(ue, vn)[ok])))
print("T corr IC vs raw nearest", round(float(np.corrcoef(T[wet & np.isfinite(Traw)], Traw[wet & np.isfinite(Traw)])[0, 1]), 3))
for i in range(1, 5):
    o = xr.open_dataset(ocn/f"forcing_obc_segment_00{i}.nc", decode_times=False)
    t = o[f"temp_segment_00{i}"].values; t = np.where(np.abs(t) > 1e10, np.nan, t)
    uu = o[f"u_segment_00{i}"].values; uu = np.where(np.abs(uu) > 1e10, np.nan, uu)
    print(f"seg{i} dims", dict(o[f'temp_segment_00{i}'].sizes), "T", round(float(np.nanmin(t)), 2), round(float(np.nanmax(t)), 2), "nanfrac", round(float(np.isnan(t).mean()), 3), "|u|max", round(float(np.nanmax(np.abs(uu))), 3), "ntime", o.sizes["time"])
ice = xr.open_dataset(I/"ice/cice_forcing.nc", decode_times=False)
print("cice vars", list(ice.data_vars)[:20], dict(ice.sizes))
for vname in ("aice", "aicen", "vicen", "hi", "vice"):
    if vname in ice:
        x = ice[vname].values; print("ice", vname, "min", float(np.nanmin(x)), "max", float(np.nanmax(x)), "mean", round(float(np.nanmean(x)), 3), "nan", float(np.isnan(x).mean()))
