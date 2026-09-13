"""Summarize CESM timing profiles side by side.

Usage: python compare_timings.py timing/cesm_timing.* 
"""
import re
import sys
from pathlib import Path

FIELDS = [
    ("Init", r"Init Time\s*:\s*([\d.]+) seconds"),
    ("Run", r"Run Time\s*:\s*([\d.]+) seconds"),
    ("OCN", r"OCN Run Time:\s*([\d.]+) seconds"),
    ("ICE", r"ICE Run Time:\s*([\d.]+) seconds"),
    ("ATM", r"ATM Run Time:\s*([\d.]+) seconds"),
    ("CPL", r"CPL Run Time:\s*([\d.]+) seconds"),
]


def parse(path):
    t = Path(path).read_text()
    row = {"file": Path(path).name}
    row["case"] = (re.search(r"Case\s*:\s*(\S+)", t) or [None, "?"])[1]
    row["pes"] = (re.search(r"total pes active\s*:\s*(\d+)", t) or [None, "?"])[1]
    row["days"] = (re.search(r"stop option : ndays, stop_n = (\d+)", t) or [None, "?"])[1]
    for name, pat in FIELDS:
        m = re.search(pat, t)
        row[name] = float(m.group(1)) if m else float("nan")
    row["Total"] = row["Init"] + row["Run"]
    return row


rows = [parse(p) for p in sys.argv[1:]]
rows.sort(key=lambda r: r["Total"])

hdr = f"{'case':<22}{'pes':>5}{'days':>6}{'Total':>9}{'Init':>9}{'Run':>9}{'OCN':>9}{'ICE':>9}{'ATM':>8}{'CPL':>8}"
print(hdr)
print("-" * len(hdr))
for r in rows:
    print(
        f"{r['case']:<22}{r['pes']:>5}{r['days']:>6}"
        f"{r['Total']:>9.1f}{r['Init']:>9.1f}{r['Run']:>9.1f}"
        f"{r['OCN']:>9.1f}{r['ICE']:>9.1f}{r['ATM']:>8.1f}{r['CPL']:>8.1f}"
    )
print("\n(all times in seconds; Total = Init + Run)")
