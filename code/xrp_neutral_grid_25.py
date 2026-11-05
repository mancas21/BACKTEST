#!/usr/bin/env python3
"""
xrp_neutral_grid_25.py — the SAME pre-declared 12-cell grid, at 25 USDT x 10x.

This is NOT a new search. The 12 cells are the ones declared in
xrp_neutral_grid.py BEFORE any result was seen, so the multiple-testing cost is
unchanged. What changes is the book's size relative to equity:

    equity          25 USDT
    per level       100% of equity  (25 USDT at inception)
    levels/side     5
    gross max       10x             (10 levels x 25 USDT = 250 USDT)
    net delta cap   2.0x equity     (50 USDT = two net lots)

WHY THE DELTA BOUND MUST MOVE. At 25 USDT equity and 1x equity per level, a
single lot is 25 USDT of notional. A 0.50x equity cap (12.50 USDT) would REFUSE
the first fill, so the bot could never trade. The cap has to be at least 1x for
one lot to exist. 2.0x keeps the *lot-level* bound of the validated book (at most
two net lots) while gross can reach the full 10x with both sides filled.

WHY MARGIN IS MEASURED, NOT ASSUMED. "10x" is a claim about margin. The base
engine does not liquidate, so a 10x run that quietly goes past maintenance would
be fiction. Per cell we report the maximum gross leverage actually reached and
the minimum distance to maintenance margin (0.5% of gross, Binance's base tier);
if that distance ever goes negative, the cell is marked UNVIABLE rather than
reported as profitable.

Usage:  python code/xrp_neutral_grid_25.py [--sym XRPUSDT]
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
K15 = os.path.join(ROOT, "data", "binance_klines_15m")
FUND = os.path.join(ROOT, "data", "binance_funding")

INIT_USDT = 25.0
EQUITY_PCT = 1.0
LEVERAGE = 10.0
DELTA_MAX = 2.0
MAINT_MARGIN = 0.005

# Identical to xrp_neutral_grid.py. Declared there, reused here on purpose.
GRID = {
    "trend_band": [0.02, 0.10],
    "stop_atr_mult": [0.5, 1.5],
    "cover_mult": [1.0, 2.0, 3.0],
}


def fresh_engine(eq_pct=EQUITY_PCT):
    """A SEPARATE module object, so the sizing override cannot leak into the
    validated engine's globals for any other importer in this process."""
    p = os.path.join(HERE, "xrp_neutral_engine.py")
    spec = importlib.util.spec_from_file_location("xrp_neutral_engine_25", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.EQUITY_PCT = eq_pct
    return m


def load15(sym):
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


def run_one(X, bars, sym, params, dmax):
    tr = {}
    eq = X.simulate(bars, sym, funding=True, fund_dir=FUND, init=INIT_USDT,
                    delta_max_pct=dmax, track=tr, **params)
    cp = np.asarray(tr["closed_pnl"], float)
    pf, win, n = X.metrics(list(cp))
    eqc = np.asarray(tr["eq_curve"], float)
    gross = np.asarray(tr["gross_curve"], float)
    expo = np.asarray(tr["expo_curve"], float)
    # Binance base-tier maintenance: 0.5% of notional. Liquidation when equity
    # falls to that level; the buffer is how far above it the book stayed.
    maint = MAINT_MARGIN * gross
    buf = (eqc - maint) / np.maximum(eqc, 1e-12)
    sl = slices(eqc)
    return {
        "params": params, "delta_max_pct": dmax,
        "net_pct": 100.0 * (eq / INIT_USDT - 1.0),
        "final_equity": float(eq),
        "PF": float(pf), "n": int(n), "win_pct": float(win),
        "maxDD_pct": float(tr["mdd"]),
        "funding": float(tr["fund"]), "fees": float(tr["fees"]),
        "max_delta_fill_pct": float(tr["max_delta_fill_pct"]),
        "max_gross_leverage": float(np.max(expo)) if len(expo) else 0.0,
        "min_margin_buffer_pct": float(np.min(buf) * 100.0),
        "min_equity_usdt": float(np.min(eqc)),
        "bars_over_leverage": int(np.sum(expo > LEVERAGE + 1e-9)),
        "green_periods": int(sum(1 for x in sl if x > 0)),
        "slices_pct": [100.0 * x for x in sl],
    }


def today_snapshot(bars, X):
    T = np.array([b[0] for b in bars], dtype=np.int64)
    H = np.array([b[2] for b in bars], float)
    L = np.array([b[3] for b in bars], float)
    C = np.array([b[4] for b in bars], float)
    a = X.atr(H, L, C)
    st = X.trend_strength(bars)
    atr_pct = 100.0 * a / C
    n30 = 30 * 96
    hi, lo = float(np.max(H[-n30:])), float(np.min(L[-n30:]))
    c = float(C[-1])
    r = np.diff(np.log(C[-7 * 96:]))
    rv_d = float(np.std(r) * np.sqrt(96) * 100.0)
    rate, ev, _ = X.funding_events("XRPUSDT", T, FUND)
    last_events = np.where(ev)[0]
    last_rate = float(rate[last_events[-1]]) if len(last_events) else 0.0
    return {
        "last_bar_utc": str(np.datetime64(int(T[-1]), "ms")),
        "close": c,
        "atr_15m_pct": float(atr_pct[-1]),
        "atr_pct_percentile_90d": float(
            100.0 * np.mean(atr_pct[-90 * 96:] < atr_pct[-1])),
        "trend_strength": float(st[-1]),
        "trend_band": 0.10,
        "range_30d_hi": hi, "range_30d_lo": lo,
        "range_30d_position_pct": 100.0 * (c - lo) / max(hi - lo, 1e-12),
        "realized_vol_daily_pct": rv_d,
        "last_funding_rate_pct": float(last_rate * 100.0),
        "rung_spacing_pct": float(atr_pct[-1]),
        "outermost_level_pct": float(5.0 * atr_pct[-1]),
        "stop_distance_pct": float(5.5 * atr_pct[-1]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="XRPUSDT")
    a = ap.parse_args()

    bars = load15(a.sym)
    X = fresh_engine()
    print(f"{a.sym} 15m: {len(bars):,} bars\n")

    print("=== TODAY'S REGIME ===")
    snap = today_snapshot(bars, X)
    for k, v in snap.items():
        print(f"  {k:<28} {v}")
    print()

    keys = list(GRID)
    combos = list(itertools.product(*[GRID[k] for k in keys]))
    print(f"PRE-DECLARED GRID: {len(combos)} combinations (same cells as v1)")
    print(f"sizing: equity {INIT_USDT:g} USDT x {LEVERAGE:g}x, "
          f"{EQUITY_PCT:g}x equity/level, net cap {DELTA_MAX:g}x equity\n")
    print(f"{'trend':>6} {'stop':>5} {'cover':>6} {'net%':>12} {'PF':>6} {'n':>6} "
          f"{'win%':>6} {'maxDD%':>7} {'maxExp':>7} {'minBuf%':>8} {'over':>5} "
          f"{'green':>6} {'finalEq':>12}")
    rows = []
    for combo in combos:
        p = dict(zip(keys, combo))
        t0 = time.time()
        r = run_one(X, bars, a.sym, p, DELTA_MAX)
        r["seconds"] = round(time.time() - t0, 1)
        rows.append(r)
        print(f"{p['trend_band']:>6} {p['stop_atr_mult']:>5} {p['cover_mult']:>6} "
              f"{r['net_pct']:>11.0f}% {r['PF']:>6.3f} {r['n']:>6} "
              f"{r['win_pct']:>5.1f}% {r['maxDD_pct']:>6.1f}% "
              f"{r['max_gross_leverage']:>6.2f}x {r['min_margin_buffer_pct']:>7.1f}% "
              f"{r['bars_over_leverage']:>5} {r['green_periods']:>4}/3 "
              f"{r['final_equity']:>11.2f}")

    viable = [r for r in rows if r["min_margin_buffer_pct"] > 0 and r["min_equity_usdt"] > 0]
    if not viable:
        print("\nNO VIABLE CELL: every combination breaches maintenance margin at 10x.")
        return 1
    best = max(viable, key=lambda r: r["PF"])
    print(f"\nBEST VIABLE BY PF: {best['params']}  net {best['net_pct']:+.0f}%  "
          f"PF {best['PF']:.3f}  n {best['n']}  maxDD {best['maxDD_pct']:.1f}%  "
          f"maxExp {best['max_gross_leverage']:.2f}x  "
          f"minBuf {best['min_margin_buffer_pct']:.1f}%")
    passing = [r for r in viable if r["PF"] > 1.2 and r["n"] >= 30 and r["green_periods"] >= 2]
    print(f"clearing PF>1.2, n>=30, green 2/3, margin-safe: {len(passing)} of {len(rows)}")

    # Sensitivity, NOT selection: the best cell re-run at other net caps, to show
    # what the neutrality bound costs or buys. Choosing the cap from this table
    # would be fitting; it is reported so the deployed number can be defended.
    print("\n=== NET-CAP SENSITIVITY (diagnostic, not selection) ===")
    sens = []
    for dmax in (1.0, 2.0, 5.0):
        r = run_one(X, bars, a.sym, best["params"], dmax)
        sens.append(r)
        print(f"  cap {dmax:>4.1f}x equity: net {r['net_pct']:>10.0f}%  PF {r['PF']:.3f} "
              f"maxDD {r['maxDD_pct']:.1f}%  maxExp {r['max_gross_leverage']:.2f}x  "
              f"minBuf {r['min_margin_buffer_pct']:.1f}%  "
              f"max|delta| {r['max_delta_fill_pct']:.1f}%")

    out = os.path.join(ROOT, "results", "xrp_neutral_grid_25.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"snapshot": snap, "sizing": {
        "init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
        "leverage": LEVERAGE, "delta_max_pct": DELTA_MAX,
        "maint_margin": MAINT_MARGIN},
        "cells": rows, "best": best, "net_cap_sensitivity": sens},
        open(out, "w"), indent=1, sort_keys=True)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
