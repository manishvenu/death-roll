import sys, re
from pathlib import Path
import numpy as np, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case
S = Path(sys.argv[1])
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=40.0, name="gw")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0); d = topo.depth.copy(); d[:, :2] = 0.0; topo.depth = d; print("land cols:", int((topo.depth.values[:, :2] == 0).sum()))
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="gw")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S/"cases/audit_gwrj", inputdir=S/"input/audit_gwrj", compset="GWR_JRA",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="TL319",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(date_range=["2019-06-05 00:00:00", "2019-06-08 00:00:00"],
                        product_name="reference_ocean", function_name="get_reference_ocean_data",
                        restore_ice=True, cice_product_name="reference_ice", cice_function_name="get_reference_ice_data",
                        ww3_obc_product_name="CESM-WW3-JRA", ww3_obc_function_name="get_cesm_ww3_jra_spectra")
case.process_forcings()
inp = S/"input/audit_gwrj"; cr = S/"cases/audit_gwrj"
for sub in ["ice", "wav"]:
    for f in sorted((inp/sub).glob("*")):
        line = f"{sub}/{f.name} {f.stat().st_size}B"
        if f.suffix == ".nc":
            ds = xr.open_dataset(f, decode_times=False)
            bad = [v for v in ds.data_vars if ds[v].dtype.kind == "f" and ds[v].size and np.isnan(ds[v].values).all()]
            line += f" vars={list(ds.data_vars)[:8]} all-NaN={bad} dims={dict(ds.sizes)}"
            ds.close()
        print(line)
for nl in ["user_nl_cice", "user_nl_ww3"]:
    t = (cr/nl).read_text()
    paths = re.findall(r"['\"](/[^'\"]+)['\"]", t)
    print(nl, "paths:", [(p.split("/")[-1], Path(p).exists()) for p in paths])
for f in sorted((inp/"mapping").glob("*.nc")) if (inp/"mapping").exists() else []:
    m = xr.open_dataset(f)
    nx = grid.tlon.shape[1]
    cols = (m["row"].values - 1) % nx
    print("map", f.name, "n_s", m.sizes.get("n_s"), "dest columns receiving runoff:", sorted(set(cols.tolist())))
    m.close()
# spectra sanity: Hs from E(f,theta)
for f in sorted((inp/"wav").glob("*.nc")):
    ds = xr.open_dataset(f, decode_times=False)
    names = list(ds.data_vars)
    ef = next((v for v in names if ds[v].ndim >= 3 and ("efth" in v.lower() or "spec" in v.lower() or v.lower() in ("e", "ef"))), None)
    if ef:
        E = ds[ef].values
        print("SPEC", f.name, ef, ds[ef].dims, "nan", float(np.isnan(E).mean()), "min", float(np.nanmin(E)), "max", float(np.nanmax(E)), "units", ds[ef].attrs.get("units"))
        fr = next((ds[c].values for c in ds.coords if "freq" in c.lower()), None); th = next((ds[c].values for c in ds.coords if "dir" in c.lower()), None)
        if fr is not None and th is not None and E.shape[-2:] == (len(fr), len(th)):
            dth = 2*np.pi/len(th); df = np.gradient(fr)
            m0 = (E * df[:, None] * dth).sum(axis=(-2, -1)); hs = 4*np.sqrt(m0)
            print("  Hs range", float(np.nanmin(hs)), float(np.nanmax(hs)), "| dir axis", th[:4], "...", "freq", fr[:2], fr[-1])
    ds.close()
