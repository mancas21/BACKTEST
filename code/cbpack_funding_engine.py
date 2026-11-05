#!/usr/bin/env python3
"""
cbpack_funding_engine.py — FORK of code/cbpack_engine.py that CHARGES FUNDING (v2, audited).

ORIGINAL: code/cbpack_engine.py
          sha256 055b584de9aa23c2695934cc50ac0b612f9b374b0c1fa19600072a4fef4e1fde
          (byte-identical to Downloads/strategy_pack.py; that file is NOT modified)

WHY THIS FORK EXISTS
  The original attaches a `funding_rate` column to the dataframe but never debits
  it from PnL. A Binance USDT-M perpetual charges funding every 8h on the open
  notional, and the long side pays whenever the rate is positive. For a strategy
  that is in the market most of the time that is a real, continuous cost.

  `funding_attached: true` means the COLUMN was attached, not that the COST was
  charged. In THIS fork every result carries `funding_charged` so you can tell.

PATCH LIST (everything not listed is byte-for-byte the original's logic)
  P1 fail-closed   BacktestConfig.charge_funding / require_funding / funding_mult.
                   If `funding_rate` is attached but `funding_event_rate` is not,
                   backtest() raises FundingConfigError instead of silently charging
                   nothing. Every metrics dict carries `funding_charged`.
  P2 backtest()    debit funding on the position held at each settlement, marked at
                   the bar OPEN (settlement instant), BEFORE the fill at that open.
  P3 trades/metrics per-trade `funding` column (+ve = paid); gross_return_pct is
                   reported BEFORE fees AND funding; funding_paid / funding_paid_pct.
  P4 concentration top-5 AND top-decile diagnostics; share is NaN when total PnL <= 0.
  P5 attach_funding_events  vectorised, accumulates (does not overwrite) multiple
                   settlements per bar, snaps ms jitter, normalises tz/resolution,
                   raises on settlements lost to data gaps, guards percent-vs-decimal.
  P6 benchmark     buy_hold_net_pct / excess_vs_bh_net_pct: buy&hold AFTER round-trip
                   fees+slippage AND funding. (Original buy_hold_return_pct and
                   excess_vs_buy_hold_pct are kept unchanged for parity.)
  P7 data          taker-flow alias (`taker_buy_base_asset_volume`), us/ns epoch
                   detection, data_quality() gap report, merge_asof unit alignment.
  P8 reporting     evaluate_all() reports `flow_source` and `funding_charged`;
                   warns when the candle-colour proxy replaced true taker flow.
  P9 research      expectancy_ci() block bootstrap; deflated_sharpe(); pbo_cscv();
                   trial_returns()/overfit_report(); walk_forward(select="plateau");
                   funding_sensitivity().

KNOWN INHERITED LIMITS (kept on purpose so zero-funding parity with the original holds)
  * _metrics() measures return from the equity at the END of the first bar.
  * Position size is computed from the signal-bar close but filled at the next open.
  * Structural stops (S09) are a frozen distance from the signal close.
  * `_first()` blocks re-entry after a stop-out while the condition stays true.
  * No liquidation engine, no partial fills, no tick/lot rounding, no maker rebates.

FUNDING CONVENTION (documented, deterministic)
  * A settlement at instant T is charged to the position HELD AT T: the one carried
    INTO the bar that opens at T.
  * A position opened at that same open is established AT T and does not pay that round.
  * A position closed at that same open was holding into T and DOES pay it.
  * Notional = qty * open price of the settlement bar (mark proxy at T).
  * Settlements mid-bar (8h not a multiple of the bar size) are charged at that bar's
    open: approximate; attach_funding_events() warns.

PARITY: with funding forced to zero this engine reproduces the original's trades and
equity exactly (see test_cbpack_funding_engine.py).

--- ORIGINAL DOCSTRING (continues; the funding bullet below was updated) ---------------

strategy_pack.py — ten composable crypto strategy designs for the backtesting agent (Python only).

Same philosophy as the audited SAX v4 engine: every strategy is a COMBINATION of
  (1) a signal core  +  (2) gates/filters  +  (3) an explicit exit & risk model,
all evaluated on CLOSED bars, filled at the NEXT open, with fees + slippage always on.
Research only: no live orders, no exchange connectivity.

────────────────────────────────── THE TEN COMBINATIONS ──────────────────────────────────
ID   Name                         Core signal                  Gates / filters                     Exit / risk
S01  TFD Taker-Flow Drift Bands   EMA-drift of true taker flow  HTF trend, cooldown, band guard      ATR SL + TP
S02  DFB Donchian+Flow Breakout   N-bar channel breakout        taker-flow z, HTF trend              channel exit + ATR SL
S03  SQZ Squeeze Release          BB inside KC, then release    momentum sign + flow z agree         ATR SL/TP + time stop
S04  VWF VWAP Fade (range only)   rolling-VWAP sigma extreme    efficiency ratio < max, flow turning exit at VWAP + ATR SL + time stop
S05  TPB HTF Trend Pullback       RSI(2) extreme                HTF + base trend                     RSI exit + ATR SL + time stop
S06  SBO Session Range Breakout   Asia-range break (UTC)        volume spike, flow z, 1 per day      session-end exit + ATR SL/TP
S07  FUN Funding Extreme Fade     funding z-score extreme       price rolls over EMA                 ATR SL/TP + time stop   [needs funding]
S08  OIP OI/Price Regime          OI z + price move             taker-flow z; squeeze-fade variant   ATR SL/TP + time stop   [needs open interest]
S09  LSR Liquidity Sweep Reversal sweep of N-bar extreme+reclaim wick ratio, volume spike, flow turn structural SL + R-multiple TP + time stop
S10  TSM Vol-Targeted Momentum    N-bar return / realised vol   hysteresis (enter >thr, exit <0)     sign-flip exit + wide ATR SL (cost-light)

"True taker flow" = taker_buy_base volume from Binance klines (signed volume = buy - sell). If the column
is absent the engine falls back to the candle-colour proxy and flags it (`flow_source`).
S07/S08 need extra series (funding, open interest) — attach_funding()/attach_oi() merge them with NO
look-ahead. Without them those strategies are skipped, never faked.
NOTE: Binance's open-interest HISTORY endpoint only serves roughly the last 30 days, so S08 cannot be
backtested over a long sample from that source.

────────────────────────────────── EXECUTION MODEL ──────────────────────────────────
• Signal at bar i close -> order at bar i+1 open (+ adverse slippage); fee per side.
• SL/TP distances are frozen at signal time (`sl_dist`, `tp_dist`, price units).
• Intrabar SL/TP; both inside one bar -> SL first (conservative, configurable). Gap through a level fills at the open.
• Time stop: `max_hold` bars including the entry bar. Exit signals execute at the next open.
• Sizing: fixed % equity or stop-risk (risk % of equity / stop distance), capped by max leverage.
• Funding: charged only when `funding_event_rate` is present (attach_funding_events); see FUNDING CONVENTION.
  No liquidation engine, no partial fills (state this in any report you produce).

────────────────────────────────── HOW TO USE ──────────────────────────────────
  df = load_ohlcv("SOLUSDT_15m.csv")                    # UTC bar-open index; Binance klines OK
  print(data_quality(df))                               # gaps / taker-flow present?
  df = attach_funding(df, funding_series)               # funding_rate column (S07's z-score)
  df = attach_funding_events(df, funding_series)        # billing schedule (REQUIRED to charge funding)
  df = attach_oi(df, oi_series, lag_bars=1)             # optional (S08)
  table = evaluate_all(df, BacktestConfig())            # all strategies vs buy&hold, with costs
  wf = walk_forward(df, "S02", BacktestConfig(), train_bars=8000, test_bars=2000, select="plateau")
  rep = overfit_report(df, "S02", BacktestConfig())     # PBO (CSCV) + deflated Sharpe over the grid
CLI:  python cbpack_funding_engine.py --data SOLUSDT_15m.csv --funding funding.csv --oi oi.csv

IMPORTANT: ranking ten strategies on one sample is itself a multiple-testing exercise. Require
out-of-sample (walk_forward), several pairs/periods, PBO/deflated Sharpe, and a positive result AFTER
costs AND funding before believing any row.

Requirements: Python 3.10+, numpy, pandas.
"""
from __future__ import annotations

import argparse
import itertools
import math
import warnings
from dataclasses import dataclass, field, replace
from statistics import NormalDist
from typing import Callable, Optional

