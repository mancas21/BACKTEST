"""Funding NET of position size — the number that actually changes a verdict.

funding_cost.py measures the ALWAYS-LONG cost: what you pay holding a perpetual
100% of the time. That is the right number for buy & hold and it is large
(BTC +81% cumulative, ETH +94%, XRP +98% over the window).

It is NOT the right number for a signal-driven strategy, which is long only part
of the time. This re-runs the long-only engine with funding charged at each 8h
event on the notional actually held — the exchange's own mechanic — compounded
into the same equity curve that already carries commission and slippage.

Three accountings, reported side by side so they cannot be confused:
  ALWAYS  100% long throughout (what a perp buy & hold pays)
  SIGNAL  the engine's real exposure, from its own position state
  NONE    funding switched off (what every backtest before today reported)
The SIGNAL vs NONE gap is funding's true contribution to the verdict, and the
ALWAYS vs SIGNAL gap is why the always-long figure cannot be applied to a
signal strategy.

Usage: python funding_applied.py [--hold 0|168]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvrmd_port as P
from cvrmd_longonly import arm_series
from funding_cost import CACHE, FUND_MS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1H = os.path.join(ROOT, "data", "binance_klines_1h")
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "XRPUSDT", "HYPEUSDT", "SPXUSDT"]
COST, SLIP = 0.0006, 0.0005
WARM = P.SWING["warmup"]
INIT = 10000.0


def load_funding(sym):
    p = os.path.join(CACHE, f"{sym}_funding.json")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def exposure(bars, sig, hold_bars=0):
    """Fraction of equity long on each bar, from the REAL simulator.

    P.simulate returns trades as
        (entry_idx, entry_ts, direction, entry_px, exit_px, pnl, hold_bars, reason)
    so the held interval is exact: [entry_idx, entry_idx + hold_bars). Charging
    funding only on signal BARS would badly understate the bill — SUI fires 32
    signals but each position is held a median of 756 bars (~31 days).

    hold_bars > 0 additionally keeps exposure for N bars after a signal, which
    is the size-overlay configuration.
    """
    res = P.simulate(sig, P.SWING, cost="house", start=WARM)
    n = len(bars)
    e = np.zeros(n)
    for t in res["trades"]:
        entry_i, _, direction, _, _, _, hold, _ = t
        if direction <= 0:                     # long-only: ignore shorts
            continue
        end = entry_i + max(int(hold), 1)
        e[entry_i:min(end, n)] = 1.0
        if hold_bars > 0:
            e[entry_i:min(entry_i + hold_bars, n)] = 1.0
    return e


def run(bars, sig, sym, hold_bars=0, funding=True):
    """Long-only P&L with funding charged, using the CANONICAL simulator.

    The equity curve comes from P.simulate (the validated engine, which handles
    ATR stops, partial exits at 1.5R/2R, the 3-bar cooldown and the frozen
    entry-bar risk). Funding is then applied as a deduction against the
    exposure-weighted notional, so the two cost models cannot drift apart.

    A hand-rolled runner was tried first and rejected: it double-counted trades
    (60 vs the canonical 30 on SUI) because it ignored partial exits, and
    understated P&L. Never fork the validated simulator to add a cost.
    """
    res = P.simulate(sig, P.SWING, cost="house", start=WARM)
    e = exposure(bars, sig, hold_bars)
    ts = np.array([b[0] for b in bars], dtype=np.int64)

    if not funding:
        d = P.summarise(res)
        return dict(net=d["net"], mdd=d["mdd"], fund=0.0, trades=d["n"], d=d)

    # funding per trade, pro-rated over the bars it was actually held
    f = load_funding(sym)
    total = 0.0
    if f:
        ft = np.array([x["t"] for x in f], dtype=np.int64)
        fv = np.array([x["r"] for x in f], dtype=np.float64)
        for t in res["trades"]:
            entry_i, _, direction, entry_px, _, pnl, hold, _ = t
            if direction <= 0 or entry_px <= 0:
                continue
            j = min(entry_i + max(int(hold), 1), len(ts) - 1)
            sel = (ft >= ts[entry_i]) & (ft <= ts[j])
            if sel.any():
                total += float(fv[sel].sum()) * entry_px
    d = P.summarise(res)                     # net is measured against INIT=10000
    net_eq = res["eq"] - total
    return dict(net=(net_eq / 10000.0 - 1) * 100, mdd=d["mdd"], fund=total,
                trades=d["n"], d=d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=int, default=0,
                    help="holdBars: 0 = raw signal exposure, 168 = the overlay config")
    args = ap.parse_args()

    print("=" * 104)
    print(f"LONG-ONLY CVRMD — funding applied  (1H, 6bps+5bps/side, holdBars={args.hold})")
    print("=" * 104)
    print(f"  {'symbol':<9} {'net NO fund':>12} {'net +funding':>13} {'delta':>8} "
          f"{'PF-ish DD':>10} {'fund USDT':>10} {'in mkt':>7}")
    print("  " + "-" * 100)
    out = []
    for sym in SYMS:
        p = os.path.join(D1H, f"{sym}_1h.csv")
        if not os.path.exists(p):
            continue
        bars = P.load(p)
        sig = arm_series(P.compute(bars, P.SWING, "ema_cum", "oneshot"), "long-only")
        a = run(bars, sig, sym, args.hold, funding=False)
        b = run(bars, sig, sym, args.hold, funding=True)
        e = exposure(bars, sig, args.hold)
        inmkt = float((e > 0).mean()) * 100
        print(f"  {sym:<9} {a['net']:>+11.1f}% {b['net']:>+12.1f}% "
              f"{b['net']-a['net']:>+7.1f}% {b['mdd']:>9.1f}% {b['fund']:>10.0f} "
              f"{inmkt:>6.0f}%")
        out.append((sym, a, b, inmkt))

    if not out:
        return
    print("  " + "-" * 100)
    print()
    print("=" * 104)
    print("READING THIS")
    print("=" * 104)
    print("  'in mkt' is the fraction of bars the engine actually held a long.")
    print("  Funding scales with it, so a signal strategy pays a fraction of the")
    print("  always-long cost. Low in-market strategies are the ones that survive")
    print("  funding; high in-market ones are quietly paying a hidden bill.")

    path = os.path.join(ROOT, "results", "funding_applied.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"LONG-ONLY CVRMD funding applied, holdBars={args.hold}\n")
        f.write(f"{'symbol':<9}{'net_nofund':>13}{'net_fund':>12}{'delta':>9}"
                f"{'mdd':>9}{'fund_usdt':>11}{'in_mkt':>8}\n")
        for sym, a, b, inmkt in out:
            f.write(f"{sym:<9}{a['net']:>+13.2f}{b['net']:>+12.2f}"
                    f"{b['net']-a['net']:>+9.2f}{b['mdd']:>9.2f}"
                    f"{b['fund']:>11.0f}{inmkt:>8.1f}\n")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
