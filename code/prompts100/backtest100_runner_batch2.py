#!/usr/bin/env python3
"""
100-Prompt Backtest Pack — Runner Batch 2 (5m only)
"""
from __future__ import annotations
import os, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\Lenovo\Downloads")
from backtest100_engine import Engine, run_is_oos, load_klines
from backtest100_strategies import STRATEGIES, build_ctx

DATA_DIR = r"C:\Users\Lenovo\Documents\backtest-system\data"
OUT_DIR = r"C:\Users\Lenovo\Downloads\backtest100_results"
os.makedirs(OUT_DIR, exist_ok=True)

TF_DIR = {"5m": "binance_klines_5m"}

STRATEGY_MAP_5M = {
    "3":  ("ETHUSDT",  "5m"), "9":  ("SOLUSDT",  "5m"), "13": ("BTCUSDT",  "5m"),
    "16": ("HYPEUSDT", "5m"), "17": ("SUIUSDT",  "5m"), "18": ("JUPUSDT",  "5m"),
    "20": ("ETHUSDT",  "5m"), "32": ("ETHUSDT",  "5m"), "36": ("SUIUSDT",  "5m"),
    "38": ("BTCUSDT",  "5m"), "40": ("SOLUSDT",  "5m"), "41": ("HYPEUSDT", "5m"),
    "43": ("JUPUSDT",  "5m"), "47": ("BTCUSDT",  "5m"), "51": ("ETHUSDT",  "5m"),
    "53": ("SOLUSDT",  "5m"), "54": ("HYPEUSDT", "5m"), "61": ("SUIUSDT",  "5m"),
    "62": ("JUPUSDT",  "5m"), "76": ("SUIUSDT",  "5m"), "78": ("BTCUSDT",  "5m"),
    "79": ("ETHUSDT",  "5m"), "80": ("SOLUSDT",  "5m"),
}

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
    
    for num_str in sorted(STRATEGY_MAP_5M.keys(), key=int):
        signal_fn = STRATEGIES.get(num_str)
        if signal_fn is None:
            skipped.append((num_str, "no implementation"))
            continue
        
        symbol, tf = STRATEGY_MAP_5M[num_str]
        path = os.path.join(DATA_DIR, TF_DIR[tf], symbol + "_" + tf + ".csv")
        if not os.path.exists(path):
            skipped.append((num_str, "missing data"))
            continue
        
        print("Strategy %s: %s %s..." % (num_str, symbol, tf), end=" ", flush=True)
        try:
            r = run_strategy(num_str, symbol, tf, signal_fn)
            results.append(r)
            print("OK (IS: %.2f%%, OOS: %.2f%%, PF: %s, trades: %d)" % (
                r["is_return_pct"], r["oos_return_pct"],
                r["oos_pf"] if r["oos_pf"] is not None else "N/A",
                r["oos_n_trades"]), flush=True)
        except Exception as e:
            print("ERROR: %s" % str(e)[:150], flush=True)
            skipped.append((num_str, "error: %s" % str(e)[:150]))
    
    df_results = pd.DataFrame(results)
    csv_path = os.path.join(OUT_DIR, "results_batch2_5m.csv")
    df_results.to_csv(csv_path, index=False)
    
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("BATCH 2 COMPLETE: %d strategies in %.1fs" % (len(results), elapsed))
    print("=" * 70)
    
    if len(df_results) > 0:
        print("\nAll results:")
        cols = ["strategy", "symbol", "tf", "oos_return_pct", "oos_pf", "oos_n_trades", "oos_sharpe"]
        print(df_results[cols].to_string(index=False))
    
    print("\nResults: %s" % csv_path)

if __name__ == "__main__":
    main()
