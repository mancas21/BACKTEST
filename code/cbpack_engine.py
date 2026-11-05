#!/usr/bin/env python3
"""
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

────────────────────────────────── EXECUTION MODEL ──────────────────────────────────
• Signal at bar i close -> order at bar i+1 open (+ adverse slippage); fee per side.
• SL/TP distances are frozen at signal time (`sl_dist`, `tp_dist`, price units).
• Intrabar SL/TP; both inside one bar -> SL first (conservative, configurable). Gap through a level fills at the open.
• Time stop: `max_hold` bars including the entry bar. Exit signals execute at the next open.
• Sizing: fixed % equity or stop-risk (risk % of equity / stop distance), capped by max leverage.
• No funding payments, no liquidation engine, no partial fills (state this in any report you produce).

────────────────────────────────── HOW TO USE ──────────────────────────────────
  df = load_ohlcv("SOLUSDT_15m.csv")                    # UTC bar-open index; Binance klines OK
  df = attach_funding(df, funding_series)               # optional (S07)
  df = attach_oi(df, oi_series, lag_bars=1)             # optional (S08)
  table = evaluate_all(df, BacktestConfig())            # all strategies vs buy&hold, with costs
  wf = walk_forward(df, "S02", BacktestConfig(), train_bars=8000, test_bars=2000)
CLI:  python strategy_pack.py --data SOLUSDT_15m.csv --funding funding.csv --oi oi.csv

IMPORTANT: ranking ten strategies on one sample is itself a multiple-testing exercise. Require
out-of-sample (walk_forward), several pairs/periods, and a positive result AFTER costs before believing any row.

Requirements: Python 3.10+, numpy, pandas.
"""
from __future__ import annotations

import argparse
import itertools
import math
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

import numpy as np
import pandas as pd


class MissingData(Exception):
    """Raised when a strategy needs a column the dataset does not have."""


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


