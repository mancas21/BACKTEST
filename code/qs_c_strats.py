#!/usr/bin/env python
"""qs_c_strats.py — strategy-catalog family C (QS-021..QS-030, volatility
and breakout). Signal plans registered into qs_strats.SPECS at import (the
qsc adapter resolves from there). Same plan interface as families A and B;
executor semantics in qs_engine.run (next-open taker fills, gap-aware
stop-market stops SL-first on ties, 5-bar cooldown, G1 risk sizing).

Declared gap-fillings (the sheets are silent; nothing swept):
  * QS-021: the 10-bar compression state is evaluated on the ten bars
    BEFORE the trigger bar (the breakout bar is expansion by definition);
    "closing in the top 30% of its range" = close >= low + 0.7*range.
  * QS-022: the squeeze percentile is the trailing-200-bar rank of the
    bandwidth (<= 10%), counted over the last 5 bars INCLUSIVE of the
    trigger bar (the expansion bar itself rarely qualifies, so this is the
    permissive reading); bandwidth = (upper-lower)/middle of BB(20,2).
  * QS-023: "realized vol percentile" needs a reference window the sheet
    does not name: declared 500 trailing bars, rank via the shared
    _pct_rank_below helper; the 30-bar high is the prior 30 bars' highs.
  * QS-024: anchor declared UTC 00:00 (crypto never sleeps; the day open
    is the only anchor with an unambiguous definition). Opening range =
    bars with UTC minute-of-day < 30; signals only once the OR is complete
    (bar at/after 00:30). Time stop at one UTC day of bars (the sheet
    gives no exit; an ORB held forever is not the hypothesis).
  * QS-026: NR7 = the bar's range equals the minimum of the last 7 ranges
    (ties count as NR, measure-zero on floats); the reference NR bar is
    the MOST RECENT one; the executor's 5-bar cooldown approximates the
    "first close" clause.
  * QS-027: the chandelier flip events are the rising edges of close vs
    the opposite side's 22-bar extreme +- 3*ATR; the position stop is the
    trailing chandelier (best close since entry -/+ 3*ATR), which the
    executor supports natively via trailing_atr_mult; the initial stop is
    the just-broken flip line.
  * QS-028: the failed-breakout extreme is the breakdown bar's low (long
    side); the range midpoint for the target is the 20-bar range midpoint
    measured at the breakdown bar.
  * QS-029: L is the 20-bar high that was broken (the prior-bars' rolling
    max at the breakout bar); "returns to within 0.25*ATR of L" is
    evaluated on lows since the breakout; the retest bar must close above
    L and above its open; the 10-bar window resets at each new breakout.
  * QS-030: the HTF regime is computed on CLOSED higher-timeframe bars
    resampled from the same klines (5m/15m -> 1h, 1h -> 4h), mapped back
    only after the HTF bar closes (no lookahead); regime = close > EMA(100)
    and ADX(14) > 20.
  * Time stops: strategies whose sheet gives no exit get the family-A
    convention (declared per plan, 150-400 bars by hold character).
Calibration grids are declared, not swept (the fixed rules run; grid-DSR
and PBO stay pending, the same declared state as families A and B).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import qs_strats as P
from qs_engine import atr, ema, wilder_dmi

SPECS = P.SPECS

_HTF_MIN = {"5m": 60, "15m": 60, "1h": 240}


def _s(x):
    return pd.Series(np.asarray(x, float))


def _edge(cond):
    c = pd.Series(cond).fillna(False).astype(bool)
    return c & ~c.shift(1, fill_value=False)


def _blank(df):
    return pd.Series(np.zeros(len(df), bool), index=df.index)


def _atr_s(df):
    return _s(atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
                  df["close"].to_numpy(float), 14))


def _adx_s(df, n=14):
    _, _, adx = wilder_dmi(df["high"].to_numpy(float), df["low"].to_numpy(float),
                           df["close"].to_numpy(float), n)
    return pd.Series(np.asarray(adx, float))


def _bars_since(flag):
    """Bars since the most recent True of `flag` (0 on the flag bar itself,
    NaN before the first True). Positional: bar_index - last_flag_index;
    the returned Series keeps the input's index."""
    src = pd.Series(flag)
    f = src.fillna(False).astype(bool).to_numpy()
    pos = np.arange(len(f))
    last = pd.Series(np.where(f, pos, np.nan)).ffill().to_numpy()
    out = pos - last
    out[np.isnan(last)] = np.nan
    return pd.Series(out, index=src.index)


