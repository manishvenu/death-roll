import numpy as np, xarray as xr
from mom6_forge.utils import longitude_slicer
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
lon = np.arange(0.0, 360.0, 1.0); lat = np.arange(-89.5, 90, 1.0)
ds = xr.Dataset({"v": (("lat","lon"), np.zeros((lat.size, lon.size)))}, coords={"lon": lon, "lat": lat})
s = longitude_slicer(ds, [10.0, 20.0], "lon")
print("longitude_slicer([10,20]) ->", float(s.lon.min()), float(s.lon.max()), s.lon.size)
# landfrac with a variable not named 'landfrac'
lf = xr.Dataset({"LANDFRAC": (("lat","lon"), np.zeros((lat.size, lon.size)))}, coords={"lon": lon, "lat": lat})
lf.to_netcdf("r14_landfrac.nc")
g = Grid(lenx=6.0, leny=4.0, resolution=1.0, xstart=10.0, ystart=30.0, name="lf")
t = Topo(g, min_depth=10.0); t.set_flat(100.0)
try:
    t.generate_mask_from_landfrac_file("r14_landfrac.nc", "LANDFRAC", "lon", "lat")
    print("landfrac ok")
except Exception as e:
    print("generate_mask_from_landfrac_file:", type(e).__name__, e)
