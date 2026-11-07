import numpy as np, xarray as xr, xesmf as xe
src = xr.open_dataset("r5/ref_polar.nc")   # reference_ocean output for lat 88..89.9, lon -180..180
print("source lat:", src.latitude.values[[0,-3,-2,-1]], " lon ends:", src.longitude.values[[0,1,-2,-1]])
tlat, tlon = np.meshgrid(np.linspace(88.2, 89.8, 5), np.linspace(-170, 170, 7), indexing="ij")
tgt = xr.Dataset(coords={"lat": (("ny","nx"), tlat), "lon": (("ny","nx"), tlon)})
for ign in (False, True):
    try:
        r = xe.Regridder(src.rename({"latitude":"lat","longitude":"lon"}), tgt, "bilinear", locstream_out=False, unmapped_to_nan=True, ignore_degenerate=ign)
        out = r(src.temp.isel(time=0, depth=0).rename({"latitude":"lat","longitude":"lon"}))
        exp = 28*np.cos(np.deg2rad(tlat))*np.exp(-5/500)+2
        print(f"ignore_degenerate={ign}: OK, max abs err vs analytic {np.nanmax(np.abs(out.values-exp)):.3f}, NaNs {int(np.isnan(out.values).sum())}")
    except Exception as e:
        print(f"ignore_degenerate={ign}: {type(e).__name__}: {str(e)[:200]}")
