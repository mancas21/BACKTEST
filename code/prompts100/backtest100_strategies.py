#!/usr/bin/env python3
"""
100-Prompt Backtest Pack — Strategy Implementations
====================================================
Each strategy is a signal_fn(j, ctx) -> dict with keys:
  side: +1 (long), -1 (short), 0 (exit)
  stop_px: stop price (required when entering)
  tp_px: take profit price (optional)
Signal computed on close of bar j; fill at open of bar j+1.
"""

from __future__ import annotations
import math
import numpy as np
import pandas as pd
from backtest100_engine import (
    ema, sma, rsi, atr, bollinger, keltner, donchian, macd, adx,
    stochastic, williams_r, cci, vwap, supertrend, rolling_beta,
    rolling_corr, hull_ma, parabolic_sar, ultimate_oscillator, mfi,
    aroon, kama, vwma,
)

STRATEGIES = {}

def register(name):
    def decorator(fn):
        STRATEGIES[name] = fn
        return fn
    return decorator

# ============================================================================
# Helper: build indicator context once per strategy run
# ============================================================================
class LazyCtx(dict):
    """Dict-like context that computes indicator arrays on first access.

    Only the indicators a given strategy actually touches get built, which keeps
    full-history 5m runs from paying for parabolic SAR / Aroon / KAMA they never use.
    """

    def __init__(self, df):
        super().__init__()
        self._df = df
        self["close"] = df["close"].values
        self["high"] = df["high"].values
        self["low"] = df["low"].values
        self["open"] = df["open"].values
        self["volume"] = df["volume"].values
        self["timestamp"] = df["timestamp"].values
        ts = df["timestamp"]
        self["hour"] = ts.dt.hour.values
        # minute-of-day (0..1439), the convention the session strategies use
        self["minute"] = (ts.dt.hour * 60 + ts.dt.minute).values
        self["dayofweek"] = ts.dt.dayofweek.values
        self["day"] = ts.dt.day.values
        self["month"] = ts.dt.month.values
        self["month_end2"] = ((ts + pd.Timedelta(days=2)).dt.month != ts.dt.month).values
        self._builders = _make_builders(df)

    def __missing__(self, key):
        b = self._builders.get(key)
        if b is None:
            raise KeyError(key)
        v = b()
        self[key] = v
        return v

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default



def _session_arrays(df):
    """Per-bar session aggregates used by the session/time-of-day strategies."""
    ts = df["timestamp"]
    day = ts.dt.floor("D")
    day_v = day.values
    minute = (ts.dt.hour * 60 + ts.dt.minute).values
    dow = ts.dt.dayofweek.values
    n = len(df)
    out = {"minute": minute}

    day_s = pd.Series(day_v)

    def agg(start, end, col, how):
        m = (minute >= start) & (minute < end)
        if not m.any():
            return np.full(n, np.nan)
        s = df.loc[m].groupby(day_v[m])[col].agg(how)
        return day_s.map(s).values

    out["or_hi"] = agg(0, 60, "high", "max")
    out["or_lo"] = agg(0, 60, "low", "min")
    out["lon_hi"] = agg(420, 480, "high", "max")
    out["lon_lo"] = agg(420, 480, "low", "min")
    out["asia_hi"] = agg(0, 360, "high", "max")
    out["asia_lo"] = agg(0, 360, "low", "min")
    out["preus_hi"] = agg(780, 810, "high", "max")
    out["preus_lo"] = agg(780, 810, "low", "min")
    out["od3_hi"] = agg(0, 15, "high", "max")
    out["od3_lo"] = agg(0, 15, "low", "min")

    def first_at(mm, col):
        m = minute == mm
        if not m.any():
            return np.full(n, np.nan)
        s = df.loc[m].groupby(day_v[m])[col].first()
        return day_s.map(s).values

    out["us_ref"] = first_at(810, "open")
    out["ny_ref"] = first_at(1200, "open")
    out["ny_end"] = first_at(1260, "close")
    out["monday_open"] = first_at(0, "open")
    out["monday_4h"] = first_at(240, "close")
    out["open5_open"] = first_at(0, "open")
    out["open5_close"] = first_at(0, "close")
    out["od3_open"] = first_at(0, "open")
    out["od3_close"] = first_at(10, "close")

    # settlement reference: close one hour before 00/08/16 settlement
    ref = np.full(n, np.nan)
    m = np.isin(minute, [420, 900, 1380])
    ref[m] = df["close"].values[m]
    last = np.nan
    for i in range(n):
        if np.isfinite(ref[i]):
            last = ref[i]
        ref[i] = last
    out["settle_ref"] = ref

    # daily first open / last close
    g = df.groupby(day_v)
    d_open = g["open"].first()
    d_close = g["close"].last()
    prev_close = d_close.shift(1)
    prev_open = d_open.shift(1)
    out["sunday_change"] = (prev_close - prev_open).reindex(day_v).values

    # last bar of the UTC day
    eod = np.zeros(n, dtype=bool)
    eod[:-1] = day_v[:-1] != day_v[1:]
    eod[-1] = True
    out["eod"] = eod
    out["dow"] = dow
    return out


def _make_builders(df):
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]
    b = {}

    def add(name, fn):
        b[name] = fn

    add("atr14", lambda: atr(df, 14).values)
    add("atr20", lambda: atr(df, 20).values)

    for p in (2, 3, 7, 14):
        add("rsi%d" % p, (lambda pp: (lambda: rsi(c, pp).values))(p))

    for p in (9, 10, 20, 21, 30, 50, 55, 100, 200):
        add("ema%d" % p, (lambda pp: (lambda: ema(c, pp).values))(p))

    for p in (10, 20, 30, 100):
        add("sma%d" % p, (lambda pp: (lambda: sma(c, pp).values))(p))

    def _bb(mult, key):
        def build():
            mid, up, lo = bollinger(c, 20, mult)
            return {"mid": mid.values, "up": up.values, "lo": lo.values}[key]
        return build

    for mult, tag in ((2.0, ""), (2.5, "25")):
        add("bb_mid" + tag, _bb(mult, "mid"))
        add("bb_up" + tag, _bb(mult, "up"))
        add("bb_lo" + tag, _bb(mult, "lo"))

    add("macd", lambda: macd(c)[0].values)
    add("macd_sig", lambda: macd(c)[1].values)
    add("macd_hist", lambda: macd(c)[2].values)

    for p in (20, 24, 30, 40, 48, 55, 72, 168, 240, 480):
        add("don_hi%d" % p, (lambda pp: (lambda: donchian(df, pp)[0].values))(p))
        add("don_lo%d" % p, (lambda pp: (lambda: donchian(df, pp)[1].values))(p))

    add("adx14", lambda: adx(df, 14)[0].values)
    add("plus_di14", lambda: adx(df, 14)[1].values)
    add("minus_di14", lambda: adx(df, 14)[2].values)

    add("stoch_k", lambda: stochastic(df, 14, 3)[0].values)
    add("stoch_d", lambda: stochastic(df, 14, 3)[1].values)

    add("williams_r14", lambda: williams_r(df, 14).values)
    add("williams_r100", lambda: williams_r(df, 100).values)

    add("cci20", lambda: cci(df, 20).values)
    add("vwap", lambda: vwap(df).values)

    add("supertrend", lambda: supertrend(df, 10, 3.0)[0].values)
    add("supertrend_dir", lambda: supertrend(df, 10, 3.0)[1].values)

    add("psar", lambda: parabolic_sar(df)[0])
    add("psar_trend", lambda: parabolic_sar(df)[1])

    add("uo", lambda: ultimate_oscillator(df).values)
    add("mfi14", lambda: mfi(df, 14).values)

    add("aroon_up", lambda: aroon(df, 25)[0].values)
    add("aroon_down", lambda: aroon(df, 25)[1].values)

    add("kama10", lambda: kama(c, 10).values)
    add("vwma30", lambda: vwma(c, v, 30).values)

    for p in (24, 168, 336, 720):
        add("ret_%d" % p, (lambda pp: (lambda: c.pct_change(pp).values))(p))

    add("atr_pct", lambda: atr(df, 14).values / c.values)
    add("lower_close", lambda: (c < c.shift(1)).astype(int).values)
    add("atr_median100", lambda: atr(df, 14).rolling(100).median().values)

    ret = c.pct_change()
    add("realized_vol20", lambda: ret.rolling(20).std().values)
    add("realized_vol500", lambda: ret.rolling(500).std().values)

    # Hoisted helpers so no strategy recomputes a full series inside the bar loop.
    add("hma21", lambda: hull_ma(c, 21).values)

    def _er30():
        change = (c - c.shift(30)).abs()
        vol = c.diff().abs().rolling(30).sum()
        return (change / vol.replace(0, np.nan)).values
    add("er30", _er30)

    def _slope50():
        # Closed-form rolling OLS slope on a fixed 0..49 index.
        y = c.values
        n = 50
        x = np.arange(n, dtype=float)
        x_mean = x.mean()
        sxx = ((x - x_mean) ** 2).sum()
        s = pd.Series(y)
        roll = s.rolling(n)
        sy = roll.sum()
        sxy = s.rolling(n).apply(lambda w: np.dot(x, w), raw=True)
        mean_y = sy / n
        # dot(x, w) - n*x_mean*mean_y  == cov numerator
        num = sxy - n * x_mean * mean_y
        return (num / sxx).values
    add("slope50", _slope50)

    def _tenkan():
        return ((h.rolling(9).max() + l.rolling(9).min()) / 2).values
    def _kijun():
        return ((h.rolling(26).max() + l.rolling(26).min()) / 2).values
    add("tenkan", _tenkan)
    add("kijun", _kijun)

    def _rv20_pctile():
        rv = ret.rolling(20).std()
        return rv.rolling(500).rank(pct=True).values
    add("rv20_pctile", _rv20_pctile)

    add("sma10", lambda: sma(c, 10).values)

    def _atr30():
        """ATR(14) on 30-minute bars, mapped back to the base timeframe."""
        s = df.set_index("timestamp")
        b30 = s.resample("30min").agg({"open": "first", "high": "max",
                                       "low": "min", "close": "last"}).dropna()
        a = atr(b30.reset_index(), 14)
        a.index = b30.index
        right = pd.DataFrame({"ts": a.index, "v": a.values}).sort_values("ts")
        left = df[["timestamp"]].sort_values("timestamp")
        out = pd.merge_asof(left, right, left_on="timestamp", right_on="ts",
                            direction="backward")
        return out["v"].values
    add("atr30", _atr30)

    def _atr1d():
        """ATR(14) on completed daily bars, shifted one day, mapped to the base timeframe."""
        s_ = df.set_index("timestamp")
        d = s_.resample("1D").agg({"open": "first", "high": "max",
                                   "low": "min", "close": "last"}).dropna()
        a = atr(d.reset_index(), 14).shift(1)
        a.index = d.index
        right = pd.DataFrame({"ts": a.index, "v": a.values}).sort_values("ts")
        left = df[["timestamp"]].sort_values("timestamp")
        out = pd.merge_asof(left, right, left_on="timestamp", right_on="ts",
                            direction="backward")
        return out["v"].values
    add("atr1d", _atr1d)


    # ---- session-timeframe aggregates (computed once, on first use) ----
    _sess = {}

    def sess():
        if not _sess:
            _sess.update(_session_arrays(df))
        return _sess

    for _k in ("minute", "or_hi", "or_lo", "lon_hi", "lon_lo", "asia_hi", "asia_lo",
               "preus_hi", "preus_lo", "od3_hi", "od3_lo", "us_ref", "ny_ref", "ny_end",
               "monday_open", "monday_4h", "open5_open", "open5_close", "od3_open",
               "od3_close", "settle_ref", "sunday_change", "eod", "dow"):
        add(_k, (lambda kk: (lambda: sess()[kk]))(_k))

    return b


