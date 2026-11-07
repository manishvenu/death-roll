"""Run process_forcings' driver (as `crocodash process --all` does) for ic+bc.

argv[1] = config.json; optional argv[2] = absolute path of ONE output file whose
xarray write is slowed down (each dask block sleeps) so the parent can SIGKILL
the process while that file is half-written. Nothing else is changed.
"""
import os, sys, time
import xarray as xr

cfg = sys.argv[1]
slow = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
if slow:
    _orig = xr.Dataset.to_netcdf

    def _sleepy(x):
        time.sleep(0.3)
        return x

    def to_netcdf(self, path=None, *a, **k):
        if path is not None and os.path.abspath(str(path)) == slow:
            print("SLOW WRITE STARTED", path, flush=True)
            ds = self.copy()
            for v in ds.data_vars:
                arr = ds[v]
                if arr.ndim == 0:
                    continue
                lead = arr.dims[:-2] if arr.ndim > 2 else arr.dims[:1]
                arr = arr.chunk({d: 1 for d in lead})
                ds[v] = arr.copy(data=arr.data.map_blocks(_sleepy, dtype=arr.dtype))
            import dask
            with dask.config.set(scheduler="synchronous"):  # one block at a time
                return _orig(ds, path, *a, **k)
        return _orig(self, path, *a, **k)

    xr.Dataset.to_netcdf = to_netcdf

from CrocoDash.forcing.driver import run_workflow
run_workflow(config_path=cfg, ic=True, bc=True)
print("PROCESS_FORCINGS RETURNED NORMALLY", flush=True)
