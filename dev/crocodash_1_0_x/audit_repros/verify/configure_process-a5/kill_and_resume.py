"""For each target file: delete it (and anything downstream), run process_forcings
with that one write slowed, SIGKILL it mid-write (like walltime/OOM/Ctrl-C), then
rerun process_forcings normally in a fresh process, as a user resuming would."""
import os, signal, subprocess, sys, time
from pathlib import Path

S = Path(__file__).resolve().parent
PY = os.environ["PY"]
inp = S / "input" / "audit_vcpa5_1"
cfg = inp / "extract_forcings" / "config.json"
raw, rgd, ocn = inp / "extract_forcings" / "raw_data", inp / "extract_forcings" / "regridded_data", inp / "ocn"


def run(args, kill_on=None, log=None):
    p = subprocess.Popen([PY, "-u", str(S / "proc.py"), str(cfg)] + args,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    lines = []
    for line in p.stdout:
        lines.append(line)
        if kill_on and line.startswith("SLOW WRITE STARTED"):
            time.sleep(3)
            os.killpg(p.pid, signal.SIGKILL)  # whole job, like PBS walltime / Ctrl-C
            break
    p.wait()
    if kill_on:
        time.sleep(1)
        left = subprocess.run(["pgrep", "-g", str(p.pid)], capture_output=True, text=True).stdout.split()
        print("processes left in the killed job:", left)
    rest = p.stdout.read() if not kill_on else ""
    lines.append(rest)
    if log:
        (S / log).write_text("".join(lines))
    return p.returncode, "".join(lines)


def describe(f):
    b = f.read_bytes()
    from CrocoDash.forcing import utils
    return f"{f.name}: {len(b)} bytes, magic={b[:4]!r}, is_valid_netcdf={utils.is_valid_netcdf(f)}"


def check_read(f, ref=None):
    import xarray as xr, numpy as np
    try:
        with xr.open_dataset(f) as ds:
            ds = ds.load()
            out = []
            for v in list(ds.data_vars)[:4]:
                a = ds[v].values
                msg = f"{v}{a.shape} nan={int(np.isnan(a).sum()) if a.dtype.kind=='f' else 0} zeros={int((a==0).sum())}/{a.size}"
                if ref is not None and v in ref:
                    msg += f" equal_to_good={np.array_equal(a, ref[v].values, equal_nan=True)}"
                out.append(msg)
            return "READ OK: " + "; ".join(out)
    except Exception as e:
        return f"READ FAILED: {type(e).__name__}: {str(e)[:200]}"


def grep(text, *keys):
    return "\n".join("    " + l for l in text.splitlines() if any(k in l for k in keys))

# 0. One clean full run, to have the good versions of every file.
import shutil as _sh
for _f in [*raw.glob("*.nc"), *rgd.glob("*.nc"), *ocn.glob("forcing_obc_segment_*.nc"), *ocn.glob("init_*.nc")]:
    _f.unlink()
code, out = run([], log="run0_clean.log")
print("clean run exit", code, "| returned:", "PROCESS_FORCINGS RETURNED NORMALLY" in out)
import shutil
good = S / "good"; shutil.rmtree(good, ignore_errors=True); good.mkdir()
ALL = lambda: [*raw.glob("*.nc"), *rgd.glob("*.nc"), *ocn.glob("forcing_obc_segment_*.nc"), *ocn.glob("init_*.nc")]
home = {}
for f in ALL():
    shutil.copy2(f, good / f.name); home[f.name] = f
print("raw files:", sorted(p.name for p in raw.glob("*.nc")))

import xarray as xr
scenarios = [
    ("A raw chunk (GET)", sorted(raw.glob("east_unprocessed.*.nc"))[0],
     lambda: [*rgd.glob("forcing_obc_segment_*.nc"), *ocn.glob("forcing_obc_segment_*.nc")]),
    ("B merged OBC (MERGE)", ocn / "forcing_obc_segment_001.nc", lambda: []),
    ("C IC filled (IC fill)", ocn / "init_tracers_filled.nc", lambda: []),
]
for label, target, downstream in scenarios:
    print("\n=== Scenario", label, "target:", target.relative_to(inp))
    for f in [target, *downstream()]:
        f.unlink(missing_ok=True)
    code, out = run([str(target)], kill_on=True, log=f"run_{label[0]}_killed.log")
    print("killed run returncode", code, "(-9 = SIGKILL)")
    print("left on disk ->", describe(target), "| good copy:", (good / target.name).stat().st_size, "bytes")
    code, out = run([], log=f"run_{label[0]}_resume.log")
    print("resume run exit", code, "| returned normally:", "PROCESS_FORCINGS RETURNED NORMALLY" in out)
    print(grep(out, "already exist", "Skipping", "skipped", "Error", "error", "Traceback", "RuntimeError"))
    ref = xr.open_dataset(good / target.name)
    print("reading the file the resumed run kept ->", check_read(target, ref))
    ref.close()
    if label.startswith("A"):
        seg = ocn / "forcing_obc_segment_004.nc"  # east = segment 4
        g = xr.open_dataset(good / seg.name)
        print("downstream east boundary the resumed run wrote ->", check_read(seg, g))
        import numpy as np
        with xr.open_dataset(seg) as c:
            t, sa = c["temp_segment_004"].values, c["salt_segment_004"].values
            print(f"    temp_segment_004 non-fill values: min={t[t>-1e19].min()} max={t[t>-1e19].max()}; good: {float(g['temp_segment_004'].where(g['temp_segment_004']>-1e19).min()):.3f}..{float(g['temp_segment_004'].max()):.3f}")
            print(f"    salt_segment_004 non-fill values: min={sa[sa>-1e19].min()} max={sa[sa>-1e19].max()}; good: {float(g['salt_segment_004'].where(g['salt_segment_004']>-1e19).min()):.3f}..{float(g['salt_segment_004'].max()):.3f}")
        g.close()
    for name, f in home.items():  # restore every file for the next scenario
        shutil.copy2(good / name, f)
