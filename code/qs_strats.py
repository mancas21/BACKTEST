#!/usr/bin/env python
"""qs_strats.py -- the ten family-A strategies of the strategy catalog
(QS-001..QS-010) as exact signal arrays for qs_engine.run.

Every entry condition is converted to a RISING EDGE (the catalog's frequency
clause: one entry per episode, no re-entry while the condition persists);
cross-based entries are already edges. All indicators use closed bars; the
fill is the next open (the executor's job). no_trade filters are applied by
ANDing the entry event. The executor owns sizing, stops' fill mechanics,
cooldown and max_hold; the stop DISTANCE here follows each sheet:
  fixed 2*ATR(14) from the signal close (QS-001/002/005/006/007/009),
  the Supertrend line capped at 3*ATR (QS-003),
  2*ATR or the closer 20-bar opposite extreme (QS-004),
  the pullback swing low bounded to [1,3]*ATR (QS-008),
  the box low capped at 3*ATR (QS-010).
Declared base variants only (the sheets' optional variants -- trailing-stop
QS-001, 4R target QS-001, 2.5R/3R targets QS-008/010 -- are separate tests;
QS-010's trailing 3*ATR exit is part of its BASE exit rule and is wired).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qs_engine import atr, ema, wilder_dmi

SPECS = {}


def supertrend(h, l, c, period=10, mult=3.0):
    """ATR-banded trailing line; returns (line, direction +1/-1)."""
    h, l, c = map(np.asarray, (h, l, c))
    n = len(c)
    a = np.asarray(atr(h, l, c, period))
    hl2 = (h + l) / 2.0
    ub = hl2 + mult * a
    lb = hl2 - mult * a
    fub = np.copy(ub)
    flb = np.copy(lb)
    st = np.copy(c)
    d = np.ones(n, dtype=float)
    started = False
    for i in range(1, n):
        if not started:
            if np.isnan(ub[i]) or np.isnan(lb[i]):
                continue
            fub[i] = ub[i]
            flb[i] = lb[i]
            d[i] = 1.0 if c[i] > hl2[i] else -1.0
            st[i] = flb[i] if d[i] == 1 else fub[i]
            started = True
            continue
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or c[i - 1] > fub[i - 1])             else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or c[i - 1] < flb[i - 1])             else flb[i - 1]
        if d[i - 1] == 1:
            d[i] = -1.0 if c[i] < flb[i] else 1.0
        else:
            d[i] = 1.0 if c[i] > fub[i] else -1.0
        st[i] = flb[i] if d[i] == 1 else fub[i]
    return pd.Series(st, index=pd.Series(c).index), pd.Series(d, index=pd.Series(c).index)


def _s(x):
    return pd.Series(np.asarray(x, float))


def _edge(cond):
    c = pd.Series(cond).fillna(False).astype(bool)
    return c & ~c.shift(1, fill_value=False)


def _pct_rank_below(x, win):
    """Fraction of the trailing `win` window at or below the current value,
    via pandas' cython rolling rank (average-rank tie handling; ties are
    measure-zero on float price statistics)."""
    s = _s(x)
    return s.rolling(win, min_periods=win).rank(pct=True)


def register(sid, name, build):
    SPECS[sid] = dict(name=name, build=build)


# ── QS-001 ────────────────────────────────────────────────────────────────
def _qs001(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    e20, e100, e200 = ema(c, 20), ema(c, 100), ema(c, 200)
    a = atr(h, l, c, 14)
    _, _, adx = wilder_dmi(h, l, c, 14)
    xup = (e20 > e100) & (e20.shift(1) <= e100.shift(1))
    xdn = (e20 < e100) & (e20.shift(1) >= e100.shift(1))
    cross_up = _edge(xup & (c > e200))
    cross_dn = _edge(xdn & (c < e200))
    # no_trade: ADX<15; ATR below its 10th pct of 200; data gap last 5 bars
    gap = pd.Series(df["open_ts"]).diff().gt(2 * _tf_minutes_ms(tf)).fillna(False)
    ok = (_s(adx) >= 15) & (_s(a) >= a.rolling(200).quantile(0.10)) & ~gap
    le = cross_up & ok
    se = cross_dn & ok
    lx = xdn | ((c < e100) & (c.shift(1) < e100))
    sx = xup | ((c > e100) & (c.shift(1) > e100))
    return dict(long_event=le, short_event=se, long_exit=lx, short_exit=sx,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=300, atr=_s(a))


def _tf_minutes_ms(tf):
    return {"5m": 5 * 60_000, "15m": 15 * 60_000, "1h": 60 * 60_000}[tf]


register("QS-001", "Moving-average trend continuation", _qs001)


# ── QS-002 ────────────────────────────────────────────────────────────────
def _qs002(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    e10, e30, e100 = ema(c, 10), ema(c, 30), ema(c, 100)
    a = atr(h, l, c, 14)
    a_med = a.rolling(50).median()
    align_l = (e10 > e30) & (e30 > e100) & (c > e10) & (a > a_med)
    align_s = (e10 < e30) & (e30 < e100) & (c < e10) & (a > a_med)
    le = _edge(align_l)
    se = _edge(align_s)
    lx = (e10 < e30) & (e10.shift(1) >= e30.shift(1))
    sx = (e10 > e30) & (e10.shift(1) <= e30.shift(1))
    # no_trade: ATR below 30th pct of 200; flat stack (spread < 0.2*ATR)
    a30 = a.rolling(200).quantile(0.30)
    flat = (e10 - e100).abs() < 0.2 * a
    ok = (a >= a30) & ~flat
    return dict(long_event=le & ok, short_event=se & ok, long_exit=lx,
                short_exit=sx, stop_dist_long=_s(2.0 * a),
                stop_dist_short=_s(2.0 * a), max_hold=250, atr=_s(a))


register("QS-002", "EMA alignment with volatility confirmation", _qs002)


# ── QS-003 ────────────────────────────────────────────────────────────────
def _qs003(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    line, d = supertrend(h, l, c, 10, 3.0)
    flip_up = (d == 1) & (d.shift(1) == -1)
    flip_dn = (d == -1) & (d.shift(1) == 1)
    # no_trade: more than 3 flips in the last 20 bars (chop)
    flips = (flip_up | flip_dn).astype(int)
    chop = flips.rolling(20).sum() > 3
    le = flip_up & ~chop
    se = flip_dn & ~chop
    # stop = the supertrend line at entry, capped at 3*ATR distance
    stop_l = _s(line)
    dist_l = (c - stop_l).clip(lower=np.nan)
    dist_l = dist_l.where(dist_l <= 3 * a, 3 * a)
    stop_s = _s(line)
    dist_s = (stop_s - c).clip(lower=np.nan)
    dist_s = dist_s.where(dist_s <= 3 * a, 3 * a)
    return dict(long_event=le, short_event=se,
                long_exit=flip_dn, short_exit=flip_up,
                stop_level_long=stop_l.where(le), stop_level_short=stop_s.where(se),
                stop_dist_long=dist_l.where(le), stop_dist_short=dist_s.where(se),
                max_hold=300, atr=_s(a))


register("QS-003", "Supertrend continuation", _qs003)


# ── QS-004 ────────────────────────────────────────────────────────────────
def _qs004(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    hh55 = h.shift(1).rolling(55).max()
    ll20 = l.shift(1).rolling(20).min()
    ll55 = l.shift(1).rolling(55).min()
    hh20 = h.shift(1).rolling(20).max()
    le = _edge(c > hh55)
    se = _edge(c < ll55)
    # no_trade: ATR below its 20th pct of 200
    a20 = a.rolling(200).quantile(0.20)
    ok = a >= a20
    # stop: 2*ATR fixed, or the 20-bar opposite extreme if closer
    dist_l = np.minimum(2.0 * a, (c - ll20).clip(lower=0.0))
    dist_s = np.minimum(2.0 * a, (hh20 - c).clip(lower=0.0))
    dist_l = dist_l.where(dist_l > 0)
    dist_s = dist_s.where(dist_s > 0)
    return dict(long_event=le & ok, short_event=se & ok,
                long_exit=c < ll20, short_exit=c > hh20,
                stop_dist_long=_s(dist_l), stop_dist_short=_s(dist_s),
                max_hold=400, atr=_s(a))


register("QS-004", "Donchian channel breakout", _qs004)


# ── QS-005 ────────────────────────────────────────────────────────────────
def _qs005(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    L = 96
    ret = c / c.shift(L) - 1.0
    # return-space sigma: R(L) is a fractional return, so sigma must be the
    # std of 1-bar RETURNS (price-unit sigma shrinks z by the price level)
    sig = c.pct_change().rolling(L).std(ddof=0)
    z = ret / (sig * np.sqrt(L))
    r20 = c / c.shift(20) - 1.0
    long_c = (z > 1.0) & (r20 > 0)
    short_c = (z < -1.0) & (r20 < 0)
    le = _edge(long_c)
    se = _edge(short_c)
    # no_trade: |z|<1; vol above its 95th pct of 500
    vol95 = sig.rolling(500).quantile(0.95)
    ok = (z.abs() >= 1.0) & (sig < vol95)
    lx = _edge(z < 0.0) | (z < 0.0)
    sx = _edge(z > 0.0) | (z > 0.0)
    return dict(long_event=le & ok, short_event=se & ok, long_exit=lx,
                short_exit=sx, stop_dist_long=_s(2.0 * a),
                stop_dist_short=_s(2.0 * a), max_hold=192, atr=_s(a))


register("QS-005", "Time-series momentum", _qs005)


# ── QS-006 ────────────────────────────────────────────────────────────────
def _qs006(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    e50 = ema(c, 50)
    pdi, mdi, adx = wilder_dmi(h, l, c, 14)
    adx_s = _s(adx)
    rising3 = adx_s > adx_s.shift(3)
    long_c = (_s(pdi) > _s(mdi)) & (adx_s > 25) & rising3 & (c > e50)
    short_c = (_s(mdi) > _s(pdi)) & (adx_s > 25) & rising3 & (c < e50)
    le = _edge(long_c)
    se = _edge(short_c)
    # no_trade: ADX < 20
    ok = adx_s >= 20
    lx = (adx_s < 20) | (_s(mdi) > _s(pdi))
    sx = (adx_s < 20) | (_s(pdi) > _s(mdi))
    return dict(long_event=le & ok, short_event=se & ok, long_exit=lx,
                short_exit=sx, stop_dist_long=_s(2.0 * a),
                stop_dist_short=_s(2.0 * a), max_hold=250, atr=_s(a))


register("QS-006", "ADX-filtered directional continuation", _qs006)


# ── QS-007 ────────────────────────────────────────────────────────────────
def _htf_map(df, htf_minutes):
    """Closed-HTF-bar EMA values mapped onto the LTF timeline (a value is
    available only after its HTF bar CLOSES)."""
    ts = pd.to_datetime(df["ts"], utc=True)
    g = (df.set_index(ts)
           .resample(f"{htf_minutes}min", label="left", closed="left")
           .agg({"open": "first", "high": "max", "low": "min",
                 "close": "last"}).dropna())
    e50 = ema(g["close"], 50)
    e200 = ema(g["close"], 200)
    a = np.asarray(atr(g["high"].to_numpy(), g["low"].to_numpy(),
                       g["close"].to_numpy(), 14))
    ready = g.index + pd.Timedelta(minutes=htf_minutes)
    out = {}
    for nm, ser in (("e50", e50), ("e200", e200),
                    ("atr", pd.Series(a, index=g.index))):
        s = pd.Series(ser.to_numpy(), index=ready).reindex(
            pd.DatetimeIndex(ts), method="ffill")
        out[nm] = s.to_numpy()   # positional, df row order
    return out


def _qs007(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    e20 = ema(c, 20)
    e50 = ema(c, 50)
    htf = _htf_map(df, 360 if tf != "1h" else 1440)
    e50h = _s(htf["e50"])
    e200h = _s(htf["e200"])
    atrh = _s(htf["atr"])
    h_up = (e50h > e200h).fillna(False)
    spread_ok = ((e50h - e200h).abs() > 0.3 * atrh).fillna(False)
    xup = (e20 > e50) & (e20.shift(1) <= e50.shift(1))
    xdn = (e20 < e50) & (e20.shift(1) >= e50.shift(1))
    le = xup & h_up & spread_ok
    se = xdn & ~h_up & spread_ok
    lx = xdn | (~h_up)
    sx = xup | h_up
    return dict(long_event=le, short_event=se, long_exit=lx, short_exit=sx,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=300, atr=_s(a))


register("QS-007", "Higher-timeframe trend, lower-timeframe entries", _qs007)


# ── QS-008 ────────────────────────────────────────────────────────────────
def _qs008(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)
    _, _, adx = wilder_dmi(h, l, c, 14)
    near = (c - e20).abs() <= 0.5 * a
    pull = near.rolling(10).max().astype(bool)          # pulled back recently
    resum = c > h.shift(1)
    trend_up = e50 > e200
    trend_dn = e50 < e200
    adx_s = _s(adx)
    ok_regime = adx_s >= 18
    # pullback swing low = lowest low of the pullback window; stop bounded
    swing_l = l.rolling(10).min()
    dist_l = ((c - swing_l).clip(lower=1.0 * a)).clip(upper=3.0 * a)
    swing_h = h.rolling(10).max()
    dist_s = ((swing_h - c).clip(lower=1.0 * a)).clip(upper=3.0 * a)
    # no_trade: pullback closed beyond EMA50 by more than 2*ATR (trend break)
    broke_up = (c - e50) > 2.0 * a
    broke_dn = (e50 - c) > 2.0 * a
    le = _edge(trend_up & pull & resum) & ok_regime & ~broke_up
    se = _edge(trend_dn & pull & resum) & ok_regime & ~broke_dn
    return dict(long_event=le, short_event=se,
                long_exit=c < e50, short_exit=c > e50,
                stop_dist_long=_s(dist_l), stop_dist_short=_s(dist_s),
                max_hold=150, atr=_s(a))


register("QS-008", "Trend pullback continuation", _qs008)


# ── QS-009 ────────────────────────────────────────────────────────────────
def _qs009(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    roc = c / c.shift(48) - 1.0
    sig = c.diff().rolling(48).std(ddof=0)
    score = roc / sig
    pctl = _pct_rank_below(score, 500)
    long_c = (pctl >= 2.0 / 3.0) & (score > 0)
    short_c = (pctl <= 1.0 / 3.0) & (score < 0)
    le = _edge(long_c)
    se = _edge(short_c)
    vol97 = sig.rolling(500).quantile(0.97)
    ok = sig < vol97
    med = score.rolling(500).median()
    return dict(long_event=le & ok, short_event=se & ok,
                long_exit=score < med, short_exit=score > med,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=144, atr=_s(a))


register("QS-009", "Volatility-adjusted momentum", _qs009)


# ── QS-010 ────────────────────────────────────────────────────────────────
def _qs010(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = atr(h, l, c, 14)
    box_hi = h.rolling(30).max().shift(1)
    box_lo = l.rolling(30).min().shift(1)
    box_rng = box_hi - box_lo
    is_box = box_rng < 3.0 * a
    vol_ok = df["volume"] > 1.2 * df["volume"].rolling(20).mean()
    le = _edge((c > box_hi + 0.1 * a) & is_box & vol_ok)
    se = _edge((c < box_lo - 0.1 * a) & is_box & vol_ok)
    # no_trade: the box is YOUNG when either defining extreme of the
    # prior-30-bar window was set less than 15 bars before the break
    hi_off = h.shift(1).rolling(30).apply(np.argmax, raw=True)
    lo_off = l.shift(1).rolling(30).apply(np.argmin, raw=True)
    ok = ((29.0 - hi_off) >= 15) & ((29.0 - lo_off) >= 15)
    # stop = box low (long) capped at 3*ATR distance; trailing 3*ATR exit
    dist_l = (c - box_lo).clip(upper=3.0 * a).where(le | is_box)
    dist_s = (box_hi - c).clip(upper=3.0 * a).where(se | is_box)
    back_inside_l = c < box_hi
    back_inside_s = c > box_lo
    return dict(long_event=le & ok, short_event=se & ok,
                long_exit=back_inside_l, short_exit=back_inside_s,
                stop_level_long=box_lo.where(le), stop_level_short=box_hi.where(se),
                stop_dist_long=_s(dist_l), stop_dist_short=_s(dist_s),
                trailing_atr_mult=3.0, max_hold=200, atr=_s(a))


register("QS-010", "Breakout continuation after consolidation", _qs010)


def costs_for(sym, tf):
    return 5.0, 2.0        # the catalog's Base block
