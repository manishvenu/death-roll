# Feed the generated script's copernicusmarine line to the real CLI (network blocked by a dead proxy).
import sys, os, subprocess, shlex, re
from pathlib import Path
script = Path(sys.argv[1])
cmd = [l for l in script.read_text().splitlines() if l.startswith("copernicusmarine")][-1]
env = dict(os.environ)
env.update(HTTPS_PROXY="http://127.0.0.1:9", HTTP_PROXY="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9", http_proxy="http://127.0.0.1:9",
           PATH=str(Path(sys.executable).parent) + ":" + os.environ["PATH"])
r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=env, timeout=120)
print("generated line -> exit", r.returncode); print((r.stdout + r.stderr)[-600:])
stub = 'copernicusmarine() { shift; while [ $# -gt 0 ]; do case "$1" in -o|-f) echo "$1 = [$2]"; shift 2;; --*) shift 2;; *) echo "stray positional = [$1]"; shift;; esac; done; }'
fixed = re.sub(r" -o (.*) -f (\S+)$", lambda m: f" -o {shlex.quote(m.group(1))} -f {shlex.quote(m.group(2))}", cmd)
print("--- with shlex.quote on -o/-f (stubbed copernicusmarine) ---")
print(subprocess.run(["bash", "-c", stub + "; " + fixed], capture_output=True, text=True).stdout)
