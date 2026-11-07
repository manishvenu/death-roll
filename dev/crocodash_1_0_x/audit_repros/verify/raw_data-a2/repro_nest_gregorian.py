"""Nest a child in a GREGORIAN parent MOM6 run via CESM_MOM_OUTPUT, window spanning 2020-02-29."""
import sys, re, time, traceback, shutil
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent / "run"
shutil.rmtree(S, ignore_errors=True)
for d in ("parent", "cases", "input"):
    (S / d).mkdir(parents=True, exist_ok=True)

# Synthetic parent: native MOM6 daily-mean output of a GREGORIAN run (what a
# CrocoDash GLORYS case writes), 2020-02-20 .. 2020-03-08.
t = pd.date_range("2020-02-20 12:00", "2020-03-08 12:00", freq="D")
xh = np.arange(-64.0, -52.0, 0.25); yh = np.arange(26.0, 38.0, 0.25)
xq = xh + 0.125; yq = yh + 0.125; zl = np.array([5.0, 50.0, 200.0, 600.0, 1500.0])
nt, nz = len(t), len(zl)
parent = xr.Dataset(
    {
        "zos": (("time", "yh", "xh"), np.zeros((nt, yh.size, xh.size))),
        "thetao": (("time", "z_l", "yh", "xh"), np.full((nt, nz, yh.size, xh.size), 15.0)),
        "so": (("time", "z_l", "yh", "xh"), np.full((nt, nz, yh.size, xh.size), 35.0)),
        "uo": (("time", "z_l", "yh", "xq"), np.full((nt, nz, yh.size, xq.size), 0.1)),
        "vo": (("time", "z_l", "yq", "xh"), np.zeros((nt, nz, yq.size, xh.size))),
    },
    coords={"time": t, "xh": xh, "yh": yh, "xq": xq, "yq": yq,
            "z_l": ("z_l", zl, {"units": "meter"})},
)
parent.to_netcdf(S / "parent" / "parent.mom6.h.native.nc",
                 encoding={"time": {"units": "days since 2020-01-01 00:00:00", "calendar": "gregorian"}})

grid = Grid(lenx=2.0, leny=2.0, resolution=0.5, xstart=-59.0, ystart=31.0, name="a2nest")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="a2nest")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases" / "audit_verify_a2_nest", inputdir=S / "input" / "audit_verify_a2_nest",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
case.configure_forcings(
    date_range=["2020-02-27 00:00:00", "2020-03-02 00:00:00"],
    product_name="CESM_MOM_OUTPUT", function_name="get_mom6_output_data",
    function_overrides={"dataset_path": str(S / "parent")},
)
xml = (case.caseroot / "env_run.xml").read_text()
print("child CALENDAR in env_run.xml:",
      re.search(r'<entry id="CALENDAR" value="([^"]+)"', xml).group(1), flush=True)
print("product calendar:", case.forcing_product.calendar, flush=True)
try:
    case.process_forcings()
    print("process_forcings finished without error", flush=True)
except Exception as e:
    print("process_forcings FAILED:", type(e).__name__, str(e)[:400], flush=True)
    traceback.print_exc(limit=-6)
for f in sorted((case.inputdir / "extract_forcings").rglob("*.nc"))[:20]:
    print("  ", f.relative_to(case.inputdir))
for f in sorted((case.inputdir / "ocnice").glob("*.nc")) if (case.inputdir / "ocnice").exists() else []:
    print("  ocnice:", f.name)
