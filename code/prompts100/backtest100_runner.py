#!/usr/bin/env python3
"""
100-Prompt Backtest Pack — Runner (Optimized)
=============================================
Caches data + indicators per (symbol, tf) pair.
"""

from __future__ import annotations
import os, sys, json, math, time
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\Lenovo\Downloads")
from backtest100_engine import Engine, run_is_oos, load_klines
from backtest100_strategies import STRATEGIES, build_ctx

DATA_DIR = r"C:\Users\Lenovo\Documents\backtest-system\data"
OUT_DIR = r"C:\Users\Lenovo\Downloads\backtest100_results"
os.makedirs(OUT_DIR, exist_ok=True)

TF_DIR = {"1h": "binance_klines_1h", "15m": "binance_klines_15m", "5m": "binance_klines_5m"}

# Strategy -> (symbol, tf) mapping
STRATEGY_MAP = {
    "1":  ("SOLUSDT",  "1h"), "2":  ("BTCUSDT",  "15m"), "3":  ("ETHUSDT",  "5m"),
    "4":  ("HYPEUSDT", "1h"), "5":  ("SUIUSDT",  "15m"), "6":  ("JUPUSDT",  "1h"),
    "7":  ("BTCUSDT",  "1h"), "8":  ("ETHUSDT",  "15m"), "9":  ("SOLUSDT",  "5m"),
    "10": ("HYPEUSDT", "15m"), "11": ("SUIUSDT",  "1h"), "12": ("JUPUSDT",  "15m"),
    "13": ("BTCUSDT",  "5m"), "14": ("ETHUSDT",  "1h"), "15": ("SOLUSDT",  "15m"),
    "16": ("HYPEUSDT", "5m"), "17": ("SUIUSDT",  "5m"), "18": ("JUPUSDT",  "5m"),
    "19": ("BTCUSDT",  "15m"), "20": ("ETHUSDT",  "5m"), "21": ("SOLUSDT",  "1h"),
    "22": ("HYPEUSDT", "1h"), "23": ("SUIUSDT",  "15m"), "24": ("JUPUSDT",  "1h"),
    "25": ("BTCUSDT",  "1h"), "26": ("ETHUSDT",  "1h"), "27": ("SOLUSDT",  "15m"),
    "28": ("BTCUSDT",  "1h"), "29": ("HYPEUSDT", "15m"), "30": ("SUIUSDT",  "1h"),
    "31": ("JUPUSDT",  "15m"), "32": ("ETHUSDT",  "5m"), "33": ("BTCUSDT",  "15m"),
    "34": ("SOLUSDT",  "1h"), "35": ("HYPEUSDT", "1h"), "36": ("SUIUSDT",  "5m"),
    "37": ("JUPUSDT",  "1h"), "38": ("BTCUSDT",  "5m"), "39": ("ETHUSDT",  "15m"),
    "40": ("SOLUSDT",  "5m"), "41": ("HYPEUSDT", "5m"), "42": ("SUIUSDT",  "15m"),
    "43": ("JUPUSDT",  "5m"), "44": ("BTCUSDT",  "1h"), "45": ("ETHUSDT",  "1h"),
    "46": ("SOLUSDT",  "15m"), "47": ("BTCUSDT",  "5m"), "48": ("HYPEUSDT", "15m"),
    "49": ("SUIUSDT",  "1h"), "50": ("JUPUSDT",  "15m"), "51": ("ETHUSDT",  "5m"),
    "52": ("BTCUSDT",  "15m"), "53": ("SOLUSDT",  "5m"), "54": ("HYPEUSDT", "5m"),
    "55": ("SUIUSDT",  "15m"), "56": ("JUPUSDT",  "1h"), "57": ("ETHUSDT",  "15m"),
    "58": ("BTCUSDT",  "1h"), "59": ("SOLUSDT",  "1h"), "60": ("HYPEUSDT", "1h"),
    "61": ("SUIUSDT",  "5m"), "62": ("JUPUSDT",  "5m"), "63": ("BTCUSDT",  "15m"),
    "64": ("ETHUSDT",  "1h"), "65": ("SOLUSDT",  "15m"), "66": ("BTCUSDT",  "15m"),
    "67": ("ETHUSDT",  "15m"), "68": ("SOLUSDT",  "1h"), "69": ("HYPEUSDT", "15m"),
    "70": ("SUIUSDT",  "15m"), "71": ("JUPUSDT",  "1h"), "72": ("BTCUSDT",  "1h"),
    "73": ("ETHUSDT",  "1h"), "74": ("SOLUSDT",  "15m"), "75": ("HYPEUSDT", "1h"),
    "76": ("SUIUSDT",  "5m"), "77": ("JUPUSDT",  "15m"), "78": ("BTCUSDT",  "5m"),
    "79": ("ETHUSDT",  "5m"), "80": ("SOLUSDT",  "5m"),
}

