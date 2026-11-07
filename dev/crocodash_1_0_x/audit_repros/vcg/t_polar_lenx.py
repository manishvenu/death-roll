# OCN_LENX/LENY CrocoDash would pass for projected / polar grids, vs the solver's bounds.
from CrocoDash.grid import Grid
def show(name, g):
    lenx = g.tlon.max().item() - g.tlon.min().item(); leny = g.tlat.max().item() - g.tlat.min().item()
    print(f"{name:40s} nx={g.nx} ny={g.ny} tlon=[{g.tlon.min().item():.2f},{g.tlon.max().item():.2f}] tlat=[{g.tlat.min().item():.2f},{g.tlat.max().item():.2f}] LENX={lenx:.3f} LENY={leny:.3f}")
show("arctic cap 3995 +-400km @50km", Grid.from_projection("EPSG:3995", -400e3, 400e3, -400e3, 400e3, 50e3, name="a"))
show("antarctic 3031 off-pole", Grid.from_projection("EPSG:3031", 1000e3, 1500e3, -250e3, 250e3, 50e3, name="b"))
show("arctic 3995 off-pole (Bering side)", Grid.from_projection("EPSG:3995", -250e3, 250e3, 1500e3, 2000e3, 50e3, name="c"))
