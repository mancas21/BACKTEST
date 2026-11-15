#!/usr/bin/env python
"""qs096_engine.py -- QS-096 "Market-structure reversal plus volatility filter" (family J).

SOURCE OF RECORD: Catalog Card QS-096
  Instruments: BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps
  Timeframes: 5m, 15m, 1h (each timeframe is a separate hypothesis)
  Signal core: #33 (QS-033 CHoCH retest reversal).
  Volatility filter: ATR(14) percentile over 500 bars is between 30 and 80.
  Long entry: #33 CHoCH retest long taken ONLY when 30 <= ATR_pct(500) <= 80.
  Short entry: Mirror image of the long rules (two-sided variant, tested as a separate hypothesis).
  Exit: As #33 (re-cross opposite CHoCH level +- 0.5*ATR).
  Stop Loss: As #33 (swing extreme before the break, clipped lower at 0.5*ATR).
  Take Profit: As #33 (2.0 * stop distance).
  Max Hold: 100 bars.
  Frequency: One entry per signal episode; cooldown 5 bars after exit; max 1 open position per symbol.
  Inherits: G1 sizing, G2 costs, G3 funding, G4 validation, G5 min_data, G6 plots, G7 acceptance_rejection.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import qs_d_strats as D
import qs_strats as P
from qs_engine import (
    COSTS, G1, INIT, atr as cat_atr, load_funding, run as cat_run,
)

ENGINE_VERSION = "qs096-1"

COSTS096 = {**COSTS, "zero": dict(fee=0.0, slip=0.0, stop_slip_mult=1.0)}

P_DEFAULTS = dict(
    atr_n=14,
    pct_win=500,
    pct_lo=30.0,
    pct_hi=80.0,
    max_hold=100,
    variant="two_side",   # two_side | long
)


def _pct_rank_below(x: pd.Series, win: int) -> pd.Series:
    """Fraction of the trailing `win` window at or below the current value (0..1),
    via pandas rolling rank."""
    return x.rolling(win, min_periods=win).rank(pct=True)


def build_plan(df: pd.DataFrame, tf: str, cfg: dict) -> dict:
    """Build the QS-096 plan on DataFrame df."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = D._atr_s(df)
    v = df["volume"].astype(float)
    ph_conf, pl_conf = D._confirmed_pivots(df, 3)
    ph_last, ph_prev = D._last_two(ph_conf)
    pl_last, pl_prev = D._last_two(pl_conf)
    adx = D._adx_s(df, 14)

    # 1. Base #33 Downtrend CHoCH Break
    dn = (ph_last < ph_prev) & (pl_last < pl_prev)
    choch = ph_last
    brk = dn & (c > choch)
    vol_ok = v >= 0.7 * v.rolling(20, min_periods=20).mean()
    adx_ok = adx <= 35.0
    brk_ok = brk & vol_ok & adx_ok

    lvl = choch.where(brk_ok).ffill()
    stop_ref = pl_last.where(brk_ok).ffill()
    anchor = D._spaced_edges(brk_ok, 8)
    since = D._bars_since(anchor)
    touch = l <= lvl
    touched = touch.where(since >= 1).astype(float).groupby(anchor.cumsum()).cummax() > 0.5
    raw_long_c = (c > lvl) & touched.astype(bool) & since.between(1, 8)

    # 2. Base #33 Uptrend CHoCH Break (Mirror)
    up = (ph_last > ph_prev) & (pl_last > pl_prev)
    choch_s = pl_last
    brk_s = up & (c < choch_s)
    brk_s_ok = brk_s & vol_ok & adx_ok

    lvl_s = choch_s.where(brk_s_ok).ffill()
    stop_ref_s = ph_last.where(brk_s_ok).ffill()
    anchor_s = D._spaced_edges(brk_s_ok, 8)
    since_s = D._bars_since(anchor_s)
    touch_s = h >= lvl_s
    touched_s = touch_s.where(since_s >= 1).astype(float).groupby(anchor_s.cumsum()).cummax() > 0.5
    raw_short_c = (c < lvl_s) & touched_s.astype(bool) & since_s.between(1, 8)

    # 3. Volatility Filter: ATR(14) percentile over 500 bars in [30, 80]
    pct_win = int(cfg.get("pct_win", 500))
    pct_lo = float(cfg.get("pct_lo", 30.0))
    pct_hi = float(cfg.get("pct_hi", 80.0))
    atr_pct = _pct_rank_below(a, pct_win) * 100.0
    vol_ok = (atr_pct >= pct_lo) & (atr_pct <= pct_hi)

    long_c = raw_long_c & vol_ok
    short_c = raw_short_c & vol_ok

    dist_l = (c - stop_ref).clip(lower=0.5 * a).where(long_c)
    dist_s = (stop_ref_s - c).clip(lower=0.5 * a).where(short_c)
    tp_l = (2.0 * dist_l).where(long_c)
    tp_s = (2.0 * dist_s).where(short_c)

    variant = cfg.get("variant", "two_side")
    long_event = D._edge(long_c)
    short_event = D._edge(short_c) if variant == "two_side" else pd.Series(np.zeros(len(df), bool), index=df.index)

    long_exit = c < (lvl - 0.5 * a)
    short_exit = c > (lvl_s + 0.5 * a) if variant == "two_side" else pd.Series(np.zeros(len(df), bool), index=df.index)

    return dict(
        long_event=long_event.to_numpy(bool),
        short_event=short_event.to_numpy(bool),
        long_exit=long_exit.fillna(False).to_numpy(bool),
        short_exit=short_exit.fillna(False).to_numpy(bool),
        stop_level_long=(c - dist_l).where(long_c).to_numpy(float),
        stop_level_short=(c + dist_s).where(short_c).to_numpy(float),
        stop_dist_long=dist_l.to_numpy(float),
        stop_dist_short=dist_s.to_numpy(float),
        tp_dist_long=tp_l.to_numpy(float),
        tp_dist_short=tp_s.to_numpy(float),
        max_hold=int(cfg.get("max_hold", 100)),
        atr=a.to_numpy(float),
        atr_pct=atr_pct.to_numpy(float),
        raw_long_c=raw_long_c.to_numpy(bool),
        raw_short_c=raw_short_c.to_numpy(bool),
    )