def get(ctx, key, j, default=np.nan):
    """Safely get a value from context array at index j."""
    arr = ctx.get(key)
    if arr is None:
        return default
    val = arr[j]
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    return val


# ============================================================================
# MEAN REVERSION (1-25)
# ============================================================================

@register("1")
def strat_01_rsi_mean_reversion(j, ctx):
    """RSI mean reversion · SOLUSDT · 1h. Long when RSI(14) < 30, exit when RSI > 70."""
    if j < 14:
        return None
    r = get(ctx, "rsi14", j)
    atr_v = get(ctx, "atr14", j)
    c = ctx["close"][j]
    if r is None or atr_v is None:
        return None
    
    # Check exit first
    # (exit handled by position logic - signal side=0 means exit)
    
    if r < 30:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif r > 70:
        return {"side": 0, "stop_px": 0}
    return None


@register("2")
def strat_02_bollinger_rsi(j, ctx):
    """Bollinger + RSI · BTCUSDT · 15m. Long when close < BB lower and RSI < 35, exit at BB mid."""
    if j < 20:
        return None
    c = ctx["close"][j]
    r = get(ctx, "rsi14", j)
    bb_lo = get(ctx, "bb_lo", j)
    bb_mid = get(ctx, "bb_mid", j)
    atr_v = get(ctx, "atr14", j)
    if r is None or bb_lo is None or bb_mid is None or atr_v is None:
        return None
    
    if c < bb_lo and r < 35:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": bb_mid}
    elif c >= bb_mid:
        return {"side": 0, "stop_px": 0}
    return None


@register("3")
def strat_03_vwap_zscore(j, ctx):
    """VWAP z-score · ETHUSDT · 5m. Long when z < -2.2, exit when z >= 0."""
    if j < 60:
        return None
    c = ctx["close"][j]
    vwap_v = get(ctx, "vwap", j)
    atr_v = get(ctx, "atr14", j)
    # z-score of close vs VWAP over 60 bars
    close_arr = ctx["close"]
    vwap_arr = ctx["vwap"]
    if j < 60 or vwap_v is None or atr_v is None:
        return None
    window = close_arr[j-59:j+1]
    vw_window = vwap_arr[j-59:j+1]
    diff = window - vw_window
    mean = np.mean(diff)
    std = np.std(diff)
    if std == 0 or math.isnan(std):
        return None
    z = (c - vwap_v - mean) / std  # z of (close - vwap)
    
    if z < -2.2:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": vwap_v}
    elif z >= 0:
        return {"side": 0, "stop_px": 0}
    return None


@register("4")
def strat_04_stochastic_cross(j, ctx):
    """Stochastic cross · HYPEUSDT · 1h. Long when %K crosses above 20, exit when %K > 80."""
    if j < 15:
        return None
    k = get(ctx, "stoch_k", j)
    k_prev = get(ctx, "stoch_k", j-1)
    atr_v = get(ctx, "atr14", j)
    c = ctx["close"][j]
    if k is None or k_prev is None or atr_v is None:
        return None
    
    if k_prev <= 20 and k > 20:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif k > 80:
        return {"side": 0, "stop_px": 0}
    return None


@register("5")
def strat_05_williams_r(j, ctx):
    """Williams %R · SUIUSDT · 15m. Long when %R < -90, exit when > -30."""
    if j < 14:
        return None
    wr = get(ctx, "williams_r14", j)
    atr_v = get(ctx, "atr14", j)
    c = ctx["close"][j]
    if wr is None or atr_v is None:
        return None
    
    if wr < -90:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif wr > -30:
        return {"side": 0, "stop_px": 0}
    return None


@register("6")
def strat_06_cci_reversal(j, ctx):
    """CCI reversal · JUPUSDT · 1h. Long when CCI(20) < -150, exit when CCI > 0."""
    if j < 20:
        return None
    cci_v = get(ctx, "cci20", j)
    atr_v = get(ctx, "atr14", j)
    c = ctx["close"][j]
    if cci_v is None or atr_v is None:
        return None
    
    if cci_v < -150:
        stop = c - 2.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif cci_v > 0:
        return {"side": 0, "stop_px": 0}
    return None


@register("7")
def strat_07_connors_rsi2(j, ctx):
    """Connors RSI(2) · BTCUSDT · 1h. Close > EMA200, RSI(2) < 10 long, exit at prior 5-bar high."""
    if j < 200:
        return None
    c = ctx["close"][j]
    r2 = get(ctx, "rsi2", j)
    ema200 = get(ctx, "ema200", j)
    atr_v = get(ctx, "atr14", j)
    if r2 is None or ema200 is None or atr_v is None:
        return None
    
    high5 = ctx["high"][j-5:j].max() if j >= 5 else c
    
    if c > ema200 and r2 < 10:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": high5}
    elif c > high5:
        return {"side": 0, "stop_px": 0}
    return None


@register("8")
def strat_08_keltner_fade(j, ctx):
    """Keltner fade · ETHUSDT · 15m. Long when close < Keltner lower, exit at midline."""
    if j < 20:
        return None
    c = ctx["close"][j]
    kel_lo = get(ctx, "bb_lo", j)  # placeholder - need keltner lower
    # Compute keltner on the fly
    from backtest100_engine import keltner
    # We don't have keltner precomputed; compute simple version
    # Use BB as approximation if keltner not available
    kel_mid = get(ctx, "bb_mid", j)
    kel_lo = ctx["low"][j-19:j+1].mean() - 1.5 * get(ctx, "atr14", j)
    atr_v = get(ctx, "atr14", j)
    if kel_lo is None or kel_mid is None or atr_v is None:
        return None
    
    if c < kel_lo:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": kel_mid}
    elif c >= kel_mid:
        return {"side": 0, "stop_px": 0}
    return None


@register("9")
def strat_09_fast_rsi(j, ctx):
    """Fast RSI · SOLUSDT · 5m. Long when RSI(7) < 20, exit when RSI(7) > 60 or 12 bars."""
    if j < 7:
        return None
    r7 = get(ctx, "rsi7", j)
    atr_v = get(ctx, "atr14", j)
    c = ctx["close"][j]
    if r7 is None or atr_v is None:
        return None
    
    # Track bars in position - this needs state, use a simpler approach:
    # exit when RSI(7) > 60; time stop handled separately
    if r7 < 20:
        stop = c - 1.2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif r7 > 60:
        return {"side": 0, "stop_px": 0}
    return None