import numpy as np
import pandas as pd


class MissingData(Exception):
    """Raised when a strategy needs a column the dataset does not have."""


class FundingConfigError(RuntimeError):
    """Funding data is attached (or required) but would silently NOT be charged.

    Deliberately NOT a MissingData subclass: evaluate_all() swallows MissingData as
    'SKIPPED', and this error must never be swallowed.
    """


# ═════════════════════════════════ configuration ═════════════════════════════════
@dataclass
class BacktestConfig:
    initial_capital: float = 10_000.0
    fee_bps: float = 5.0              # per side
    slippage_bps: float = 2.0         # per side, adverse; market entries/exits and stop exits
    sizing_mode: str = "stop_risk"    # "stop_risk" | "fixed_pct"
    risk_pct: float = 1.0             # % of equity risked to the stop (stop_risk)
    pct_equity: float = 100.0         # fixed_pct
    max_leverage: float = 3.0
    opposite_signal: str = "ignore"   # "ignore" | "close" | "reverse"
    allow_long: bool = True
    allow_short: bool = True
    both_hit_rule: str = "sl_first"
    start: Optional[str] = None
    end: Optional[str] = None
    # P1 — funding controls
    charge_funding: bool = True       # False = explicitly run WITHOUT funding (reported as funding_charged=False)
    require_funding: bool = False     # True = raise if no funding events are available to charge
    funding_mult: float = 1.0         # scale the settled rates (0 = off, 2 = stress)


# ═════════════════════════════════ data helpers ═════════════════════════════════
_ALIASES = {"taker_buy_base": "taker_buy", "taker_buy_volume": "taker_buy", "taker_buy_base_volume": "taker_buy",
            "takerbuybase": "taker_buy",
            "taker_buy_base_asset_volume": "taker_buy",          # P7: standard Binance kline column name
            "count": "num_trades", "trades": "num_trades", "number_of_trades": "num_trades",
            "fundingrate": "funding_rate", "funding": "funding_rate", "oi": "open_interest",
            "sumopeninterest": "open_interest"}
_NUMERIC = ("open", "high", "low", "close", "volume", "taker_buy", "num_trades", "funding_rate", "open_interest")


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_ALIASES.get(str(c).strip().lower(), str(c).strip().lower()) for c in df.columns]
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame needs a DatetimeIndex (bar open time, UTC)")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for c in _NUMERIC:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    keep = [c for c in _NUMERIC if c in df.columns]
    return df[keep].dropna(subset=["open", "high", "low", "close"])


def load_ohlcv(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    tcol = next((c for c in ("open_time", "timestamp", "time", "datetime", "date") if c in df.columns), None)
    if tcol is not None:
        ts = df[tcol]
        if pd.api.types.is_numeric_dtype(ts):
            m = float(ts.iloc[0])                                   # P7: s / ms / us / ns epochs
            unit = "ns" if m > 1e17 else "us" if m > 1e14 else "ms" if m > 1e11 else "s"
            df.index = pd.to_datetime(ts, unit=unit, utc=True)
        else:
            df.index = pd.to_datetime(ts, utc=True)
    return prepare(df)


def base_seconds(df: pd.DataFrame) -> int:
    return int(round(df.index.to_series().diff().dropna().dt.total_seconds().median()))


def data_quality(df: pd.DataFrame) -> dict:
    """P7: bar-grid sanity. rolling(n) means n BARS, so gaps silently stretch every lookback."""
    base = base_seconds(df)
    d = df.index.to_series().diff().dropna().dt.total_seconds()
    gaps = d[d > 1.5 * base]
    missing = int(((gaps / base).round() - 1).clip(lower=0).sum())
    return {"bars": int(len(df)), "base_seconds": base, "gaps": int(len(gaps)), "missing_bars": missing,
            "max_gap_bars": float(gaps.max() / base) if len(gaps) else 1.0,
            "taker_buy_present": bool("taker_buy" in df.columns and df["taker_buy"].notna().any())}


def _asof_to_bars(df: pd.DataFrame, s: pd.Series) -> pd.Series:
    """Value of series `s` (index = time the value became KNOWN) as of each bar's CLOSE time."""
    s = s.copy()
    s.index = pd.to_datetime(s.index, utc=True)
    s = s[~s.index.duplicated(keep="last")].sort_index().astype(float)
    close_t = df.index + pd.Timedelta(seconds=base_seconds(df))
    if hasattr(s.index, "as_unit") and hasattr(close_t, "unit"):    # P7: ns vs us (pandas >= 2/3)
        s.index = s.index.as_unit(close_t.unit)
    left = pd.DataFrame({"t": close_t})
    right = pd.DataFrame({"t": s.index, "v": s.to_numpy()})
    out = pd.merge_asof(left, right, on="t", direction="backward")["v"]
    return pd.Series(out.to_numpy(), index=df.index)


def attach_funding(df: pd.DataFrame, funding: pd.Series) -> pd.DataFrame:
    """funding: Series of funding RATES indexed by settlement time (UTC). Known at settlement time."""
    out = df.copy()
    out["funding_rate"] = _asof_to_bars(df, funding)
    return out


def attach_funding_events(df: pd.DataFrame, funding: pd.Series, max_abs_rate: float = 0.01,
                          strict_gaps: bool = True) -> pd.DataFrame:
    """Mark the bars on which a funding SETTLEMENT occurs, with the settled rate (P5).

    attach_funding() carries the last known rate FORWARD onto every later bar. That is what
    a z-score of funding needs (S07) but it is NOT a billing schedule: on 1h data it would
    bill 8 settlements for every real one. This builds the billing schedule: a column that
    is non-zero only on the bar that CONTAINS the settlement instant.

      * settlements are snapped to the minute (second for sub-minute bars): exchange
        timestamps carry ms jitter, and T-3ms must not slide into the previous bar;
      * several settlements inside one bar (1d bars hold three) are SUMMED, not overwritten;
      * a settlement that falls in a data gap raises (strict_gaps) or warns - never silently dropped;
      * |rate| > max_abs_rate raises (percent-vs-decimal mixups: 0.0001 is 0.01%, not 0.0001%);
      * settlements strictly inside a bar (not on its open) are charged at that bar's open
        and a warning is issued, because that is only approximate.
    """
    out = df.copy()
    out["funding_event_rate"] = 0.0
    if funding is None or len(funding) == 0:
        return out
    base = base_seconds(df)
    f = pd.Series(np.asarray(funding, dtype=float), index=pd.to_datetime(funding.index, utc=True)).dropna()
    f.index = f.index.round("min" if base >= 60 else "s")
    f = f[~f.index.duplicated(keep="last")].sort_index()       # dedupe in ORIGINAL order, then sort (sort is not stable)
    if len(f) == 0:
        return out
    if hasattr(f.index, "as_unit") and hasattr(out.index, "unit"):
        f.index = f.index.as_unit(out.index.unit)
    bar = pd.Timedelta(seconds=base)
    in_range = np.asarray((f.index >= out.index[0]) & (f.index < out.index[-1] + bar))
    # the guard is scoped to the loaded window on purpose: a 2022 squeeze settlement must not
    # abort a 2024-2026 backtest, and a genuine >1% rate inside the window is a real cap event.
    if in_range.any() and float(f[in_range].abs().max()) > max_abs_rate:
        raise ValueError(f"|funding rate| {float(f[in_range].abs().max()):.4g} > {max_abs_rate} in the loaded "
                         "window: percent vs decimal mixup? (Binance rates are decimals, e.g. 0.0001 = 0.01%)")
    j = out.index.searchsorted(f.index, side="right") - 1            # bar whose OPEN <= T
    valid = (j >= 0) & (j < len(out))
    j0 = np.where(valid, j, 0)
    off = f.index - out.index[j0]
    inside = valid & np.asarray(off < bar)
    dropped = in_range & ~inside
    if dropped.any():
        msg = (f"{int(dropped.sum())} funding settlement(s) fall in data gaps (no bar contains them), "
               f"first at {f.index[np.argmax(dropped)]}")
        if strict_gaps:
            raise ValueError(msg)
        warnings.warn(msg, stacklevel=2)
    mid = inside & np.asarray(off != pd.Timedelta(0))
    if mid.any():
        warnings.warn(f"{int(mid.sum())} settlement(s) fall mid-bar (8h is not a multiple of the "
                      f"{base}s bar); charged at that bar's open - approximate", stacklevel=2)
    ev = np.zeros(len(out))
    np.add.at(ev, j0[inside], f.to_numpy()[inside])                   # accumulate, never overwrite
    out["funding_event_rate"] = ev
    return out


def attach_oi(df: pd.DataFrame, oi: pd.Series, lag_bars: int = 1) -> pd.DataFrame:
    """oi: open-interest Series indexed by its timestamp (UTC). `lag_bars` delays it further because
    exchange history timestamps are ambiguous (period start vs end): the safe default is 1 bar."""
    out = df.copy()
    out["open_interest"] = _asof_to_bars(df, oi).shift(lag_bars)
    return out


# ═════════════════════════════════ indicators ═════════════════════════════════
def sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n).mean()


