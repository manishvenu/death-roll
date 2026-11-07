import numpy as np
from mom6_forge.grid import Grid
from r2_angles import indep_angle
g = Grid.from_projection("EPSG:3995", -500e3, 500e3, -500e3, 500e3, 50e3, name="p")
sg = g.supergrid
a = sg.angle_dx[:, 1:-1]; b = indep_angle(sg.x, sg.y)
d = np.abs((a - b + 180) % 360 - 180)
yy = sg.y[:, 1:-1]
for thr in (1, 5, 30):
    bad = d > thr
    print(thr, bad.sum(), "of", d.size, "lat of bad:", np.unique(np.round(yy[bad],2))[:10])
print("x range", sg.x.min(), sg.x.max())
# where the bad ones sit relative to seam
j,i = np.where(d>5)
print(list(zip(j[:10], i[:10])), sg.x[j[:10], i[:10]+1])
