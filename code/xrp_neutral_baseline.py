#!/usr/bin/env python3
"""
xrp_neutral_baseline.py — baseline + kill criteria for the NEUTRAL XRP book.

Runs the neutral book over the real XRPUSDT 15m history in data/binance_klines_15m
and reports the repo's kill criteria. This is the DAY-0 reference the paper bot is
measured against.

The criteria (repo protocol, AGENTS.md):
  * OOS PF < 1            -> KILL, no rescue loops
  * ex-cost PF > 1.2      -> required to survive
  * n >= 30 closed trades
  * commission/gross < 30-40%
  * green in >= 2/3 periods
  * walk-forward holds
  * NEUTRALITY: max |net delta| must stay inside the configured cap
  * FUNDING: the neutral book should pay materially less funding than the long grid

Usage:  python code/xrp_neutral_baseline.py [--sym XRPUSDT]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import xrp_neutral_engine as X  # noqa: E402

K15 = os.path.join(ROOT, "data", "binance_klines_15m")
FUND = os.path.join(ROOT, "data", "binance_funding")


def load15(sym):
    p = os.path.join(K15, f"{sym}_15m.csv")
    if not os.path.exists(p):
        raise SystemExit(f"missing {p}")
    rows = []
    with open(p) as f:
        for r in csv.DictReader(f):
            rows.append((int(r["open_ts"]), float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), float(r["volume"])))
    rows.sort(key=lambda b: b[0])
    return rows


import csv  # noqa: E402  (used by load15)


def period_slices(eq, n=3):
    e = np.asarray(eq, float)
    out = []
    for k in range(n):
        a, b = int(len(e) * k / n), int(len(e) * (k + 1) / n)
        if b > a and e[b - 1] > 0:
            out.append(e[b - 1] / e[a] - 1.0)
        else:
            out.append(0.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="XRPUSDT")
    ap.add_argument("--tf", default="15m")
    a = ap.parse_args()

    bars = load15(a.sym)
    print(f"{a.sym} {a.tf}: {len(bars):,} bars  "
          f"{pd.to_datetime(bars[0][0], unit='ms', utc=True)} -> "
          f"{pd.to_datetime(bars[-1][0], unit='ms', utc=True)}")

    tr = {}
    eq = X.simulate(bars, a.sym, funding=True, fund_dir=FUND, track=tr)
    cp = tr["closed_pnl"]
    pf, win, n = X.metrics(cp)
    gross = sum(abs(x) for x in cp) or 1.0
    fees = tr["fees"]
    sl = period_slices(tr["eq_curve"])

    print(f"\n  equity        ${eq:,.2f}   (init ${X.INIT:,.0f})   "
          f"net {100*(eq/X.INIT-1):+.2f}%")
    print(f"  max drawdown  {tr['mdd']:.2f}%")
    print(f"  closed trades {n}   win {win:.1f}%   PF {pf:.3f}")
    print(f"  fees ${tr['fees']:,.2f}   funding ${tr['fund']:,.2f}   "
          f"commission/gross {100*fees/gross:.1f}%")
    print(f"  grids built {tr['grids']}   fills {tr['fills']}   cycles {tr['cycles']}")
    print(f"  NEUTRALITY: max |net delta| {tr['max_abs_delta_pct']:.2f}% of equity   "
          f"cap hits {tr['delta_cap_hits']}   stand-down bars {tr['stand_down_bars']:,}")
    print(f"  exit reasons {tr['reasons']}")
    print(f"  period returns " + " / ".join(f"{100*x:+.1f}%" for x in sl))
    print(f"  funding prints {tr['n_funding_events']}")

    print("\n  KILL CRITERIA")
    crit = [
        ("OOS PF >= 1", pf >= 1.0),
        ("ex-cost PF > 1.2", pf > 1.2),
        ("n >= 30 closed trades", n >= 30),
        ("commission/gross < 40%", 100 * fees / gross < 40.0),
        ("green in >= 2/3 periods", sum(1 for x in sl if x > 0) >= 2),
        (f"max |delta| <= {100*X.DELTA_MAX_PCT:.0f}% of equity", tr["max_abs_delta_pct"] <= 100 * X.DELTA_MAX_PCT + 1e-6),
    ]
    for name, ok in crit:
        print(f"    [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"    [{'PASS' if pf >= 1.0 else 'FAIL'}] -> "
          f"{'SURVIVES' if all(o for _, o in crit) else 'KILLED / NOT A CANDIDATE'}")
    print("\n  NOTE: this is the DAY-0 reference over FULL history, not out-of-sample.")
    print("  A full-history number is an upper bound; the paper bot measures the")
    print("  forward window. See code/xrp_neutral_audit.py for the known-answer tests.")


if __name__ == "__main__":
    main()
