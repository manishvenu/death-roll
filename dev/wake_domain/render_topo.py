import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mask_design_wake import ocean, NX, NY, SEGMENT_SPECS

fig, ax = plt.subplots(figsize=(12, 8.5))
ax.imshow(ocean, origin="lower", cmap="Blues", vmin=-0.3, vmax=1.3, extent=(0, NX, 0, NY))

colors = plt.cm.tab10(np.linspace(0, 1, 10))

def draw_cardinal(orientation, index_range, color, label):
    lo, hi = (0, NY) if index_range is None else index_range
    if orientation == "north":
        ax.plot([lo, hi], [NY, NY], color=color, lw=5, solid_capstyle="butt")
        ax.text((lo+hi)/2, NY-3, label, color=color, fontsize=9, ha="center", weight="bold")
    elif orientation == "south":
        ax.plot([lo, hi], [0, 0], color=color, lw=5, solid_capstyle="butt")
        ax.text((lo+hi)/2, 3, label, color=color, fontsize=9, ha="center", weight="bold")
    elif orientation == "east":
        ax.plot([NX, NX], [lo, hi], color=color, lw=5, solid_capstyle="butt")
        ax.text(NX-4, (lo+hi)/2, label, color=color, fontsize=9, ha="right", weight="bold", rotation=90)
    elif orientation == "west":
        ax.plot([0, 0], [lo, hi], color=color, lw=5, solid_capstyle="butt")
        ax.text(4, (lo+hi)/2, label, color=color, fontsize=9, ha="left", weight="bold", rotation=90)

for i, (name, spec) in enumerate(SEGMENT_SPECS.items()):
    color = colors[i]
    label = name
    if spec["kind"] == "cardinal":
        draw_cardinal(spec["orientation"], spec["index_range"], color, label)
    elif spec["kind"] == "interior_horizontal":
        lo, hi = spec["col_range"]
        row = spec["row"]
        ax.plot([lo, hi], [row, row], color=color, lw=5, solid_capstyle="butt")
        ax.text((lo+hi)/2, row+1.5, label, color=color, fontsize=9, ha="center", weight="bold")
        ax.scatter([lo], [row], color=color, marker="x", s=60, zorder=5)
    elif spec["kind"] == "interior_vertical":
        rlo, rhi = spec["row_range"] if spec["row_range"] else (0, NY)
        col = spec["col"]
        ax.plot([col, col], [rlo, rhi], color=color, lw=5, solid_capstyle="butt")
        ax.text(col+1.5, (rlo+rhi)/2, label, color=color, fontsize=9, va="center", weight="bold")

ax.set_xlim(-2, NX+2)
ax.set_ylim(-2, NY+2)
ax.set_xlabel("T-column (I index)")
ax.set_ylabel("T-row (J index)")
ax.set_title("wake_domain: bathymetry mask + 7 OBC segments")
plt.tight_layout()
plt.savefig("current_topo.png", dpi=130)
print("saved current_topo.png")