def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
    return tr


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    out = 100.0 - 100.0 / (1.0 + up / dn)
    return out.where(dn != 0, 100.0).where(up.notna() & dn.notna())


def zscore(x: pd.Series, n: int) -> pd.Series:
    mu, sd = x.rolling(n).mean(), x.rolling(n).std(ddof=0)
    return ((x - mu) / sd).where(sd > 0, 0.0).where(sd.notna())


def efficiency_ratio(close: pd.Series, n: int) -> pd.Series:
    return (close - close.shift(n)).abs() / close.diff().abs().rolling(n).sum()


def htf_trend(df: pd.DataFrame, minutes: int, fast: int = 20, slow: int = 50) -> pd.Series:
    """+1 / -1 from EMA(fast) vs EMA(slow) of the last COMPLETED higher-timeframe bar; 0 = unknown."""
    base = base_seconds(df)
    if minutes * 60 < base:
        raise ValueError("htf minutes must be >= chart timeframe")
    hc = df["close"].resample(f"{int(minutes)}min", label="left", closed="left").last().dropna()
    ef, es = ema(hc, fast).shift(1), ema(hc, slow).shift(1)
    tr = pd.Series(np.where(ef.notna() & es.notna(), np.where(ef > es, 1, -1), 0), index=hc.index)
    return tr.reindex(df.index, method="ffill").fillna(0).astype(int)


def flow_series(df: pd.DataFrame) -> tuple[pd.Series, str]:
    """Signed volume normalised by average volume. Taker-based if available, else candle-colour proxy."""
    v = df["volume"]
    if "taker_buy" in df.columns and df["taker_buy"].notna().any():
        flow, src = df["taker_buy"] - (v - df["taker_buy"]), "taker"
    else:
        flow, src = v * np.sign(df["close"] - df["open"]), "candle_proxy"
    return flow / sma(v, 50), src


def flow_z(df: pd.DataFrame, k: int = 5, zwin: int = 100) -> pd.Series:
    f, _ = flow_series(df)
    return zscore(ema(f, k), zwin)


def _first(cond: pd.Series) -> pd.Series:
    cond = cond.fillna(False).astype(bool)
    return cond & ~cond.shift(1, fill_value=False)


def _cooldown(sig: np.ndarray, bars: int) -> np.ndarray:
    out, last = np.zeros(len(sig), dtype=bool), -10**9
    for i in range(len(sig)):
        if sig[i] and i - last >= bars:
            out[i], last = True, i
    return out


def _frame(df, buy, sell, sl_dist, tp_dist=None, max_hold=0, exit_long=None, exit_short=None, meta=None):
    n = len(df)
    arr = lambda x, d=False: np.asarray(x.fillna(d) if hasattr(x, "fillna") else x, dtype=bool) if x is not None else np.zeros(n, bool)
    sl = np.asarray(sl_dist, dtype=float)
    ok = np.isfinite(sl) & (sl > 0)
    out = pd.DataFrame(index=df.index)
    out["buy"] = arr(buy) & ok
    out["sell"] = arr(sell) & ok
    out["sl_dist"] = sl
    out["tp_dist"] = np.full(n, np.nan) if tp_dist is None else np.asarray(tp_dist, dtype=float)
    out["max_hold"] = int(max_hold)
    out["exit_long"] = arr(exit_long)
    out["exit_short"] = arr(exit_short)
    out.attrs["meta"] = meta or {}
    return out


def _band_machine(high, low, close, dn, atr_v, am, guard):
    """SAX-style volume-shifted trailing bands (same logic as the audited SAX v4 engine)."""
    n = len(close)
    ub, lb = np.full(n, np.nan), np.full(n, np.nan)
    buy, sell = np.zeros(n, bool), np.zeros(n, bool)
    tr_prev, last_sig = 0, 0
    for i in range(n):
        d, a = dn[i], atr_v[i]
        if np.isnan(d) or np.isnan(a):
            ur = lr = np.nan
        else:
            ur, lr = (high[i] - d * a) + a * am, (low[i] + d * a) - a * am
        ub_p, lb_p = (ub[i - 1], lb[i - 1]) if i else (np.nan, np.nan)
        c_p = close[i - 1] if i else np.nan
        ub[i] = np.nan if np.isnan(ur) else (ur if np.isnan(ub_p) else (min(ur, ub_p) if c_p <= ub_p else ur))
        lb[i] = np.nan if np.isnan(lr) else (lr if np.isnan(lb_p) else (max(lr, lb_p) if c_p >= lb_p else lr))
        both = not (np.isnan(ub_p) or np.isnan(lb_p))
        ok = (not guard) or (both and ub_p > lb_p)
        cb = (not np.isnan(ub_p)) and close[i] > ub_p and tr_prev != 1 and ok
        cs = (not np.isnan(lb_p)) and close[i] < lb_p and tr_prev != -1 and ok
        tr_i = -1 if cs else (1 if cb else tr_prev)
        b = cb and (not np.isnan(d)) and d > 0 and last_sig != 1
        s = cs and (not np.isnan(d)) and d < 0 and last_sig != -1
        if b:
            last_sig = 1
        if s:
            last_sig = -1
        buy[i], sell[i], tr_prev = b, s, tr_i
    return buy, sell


# ═════════════════════════════════ the ten strategies ═════════════════════════════════
def s01_tfd(df, fast=3, slow=13, norm_len=20, atr_len=14, band_mult=1.68, htf=60, cooldown=10,
            band_guard=True, sl_k=1.5, tp_k=3.0):
    flow, src = flow_series(df)
    drift = ema(flow, fast) - ema(flow, slow)
    dn = zscore(drift, norm_len).to_numpy()
    a = atr(df, atr_len)
    b, s = _band_machine(df.high.to_numpy(float), df.low.to_numpy(float), df.close.to_numpy(float), dn,
                         a.to_numpy(), band_mult, band_guard)
    tr = htf_trend(df, htf)
    b = _cooldown(b & (tr.to_numpy() == 1), cooldown)
    s = _cooldown(s & (tr.to_numpy() == -1), cooldown)
    return _frame(df, b, s, a * sl_k, a * tp_k, 0, meta={"flow_source": src})


def s02_dfb(df, n=48, m=16, flow_k=5, flow_zwin=100, z_thr=0.5, htf=60, atr_len=14, sl_k=2.0):
    hh, ll = df.high.rolling(n).max().shift(1), df.low.rolling(n).min().shift(1)
    fz = flow_z(df, flow_k, flow_zwin)
    tr = htf_trend(df, htf)
    up = _first(df.close > hh) & (fz > z_thr) & (tr == 1)
    dnx = _first(df.close < ll) & (fz < -z_thr) & (tr == -1)
    x_long = df.close < df.low.rolling(m).min().shift(1)
    x_short = df.close > df.high.rolling(m).max().shift(1)
    a = atr(df, atr_len)
    return _frame(df, up, dnx, a * sl_k, None, 0, x_long, x_short, {"flow_source": flow_series(df)[1]})


def s03_sqz(df, bb_len=20, bb_k=2.0, kc_len=20, kc_k=1.5, min_squeeze=6, flow_k=5, flow_zwin=100,
            atr_len=14, sl_k=1.5, tp_k=3.0, max_hold=48):
    mid, sd = sma(df.close, bb_len), df.close.rolling(bb_len).std(ddof=0)
    kc_mid, kc_a = ema(df.close, kc_len), atr(df, kc_len)
    sq = ((mid + bb_k * sd) < (kc_mid + kc_k * kc_a)) & ((mid - bb_k * sd) > (kc_mid - kc_k * kc_a))
    run = sq.astype(int).groupby((~sq).cumsum()).cumsum()
    release = (~sq) & sq.shift(1, fill_value=False) & (run.shift(1) >= min_squeeze)
    mom, fz = df.close - mid, flow_z(df, flow_k, flow_zwin)
    a = atr(df, atr_len)
    return _frame(df, release & (mom > 0) & (fz > 0), release & (mom < 0) & (fz < 0), a * sl_k, a * tp_k,
                  max_hold, meta={"flow_source": flow_series(df)[1]})


