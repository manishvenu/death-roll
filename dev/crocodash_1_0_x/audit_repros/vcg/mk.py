import os, sys, time
from pathlib import Path
from CrocoDash.grid import Grid
from CrocoDash.topo import Topo
from CrocoDash.vgrid import VGrid
from CrocoDash.case import Case

S = Path("/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/vcg")
CESMROOT = Path("/glade/u/home/manishrv/work/installs/CESM_crocodash")
NYF = "1850_DATM%NYF_SLND_SICE_MOM6%REGIONAL_SROF_SGLC_SWAV"

def objs(name="vcgg", lenx=4.0, leny=4.0, res=0.5, xstart=-60.0, ystart=30.0, nk=5, depth=1000.0):
    grid = Grid(lenx=lenx, leny=leny, resolution=res, xstart=xstart, ystart=ystart, name=name)
    topo = Topo(grid, min_depth=10.0)
    topo.set_flat(depth)
    vgrid = VGrid.uniform(nk=nk, depth=depth, name=name)
    return grid, topo, vgrid

def make(label, compset=NYF, caseroot=None, inputdir=None, grid_kw=None, **kw):
    grid, topo, vgrid = objs(**(grid_kw or {}))
    caseroot = caseroot if caseroot is not None else S / "cases" / f"audit_vcg_{label}"
    inputdir = inputdir if inputdir is not None else S / "input" / f"audit_vcg_{label}"
    args = dict(cesmroot=CESMROOT, caseroot=caseroot, inputdir=inputdir, compset=compset,
                ocn_grid=grid, ocn_topo=topo, ocn_vgrid=vgrid, atm_grid_name="T62",
                machine="derecho", project="ncgd0011", override=True)
    args.update(kw)
    t0 = time.time()
    case = Case(**args)
    print(f"[{label}] created in {time.time()-t0:.1f}s", flush=True)
    return case

def show(caseroot, ids=("OCN_GRID","ICE_GRID","WAV_GRID","OCN_DOMAIN_MESH","ICE_DOMAIN_MESH","WAV_DOMAIN_MESH","MASK_MESH","ATM_GRID","LND_GRID","ROF_GRID","OCN_NCPL","ICE_NCPL","WAV_NCPL","ATM_NCPL","GRID","RUNDIR","EXEROOT")):
    import re
    caseroot = Path(caseroot)
    for f in sorted(caseroot.glob("env_*.xml")):
        for line in f.read_text().splitlines():
            m = re.search(r'<entry id="([A-Z0-9_]+)" value="([^"]*)"', line)
            if m and m.group(1) in ids:
                print(f"  {f.name}: {m.group(1)}={m.group(2)}")