@register("10")
def strat_10_down_streak_bounce(j, ctx):
    """Down-streak bounce · HYPEUSDT · 15m. 3 consecutive lower closes + RSI<35, exit on close above prior high."""
    if j < 14:
        return None
    c = ctx["close"][j]
    r14 = get(ctx, "rsi14", j)
    atr_v = get(ctx, "atr14", j)
    if r14 is None or atr_v is None:
        return None
    
    # 3 consecutive lower closes
    if j >= 2:
        three_down = (ctx["close"][j] < ctx["close"][j-1] and 
                      ctx["close"][j-1] < ctx["close"][j-2] and
                      ctx["close"][j-2] < ctx["close"][j-3])
    else:
        three_down = False
    
    if three_down and r14 < 35:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    # Exit on close above prior bar's high
    if j >= 1 and c > ctx["high"][j-1]:
        return {"side": 0, "stop_px": 0}
    return None


@register("11")
def strat_11_ema_deviation(j, ctx):
    """EMA deviation · SUIUSDT · 1h. Long when close >= 2.5*ATR(20) below EMA20, exit at EMA20."""
    if j < 20:
        return None
    c = ctx["close"][j]
    ema20 = get(ctx, "ema20", j)
    atr20 = get(ctx, "atr20", j)
    atr14 = get(ctx, "atr14", j)
    if ema20 is None or atr20 is None or atr14 is None:
        return None
    
    if c <= ema20 - 2.5 * atr20:
        stop = c - 3 * atr14
        return {"side": 1, "stop_px": stop, "tp_px": ema20}
    elif c >= ema20:
        return {"side": 0, "stop_px": 0}
    return None


@register("12")
def strat_12_donchian_fade(j, ctx):
    """Donchian fade · JUPUSDT · 15m. Long on touch of 20-bar lower channel, exit at midline."""
    if j < 20:
        return None
    c = ctx["close"][j]
    don_lo = get(ctx, "don_lo20", j)
    don_hi = get(ctx, "don_hi20", j)
    atr_v = get(ctx, "atr14", j)
    if don_lo is None or don_hi is None or atr_v is None:
        return None
    
    mid = (don_hi + don_lo) / 2
    if c <= don_lo:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": mid}
    elif c >= mid:
        return {"side": 0, "stop_px": 0}
    return None


@register("13")
def strat_13_volume_rsi(j, ctx):
    """Volume-confirmed RSI · BTCUSDT · 5m. RSI<25 and volume > 2x 20-bar avg, exit RSI>55."""
    if j < 20:
        return None
    c = ctx["close"][j]
    r14 = get(ctx, "rsi14", j)
    vol = ctx["volume"][j]
    vol_avg = ctx["volume"][j-19:j+1].mean() if j >= 19 else vol
    atr_v = get(ctx, "atr14", j)
    if r14 is None or atr_v is None:
        return None
    
    if r14 < 25 and vol > 2 * vol_avg:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif r14 > 55:
        return {"side": 0, "stop_px": 0}
    return None


@register("14")
def strat_14_50ema_stretch(j, ctx):
    """50-EMA stretch · ETHUSDT · 1h. Long when close > 3% below EMA50, exit at EMA50."""
    if j < 50:
        return None
    c = ctx["close"][j]
    ema50 = get(ctx, "ema50", j)
    atr_v = get(ctx, "atr14", j)
    if ema50 is None or atr_v is None:
        return None
    
    if c < ema50 * 0.97:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": ema50}
    elif c >= ema50:
        return {"side": 0, "stop_px": 0}
    return None


@register("15")
def strat_15_bollinger_pctb(j, ctx):
    """Bollinger %B · SOLUSDT · 15m. Long when %B < 0, exit when %B > 0.8 or 24 bars."""
    if j < 20:
        return None
    c = ctx["close"][j]
    bb_up = get(ctx, "bb_up", j)
    bb_lo = get(ctx, "bb_lo", j)
    atr_v = get(ctx, "atr14", j)
    if bb_up is None or bb_lo is None or atr_v is None:
        return None
    
    pctb = (c - bb_lo) / (bb_up - bb_lo) if bb_up != bb_lo else 0
    
    if pctb < 0:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif pctb > 0.8:
        return {"side": 0, "stop_px": 0}
    return None


@register("16")
def strat_16_rsi_divergence(j, ctx):
    """RSI divergence · HYPEUSDT · 5m. Bullish RSI divergence vs 30-bar price low."""
    if j < 30:
        return None
    c = ctx["close"][j]
    r14 = get(ctx, "rsi14", j)
    atr_v = get(ctx, "atr14", j)
    if r14 is None or atr_v is None:
        return None
    
    # Find 30-bar price low
    window_low = ctx["low"][j-30:j].min()
    low_idx = j - 30 + np.argmin(ctx["low"][j-30:j])
    
    # Bullish divergence: price makes lower low, RSI makes higher low
    if ctx["low"][j] <= window_low and j > low_idx:
        # Check if current RSI > RSI at the low point
        r_at_low = get(ctx, "rsi14", low_idx)
        if r_at_low is not None and r14 > r_at_low:
            stop = c - 1.5 * atr_v
            return {"side": 1, "stop_px": stop}
    elif r14 > 65:
        return {"side": 0, "stop_px": 0}
    return None


@register("17")
def strat_17_ultimate_oscillator(j, ctx):
    """Ultimate Oscillator · SUIUSDT · 5m. Long when UO < 30, exit when > 70."""
    if j < 28:
        return None
    uo = get(ctx, "uo", j)
    atr_v = get(ctx, "atr14", j)
    c = ctx["close"][j]
    if uo is None or atr_v is None:
        return None
    
    if uo < 30:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif uo > 70:
        return {"side": 0, "stop_px": 0}
    return None


@register("18")
def strat_18_mfi_reversal(j, ctx):
    """MFI reversal · JUPUSDT · 5m. Long when MFI(14) < 20, exit when MFI > 75."""
    if j < 14:
        return None
    mfi_v = get(ctx, "mfi14", j)
    atr_v = get(ctx, "atr14", j)
    c = ctx["close"][j]
    if mfi_v is None or atr_v is None:
        return None
    
    if mfi_v < 20:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif mfi_v > 75:
        return {"side": 0, "stop_px": 0}
    return None


@register("19")
def strat_19_range_fade(j, ctx):
    """Range fade · BTCUSDT · 15m. Long when close 1.5*ATR below 20-bar high, exit at 10-bar SMA."""
    if j < 20:
        return None
    c = ctx["close"][j]
    hi20 = ctx["high"][j-20:j].max()
    sma10 = ctx["close"][j-9:j+1].mean() if j >= 9 else c
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    if c <= hi20 - 1.5 * atr_v:
        stop = ctx["low"][j] - 1 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": sma10}
    elif c >= sma10:
        return {"side": 0, "stop_px": 0}
    return None


@register("20")
def strat_20_multi_tf_rsi(j, ctx):
    """Multi-timeframe RSI · ETHUSDT · 5m. Long when RSI(14)<30 and 1h RSI<45."""
    # Simplified: use same-bar RSI and a slower RSI as proxy for HTF
    if j < 14:
        return None
    c = ctx["close"][j]
    r14 = get(ctx, "rsi14", j)
    # Use RSI on a slower scale as proxy for 1h RSI on 5m data
    r_slow = get(ctx, "rsi14", j)  # proxy - in practice would use resampled data
    atr_v = get(ctx, "atr14", j)
    if r14 is None or atr_v is None:
        return None
    
    if r14 < 30 and r_slow < 45:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif r14 > 60:
        return {"side": 0, "stop_px": 0}
    return None


@register("21")
def strat_21_trend_filtered_rsi(j, ctx):
    """Trend-filtered RSI · SOLUSDT · 1h. Long when RSI<30 and close > EMA200."""
    if j < 200:
        return None
    c = ctx["close"][j]
    r14 = get(ctx, "rsi14", j)
    ema200 = get(ctx, "ema200", j)
    atr_v = get(ctx, "atr14", j)
    if r14 is None or ema200 is None or atr_v is None:
        return None
    
    if r14 < 30 and c > ema200:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif r14 > 70:
        return {"side": 0, "stop_px": 0}
    return None


@register("22")
def strat_22_band_fade_time_stop(j, ctx):
    """Band fade with time stop · HYPEUSDT · 1h. Long on lower BB(20,2.5) touch, exit at mid or 10 bars."""
    if j < 20:
        return None
    c = ctx["close"][j]
    bb_lo25 = get(ctx, "bb_lo25", j)
    bb_mid25 = get(ctx, "bb_mid25", j)
    atr_v = get(ctx, "atr14", j)
    if bb_lo25 is None or bb_mid25 is None or atr_v is None:
        return None
    
    if c <= bb_lo25:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": bb_mid25}
    elif c >= bb_mid25:
        return {"side": 0, "stop_px": 0}
    return None


