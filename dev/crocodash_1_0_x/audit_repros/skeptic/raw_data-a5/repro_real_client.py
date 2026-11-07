"""raw_data-a5 skeptic repro: real cdsapi 0.7.7 -> ecmwf.datastores LegacyClient,
real HTTP, against a local stub of the EWDS retrieve API on 127.0.0.1.

Nothing in CrocoDash or cdsapi/ecmwf.datastores is mocked: the only stand-in is
the server. The stub models two server behaviours (the parts that cannot be
checked without network): download_format='zip' -> zip archive asset,
'unarchived' -> bare netCDF; hyear x hmonth x hday combined as a Cartesian
product (invalid dates dropped).
"""
import datetime as dt
import io
import itertools
import json
import os
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

STATE = {"inputs": None, "payload": b"", "ctype": ""}


def build_payload(inputs):
    days = []
    for y, m, d in itertools.product(inputs["hyear"], inputs["hmonth"], inputs["hday"]):
        try:
            days.append(dt.date(int(y), int(m), int(d)))
        except ValueError:
            pass
    days = sorted(days)
    ds = xr.Dataset(
        {"dis24": (("valid_time", "latitude", "longitude"), np.ones((len(days), 2, 2), "f4"))},
        coords={"valid_time": pd.to_datetime(days), "latitude": [0.0, 0.05], "longitude": [0.0, 0.05]},
    )
    nc = ds.to_netcdf()
    if inputs.get("download_format") == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("data_version-4.nc", nc)
        return buf.getvalue(), "application/zip"
    return nc, "application/x-netcdf"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def base(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/api/retrieve/v1/processes/cems-glofas-historical":
            return self._json({"id": "cems-glofas-historical", "links": []})
        if p == "/api/retrieve/v1/jobs/job1":
            return self._json({
                "jobID": "job1", "status": "successful", "processID": "cems-glofas-historical",
                "metadata": {},
                "links": [{"rel": "results", "href": self.base() + "/api/retrieve/v1/jobs/job1/results"}],
            })
        if p == "/api/retrieve/v1/jobs/job1/results":
            return self._json({"asset": {"value": {
                "href": self.base() + "/download/result_blob",
                "file:size": len(STATE["payload"]), "type": STATE["ctype"]}}})
        if p == "/download/result_blob":
            b = STATE["payload"]
            self.send_response(200)
            self.send_header("Content-Type", STATE["ctype"])
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self._json({"detail": "nf " + p}, 404)

    def do_HEAD(self):
        b = STATE["payload"]
        self.send_response(200)
        self.send_header("Content-Type", STATE["ctype"])
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()

    def do_POST(self):
        p = urlparse(self.path).path
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if p == "/api/retrieve/v1/processes/cems-glofas-historical/execution":
            STATE["inputs"] = body["inputs"]
            STATE["payload"], STATE["ctype"] = build_payload(body["inputs"])
            return self._json({
                "jobID": "job1", "status": "accepted",
                "links": [{"rel": "monitor", "href": self.base() + "/api/retrieve/v1/jobs/job1"}],
            }, 201)
        self._json({}, 200)

    def do_DELETE(self):
        self._json({"jobID": "job1", "status": "dismissed"})


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
rc = HERE / "fake_cdsapirc"
rc.write_text(f"url: http://127.0.0.1:{srv.server_port}/api\nkey: 00000000-0000-0000-0000-000000000000\n")
os.environ["CDSAPI_RC"] = str(rc)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"

import cdsapi
import CrocoDash.raw_data_access.datasets.glofas as gl
from CrocoDash.raw_data_access.registry import ProductRegistry

print("glofas module:", gl.__file__)
print("cdsapi", cdsapi.__version__ if hasattr(cdsapi, "__version__") else "", "Client class ->", type(cdsapi.Client()).__module__)

fn = ProductRegistry.get_access_function("glofas", "get_global_data_with_python")
for window in (["2019-12-30", "2020-01-02"], ["2020-01-30", "2020-02-02"], ["2020-06-01", "2021-05-31"]):
    out = OUT / f"glofas_{window[0]}.nc"
    p = fn(dates=window, output_folder=OUT, output_filename=out.name)
    r = STATE["inputs"]
    want = pd.date_range(*window)
    print(f"\nwindow {window}: returned {p}")
    print(f"  sent: hyear={r['hyear']} hmonth={r['hmonth']} hday(len)={len(r['hday'])} download_format={r['download_format']!r}")
    print(f"  bytes on disk == server asset bytes: {Path(p).read_bytes() == STATE['payload']}; is zip: {zipfile.is_zipfile(p)}")
    try:
        with xr.open_dataset(p) as ds:
            print("  xr.open_dataset OK", ds.sizes)
    except Exception as e:
        print(f"  xr.open_dataset FAILED: {type(e).__name__}: {str(e).splitlines()[0][:160]}")
    # what the user actually gets after unzipping by hand
    if zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z:
            names = z.namelist()
            z.extractall(OUT / f"unz_{window[0]}")
        with xr.open_dataset(OUT / f"unz_{window[0]}" / names[0]) as ds:
            t = pd.DatetimeIndex(ds.valid_time.values)
        outside = t[(t < want[0]) | (t > want[-1])]
        print(f"  after manual unzip: {len(want)} days requested, file holds {len(t)} days, {len(outside)} outside;"
              f" first outside {[str(x.date()) for x in outside[:4]]}")

# fix check: download_format='unarchived' + same client path
orig = gl.cdsapi.Client


class PatchedClient:
    def __init__(self):
        self.c = orig()

    def retrieve(self, name, request, target):
        request = dict(request, download_format="unarchived")
        return self.c.retrieve(name, request, target)


gl.cdsapi.Client = PatchedClient
p = gl.GLOFAS.get_global_data_with_python(dates=["2020-01-01", "2020-01-03"], output_folder=OUT,
                                           output_filename="glofas_fix.nc")
with xr.open_dataset(p) as ds:
    print("\nfix check (download_format='unarchived'): xr.open_dataset OK, days:", ds.sizes["valid_time"])
srv.shutdown()
