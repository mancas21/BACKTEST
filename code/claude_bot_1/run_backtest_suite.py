"""
run_backtest_suite.py
Single entry point: runs all 20 MP-STRAT strategies over a data universe and produces
a ranked summary table + one equity/drawdown chart per strategy.

REAL DATA MODE (default):
    Put one CSV per pair in --data-dir, named exactly as the pair id, e.g.:
        data/SOLUSDC.csv, data/BTCUSDC.csv, data/ETHUSDC.csv, data/AVAXUSDC.csv, data/LINKUSDC.csv
    Required columns: timestamp, open, high, low, close, volume
        - timestamp: UTC, ISO8601 or epoch ms/s, 1h candles, ascending, minimal gaps
    Then:
        python run_backtest_suite.py --data-dir ./data --out-dir ./results

SYNTHETIC SMOKE-TEST MODE (engine validation only -- NOT real performance):
        python run_backtest_suite.py --synthetic --out-dir ./results
"""
from __future__ import annotations
import argparse
import os
import numpy as np
import pandas as pd
from engine_core import (
    align_universe, precompute_indicators, run_backtest, build_benchmark,
    compute_metrics, plot_equity_and_drawdown, UNIVERSE
)
from strategies import build_strategies


def load_real_universe(data_dir: str, pairs: list[str]) -> dict[str, pd.DataFrame]:
    data = {}
    for p in pairs:
        path = os.path.join(data_dir, f"{p}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {path} -- expected one CSV per pair named exactly '<PAIR>.csv'")
        df = pd.read_csv(path)
        cols = {c.lower().strip(): c for c in df.columns}
        required = ["timestamp", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in cols]
        if missing:
            raise ValueError(f"{path} missing required columns: {missing}")
        df = df.rename(columns={cols[c]: c for c in required})
        ts = df["timestamp"]
        if np.issubdtype(ts.dtype, np.number):
            unit = "ms" if ts.iloc[0] > 10 ** 12 else "s"
            idx = pd.to_datetime(ts, unit=unit, utc=True)
        else:
            idx = pd.to_datetime(ts, utc=True)
        df = df.set_index(idx)[["open", "high", "low", "close", "volume"]].sort_index()
        df = df[~df.index.duplicated(keep="first")]
        data[p] = df
    return data


def make_synthetic_universe(pairs, n_bars=24 * 30 * 6):
    """ENGINE VALIDATION ONLY. Not calibrated to real market dynamics -- do not read results
    from this mode as evidence of strategy edge."""
    rng = np.random.default_rng(42)
    start_price = {"SOLUSDC": 150.0, "BTCUSDC": 60000.0, "ETHUSDC": 3000.0, "AVAXUSDC": 30.0, "LINKUSDC": 15.0}
    idx = pd.date_range("2026-03-28", periods=n_bars, freq="h", tz="UTC")
    market_factor = rng.normal(0, 0.006, n_bars)
    data = {}
    for p in pairs:
        beta = rng.uniform(0.6, 1.3)
        idio = rng.normal(0, 0.006, n_bars)
        regime = np.sin(np.linspace(0, rng.uniform(2, 6) * np.pi, n_bars)) * 0.0008
        logret = beta * market_factor + idio + regime
        close = start_price.get(p, 100.0) * np.exp(np.cumsum(logret))
        high = close * (1 + np.abs(rng.normal(0, 0.0025, n_bars)))
        low = close * (1 - np.abs(rng.normal(0, 0.0025, n_bars)))
        open_ = np.roll(close, 1)
        open_[0] = close[0]
        vol = rng.uniform(1e5, 1e6, n_bars)
        data[p] = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="./data")
    ap.add_argument("--out-dir", default="./results")
    ap.add_argument("--synthetic", action="store_true", help="engine validation only -- NOT real performance")
    ap.add_argument("--pairs", nargs="*", default=UNIVERSE)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if args.synthetic:
        print("*** SYNTHETIC MODE: results are for engine validation only, NOT real performance. ***")
        raw = make_synthetic_universe(args.pairs)
    else:
        raw = load_real_universe(args.data_dir, args.pairs)

    data = align_universe(raw)
    n_aligned = len(next(iter(data.values())))
    if n_aligned < 24 * 60:
        print(f"WARNING: only {n_aligned} aligned bars across all pairs -- "
              f"check for missing data / mismatched timestamps across your CSVs.")

    indicators = precompute_indicators(data)
    benchmark = build_benchmark(data)

    rows = []
    for cfg in build_strategies():
        res = run_backtest(cfg, data, indicators)
        m = compute_metrics(res, benchmark)
        m.update(id=cfg.id, name=cfg.name, archetype=cfg.archetype, mode=cfg.mode)
        rows.append(m)
        plot_equity_and_drawdown(
            res, benchmark, f"{cfg.id}: {cfg.name}",
            os.path.join(args.out_dir, f"{cfg.id}_equity_drawdown.png")
        )
        print(f"{cfg.id:14s} sharpe={m['sharpe']:.2f}  maxdd={m['max_dd_pct']:.1f}%  trades/periods={m['total_trades']}")

    summary = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    cols = ["id", "name", "archetype", "mode", "cumulative_return_pct", "benchmark_return_pct",
            "sharpe", "sortino", "max_dd_pct", "win_rate_pct", "total_trades", "profit_factor", "expectancy_r"]
    summary = summary[cols]
    out_csv = os.path.join(args.out_dir, "summary_ranked_by_sharpe.csv")
    summary.to_csv(out_csv, index=False)
    print(f"\nWrote {out_csv} and one chart per strategy to {args.out_dir}/")


if __name__ == "__main__":
    main()