def run_symbol(df: pd.DataFrame, tf: str, cfg: dict,
               funding_path=None, cost="gate", init=INIT):
    """Run one symbol under the catalog executor (G1/G2/G3)."""
    cc = COSTS096[cost]
    plan = build_plan(df, tf, cfg)
    funding = load_funding(funding_path) if funding_path else None
    out = cat_run(df, plan, cc["fee"], cc["slip"],
                  stop_slip_mult=cc.get("stop_slip_mult", 1.0),
                  funding=funding, g1=dict(G1), init=init)
    out["plan_counts"] = dict(
        long_events=int(np.asarray(plan["long_event"]).sum()),
        short_events=int(np.asarray(plan["short_event"]).sum()),
        raw_long_events=int(D._edge(plan["raw_long_c"]).sum()),
        raw_short_events=int(D._edge(plan["raw_short_c"]).sum()),
    )
    out["cost"] = cost
    return out


def _pf(pnls):
    gp = pnls[pnls > 0].sum()
    gl = -pnls[pnls < 0].sum()
    if gl > 0:
        return float(gp / gl)
    return (float("inf") if gp > 0 else 0.0)


def _thirds(eq):
    e = np.asarray(eq, float)
    out = []
    for k in range(3):
        a, b = int(len(e) * k / 3), int(len(e) * (k + 1) / 3)
        out.append(100.0 * (e[b - 1] / e[a] - 1.0) if b > a and e[b - 1] > 0 else 0.0)
    return out


