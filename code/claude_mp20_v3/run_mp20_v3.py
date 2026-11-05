"""
run_mp20_v3.py — claude_mp20_v3
Runner for all 20 v3 strategies.

Usage (from repo root):
    python code/claude_mp20_v3/run_mp20_v3.py
    python code/claude_mp20_v3/run_mp20_v3.py --stress-cost
    python code/claude_mp20_v3/run_mp20_v3.py --data-dir data/mp20_real_6m --out-dir results/mp20_v3_6m

Outputs:
    results/mp20_v3_6m/summary_ranked_by_sharpe.csv
    results/mp20_v3_6m/summary_stressed_cost.csv   (if --stress-cost)
    results/mp20_v3_6m/<id>_equity_drawdown.png    (one per strategy)
"""
from __future__ import annotations

import argparse
import os
import sys

# Resolve paths relative to THIS script so it works regardless of cwd
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_V2_DIR = os.path.join(_THIS_DIR, "..", "claude_mp20_v2")
sys.path.insert(0, _V2_DIR)
sys.path.insert(0, _THIS_DIR)

import numpy as np
import pandas as pd

from engine_core import (
    align_universe,
    precompute_indicators,
    run_backtest,
    build_benchmark,
    compute_metrics,
    plot_equity_and_drawdown,
    UNIVERSE,
    TAKER_FEE,
    SLIPPAGE_BPS,
)
from strategies import build_strategies


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_real_universe(data_dir: str, pairs: list[str]) -> dict[str, pd.DataFrame]:
    """
    Load one CSV per pair from data_dir. Supports:
      - timestamp column: epoch ms (>1e12) or epoch s, or ISO datetime string.
      - Column aliases: 'open_ts' accepted as 'timestamp'.
    """
    data = {}
    for p in pairs:
        path = os.path.join(data_dir, f"{p}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Missing {path} — expected CSV named exactly '{p}.csv' in {data_dir}"
            )
        df = pd.read_csv(path)
        # Normalise column names (lowercase, strip whitespace)
        df.columns = [c.lower().strip() for c in df.columns]

        # Handle timestamp alias 'open_ts'
        if "timestamp" not in df.columns and "open_ts" in df.columns:
            df = df.rename(columns={"open_ts": "timestamp"})

        required = ["timestamp", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"{path} missing required columns: {missing}")

        ts = df["timestamp"]
        if np.issubdtype(ts.dtype, np.number):
            unit = "ms" if ts.iloc[0] > 10**12 else "s"
            idx = pd.to_datetime(ts, unit=unit, utc=True)
        else:
            idx = pd.to_datetime(ts, utc=True)

        df = df.set_index(idx)[["open", "high", "low", "close", "volume"]].sort_index()
        df = df[~df.index.duplicated(keep="first")]

        # Ensure numeric dtypes
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])

        data[p] = df
        print(f"  Loaded {p}: {len(df):,} bars  [{df.index[0]} → {df.index[-1]}]")
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run claude_mp20_v3 strategy suite on real 6-month crypto data."
    )
    ap.add_argument(
        "--data-dir",
        default=os.path.join("data", "mp20_real_6m"),
        help="Directory containing SOLUSDC.csv, BTCUSDC.csv, etc.",
    )
    ap.add_argument(
        "--out-dir",
        default=os.path.join("results", "mp20_v3_6m"),
        help="Output directory for charts and summary CSV.",
    )
    ap.add_argument(
        "--stress-cost",
        action="store_true",
        help="Run 2× taker fee + slippage stress test.",
    )
    ap.add_argument(
        "--pairs",
        nargs="*",
        default=UNIVERSE,
        help="Pairs to run (default: all 5 universe pairs).",
    )
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Resolve data-dir relative to cwd (allows running from repo root)
    data_dir = args.data_dir
    if not os.path.isabs(data_dir):
        data_dir = os.path.join(os.getcwd(), data_dir)

    print(f"\n{'='*60}")
    print("  claude_mp20_v3  —  20-Strategy Suite Runner")
    print(f"  Data dir : {data_dir}")
    print(f"  Out dir  : {args.out_dir}")
    print(f"  Pairs    : {args.pairs}")
    if args.stress_cost:
        print("  Mode     : 2× COST STRESS TEST")
    print(f"{'='*60}\n")

    # Load & align data
    print("Loading data …")
    raw = load_real_universe(data_dir, args.pairs)
    data = align_universe(raw)
    n_bars = len(next(iter(data.values())))
    print(f"\nAligned universe: {len(data)} pairs × {n_bars:,} bars\n")

    # Precompute indicators
    print("Precomputing indicators …")
    indicators = precompute_indicators(data)

    # Build benchmark
    benchmark = build_benchmark(data)
    btc_series = data.get("BTCUSDC", {})
    btc_close = btc_series["close"] if isinstance(btc_series, pd.DataFrame) and "close" in btc_series.columns else None

    # Load strategies
    strategies = build_strategies()
    n_trials = len(strategies)
    assert n_trials == 20, f"Expected 20 strategies, got {n_trials}"

    # Cost parameters
    if args.stress_cost:
        eff_fee = TAKER_FEE * 2.0
        eff_slip = SLIPPAGE_BPS * 2.0
        print(f"*** 2× COST STRESS: fee={eff_fee*10000:.1f}bps  slip={eff_slip*10000:.1f}bps ***\n")
    else:
        eff_fee = TAKER_FEE
        eff_slip = SLIPPAGE_BPS

    # Run each strategy
    rows = []
    print(f"{'ID':<14} {'Name':<38} {'Sharpe(rf0)':>11} {'OOS':>7} {'DSR':>6} {'MaxDD%':>8} {'Trades':>7} {'Verdict'}")
    print("-" * 100)

    for cfg in strategies:
        try:
            res = run_backtest(cfg, data, indicators, taker_fee=eff_fee, slippage_bps=eff_slip)
            m = compute_metrics(res, benchmark, btc_series=btc_close, n_trials=n_trials)
        except Exception as exc:
            print(f"{cfg.id:<14} ERROR: {exc}")
            # Insert a blank row so the CSV stays aligned
            m = {k: np.nan for k in [
                "cumulative_return_pct", "benchmark_return_pct",
                "sharpe_rf0", "sharpe_rf45", "sharpe_is", "sharpe_oos",
                "sortino", "calmar", "ulcer_index", "max_dd_pct",
                "win_rate_pct", "avg_win_loss", "total_trades", "profit_factor",
                "expectancy_r", "turnover_notional", "fees_paid", "slippage_paid",
                "funding_paid", "btc_beta", "btc_alpha_pct", "btc_r2",
                "dsr", "haircut_sharpe",
            ]}
            m["verdict"] = "ERROR"
            # Build a minimal equity curve for plotting
            from engine_core import BacktestResult
            idx = next(iter(data.values())).index
            res = BacktestResult(cfg.id, cfg.mode, pd.Series(np.ones(len(idx)) * 100_000, index=idx), [], 0, 0, 0, 0)

        m.update(id=cfg.id, name=cfg.name, archetype=cfg.archetype, mode=cfg.mode)
        rows.append(m)

        # Save per-strategy chart
        chart_path = os.path.join(args.out_dir, f"{cfg.id}_equity_drawdown.png")
        try:
            plot_equity_and_drawdown(
                res, benchmark,
                f"{cfg.id}: {cfg.name}  [Verdict: {m.get('verdict','?')}]",
                chart_path,
            )
        except Exception:
            pass  # chart failure should never abort the run

        print(
            f"{cfg.id:<14} {cfg.name:<38} "
            f"{m.get('sharpe_rf0', float('nan')):>11.3f} "
            f"{m.get('sharpe_oos', float('nan')):>7.3f} "
            f"{m.get('dsr', float('nan')):>6.3f} "
            f"{m.get('max_dd_pct', float('nan')):>8.2f} "
            f"{int(m.get('total_trades', 0) or 0):>7d} "
            f"[{m.get('verdict','?')}]"
        )

    # Build summary DataFrame
    summary = pd.DataFrame(rows).sort_values("sharpe_oos", ascending=False)

    desired_cols = [
        "id", "name", "archetype", "mode", "verdict",
        "sharpe_oos", "sharpe_is", "sharpe_rf0", "sharpe_rf45",
        "dsr", "haircut_sharpe",
        "cumulative_return_pct", "benchmark_return_pct",
        "max_dd_pct", "calmar", "ulcer_index", "sortino",
        "win_rate_pct", "avg_win_loss", "total_trades",
        "profit_factor", "expectancy_r",
        "turnover_notional", "fees_paid", "slippage_paid", "funding_paid",
        "btc_alpha_pct", "btc_beta", "btc_r2",
    ]
    # Only keep columns that exist
    cols = [c for c in desired_cols if c in summary.columns]
    summary = summary[cols]

    fname = "summary_stressed_cost.csv" if args.stress_cost else "summary_ranked_by_sharpe.csv"
    out_csv = os.path.join(args.out_dir, fname)
    summary.to_csv(out_csv, index=False)

    print(f"\n{'='*60}")
    print(f"  Results written to : {out_csv}")
    print(f"  Charts written to  : {args.out_dir}/")
    print(f"{'='*60}")

    # Also run stress test automatically if this was the base run
    if not args.stress_cost:
        print("\nRunning 2× cost stress test …")
        rows_stress = []
        for cfg in strategies:
            try:
                res_s = run_backtest(cfg, data, indicators,
                                     taker_fee=TAKER_FEE * 2,
                                     slippage_bps=SLIPPAGE_BPS * 2)
                m_s = compute_metrics(res_s, benchmark, btc_series=btc_close, n_trials=n_trials)
            except Exception as exc:
                m_s = {"verdict": "ERROR", "sharpe_rf0": np.nan, "sharpe_oos": np.nan}
            m_s.update(id=cfg.id, name=cfg.name, archetype=cfg.archetype, mode=cfg.mode)
            rows_stress.append(m_s)

        summary_stress = pd.DataFrame(rows_stress).sort_values("sharpe_oos", ascending=False)
        cols_s = [c for c in desired_cols if c in summary_stress.columns]
        summary_stress = summary_stress[cols_s]
        stress_csv = os.path.join(args.out_dir, "summary_stressed_cost.csv")
        summary_stress.to_csv(stress_csv, index=False)
        print(f"  Stress results written to : {stress_csv}")


if __name__ == "__main__":
    main()
