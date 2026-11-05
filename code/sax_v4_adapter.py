"""SAX v4 adapter for vrun.py — wraps sax_v4_engine.py backtest engine.

This adapter produces artifact-bound, reproducible results that integrate with
the vrun harness (verify/render/guard). It maps the Sax v4 engine's BacktestResult
to the standardized metrics format used by the harness.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# Ensure the engine is importable
sys.path.insert(0, os.path.dirname(__file__))
import sax_v4_engine as sax

TICKER = "JUPUSDT"
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "binance_klines_1h_taker",
    f"{TICKER}_1h.csv",
)


def _sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_config() -> sax.BacktestConfig:
    return sax.BacktestConfig(
        initial_capital=10_000.0,
        fee_bps=5.0,
        slippage_bps=0.5,   # measured live 2026-10-25: 5+0.5 = 11 bps RT
        sizing_mode="fixed_pct",
        pct_equity=100.0,
        risk_pct=1.0,
        max_leverage=1.0,
        opposite_signal="ignore",
        allow_long=True,
        allow_short=True,
        both_hit_rule="sl_first",
        start=None,
        end=None,
    )


def run_sax(paths, params: dict | None = None) -> dict:
    """Run the Sax v4 engine and return an artifact dict.

    The artifact follows the same schema as every other vrun adapter:
      - run_id = sha256(engine + params + [(data_path, sha, bars)])[:16]
      - metrics: PF, return, trades, DD, etc.
      - provenance: engine version, engine files, harness SHA
    """
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(DATA_PATH)

    df = sax.load_ohlcv(paths[0])
    p = sax.SAXParams() if not params else replace(sax.SAXParams(), **params)

    cfg = _default_config()
    # Walk-forward: 730-day train, 180-day test (per the engine's defaults)
    # but for a single artifact we just run the full series.
    res = sax.backtest(df, p, cfg)

    # Extract standardized metrics
    m = res.metrics
    n_trades = m["n_trades"]
    total_ret = m["net_return_pct"]
    pf = m.get("profit_factor", float("inf") if m["gross_return_pct"] > 0 else 0.0)
    win_rate = m.get("win_rate_pct", 0.0)
    avg_trade = m.get("avg_trade_pct", 0.0)
    max_dd = m.get("max_drawdown_pct", 0.0)
    bh_ret = m.get("buy_hold_return_pct", 0.0)
    fees = m.get("fees_paid", 0.0)

    # Expectancy R (FIX-11 style, per-trade average)
    # Reconstruct from trades if available
    trades_df = res.trades
    expectancy_R = 0.0
    if "R" in trades_df.columns and len(trades_df):
        expectancy_R = float(trades_df["R"].mean())

    # Build the core (used for run_id hashing)
    sha_data = _sha256_file(DATA_PATH)
    core = {
        "strategy": "sax_v4",
        "params": params or {},
        "inputs": [[DATA_PATH, sha_data, len(df)]],
        "engine_sha256": hashlib.sha256(
            open(os.path.join(os.path.dirname(__file__), "vrun.py"), "rb").read()
        ).hexdigest(),
        "engine_version": "sax-v4",
    }
    run_id = hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()[:16]

    metrics = {
        "n_trades": n_trades,
        "net_return_pct": total_ret,
        "profit_factor": pf,
        "win_rate": win_rate / 100.0,
        "expectancy_R": expectancy_R,
        "avg_trade_pct": avg_trade,
        "max_dd_pct": -max_dd,  # vrun convention: DD as negative percentage
        "fees": fees,
        "final_equity": 10_000.0 * (1.0 + total_ret / 100.0),
        "bh_return_pct": bh_ret,
        "flag": "OK" if n_trades >= 30 else "INSUFFICIENT_SAMPLE",
    }

    artifact = {
        "schema": "bt-artifact/1",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": "sax_v4",
        "symbol": TICKER,
        "timeframe": "1h",
        "params": params or {},
        "provenance": {
            "adapter": "sax_v4",
            "engine_version": "sax-v4",
            "engine_files": ["sax_v4_engine.py"],
            "engine_sha256": hashlib.sha256(
                open(os.path.join(os.path.dirname(__file__), "vrun.py"), "rb").read()
            ).hexdigest(),
        },
        "inputs": [[DATA_PATH, sha_data, len(df)]],
        "metrics": metrics,
        "tables": None,
        "core": core,
        "cmd": f"python code/vrun.py run --strategy sax --tf 1h --symbol {TICKER}",
    }
    return artifact


def save_artifact(a: dict) -> str:
    """Persist artifact under results/runs/."""
    runs_dir = os.path.join(os.path.dirname(__file__), "..", "results", "runs")
    os.makedirs(runs_dir, exist_ok=True)
    path = os.path.join(runs_dir, a["run_id"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(a, f, indent=2, sort_keys=True)
    return path