"""Verify raw_data-a1: CESM-POP UVEL/VVEL are grid-x/grid-y components, but
CrocoDash hands them to regional-mom6 as east/north.

Synthetic POP tseries archive on a GENUINELY rotated source mesh near the equator:
grid-x points 30 deg CCW of east (TLONG/TLAT geometry and ANGLE agree).
True ocean flow: purely EASTWARD 0.5 m/s, v_north = 0.
Stored the way POP stores it (grid components):
    UVEL =  u_e*cos(A) + v_n*sin(A) =  50*cos30 = 43.30 cm/s
    VVEL = -u_e*sin(A) + v_n*cos(A) = -50*sin30 = -25.00 cm/s
Target: plain lat-lon MOM6 grid (angle 0) -> correct OBC/IC is u=0.5, v=0.
Run through the public flow: Case -> configure_forcings(CESM_POP_OUTPUT) -> process_forcings.
"""
import sys, time, shutil
from pathlib import Path
import numpy as np, xarray as xr, cftime

S = Path(sys.argv[1]).resolve()
A = np.deg2rad(30.0)


def make_pop_archive(root, year=2000):
    root.mkdir(parents=True, exist_ok=True)
    d = 0.25
    ii, jj = np.meshgrid(np.arange(-48, 49), np.arange(-48, 49))  # (nlat, nlon)
    # rotated mesh: grid-x direction = (cos A, sin A) in (east, north), centered at 201E, 0N
    TLONG = 201.0 + (ii * np.cos(A) - jj * np.sin(A)) * d
    TLAT = 0.0 + (ii * np.sin(A) + jj * np.cos(A)) * d
    # U points: NE corner of T cell (half a cell along +x and +y)
    ULONG = 201.0 + ((ii + .5) * np.cos(A) - (jj + .5) * np.sin(A)) * d
    ULAT = 0.0 + ((ii + .5) * np.sin(A) + (jj + .5) * np.cos(A)) * d
    nlat, nlon = TLAT.shape
    nmon = 12
    times = [cftime.DatetimeNoLeap(year + (m + 1) // 12, (m + 1) % 12 + 1, 1) for m in range(nmon)]
    z_t = np.array([500., 5000., 20000., 50000., 100000., 150000.])  # cm
    u_e, v_n = 50.0, 0.0  # cm/s, earth-relative truth
    UVEL = u_e * np.cos(A) + v_n * np.sin(A)
    VVEL = -u_e * np.sin(A) + v_n * np.cos(A)
    spec = {
        "SSH": (("time", "nlat", "nlon"), 10.0, "centimeter", "Sea Surface Height", "TLONG TLAT time"),
        "TEMP": (("time", "z_t", "nlat", "nlon"), 15.0, "degC", "Potential Temperature", "TLONG TLAT z_t time"),
        "SALT": (("time", "z_t", "nlat", "nlon"), 35.0, "gram/kilogram", "Salinity", "TLONG TLAT z_t time"),
        "UVEL": (("time", "z_t", "nlat", "nlon"), UVEL, "centimeter/s", "Velocity in grid-x direction", "ULONG ULAT z_t time"),
        "VVEL": (("time", "z_t", "nlat", "nlon"), VVEL, "centimeter/s", "Velocity in grid-y direction", "ULONG ULAT z_t time"),
    }
    for v, (dims, val, units, ln, crd) in spec.items():
        shape = [{"time": nmon, "z_t": len(z_t), "nlat": nlat, "nlon": nlon}[k] for k in dims]
        ds = xr.Dataset(
            {v: (dims, np.full(shape, val, dtype="f4"), {"units": units, "long_name": ln})},
            coords={
                "time": ("time", times),
                "z_t": ("z_t", z_t, {"units": "centimeters"}),
                "TLAT": (("nlat", "nlon"), TLAT), "TLONG": (("nlat", "nlon"), TLONG),
                "ULAT": (("nlat", "nlon"), ULAT), "ULONG": (("nlat", "nlon"), ULONG),
            },
        )
        ds["ANGLE"] = (("nlat", "nlon"), np.full((nlat, nlon), A),
                       {"units": "radians", "long_name": "angle grid makes with latitude line"})
        ds.to_netcdf(root / f"audit.pop.h.{v}.{year}01-{year}12.nc")
    return root


t0 = time.time()
for p in ("cases", "input", "popsrc"):
    shutil.rmtree(S / p, ignore_errors=True)
(S / "cases").mkdir(parents=True)
(S / "input").mkdir(parents=True)
src = make_pop_archive(S / "popsrc")
print("synthetic POP archive:", src, " UVEL/VVEL stored (cm/s):",
      round(50 * np.cos(A), 2), round(-50 * np.sin(A), 2), flush=True)

from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

grid = Grid(lenx=2.0, leny=2.0, resolution=0.25, xstart=200.0, ystart=-1.0, name="va1")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="va1")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases/audit_va1_pop", inputdir=S / "input/audit_va1_pop",
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
print("case created", round(time.time() - t0), flush=True)
case.configure_forcings(date_range=["2000-03-01 00:00:00", "2000-03-06 00:00:00"],
                        product_name="CESM_POP_OUTPUT",
                        function_name="get_cesm_single_variable_data",
                        function_overrides={"dataset_path": str(src)})
print("configured", round(time.time() - t0), flush=True)
case.process_forcings()
print("processed", round(time.time() - t0), flush=True)

inp = S / "input/audit_va1_pop"
print("files:", sorted(str(p.relative_to(inp)) for p in inp.rglob("*.nc") if "weights" not in str(p))[:40])
for f in sorted(inp.rglob("forcing_obc_segment_00*.nc")):
    ds = xr.open_dataset(f)
    uv = [k for k in ds.data_vars if k.startswith("u_segment") or k.startswith("v_segment")]
    for k in uv:
        print(f"OBC {f.name} {k}: mean {float(ds[k].mean()):.4f} m/s")
for f in sorted(inp.rglob("init_vel*.nc")):
    ds = xr.open_dataset(f)
    for k in ds.data_vars:
        print(f"IC {f.name} {k}: mean {float(ds[k].mean()):.4f} m/s")
print("EXPECTED (true flow is due east 0.5 m/s on a lat-lon target): u=0.5000 v=0.0000")
print("raw-file ANGLE present:", [str(p.name) for p in inp.rglob("*unprocessed*.nc")
                                  if "ANGLE" in xr.open_dataset(p).variables][:3])
