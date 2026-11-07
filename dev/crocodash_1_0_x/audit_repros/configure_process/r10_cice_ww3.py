"""R10: CICE + WW3 compset with reference products, end to end; then reconfigure
with a later date range and reprocess."""
import sys, time, re, json
from pathlib import Path
import xarray as xr
t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).parent
name = "audit_cp_10"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=60.0, name="acp10")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="v")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases"/name, inputdir=S/"input"/name,
            compset="1850_DATM%JRA_SLND_CICE_MOM6%REGIONAL_SROF_SGLC_WW3",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="TL319",
            machine="derecho", project="ncgd0011", override=True)
print("created", time.time() - t0, flush=True)
cr = S/"cases"/name; inp = S/"input"/name
kw = dict(product_name="reference_ocean", function_name="get_reference_ocean_data",
          boundaries=["south", "east"],
          ww3_obc_product_name="reference_waves", ww3_obc_function_name="get_reference_wave_spectra",
          cice_product_name="reference_ice", cice_function_name="get_reference_ice_data", restore_ice=True)
case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"], **kw)
for f in ("user_nl_cice", "user_nl_ww3"):
    print("=====", f)
    print("".join(l for l in open(cr/f) if not l.startswith("!") or "CrocoDash" in l))
case.process_forcings()
print("processed", time.time() - t0, flush=True)
print("wav:", sorted(p.name for p in (inp/"wav").iterdir()))
print("spec.list:", open(inp/"wav"/"spec.list").read())
ds = xr.open_dataset(inp/"wav"/"ww3.point1_spec.nc", decode_times=False)
print("spec time:", ds.time.values, ds.time.attrs)
ds.close()
ds = xr.open_dataset(inp/"ice"/"cice_forcing.nc")
print("cice dims:", dict(ds.sizes), list(ds.data_vars)[:8])
ds.close()
# Reconfigure with a later window
case.configure_forcings(date_range=["2020-01-10 00:00:00", "2020-01-12 00:00:00"], **kw)
case.process_forcings()
ds = xr.open_dataset(inp/"wav"/"ww3.point1_spec.nc", decode_times=False)
print("spec time after reconfigure:", ds.time.values[[0, -1]], ds.time.attrs)
ds.close()