def run_symbol_metrics(df: pd.DataFrame, tf: str, cfg: dict,
                       funding_path=None, cost="gate", init=INIT) -> dict:
    """Full institutional metrics for bt.py / vrun harness."""
    out = run_symbol(df, tf, cfg, funding_path, cost, init)
    eq = out["eq"]
    trades = out["trades"]
    n_bars = len(eq)
    pnls = np.array([t["pnl"] for t in trades], float) if trades else np.zeros(0)
    ret = 100.0 * (eq[-1] / float(init) - 1.0)
    peak = np.maximum.accumulate(np.nan_to_num(eq, nan=float(init)))
    mdd = float(((np.nan_to_num(eq, nan=float(init)) - peak)
                 / np.maximum(peak, 1e-9)).min())
    n = len(trades)
    wins = sum(1 for t in trades if t["pnl"] > 0)

    # 70/30 OOS split
    split = int(n_bars * 0.7)
    ts_bar = df["open_ts"].to_numpy(np.int64) if "open_ts" in df else np.arange(n_bars)
    split_ms = int(ts_bar[split]) if len(ts_bar) else 0
    oos_mask = np.array([t["entry_ts"] >= split_ms for t in trades]) if n else np.zeros(0, bool)

    m = dict(
        return_pct=ret,
        profit_factor=_pf(pnls) if n else 0.0,
        n_trades=n,
        win_rate=100.0 * wins / n if n else 0.0,
        max_dd_pct=100.0 * mdd,
        thirds_net_pct=_thirds(eq),
        n_periods_green=int(sum(1 for x in _thirds(eq) if x > 0)),
        oos_split_bar=split,
        oos_return_pct=100.0 * (eq[-1] / eq[split] - 1.0) if len(eq) > split + 1 and np.isfinite(eq[split]) and eq[split] > 0 else 0.0,
        oos_n_trades=int(oos_mask.sum()),
        oos_profit_factor=_pf(pnls[oos_mask]) if oos_mask.any() else 0.0,
        best5_share_pct=(100.0 * float(np.sort(pnls)[::-1][:5].sum()) / float(pnls.sum())) if n and pnls.sum() else float("nan"),
        n_stop_fills=out["n_stop_fills"],
        n_gap_fills=out["n_gap_fills"],
        n_daily_halts=out["n_daily_halts"],
        n_review_halt=out["n_review_halt"],
        max_leverage=out["max_leverage"],
        funding_paid=out["fund_paid"],
        n_funding=out["n_funding"],
        fees_paid=out["fees_paid"],
        plan_counts=out["plan_counts"],
        variant=cfg["variant"],
        cost_mode=cost,
        cost_bp_roundtrip=2.0 * (COSTS096[cost]["fee"] + COSTS096[cost]["slip"]) * 1e4,
        fee_bps_per_side=COSTS096[cost]["fee"] * 1e4,
        slippage_bps_per_side=COSTS096[cost]["slip"] * 1e4,
        funding_model=("real settlements" if funding_path else "off"),
    )
    if cost != "zero":
        zc = run_symbol(df, tf, cfg, None, "zero", init)
        zpn = np.array([t["pnl"] for t in zc["trades"]], float) if zc["trades"] else np.zeros(0)
        m["ret_zero_pct"] = 100.0 * (zc["eq"][-1] / float(init) - 1.0)
        m["pf_zero"] = _pf(zpn) if len(zpn) else 0.0
        m["n_zero"] = len(zc["trades"])
        m["drag_pp"] = m["ret_zero_pct"] - ret

    if n > 1:
        rng = np.random.default_rng(7)
        boot = np.array([rng.choice(pnls, len(pnls), replace=True).mean() for _ in range(20000)])
        m["boot_ci_lo"] = float(np.percentile(boot, 2.5))
        m["boot_ci_hi"] = float(np.percentile(boot, 97.5))
        m["boot_p_le_zero"] = float((boot <= 0).mean())
        m["boot_draws"] = 20000
        m["boot_seed"] = 7

    m["gate_pf"] = bool(m["profit_factor"] > 1.2)
    m["gate_n"] = bool(m["n_trades"] >= 30)
    m["gate_net"] = bool(m["return_pct"] > 0)
    m["gate_thirds"] = bool(m["n_periods_green"] >= 2)
    m["gate_oos"] = bool(m["oos_profit_factor"] > 1.2 and m["oos_return_pct"] > 0)
    m["gate_conc"] = bool(np.isfinite(m["best5_share_pct"]) and m["best5_share_pct"] <= 100.0)
    m["gate_boot_ci"] = bool(n > 1 and m.get("boot_ci_lo", 0.0) > 0)
    m["gate_all"] = bool(m["gate_pf"] and m["gate_n"] and m["gate_net"]
                         and m["gate_thirds"] and m["gate_oos"]
                         and m["gate_conc"] and m["gate_boot_ci"])
    m["closed_pnl"] = [float(x) for x in pnls]
    return m


def run_cell(paths, params):
    """vrun harness adapter entry."""
    p = dict(P_DEFAULTS)
    p.update({k: v for k, v in params.items() if v is not None})
    tf = str(p.get("tf", "1h"))
    kline_path = paths[0]
    fund_path = paths[1] if len(paths) > 1 and paths[1].endswith(".json") else None

    # Load klines
    df = pd.read_csv(kline_path)
    if "open_time" in df and "open_ts" not in df:
        df["open_ts"] = df["open_time"]
    elif "timestamp" in df and "open_ts" not in df:
        df["open_ts"] = df["timestamp"]

    cost = str(p.get("cost", "gate"))
    m = run_symbol_metrics(df, tf, p, funding_path=fund_path, cost=cost)
    return m