@register("23")
def strat_23_connors_rsi32100(j, ctx):
    """Connors RSI(3,2,100) · SUIUSDT · 15m. Long when CRSI < 10, exit when > 70."""
    # Simplified Connors RSI: average of RSI(3), RSI(2), and %R(100)
    if j < 100:
        return None
    c = ctx["close"][j]
    r3 = get(ctx, "rsi3", j)
    r2 = get(ctx, "rsi2", j)
    wr100 = get(ctx, "williams_r100", j)
    atr_v = get(ctx, "atr14", j)
    
    if r3 is None or r2 is None or wr100 is None or atr_v is None:
        return None
    
    crsi = (r3 + r2 + wr100) / 3
    
    if crsi < 10:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif crsi > 70:
        return {"side": 0, "stop_px": 0}
    return None


@register("24")
def strat_24_failed_breakdown_reclaim(j, ctx):
    """Failed breakdown reclaim · JUPUSDT · 1h. A close below the prior 10-bar low that is
    reclaimed within two bars; stop 1 ATR under the reclaim low, exit at the 10-bar high."""
    if j < 13:
        return None
    c = ctx["close"][j]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None

    # Case 1: the previous bar broke below the 10-bar low formed before it
    lo_prev = ctx["low"][j-11:j-1].min()
    broke1 = ctx["close"][j-1] < lo_prev and c > lo_prev
    # Case 2: two bars ago broke, last bar still below, now reclaimed
    lo_prev2 = ctx["low"][j-12:j-2].min()
    broke2 = (ctx["close"][j-2] < lo_prev2 and ctx["close"][j-1] <= lo_prev2
              and c > lo_prev2)
    if broke1 or broke2:
        reclaim_low = ctx["low"][j-2:j+1].min()
        stop = reclaim_low - 1.0 * atr_v
        hi10 = ctx["high"][j-9:j+1].max()
        return {"side": 1, "stop_px": stop, "tp_px": hi10}
    return None


@register("25")
def strat_25_vwap_band(j, ctx):
    """VWAP band · BTCUSDT · 1h. Long when price 2 std below 30-bar VWAP, exit at VWAP."""
    if j < 30:
        return None
    c = ctx["close"][j]
    vwap_v = get(ctx, "vwap", j)
    atr_v = get(ctx, "atr14", j)
    if vwap_v is None or atr_v is None:
        return None
    
    # 2 std below VWAP using 30-bar std of close-vwap
    window = ctx["close"][j-29:j+1] - ctx["vwap"][j-29:j+1]
    std = np.std(window)
    if std == 0 or math.isnan(std):
        return None
    
    if c < vwap_v - 2 * std:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": vwap_v}
    elif c >= vwap_v:
        return {"side": 0, "stop_px": 0}
    return None


# ============================================================================
# TREND FOLLOWING (26-45)
# ============================================================================

@register("26")
def strat_26_ema_cross(j, ctx):
    """EMA cross · ETHUSDT · 1h. Long on EMA20>EMA50, short on reverse."""
    if j < 50:
        return None
    c = ctx["close"][j]
    e20 = get(ctx, "ema20", j)
    e50 = get(ctx, "ema50", j)
    e20_prev = get(ctx, "ema20", j-1)
    e50_prev = get(ctx, "ema50", j-1)
    atr_v = get(ctx, "atr14", j)
    if e20 is None or e50 is None or e20_prev is None or e50_prev is None or atr_v is None:
        return None
    
    if e20_prev <= e50_prev and e20 > e50:
        stop = c - 3 * atr_v
        return {"side": 1, "stop_px": stop}
    elif e20_prev >= e50_prev and e20 < e50:
        return {"side": -1, "stop_px": c + 3 * atr_v}
    return None


@register("27")
def strat_27_supertrend(j, ctx):
    """Supertrend · SOLUSDT · 15m. Supertrend flips define long/short."""
    if j < 10:
        return None
    c = ctx["close"][j]
    st = get(ctx, "supertrend", j)
    st_dir = get(ctx, "supertrend_dir", j)
    st_prev_dir = get(ctx, "supertrend_dir", j-1)
    atr_v = get(ctx, "atr14", j)
    if st is None or st_dir is None or st_prev_dir is None or atr_v is None:
        return None
    
    if st_prev_dir == -1 and st_dir == 1:
        stop = st
        return {"side": 1, "stop_px": stop}
    elif st_prev_dir == 1 and st_dir == -1:
        stop = st
        return {"side": -1, "stop_px": stop}
    return None


@register("28")
def strat_28_donchian_breakout(j, ctx):
    """Donchian breakout · BTCUSDT · 1h. Long on 55-bar high break, exit on 20-bar low break."""
    if j < 55:
        return None
    c = ctx["close"][j]
    don_hi55 = ctx["high"][j-55:j].max()
    don_lo20 = ctx["low"][j-20:j].min()
    atr_v = get(ctx, "atr14", j)
    if don_hi55 is None or don_lo20 is None or atr_v is None:
        return None
    
    if c > don_hi55:
        stop = c - 3 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < don_lo20:
        return {"side": 0, "stop_px": 0}
    return None


@register("29")
def strat_29_macd_zero_cross(j, ctx):
    """MACD zero-cross · HYPEUSDT · 15m. Long on MACD hist zero cross, close > EMA200."""
    if j < 200:
        return None
    c = ctx["close"][j]
    hist = get(ctx, "macd_hist", j)
    hist_prev = get(ctx, "macd_hist", j-1)
    ema200 = get(ctx, "ema200", j)
    atr_v = get(ctx, "atr14", j)
    if hist is None or hist_prev is None or ema200 is None or atr_v is None:
        return None
    
    if hist_prev <= 0 and hist > 0 and c > ema200:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("30")
def strat_30_adx_di_cross(j, ctx):
    """ADX DI cross · SUIUSDT · 1h. Long on +DI>-DI with ADX>25, short on reverse."""
    if j < 14:
        return None
    c = ctx["close"][j]
    adx_v = get(ctx, "adx14", j)
    pdi = get(ctx, "plus_di14", j)
    mdi = get(ctx, "minus_di14", j)
    pdi_prev = get(ctx, "plus_di14", j-1)
    mdi_prev = get(ctx, "minus_di14", j-1)
    atr_v = get(ctx, "atr14", j)
    if adx_v is None or pdi is None or mdi is None or pdi_prev is None or mdi_prev is None or atr_v is None:
        return None
    
    if pdi_prev <= mdi_prev and pdi > mdi and adx_v > 25:
        stop = c - 2.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif pdi_prev >= mdi_prev and pdi < mdi and adx_v > 25:
        stop = c + 2.5 * atr_v
        return {"side": -1, "stop_px": stop}
    return None


@register("31")
def strat_31_triple_ema_pullback(j, ctx):
    """Triple EMA pullback · JUPUSDT · 15m. EMA9>EMA21>EMA55, long on touch of EMA21."""
    if j < 55:
        return None
    c = ctx["close"][j]
    e9 = get(ctx, "ema9", j)
    e21 = get(ctx, "ema21", j)
    e55 = get(ctx, "ema55", j)
    atr_v = get(ctx, "atr14", j)
    if e9 is None or e21 is None or e55 is None or atr_v is None:
        return None
    
    if e9 > e21 > e55 and abs(c - e21) < atr_v * 0.5:  # touching EMA21
        stop = e55 - 0.5 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("32")
def strat_32_hma_slope(j, ctx):
    """HMA slope · ETHUSDT · 5m. Long when HMA(21) slope positive 3 bars, exit when negative."""
    if j < 21:
        return None
    c = ctx["close"][j]
    hma_series = ctx["hma21"]
    hma_v = hma_series[j] if j < len(hma_series) else np.nan
    hma_v1 = hma_series[j-1] if j-1 < len(hma_series) else np.nan
    hma_v2 = hma_series[j-2] if j-2 < len(hma_series) else np.nan
    atr_v = get(ctx, "atr14", j)
    
    if math.isnan(hma_v) or math.isnan(hma_v1) or math.isnan(hma_v2) or atr_v is None:
        return None
    
    slope_pos = hma_v > hma_v1 > hma_v2
    slope_neg = hma_v < hma_v1 < hma_v2
    
    if slope_pos:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif slope_neg:
        return {"side": 0, "stop_px": 0}
    return None


@register("33")
def strat_33_ichimoku(j, ctx):
    """Ichimoku · BTCUSDT · 15m. Long when close > cloud and Tenkan > Kijun."""
    if j < 52:
        return None
    c = ctx["close"][j]
    # Tenkan-sen (9-period), Kijun-sen (26-period), Senkou Span A/B
    tenkan = get(ctx, "tenkan", j)
    kijun = get(ctx, "kijun", j)
    # Cloud (simplified)
    span_a = (tenkan + kijun) / 2  # Simplified
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    if c > span_a and tenkan > kijun:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < kijun:
        return {"side": 0, "stop_px": 0}
    return None


@register("34")
def strat_34_regression_slope(j, ctx):
    """Regression slope · SOLUSDT · 1h. Long when 50-bar LR slope positive, short when negative."""
    if j < 50:
        return None
    c = ctx["close"][j]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    window = ctx["close"][j-49:j+1]
    slope = ctx["slope50"][j]
    
    if slope > 0:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif slope < 0:
        stop = c + 2 * atr_v
        return {"side": -1, "stop_px": stop}
    return None