def s04_vwf(df, vwap_len=96, k=2.0, er_len=30, er_max=0.30, flow_k=3, flow_zwin=100, atr_len=14,
            sl_k=2.5, max_hold=48):
    tp_ = (df.high + df.low + df.close) / 3.0
    vwap = (tp_ * df.volume).rolling(vwap_len).sum() / df.volume.rolling(vwap_len).sum()
    dev = df.close - vwap
    z = dev / dev.rolling(vwap_len).std(ddof=0)
    er, fz = efficiency_ratio(df.close, er_len), flow_z(df, flow_k, flow_zwin)
    rng = er < er_max
    long_ = _first((z < -k) & rng & (fz > fz.shift(1)))
    short_ = _first((z > k) & rng & (fz < fz.shift(1)))
    a = atr(df, atr_len)
    return _frame(df, long_, short_, a * sl_k, None, max_hold, df.close >= vwap, df.close <= vwap,
                  {"flow_source": flow_series(df)[1]})


def s05_tpb(df, htf=60, htf_fast=20, htf_slow=50, trend_len=100, rsi_len=2, lo=10, hi=90,
            exit_long_rsi=70, exit_short_rsi=30, atr_len=14, sl_k=2.0, max_hold=24):
    r, tr = rsi(df.close, rsi_len), htf_trend(df, htf, htf_fast, htf_slow)
    base = ema(df.close, trend_len)
    up = (tr == 1) & (df.close > base) & (r < lo) & (r.shift(1) >= lo)
    dn = (tr == -1) & (df.close < base) & (r > hi) & (r.shift(1) <= hi)
    a = atr(df, atr_len)
    return _frame(df, up, dn, a * sl_k, None, max_hold, r > exit_long_rsi, r < exit_short_rsi)


def s06_sbo(df, asia_start=0, asia_end=8, trade_end=20, vol_spike=1.3, flow_k=5, flow_zwin=100,
            atr_len=14, sl_k=1.5, tp_k=3.0):
    hr, day = df.index.hour, df.index.normalize()
    in_asia = pd.Series((hr >= asia_start) & (hr < asia_end), index=df.index)
    a_hi = df.high.where(in_asia).groupby(day).transform("max")
    a_lo = df.low.where(in_asia).groupby(day).transform("min")
    live = pd.Series((hr >= asia_end) & (hr < trade_end), index=df.index)
    spike, fz = df.volume > vol_spike * sma(df.volume, 20), flow_z(df, flow_k, flow_zwin)
    cl, cs = live & (df.close > a_hi) & spike & (fz > 0), live & (df.close < a_lo) & spike & (fz < 0)
    cl = cl & (cl.astype(int).groupby(day).cumsum() == 1)
    cs = cs & (cs.astype(int).groupby(day).cumsum() == 1)
    a = atr(df, atr_len)
    after = pd.Series(hr >= trade_end, index=df.index)
    return _frame(df, cl, cs, a * sl_k, a * tp_k, 0, after, after, {"flow_source": flow_series(df)[1]})


def s07_fun(df, z_days=30, thr=2.0, ema_len=20, atr_len=14, sl_k=2.0, tp_k=4.0, max_hold=96):
    if "funding_rate" not in df.columns or df["funding_rate"].notna().sum() == 0:
        raise MissingData("S07 needs a funding_rate column (use attach_funding)")
    zb = max(int(z_days * 86400 / base_seconds(df)), 50)
    fz, e = zscore(df.funding_rate, zb), ema(df.close, ema_len)
    cross_dn = (df.close < e) & (df.close.shift(1) >= e.shift(1))
    cross_up = (df.close > e) & (df.close.shift(1) <= e.shift(1))
    a = atr(df, atr_len)
    return _frame(df, cross_up & (fz < -thr), cross_dn & (fz > thr), a * sl_k, a * tp_k, max_hold)


def s08_oip(df, k=12, z_win=200, oi_thr=1.0, flow_k=5, flow_zwin=100, mode="both", drop_atr=2.0,
            atr_len=14, sl_k=2.0, tp_k=4.0, max_hold=48):
    if "open_interest" not in df.columns or df["open_interest"].notna().sum() == 0:
        raise MissingData("S08 needs an open_interest column (use attach_oi)")
    oi_z = zscore(df.open_interest.pct_change(k), z_win)
    fz, a = flow_z(df, flow_k, flow_zwin), atr(df, atr_len)
    chg = df.close - df.close.shift(k)
    z = pd.Series(False, index=df.index)
    b, s = z.copy(), z.copy()
    if mode in ("trend", "both"):
        b |= _first((chg > 0) & (oi_z > oi_thr) & (fz > 0))
        s |= _first((chg < 0) & (oi_z > oi_thr) & (fz < 0))
    if mode in ("fade", "both"):
        b |= _first((chg < -drop_atr * a) & (oi_z < -oi_thr) & (fz > fz.shift(1)))
        s |= _first((chg > drop_atr * a) & (oi_z < -oi_thr) & (fz < fz.shift(1)))
    return _frame(df, b, s, a * sl_k, a * tp_k, max_hold, meta={"flow_source": flow_series(df)[1]})


def s09_lsr(df, n=24, wick_ratio=0.5, vol_spike=1.2, flow_k=3, flow_zwin=100, atr_len=14,
            sl_buffer=0.25, rr=2.0, max_hold=24):
    sw_lo, sw_hi = df.low.rolling(n).min().shift(1), df.high.rolling(n).max().shift(1)
    rng = (df.high - df.low).replace(0, np.nan)
    lw = (np.minimum(df.open, df.close) - df.low) / rng
    uw = (df.high - np.maximum(df.open, df.close)) / rng
    spike, fz, a = df.volume > vol_spike * sma(df.volume, 20), flow_z(df, flow_k, flow_zwin), atr(df, atr_len)
    long_ = (df.low < sw_lo) & (df.close > sw_lo) & (lw >= wick_ratio) & spike & (fz > fz.shift(1))
    short_ = (df.high > sw_hi) & (df.close < sw_hi) & (uw >= wick_ratio) & spike & (fz < fz.shift(1))
    sl_l = ((df.close - df.low) + sl_buffer * a).clip(lower=0.5 * a, upper=3.0 * a)
    sl_s = ((df.high - df.close) + sl_buffer * a).clip(lower=0.5 * a, upper=3.0 * a)
    sl = np.where(long_, sl_l, np.where(short_, sl_s, np.nan))
    return _frame(df, long_, short_, sl, sl * rr, max_hold, meta={"flow_source": flow_series(df)[1]})


def s10_tsm(df, lookback=168, vol_len=96, thr=0.5, atr_len=14, sl_k=3.0):
    lr = np.log(df.close).diff()
    strength = np.log(df.close / df.close.shift(lookback)) / (lr.rolling(vol_len).std(ddof=0) * math.sqrt(lookback))
    a = atr(df, atr_len)
    return _frame(df, _first(strength > thr), _first(strength < -thr), a * sl_k, None, 0, strength < 0, strength > 0)


# ═════════════════════════════════ registry ═════════════════════════════════
@dataclass
class StrategySpec:
    id: str
    name: str
    thesis: str
    failure_mode: str
    fn: Callable
    requires: tuple = ()
    timeframes: str = "5m-1h"
    grid: dict = field(default_factory=dict)


