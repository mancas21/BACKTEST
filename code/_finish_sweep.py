"""Wait for the running conformance sweep to finish, then run the finishing pass.

Why: the sweep currently running verified three cbot 1m slice artifacts BEFORE the
warmup fix, so they sit in results/conformance_sweep.json as rc=2 (REFUSED). The
sweep's own resume rule retries rc=2 automatically. That pass also extends the
record to the cbpack artifacts the current sweep's fixed work list never covered.
"""
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
LOG = (r"C:\Users\Lenovo\.local\share\opencode\shell"
       r"\fa20823d0df51dff9500eed8225add0541bf26de\sh_14b74edda001KcaErx1bhgTfLg.out")

print("waiting for the running sweep to print its summary line...", flush=True)
for i in range(120):                      # up to 40 min
    try:
        with open(LOG, encoding="utf-8", errors="replace") as f:
            if "NON-SAX FAILURES" in f.read():
                break
    except OSError:
        pass
    time.sleep(20)
else:
    print("TIMEOUT waiting for the sweep; running the finish pass anyway", flush=True)

prev = json.load(open(os.path.join(ROOT, "results", "conformance_sweep.json"), encoding="utf-8"))
print(f"record before the finish pass: {len(prev)} entries", flush=True)

t = time.time()
p = subprocess.run([sys.executable, os.path.join(ROOT, "code", "_conformance_sweep.py")],
                   cwd=ROOT)
print(f"finish pass exit={p.returncode} in {time.time()-t:.0f}s", flush=True)

cur = json.load(open(os.path.join(ROOT, "results", "conformance_sweep.json"), encoding="utf-8"))
bad = [r for r in cur if r["rc"] not in (0, 3)]
nonsax = [r for r in bad if r["strategy"] != "sax"]
print(f"FINAL: {len(cur)} entries; rc not in (0,3): {len(bad)} "
      f"(sax {len(bad)-len(nonsax)} + non-sax {len(nonsax)})", flush=True)
for r in nonsax:
    print(f"   NON-SAX {r['run_id']} {r['strategy']} {r['symbol']} {r['timeframe']} "
          f"rc={r['rc']} {r['msg']}", flush=True)