# ═════════════════════════════════ data helpers ═════════════════════════════════
_ALIASES = {"taker_buy_base": "taker_buy", "taker_buy_volume": "taker_buy", "taker_buy_base_volume": "taker_buy",
            "takerbuybase": "taker_buy", "count": "num_trades", "trades": "num_trades",
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
        df.index = (pd.to_datetime(ts, unit="ms" if ts.iloc[0] > 1e11 else "s", utc=True)
                    if pd.api.types.is_numeric_dtype(ts) else pd.to_datetime(ts, utc=True))
    return prepare(df)


def base_seconds(df: pd.DataFrame) -> int:
    return int(round(df.index.to_series().diff().dropna().dt.total_seconds().median()))


def _asof_to_bars(df: pd.DataFrame, s: pd.Series) -> pd.Series:
    """Value of series `s` (index = time the value became KNOWN) as of each bar's CLOSE time."""
    s = s.copy()
    s.index = pd.to_datetime(s.index, utc=True)
    s = s[~s.index.duplicated(keep="last")].sort_index().astype(float)
    close_t = df.index + pd.Timedelta(seconds=base_seconds(df))
    left = pd.DataFrame({"t": close_t})
    right = pd.DataFrame({"t": s.index, "v": s.to_numpy()})
    out = pd.merge_asof(left, right, on="t", direction="backward")["v"]
    return pd.Series(out.to_numpy(), index=df.index)


def attach_funding(df: pd.DataFrame, funding: pd.Series) -> pd.DataFrame:
    """funding: Series of funding RATES indexed by settlement time (UTC). Known at settlement time."""
    out = df.copy()
    out["funding_rate"] = _asof_to_bars(df, funding)
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


def _metrics(eq, trades, df, cfg, i0, i1, exposure, bpy) -> dict:
    e = eq.iloc[i0:i1 + 1]
    ret = e.pct_change().dropna()
    total = e.iloc[-1] / e.iloc[0] - 1.0 if len(e) > 1 else 0.0
    bh = df["close"].iloc[i1] / df["close"].iloc[i0] - 1.0
    sd = ret.std(ddof=1)
    m = {"bars": int(i1 - i0 + 1), "n_trades": int(len(trades)), "net_return_pct": total * 100,
         "buy_hold_return_pct": bh * 100, "excess_vs_buy_hold_pct": (total - bh) * 100,
         "max_drawdown_pct": float((e / e.cummax() - 1.0).min() * 100) if len(e) > 1 else 0.0,
         "sharpe_annualised": float(ret.mean() / sd * math.sqrt(bpy)) if sd and sd > 0 else float("nan"),
         "exposure_pct": exposure / max(i1 - i0 + 1, 1) * 100,
         "win_rate_pct": float("nan"), "profit_factor": float("nan"), "expectancy_R": float("nan"),
         "avg_trade_pct": float("nan"), "fees_paid": 0.0, "gross_return_pct": total * 100, "exit_reasons": {}}
    if len(trades):
        w, l = trades[trades.pnl > 0], trades[trades.pnl <= 0]
        gl = -l.pnl.sum()
        m.update({"win_rate_pct": len(w) / len(trades) * 100,
                  "profit_factor": float(w.pnl.sum() / gl) if gl > 0 else float("inf"),
                  "expectancy_R": float(trades.R.mean()), "avg_trade_pct": float(trades.pnl_pct.mean() * 100),
                  "fees_paid": float(trades.fees.sum()),
                  "gross_return_pct": float((trades.pnl + trades.fees).sum() / cfg.initial_capital * 100),
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

    def close_pos(px, i, reason):
        nonlocal cash, pos, qty
        xf = qty * px * fee
        gross = pos * qty * (px - entry)
        pnl = gross - xf - entry_fee
        cash += gross - xf
        trades.append({"entry_time": idx[entry_i], "exit_time": idx[i], "dir": pos, "entry": entry, "exit": px,
                       "qty": qty, "pnl": pnl, "pnl_pct": pnl / max(qty * entry, 1e-12),
                       "R": pnl / risk_amt if risk_amt > 0 else np.nan, "bars": i - entry_i,
                       "fees": entry_fee + xf, "reason": reason})
        pos, qty = 0, 0.0

    for i in range(i0, i1 + 1):
        if pending is not None:                                   # 1) execute at the open
            if pending["kind"] in ("close", "reverse") and pos != 0:
                close_pos(o[i] * (1.0 - slip * pos), i, pending.get("why", "opposite_signal"))
            if pending["kind"] in ("open", "reverse"):
                d = pending["dir"]
                px = o[i] * (1.0 + slip * d)
                entry_fee = pending["qty"] * px * fee
                cash -= entry_fee
                pos, qty, entry, entry_i = d, pending["qty"], px, i
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
    cols = ["entry_time", "exit_time", "dir", "entry", "exit", "qty", "pnl", "pnl_pct", "R", "bars", "fees", "reason"]
    tdf = pd.DataFrame(trades, columns=cols)
    bpy = 365.0 * 86400.0 / base_seconds(df)
    return BacktestResult(_metrics(eq_s, tdf, df, cfg, i0, i1, exposure, bpy), tdf, eq_s, sig)


# ═════════════════════════════════ research helpers ═════════════════════════════════
def make_signals(df: pd.DataFrame, strategy_id: str, **overrides) -> pd.DataFrame:
    return STRATEGIES[strategy_id].fn(df, **overrides)


def evaluate_all(df: pd.DataFrame, cfg: BacktestConfig, ids: Optional[list[str]] = None) -> pd.DataFrame:
    rows = []
    for sid in ids or list(STRATEGIES):
        spec = STRATEGIES[sid]
        try:
            r = backtest(df, spec.fn(df), cfg)
        except MissingData as e:
            rows.append({"id": sid, "name": spec.name, "status": f"SKIPPED: {e}"})
            continue
        m = r.metrics
        rows.append({"id": sid, "name": spec.name, "status": "ok", "trades": m["n_trades"],
                     "net_%": m["net_return_pct"], "gross_%": m["gross_return_pct"], "buy_hold_%": m["buy_hold_return_pct"],
                     "excess_%": m["excess_vs_buy_hold_pct"], "maxDD_%": m["max_drawdown_pct"],
                     "win_%": m["win_rate_pct"], "PF": m["profit_factor"], "exp_R": m["expectancy_R"],
                     "sharpe": m["sharpe_annualised"], "exposure_%": m["exposure_pct"]})
    return pd.DataFrame(rows)


def cost_sensitivity(df, strategy_id, cfg, fee_grid=(0.0, 2.0, 5.0, 8.0), slip_grid=(0.0, 2.0, 5.0), **kw) -> pd.DataFrame:
    sig = make_signals(df, strategy_id, **kw)
    rows = []
    for f, s in itertools.product(fee_grid, slip_grid):
        m = backtest(df, sig, replace(cfg, fee_bps=f, slippage_bps=s)).metrics
        rows.append({"fee_bps": f, "slippage_bps": s, "net_%": m["net_return_pct"], "PF": m["profit_factor"], "trades": m["n_trades"]})
    return pd.DataFrame(rows)


def walk_forward(df, strategy_id, cfg, train_bars, test_bars, grid=None, objective="sharpe_annualised",
                 min_trades=20, max_combos=40) -> dict:
    """Pick the best grid point on each train window, then trade it untouched on the next test window.
    Signals are causal -> computed once per combo over the full series (no leakage)."""
    spec = STRATEGIES[strategy_id]
    grid = grid or spec.grid
    keys = list(grid)
    combos = list(itertools.product(*[grid[k] for k in keys]))
    if len(combos) > max_combos:
        raise ValueError(f"{len(combos)} combos > max_combos={max_combos}: shrink the grid")
    sigs = {cmb: spec.fn(df, **dict(zip(keys, cmb))) for cmb in combos}
    folds, start, i = [], 0, 0
    while start + train_bars + test_bars <= len(df):
        tr, te = (start, start + train_bars - 1), (start + train_bars, start + train_bars + test_bars - 1)
        best, bv, bm = None, -np.inf, None
        for cmb in combos:
            m = backtest(df, sigs[cmb], cfg, bounds=tr).metrics
            v = m.get(objective, float("nan"))
            if m["n_trades"] >= min_trades and np.isfinite(v) and v > bv:
                best, bv, bm = cmb, v, m
        if best is None:
            folds.append({"fold": i, "params": None, "test_net_%": 0.0, "test_trades": 0})
        else:
            mt = backtest(df, sigs[best], cfg, bounds=te).metrics
            folds.append({"fold": i, "params": dict(zip(keys, best)), "train_obj": bv, "train_net_%": bm["net_return_pct"],
                          "test_net_%": mt["net_return_pct"], "test_buy_hold_%": mt["buy_hold_return_pct"],
                          "test_trades": mt["n_trades"], "test_PF": mt["profit_factor"]})
        i, start = i + 1, start + test_bars
    tab = pd.DataFrame(folds)
    oos = float(np.prod(1 + tab["test_net_%"].fillna(0) / 100.0) - 1) * 100 if len(tab) else float("nan")
    return {"folds": tab, "summary": {"folds": len(tab), "oos_compounded_net_%": oos,
            "folds_profitable": int((tab["test_net_%"] > 0).sum()) if len(tab) else 0,
            "mean_train_net_%": float(tab["train_net_%"].mean()) if "train_net_%" in tab else float("nan"),
            "mean_test_net_%": float(tab["test_net_%"].mean()) if len(tab) else float("nan")}}


def strategy_card(strategy_id: str) -> str:
    s = STRATEGIES[strategy_id]
    return (f"{s.id} {s.name}\n  thesis: {s.thesis}\n  requires: {s.requires or 'OHLCV (+ taker_buy recommended)'}\n"
            f"  timeframes: {s.timeframes}\n  WHY THIS COULD STOP WORKING: {s.failure_mode}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--funding", help="CSV with columns time,rate (time = settlement, UTC)")
    ap.add_argument("--oi", help="CSV with columns time,open_interest (UTC)")
    ap.add_argument("--only", help="comma list, e.g. S01,S02")
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--slippage-bps", type=float, default=2.0)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--cards", action="store_true", help="print each strategy's thesis and failure mode")
    a = ap.parse_args()
    df = load_ohlcv(a.data)
    if a.funding:
        f = pd.read_csv(a.funding)
        df = attach_funding(df, pd.Series(f.iloc[:, 1].to_numpy(), index=pd.to_datetime(f.iloc[:, 0], utc=True)))
    if a.oi:
        o = pd.read_csv(a.oi)
        df = attach_oi(df, pd.Series(o.iloc[:, 1].to_numpy(), index=pd.to_datetime(o.iloc[:, 0], utc=True)))
    cfg = BacktestConfig(fee_bps=a.fee_bps, slippage_bps=a.slippage_bps, start=a.start, end=a.end)
    pd.set_option("display.width", 220)
    pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
    ids = a.only.split(",") if a.only else None
    print(evaluate_all(df, cfg, ids).to_string(index=False))
    print("\nNote: ten strategies ranked on one sample = multiple testing. Confirm with walk_forward(), several pairs, and costs.")
    if a.cards:
        print()
        for sid in ids or STRATEGIES:
            print(strategy_card(sid) + "\n")


if __name__ == "__main__":
    main()
