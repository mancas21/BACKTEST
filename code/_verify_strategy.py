#!/usr/bin/env python
"""Verify every artifact of one strategy, for artifacts created after the main
conformance sweep built its work list.

Same contract as _conformance_sweep.py: rc 0 = reproduces bit-for-bit, 2 = REFUSED
(tampering / non-reproducible -> do not publish), 3 = STALE (input bytes changed).

Usage:  python code/_verify_strategy.py cbpack
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")


def main() -> int:
    strategy = sys.argv[1] if len(sys.argv) > 1 else "cbpack"
    out = os.path.join(ROOT, "results", f"verify_{strategy}.json")

    arts = []
    for fn in sorted(os.listdir(RUNS)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        with open(os.path.join(RUNS, fn), encoding="utf-8") as f:
            a = json.load(f)
        if a.get("schema") == "bt-artifact/1" and a.get("strategy") == strategy:
            arts.append(a)
    print(f"{len(arts)} {strategy} artifacts to verify\n", flush=True)

    results = []
    t0 = time.time()
    for i, a in enumerate(arts, 1):
        t = time.time()
        p = subprocess.run([sys.executable, os.path.join(ROOT, "code", "vrun.py"),
                            "verify", a["run_id"]], capture_output=True, text=True, cwd=ROOT)
        dt = time.time() - t
        rec = {"run_id": a["run_id"], "symbol": a["symbol"], "timeframe": a["timeframe"],
               "params": a.get("params"), "rc": p.returncode, "seconds": round(dt, 1),
               "msg": (p.stdout or "").strip().splitlines()[:1],
               "err": (p.stderr or "").strip().splitlines()[-1:] if p.returncode not in (0, 2, 3) else []}
        results.append(rec)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, sort_keys=True)
        tally = {c: sum(1 for r in results if r["rc"] == c) for c in sorted({r["rc"] for r in results})}
        print(f"[{i:>3}/{len(arts)}] {a['run_id']} {a['symbol']:<10} {a['timeframe']:<4} "
              f"{json.dumps(a.get('params') or {}, sort_keys=True)[:44]:<46} "
              f"rc={p.returncode} {dt:6.1f}s {tally}", flush=True)

    print(f"\ndone in {time.time()-t0:.0f}s", flush=True)
    bad = [r for r in results if r["rc"] not in (0, 3)]
    print(f"FAILURES (not rc 0 or 3): {len(bad)}", flush=True)
    for r in bad:
        print(f"   {r['run_id']} {r['symbol']} {r['timeframe']} {r['params']} rc={r['rc']} "
              f"{r['msg']} {r['err']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
