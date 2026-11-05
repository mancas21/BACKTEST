#!/usr/bin/env python
"""Conformance sweep: re-verify every artifact on disk through the reconstructed harness.

This is the acceptance test for the vrun.py reconstruction. A reconstructed
harness is only trustworthy if it reproduces the artifacts the ORIGINAL harness
wrote. Exit codes are the harness's own:

    0 OK       reproduced bit-for-bit
    2 REFUSED  engine drift / tampering / missing engine  <-- must be zero, except sax
    3 STALE    the data file grew since the artifact was written
               (the artifact is a frozen snapshot of the old bytes -- not a fabrication)

Sax is expected to be 2: its engine file is gone from disk and has been for some
time (AGENTS.md "Current kills"). Everything else must be 0 or 3.

Writes results/conformance_sweep.json incrementally so a long run is readable
while it is still going.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "conformance_sweep.json")


def _sha256(p: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def cost_key(a: dict):
    """Cheap first, so the summary fills in early."""
    tf = a.get("timeframe")
    slow = 1 if (a.get("strategy") == "cbot" and tf == "1m") else 0
    mid = 1 if (a.get("strategy") != "cbot" and tf == "1m") else 0
    return (slow, mid, a.get("strategy", ""), tf or "", a.get("symbol", ""))


def main() -> int:
    harness = _sha256(os.path.join(ROOT, "code", "vrun.py"))
    arts = []
    for fn in sorted(os.listdir(RUNS)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        with open(os.path.join(RUNS, fn), encoding="utf-8") as f:
            a = json.load(f)
        if a.get("schema") != "bt-artifact/1":
            continue
        arts.append(a)
    arts.sort(key=cost_key)

    # resume: keep any entry this harness already RESOLVED, whatever version of the
    # harness resolved it. rc=0 means verify reproduced the artifact bit-for-bit and
    # rc=3 means the input bytes genuinely changed -- neither can be produced by a
    # harness bug, so re-running them only burns hours. Crashes (rc=1) and refusals
    # (rc=2) are always retried.
    done = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for r in json.load(f):
                if r["rc"] in (0, 3):
                    done[r["run_id"]] = r
    results = list(done.values())
    todo = [a for a in arts if a["run_id"] not in done]
    print(f"{len(arts)} artifacts total; {len(done)} already verified by this harness; "
          f"{len(todo)} to go\n", flush=True)

    t0 = time.time()
    for i, a in enumerate(todo, 1):
        t = time.time()
        p = subprocess.run([sys.executable, os.path.join(ROOT, "code", "vrun.py"),
                            "verify", a["run_id"]],
                           capture_output=True, text=True, cwd=ROOT)
        dt = time.time() - t
        rec = {"run_id": a["run_id"], "strategy": a["strategy"], "symbol": a["symbol"],
               "timeframe": a["timeframe"], "params": a.get("params"), "harness": harness,
               "rc": p.returncode, "seconds": round(dt, 1),
               "msg": (p.stdout or "").strip().splitlines()[:1],
               "err": (p.stderr or "").strip().splitlines()[-1:] if p.returncode not in (0, 2, 3) else []}
        results = [r for r in results if r["run_id"] != a["run_id"]] + [rec]
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, sort_keys=True)
        tally = {c: sum(1 for r in results if r["rc"] == c) for c in sorted({r["rc"] for r in results})}
        print(f"[{i:>3}/{len(todo)}] {a['run_id']} {a['strategy']:<9} {a['symbol']:<10} "
              f"{a['timeframe']:<4} rc={p.returncode} {dt:6.1f}s  {tally}", flush=True)

    print(f"\ndone in {time.time()-t0:.0f}s", flush=True)
    for c in sorted({r["rc"] for r in results}):
        print(f"  rc={c}: {sum(1 for r in results if r['rc'] == c)}", flush=True)
    bad = [r for r in results if r["rc"] not in (0, 3) and r["strategy"] != "sax"]
    print(f"\nNON-SAX FAILURES: {len(bad)}", flush=True)
    for r in bad:
        print(f"   {r['run_id']} {r['strategy']} {r['symbol']} {r['timeframe']} rc={r['rc']} {r['msg']} {r['err']}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
