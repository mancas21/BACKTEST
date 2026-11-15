#!/usr/bin/env python
"""Regression: re-run the citable prompts100/top10 artifacts under the
generation-2 cut hashing and require EXACT metric equality with the stored
artifact. cut_ts = stored input end + 1s, so the served slice is the byte
prefix that equals the original file (PREFIX-INTACT ones only; the two whose
on-disk bytes changed since creation -- SUI funding, JUP taker klines -- are
excluded and remain legacy-STALE, honestly).

Usage: python code/_cut_regression_prompts100.py [--ids id1,id2]
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import vrun  # noqa: E402

EXCLUDE = {"2238dab3387fa706", "87d05e23be45b524"}   # PREFIX-CHANGED (measured)


def main() -> int:
    only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 and sys.argv[1] else None
    arts = []
    for p in sorted(os.listdir(os.path.join(ROOT, "results", "runs"))):
        if p.startswith("_") or not p.endswith(".json"):
            continue
        a = json.load(open(os.path.join(ROOT, "results", "runs", p), encoding="utf-8"))
        if a.get("strategy") in ("prompts100", "top10") and a["run_id"] not in EXCLUDE:
            arts.append(a)
    if only:
        arts = [a for a in arts if a["run_id"] in only]

    n_ok = n_fail = 0
    for a in arts:
        # one cut for ALL inputs: the max input end + 1s, so every input's
        # slice is its full original content (multi-input artifacts splice
        # main + tail files; cutting at the main file's end would drop the tail)
        cut = vrun._norm_cut_ts(max(vrun._parse_cut_ts(i["end"]) for i in a["inputs"]) + 1000)
        t0 = time.time()
        try:
            b = vrun.make_artifact(a["strategy"], a["timeframe"], a["symbol"],
                                   a["params"], cut_ts=cut)
        except Exception as e:
            print(f"FAIL {a['run_id']} {a['strategy']} {a['symbol']} id={a['params'].get('id')}: "
                  f"{type(e).__name__}: {e}")
            n_fail += 1
            continue
        dt = time.time() - t0
        same_m = vrun._same(a["metrics"], b["metrics"])
        same_t = vrun._same(a.get("tables"), b.get("tables"))
        # inputs hashes must equal the stored full-file hashes (prefix intact)
        same_in = all(x[1] == y[1] and x[2] == y[2]
                      for x, y in zip(a["core"]["inputs"], b["core"]["inputs"]))
        ok = same_m and same_t and same_in
        tag = "PASS" if ok else "FAIL"
        print(f"{tag} {a['run_id']} {a['strategy']:<11} {a['symbol']:<9} "
              f"id={str(a['params'].get('id')):<3} cut={cut[:10]} {dt:6.1f}s "
              f"metrics={same_m} tables={same_t} inputs={same_in}")
        if ok:
            vrun.save_artifact(b)
            print(f"     saved gen-2 artifact {b['run_id']} (cut {cut})")
            n_ok += 1
        else:
            n_fail += 1
            for k in sorted(set(a["metrics"]) | set(b["metrics"])):
                av, bv = a["metrics"].get(k), b["metrics"].get(k)
                if not vrun._same(av, bv):
                    print(f"     {k}: stored={av} recomputed={bv}")
    print(f"\nregression: {n_ok} PASS, {n_fail} FAIL (of {len(arts)})")
    return 0 if not n_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
