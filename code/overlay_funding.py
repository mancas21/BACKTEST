"""Funding on the SIZE OVERLAY — the configuration that actually holds a position.

Two different things were measured and they must not be conflated:

  SIGNAL strategy (holdBars=0)  fires ~30 times in 3.5 years and each position
    lasts ~13 bars. It is in the market ~1.3% of the time, so its funding bill
    is ~0.0-0.3% — negligible. funding_applied.py shows this.

  SIZE OVERLAY (holdBars=168)  is FULL 14-26% of bars and REDUCED the rest, so
    it holds something ~85-90% of the time. THIS is where the always-long cost
    (+81% BTC, +94% ETH, +98% XRP cumulative) actually lands, because funding
    scales with time-in-market, not with trade count.

That distinction is the whole point: the overlay's drawdown benefit was measured
against buy & hold, and buy & hold on a PERPETUAL pays funding that a SPOT
holding does not. If the overlay is compared against a spot benchmark but pays a
perp's funding, the comparison is rigged in the overlay's favour.

This charges funding inside cvrmd_sizer's own cash+shares accounting — the same
loop that produced the headline numbers — rather than mixing simulators.

Usage: python overlay_funding.py [--hold 168]
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvrmd_port as P
from cvrmd_longonly import arm_series
from cvrmd_sizer import target_states, buy_and_hold
from funding_applied import load_funding

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1H = os.path.join(ROOT, "data", "binance_klines_1h")
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "XRPUSDT", "HYPEUSDT", "SPXUSDT"]
COST, SLIP = 0.0006, 0.0005
WARM = P.SWING["warmup"]
INIT = 10000.0
FUND_MS = 8 * 3600 * 1000


def overlay_funded(bars, sig, sym, reduced=0.5, floor=0.25, hold_bars=168,
                   min_hold=3, funding=True):
    """Identical to cvrmd_sizer.overlay, plus funding on the held notional.

    Copied rather than imported-and-patched so the funding charge is provably
    inside the same accounting that produced the published numbers. A diff
    against cvrmd_sizer.overlay with funding=False must return the same equity.
    """
    O = np.array([b[1] for b in bars]); C = np.array([b[4] for b in bars])
    T = np.array([b[0] for b in bars], dtype=np.int64)
    n = len(bars)
    st = target_states(bars, sig, hold_bars=hold_bars)

    # Funding is charged ONLY at each 8h event, not once per hourly bar.
    # Assigning the prevailing rate to every bar and charging each one bills
    # 8x too much (29,810 bars vs 3,726 events on SUI) — that bug produced
    # impossible numbers like ETH -1324% before it was caught.
    is_event = np.zeros(n, dtype=bool)
    frate = np.zeros(n)
    if funding:
        f = load_funding(sym)
        if f:
            ft = np.array([x["t"] for x in f], dtype=np.int64)
            fv = np.array([x["r"] for x in f], dtype=np.float64)
            m = (ft >= T[0]) & (ft <= T[-1])
            ft, fv = ft[m], fv[m]
            for ts_e, rate in zip(ft, fv):
                j = int(np.searchsorted(T, ts_e, side="left"))
                if j < n:
                    is_event[j] = True
                    frate[j] = rate

    cash, shares, frac = INIT, 0.0, None
    peak, mdd = 0.0, 0.0
    rebal, fund_paid = 0, 0.0
    last_change = -10 ** 9
    for i in range(max(WARM, 1), n):
        o = O[i]
        eq_now = cash + shares * o
        if eq_now <= 0:
            continue
        want = st[i - 1]
        tgt = 1.0 if want == 1 else (floor if want == 2 else reduced)
        if tgt != frac and (i - last_change) >= min_hold:
            px = o * (1 + SLIP)
            delta = eq_now * tgt - shares * o
            if abs(delta) > eq_now * 0.005:
                fee = abs(delta) * COST
                cash -= delta + fee
                shares += delta / px
                frac = tgt
                rebal += 1
                last_change = i
            else:
                frac = tgt
        if funding and shares > 0 and is_event[i]:
            f = shares * o * frate[i]
            cash -= f
            fund_paid += f
        ce = cash + shares * C[i]
        peak = max(peak, ce)
        mdd = max(mdd, (peak - ce) / max(peak, 1e-9))
    return dict(eq=ce, net=(ce / INIT - 1) * 100, mdd=mdd * 100,
                rebal=rebal, fund=fund_paid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=int, default=168)
    ap.add_argument("--symbols", nargs="*", default=SYMS)
    args = ap.parse_args()

    print("=" * 104)
    print(f"SIZE OVERLAY with funding  (1H, holdBars={args.hold}, reduced 0.5 / floor 0.25)")
    print("=" * 104)
    print(f"  {'symbol':<9} {'overlay':>9} {'+funding':>10} {'delta':>8} {'fund USDT':>10} "
          f"{'DD':>7} {'spot BH':>9} {'perp BH*':>9}")
    print("  " + "-" * 96)
    rows = []
    for sym in args.symbols:
        p = os.path.join(D1H, f"{sym}_1h.csv")
        if not os.path.exists(p):
            continue
        bars = P.load(p)
        sig = arm_series(P.compute(bars, P.SWING, "ema_cum", "oneshot"), "long-only")
        a = overlay_funded(bars, sig, sym, hold_bars=args.hold, funding=False)
        b = overlay_funded(bars, sig, sym, hold_bars=args.hold, funding=True)
        bh = buy_and_hold(bars)
        st = target_states(bars, sig, hold_bars=args.hold)
        inmkt = float((st != 0).mean()) * 100
        print(f"  {sym:<9} {a['net']:>+8.1f}% {b['net']:>+9.1f}% "
              f"{b['net']-a['net']:>+7.1f}% {b['fund']:>10.0f} {b['mdd']:>6.1f}% "
              f"{bh['net']:>+8.0f}% {'see note':>9}")
        rows.append((sym, a, b, bh, inmkt))

    if not rows:
        return
    print("  " + "-" * 96)
    print(f"\n  time in market (holding something, not flat): "
          f"{min(r[4] for r in rows):.0f}-{max(r[4] for r in rows):.0f}% of bars")
    print()
    print("=" * 104)
    print("THE COMPARISON THAT MATTERS")
    print("=" * 104)
    print("  'spot BH' is buy & hold WITHOUT funding — the benchmark the overlay")
    print("  was declared to beat. But the overlay runs on a PERPETUAL and pays")
    print("  funding continuously. A fair comparison charges funding to BOTH sides.")
    print()
    for sym, a, b, bh, inmkt in rows:
        bh_perp = bh["net"] - 0.0        # placeholder filled below
        print(f"  {sym:<9} overlay+funding {b['net']:+7.1f}%  vs  "
              f"spot BH {bh['net']:+7.0f}%  ({b['net']-bh['net']:+.0f}pp)")

    path = os.path.join(ROOT, "results", "overlay_funding.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"SIZE OVERLAY funding, holdBars={args.hold}\n")
        f.write(f"{'symbol':<9}{'nofund':>10}{'withfund':>11}{'delta':>9}"
                f"{'fund_usdt':>11}{'mdd':>8}{'bh':>10}\n")
        for sym, a, b, bh, inmkt in rows:
            f.write(f"{sym:<9}{a['net']:>+10.2f}{b['net']:>+11.2f}"
                    f"{b['net']-a['net']:>+9.2f}{b['fund']:>11.0f}"
                    f"{b['mdd']:>8.2f}{bh['net']:>+10.2f}\n")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
