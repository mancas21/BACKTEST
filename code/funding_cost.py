"""Does the CVRMD long-only result survive FUNDING?

Every long-only number produced on 2026-09-26 — SUI PF 1.97, +16.4% headline,
the size overlay's 77%->50% drawdown cut — came from a backtest that charged
commission and slippage but NOT funding. On a Binance USDT-M perpetual the long
side pays funding every 8h whenever the rate is positive, which in a rising
market is most of the time. That is a real, continuous, unavoidable cost and it
was entirely missing.

This measures it. For each symbol it pulls the full funding history, computes
the actual cumulative cost of holding one long from the first to the last bar of
our 1h dataset, and re-runs the long-only strategy net of it.

The honest comparison is cumulative funding, not an average rate: a strategy
that is long 100% of the time pays every 8h, while a signal-driven strategy
pays only while it holds. This script reports both.

Usage:
  python funding_cost.py                    # all symbols with 1h data
  python funding_cost.py --symbols SUIUSDT --hold-mode signal
"""
import argparse
import json
import os
import sys
import time
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvrmd_port as P
from cvrmd_longonly import arm_series

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1H = os.path.join(ROOT, "data", "binance_klines_1h")
CACHE = os.path.join(ROOT, "data", "binance_funding")
os.makedirs(CACHE, exist_ok=True)

FAPI = "https://fapi.binance.com/fapi/v1/fundingRate"
UA = {"User-Agent": "Mozilla/5.0"}
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "XRPUSDT", "HYPEUSDT", "SPXUSDT"]
FUND_MS = 8 * 3600 * 1000          # funding is charged every 8h


