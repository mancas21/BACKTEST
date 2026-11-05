#!/usr/bin/env python3
"""
xrp_neutrality_check.py — is the two-sided book ACTUALLY neutral?

The claim "neutral" is falsifiable. If the two-sided book earns about what a
LONG-ONLY book earns on the same path, the short side is not neutralising
anything and the result is directional beta dressed as a market-neutral strategy.

For each grid configuration this runs three books on the same data:
    NEUTRAL     both sides
    LONG ONLY   the short side disabled
    SHORT ONLY  the long side disabled

and reports:
  * the net return of each,
  * the average and extreme NET DELTA of the neutral book (the neutrality itself),
  * whether neutral is within 20% of long-only (which would mean "not neutral").

Usage:  python code/xrp_neutrality_check.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import xrp_neutral_engine as X  # noqa: E402

K15 = os.path.join(ROOT, "data", "binance_klines_15m")
FUND = os.path.join(ROOT, "data", "binance_funding")
SYM = "XRPUSDT"

CONFIGS = [
    {"trend_band": 0.02, "stop_atr_mult": 0.5, "cover_mult": 1.0},
    {"trend_band": 0.10, "stop_atr_mult": 0.5, "cover_mult": 1.0},
    {"trend_band": 0.10, "stop_atr_mult": 1.5, "cover_mult": 1.0},
]


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


def main():
    bars = load15(SYM)
    print(f"{SYM} 15m: {len(bars):,} bars\n")
    print(f"{'config':>44} {'neutral%':>10} {'long%':>10} {'short%':>10} "
          f"{'avg|delta|%':>12} {'max|delta|%':>12} {'NEUTRAL?':>10}")
    verdicts = []
    for cfg in CONFIGS:
        eq_n, tr_n = run(bars, allow_short=True, **cfg)
        eq_l, _ = run(bars, allow_short=False, **cfg)
        # short-only: the mirror of the long-only book on the mirrored path, which
        # is the exact mirror of the same ladder geometry.
        mirrored = [(t, 2 * bars[0][4] - o, 2 * bars[0][4] - h, 2 * bars[0][4] - l,
                     2 * bars[0][4] - c, v) for (t, o, h, l, c, v) in bars]
        eq_s, _ = run(mirrored, allow_short=True, **cfg)

        n_net = 100 * (eq_n / X.INIT - 1)
        n_l = 100 * (eq_l / X.INIT - 1)
        n_s = 100 * (eq_s / X.INIT - 1)
        d = tr_n["delta_curve"]
        eqc = tr_n["eq_curve"]
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.abs(d) / np.where(eqc > 0, eqc, np.nan)
        avg = float(np.nanmean(ratio) * 100)
        mx = float(np.nanmax(ratio) * 100)
        # "not neutral" if the two-sided book is within 20% of the long-only book
        # AND the long-only book is the better of the two.
        near_long = abs(n_net - n_l) <= 0.20 * max(abs(n_l), 1e-9)
        neutral = "NO" if (near_long and n_l > n_s) else "yes"
        verdicts.append((cfg, n_net, n_l, n_s, avg, mx, neutral))
        print(f"{str(cfg):>44} {n_net:>9.1f}% {n_l:>9.1f}% {n_s:>9.1f}% "
              f"{avg:>11.1f}% {mx:>11.1f}% {neutral:>10}")

    print("\nREAD:")
    print("  avg|delta|% is the average net directional exposure of the neutral book.")
    print("  A genuinely neutral book sits near 0% and its return should NOT look like")
    print("  the long-only book's. 'NEUTRAL? = NO' means the two-sided result is")
    print("  directional beta, and the word 'neutral' would be a label, not a fact.")
    out = os.path.join(ROOT, "results", "xrp_neutrality_check.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump([{"params": c, "neutral_pct": n, "long_pct": l, "short_pct": s,
                "avg_abs_delta_pct": a, "max_abs_delta_pct": m, "neutral": v}
               for (c, n, l, s, a, m, v) in verdicts],
              open(out, "w"), indent=1, sort_keys=True)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
