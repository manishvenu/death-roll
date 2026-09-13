"""
Animate significant wave height (HS) across the whole domain over the full
run, from ww3.obc.2's archived wave history output.

Reads every wav/hist/*.nc file in the archive (st_archive moves them there
after the run finishes), so it's safe to point this at the same archive
directory after any rerun -- it always picks up whatever's currently there.

Run with: conda run -n CrocoDash python animate_hs.py
Output: hs_animation.gif next to this script.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import xarray as xr

ARCHIVE_HIST_DIR = Path("/glade/u/home/manishrv/scratch/archive/ww3.obc.2/wav/hist")
OUTPUT_PATH = Path(__file__).parent / "hs_animation.gif"

STRIDE = 3  # take every 3rd hourly file (~3h effective step) to keep frame count sane
VMAX = 8.0  # fixed color scale (m) so growth reads as a color change, not autoscaling
FPS = 8

files = sorted(ARCHIVE_HIST_DIR.glob("*.nc"))[::STRIDE]
if not files:
    raise SystemExit(f"No wave history files found in {ARCHIVE_HIST_DIR}")

datasets = [xr.open_dataset(f) for f in files]
lon = datasets[0]["lon"].values
lat = datasets[0]["lat"].values

fig, ax = plt.subplots(figsize=(8, 6))
ax.set_facecolor("lightgrey")  # land (NaN) shows through as grey
mesh = ax.pcolormesh(
    lon,
    lat,
    datasets[0]["HS"].isel(time=0).values,
    vmin=0,
    vmax=VMAX,
    shading="auto",
    cmap="viridis",
)
fig.colorbar(mesh, ax=ax, label="Significant wave height (m)")
title = ax.set_title("")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")


def update(i):
    ds = datasets[i]
    hs = ds["HS"].isel(time=0).values
    mesh.set_array(hs.ravel())
    t = ds["time"].values[0]
    title.set_text(f"HS -- {t}")
    return mesh, title


anim = FuncAnimation(fig, update, frames=len(datasets), blit=False)
anim.save(OUTPUT_PATH, writer=PillowWriter(fps=FPS))

for ds in datasets:
    ds.close()

print(f"Wrote {OUTPUT_PATH} ({len(datasets)} frames, {len(datasets) / FPS:.1f}s)")
