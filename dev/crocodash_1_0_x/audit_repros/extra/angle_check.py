import sys, numpy as np, xarray as xr
hg = xr.open_dataset(sys.argv[1])
x = hg.x.values; y = hg.y.values; ang = hg.angle_dx.values
# geometric direction of +x (i increasing) at T points, CCW from east, in degrees
j = slice(1, None, 2); 
xl, xr_ = x[1::2, 0:-2:2], x[1::2, 2::2]; yl, yr = y[1::2, 0:-2:2], y[1::2, 2::2]
dlon = ((xr_ - xl + 180) % 360) - 180; latm = np.deg2rad(y[1::2, 1::2])
geo = np.rad2deg(np.arctan2(yr - yl, dlon*np.cos(latm)))
a = ang[1::2, 1::2]
d = ((a - geo + 180) % 360) - 180; dneg = ((-a - geo + 180) % 360) - 180
print("angle_dx vs geometric (deg): median |diff| same sign", round(float(np.median(np.abs(d))), 3), "| with sign flipped", round(float(np.median(np.abs(dneg))), 3))
print("sample (angle_dx, geometric):", [(round(float(a[k, l]), 1), round(float(geo[k, l]), 1)) for k, l in [(0, 0), (0, 39), (39, 0), (20, 5), (5, 20)]])
