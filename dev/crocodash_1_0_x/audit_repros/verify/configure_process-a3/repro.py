"""configure_process-a3: STOP_N vs NO_LEAP calendar for CESM_MOM_OUTPUT."""
import sys, re, datetime
from pathlib import Path
import cftime, xarray as xr
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).parent
name = sys.argv[1] if len(sys.argv) > 1 else "audit_v_cpa3_1"
grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name="cpa3")
topo = Topo(grid, min_depth=10.0)
topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=10, depth=1000.0, name="cpa3")
case = Case(cesmroot=Path("~/work/installs/CESM_crocodash").expanduser(),
            caseroot=S / "cases" / name, inputdir=S / "input" / name,
            compset="1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV",
            ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
            machine="derecho", project="ncgd0011", override=True)
date_range = sys.argv[2:4] if len(sys.argv) > 3 else ["2020-02-01 00:00:00", "2020-03-01 00:00:00"]
case.configure_forcings(date_range=date_range, boundaries=["south", "north", "west", "east"],
                        product_name="CESM_MOM_OUTPUT", function_name="get_mom6_output_data",
                        function_overrides={"dataset_path": str(S / "src"), "file_glob": "*.nc"})
cr = S / "cases" / name
def xml(var):
    for f in cr.glob("env_*.xml"):
        m = re.search(rf'<entry id="{var}" value="([^"]*)"', f.read_text())
        if m:
            return m.group(1)
cal, start, stop_opt, stop_n = (xml(v) for v in ("CALENDAR", "RUN_STARTDATE", "STOP_OPTION", "STOP_N"))
print(f"CALENDAR={cal} RUN_STARTDATE={start} STOP_OPTION={stop_opt} STOP_N={stop_n}", flush=True)
y, m, d = map(int, start.split("-"))
end_model = cftime.DatetimeNoLeap(y, m, d) + datetime.timedelta(days=int(stop_n))
print("model stop time in NO_LEAP calendar:", end_model, " | user date_range end:", date_range[1], flush=True)
case.process_forcings(process_ic=True, process_bc=True)
for p in sorted((S / "input" / name / "ocn").glob("forcing_obc_segment_*.nc")):
    ds = xr.open_dataset(p, decode_times=False)
    t = ds.time
    dec = cftime.num2date(t.values, t.attrs["units"], t.attrs.get("calendar", "standard"))
    print(p.name, "units:", t.attrs["units"], "calendar:", t.attrs.get("calendar"),
          "first:", dec[0], "last:", dec[-1], "n:", t.size,
          "-> model passes last record:", end_model > dec[-1], flush=True)
