import sys, datetime
from pathlib import Path
import cftime, xarray as xr
d = Path(sys.argv[1]); start = sys.argv[2]; stop_n = int(sys.argv[3])
y, m, dd = map(int, start.split("-"))
end_model = cftime.DatetimeNoLeap(y, m, dd) + datetime.timedelta(days=stop_n)
end_right = None
for p in sorted(d.glob("forcing_obc_segment_*.nc")):
    t = xr.open_dataset(p, decode_times=False).time
    dec = cftime.num2date(t.values, t.attrs["units"], t.attrs.get("calendar", "standard"))
    print(p.name, "| units:", t.attrs["units"], "| calendar:", t.attrs.get("calendar"),
          "| first:", dec[0], "| last:", dec[-1], "| n:", t.size,
          "| model stop (NO_LEAP):", end_model, "| model passes last record:", end_model > dec[-1])
