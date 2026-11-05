#!/usr/bin/env python3
"""
xrp_neutral_grid.py — PRE-DECLARED parameter grid for the neutral XRP book.

THE GRID IS DECLARED HERE, BEFORE ANY RESULT WAS SEEN. That is the point: a grid
chosen after seeing results is a fitted grid, and the repo's protocol treats a
strategy that only wins by fishing as dead. 12 combinations, and the multiple-
testing cost is stated explicitly in the output.

Grid (12 combinations):
    trend_band    : {0.02, 0.10}   how far from the 1h EMA200 the book stands down
    stop_atr_mult : {0.5, 1.5}     hard-stop distance beyond the outermost level
    cover_mult    : {1, 2, 3}      cover distance in grid steps (the R:R knob)
    delta_max_pct : 0.50           fixed: the neutrality bound

The R:R observation that motivates the grid: the first baseline had a 75.8% win
rate with PF 0.918, because a cover earns ONE step (1 ATR) while the stop risks
5.5 ATR. You need 5.5 wins to pay for one stop. cover_mult is the direct knob.

Usage:  python code/xrp_neutral_grid.py [--sym XRPUSDT]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import xrp_neutral_engine as X  # noqa: E402

K15 = os.path.join(ROOT, "data", "binance_klines_15m")
FUND = os.path.join(ROOT, "data", "binance_funding")

GRID = {
    "trend_band": [0.02, 0.10],
    "stop_atr_mult": [0.5, 1.5],
    "cover_mult": [1.0, 2.0, 3.0],
}


def load15(sym):
    import csv
    p = os.path.join(K15, f"{sym}_15m.csv")
    rows = []
    with open(p) as f:
        for r in csv.DictReader(f):
            rows.append((int(r["open_ts"]), float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), float(r["volume"])))
    rows.sort(key=lambda b: b[0])
    return rows


def slices(eq, n=3):
    e = np.asarray(eq, float)
    out = []
    for k in range(n):
        a, b = int(len(e) * k / n), int(len(e) * (k + 1) / n)
        out.append(e[b - 1] / e[a] - 1.0 if b > a and e[b - 1] > 0 else 0.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="XRPUSDT")
    a = ap.parse_args()
    bars = load15(a.sym)
    print(f"{a.sym} 15m: {len(bars):,} bars\n")
    keys = list(GRID)
    combos = list(itertools.product(*[GRID[k] for k in keys]))
    print(f"PRE-DECLARED GRID: {len(combos)} combinations over {keys}")
    print("  (the multiple-testing haircut applies: with 12 draws, a winner is")
    print("   expected to look this good by chance more often than 1 time in 12)\n")
    print(f"{'trend':>6} {'stop':>5} {'cover':>6} {'net%':>9} {'PF':>7} {'n':>6} "
          f"{'win%':>6} {'maxDD%':>8} {'fund$':>9} {'fees$':>9} {'dFill%':>8} "
          f"{'green':>6} {'slices':>26}")
    rows = []
    for combo in combos:
        p = dict(zip(keys, combo))
        t0 = time.time()
        tr = {}
        eq = X.simulate(bars, a.sym, funding=True, fund_dir=FUND,
                        delta_max_pct=0.50, track=tr, **p)
        cp = tr["closed_pnl"]
        pf, win, n = X.metrics(cp)
        gross = sum(abs(x) for x in cp) or 1.0
        sl = slices(tr["eq_curve"])
        green = sum(1 for x in sl if x > 0)
        rows.append((p, 100 * (eq / X.INIT - 1), pf, n, win, tr["mdd"], tr["fund"],
                     tr["fees"], tr["max_delta_fill_pct"], green, sl))
        print(f"{p['trend_band']:>6} {p['stop_atr_mult']:>5} {p['cover_mult']:>6} "
              f"{100*(eq/X.INIT-1):>8.1f}% {pf:>7.3f} {n:>6} {win:>5.1f}% {tr['mdd']:>7.1f}% "
              f"{tr['fund']:>9.0f} {tr['fees']:>9.0f} {tr['max_delta_fill_pct']:>7.1f}% "
              f"{green:>4}/3  " + " / ".join(f"{100*x:+.1f}%" for x in sl))
    best = max(rows, key=lambda r: r[2])
    print(f"\nBEST BY PF: {best[0]}  net {best[1]:+.1f}%  PF {best[2]:.3f}  n {best[3]}")
    passing = [r for r in rows if r[2] > 1.2 and r[3] >= 30 and r[9] >= 2]
    print(f"combinations clearing PF>1.2, n>=30, green in 2/3: {len(passing)} of {len(rows)}")
    for r in passing:
        print(f"   {r[0]}  net {r[1]:+.1f}%  PF {r[2]:.3f}")
    out = os.path.join(ROOT, "results", "xrp_neutral_grid.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump([{"params": r[0], "net_pct": r[1], "PF": r[2], "n": r[3], "win_pct": r[4],
                "maxDD_pct": r[5], "funding": r[6], "fees": r[7],
                "max_delta_fill_pct": r[8], "green_periods": r[9], "slices": r[10]}
               for r in rows], open(out, "w"), indent=1, sort_keys=True)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
