#!/usr/bin/env python
"""Zero-cost control: is there any GROSS edge, or only a cost artefact?

A strategy whose gross PF (0 fees, 0 slippage) is ~1.0 has no signal at all -- its
net PF is just noise minus cost. One whose gross PF is clearly > 1 but whose net PF
collapses is a real signal killed by costs. Those are different findings, and only
the control can tell them apart.

Runs through vrun.make_artifact, so every number persists as an artifact.

Usage:  python code/_cbpack_cost.py [tf ...]        (default 1h 15m 5m)
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import vrun  # noqa: E402

OUT = os.path.join(ROOT, "results", "cbpack_cost_control.json")
GROSS = {"fee_bps": 0.0, "slippage_bps": 0.0}
WATCH = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S09", "S10"]


def _scan(tf, params):
    """{symbol: {sid: row}} for cbpack cells of this tf with EXACTLY these params."""
    out = {}
    for p in sorted(glob.glob(os.path.join(vrun.RUNS, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        a = json.load(open(p, encoding="utf-8"))
        if (a.get("schema") == "bt-artifact/1" and a.get("strategy") == "cbpack"
                and a.get("timeframe") == tf and (a.get("params") or {}) == params):
            out[a["symbol"]] = {r["id"]: r for r in (a.get("tables") or [])}
    return out


def main() -> int:
    tfs = sys.argv[1:] or ["1h", "15m", "5m"]
    rec = {"note": "fee_bps=0, slippage_bps=0 -> gross (pre-cost) PF", "cells": [],
           "net_params": {}, "gross_params": GROSS}
    gross_by = {}

    for tf in tfs:
        net = _scan(tf, {})                       # the pack-cost full-window cells
        for sym in sorted(net):
            t = time.time()
            art = vrun.make_artifact("cbpack", tf, sym, GROSS)
            vrun.save_artifact(art)
            gross_by[(tf, sym)] = {r["id"]: r for r in art["tables"]}
            rec["cells"].append({"tf": tf, "sym": sym, "run_id": art["run_id"],
                                 "seconds": round(time.time() - t, 1)})
            print(f"  gross {tf} {sym:<10} {art['run_id']} {time.time()-t:5.1f}s", flush=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, sort_keys=True)

    print("\n" + "=" * 100)
    print(f"{'strat':<7}{'tf':<6}{'grossPF(0bp)':>14}{'netPF(14bp)':>13}{'cost drag':>11}"
          f"{'gross>1':>10}{'net>1':>8}{'gross>1.2':>11}")
    print("-" * 100)
    for tf in tfs:
        net = _scan(tf, {})
        for sid in WATCH:
            g, n = [], []
            for sym in sorted(set(net) | {s for (t, s) in gross_by if t == tf}):
                gr = gross_by.get((tf, sym), {}).get(sid)
                nr = net.get(sym, {}).get(sid)
                if gr and gr.get("status") == "ok":
                    g.append(gr["PF"])
                if nr and nr.get("status") == "ok":
                    n.append(nr["PF"])
            if not g:
                continue
            med = lambda v: sorted(v)[len(v) // 2] if v else float("nan")
            print(f"{sid:<7}{tf:<6}{med(g):>14.2f}{med(n):>13.2f}{med(g)-med(n):>11.2f}"
                  f"{sum(1 for v in g if v > 1.0):>8}/{len(g):<2}"
                  f"{sum(1 for v in n if v > 1.0):>6}/{len(n):<2}"
                  f"{sum(1 for v in g if v > 1.2):>9}/{len(g):<2}")
    print("=" * 100)
    print(f"wrote {OUT} ({len(rec['cells'])} zero-cost artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
