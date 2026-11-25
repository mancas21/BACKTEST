"""
trendmagic_engine.py - Trend Magic adapter for vrun.py.

Wraps code/tm_core.py + code/tm_backtest.py (+ code/tm_data.py), copied
byte-identical from Downloads/ because Downloads/ is not durable
(AGENTS.md rule #2: the SAX v3 engine was deleted from Downloads and took
49 artifacts' verifiability with it).

Signal: tm_core.trend_magic(df, TMParams, mode="fixed") -> DataFrame with "sig".
Execution: tm_backtest.run_backtest(df, sig, BTConfig) -> BTResult (next-open
fill, stop-and-reverse, position in {-1,0,+1} x leverage, costs per side).
Metrics: tm_backtest.perf(ret, ppy, pos, trades).

Conventions (declared, printed in every artifact's provenance):
  * mode="fixed" -- the audited engine. mode="legacy" reproduces the original
    Pine v5's zero-seed bug (AUDIT.md findings 1 & 2) and is NOT used here.
  * Fill at the open of bar t+delay (delay >= 1 enforced): a flip is known at
    the close of bar t, so the earliest fill is the next bar's open.
  * Stop-and-reverse; position in {-1, 0, +1} x leverage, rebalanced each bar.
  * Costs: (fee_bps + slip_bps) per side on traded notional. Defaults
    5.0 + 0.5 = 11 bps RT (repo regime, measured 2026-10-25 on live books).
  * Leverage 1.0, side "both", delay 1 by default.
  * No funding charged -- the indicator is kline-only and carries no funding
    input (declared limit; funding can be added via run_backtest(funding=...)).
  * Accounting invariant eq[-1] - INIT == sum(pnl) is asserted inside
    run_backtest and exercised by test_tm.py (test_trade_log_returns_sum_to_equity_log_exactly).

Params (all optional; defaults match TMParams / BTConfig):
  fee_bps, slip_bps, leverage, side, delay,
  cci_len, atr_len, atr_mult, src, atr_type, flip_on, smooth, ma_len, ma_type

One artifact = one (symbol, timeframe, params) cell.
"""
from __future__ import annotations

import os
import sys

import importlib
import pandas as pd