@register("35")
def strat_35_480_bar_breakout(j, ctx):
    """480-bar breakout · HYPEUSDT · 1h. Long on 480-bar high, exit on 240-bar low."""
    if j < 480:
        return None
    c = ctx["close"][j]
    don_hi480 = ctx["high"][j-480:j].max()
    don_lo240 = ctx["low"][j-240:j].min()
    atr_v = get(ctx, "atr14", j)
    if don_hi480 is None or don_lo240 is None or atr_v is None:
        return None
    
    if c > don_hi480:
        stop = c - 3 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < don_lo240:
        return {"side": 0, "stop_px": 0}
    return None


@register("36")
def strat_36_ema_adx(j, ctx):
    """EMA(9/21) with ADX · SUIUSDT · 5m. Long on EMA9>EMA21 with ADX>20, exit on reverse."""
    if j < 21:
        return None
    c = ctx["close"][j]
    e9 = get(ctx, "ema9", j)
    e21 = get(ctx, "ema21", j)
    e9_prev = get(ctx, "ema9", j-1)
    e21_prev = get(ctx, "ema21", j-1)
    adx_v = get(ctx, "adx14", j)
    atr_v = get(ctx, "atr14", j)
    if e9 is None or e21 is None or e9_prev is None or e21_prev is None or adx_v is None or atr_v is None:
        return None
    
    if e9_prev <= e21_prev and e9 > e21 and adx_v > 20:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif e9_prev >= e21_prev and e9 < e21:
        return {"side": 0, "stop_px": 0}
    return None


@register("37")
def strat_37_parabolic_sar(j, ctx):
    """Parabolic SAR · JUPUSDT · 1h. Long on SAR flip up, short on flip down."""
    if j < 1:
        return None
    c = ctx["close"][j]
    psar_v = get(ctx, "psar", j)
    psar_trend = get(ctx, "psar_trend", j)
    psar_trend_prev = get(ctx, "psar_trend", j-1)
    atr_v = get(ctx, "atr14", j)
    if psar_v is None or psar_trend is None or psar_trend_prev is None or atr_v is None:
        return None
    
    if psar_trend_prev == -1 and psar_trend == 1:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif psar_trend_prev == 1 and psar_trend == -1:
        stop = c + 2 * atr_v
        return {"side": -1, "stop_px": stop}
    return None


@register("38")
def strat_38_keltner_breakout(j, ctx):
    """Keltner breakout · BTCUSDT · 5m. Long on close > upper Keltner, exit at midline."""
    if j < 20:
        return None
    c = ctx["close"][j]
    bb_up = get(ctx, "bb_up", j)
    bb_mid = get(ctx, "bb_mid", j)
    atr_v = get(ctx, "atr14", j)
    if bb_up is None or bb_mid is None or atr_v is None:
        return None
    
    if c > bb_up:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < bb_mid:
        return {"side": 0, "stop_px": 0}
    return None


@register("39")
def strat_39_aroon(j, ctx):
    """Aroon · ETHUSDT · 15m. Long when Aroon Up > 70 and Aroon Down < 30."""
    if j < 25:
        return None
    c = ctx["close"][j]
    au = get(ctx, "aroon_up", j)
    ad = get(ctx, "aroon_down", j)
    atr_v = get(ctx, "atr14", j)
    if au is None or ad is None or atr_v is None:
        return None
    
    if au > 70 and ad < 30:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif au < 30 and ad > 70:
        return {"side": 0, "stop_px": 0}
    return None


@register("40")
def strat_40_vwma_cross(j, ctx):
    """VWMA cross · SOLUSDT · 5m. Long on VWMA30 > SMA30, short on reverse."""
    if j < 30:
        return None
    c = ctx["close"][j]
    vwma30 = get(ctx, "vwma30", j)
    sma30 = get(ctx, "sma30", j)
    vwma30_prev = get(ctx, "vwma30", j-1)
    sma30_prev = get(ctx, "sma30", j-1)
    atr_v = get(ctx, "atr14", j)
    if vwma30 is None or sma30 is None or vwma30_prev is None or sma30_prev is None or atr_v is None:
        return None
    
    if vwma30_prev <= sma30_prev and vwma30 > sma30:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif vwma30_prev >= sma30_prev and vwma30 < sma30:
        stop = c + 1.5 * atr_v
        return {"side": -1, "stop_px": stop}
    return None


@register("41")
def strat_41_efficiency_ratio(j, ctx):
    """Efficiency ratio filter · HYPEUSDT · 5m. Long when ER(30) > 0.4 and EMA10 > EMA30."""
    if j < 30:
        return None
    c = ctx["close"][j]
    er = get(ctx, "er30", j)
    e10 = get(ctx, "ema10", j)
    e30 = get(ctx, "ema30", j)
    atr_v = get(ctx, "atr14", j)
    if atr_v is None or er is None:
        return None
    
    if er > 0.4 and e10 is not None and e30 is not None and e10 > e30:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("42")
def strat_42_kama_slope(j, ctx):
    """KAMA slope · SUIUSDT · 15m. Long while KAMA(10) slope positive, exit when negative."""
    if j < 10:
        return None
    c = ctx["close"][j]
    kama_v = get(ctx, "kama10", j)
    kama_prev = get(ctx, "kama10", j-1)
    atr_v = get(ctx, "atr14", j)
    if kama_v is None or kama_prev is None or atr_v is None:
        return None
    
    if kama_v > kama_prev:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif kama_v < kama_prev:
        return {"side": 0, "stop_px": 0}
    return None


@register("43")
def strat_43_htf_trend_filter(j, ctx):
    """HTF trend filter · JUPUSDT · 5m. Long when 15m close > 15m EMA100 and 5m RSI>50."""
    # Simplified: use same-bar EMA100 and RSI as proxy
    if j < 100:
        return None
    c = ctx["close"][j]
    ema100 = get(ctx, "ema100", j)
    r14 = get(ctx, "rsi14", j)
    atr_v = get(ctx, "atr14", j)
    if ema100 is None or r14 is None or atr_v is None:
        return None
    
    if c > ema100 and r14 > 50:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < ema100:
        return {"side": 0, "stop_px": 0}
    return None


@register("44")
def strat_44_168_bar_breakout(j, ctx):
    """168-bar breakout · BTCUSDT · 1h. Long on close above 168-bar high, exit below 72-bar low."""
    if j < 168:
        return None
    c = ctx["close"][j]
    don_hi168 = ctx["high"][j-168:j].max()
    don_lo72 = ctx["low"][j-72:j].min()
    atr_v = get(ctx, "atr14", j)
    if don_hi168 is None or don_lo72 is None or atr_v is None:
        return None
    
    if c > don_hi168:
        stop = c - 2.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < don_lo72:
        return {"side": 0, "stop_px": 0}
    return None


@register("45")
def strat_45_time_series_momentum(j, ctx):
    """Time-series momentum · ETHUSDT · 1h. Sign of 168-bar return sets direction, rebalance at 00:00 UTC."""
    if j < 168:
        return None
    c = ctx["close"][j]
    ret168 = get(ctx, "ret_168", j)
    atr_v = get(ctx, "atr14", j)
    if ret168 is None or atr_v is None:
        return None
    
    # Rebalance at 00:00 UTC - check if this is the first bar of the day
    is_new_day = ctx["hour"][j] == 0 and ctx["minute"][j] == 0
    
    if is_new_day:
        if ret168 > 0:
            stop = c - 2 * atr_v
            return {"side": 1, "stop_px": stop}
        elif ret168 < 0:
            stop = c + 2 * atr_v
            return {"side": -1, "stop_px": stop}
    return None


# ============================================================================
# BREAKOUT AND VOLATILITY EXPANSION (46-65)
# ============================================================================

@register("46")
def strat_46_bollinger_squeeze(j, ctx):
    """Bollinger squeeze · SOLUSDT · 15m. BB bandwidth at 100-bar low, long on close above upper band."""
    if j < 100:
        return None
    c = ctx["close"][j]
    bb_up = get(ctx, "bb_up", j)
    bb_lo = get(ctx, "bb_lo", j)
    bb_mid = get(ctx, "bb_mid", j)
    atr_v = get(ctx, "atr14", j)
    if bb_up is None or bb_lo is None or bb_mid is None or atr_v is None:
        return None
    
    bw = (bb_up - bb_lo) / bb_mid
    bw_min100 = ctx["bb_up"][j-99:j+1] - ctx["bb_lo"][j-99:j+1]
    bw_min100 = bw_min100 / ctx["bb_mid"][j-99:j+1]
    is_min = bw == bw_min100.min()
    
    if is_min and c > bb_up:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": bb_mid}
    elif c >= bb_mid:
        return {"side": 0, "stop_px": 0}
    return None


@register("47")
def strat_47_opening_range_breakout(j, ctx):
    """Opening range breakout · BTCUSDT · 5m. 00:00-01:00 range, break, stop at mid, exit end of day."""
    if ctx["minute"][j] < 60:
        return None
    hi = ctx["or_hi"][j]
    lo = ctx["or_lo"][j]
    if not (np.isfinite(hi) and np.isfinite(lo)):
        return None
    mid = (hi + lo) / 2
    c = ctx["close"][j]
    if ctx["eod"][j]:
        return {"side": 0, "stop_px": 0}
    if c > hi:
        return {"side": 1, "stop_px": mid}
    if c < lo:
        return {"side": -1, "stop_px": mid}
    return None


