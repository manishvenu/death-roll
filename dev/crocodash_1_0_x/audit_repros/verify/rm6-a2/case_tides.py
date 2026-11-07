"""Full CrocoDash flow: Case -> configure_forcings(tides) -> process_forcings
on a tiny all-ocean grid whose WEST edge is at lon XSTART (argv[2]).
Synthetic TPXO files are uniform, so every boundary should get
zamp=0.5, uamp=0.10, vamp=0.06."""
import sys, time
from pathlib import Path
import numpy as np, xarray as xr

t0 = time.time()
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
label = sys.argv[1]
xstart = float(sys.argv[2])
(S / "cases").mkdir(exist_ok=True)
(S / "input").mkdir(exist_ok=True)

grid = Grid(lenx=1.0, leny=1.0, resolution=0.1, xstart=xstart, ystart=-4.0, name="tseam")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name="tseam")
case = Case(
    cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
    caseroot=S / f"cases/audit_rm6a2v_{label}",
    inputdir=S / f"input/audit_rm6a2v_{label}",
    compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
    ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
    machine="derecho", project="ncgd0011", override=True,
)
print("case created", round(time.time() - t0), flush=True)
case.configure_forcings(
    date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
    product_name="reference_ocean", function_name="get_reference_ocean_data",
    tpxo_elevation_filepath=str(S / "tpxo/h_synth.nc"),
    tpxo_velocity_filepath=str(S / "tpxo/u_synth.nc"),
    tidal_constituents=["M2"],
)
print("configured", round(time.time() - t0), flush=True)
case.process_forcings()
print("processed", round(time.time() - t0), flush=True)

ocn = S / f"input/audit_rm6a2v_{label}/ocn"
seg_of = {}
for p in sorted(ocn.rglob("tu_*.nc")):
    tu = xr.open_dataset(p)
    tz = xr.open_dataset(str(p).replace("/tu_", "/tz_"))
    n = p.stem.split("tu_")[1]
    lonv = [c for c in tu.coords if c.startswith("lon")]
    lon = tu[lonv[0]].values if lonv else None
    msg = f"{p.name}: lon {np.nanmin(lon):.3f}..{np.nanmax(lon):.3f}" if lon is not None else p.name
    for v in (f"uamp_{n}", f"vamp_{n}"):
        a = tu[v].values
        msg += f" | {v.split('_')[0]} min={a.min():.4f} max={a.max():.4f} zeros={(a == 0).sum()}/{a.size}"
    a = tz[f"zamp_{n}"].values
    msg += f" | zamp min={a.min():.4f} max={a.max():.4f} zeros={(a == 0).sum()}/{a.size}"
    print(msg, flush=True)
