from mom6_forge.grid import Grid
from mom6_forge._supergrid import ProjectedSupergrid
for ang in (90.0, -90.0, 89.0):
    try:
        g = Grid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=ang, name="m")
        print(ang, "ok", g.tlon.shape, "cyclic_x", g.cyclic_x)
    except AssertionError as e:
        sg = ProjectedSupergrid.from_center(30.0, -60.0, 100e3, 60e3, 5e3, angle_deg=ang)
        print(ang, "AssertionError:", e, "| x[:,0] range", sg.x[:,0].min().round(3), sg.x[:,0].max().round(3),
              "y[:,0]", sg.y[:,0].min().round(2), sg.y[:,0].max().round(2), "y[:,-1]", sg.y[:,-1].min().round(2), sg.y[:,-1].max().round(2))
