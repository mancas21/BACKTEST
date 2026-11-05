#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_emaadx_report_table.py — per-symbol gate table over all emaadx artifacts.

PRE-DECLARED gates (repo criteria, AGENTS.md):
  G1 pf_strict > 1.2
  G2 n >= 30 closed trades
  G3 period split: pf_h1 > 1 AND pf_h2 > 1
  G4 full window only: green in >= 2/3 of the calendar years scored
  G5 beats buy&hold on the same scored window
  G6 concentration: conc_net_without_top5_pct > 0 (None when the book's total
     pnl <= 0, in which case the gate FAILS by construction)
Usage: python code/_emaadx_report_table.py [run_ids...]  (default: every artifact)
"""
from __future__ import annotations

import glob
import json
import os
import sys

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "runs")


def load_all(ids=None):
    arts = []
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        with open(p, encoding="utf-8") as f:
            a = json.load(f)
        if isinstance(a.get("metrics"), dict) and a.get("strategy") != "emaadx":
            continue
        if ids and a.get("run_id") not in ids:
            continue
        arts.append(a)
    if not arts:
        raise SystemExit("no emaadx artifacts found")
    return arts


def gates(m):
    window = m.get("window", "?")
    pf = m.get("pf_strict")
    g1 = (pf is not None) and pf > 1.2
    g2 = (m.get("n") or 0) >= 30
    h1, h2 = m.get("pf_h1"), m.get("pf_h2")
    g3 = (h1 is not None and h2 is not None and h1 > 1 and h2 > 1)
    yrs = m.get("year_returns") or {}
    n_yr, n_green = len(yrs), len([v for v in yrs.values() if v > 0])
    g4 = (n_yr >= 3 and n_green * 3 >= n_yr * 2) if window == "full" else None
    g5 = bool(m.get("beats_bh"))
    c = m.get("conc_net_without_top5_pct")
    g6 = c is not None and c > 0
    gs = [g1, g2, g3] + ([g4] if g4 is not None else []) + [g5, g6]
    return gs, dict(g1=g1, g2=g2, g3=g3, g4=g4, g5=g5, g6=g6,
                    yr=(n_green, n_yr), conc=c)


def main(only_ids):
    arts = load_all(only_ids or None)
    arts.sort(key=lambda a: (a["metrics"].get("window", ""),
                             a["metrics"].get("costs", ""),
                             a["symbol"]))
    print("%-18s %-9s %-8s %-8s %9s %6s %5s %6s %6s %7s %8s %8s %7s %4s"
          % ("run_id", "symbol", "window", "costs",
             "ret%", "pfs", "n", "h1", "h2", "GYR", "B&H%", "conc-w/o",
             "dragpp", "PASS"))
    tally = {}
    for a in arts:
        m = a["metrics"]
        gs, g = gates(m)
        ng, ny = g["yr"]
        conc = g["conc"]
        passed = all(gs)
        key = (m.get("window"), m.get("costs"))
        tally[key] = tally.get(key, 0) + (1 if passed else 0)
        print("%-18s %-9s %-8s %-8s %9.2f %6s %5s %6s %6s %7s %8.2f %8s %7s %4s"
              % (a["run_id"], a["symbol"], m.get("window"), m.get("costs"),
                 m["ret_pct"],
                 '-' if m.get("pf_strict") is None else format(m.get("pf_strict"), ".2f"),
                 m.get("n"),
                 '-' if m.get("pf_h1") is None else format(m.get("pf_h1"), ".2f"),
                 '-' if m.get("pf_h2") is None else format(m.get("pf_h2"), ".2f"),
                 ('%d/%d' % (ng, ny)) if ny else 'n/a',
                 m.get("bench_ret_pct", float("nan")),
                 '-' if conc is None else format(conc, ".2f"),
                 '-' if m.get("drag_pp") is None else format(m.get("drag_pp"), ".2f"),
                 "PASS" if passed else "fail"))
        # explicit detail line for gates, since conc is not a headline column
        print("   gates: G1=%s G2=%s G3=%s G4=%s G5=%s G6=%s"
              % ("Y" if g["g1"] else "N", "Y" if g["g2"] else "N",
                 "Y" if g["g3"] else "N",
                 "n/a" if g["g4"] is None else ("Y" if g["g4"] else "N"),
                 "Y" if g["g5"] else "N", "Y" if g["g6"] else "N"))
    print("\nGate-pass counts by cell (in words):")
    for (w, c), v in sorted(tally.items()):
        print("  window %s / costs %s: %d of %d symbols pass G1..G6"
              % (w, c, v, sum(1 for x in arts if x["metrics"].get("window") == w
                              and x["metrics"].get("costs") == c)))


if __name__ == "__main__":
    main(sys.argv[1:])
