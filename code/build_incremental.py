#!/usr/bin/env python3
"""Incremental feature builder: build only missing days + today, merge with
existing parquet, recompute trailing indicators over the full frame.

Usage: build_incremental.py --symbol SUIUSDT [--raw-root ...] [--out-dir ...]
Reads existing <out-dir>/<SYMBOL>_5m.parquet (if any), builds day-files with
date >= (max_existing_date - 1 day) to refresh the seam + today partial,
drops overlap, recomputes real_cvd/delta_z/cvd_slope/oi_change over full frame.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_daily import build_day, rolling_z

RAW_COLS = [
    "date", "real_buy_volume", "real_sell_volume", "real_delta",
    "trade_count", "trade_volume", "aggressive_buy_ratio",
    "l2_spread_bps", "l2_imbalance", "l2_microprice_edge_bps",
    "bid_depth", "ask_depth", "slippage_buy_10k_bps", "slippage_sell_10k_bps",
    "top_bid_qty", "top_ask_qty", "mark_price", "funding_rate", "open_interest",
    "book_valid_fraction", "depth_event_count",
]


def recompute_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)
    df["real_cvd"] = df["real_delta"].cumsum()
    df["delta_z"] = rolling_z(
        df["real_delta"].replace([np.inf, -np.inf], np.nan), 96, 24
    )
    df["cvd_slope"] = df["real_cvd"].diff(3) / 3.0
    df["open_interest_change_pct"] = df["open_interest"].pct_change() * 100.0
    df["feature_valid"] = df["trade_count"] > 0
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--levels", type=int, default=5)
    ap.add_argument("--raw-root", default="/home/ubuntu/of-collector/data/orderflow_raw")
    ap.add_argument("--out-dir", default="/home/ubuntu/of-collector/data/features")
    args = ap.parse_args()

    root = Path(args.raw_root)
    symbol = args.symbol.upper()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{symbol}_5m.parquet"

    d = root / symbol
    day_files = sorted(f.name for f in d.glob("*.trades.jsonl"))
    days = [f.replace(".trades.jsonl", "") for f in day_files if f.startswith("2026-")]
    if not days:
        print(f"[{symbol}] NO DAY FILES", flush=True)
        return

    old = None
    if out_path.exists():
        old = pd.read_parquet(out_path)
        old["date"] = pd.to_datetime(old["date"], utc=True)
        max_dt = old["date"].max()
        cutoff = (max_dt - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        todo = [x for x in days if x >= cutoff]
        print(f"[{symbol}] existing {len(old)} rows to {max_dt}, rebuild {len(todo)} days from {cutoff}", flush=True)
    else:
        todo = days
        print(f"[{symbol}] no parquet, building all {len(todo)} days", flush=True)

    frames = []
    for day in todo:
        print(f"[{symbol}] processing {day}...", flush=True)
        df = build_day(root, symbol, day, args.levels)
        if df is not None and len(df) > 0:
            frames.append(df[RAW_COLS])
            print(f"[{symbol}] {day}: {len(df)} rows", flush=True)

    if old is None and not frames:
        print(f"[{symbol}] NO DATA", flush=True)
        return

    if old is not None:
        # Gracefully handle older parquets missing the new completeness cols
        for c in ["book_valid_fraction", "depth_event_count",
                  "book_gap_events", "book_resyncs", "data_latency_ms",
                  "liquidation_long_notional", "liquidation_short_notional",
                  "liq_imbalance", "absorption_long", "absorption_short",
                  "queue_consumption_long", "queue_consumption_short"]:
            if c not in old.columns:
                old[c] = np.nan
        base = old[RAW_COLS].copy()
        full = pd.concat([base] + frames, ignore_index=True) if frames else base
    else:
        full = pd.concat(frames, ignore_index=True)

    full["date"] = pd.to_datetime(full["date"], utc=True)
    full = full.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    full = recompute_derived(full)
    full.to_parquet(out_path, index=False)
    print(f"[{symbol}] wrote {len(full)} rows -> {out_path} "
          f"({full['date'].min()} .. {full['date'].max()})", flush=True)


if __name__ == "__main__":
    main()
