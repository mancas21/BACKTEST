#!/usr/bin/env python3
"""
xrp_neutral_gauntlet.py — the same gauntlet the pack candidates failed.

A number is a result only if it survives an attempt to break it. For the
neutral XRP book that means:

  1. CONCENTRATION. If the best 5 trades carry more than the whole PnL, the
     result is a handful of lucky positions, not an edge.
  2. SIGNIFICANCE. Bootstrap CI of the mean per trade. If it crosses zero, the
     edge is not distinguishable from luck.
  3. PERIOD SPLIT. Green in at least 2 of 3 equal slices.
  4. OUT-OF-SAMPLE. The parameters are FIXED; the strategy is run on a window it
     was not chosen on. No re-tuning, no window picking.
  5. NEUTRALITY. The average net delta must be near zero, or "neutral" is a label.
  6. MULTIPLE TESTING. The grid had 12 combinations; two passed. The winner is a
     MAX over 12 draws, and that is stated, not hidden.

Usage:  python code/xrp_neutral_gauntlet.py
"""
from __future__ import annotations

import csv
import json
import math
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
SYM = "XRPUSDT"

# the winner of the PRE-DECLARED 12-combination grid
BEST = {"trend_band": 0.10, "stop_atr_mult": 0.5, "cover_mult": 1.0}

rng = np.random.default_rng(7)
FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def load15(sym):
    p = os.path.join(K15, f"{sym}_15m.csv")
    rows = []
    with open(p) as f:
        for r in csv.DictReader(f):
            rows.append((int(r["open_ts"]), float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), float(r["volume"])))
    rows.sort(key=lambda b: b[0])
    return rows


def run(bars, **kw):
    tr = {}
    eq = X.simulate(bars, SYM, funding=True, fund_dir=FUND, track=tr, **kw)
    return eq, tr


def boot_ci(x, n=20000):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    m = np.array([rng.choice(x, len(x), True).mean() for _ in range(n)])
    t = x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))
    return t, np.percentile(m, 2.5), np.percentile(m, 97.5), (m <= 0).mean()


def slices(eq, n=3):
    e = np.asarray(eq, float)
    out = []
    for k in range(n):
        a, b = int(len(e) * k / n), int(len(e) * (k + 1) / n)
        out.append(e[b - 1] / e[a] - 1.0 if b > a and e[b - 1] > 0 else 0.0)
    return out


def main():
    bars = load15(SYM)
    ts = [b[0] for b in bars]
    print(f"{SYM} 15m: {len(bars):,} bars  "
          f"{pd.to_datetime(ts[0], unit='ms', utc=True).date()} -> "
          f"{pd.to_datetime(ts[-1], unit='ms', utc=True).date()}")
    print(f"config (winner of the pre-declared 12-combo grid): {BEST}\n")

    eq, tr = run(bars, **BEST)
    cp = np.asarray(tr["closed_pnl"], float)
    pf, win, n = X.metrics(list(cp))
    net = eq / X.INIT - 1
    print(f"FULL HISTORY: net {100*net:+.1f}%   PF {pf:.3f}   n {n}   win {win:.1f}%   "
          f"maxDD {tr['mdd']:.1f}%   funding ${tr['fund']:,.0f}   fees ${tr['fees']:,.0f}")

    # 1. concentration
    srt = np.sort(cp)[::-1]
    tot = srt.sum()
    share5 = srt[:5].sum() / tot if tot else float("nan")
    without5 = (tot - srt[:5].sum()) / X.INIT
    print(f"\n1. CONCENTRATION")
    print(f"   best 5 trades = {100*share5:.0f}% of total PnL   net without them {100*without5:+.1f}%")
    check("result survives removing the best 5 trades", without5 > 0,
          f"without best-5: {100*without5:+.1f}%")

    # 2. significance
    t, lo, hi, p0 = boot_ci(cp)
    print(f"\n2. SIGNIFICANCE  (bootstrap of mean per trade)")
    print(f"   mean {cp.mean():+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  t={t:+.2f}  P(<=0)={p0:.1%}")
    check("bootstrap CI excludes zero", lo > 0, f"CI [{lo:+.4f}, {hi:+.4f}]")

    # 3. period split
    sl = slices(tr["eq_curve"])
    print(f"\n3. PERIOD SPLIT  " + " / ".join(f"{100*x:+.1f}%" for x in sl))
    check("green in at least 2 of 3 periods", sum(1 for x in sl if x > 0) >= 2)

    # 4. out-of-sample, FIXED parameters
    print(f"\n4. OUT-OF-SAMPLE  (parameters frozen; no re-tuning)")
    splits = [("2020-2022 -> 2023-2026", "2023-01-01", "2026-12-31"),
              ("first half -> second half", None, None)]
    for label, a, b in splits:
        if a is None:
            h = len(bars) // 2
            tr_b, te_b = bars[:h], bars[h:]
        else:
            ta = pd.Timestamp(a, tz="UTC").value // 10**6
            tb = pd.Timestamp(b, tz="UTC").value // 10**6
            tr_b = [x for x in bars if x[0] < ta]
            te_b = [x for x in bars if x[0] >= ta and x[0] < tb]
        if not tr_b or not te_b:
            continue
        eq_tr, _ = run(tr_b, **BEST)
        eq_te, tr_te = run(te_b, **BEST)
        pf_te, _, n_te = X.metrics(list(tr_te["closed_pnl"]))
        print(f"   {label}: train {100*(eq_tr/X.INIT-1):+.1f}%  ->  "
              f"TEST {100*(eq_te/X.INIT-1):+.1f}%  PF {pf_te:.3f}  n {n_te}  "
              f"maxDD {tr_te['mdd']:.1f}%")
        check(f"OOS positive ({label})", eq_te > X.INIT, f"OOS {100*(eq_te/X.INIT-1):+.1f}%")

    # 5. neutrality
    d = tr["delta_curve"]
    e = tr["eq_curve"]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.abs(d) / np.where(e > 0, e, np.nan)
    avg = float(np.nanmean(ratio) * 100)
    print(f"\n5. NEUTRALITY  average |net delta| = {avg:.2f}% of equity   "
          f"(max {np.nanmax(ratio)*100:.1f}%)")
    check("average net delta is near zero", avg < 10.0, f"avg |delta| {avg:.2f}%")

    # 6. multiple testing
    print(f"\n6. MULTIPLE TESTING")
    print("   the grid had 12 pre-declared combinations; 2 cleared PF>1.2 & n>=30 & 2/3 green.")
    print("   This number is the MAX over those 12 draws. The haircut applies.")

    print("\n" + "=" * 74)
    if FAIL:
        print(f"GAUNTLET FAILED: {len(FAIL)} check(s): {FAIL}")
    else:
        print("GAUNTLET PASSED — the book is a candidate for forward paper")
    out = os.path.join(ROOT, "results", "xrp_neutral_gauntlet.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"config": BEST, "net_pct": float(100 * net), "PF": pf, "n": n,
               "win_pct": win, "maxDD_pct": tr["mdd"], "funding": tr["fund"],
               "fees": tr["fees"], "best5_share_pct": float(100 * share5),
               "net_without_best5_pct": float(100 * without5),
               "bootstrap_ci": [float(lo), float(hi)], "t": float(t),
               "p_mean_le_zero": float(p0), "slices": [float(x) for x in sl],
               "avg_abs_delta_pct": avg, "failed": FAIL}, open(out, "w"), indent=1)
    print(f"wrote {out}")
    raise SystemExit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
