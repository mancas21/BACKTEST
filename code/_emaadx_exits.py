#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_emaadx_exits.py — exit-reason distribution straight from artifact tables."""
import json
import os
import sys
from collections import Counter

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "results", "runs")

for rid in sys.argv[1:]:
    p = os.path.join(RUNS, rid + ".json")
    with open(p, encoding="utf-8") as f:
        a = json.load(f)
    rows = a.get("tables") or []
    c = Counter()
    pnl = {}
    for r in rows:
        if r.get("kind") != "trade" or "why" not in r:
            continue
        c[r["why"]] += 1
        pnl[r["why"]] = pnl.get(r["why"], 0.0) + r["pnl"]
    tot = sum(c.values())
    print("%s (%s %s %s): n_close_rows=%d" % (rid, a["strategy"], a["symbol"],
                                              a["timeframe"], tot))
    for k in ("SL", "TP", "reverse"):
        if c[k]:
            print("  %-8s %5d rows   sum_pnl=%.2f" % (k, c[k], pnl[k]))
    openn = (a.get("metrics") or {}).get("n_open")
    if openn:
        print("  open     %5d (marked, not a row)" % openn)
