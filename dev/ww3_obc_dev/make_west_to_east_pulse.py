"""
One-off regeneration of ww3.obc.2's WW3 boundary spectra so a wave clearly
enters at the west boundary, travels east across the domain, then shuts off
-- instead of the plumbing test's flat, isotropic, always-on values.

What changes vs. the original files (all still produced by CrocoDash's own
write_ww3_boundary_spectrum/write_spec_list/write_ww3_bounc_nml, just called
with different efth arrays):

1. Only the west point carries energy at all -- south/north/east are zeroed
   out. With every point active, waves radiate from all four sides at once
   and there's no single "propagating from west to east" signal to see.

2. The west point's energy sits in a single frequency bin and a single
   direction bin, instead of being spread flat across all of them. A flat
   spectrum has no preferred direction of travel; concentrating it makes a
   trackable swell.

3. That energy is only nonzero for the first PULSE_DAYS days, then zero for
   the rest of the run -- so wave height visibly turns on, crosses the
   domain, and turns back off in the hi-history output, instead of being a
   constant background level for the whole run.

4. The pulse magnitude is large enough (~4.7m HS) to stand out against the
   locally wind-generated sea, and ww3_bounc.nml uses linear (not nearest)
   interpolation between the 4 station points, so the energy is clearly
   peaked at the single west point rather than spread as a uniform wall
   across the whole west edge.

Direction convention: WW3 boundary spectra use "coming from" (like wind
direction, clockwise from true north), which is also what ww3_bounc.F90
expects and what write_ww3_boundary_spectrum's docstring documents. 270 deg
means "coming from the west" -> traveling east, which is what we want here.
If the pulse looks like it travels the wrong way once you look at the
output, flip PULSE_FROM_DIRECTION_DEG by 180.

Run with: conda run -n CrocoDash python make_west_to_east_pulse.py
Then rebuild the case (buildnml reruns ww3_bounc from these files into
nest.ww3) before resubmitting.
"""

import json
from pathlib import Path

import numpy as np
import xarray as xr

from CrocoDash.extract_forcings.ww3 import (
    write_ww3_boundary_spectrum,
    write_spec_list,
    write_ww3_bounc_nml,
)

INPUTDIR = Path("/glade/u/home/manishrv/scratch/croc_input/ww3.obc.2")
OCNICE_DIR = INPUTDIR / "ocnice"

PULSE_BOUNDARY = "west"
PULSE_DAYS = 10
PULSE_FROM_DIRECTION_DEG = 270.0  # "coming from the west" -> traveling east
PULSE_FREQ_INDEX = 10  # a single mid-range frequency bin (~9s period swell)
# m^2 s / rad in that one (freq, direction) bin. The first run (5.0) only
# gave ~0.46m significant wave height at the boundary -- too small to stand
# out against the locally wind-generated sea, which reached ~5.6m HS on its
# own by the end of this run. 500 puts the boundary-forced HS at ~4.7m
# (HS = 4*sqrt(E * df * dtheta), df/dtheta from this frequency/direction
# discretization), clearly larger than the background.
PULSE_VALUE = 500.0

with open(INPUTDIR / "extract_forcings" / "config.json") as f:
    config = json.load(f)

boundaries = config["ww3obc"]["inputs"]["boundaries"]
start = np.datetime64(config["basic"]["dates"]["start"])
end = np.datetime64(config["basic"]["dates"]["end"])
time = np.arange(start, end + np.timedelta64(1, "h"), np.timedelta64(1, "h"))

pulse_end = start + np.timedelta64(PULSE_DAYS, "D")
in_pulse_window = time < pulse_end

NK, NTH = 25, 24
freq = 0.04118 * 1.1 ** np.arange(NK)
direction = np.linspace(0, 360, NTH, endpoint=False)
pulse_dir_index = int(np.argmin(np.abs(direction - PULSE_FROM_DIRECTION_DEG)))

spectra_names = []
for i, side in enumerate(boundaries):
    name = f"ww3.point{i + 1}_spec.nc"
    with xr.open_dataset(OCNICE_DIR / name, decode_times=False) as ds:
        lat = float(ds["latitude"].values[0])
        lon = float(ds["longitude"].values[0])

    efth = np.zeros((len(time), NK, NTH))
    if side == PULSE_BOUNDARY:
        efth[in_pulse_window, PULSE_FREQ_INDEX, pulse_dir_index] = PULSE_VALUE

    write_ww3_boundary_spectrum(
        OCNICE_DIR / name, lat, lon, freq, direction, efth, time=time
    )
    spectra_names.append(name)

write_spec_list(OCNICE_DIR, spectra_names)
# linear (not nearest) interpolation: with 4 station points along the whole
# perimeter, nearest-neighbor assigns every boundary cell closest to the west
# point the exact same uniform value, i.e. a flat wall of energy along the
# whole west edge. Linear blends toward the (zero-energy) north/south
# neighbors, so energy peaks right at the west point and fades along the
# edge -- visibly sourced from a single point instead of a uniform front.
write_ww3_bounc_nml(OCNICE_DIR, interp=2)

print(f"Rewrote {len(spectra_names)} boundary spectra in {OCNICE_DIR}")
print(f"'{PULSE_BOUNDARY}' pulse active {start} -> {pulse_end} ({PULSE_DAYS} days)")
