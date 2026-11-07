import sys, numpy as np, netCDF4
F = sys.argv[1]; st = int(sys.argv[2])
with netCDF4.Dataset(F) as nc:
    A = np.rad2deg(nc["ANGLE"][::st, ::st].filled(np.nan)); la = nc["ULAT"][::st, ::st].filled(np.nan); lo = nc["ULONG"][::st, ::st].filled(np.nan) % 360
pts = {"Gulf of Alaska": (57, 215), "Labrador Sea": (58, 305), "Nordic Seas": (70, 2), "North Sea": (56, 3), "Gulf of Maine": (43, 292), "Gulf of Mexico": (25, 270), "Tropical Pacific": (0, 200), "Southern Ocean": (-55, 180)}
for name, (y, x) in pts.items():
    d = (la - y) ** 2 + (((lo - x + 180) % 360 - 180) * np.cos(np.deg2rad(y))) ** 2
    j, i = np.unravel_index(np.nanargmin(d), d.shape)
    print(f"{name:16s} ULAT={la[j,i]:6.2f} ULONG={lo[j,i]:7.2f} ANGLE={A[j,i]:7.2f} deg")
print("max |ANGLE| north of 60N: %.1f deg" % np.nanmax(np.abs(A[la > 60])))