def _htf_regime(df, htf_min):
    """Closed-HTF-bar (close, EMA(100), ADX(14)) mapped onto the LTF rows;
    a value appears only after its HTF bar CLOSES."""
    ts = pd.to_datetime(df["ts"], utc=True)
    g = (df.set_index(ts)
           .resample(f"{htf_min}min", label="left", closed="left")
           .agg({"open": "first", "high": "max", "low": "min",
                 "close": "last"}).dropna())
    e100 = ema(g["close"], 100)
    _, _, adx = wilder_dmi(g["high"].to_numpy(float), g["low"].to_numpy(float),
                           g["close"].to_numpy(float), 14)
    adx = pd.Series(np.asarray(adx, float), index=g.index)
    ready = g.index + pd.Timedelta(minutes=htf_min)
    out = {}
    for nm, ser in (("close", g["close"]), ("ema", e100), ("adx", adx)):
        s = pd.Series(ser.to_numpy(), index=ready).reindex(
            pd.DatetimeIndex(ts), method="ffill")
        out[nm] = s.to_numpy()
    return out


# ── QS-021 ATR compression, then expansion ────────────────────────────────
def _qs021(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    a100 = _s(atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
                  df["close"].to_numpy(float), 100))
    ratio = a / a100.replace(0, np.nan)
    compressed = ratio.rolling(10, min_periods=10).max() < 0.7   # prior-10 via shift
    comp_state = compressed.shift(1).fillna(False).astype(bool)
    rng = h - l
    big = rng > 1.5 * a
    top30 = c >= l + 0.7 * rng
    bot30 = c <= l + 0.3 * rng
    trig_l = big & top30 & comp_state
    trig_s = big & bot30 & comp_state
    stop_l = (c - 2.0 * a).where(trig_l)
    stop_s = (c + 2.0 * a).where(trig_s)
    return dict(long_event=_edge(trig_l), short_event=_edge(trig_s),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=(c - stop_l).where(trig_l),
                stop_dist_short=(stop_s - c).where(trig_s),
                max_hold=150, atr=a)


# ── QS-022 Bollinger squeeze breakout ─────────────────────────────────────
def _qs022(df, tf):
    c = df["close"]
    a = _atr_s(df)
    mid = c.rolling(20, min_periods=20).mean()
    sd = c.rolling(20, min_periods=20).std(ddof=0)
    hi, lo = mid + 2.0 * sd, mid - 2.0 * sd
    bw = (hi - lo) / mid.replace(0, np.nan)
    rank = bw.rolling(200, min_periods=200).rank(pct=True)
    squeeze = rank <= 0.10
    recent = squeeze.rolling(5, min_periods=1).max() >= 1.0
    long_c = (c > hi) & recent
    short_c = (c < lo) & recent
    stop_l = (c - 2.0 * a).where(long_c)
    stop_s = (c + 2.0 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=(c - stop_l).where(long_c),
                stop_dist_short=(stop_s - c).where(short_c),
                max_hold=150, atr=a)


# ── QS-023 realized-vol regime breakout ───────────────────────────────────
def _qs023(df, tf):
    c = df["close"]
    h = df["high"]
    a = _atr_s(df)
    rv = c.pct_change().rolling(48, min_periods=48).std(ddof=0)
    pct = rv.rolling(500, min_periods=500).rank(pct=True) * 100.0
    cross_up = _edge(pct > 60.0)
    from_below = pct.shift(1).rolling(10, min_periods=1).min() < 40.0
    valid = cross_up & from_below
    regime = valid.rolling(10, min_periods=1).max() >= 1.0
    hh30 = h.rolling(30, min_periods=30).max().shift(1)
    ll30 = h.rolling(30, min_periods=30).min().shift(1)
    long_c = (c > hh30) & regime
    short_c = (c < ll30) & regime
    stop_l = (c - 2.0 * a).where(long_c)
    stop_s = (c + 2.0 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=(c - stop_l).where(long_c),
                stop_dist_short=(stop_s - c).where(short_c),
                max_hold=150, atr=a)