@register("48")
def strat_48_nr7_breakout(j, ctx):
    """NR7 breakout · HYPEUSDT · 15m. Break of NR7 bar high/low."""
    if j < 7:
        return None
    c = ctx["close"][j]
    ranges = ctx["high"][j-7:j] - ctx["low"][j-7:j]
    nr7_idx = j - 7 + np.argmin(ranges)
    nr7_hi = ctx["high"][nr7_idx]
    nr7_lo = ctx["low"][nr7_idx]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    if c > nr7_hi:
        stop = min(nr7_lo, c - 1.5 * atr_v)
        return {"side": 1, "stop_px": stop}
    elif c < nr7_lo:
        stop = max(nr7_hi, c + 1.5 * atr_v)
        return {"side": -1, "stop_px": stop}
    return None


@register("49")
def strat_49_atr_expansion(j, ctx):
    """ATR expansion · SUIUSDT · 1h. Long when ATR > 1.8x median and close > 20-bar high."""
    if j < 100:
        return None
    c = ctx["close"][j]
    atr_v = get(ctx, "atr14", j)
    atr_med = get(ctx, "atr_median100", j)
    hi20 = ctx["high"][j-20:j].max()
    if atr_v is None or atr_med is None:
        return None
    
    if atr_v > 1.8 * atr_med and c > hi20:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("50")
def strat_50_volatility_breakout(j, ctx):
    """Volatility breakout · JUPUSDT · 15m. Long if price > open + 0.5*ATR, short if < open - 0.5*ATR."""
    if j < 1:
        return None
    o = ctx["open"][j]
    c = ctx["close"][j]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    # Time exit after 96 bars - simplified (no state tracking)
    if c > o + 0.5 * atr_v:
        stop = c - 1 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < o - 0.5 * atr_v:
        stop = c + 1 * atr_v
        return {"side": -1, "stop_px": stop}
    return None


@register("51")
def strat_51_ttm_squeeze(j, ctx):
    """TTM squeeze · ETHUSDT · 5m. Squeeze when Keltner inside Bollinger, long on release with mom>0."""
    if j < 20:
        return None
    c = ctx["close"][j]
    bb_up = get(ctx, "bb_up", j)
    bb_lo = get(ctx, "bb_lo", j)
    atr_v = get(ctx, "atr14", j)
    if bb_up is None or bb_lo is None or atr_v is None:
        return None
    
    # Simplified: long on close above upper BB with momentum
    hist = get(ctx, "macd_hist", j)
    if hist is None:
        return None
    
    if c > bb_up and hist > 0:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif hist < 0:
        return {"side": 0, "stop_px": 0}
    return None


@register("52")
def strat_52_range_compression(j, ctx):
    """Range compression · BTCUSDT · 15m. 192-bar (2-day) range < 1.5 x daily ATR,
    then trade the break of that range.
    The prompt compares a 2-day range with "ATR(14)", which only has meaning on the
    daily timeframe; a 15m ATR would never be 2/3 of a 2-day range."""
    if j < 192:
        return None
    c = ctx["close"][j]
    hi192 = ctx["high"][j-192:j].max()
    lo192 = ctx["low"][j-192:j].min()
    atr_d = get(ctx, "atr1d", j)
    if atr_d is None or not np.isfinite(atr_d):
        return None

    if (hi192 - lo192) < 1.5 * atr_d:
        if c > hi192:
            stop = c - 2 * get(ctx, "atr14", j)
            return {"side": 1, "stop_px": stop}
        elif c < lo192:
            stop = c + 2 * get(ctx, "atr14", j)
            return {"side": -1, "stop_px": stop}
    return None


@register("53")
def strat_53_volume_breakout(j, ctx):
    """Volume breakout · SOLUSDT · 5m. Long on 60-bar high break with volume > 2x avg."""
    if j < 60:
        return None
    c = ctx["close"][j]
    hi60 = ctx["high"][j-60:j].max()
    vol = ctx["volume"][j]
    vol_avg = ctx["volume"][j-60:j].mean()
    lo30 = ctx["low"][j-30:j].min()
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    if c > hi60 and vol > 2 * vol_avg:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < lo30:
        return {"side": 0, "stop_px": 0}
    return None


@register("54")
def strat_54_failed_breakout_fade(j, ctx):
    """Failed breakout fade · HYPEUSDT · 5m. Short when close above 40-bar high falls back within 3 bars."""
    if j < 40:
        return None
    c = ctx["close"][j]
    hi40 = ctx["high"][j-40:j-3].max() if j >= 40 else ctx["high"][:j].max() if j > 0 else c
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    # Simplified: check for false breakout
    if j >= 3 and ctx["close"][j-3] > hi40 and c <= hi40:
        stop = hi40 + 1 * atr_v
        return {"side": -1, "stop_px": stop}
    return None


@register("55")
def strat_55_pivot_breakout(j, ctx):
    """Pivot breakout · SUIUSDT · 15m. Break of prior day's high/low with ADX>20."""
    if j < 14:
        return None
    c = ctx["close"][j]
    adx_v = get(ctx, "adx14", j)
    atr_v = get(ctx, "atr14", j)
    if adx_v is None or atr_v is None:
        return None
    
    # Prior day high/low - simplified using 24-bar lookback on 15m
    prev_hi = ctx["high"][j-24:j].max() if j >= 24 else c
    prev_lo = ctx["low"][j-24:j].min() if j >= 24 else c
    
    if adx_v > 20:
        if c > prev_hi:
            stop = (prev_hi + prev_lo) / 2  # pivot
            return {"side": 1, "stop_px": stop}
        elif c < prev_lo:
            stop = (prev_hi + prev_lo) / 2
            return {"side": -1, "stop_px": stop}
    return None


@register("56")
def strat_56_donchian_chandelier(j, ctx):
    """Donchian with chandelier exit · JUPUSDT · 1h. Long on 30-bar high, trail at HH - 3*ATR."""
    if j < 30:
        return None
    c = ctx["close"][j]
    don_hi30 = ctx["high"][j-30:j].max()
    atr_v = get(ctx, "atr14", j)
    if don_hi30 is None or atr_v is None:
        return None
    
    if c > don_hi30:
        stop = don_hi30 - 3 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("57")
def strat_57_vol_percentile_breakout(j, ctx):
    """Volatility-percentile breakout · ETHUSDT · 15m. RV20 below 10th percentile of 500, break above 20-bar high."""
    if j < 500:
        return None
    c = ctx["close"][j]
    rv20 = get(ctx, "realized_vol20", j)
    pct_rank = get(ctx, "rv20_pctile", j)
    hi20 = ctx["high"][j-20:j].max()
    atr_v = get(ctx, "atr14", j)
    if rv20 is None or atr_v is None or pct_rank is None:
        return None
    
    if pct_rank <= 0.10 and c > hi20:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("58")
def strat_58_gap_continuation(j, ctx):
    """Gap continuation · BTCUSDT · 1h. Gap > 0.8*ATR, trade gap direction for 4 bars."""
    if j < 1:
        return None
    c = ctx["close"][j]
    o = ctx["open"][j]
    prev_c = ctx["close"][j-1]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    gap = o - prev_c
    if abs(gap) > 0.8 * atr_v:
        side = 1 if gap > 0 else -1
        stop = c - side * 1.5 * atr_v
        return {"side": side, "stop_px": stop}
    return None


@register("59")
def strat_59_range_expansion(j, ctx):
    """Range expansion · SOLUSDT · 1h. Range > 2*ATR and close in top 20%."""
    if j < 1:
        return None
    c = ctx["close"][j]
    h = ctx["high"][j]
    l = ctx["low"][j]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    bar_range = h - l
    close_pos = (c - l) / bar_range if bar_range > 0 else 0
    
    if bar_range > 2 * atr_v and close_pos > 0.8:
        stop = l
        return {"side": 1, "stop_px": stop}
    elif c < l:
        return {"side": 0, "stop_px": 0}
    return None


@register("60")
def strat_60_keltner_rsi(j, ctx):
    """Keltner with RSI · HYPEUSDT · 1h. Long on close > upper Keltner with RSI>60."""
    if j < 20:
        return None
    c = ctx["close"][j]
    bb_up = get(ctx, "bb_up", j)
    r14 = get(ctx, "rsi14", j)
    ema20 = get(ctx, "ema20", j)
    atr_v = get(ctx, "atr14", j)
    if bb_up is None or r14 is None or ema20 is None or atr_v is None:
        return None
    
    if c > bb_up and r14 > 60:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif c < ema20:
        return {"side": 0, "stop_px": 0}
    return None


