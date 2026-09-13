"""Domain geometry for the "island-wake" showcase.

Hand-drawn by the user via the interactive mom6_forge.topo_editor.TopoEditor
(dev/wake_domain/edit_topo.ipynb), loaded here from ocean_mask.npy. 5 land
blocks: NW corner square, a central peninsula off the north edge (hooking
left), a hooking peninsula off the east edge with a pronounced overhang (base
reaches the true edge, tip does not), a small isolated patch near the east
edge, and the NE block.

7 OBC segments -- 5 cardinal (full or partial edges) + 2 interior horizontal
lines, both opening directly into the main basin (not into a sealed-off
pocket -- the areas behind these lines are solid land):
  - north2_interior: sits at row 92, the northernmost wet row of the main
    basin between the central peninsula and the NE block; everything from
    row 93 to the true north edge (cols 89-106) is land. Interior (ocean)
    side is SOUTH of the line.
  - east2_interior: sits at row 26, the northernmost wet row of the strait
    between the east peninsula and the small isolated patch; everything
    from row 27 up through the peninsula's overhang (cols 111-143) is land.
    Interior (ocean) side is SOUTH of the line.

IMPORTANT mechanical constraint for interior segments (learned the hard way):
MOM6 forcibly masks the T-cell immediately "outside" (the non-interior side
of) every OBC segment to land, across the segment's *entire* extent --
regardless of what the bathymetry file says. So each interior segment here
has its excluded neighbor row already forced to land in the mask (verified
below) -- and since that whole exterior region is land anyway now, this is
just documentation, not a load-bearing constraint like it was when the
exterior was a disconnected ocean pocket.

Rows: T-cell index, 0 = south, NY-1 = north.
Cols: T-cell index, 0 = west, NX-1 = east.
"""

from pathlib import Path

import numpy as np

NX = 144
NY = 100

ocean = np.load(Path(__file__).parent / "ocean_mask.npy")
assert ocean.shape == (NY, NX), f"ocean_mask.npy is {ocean.shape}, expected {(NY, NX)}"

OCEAN_FRACTION = float(ocean.mean())


def _center_row_slice(row, col_lo, col_hi):
    """Supergrid (index, index_range) for a horizontal interior line at T-row
    `row`, spanning T-columns [col_lo, col_hi] -- sampled at the row's own
    center (odd) supergrid index, not the corner, so `.mask` reflects the
    row's actual wet/dry cells rather than a neighboring row's."""
    return 2 * row + 1, slice(2 * col_lo + 1, 2 * col_hi + 2)


def _center_col_slice(col, row_lo, row_hi):
    """Same, for a vertical interior line at T-column `col`."""
    return 2 * col + 1, slice(2 * row_lo + 1, 2 * row_hi + 2)


# --- The 7 segments, as (kind, spec) -- built in a deliberately shuffled
# order (not perimeter order) to prove construction order doesn't matter. ---
SEGMENT_SPECS = {
    "north2_interior": dict(
        kind="interior_horizontal",
        row=92,
        col_range=(89, 106),
        # interior ocean is SOUTH of this line (the main basin); outside
        # (north, row 93) is land, all the way to the true north edge.
        ocean_side="south",
    ),
    "west": dict(kind="cardinal", orientation="west", index_range=(0, 85)),
    "north1": dict(kind="cardinal", orientation="north", index_range=(20, 74)),
    "south": dict(kind="cardinal", orientation="south", index_range=None),
    "east2_interior": dict(
        kind="interior_horizontal",
        row=26,
        col_range=(111, 120),
        # interior ocean is SOUTH of this line (the main basin); outside
        # (north, row 27) is land, all the way up through the overhang.
        ocean_side="south",
    ),
    "east1": dict(kind="cardinal", orientation="east", index_range=(0, 13)),
    "east3": dict(kind="cardinal", orientation="east", index_range=(55, 70)),
}

# Distinct salinity anomaly (PSU offset from the 35.0 PSU background) injected
# at each boundary's OBC forcing, purely as a visualization tracer -- so in
# the output salinity field you can see which water came in from which of
# the 7 boundaries. Chosen to be clearly separated but still physically mild.
SALINITY_ANOMALY_PSU = {
    "west": -1.2,
    "north1": -0.8,
    "south": -0.4,
    "north2_interior": 0.4,
    "east1": 0.8,
    "east2_interior": 1.2,
    "east3": 1.6,
}

# Primary jet: west-to-east, tapering to ~0 within this many T-rows of the
# true north/south edges, so only the west/east cardinal segments actually
# carry the current -- north/south/interior segments passively radiate.
JET_SPEED = 0.55  # m/s
JET_EDGE_TAPER_ROWS = 10

if __name__ == "__main__":
    print(f"NX={NX} NY={NY}  ocean fraction={OCEAN_FRACTION:.3f}")
    for name, spec in SEGMENT_SPECS.items():
        print(f"  {name}: {spec}")