def _load_binance_csv(path: str) -> pd.DataFrame:
    """Read a Binance kline CSV (open_ts, open, high, low, close, volume) into
    a DatetimeIndexed OHLCV frame. open_ts is epoch ms.

    tm_data.load_ohlcv only recognises (timestamp, open_time, time, date,
    datetime) as time columns, not open_ts, so we normalise here rather than
    editing the byte-identical tm_data.py port.
    """
    df = pd.read_csv(path)
    df.columns = [str(c).lower() for c in df.columns]
    if "open_ts" in df.columns:
        df = df.rename(columns={"open_ts": "open_time"})
    tcol = "open_time" if "open_time" in df.columns else None
    if tcol is None:
        raise ValueError(f"no time column in {df.columns.tolist()}")
    ts = df[tcol]
    if pd.api.types.is_numeric_dtype(ts):
        ts = pd.to_datetime(ts, unit="ms" if float(ts.iloc[0]) > 1e11 else "s", utc=True)
    else:
        ts = pd.to_datetime(ts, utc=True)
    df = df.set_index(pd.DatetimeIndex(ts, name="time")).drop(columns=[tcol]).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if "volume" not in df:
        df["volume"] = 1.0
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def run_symbol(paths: list, params: dict):
    """Run Trend Magic on a single kline CSV.

    Returns (metrics, prov, tables) in the vrun.py adapter protocol.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    tm_core = importlib.import_module("tm_core")
    tm_backtest = importlib.import_module("tm_backtest")
    tm_data = importlib.import_module("tm_data")

    p = dict(params)
    p.pop("tf", None)   # injected by make_artifact for internal timing; not an engine param

    tm_params = tm_core.TMParams(
        cci_len=int(p.pop("cci_len", 20)),
        atr_len=int(p.pop("atr_len", 5)),
        atr_mult=float(p.pop("atr_mult", 2.0)),
        src=str(p.pop("src", "close")),
        atr_type=str(p.pop("atr_type", "SMA(TR)")),
        flip_on=str(p.pop("flip_on", "wick")),
        smooth=bool(p.pop("smooth", False)),
        ma_len=int(p.pop("ma_len", 14)),
        ma_type=str(p.pop("ma_type", "SMA")),
    )
    tm_params.validate("fixed")

    cfg = tm_backtest.BTConfig(
        fee_bps=float(p.pop("fee_bps", 5.0)),
        slip_bps=float(p.pop("slip_bps", 0.5)),
        leverage=float(p.pop("leverage", 1.0)),
        side=str(p.pop("side", "both")),
        delay=int(p.pop("delay", 1)),
    )
    cfg.validate()

    if p:
        raise ValueError(f"unknown trendmagic params: {sorted(p)}")

    # Load OHLCV from the served CSV (Binance open_ts ms epoch).
    df = tm_data.validate_ohlcv(_load_binance_csv(paths[0]))

    # Indicator: fixed (audited) mode.
    tm = tm_core.trend_magic(df, tm_params, mode="fixed")

    # Backtest: next-open fill, stop-and-reverse, costs per side.
    res = tm_backtest.run_backtest(df, tm["sig"].to_numpy(), cfg)

    ppy = tm_backtest.periods_per_year(df.index)
    m = tm_backtest.perf(res.ret, ppy, res.pos.to_numpy(), res.trades)

    sym = os.path.basename(paths[0]).split("_")[0]

    # Buy & hold reference over the same window.
    bh = tm_backtest.perf(tm_backtest.buy_hold(df), ppy)

    n_trades = int(m.get("n_trades", 0))
    total_ret = float(m.get("total_ret", 0.0))
    pf = m.get("profit_factor")
    pf_out = None if pf in (float("inf"), float("-inf")) else float(pf) if pf is not None else None

    metrics = {
        "symbol": sym,
        "bars": int(len(df)),
        "first": str(df.index[0]),
        "last": str(df.index[-1]),
        "n_trades": n_trades,
        "return_pct": total_ret * 100.0,
        "final_equity": (1.0 + total_ret) * 10000.0,
        "cagr_pct": float(m.get("cagr", 0.0)) * 100.0,
        "sharpe": float(m.get("sharpe", float("nan"))),
        "sortino": float(m.get("sortino", float("nan"))),
        "vol_ann_pct": float(m.get("vol_ann", 0.0)) * 100.0,
        "max_dd_pct": float(m.get("max_dd", 0.0)) * 100.0,
        "calmar": float(m.get("calmar", float("nan"))),
        "exposure_pct": float(m.get("exposure", 0.0)) * 100.0,
        "turnover_yr": float(m.get("turnover_yr", 0.0)),
        "win_rate": float(m.get("win_rate", 0.0)) * 100.0 if m.get("win_rate") is not None else 0.0,
        "profit_factor": pf_out,
        "avg_trade_pct": float(m.get("avg_trade", 0.0)) * 100.0,
        "avg_bars": float(m.get("avg_bars", 0.0)),
        "bh_return_pct": float(bh.get("total_ret", 0.0)) * 100.0,
        "cost_bp_roundtrip": 2.0 * (cfg.fee_bps + cfg.slip_bps),
        "fee_bps_per_side": cfg.fee_bps,
        "slippage_bps_per_side": cfg.slip_bps,
        "leverage": cfg.leverage,
        "side": cfg.side,
        "delay": cfg.delay,
        "funding_charged": False,
        "flag": "OK" if n_trades >= 30 else "INSUFFICIENT_SAMPLE",
    }

    prov = {
        "adapter": "trendmagic",
        "engine_version": "trendmagic-1",
        "engine_files": ["tm_core.py", "tm_backtest.py", "tm_data.py"],
        "mode": "fixed",
        "conventions": {
            "fill": "next open (delay >= 1)",
            "sizing": "stop-and-reverse, {-1,0,+1} x leverage, rebalanced each bar",
            "costs": f"{cfg.fee_bps} bps fee + {cfg.slip_bps} bps slip per side",
            "funding": "not charged (kline-only indicator, declared limit)",
            "accounting_identity": "eq[-1] - INIT == sum(pnl) asserted inside run_backtest",
        },
        "tm_params": {
            "cci_len": tm_params.cci_len, "atr_len": tm_params.atr_len,
            "atr_mult": tm_params.atr_mult, "src": tm_params.src,
            "atr_type": tm_params.atr_type, "flip_on": tm_params.flip_on,
            "smooth": tm_params.smooth, "ma_len": tm_params.ma_len,
            "ma_type": tm_params.ma_type,
        },
    }

    tables = None
    if res.trades is not None and len(res.trades):
        t = res.trades
        tables = [
            {
                "entry_time": str(et), "exit_time": str(xt),
                "side": s, "entry_px": float(ep), "exit_px": float(xp),
                "bars": int(b), "ret_pct": float(r) * 100.0, "open": bool(o),
            }
            for et, xt, s, ep, xp, b, r, o in zip(
                t["entry_time"], t["exit_time"], t["side"],
                t["entry_px"], t["exit_px"], t["bars"], t["ret"], t["open"],
            )
        ]

    return metrics, prov, tables