STRATEGIES: dict[str, StrategySpec] = {x.id: x for x in [
    StrategySpec("S01", "Taker-Flow Drift Bands",
                 "SAX idea with TRUE taker flow (not candle colour), HTF-aligned and with the band-inversion bug guarded.",
                 "Flow drift is a lagging transform of price in quiet markets; bands whipsaw in ranges.", s01_tfd,
                 grid={"fast": [3, 5], "slow": [13, 21], "tp_k": [2.0, 3.0]}),
    StrategySpec("S02", "Donchian + Flow Breakout",
                 "Channel breakouts that come with real aggressive buying/selling and HTF trend are more likely to follow through.",
                 "False breakouts in ranges; stops are wide so costs matter less but drawdowns are slow.", s02_dfb,
                 timeframes="15m-4h", grid={"n": [32, 48, 96], "m": [12, 24], "z_thr": [0.25, 0.5]}),
    StrategySpec("S03", "Squeeze Release",
                 "Volatility compression precedes expansion; direction from momentum plus flow agreement.",
                 "Squeezes release both ways; many releases are fakeouts.", s03_sqz,
                 grid={"min_squeeze": [4, 6, 10], "tp_k": [2.0, 3.0]}),
    StrategySpec("S04", "VWAP Fade (range regime only)",
                 "In low-efficiency regimes, sigma extremes from rolling VWAP revert when selling/buying pressure is exhausted.",
                 "A regime break (trend start) turns every fade into a loser; ER filter lags.", s04_vwf,
                 grid={"k": [1.5, 2.0, 2.5], "er_max": [0.2, 0.3]}),
    StrategySpec("S05", "HTF Trend Pullback (RSI-2)",
                 "Short-term exhaustion inside a higher-timeframe trend tends to snap back.",
                 "Trend ends; RSI-2 'oversold' keeps getting more oversold.", s05_tpb,
                 grid={"lo": [5, 10, 15], "max_hold": [12, 24]}),
    StrategySpec("S06", "Session Range Breakout (UTC)",
                 "Asia-session range sets levels; EU/US liquidity breaks them with volume; one attempt per day.",
                 "Session seasonality drifts; breakouts fail on low-volume days.", s06_sbo,
                 timeframes="5m-1h", grid={"vol_spike": [1.0, 1.3, 1.6], "tp_k": [2.0, 3.0]}),
    StrategySpec("S07", "Funding Extreme Fade",
                 "Extreme funding marks crowded positioning; fade once price rolls over its EMA.",
                 "Funding stays extreme in strong trends; edge, if any, is slow and thin.", s07_fun,
                 requires=("funding_rate",), timeframes="15m-4h", grid={"thr": [1.5, 2.0, 2.5], "max_hold": [48, 96]}),
    StrategySpec("S08", "OI / Price Regime",
                 "Rising OI with price and flow = new money (trend); collapsing OI after a violent move = liquidation exhaustion (fade).",
                 "OI data timing/definition quirks; regimes flip fast.", s08_oip,
                 requires=("open_interest",), timeframes="5m-1h", grid={"mode": ["trend", "fade", "both"], "oi_thr": [1.0, 1.5]}),
    StrategySpec("S09", "Liquidity Sweep Reversal",
                 "Stop-run beyond a prior extreme that closes back inside, with a wick and a volume/flow turn, marks absorbed liquidity.",
                 "Sweeps in trends continue instead of reverting; tight structural stops get noise-hit.", s09_lsr,
                 grid={"n": [16, 24, 48], "rr": [1.5, 2.0, 3.0]}),
    StrategySpec("S10", "Vol-Targeted Time-Series Momentum",
                 "Slow trend-following on risk-adjusted past return: few trades, so costs stay small.",
                 "Long flat/choppy regimes bleed small losses; needs trending sample to show an edge.", s10_tsm,
                 timeframes="1h-4h", grid={"lookback": [84, 168, 336], "thr": [0.3, 0.5, 0.8]}),
]}


# ═════════════════════════════════ backtest engine ═════════════════════════════════
@dataclass
class BacktestResult:
    metrics: dict
    trades: pd.DataFrame
    equity: pd.Series
    signals: pd.DataFrame


def _metrics(eq, trades, df, cfg, i0, i1, exposure, bpy, bh_fund=0.0, funding_charged=False) -> dict:
    e = eq.iloc[i0:i1 + 1]
    ret = e.pct_change().dropna()
    total = e.iloc[-1] / e.iloc[0] - 1.0 if len(e) > 1 else 0.0
    bh = df["close"].iloc[i1] / df["close"].iloc[i0] - 1.0
    sd = ret.std(ddof=1)
    # P6: buy&hold on the same perp pays the same round-trip costs and the same funding
    bh_net = bh - 2.0 * (cfg.fee_bps + cfg.slippage_bps) / 1e4 - bh_fund
    m = {"bars": int(i1 - i0 + 1), "n_trades": int(len(trades)), "net_return_pct": total * 100,
         "buy_hold_return_pct": bh * 100, "excess_vs_buy_hold_pct": (total - bh) * 100,
         "buy_hold_net_pct": bh_net * 100, "excess_vs_bh_net_pct": (total - bh_net) * 100,
         "max_drawdown_pct": float((e / e.cummax() - 1.0).min() * 100) if len(e) > 1 else 0.0,
         "sharpe_annualised": float(ret.mean() / sd * math.sqrt(bpy)) if sd and sd > 0 else float("nan"),
         "exposure_pct": exposure / max(i1 - i0 + 1, 1) * 100,
         "win_rate_pct": float("nan"), "profit_factor": float("nan"), "expectancy_R": float("nan"),
         "avg_trade_pct": float("nan"), "fees_paid": 0.0, "gross_return_pct": total * 100, "exit_reasons": {},
         "funding_paid": 0.0, "funding_paid_pct": 0.0, "funding_charged": bool(funding_charged)}
    if len(trades):
        w, l = trades[trades.pnl > 0], trades[trades.pnl <= 0]
        gl = -l.pnl.sum()
        fund_paid = float(trades.funding.sum()) if "funding" in trades else 0.0
        m.update({"win_rate_pct": len(w) / len(trades) * 100,
                  "profit_factor": float(w.pnl.sum() / gl) if gl > 0 else float("inf"),
                  "expectancy_R": float(trades.R.mean()), "avg_trade_pct": float(trades.pnl_pct.mean() * 100),
                  "fees_paid": float(trades.fees.sum()),
                  "funding_paid": fund_paid,                       # P3: +ve = paid
                  "funding_paid_pct": fund_paid / cfg.initial_capital * 100,
                  # P3: gross is BEFORE fees and funding (pnl + fees + funding)
                  "gross_return_pct": float((trades.pnl + trades.fees
                                             + (trades.funding if "funding" in trades else 0.0)
                                             ).sum() / cfg.initial_capital * 100),
                  "avg_bars_in_trade": float(trades.bars.mean()),
                  "exit_reasons": trades.reason.value_counts().to_dict()})
    return m