# ── QS-024 opening-range breakout (UTC 00:00 anchor) ──────────────────────
def _qs024(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    ts = pd.to_datetime(df["ts"], utc=True)
    minute_of_day = ts.dt.hour * 60 + ts.dt.minute
    in_or = minute_of_day < 30
    day = ts.dt.floor("D")
    or_high = h.where(in_or).groupby(day).transform("max")
    or_low = l.where(in_or).groupby(day).transform("min")
    or_done = (minute_of_day >= 30) & or_high.notna() & or_low.notna()
    long_c = or_done & (c > or_high)
    short_c = or_done & (c < or_low)
    stop_l = or_low.where(long_c)
    stop_s = or_high.where(short_c)
    dist_l = (c - stop_l).clip(upper=3.0 * a)
    dist_s = (stop_s - c).clip(upper=3.0 * a)
    day_bars = 86_400_000 // {"5m": 5 * 60_000, "15m": 15 * 60_000}[tf]
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                max_hold=day_bars, atr=a)


# ── QS-025 Donchian breakout with volume ──────────────────────────────────
def _qs025(df, tf):
    c = df["close"]
    h = df["high"]
    l = df["low"]
    a = _atr_s(df)
    v = df["volume"].astype(float)
    hh20 = h.rolling(20, min_periods=20).max().shift(1)
    ll20 = l.rolling(20, min_periods=20).min().shift(1)
    vol_ok = v > 2.0 * v.rolling(20, min_periods=20).mean()
    long_c = (c > hh20) & vol_ok
    short_c = (c < ll20) & vol_ok
    stop_l = (c - 2.0 * a).where(long_c)
    stop_s = (c + 2.0 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=(c - stop_l).where(long_c),
                stop_dist_short=(stop_s - c).where(short_c),
                max_hold=150, atr=a)


# ── QS-026 NR7 range expansion ────────────────────────────────────────────
def _qs026(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    rng = h - l
    nr = rng <= rng.rolling(7, min_periods=7).min()
    ref_high = h.where(nr).ffill()
    ref_low = l.where(nr).ffill()
    since = _bars_since(nr)
    in_win = since.between(1, 3)
    long_c = (c > ref_high) & in_win
    short_c = (c < ref_low) & in_win
    dist_l = (c - ref_low).clip(upper=2.5 * a).where(long_c)
    dist_s = (ref_high - c).clip(upper=2.5 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=(2.0 * dist_l).where(long_c),
                tp_dist_short=(2.0 * dist_s).where(short_c),
                max_hold=150, atr=a)


# ── QS-027 chandelier stop-and-reverse ────────────────────────────────────
def _qs027(df, tf):
    c = df["close"]
    l = df["low"]
    h = df["high"]
    a = _atr_s(df)
    ll22 = l.rolling(22, min_periods=22).min().shift(1)
    hh22 = h.rolling(22, min_periods=22).max().shift(1)
    long_c = c > ll22 + 3.0 * a
    short_c = c < hh22 - 3.0 * a
    dist_l = (c - (ll22 + 3.0 * a)).where(long_c)
    dist_s = ((hh22 - 3.0 * a) - c).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                trailing_atr_mult=3.0, max_hold=400, atr=a)


