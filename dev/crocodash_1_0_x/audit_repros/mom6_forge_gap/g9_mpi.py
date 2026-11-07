"""mpi_set_depth_from_xesmf / write_to_file with a source that carries _FillValue."""
import numpy as np, xarray as xr
from pathlib import Path
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo
out = Path("g9_out"); out.mkdir(exist_ok=True)
lon = np.arange(-70, -40, 0.1) + 0.05; lat = np.arange(20, 45, 0.1) + 0.05
for name, sign, enc in [("elev_fill", -1, {"elevation": {"_FillValue": -9999.0}}),
                        ("depth_fill", 1, {"elevation": {"_FillValue": -9999.0}}),
                        ("depth_nofill", 1, {"elevation": {"_FillValue": None}})]:
    d = xr.Dataset({"elevation": (("lat", "lon"), sign * np.full((lat.size, lon.size), 1000.0))}, coords={"lon": lon, "lat": lat})
    p = out / f"{name}.nc"; d.to_netcdf(p, encoding=enc)
    g = Grid(lenx=6.0, leny=5.0, resolution=1.0, xstart=-60.0, ystart=30.0, name="m")
    t = Topo(g, min_depth=10.0)
    try:
        t.mpi_set_depth_from_xesmf(bathymetry_path=str(p), longitude_coordinate_name="lon", latitude_coordinate_name="lat",
                                   vertical_coordinate_name="elevation", is_input_positive_below_msl=(sign == 1),
                                   output_dir=out, verbose=False)
        print(name, "mpi prep OK")
    except Exception as e:
        print(name, "mpi prep ERR:", type(e).__name__, str(e)[:150])
