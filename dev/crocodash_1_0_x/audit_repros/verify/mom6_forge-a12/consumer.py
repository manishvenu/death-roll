import numpy as np, xarray as xr
c = xr.open_dataset("cice_grid.nc").set_coords(["tlat", "tlon", "ulat", "ulon"])
try:
    import cf_xarray  # noqa
    lat = c.cf["latitude"]
    print("cf_xarray picks latitude =", lat.name, "units", lat.attrs["units"], "range", float(lat.min()), float(lat.max()))
except Exception as e:
    print("cf_xarray:", type(e).__name__, e)
try:
    import pint
    u = pint.UnitRegistry()
    h = xr.open_dataset("hgrid.nc")
    q = u.Quantity(float(h.angle_dx[0, 0]), h.angle_dx.attrs["units"]).to("degree")
    print("pint reading angle_dx[0,0] via its units attr ->", q)
except Exception as e:
    print("pint:", type(e).__name__, e)
