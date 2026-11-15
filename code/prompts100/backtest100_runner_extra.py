#!/usr/bin/env python3
"""Supplemental runner: strategies missing from batch1/batch2 maps (10, 52)."""
from __future__ import annotations
import os, sys, time
import pandas as pd

sys.path.insert(0, r"C:\Users\Lenovo\Downloads")
from backtest100_engine import run_is_oos, load_klines
from backtest100_strategies import STRATEGIES, build_ctx

OUT_DIR = r"C:\Users\Lenovo\Downloads\backtest100_results"
EXTRA = {"10": ("HYPEUSDT", "15m"), "52": ("BTCUSDT", "15m")}


def run_strategy(num, symbol, tf, signal_fn):
    df = load_klines(symbol, tf)
    ctx = build_ctx(df)

    def wrapped(j, _):
        return signal_fn(j, ctx)

    is_m, oos_m = run_is_oos(df, wrapped, oos_frac=0.3)
    return {
        "strategy": int(num), "symbol": symbol, "tf": tf,
        "is_return_pct": is_m["total_return_pct"], "is_max_dd_pct": is_m["max_dd_pct"],
        "is_pf": is_m["profit_factor"], "is_n_trades": is_m["n_trades"],
        "is_win_rate": is_m["win_rate"], "is_sharpe": is_m["sharpe"],
        "oos_return_pct": oos_m["total_return_pct"], "oos_max_dd_pct": oos_m["max_dd_pct"],
        "oos_pf": oos_m["profit_factor"], "oos_n_trades": oos_m["n_trades"],
        "oos_win_rate": oos_m["win_rate"], "oos_sharpe": oos_m["sharpe"],
        "bh_return_pct": is_m["bh_return_pct"],
    }


def main():
    rows = []
    for num, (sym, tf) in EXTRA.items():
        print("Strategy %s: %s %s..." % (num, sym, tf), end=" ", flush=True)
        t0 = time.time()
        r = run_strategy(num, sym, tf, STRATEGIES[num])
        rows.append(r)
        print("OK (IS %.2f%%, OOS %.2f%%, PF %s, trades %d) %.1fs" % (
            r["is_return_pct"], r["oos_return_pct"],
            r["oos_pf"] if r["oos_pf"] is not None else "N/A",
            r["oos_n_trades"], time.time() - t0), flush=True)
    df = pd.DataFrame(rows)
    out = os.path.join(OUT_DIR, "results_extra_10_52.csv")
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print("Saved", out)


if __name__ == "__main__":
    main()