def backtest(df: pd.DataFrame, sig: pd.DataFrame, cfg: BacktestConfig,
             bounds: Optional[tuple[int, int]] = None) -> BacktestResult:
    n, idx = len(df), df.index
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    buy, sell = sig["buy"].to_numpy(bool), sig["sell"].to_numpy(bool)
    exl, exs = sig["exit_long"].to_numpy(bool), sig["exit_short"].to_numpy(bool)
    sl_d, tp_d, mh = sig["sl_dist"].to_numpy(float), sig["tp_dist"].to_numpy(float), int(sig["max_hold"].iloc[0])
    if bounds is not None:
        i0, i1 = bounds
    else:
        i0 = int(idx.searchsorted(pd.Timestamp(cfg.start, tz="UTC"), side="left")) if cfg.start else 0
        i1 = (int(idx.searchsorted(pd.Timestamp(cfg.end, tz="UTC"), side="right")) - 1) if cfg.end else n - 1
    i0, i1 = max(i0, 0), min(i1, n - 1)
    fee, slip = cfg.fee_bps / 1e4, cfg.slippage_bps / 1e4

    cash, pos, qty, entry, sl, tp = cfg.initial_capital, 0, 0.0, np.nan, np.nan, np.nan
    entry_i, entry_fee, risk_amt, pending, exposure = -1, 0.0, np.nan, None, 0
    trades, equity = [], np.full(n, np.nan)

    # P1/P2 — funding. The pack's attach_funding() carries the last known rate FORWARD onto
    # every bar (right for S07's z-score, WRONG for billing). Billing is driven by the
    # `funding_event_rate` column built by attach_funding_events() from the RAW settlement
    # timestamps: non-zero only on the bar that CONTAINS the settlement. A settlement at T
    # is charged to the position HELD AT T: funding is applied BEFORE the fill at that open
    # (so a position opened at T does not pay; one closed at T does), marked at the open.
    has_evt = "funding_event_rate" in df.columns
    if cfg.charge_funding and "funding_rate" in df.columns and not has_evt:
        raise FundingConfigError(
            "funding_rate is attached but funding_event_rate is not: funding would NOT be charged. "
            "Call attach_funding_events(df, funding_series), or set BacktestConfig(charge_funding=False).")
    if cfg.require_funding and not (cfg.charge_funding and has_evt):
        raise FundingConfigError("require_funding=True but no funding_event_rate is available to charge.")
    funding_on = bool(cfg.charge_funding and has_evt)
    if cfg.charge_funding and not has_evt:
        warnings.warn("No funding data in the dataframe: funding is NOT charged (funding_charged=False).",
                      stacklevel=2)
    fund = (df["funding_event_rate"].fillna(0.0).to_numpy(float) * float(cfg.funding_mult)
            if funding_on else np.zeros(n))
    fund_acc = 0.0

    def close_pos(px, i, reason):
        nonlocal cash, pos, qty, fund_acc
        xf = qty * px * fee
        gross = pos * qty * (px - entry)
        pnl = gross - xf - entry_fee + fund_acc      # P2: funding is part of the trade
        cash += gross - xf
        trades.append({"entry_time": idx[entry_i], "exit_time": idx[i], "dir": pos, "entry": entry, "exit": px,
                       "qty": qty, "pnl": pnl, "pnl_pct": pnl / max(qty * entry, 1e-12),
                       "R": pnl / risk_amt if risk_amt > 0 else np.nan, "bars": i - entry_i,
                       "fees": entry_fee + xf, "reason": reason,
                       "funding": -fund_acc})            # P3: +ve = paid, -ve = received
        pos, qty = 0, 0.0
        fund_acc = 0.0

    for i in range(i0, i1 + 1):
        if pos != 0 and fund[i] != 0:                  # 0) P2: FUNDING at the settlement
            fc = pos * qty * o[i] * fund[i]            # long pays a positive rate; short receives; marked at the open
            cash -= fc
            fund_acc -= fc
        if pending is not None:                                   # 1) execute at the open
            if pending["kind"] in ("close", "reverse") and pos != 0:
                close_pos(o[i] * (1.0 - slip * pos), i, pending.get("why", "opposite_signal"))
            if pending["kind"] in ("open", "reverse"):
                d = pending["dir"]
                px = o[i] * (1.0 + slip * d)
                entry_fee = pending["qty"] * px * fee
                cash -= entry_fee
                pos, qty, entry, entry_i = d, pending["qty"], px, i
                fund_acc = 0.0                        # P2: new trade starts at 0 funding
                sl = px - d * pending["sl_d"]
                tp = px + d * pending["tp_d"] if np.isfinite(pending["tp_d"]) else np.nan
                risk_amt = pending["qty"] * pending["sl_d"]
            pending = None

        if pos != 0:                                              # 2) intrabar SL / TP
            has_tp = np.isfinite(tp)
            if pos == 1:
                sl_open, tp_open = o[i] <= sl, has_tp and o[i] >= tp
                sl_in, tp_in = l[i] <= sl, has_tp and h[i] >= tp
            else:
                sl_open, tp_open = o[i] >= sl, has_tp and o[i] <= tp
                sl_in, tp_in = h[i] >= sl, has_tp and l[i] <= tp
            kind = fill = None
            if sl_open:
                kind, fill = "sl", o[i]
            elif tp_open:
                kind, fill = "tp", o[i]
            elif sl_in and tp_in:
                kind = "sl" if cfg.both_hit_rule == "sl_first" else "tp"
                fill = sl if kind == "sl" else tp
            elif sl_in:
                kind, fill = "sl", sl
            elif tp_in:
                kind, fill = "tp", tp
            if kind == "sl":
                close_pos(fill * (1.0 - slip * pos), i, "sl")
            elif kind == "tp":
                close_pos(fill, i, "tp")

        equity[i] = cash + (pos * qty * (c[i] - entry) if pos != 0 else 0.0)   # 3) mark to market
        exposure += pos != 0

        if i < i1:                                                # 4) decisions at this close
            want = 1 if buy[i] else (-1 if sell[i] else 0)
            new = None
            if want != 0 and np.isfinite(sl_d[i]) and sl_d[i] > 0 and (cfg.allow_long if want == 1 else cfg.allow_short):
                eq = equity[i]
                q = (eq * cfg.risk_pct / 100.0 / sl_d[i]) if cfg.sizing_mode == "stop_risk" else eq * cfg.pct_equity / 100.0 / c[i]
                q = min(q, eq * cfg.max_leverage / c[i])
                if q > 0:
                    new = {"kind": "open", "dir": want, "qty": q, "sl_d": sl_d[i],
                           "tp_d": tp_d[i] if np.isfinite(tp_d[i]) else np.nan}
            if pos == 0:
                pending = new
            else:
                why = None
                if (pos == 1 and exl[i]) or (pos == -1 and exs[i]):
                    why = "exit_signal"
                elif mh > 0 and i - entry_i + 1 >= mh:
                    why = "time_stop"
                if why is not None:
                    pending = {"kind": "close", "why": why}
                    if new is not None and new["dir"] == -pos and cfg.opposite_signal == "reverse":
                        new.update(kind="reverse", why=why)
                        pending = new
                elif want == -pos and cfg.opposite_signal != "ignore":
                    if cfg.opposite_signal == "reverse" and new is not None:
                        new["kind"] = "reverse"
                        pending = new
                    else:
                        pending = {"kind": "close", "why": "opposite_signal"}

    if pos != 0:
        close_pos(c[i1] * (1.0 - slip * pos), i1, "end_of_data")
        equity[i1] = cash
    eq_s = pd.Series(equity, index=idx).ffill()
    cols = ["entry_time", "exit_time", "dir", "entry", "exit", "qty", "pnl", "pnl_pct", "R", "bars", "fees", "reason", "funding"]
    tdf = pd.DataFrame(trades, columns=cols)
    bpy = 365.0 * 86400.0 / base_seconds(df)
    bh_fund = float(np.sum(fund[i0 + 1:i1 + 1] * o[i0 + 1:i1 + 1]) / c[i0]) if funding_on and i1 > i0 else 0.0
    return BacktestResult(_metrics(eq_s, tdf, df, cfg, i0, i1, exposure, bpy, bh_fund, funding_on), tdf, eq_s, sig)


# ═════════════════════════════════ research helpers ═════════════════════════════════
def make_signals(df: pd.DataFrame, strategy_id: str, **overrides) -> pd.DataFrame:
    return STRATEGIES[strategy_id].fn(df, **overrides)


def concentration(tr: pd.DataFrame, init: float = 10_000.0) -> dict:
    """How much of the result is carried by the few best trades? (P4)

    A strategy whose best 5 trades exceed 100% of total PnL has a handful of lucky positions,
    not an edge. `conc_net_without_top5_pct` is the return WITHOUT them. The top-decile view
    scales with trade count (top 5 means different things at 30 and 3,000 trades).
    CAUTION: one-sided trimming penalises right-tail strategies (S02/S10) by construction;
    read it next to expectancy_ci(), not instead of it. Share is NaN when total PnL <= 0.
    """
    empty = {"conc_total_pnl": 0.0, "conc_top5_pnl": 0.0, "conc_top5_share": float("nan"),
             "conc_top5_share_pct": float("nan"), "conc_net_pct": 0.0,
             "conc_net_without_top5_pct": float("nan"), "conc_passes": False,
             "conc_topdecile_share": float("nan"), "conc_net_without_topdecile_pct": float("nan"),
             "conc_passes_decile": False}
    if tr is None or not len(tr):
        return empty
    srt = tr.sort_values("pnl", ascending=False)
    total = float(srt.pnl.sum())
    top5 = float(srt.head(5).pnl.sum())
    k10 = max(1, int(math.ceil(0.10 * len(srt))))
    topd = float(srt.head(k10).pnl.sum())
    share = (top5 / total) if total > 0 else float("nan")
    share_d = (topd / total) if total > 0 else float("nan")
    without = (total - top5) / init * 100.0
    without_d = (total - topd) / init * 100.0
    return {"conc_total_pnl": total, "conc_top5_pnl": top5, "conc_top5_share": share,
            "conc_top5_share_pct": share * 100.0 if np.isfinite(share) else float("nan"),
            "conc_net_pct": total / init * 100.0, "conc_net_without_top5_pct": without,
            "conc_passes": bool(np.isfinite(without) and without > 0),
            "conc_topdecile_share": share_d, "conc_net_without_topdecile_pct": without_d,
            "conc_passes_decile": bool(np.isfinite(without_d) and without_d > 0)}