# Cache: (symbol, tf) -> (df, ctx)
_cache = {}

def get_cached(symbol, tf):
    key = (symbol, tf)
    if key not in _cache:
        path = os.path.join(DATA_DIR, TF_DIR[tf], symbol + "_" + tf + ".csv")
        df = load_klines(symbol, tf)
        ctx = build_ctx(df)
        _cache[key] = (df, ctx)
    return _cache[key]

def run_strategy(num, symbol, tf, signal_fn):
    df, ctx = get_cached(symbol, tf)
    
    def wrapped_signal(j, engine_ctx):
        return signal_fn(j, ctx)
    
    is_metrics, oos_metrics = run_is_oos(df, wrapped_signal, oos_frac=0.3)
    
    return {
        "strategy": int(num),
        "symbol": symbol,
        "tf": tf,
        "is_return_pct": is_metrics["total_return_pct"],
        "is_max_dd_pct": is_metrics["max_dd_pct"],
        "is_pf": is_metrics["profit_factor"],
        "is_n_trades": is_metrics["n_trades"],
        "is_win_rate": is_metrics["win_rate"],
        "is_sharpe": is_metrics["sharpe"],
        "oos_return_pct": oos_metrics["total_return_pct"],
        "oos_max_dd_pct": oos_metrics["max_dd_pct"],
        "oos_pf": oos_metrics["profit_factor"],
        "oos_n_trades": oos_metrics["n_trades"],
        "oos_win_rate": oos_metrics["win_rate"],
        "oos_sharpe": oos_metrics["sharpe"],
        "bh_return_pct": is_metrics["bh_return_pct"],
    }

def main():
    results = []
    skipped = []
    t0 = time.time()
    
    for num_str in sorted(STRATEGY_MAP.keys(), key=int):
        signal_fn = STRATEGIES.get(num_str)
        if signal_fn is None:
            skipped.append((num_str, "no implementation"))
            continue
        
        symbol, tf = STRATEGY_MAP[num_str]
        path = os.path.join(DATA_DIR, TF_DIR[tf], symbol + "_" + tf + ".csv")
        if not os.path.exists(path):
            skipped.append((num_str, "missing data: %s %s" % (symbol, tf)))
            continue
        
        print("Strategy %s: %s %s..." % (num_str, symbol, tf), end=" ", flush=True)
        try:
            r = run_strategy(num_str, symbol, tf, signal_fn)
            results.append(r)
            print("OK (IS: %.2f%%, OOS: %.2f%%, PF: %s)" % (
                r["is_return_pct"], r["oos_return_pct"],
                r["oos_pf"] if r["oos_pf"] is not None else "N/A"), flush=True)
        except Exception as e:
            print("ERROR: %s" % str(e)[:100], flush=True)
            skipped.append((num_str, "error: %s" % str(e)[:100]))
    
    # Save results
    df_results = pd.DataFrame(results)
    csv_path = os.path.join(OUT_DIR, "results_100_prompt.csv")
    df_results.to_csv(csv_path, index=False)
    
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("COMPLETED: %d strategies in %.1fs, %d skipped" % (len(results), elapsed, len(skipped)))
    print("=" * 70)
    
    if len(df_results) > 0:
        print("\nTop 10 by OOS return:")
        cols = ["strategy", "symbol", "tf", "oos_return_pct", "oos_pf", "oos_n_trades", "oos_sharpe"]
        print(df_results.nlargest(10, "oos_return_pct")[cols].to_string(index=False))
        
        print("\nTop 10 by OOS profit factor (min 10 trades):")
        pf_df = df_results[df_results["oos_n_trades"] >= 10]
        print(pf_df.nlargest(10, "oos_pf")[cols].to_string(index=False))
    
    if skipped:
        print("\nSkipped (%d):" % len(skipped))
        for s in skipped[:20]:
            print("  %s: %s" % s)
        if len(skipped) > 20:
            print("  ... and %d more" % (len(skipped) - 20))
    
    print("\nResults: %s" % csv_path)

if __name__ == "__main__":
    main()
