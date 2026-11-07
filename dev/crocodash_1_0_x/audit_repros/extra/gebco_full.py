import numpy as np, time
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
G = "/glade/campaign/cgd/oce/projects/CROCODILE/workshops/2026/CrocoDash/data/gebco_2026/GEBCO_2026.nc"
t = time.time()
grid = Grid(lenx=2.0, leny=2.0, resolution=0.05, xstart=-70.0, ystart=42.0, name="gom")
topo = Topo(grid, min_depth=5.0)
topo.set_from_dataset(bathymetry_path=G, longitude_coordinate_name="lon", latitude_coordinate_name="lat", vertical_coordinate_name="elevation")
d = topo.depth.values
print("full GEBCO small domain: shape", d.shape, "ocean frac", round(float((d > 0).mean()), 3), "max", float(np.nanmax(d)), "nan", int(np.isnan(d).sum()), "secs", round(time.time() - t, 1))
# spot check vs raw GEBCO at a deep-ish interior point
import xarray as xr
g = xr.open_dataset(G).sel(lat=slice(42.4, 42.5), lon=slice(-68.0, -67.9))
print("raw mean depth there", float(-g.elevation.mean()), "topo at nearest", float(d[int((42.45-42)/0.05), int((-67.95+70)/0.05)]))
