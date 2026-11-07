# What OCN_LENX/LENY CrocoDash passes for various grids, and the DT vCG derives from it.
from CrocoDash.grid import Grid
def vcg_dt(lenx, leny, nx, ny):
    res_x = lenx / nx; res_y = leny / ny
    dt = 7200.0 * min(res_x, res_y)
    dt = min((1800.0 / n for n in [2**i * 3**j for i in range(10) for j in range(6)] if 1800.0 % n == 0), key=lambda x: abs(dt - x))
    return dt
cases = {
 "plain 0.5deg": dict(lenx=4, leny=4, resolution=0.5, xstart=-60, ystart=30),
 "antimeridian 0.5deg (xstart=178)": dict(lenx=4, leny=4, resolution=0.5, xstart=178, ystart=30),
 "antimeridian (xstart=-182)": dict(lenx=4, leny=4, resolution=0.5, xstart=-182, ystart=30),
 "1/12deg": dict(lenx=1, leny=1, resolution=1/12, xstart=-60, ystart=30),
 "1/4deg at 75N": dict(lenx=5, leny=5, resolution=0.25, xstart=-60, ystart=72),
}
for k, kw in cases.items():
    g = Grid(name="t", **kw)
    lenx = g.tlon.max().item() - g.tlon.min().item(); leny = g.tlat.max().item() - g.tlat.min().item()
    print(f"{k:35s} nx={g.nx} ny={g.ny} tlon=[{g.tlon.min().item():.2f},{g.tlon.max().item():.2f}] LENX={lenx:.2f} LENY={leny:.2f} DT={vcg_dt(lenx,leny,g.nx,g.ny)} min_dx_km={float(min(g.dxt.min(), g.dyt.min()))/1e3:.1f}")
