"""mom6_forge-a11: generate_mask_from_landfrac_file ignores landfrac_name / xcoord_name / ycoord_name."""
import os, traceback
import numpy as np
import xarray as xr
import mom6_forge, mom6_forge.topo as T
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo

print("mom6_forge from", mom6_forge.__file__)
HERE = os.path.dirname(os.path.abspath(__file__))

grid = Grid(lenx=10.0, leny=10.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="a11")

def fresh_topo():
    t = Topo(grid, min_depth=10.0)
    t.set_flat(1000.0)
    return t

# Synthetic land fraction on a 0.5 deg lat/lon grid: land (1) west of lon=-55, ocean (0) east.
lon = np.arange(-65.0, -44.9, 0.5)
lat = np.arange(25.0, 45.1, 0.5)
frac = np.where(lon[None, :] < -55.0, 1.0, 0.0) * np.ones((lat.size, 1))

def write(fname, varname, xname, yname, cf_attrs=False):
    xa = {"units": "degrees_east"} if cf_attrs else {}
    ya = {"units": "degrees_north"} if cf_attrs else {}
    ds = xr.Dataset({varname: ((yname, xname), frac)},
                    coords={xname: (xname, lon, xa), yname: (yname, lat, ya)})
    p = os.path.join(HERE, fname)
    ds.to_netcdf(p)
    return p

def run(label, path, *args):
    t = fresh_topo()
    try:
        t.generate_mask_from_landfrac_file(path, *args)
        m = t.tmask.values
        print(f"[{label}] OK  ocean cells={int(m.sum())}/{m.size}  first row={m[0].tolist()}")
    except Exception as e:
        print(f"[{label}] FAIL {type(e).__name__}: {e}")
        traceback.print_exc(limit=-2)

# 0. baseline: variable literally named landfrac, coords lon/lat -> expected to work
run("baseline landfrac/lon/lat", write("lf_baseline.nc", "landfrac", "lon", "lat"), "landfrac", "lon", "lat")
# 1. CAM/CLM-style variable name LANDFRAC (validated by the assert, then ignored)
run("LANDFRAC/lon/lat", write("lf_upper.nc", "LANDFRAC", "lon", "lat"), "LANDFRAC", "lon", "lat")
# 2. file with BOTH 'landfrac' and the requested field 'frac' (different values): which one is used?
p = os.path.join(HERE, "lf_both.nc")
xr.Dataset({"landfrac": (("lat", "lon"), np.zeros_like(frac)),   # all ocean
            "frac": (("lat", "lon"), frac)},                        # west half land
           coords={"lon": lon, "lat": lat}).to_netcdf(p)
run("both: ask for 'frac'", p, "frac", "lon", "lat")
run("both: ask for 'landfrac'", p, "landfrac", "lon", "lat")
# 3. coordinate names other than lon/lat, no CF attrs
run("landfrac/x/y no attrs", write("lf_xy.nc", "landfrac", "x", "y"), "landfrac", "x", "y")
# 4. coordinate names other than lon/lat but CF units attrs (cf_xarray may find them)
run("landfrac/longitude/latitude CF attrs", write("lf_cf.nc", "landfrac", "longitude", "latitude", cf_attrs=True), "landfrac", "longitude", "latitude")

# 5. monkeypatched fix: use ds[landfrac_name] and rename coords to lon/lat
_orig_open = xr.open_dataset
def patched(self, landfrac_filepath, landfrac_name, xcoord_name, ycoord_name, cutoff_frac=0.5, method="bilinear"):
    ds = _orig_open(landfrac_filepath)
    ds = ds[[landfrac_name]].rename({xcoord_name: "lon", ycoord_name: "lat"}).rename({landfrac_name: "landfrac"})
    tmp = os.path.join(HERE, "_patched_tmp.nc")
    ds.to_netcdf(tmp)
    return orig_method(self, tmp, "landfrac", "lon", "lat", cutoff_frac, method)
orig_method = T.Topo.generate_mask_from_landfrac_file
T.Topo.generate_mask_from_landfrac_file = patched
print("--- with monkeypatched fix ---")
run("fix LANDFRAC/lon/lat", os.path.join(HERE, "lf_upper.nc"), "LANDFRAC", "lon", "lat")
run("fix both: ask for 'frac'", os.path.join(HERE, "lf_both.nc"), "frac", "lon", "lat")
run("fix landfrac/x/y", os.path.join(HERE, "lf_xy.nc"), "landfrac", "x", "y")