def expectancy_ci(trades: pd.DataFrame, n_boot: int = 2000, block: int = 5, seed: int = 0,
                  col: str = "R") -> dict:
    """P9: circular block bootstrap of mean trade expectancy (default: R multiples).

    Trades are serially dependent (regime clustering), so the iid t-stat is optimistic;
    the block bootstrap CI is the honest one. `p_mean_le_0` = share of resamples with mean <= 0.
    """
    nan = float("nan")
    r = trades[col].dropna().to_numpy(float) if trades is not None and len(trades) else np.array([])
    n = len(r)
    if n < 2:
        return {"n": n, "mean": nan, "t_stat_iid": nan, "ci_lo": nan, "ci_hi": nan, "p_mean_le_0": nan}
    block = max(1, min(int(block), n))
    nb = int(math.ceil(n / block))
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(n_boot, nb))
    idxs = ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(n_boot, -1)[:, :n]
    means = r[idxs].mean(axis=1)
    sd = r.std(ddof=1)
    return {"n": n, "mean": float(r.mean()), "t_stat_iid": float(r.mean() / (sd / math.sqrt(n))) if sd > 0 else nan,
            "ci_lo": float(np.percentile(means, 2.5)), "ci_hi": float(np.percentile(means, 97.5)),
            "p_mean_le_0": float((means <= 0).mean())}


def probabilistic_sharpe(sr: float, n: int, skew: float, kurt: float, sr_bench: float = 0.0) -> float:
    """Bailey & Lopez de Prado PSR. sr is PER-PERIOD (not annualised); kurt is raw (normal = 3)."""
    d = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if n < 2 or d <= 0:
        return float("nan")
    return NormalDist().cdf((sr - sr_bench) * math.sqrt(n - 1) / math.sqrt(d))


def deflated_sharpe(returns, trial_sharpes) -> dict:
    """P9: Deflated Sharpe Ratio. `returns` = per-bar returns of the SELECTED configuration,
    `trial_sharpes` = per-bar (non-annualised) Sharpes of ALL configurations that were tried.
    DSR = PSR against the Sharpe you would expect from the best of N pure-noise trials."""
    r = pd.Series(np.asarray(returns, float)).dropna()
    ts = np.asarray([x for x in trial_sharpes if np.isfinite(x)], float)
    n = len(r)
    sd = r.std(ddof=1)
    if n < 3 or not sd > 0:
        return {"sr": float("nan"), "sr0": float("nan"), "dsr": float("nan"), "n_trials": int(len(ts))}
    sr = float(r.mean() / sd)
    skew, kurt = float(r.skew()), float(r.kurt() + 3.0)
    N = len(ts)
    if N >= 2 and ts.var(ddof=1) > 0:
        g, nd = 0.5772156649015329, NormalDist()
        sr0 = math.sqrt(float(ts.var(ddof=1))) * ((1 - g) * nd.inv_cdf(1 - 1.0 / N)
                                                  + g * nd.inv_cdf(1 - 1.0 / (N * math.e)))
    else:
        sr0 = 0.0
    return {"sr": sr, "sr0": sr0, "dsr": probabilistic_sharpe(sr, n, skew, kurt, sr0), "n_trials": int(N)}


