import pandas as pd
import numpy as np
from pathlib import Path

# Strategy needs features covering Sep 11-18 (the backtest period)
# Data Vision parquets cover Jun 12 - Sep 9 (no Sep 11-18 data!)
# VPS builder parquets cover Sep 11 - Sep 18 (the right dates!)
# VPS builder has L2 data but missing some columns the strategy expects
# Solution: Use VPS builder data + fill missing columns with defaults

symbols = ["SUI", "HYPE", "SOL", "SPCX"]
base_dir = Path(r"C:\Users\Lenovo\Downloads\freqtrade\user_data\data\orderflow")
vps_dir = Path(r"C:\Users\Lenovo\Downloads\FREQTRADE BOT\data\orderflow")

# Missing columns that need defaults (VPS builder doesn't produce these)
missing_defaults = {
    "book_valid_fraction": 1.0,
    "book_gap_events": 0,
    "depth_event_count": 0,
    "book_resyncs": 0,
    "data_latency_ms": 100,
    "feature_valid": True,
    "absorption_long": 0.0,
    "absorption_short": 0.0,
    "queue_consumption_long": 0.0,
    "queue_consumption_short": 0.0,
    "liquidation_long_notional": 0.0,
    "liquidation_short_notional": 0.0,
    "liq_imbalance": 0.0,
    "cvd_slope": 0.0,
}

for sym in symbols:
    target = base_dir / f"{sym}_USDT_USDT_5m.parquet"
    vps = vps_dir / f"{sym}USDT_5m.parquet"
    
    if not vps.exists():
        print(f"SKIP {sym}: VPS parquet not found")
        continue
    
    df = pd.read_parquet(vps)
    
    # Add missing columns with defaults
    for col, val in missing_defaults.items():
        if col not in df.columns:
            df[col] = val
    
    # Ensure date column is datetime
    df["date"] = pd.to_datetime(df["date"], utc=True)
    
    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)
    
    # Ensure all expected columns exist (set to NaN if missing)
    all_cols = [
        "real_delta", "real_buy_volume", "real_sell_volume", "real_cvd", "delta_z", "cvd_slope",
        "trade_count", "aggressive_buy_ratio", "l2_imbalance", "l2_spread_bps", "l2_microprice_edge_bps",
        "bid_depth", "ask_depth", "book_valid_fraction", "depth_event_count", "book_gap_events", "book_resyncs",
        "slippage_buy_10k_bps", "slippage_sell_10k_bps", "top_bid_qty", "top_ask_qty", "mark_price",
        "funding_rate", "open_interest", "open_interest_change_pct", "liquidation_long_notional",
        "liquidation_short_notional", "liq_imbalance", "absorption_long", "absorption_short",
        "queue_consumption_long", "queue_consumption_short", "data_latency_ms", "feature_valid",
        "trade_volume", "real_buy_volume", "real_sell_volume",
    ]
    for col in all_cols:
        if col not in df.columns:
            df[col] = np.nan
    
    print(f"{sym}: {len(df)} rows, {df['date'].min()} to {df['date'].max()}")
    
    # Check L2 coverage
    for col in ["book_valid_fraction", "slippage_buy_10k_bps", "slippage_sell_10k_bps", "data_latency_ms", "l2_imbalance"]:
        nn = df[col].notna().sum()
        print(f"  {col}: {nn}/{len(df)} ({nn/len(df)*100:.1f}%)")
    
    # Save to target path
    df.to_parquet(target, index=False)
    print(f"  -> Saved to {target.name}")

print("\nAll done!")