@register("61")
def strat_61_opening_drive(j, ctx):
    """Opening drive · SUIUSDT · 5m. First 3 bars range > 1 ATR, enter on the 4th in the drive direction."""
    if ctx["minute"][j] != 15:
        return None
    hi = ctx["od3_hi"][j]
    lo = ctx["od3_lo"][j]
    o = ctx["od3_open"][j]
    c3 = ctx["od3_close"][j]
    atr_v = get(ctx, "atr14", j)
    if not (np.isfinite(hi) and np.isfinite(lo) and np.isfinite(o) and np.isfinite(c3) and atr_v):
        return None
    if hi - lo <= 1.0 * atr_v:
        return None
    if c3 > o:
        return {"side": 1, "stop_px": lo, "max_hold": 12}
    if c3 < o:
        return {"side": -1, "stop_px": hi, "max_hold": 12}
    return None


@register("62")
def strat_62_volume_spike_breakout(j, ctx):
    """Volume spike breakout · JUPUSDT · 5m. Volume > 3x mean and close > 10-bar high."""
    if j < 50:
        return None
    c = ctx["close"][j]
    vol = ctx["volume"][j]
    vol_avg = ctx["volume"][j-50:j].mean()
    hi10 = ctx["high"][j-10:j].max()
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    if vol > 3 * vol_avg and c > hi10:
        stop = c - 1.2 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": c + 2 * atr_v}
    return None


@register("63")
def strat_63_bollinger_breakout_adx(j, ctx):
    """Bollinger breakout with ADX · BTCUSDT · 15m. Long on close > BB upper with ADX rising."""
    if j < 20:
        return None
    c = ctx["close"][j]
    bb_up = get(ctx, "bb_up", j)
    adx_v = get(ctx, "adx14", j)
    adx_prev = get(ctx, "adx14", j-1)
    atr_v = get(ctx, "atr14", j)
    if bb_up is None or adx_v is None or adx_prev is None or atr_v is None:
        return None
    
    if c > bb_up and adx_v > adx_prev:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("64")
def strat_64_consolidation_breakout(j, ctx):
    """Consolidation breakout · ETHUSDT · 1h. 30-bar range < 3*ATR, break of range."""
    if j < 30:
        return None
    c = ctx["close"][j]
    hi30 = ctx["high"][j-30:j].max()
    lo30 = ctx["low"][j-30:j].min()
    atr_v = get(ctx, "atr14", j)
    lo15 = ctx["low"][j-15:j].min()
    if atr_v is None:
        return None
    
    if (hi30 - lo30) < 3 * atr_v:
        if c > hi30:
            stop = c - 2 * atr_v
            return {"side": 1, "stop_px": stop}
        elif c < lo15:
            return {"side": 0, "stop_px": 0}
    return None


@register("65")
def strat_65_stop_hunt_reclaim(j, ctx):
    """Stop-hunt reclaim · SOLUSDT · 15m. Short when close breaks above 50-bar high then back below."""
    if j < 50:
        return None
    c = ctx["close"][j]
    hi50 = ctx["high"][j-50:j-2].max() if j >= 50 else ctx["high"][:max(1, j-2)].max()
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    # Simplified: check for false breakout
    if j >= 2 and ctx["close"][j-2] > hi50 and c <= hi50:
        stop = hi50 + 1 * atr_v  # above wick
        return {"side": -1, "stop_px": stop, "tp_px": hi50 - 1 * atr_v}
    return None


# ============================================================================
# SESSION AND EVENT (66-80)
# ============================================================================

@register("66")
def strat_66_london_open_range(j, ctx):
    """London open range · BTCUSDT · 15m. 07:00-08:00 range, break, stop at mid, exit 13:00 UTC."""
    if ctx["minute"][j] < 480:
        return None
    if ctx["minute"][j] >= 780:
        return {"side": 0, "stop_px": 0}
    hi = ctx["lon_hi"][j]
    lo = ctx["lon_lo"][j]
    if not (np.isfinite(hi) and np.isfinite(lo)):
        return None
    mid = (hi + lo) / 2
    c = ctx["close"][j]
    if c > hi:
        return {"side": 1, "stop_px": mid}
    if c < lo:
        return {"side": -1, "stop_px": mid}
    return None


@register("67")
def strat_67_asian_range_fade(j, ctx):
    """Asian range fade · ETHUSDT · 15m. Fade the 00:00-06:00 range extremes, target the midpoint."""
    if ctx["minute"][j] < 360:
        return None
    hi = ctx["asia_hi"][j]
    lo = ctx["asia_lo"][j]
    if not (np.isfinite(hi) and np.isfinite(lo)):
        return None
    rng = hi - lo
    if rng <= 0:
        return None
    mid = (hi + lo) / 2
    c = ctx["close"][j]
    if ctx["low"][j] <= lo + 0.1 * rng:
        return {"side": 1, "stop_px": lo - rng, "tp_px": mid}
    if ctx["high"][j] >= hi - 0.1 * rng:
        return {"side": -1, "stop_px": hi + rng, "tp_px": mid}
    return None


@register("68")
def strat_68_weekend_effect(j, ctx):
    """Weekend effect · SOLUSDT · 1h. Long at Friday 20:00 UTC, exit Monday 00:00 UTC."""
    if j < 1:
        return None
    c = ctx["close"][j]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    ts_dow = ctx["dayofweek"][j]
    ts_hour = ctx["hour"][j]
    if ts_dow == 4 and ts_hour == 20:  # Friday 20:00 UTC
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    elif ts_dow == 0 and ts_hour == 0:  # Monday 00:00 UTC
        return {"side": 0, "stop_px": 0}
    return None


@register("69")
def strat_69_us_cash_open_fade(j, ctx):
    """US cash open fade · HYPEUSDT · 15m. Fade a 1.5 ATR move in the first 30 min from 13:30."""
    m = ctx["minute"][j]
    if m < 810 or m >= 840:
        return None
    ref = ctx["us_ref"][j]
    atr_v = get(ctx, "atr14", j)
    if not (np.isfinite(ref) and np.isfinite(atr_v)):
        return None
    c = ctx["close"][j]
    if ctx["high"][j] >= ref + 1.5 * atr_v:
        return {"side": -1, "stop_px": c + 1.0 * atr_v, "max_hold": 4}
    if ctx["low"][j] <= ref - 1.5 * atr_v:
        return {"side": 1, "stop_px": c - 1.0 * atr_v, "max_hold": 4}
    return None


@register("70")
def strat_70_funding_window_fade(j, ctx):
    """Funding-window fade · SUIUSDT · 15m. Fade a 1 ATR move off the prior-hour close before settlement."""
    if ctx["minute"][j] not in (450, 930, 1410):
        return None
    ref = ctx["settle_ref"][j]
    atr_v = get(ctx, "atr14", j)
    if not (np.isfinite(ref) and np.isfinite(atr_v)):
        return None
    c = ctx["close"][j]
    if ctx["high"][j] >= ref + 1.0 * atr_v:
        return {"side": -1, "stop_px": c + 1.0 * atr_v, "max_hold": 4}
    if ctx["low"][j] <= ref - 1.0 * atr_v:
        return {"side": 1, "stop_px": c - 1.0 * atr_v, "max_hold": 4}
    return None


@register("71")
def strat_71_hour_of_day_filter(j, ctx):
    """Hour-of-day filter · JUPUSDT · 1h. EMA20/50 crosses only 14:00-18:00 UTC."""
    if j < 50:
        return None
    c = ctx["close"][j]
    e20 = get(ctx, "ema20", j)
    e50 = get(ctx, "ema50", j)
    e20_prev = get(ctx, "ema20", j-1)
    e50_prev = get(ctx, "ema50", j-1)
    atr_v = get(ctx, "atr14", j)
    if e20 is None or e50 is None or e20_prev is None or e50_prev is None or atr_v is None:
        return None
    
    in_window = 14 <= ctx["hour"][j] <= 18
    
    if in_window:
        if e20_prev <= e50_prev and e20 > e50:
            stop = c - 2 * atr_v
            return {"side": 1, "stop_px": stop}
        elif e20_prev >= e50_prev and e20 < e50:
            stop = c + 2 * atr_v
            return {"side": -1, "stop_px": stop}
    return None


@register("72")
def strat_72_monday_persistence(j, ctx):
    """Monday persistence · BTCUSDT · 1h. First 4h of Monday sets direction until Tuesday 00:00."""
    if ctx["dow"][j] != 0 or ctx["minute"][j] != 240:
        return None
    o = ctx["monday_open"][j]
    c4 = ctx["monday_4h"][j]
    atr_v = get(ctx, "atr14", j)
    if not (np.isfinite(o) and np.isfinite(c4) and np.isfinite(atr_v)):
        return None
    if c4 > o:
        return {"side": 1, "stop_px": ctx["close"][j] - 2 * atr_v, "max_hold": 19}
    if c4 < o:
        return {"side": -1, "stop_px": ctx["close"][j] + 2 * atr_v, "max_hold": 19}
    return None


@register("73")
def strat_73_sunday_monday_reversion(j, ctx):
    """Sunday-to-Monday reversion · ETHUSDT · 1h. Long Monday if Sunday fell more than 1 ATR."""
    if ctx["dow"][j] != 0 or ctx["minute"][j] != 0:
        return None
    chg = ctx["sunday_change"][j]
    atr_v = get(ctx, "atr14", j)
    if not (np.isfinite(chg) and np.isfinite(atr_v)):
        return None
    if chg < -1.0 * atr_v:
        return {"side": 1, "stop_px": ctx["close"][j] - 2 * atr_v, "max_hold": 23}
    return None


