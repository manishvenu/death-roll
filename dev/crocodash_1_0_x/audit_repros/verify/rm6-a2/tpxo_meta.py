import xarray as xr, numpy as np
D="/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/tpxo/"
for f in ("h_tpxo9.v1.nc","u_tpxo9.v1.nc"):
    ds=xr.open_dataset(D+f)
    print(f, dict(ds.sizes))
    for v in ds.data_vars:
        print("  ",v, ds[v].dims)
    for c in ("lon_z","lat_z","lon_u","lat_u","lon_v","lat_v"):
        if c in ds:
            a=ds[c].values
            print("  ",c, ds[c].dims, a.shape, "min",a.min(),"max",a.max(), "row0[:3]",a[:3,0], "col0[:3]",a[0,:3])
    print("  con", ds["con"].values if "con" in ds else None)
