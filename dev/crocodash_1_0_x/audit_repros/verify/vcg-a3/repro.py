# vcg-a3: Case() accepts the docstring's example compset (no %REGIONAL) -> MOM6_DOMAIN_TYPE=GLOBAL
import re, sys, time, warnings
from pathlib import Path
import yaml
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path(__file__).resolve().parent
CESMROOT = Path("/glade/u/home/manishrv/work/installs/CESM_crocodash")
LNAME = sys.argv[1] if len(sys.argv) > 1 else "1850_DATM%JRA_SLND_SICE_MOM6_SROF_SGLC_SWAV_SESP"  # Case docstring example
label = sys.argv[2] if len(sys.argv) > 2 else "doc"
atm = sys.argv[3] if len(sys.argv) > 3 else "TL319"

grid = Grid(lenx=4.0, leny=4.0, resolution=0.5, xstart=-60.0, ystart=30.0, name=f"va3{label}")
topo = Topo(grid, min_depth=10.0); topo.set_flat(1000.0)
vgrid = VGrid.uniform(nk=5, depth=1000.0, name=f"va3{label}")
t0 = time.time()
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    case = Case(cesmroot=CESMROOT, caseroot=S / "cases" / f"audit_va3_{label}", inputdir=S / "input" / f"audit_va3_{label}",
                compset=LNAME, ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name=atm,
                machine="derecho", project="ncgd0011", override=True)
    print(f"Case() OK in {time.time()-t0:.1f}s", flush=True)
    case.configure_forcings(date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                            product_name="reference_ocean", function_name="get_reference_ocean_data")
    print("configure_forcings OK", flush=True)
print("warnings mentioning REGIONAL/compset/domain:",
      [str(x.message)[:120] for x in w if re.search("regional|compset|domain", str(x.message), re.I)])

cr = case.caseroot
xml = {}
for f in cr.glob("env_*.xml"):
    for m in re.finditer(r'<entry id="([A-Z0-9_]+)" value="([^"]*)"', f.read_text()):
        xml[m.group(1)] = m.group(2)
for k in ("COMPSET", "MOM6_DOMAIN_TYPE", "OCN_GRID"):
    print(f"  {k} = {xml.get(k)}")

# which REGIONAL-keyed MOM_input defaults are lost (OCN_GRID is custom, so only else/REGIONAL keys can match)
unl = (cr / "user_nl_mom").read_text()
set_in_unl = set(re.findall(r"^\s*([A-Z0-9_%]+)\s*=", unl, re.M))
y = yaml.safe_load(open(CESMROOT / "components/mom/param_templates/MOM_input.yaml"))
lost = []
for sect, params in y.items():
    for p, spec in (params or {}).items():
        v = spec.get("value") if isinstance(spec, dict) else None
        if not isinstance(v, dict):
            continue
        reg = [val for cond, val in v.items() if 'MOM6_DOMAIN_TYPE == "REGIONAL"' in str(cond) and " and " not in str(cond)]
        if not reg or p in set_in_unl:
            continue
        lost.append(f"{p}: REGIONAL={reg[0]!r} GLOBAL={v.get('else', '<MOM6 default>')!r}")
print(f"{len(lost)} REGIONAL-keyed params not overridden in user_nl_mom; with MOM6_DOMAIN_TYPE={xml.get('MOM6_DOMAIN_TYPE')} they take the GLOBAL value:")
for k in ("USE_KPP", "MAXTRUNC", "DO_GEOTHERMAL", "DTBT", "DIABATIC_FIRST", "KD", "KV", "ENERGYSAVEDAYS", "DEPRESS_INITIAL_SURFACE", "OBC_RAMP_TIMESCALE", "PARALLEL_RESTARTFILES"):
    print("   ", next((l for l in lost if l.startswith(k + ":")), f"{k}: (set by CrocoDash/vCG or not keyed)"))
print("  ENERGETICS_SFC_PBL in user_nl_mom:", "ENERGETICS_SFC_PBL" in set_in_unl, "| USE_KPP in user_nl_mom:", "USE_KPP" in set_in_unl)