@register("74")
def strat_74_ny_close_momentum(j, ctx):
    """NY close momentum · SOLUSDT · 15m. 20:00-21:00 return sets the 21:00-23:00 direction."""
    if ctx["minute"][j] != 1260:
        return None
    o = ctx["ny_ref"][j]
    c = ctx["ny_end"][j]
    atr_v = get(ctx, "atr14", j)
    if not (np.isfinite(o) and np.isfinite(c) and np.isfinite(atr_v)):
        return None
    if c > o:
        return {"side": 1, "stop_px": ctx["close"][j] - 1.5 * atr_v, "max_hold": 8}
    if c < o:
        return {"side": -1, "stop_px": ctx["close"][j] + 1.5 * atr_v, "max_hold": 8}
    return None


@register("75")
def strat_75_month_end_drift(j, ctx):
    """Month-end drift · HYPEUSDT · 1h. Last 2 days of month, long when RSI<50."""
    if j < 14:
        return None
    c = ctx["close"][j]
    r14 = get(ctx, "rsi14", j)
    atr_v = get(ctx, "atr14", j)
    if r14 is None or atr_v is None:
        return None
    
    is_month_end = ctx["month_end2"][j]
    
    if is_month_end and r14 < 50:
        stop = c - 2 * atr_v
        return {"side": 1, "stop_px": stop}
    return None


@register("76")
def strat_76_pre_us_compression(j, ctx):
    """Pre-US compression · SUIUSDT · 5m. 13:00-13:30 range < 0.5 ATR(30m); enter a break
    of that range between 13:30 and 14:30, stop at the opposite side, 60-minute hold."""
    m = ctx["minute"][j]
    if m < 810 or m >= 870:
        return None
    hi = ctx["preus_hi"][j]
    lo = ctx["preus_lo"][j]
    a30 = get(ctx, "atr30", j)
    if not (np.isfinite(hi) and np.isfinite(lo) and np.isfinite(a30)):
        return None
    if hi - lo >= 0.5 * a30:
        return None
    c = ctx["close"][j]
    if c > hi:
        return {"side": 1, "stop_px": lo, "max_hold": 12}
    if c < lo:
        return {"side": -1, "stop_px": hi, "max_hold": 12}
    return None


@register("77")
def strat_77_asia_gap_fade(j, ctx):
    """Asia gap fade · JUPUSDT · 15m. Gap > 1*ATR from prior close, fade for 8 bars."""
    if j < 1:
        return None
    c = ctx["close"][j]
    prev_c = ctx["close"][j-1]
    o = ctx["open"][j]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    gap = o - prev_c
    if abs(gap) > 1 * atr_v:
        side = -1 if gap > 0 else 1  # Fade the gap
        stop = o + side * 1 * atr_v
        return {"side": side, "stop_px": stop}
    return None


@register("78")
def strat_78_session_vwap_band(j, ctx):
    """Session VWAP band · BTCUSDT · 5m. Fade VWAP ±1 std, exit at VWAP."""
    if j < 30:
        return None
    c = ctx["close"][j]
    vwap_v = get(ctx, "vwap", j)
    atr_v = get(ctx, "atr14", j)
    if vwap_v is None or atr_v is None:
        return None
    
    # Simplified: use Bollinger as proxy for VWAP band
    bb_up = get(ctx, "bb_up", j)
    bb_lo = get(ctx, "bb_lo", j)
    bb_mid = get(ctx, "bb_mid", j)
    
    if c < bb_lo:
        stop = c - 1.5 * atr_v
        return {"side": 1, "stop_px": stop, "tp_px": bb_mid}
    elif c > bb_up:
        stop = c + 1.5 * atr_v
        return {"side": -1, "stop_px": stop, "tp_px": bb_mid}
    return None


@register("79")
def strat_79_impulse_fade(j, ctx):
    """Impulse fade · ETHUSDT · 5m. After 3 bars moving 2*ATR in 15 min, fade 50% retrace."""
    if j < 3:
        return None
    c = ctx["close"][j]
    atr_v = get(ctx, "atr14", j)
    if atr_v is None:
        return None
    
    # Simplified impulse detection
    move = abs(ctx["close"][j] - ctx["close"][j-3])
    if move >= 2 * atr_v:
        # Fade 50% retrace
        extreme = ctx["high"][j] if ctx["close"][j] > ctx["close"][j-3] else ctx["low"][j]
        retrace = extreme - 0.5 * move if ctx["close"][j] > ctx["close"][j-3] else extreme + 0.5 * move
        if c >= retrace:
            stop = extreme
            return {"side": -1 if ctx["close"][j] > ctx["close"][j-3] else 1, "stop_px": stop}
    return None


@register("80")
def strat_80_opening_bar_momentum(j, ctx):
    """Opening-bar momentum · SOLUSDT · 5m. First 00:00 bar's direction, 12-bar hold."""
    if ctx["minute"][j] != 5:
        return None
    o = ctx["open5_open"][j]
    c = ctx["open5_close"][j]
    atr_v = get(ctx, "atr14", j)
    if not (np.isfinite(o) and np.isfinite(c) and np.isfinite(atr_v)):
        return None
    if c > o:
        return {"side": 1, "stop_px": ctx["close"][j] - 1.5 * atr_v, "max_hold": 12}
    if c < o:
        return {"side": -1, "stop_px": ctx["close"][j] + 1.5 * atr_v, "max_hold": 12}
    return None


@register("81")
def strat_81_sol_eth_zscore(j, ctx):
    """SOL/ETH z-score · 1h. Dollar-neutral ratio strategy."""
    return None  # Multi-pair - needs separate engine


@register("82")
def strat_82_btc_eth_zscore(j, ctx):
    """BTC/ETH z-score · 1h."""
    return None  # Multi-pair


@register("83")
def strat_83_weekly_basket_rotation(j, ctx):
    """Weekly basket rotation · 1h. Six perps."""
    return None  # Multi-pair


@register("84")
def strat_84_24bar_rel_strength(j, ctx):
    """24-bar relative strength · 1h."""
    return None  # Multi-pair


@register("85")
def strat_85_hype_sol_kalman(j, ctx):
    """HYPE/SOL Kalman hedge · 1h."""
    return None  # Multi-pair


@register("86")
def strat_86_sui_jup_coint(j, ctx):
    """SUI/JUP cointegration · 1h."""
    return None  # Multi-pair


@register("87")
def strat_87_low_vol_rotation(j, ctx):
    """Low-volatility rotation · 1h."""
    return None  # Multi-pair


@register("88")
def strat_88_alt_basket_vs_btc(j, ctx):
    """Alt basket vs BTC · 1h."""
    return None  # Multi-pair


@register("89")
def strat_89_eth_btc_ratio_breakout(j, ctx):
    """ETH/BTC ratio breakout · 15m."""
    return None  # Multi-pair


@register("90")
def strat_90_vol_scaled_momentum(j, ctx):
    """Volatility-scaled momentum · 1h."""
    return None  # Multi-pair


# ============================================================================
# FUNDING CARRY AND EXTREMES (91-100)
# ============================================================================

# Funding strategies need funding data aligned with klines
# These require a different data structure

@register("91")
def strat_91_funding_extreme_fade(j, ctx):
    """Funding extreme fade · BTCUSDT · 1h."""
    return None  # Needs funding data


@register("92")
def strat_92_funding_zscore(j, ctx):
    """Funding z-score · ETHUSDT · 1h."""
    return None  # Needs funding data


@register("93")
def strat_93_negative_funding_long(j, ctx):
    """Negative-funding long · SOLUSDT · 1h."""
    return None  # Needs funding data


@register("94")
def strat_94_funding_persistence(j, ctx):
    """Funding persistence · HYPEUSDT · 1h."""
    return None  # Needs funding data


@register("95")
def strat_95_price_funding_divergence(j, ctx):
    """Price-funding divergence · SUIUSDT · 1h."""
    return None  # Needs funding data


@register("96")
def strat_96_funding_trend_filter(j, ctx):
    """Funding with trend filter · JUPUSDT · 1h."""
    return None  # Needs funding data


@register("97")
def strat_97_funding_filtered_reversion(j, ctx):
    """Funding-filtered reversion · BTCUSDT · 1h."""
    return None  # Needs funding data


@register("98")
def strat_98_funding_vs_4h_rsi(j, ctx):
    """Funding vs 4h RSI · ETHUSDT · 1h."""
    return None  # Needs funding data


@register("99")
def strat_99_funding_momentum(j, ctx):
    """Funding momentum · SOLUSDT · 1h."""
    return None  # Needs funding data


@register("100")
def strat_100_funding_harvest(j, ctx):
    """Funding harvest · HYPEUSDT · 15m."""
    return None  # Needs funding data


# ============================================================================
# EXPORT
# ============================================================================
build_ctx = LazyCtx  # backwards-compatible alias


if __name__ == "__main__":
    print("Registered %d strategies" % len(STRATEGIES))
    for k in sorted(STRATEGIES.keys(), key=int):
        print("  %s: %s" % (k, STRATEGIES[k].__name__))