def pbo_cscv(perf, n_splits: int = 8) -> dict:
    """P9: Probability of Backtest Overfitting via CSCV. `perf` = T x N matrix of per-bar returns
    (one column per configuration). For every split of the T bars into S blocks, pick the best
    in-sample configuration and rank it out-of-sample. PBO = P(logit(rank) <= 0)."""
    M = np.asarray(perf, float)
    if M.ndim != 2 or M.shape[1] < 2:
        raise ValueError("pbo_cscv needs a T x N matrix with N >= 2 configurations")
    T, N = M.shape
    S = int(n_splits)
    if S % 2 or S < 4 or T < S * 2:
        raise ValueError("n_splits must be even, >= 4, and T >= 2*n_splits")

    def sharpe(x):
        sd = x.std(axis=0, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            s = x.mean(axis=0) / sd
        return np.where(sd > 0, s, -np.inf)

    blocks = np.array_split(np.arange(T), S)
    logits = []
    for comb in itertools.combinations(range(S), S // 2):
        tr_idx = np.concatenate([blocks[b] for b in comb])
        te_idx = np.concatenate([blocks[b] for b in range(S) if b not in comb])
        best = int(np.argmax(sharpe(M[tr_idx])))
        s_te = sharpe(M[te_idx])
        rank = float((s_te < s_te[best]).sum() + 1)                  # 1 = worst, N = best
        w = rank / (N + 1.0)
        logits.append(math.log(w / (1.0 - w)))
    lg = np.asarray(logits)
    return {"pbo": float((lg <= 0).mean()), "n_combos": int(len(lg)), "mean_logit": float(lg.mean()),
            "n_configs": int(N)}


def trial_returns(df, strategy_id, cfg, grid=None, max_combos=40, bounds=None) -> pd.DataFrame:
    """P9: per-bar equity returns for EVERY grid point (the 'trials' PBO/DSR need)."""
    spec = STRATEGIES[strategy_id]
    grid = grid or spec.grid
    keys = list(grid)
    combos = list(itertools.product(*[grid[k] for k in keys]))
    if len(combos) > max_combos:
        raise ValueError(f"{len(combos)} combos > max_combos={max_combos}: shrink the grid")
    cols = {}
    for cmb in combos:
        params = dict(zip(keys, cmb))
        eq = backtest(df, spec.fn(df, **params), cfg, bounds=bounds).equity.dropna()
        cols[str(params)] = eq.pct_change().fillna(0.0)
    return pd.concat(cols, axis=1).fillna(0.0)


def overfit_report(df, strategy_id, cfg, grid=None, n_splits: int = 8, max_combos: int = 40) -> dict:
    """P9: PBO (CSCV) and Deflated Sharpe of the best-in-sample configuration over the whole grid."""
    R = trial_returns(df, strategy_id, cfg, grid, max_combos)
    R = R.loc[:, R.std(ddof=1) > 0]
    if R.shape[1] < 2:
        return {"status": "need >= 2 active configurations", "n_configs": int(R.shape[1])}
    sh = R.mean() / R.std(ddof=1)
    best = sh.idxmax()
    out = {"status": "ok", "best_params": best, "n_configs": int(R.shape[1]),
           "best_sharpe_per_bar": float(sh[best])}
    out.update(deflated_sharpe(R[best], sh.to_numpy()))
    out.update(pbo_cscv(R, n_splits))
    return out


def evaluate_all(df: pd.DataFrame, cfg: BacktestConfig, ids: Optional[list[str]] = None) -> pd.DataFrame:
    rows = []
    for sid in ids or list(STRATEGIES):
        spec = STRATEGIES[sid]
        try:
            sig = spec.fn(df)
            r = backtest(df, sig, cfg)          # FundingConfigError is NOT caught on purpose
        except MissingData as e:
            rows.append({"id": sid, "name": spec.name, "status": f"SKIPPED: {e}"})
            continue
        m = r.metrics
        fsrc = sig.attrs.get("meta", {}).get("flow_source", "n/a")
        if fsrc == "candle_proxy":
            warnings.warn(f"{sid}: no taker-buy column -> running on the candle-colour PROXY, not true taker flow",
                          stacklevel=2)
        rows.append({"id": sid, "name": spec.name, "status": "ok", "trades": m["n_trades"],
                     "net_%": m["net_return_pct"], "gross_%": m["gross_return_pct"], "buy_hold_%": m["buy_hold_return_pct"],
                     "excess_%": m["excess_vs_buy_hold_pct"], "maxDD_%": m["max_drawdown_pct"],
                     "win_%": m["win_rate_pct"], "PF": m["profit_factor"], "exp_R": m["expectancy_R"],
                     "sharpe": m["sharpe_annualised"], "exposure_%": m["exposure_pct"],
                     # P6/P8: honest benchmark + provenance of what was actually modelled
                     "bh_net_%": m["buy_hold_net_pct"], "excess_net_%": m["excess_vs_bh_net_pct"],
                     "funding_charged": m["funding_charged"], "flow_source": fsrc,
                     "funding_paid_pct": m.get("funding_paid_pct", 0.0),
                     **concentration(r.trades, cfg.initial_capital)})
    return pd.DataFrame(rows)


def cost_sensitivity(df, strategy_id, cfg, fee_grid=(0.0, 2.0, 5.0, 8.0), slip_grid=(0.0, 2.0, 5.0), **kw) -> pd.DataFrame:
    sig = make_signals(df, strategy_id, **kw)
    rows = []
    for f, s in itertools.product(fee_grid, slip_grid):
        m = backtest(df, sig, replace(cfg, fee_bps=f, slippage_bps=s)).metrics
        rows.append({"fee_bps": f, "slippage_bps": s, "net_%": m["net_return_pct"], "PF": m["profit_factor"], "trades": m["n_trades"]})
    return pd.DataFrame(rows)


def funding_sensitivity(df, strategy_id, cfg, mults=(0.0, 1.0, 2.0), **kw) -> pd.DataFrame:
    """P9: how much of the result is funding? 0x = no funding, 1x = realised, 2x = stress.
    Funding regimes differ by an order of magnitude between years; a strategy that only
    survives at 0x is a funding-free fantasy."""
    sig = make_signals(df, strategy_id, **kw)
    rows = []
    for mult in mults:
        m = backtest(df, sig, replace(cfg, funding_mult=float(mult))).metrics
        rows.append({"funding_mult": mult, "net_%": m["net_return_pct"], "gross_%": m["gross_return_pct"],
                     "funding_paid_pct": m["funding_paid_pct"], "PF": m["profit_factor"], "trades": m["n_trades"]})
    return pd.DataFrame(rows)


def walk_forward(df, strategy_id, cfg, train_bars, test_bars, grid=None, objective="sharpe_annualised",
                 min_trades=20, max_combos=40, select="argmax") -> dict:
    """Pick a grid point on each train window, then trade it untouched on the next test window.
    Signals are causal -> computed once per combo over the full series (no leakage).

    select="argmax"   best train objective (original behaviour).
    select="plateau"  (P9) best MEAN objective over the point and its grid neighbours (one step in one
                      parameter): rewards parameter regions, not lucky isolated peaks."""
    if select not in ("argmax", "plateau"):
        raise ValueError("select must be 'argmax' or 'plateau'")
    spec = STRATEGIES[strategy_id]
    grid = grid or spec.grid
    keys = list(grid)
    levels = [list(grid[k]) for k in keys]
    combos = list(itertools.product(*levels))
    if len(combos) > max_combos:
        raise ValueError(f"{len(combos)} combos > max_combos={max_combos}: shrink the grid")
    sigs = {cmb: spec.fn(df, **dict(zip(keys, cmb))) for cmb in combos}
    where = {cmb: tuple(levels[d].index(cmb[d]) for d in range(len(keys))) for cmb in combos}
    at = {p: cmb for cmb, p in where.items()}

    def neighbours(cmb):
        p = where[cmb]
        for d in range(len(keys)):
            for st in (-1, 1):
                q = p[:d] + (p[d] + st,) + p[d + 1:]
                if q in at:
                    yield at[q]

    folds, start, i = [], 0, 0
    while start + train_bars + test_bars <= len(df):
        tr, te = (start, start + train_bars - 1), (start + train_bars, start + train_bars + test_bars - 1)
        ms = {cmb: backtest(df, sigs[cmb], cfg, bounds=tr).metrics for cmb in combos}
        vals = {}
        for cmb, m in ms.items():
            v = m.get(objective, float("nan"))
            vals[cmb] = v if (m["n_trades"] >= min_trades and np.isfinite(v)) else float("nan")
        if select == "plateau":
            score = {cmb: float(np.nanmean([v] + [vals[q] for q in neighbours(cmb)]))
                     for cmb, v in vals.items() if np.isfinite(v)}
        else:
            score = {cmb: v for cmb, v in vals.items() if np.isfinite(v)}
        best, bv = None, -np.inf
        for cmb in combos:
            sc = score.get(cmb)
            if sc is not None and sc > bv:
                best, bv = cmb, sc
        if best is None:
            folds.append({"fold": i, "params": None, "test_net_%": 0.0, "test_trades": 0})
        else:
            bm = ms[best]
            mt = backtest(df, sigs[best], cfg, bounds=te).metrics
            folds.append({"fold": i, "params": dict(zip(keys, best)), "train_obj": vals[best], "train_score": bv,
                          "train_net_%": bm["net_return_pct"],
                          "test_net_%": mt["net_return_pct"], "test_buy_hold_%": mt["buy_hold_return_pct"],
                          "test_trades": mt["n_trades"], "test_PF": mt["profit_factor"],
                          "test_funding_paid_%": mt["funding_paid_pct"]})
        i, start = i + 1, start + test_bars
    tab = pd.DataFrame(folds)
    oos = float(np.prod(1 + tab["test_net_%"].fillna(0) / 100.0) - 1) * 100 if len(tab) else float("nan")
    mtr = float(tab["train_net_%"].mean()) if "train_net_%" in tab else float("nan")
    mte = float(tab["test_net_%"].mean()) if len(tab) else float("nan")
    return {"folds": tab, "summary": {"folds": len(tab), "oos_compounded_net_%": oos,
            "folds_profitable": int((tab["test_net_%"] > 0).sum()) if len(tab) else 0,
            "mean_train_net_%": mtr, "mean_test_net_%": mte,
            "oos_over_is": (mte / mtr) if (np.isfinite(mtr) and mtr != 0 and np.isfinite(mte)) else float("nan"),
            "select": select}}


def strategy_card(strategy_id: str) -> str:
    s = STRATEGIES[strategy_id]
    return (f"{s.id} {s.name}\n  thesis: {s.thesis}\n  requires: {s.requires or 'OHLCV (+ taker_buy recommended)'}\n"
            f"  timeframes: {s.timeframes}\n  WHY THIS COULD STOP WORKING: {s.failure_mode}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--funding", help="CSV with columns time,rate (time = settlement, UTC; rate = decimal)")
    ap.add_argument("--oi", help="CSV with columns time,open_interest (UTC)")
    ap.add_argument("--only", help="comma list, e.g. S01,S02")
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--slippage-bps", type=float, default=2.0)
    ap.add_argument("--funding-mult", type=float, default=1.0, help="scale settled funding (0 off, 2 stress)")
    ap.add_argument("--no-funding-charge", action="store_true", help="explicitly run WITHOUT charging funding")
    ap.add_argument("--require-funding", action="store_true", help="fail if no funding events can be charged")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--cards", action="store_true", help="print each strategy's thesis and failure mode")
    a = ap.parse_args()
    df = load_ohlcv(a.data)
    dq = data_quality(df)
    print(f"data: {dq}")
    if dq["gaps"]:
        print(f"WARNING: {dq['gaps']} gaps / {dq['missing_bars']} missing bars: rolling(n) lookbacks are stretched.")
    if not dq["taker_buy_present"]:
        print("WARNING: no taker-buy column -> candle-colour PROXY flow, not true taker flow.")
    if a.funding:
        f = pd.read_csv(a.funding)
        fs = pd.Series(f.iloc[:, 1].to_numpy(), index=pd.to_datetime(f.iloc[:, 0], utc=True))
        df = attach_funding(df, fs)
        df = attach_funding_events(df, fs)          # the billing schedule: without it nothing is charged
    if a.oi:
        o = pd.read_csv(a.oi)
        df = attach_oi(df, pd.Series(o.iloc[:, 1].to_numpy(), index=pd.to_datetime(o.iloc[:, 0], utc=True)))
    cfg = BacktestConfig(fee_bps=a.fee_bps, slippage_bps=a.slippage_bps, start=a.start, end=a.end,
                         charge_funding=not a.no_funding_charge, require_funding=a.require_funding,
                         funding_mult=a.funding_mult)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
    ids = a.only.split(",") if a.only else None
    print(evaluate_all(df, cfg, ids).to_string(index=False))
    print("\nNote: ten strategies ranked on one sample = multiple testing. Confirm with walk_forward(), "
          "overfit_report(), several pairs, and costs AND funding.")
    if a.cards:
        print()
        for sid in ids or STRATEGIES:
            print(strategy_card(sid) + "\n")


if __name__ == "__main__":
    main()
