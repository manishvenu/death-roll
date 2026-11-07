import xarray as xr
from mom6_forge.grid import Grid
ds = xr.open_dataset("r3_out/hgrid.nc").load()
ds.x.attrs["units"] = "degree_east"; ds.y.attrs["units"] = "degree_north"
ds.to_netcdf("r12_hgrid_fre_units.nc")
Grid.check_supergrid(ds); print("check_supergrid accepts degree_east/degree_north")
try:
    g = Grid.from_supergrid("r12_hgrid_fre_units.nc"); print("from_supergrid ok", g.tlon.shape)
except AssertionError as e:
    print("from_supergrid AssertionError:", e)
