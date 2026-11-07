"""Check angle_dx sign/magnitude on rotated grids vs an independent local computation,
and check the grid metrics, CICE grid file contents."""
import numpy as np
import xarray as xr
from mom6_forge.grid import Grid
from mom6_forge.topo import Topo


def indep_angle(x, y):
    # angle of local +i direction CCW from east at each supergrid node (interior),
    # by centred difference in a local tangent plane
    dlon = (x[:, 2:] - x[:, :-2] + 180) % 360 - 180
    dlat = y[:, 2:] - y[:, :-2]
    lat = np.deg2rad(y[:, 1:-1])
    return np.rad2deg(np.arctan2(dlat, dlon * np.cos(lat)))


for ang in (0.0, 30.0, -45.0):
    g = Grid.from_center(40.0, -60.0, 200e3, 100e3, 10e3, angle_deg=ang, name="r")
    sg = g.supergrid
    a = sg.angle_dx[:, 1:-1]
    b = indep_angle(sg.x, sg.y)
    print(f"angle_deg={ang:6.1f}: angle_dx mean {a.mean():8.3f}, independent {b.mean():8.3f}, "
          f"max|diff| {np.abs(a-b).max():.3f}; dx_dy_calc_type={sg._dx_dy_calc_type}")

# polar
g = Grid.from_projection("EPSG:3995", -500e3, 500e3, -500e3, 500e3, 50e3, name="p")
sg = g.supergrid
a = sg.angle_dx[:, 1:-1]
b = indep_angle(sg.x, sg.y)
d = (a - b + 180) % 360 - 180
print(f"polar: max|angle diff| {np.nanmax(np.abs(d)):.3f} deg, dx_dy_calc_type {sg._dx_dy_calc_type}")