# ── QS-028 failed-breakout reversal ───────────────────────────────────────
def _qs028(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    hh20 = h.rolling(20, min_periods=20).max().shift(1)
    ll20 = l.rolling(20, min_periods=20).min().shift(1)
    break_dn = c < ll20
    break_up = c > hh20
    # "a close back above that low": THAT low is the 20-bar low that was
    # broken, not the breakdown bar's own extreme
    ref_low = ll20.where(break_dn).ffill()
    ref_high = hh20.where(break_up).ffill()
    mid = ((hh20 + ll20) / 2.0)
    mid_l = mid.where(break_dn).ffill()
    mid_s = mid.where(break_up).ffill()
    since_dn = _bars_since(break_dn)
    since_up = _bars_since(break_up)
    long_c = (c > ref_low) & since_dn.between(1, 3)
    short_c = (c < ref_high) & since_up.between(1, 3)
    # the stop sits beyond the failed-move EXTREME (the breakdown bar's low /
    # breakout bar's high), distance capped at 3*ATR
    ext_low = l.where(break_dn).ffill()
    ext_high = h.where(break_up).ffill()
    dist_l = (c - ext_low).clip(upper=3.0 * a).where(long_c)
    dist_s = (ext_high - c).clip(upper=3.0 * a).where(short_c)
    tp_l = (mid_l - c).where(long_c)
    tp_s = (c - mid_s).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=150, atr=a)


# ── QS-029 breakout with retest confirmation ──────────────────────────────
def _qs029(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    hh20 = h.rolling(20, min_periods=20).max().shift(1)
    ll20 = l.rolling(20, min_periods=20).min().shift(1)
    bo_up = c > hh20
    bo_dn = c < ll20
    lvl_up = hh20.where(bo_up).ffill()
    lvl_dn = ll20.where(bo_dn).ffill()
    since_up = _bars_since(bo_up)
    since_dn = _bars_since(bo_dn)
    grp_up = bo_up.cumsum()
    grp_dn = bo_dn.cumsum()
    touch_up = (l <= lvl_up + 0.25 * a).groupby(grp_up).cummax().astype(bool)
    touch_dn = (h >= lvl_dn - 0.25 * a).groupby(grp_dn).cummax().astype(bool)
    long_c = (c > lvl_up) & (c > o) & touch_up & since_up.between(1, 10)
    short_c = (c < lvl_dn) & (c < o) & touch_dn & since_dn.between(1, 10)
    dist_l = (c - (lvl_up - 0.75 * a)).clip(upper=3.0 * a).where(long_c)
    dist_s = ((lvl_dn + 0.75 * a) - c).clip(upper=3.0 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                max_hold=150, atr=a)


# ── QS-030 HTF-regime-filtered breakout ───────────────────────────────────
def _qs030(df, tf):
    c = df["close"]
    h = df["high"]
    l = df["low"]
    a = _atr_s(df)
    reg = _htf_regime(df, {"5m": 60, "15m": 60, "1h": 240}[tf])
    reg_up = (reg["close"] > reg["ema"]) & (reg["adx"] > 20.0)
    reg_dn = (reg["close"] < reg["ema"]) & (reg["adx"] > 20.0)
    hh20 = h.rolling(20, min_periods=20).max().shift(1)
    ll20 = l.rolling(20, min_periods=20).min().shift(1)
    long_c = (c > hh20) & reg_up
    short_c = (c < ll20) & reg_dn
    stop_l = (c - 2.0 * a).where(long_c)
    stop_s = (c + 2.0 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=(c - stop_l).where(long_c),
                stop_dist_short=(stop_s - c).where(short_c),
                max_hold=150, atr=a)


P.register("QS-021", "ATR compression followed by expansion", _qs021)
P.register("QS-022", "Bollinger Band squeeze breakout", _qs022)
P.register("QS-023", "Realized-volatility regime breakout", _qs023)
P.register("QS-024", "Opening-range breakout (UTC 00:00 anchor)", _qs024)
P.register("QS-025", "Donchian breakout with volume confirmation", _qs025)
P.register("QS-026", "NR7 range expansion", _qs026)
P.register("QS-027", "Chandelier stop-and-reverse", _qs027)
P.register("QS-028", "Failed breakout reversal", _qs028)
P.register("QS-029", "Breakout with retest confirmation", _qs029)
P.register("QS-030", "Breakout filtered by higher-timeframe regime", _qs030)
