# Repro for H9: Grid.subgrid_from_supergrid on the gallery's global 1/12-degree hgrid (HGRID_TRIMMED)
import numpy as np
from CrocoDash.grid import Grid
P = "/glade/campaign/cesm/cesmdata/inputdata/ocn/mom/croc/crocogallerydata/grids/ocean_hgrid_trimmed.nc"
def tryit(llc, urc, label):
    try:
        g = Grid.subgrid_from_supergrid(path=P, llc=llc, urc=urc, name="s")
        print(f"{label}: OK {g.ny}x{g.nx}")
    except BaseException as e:
        print(f"{label}: {type(e).__name__}: {e}")
tryit((16.0, 192.0), (27.0, 209.0), "gallery Hawaii box")
tryit((0.0, 65.0), (10.0, 81.0), "Laccadive Sea box across the parent's x seam at 73E")
tryit((50.0, 10.0), (75.0, 40.0), "Baltic-to-Barents box reaching into the tripolar cap")