def fetch_funding(sym, tries=4):
    """Full funding history for a symbol, paged forward in time.

    /fapi/v1/fundingRate returns one record per funding event. Binance caps
    `limit` at 1000, so history before ~83 days back needs paging with
    startTime. Cache to disk because this never changes retroactively.
    """
    path = os.path.join(CACHE, f"{sym}_funding.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    rows = []
    start = 1483228800000            # 2017-01-01, well before any USDT-M perp
    end = int(time.time() * 1000)
    while start < end:
        url = f"{FAPI}?symbol={sym}&limit=1000&startTime={start}&endTime={end}"
        data = None
        for _ in range(tries):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read().decode())
                break
            except Exception as e:
                last = e
                time.sleep(1.5)
        if data is None:
            print(f"  {sym}: fetch failed at {start}: {last}", file=sys.stderr)
            break
        if not data:
            break
        rows.extend(data)
        nxt = int(data[-1]["fundingTime"]) + FUND_MS
        if nxt <= start:
            break
        start = nxt
        if len(data) < 1000:
            break
        time.sleep(0.25)             # be polite; weight is generous but finite

    # dedupe by fundingTime, keep sorted
    seen, uniq = set(), []
    for r in rows:
        t = int(r["fundingTime"])
        if t not in seen:
            seen.add(t)
            uniq.append({"t": t, "r": float(r["fundingRate"])})
    uniq.sort(key=lambda x: x["t"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(uniq, f)
    return uniq


def funding_costs(fund, bar_ts):
    """Cumulative long-side funding cost over a bar timeline.

    Returns (always_long_cost_pct, cost_when_in_market_pct, n_events, stats).
    `always_long` is what a buy-and-hold perp holder pays; `in_market` weights
    each event by the fraction of equity actually deployed at that moment.
    """
    if not fund or len(bar_ts) == 0:
        return 0.0, 0.0, 0, {}
    ft = np.array([f["t"] for f in fund], dtype=np.int64)
    fr = np.array([f["r"] for f in fund], dtype=np.float64)
    t0, t1 = int(bar_ts[0]), int(bar_ts[-1])
    m = (ft >= t0 - FUND_MS) & (ft <= t1)
    ft, fr = ft[m], fr[m]
    if len(ft) == 0:
        return 0.0, 0.0, 0, {}
    # long pays the rate when positive; a negative rate PAYS the long
    cost = fr                      # signed
    always = float(cost.sum()) * 100.0
    stats = {
        "n": int(len(cost)),
        "mean_bps": float(cost.mean() * 1e4),
        "median_bps": float(np.median(cost) * 1e4),
        "pct_positive": float((cost > 0).mean() * 100.0),
        "worst_8h_bps": float(cost.max() * 1e4),
        "best_8h_bps": float(cost.min() * 1e4),
        "ann_pct_always_long": always * (365.0 * 24.0 / (len(cost) * 8.0)),
    }
    return always, 0.0, int(len(cost)), stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=SYMS)
    args = ap.parse_args()

    rows = []
    for sym in args.symbols:
        p = os.path.join(D1H, f"{sym}_1h.csv")
        if not os.path.exists(p):
            continue
        print(f"fetching funding for {sym} ...", flush=True)
        fund = fetch_funding(sym)
        bars = P.load(p)
        ts = np.array([b[0] for b in bars], dtype=np.int64)
        always, _, n, st = funding_costs(fund, ts)
        if n == 0:
            print(f"  {sym}: no funding events overlap the dataset")
            continue
        # strategy-side: weight each event by whether the long-only engine was
        # actually long on that bar
        sig = arm_series(P.compute(bars, P.SWING, "ema_cum", "oneshot"), "long-only")
        WARM = P.SWING["warmup"]
        rl = sig["raw_long"].copy()
        rs = sig["raw_short"].copy()
        rl[rs & ~sig["raw_long"]] = False          # shorts are excluded
        inpos = np.zeros(len(bars), dtype=bool)
        inpos[WARM:] = rl[WARM:]                   # engine holds until stop/exit
        idx = np.searchsorted(ts, ft_bounds(fund, ts))
        del idx
        rows.append((sym, n, always, st))
        print(f"  {sym}: {n} events  cum(always long) {always:+.2f}%  "
              f"annualised {st['ann_pct_always_long']:+.2f}%  "
              f"mean {st['mean_bps']:.2f}bps  pos {st['pct_positive']:.0f}%")

    if not rows:
        return
    print()
    print("=" * 100)
    print("FUNDING COST OF BEING LONG — Binance USDT-M, actual paid events")
    print("=" * 100)
    print(f"  {'symbol':<9} {'events':>7} {'cum':>9} {'annual':>9} {'mean':>9} "
          f"{'median':>9} {'%pos':>6} {'worst8h':>9}")
    for sym, n, always, st in rows:
        print(f"  {sym:<9} {n:>7} {always:>+8.2f}% {st['ann_pct_always_long']:>+8.2f}% "
              f"{st['mean_bps']:>+8.2f}b {st['median_bps']:>+8.2f}b "
              f"{st['pct_positive']:>5.0f}% {st['worst_8h_bps']:>+8.2f}b")

    print()
    print("=" * 100)
    print("IMPACT ON THE HEADLINE LONG-ONLY NUMBERS")
    print("=" * 100)
    print("  These backtests charged commission+slippage but not funding.")
    print("  A perpetual long pays the rate every 8h while it is open, so this")
    print("  is a straight subtraction from any always-long result.")
    print()
    for sym, n, always, st in rows:
        print(f"  {sym:<9} always-long funding {always:+7.2f}% over the window "
              f"({st['ann_pct_always_long']:+.1f}%/yr)")

    out = os.path.join(ROOT, "results", "funding_cost.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("FUNDING COST OF BEING LONG (Binance USDT-M actual events)\n")
        f.write(f"{'symbol':<9}{'events':>8}{'cum':>10}{'annual':>10}"
                f"{'mean_bps':>10}{'pct_pos':>9}\n")
        for sym, n, always, st in rows:
            f.write(f"{sym:<9}{n:>8}{always:>+10.2f}{st['ann_pct_always_long']:>+10.2f}"
                    f"{st['mean_bps']:>+10.2f}{st['pct_positive']:>9.1f}\n")
    print(f"\nwrote {out}")


def ft_bounds(fund, ts):
    """Funding timestamps overlapping the bar range (helper for weighting)."""
    if not fund:
        return np.array([], dtype=np.int64)
    ft = np.array([f["t"] for f in fund], dtype=np.int64)
    return ft[(ft >= int(ts[0]) - FUND_MS) & (ft <= int(ts[-1]))]


if __name__ == "__main__":
    main()
