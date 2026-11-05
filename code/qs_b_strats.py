#!/usr/bin/env python
"""qs_b_strats.py -- the catalog's family B (QS-011..QS-020, mean reversion)
as exact signal arrays for qs_engine.run / pack50_core.run_pair, registered
into qs_strats.SPECS at import (the qs/qsb adapters resolve from there).

DECLARED READINGS not fixed by the sheets:
  * QS-011 ships TWO declared sub-hypotheses: V1 (RSI crosses below 30, the
    exact cross bar) and V2 (first bar with RSI < 30 after an intervening
    bar with RSI >= 30 -- the persistent variant's no-re-entry rule). Both
    are registered (QS-011, QS-011V2).
  * QS-013: the entry sheet leaves L unspecified (the calibrate grid is
    {50,100,200}); the fixed-rules run uses L=100 (the grid's centre).
  * QS-014 ships TWO declared anchors: the UTC day open (QS-014) and the
    week open, Monday 00:00 UTC (QS-014W). AVWAP is candle-based
    (hlc3 x volume cumsum from the anchor); sigma = the 100-bar rolling
    stdev of (close - AVWAP). max_hold "until session end 23:55 UTC" is the
    day-anchor rule; the week variant exits at Friday 23:55 UTC (declared).
  * QS-016: the displacement return is close-to-close; the 50% target is
    half the displacement bar's body; sigma windows are 100 bars.
  * QS-017: touch tolerance = 0.25*ATR from the edge; "range older than 20
    bars" = the range state true for the last 20 consecutive bars; the
    primary target is mid-range.
  * QS-019: the declared primary pair is BTC/ETH (the most liquid pair in
    the catalog universe; the sheet names no pair). Beta = rolling OLS of
    ln(A) on ln(B) over 500 bars; stationarity = ADF-style t-stat on the
    training window (t < -2.86, the n=500 no-trend critical value) with
    half-life in 5..100 bars, retested every 100 bars; the OU z-score uses
    the spread mean/std of the estimation window; stop = |z| >= 3.5 (the
    sheet's primary; the 2*ATR-of-spread alternative is not wired); exit at
    z = 0 or 3x half-life. Dollar-neutral via pack50_core.run_pair.
  * QS-020: sigma windows for the 6-sigma news filter are 100 bars of the
    wick and of the range respectively.
Calibration grids are declared, not swept (the fixed rules run; grid-DSR and
PBO stay pending, the same declared state as families A and flow).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import qs_strats as P
from qs_engine import atr, ema, rsi as rsi_fn, wilder_dmi
from pack50_core import session_vwap

SPECS = P.SPECS


def _s(x):
    return pd.Series(np.asarray(x, float))


def _edge(cond):
    c = pd.Series(cond).fillna(False).astype(bool)
    return c & ~c.shift(1, fill_value=False)


def _atr_s(df):
    return _s(atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
                  df["close"].to_numpy(float), 14))


def _adx_s(df):
    _, _, adx = wilder_dmi(df["high"].to_numpy(float),
                           df["low"].to_numpy(float),
                           df["close"].to_numpy(float), 14)
    return _s(adx)


def _mod(df):
    ts = pd.to_datetime(df["ts"], utc=True)
    return pd.Series(ts.dt.hour * 60 + ts.dt.minute, index=df.index)


def _doy(df):
    return pd.Series(pd.to_datetime(df["ts"], utc=True).dt.floor("1D"),
                     index=df.index)


# ── QS-011 RSI reversal (V1 event / V2 persistent) ────────────────────────
def _rsi_state_events(rsi, level=30.0):
    """V2: first bar with RSI < level after an intervening bar >= level."""
    n = len(rsi)
    out = np.zeros(n, bool)
    armed = True
    r = rsi.to_numpy(float)
    for i in range(n):
        if np.isnan(r[i]):
            continue
        if armed and r[i] < level:
            out[i] = True
            armed = False
        elif r[i] >= level:
            armed = True
    return pd.Series(out, index=rsi.index)


def _qs011(df, tf, variant="v1"):
    c = df["close"]
    a = _atr_s(df)
    adx = _adx_s(df)
    r = rsi_fn(c.to_numpy(float), 14)
    r = _s(r)
    r_prev = r.shift(1)
    le_v1 = (r < 30.0) & (r_prev >= 30.0)
    se_v1 = (r > 70.0) & (r_prev <= 70.0)
    if variant == "v2":
        le = _rsi_state_events(r, 30.0)
        se = _rsi_state_events(-r, -70.0)   # first bar RSI > 70 after <= 70
        # symmetric: use level crossings for the short state
        se = _rsi_state_events(100.0 - r, 30.0)
    else:
        le = le_v1.fillna(False)
        se = se_v1.fillna(False)
    ok = adx <= 30.0                     # no_trade: strong trend
    lx = (r > 70.0) & (r_prev <= 70.0)
    sx = (r < 30.0) & (r_prev >= 30.0)
    return dict(long_event=le & ok, short_event=se & ok,
                long_exit=lx.fillna(False), short_exit=sx.fillna(False),
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=96, atr=a)


def _qs011a(df, tf):
    return _qs011(df, tf, "v1")


def _qs011b(df, tf):
    return _qs011(df, tf, "v2")


SPECS["QS-011"] = dict(name="RSI oversold reversal (V1 event)", build=_qs011a)
SPECS["QS-011V2"] = dict(name="RSI oversold reversal (V2 persistent)",
                         build=_qs011b)


# ── QS-012 Bollinger re-entry ─────────────────────────────────────────────
def _qs012(df, tf):
    c = df["close"]
    a = _atr_s(df)
    adx = _adx_s(df)
    from pack50_core import bollinger
    lo, mid, hi = ( _s(x) for x in bollinger(c.to_numpy(float), 20, 2.0) )
    re_l = (c > lo) & (c.shift(1) < lo.shift(1))
    re_s = (c < hi) & (c.shift(1) > hi.shift(1))
    bw = (hi - lo) / mid.replace(0, np.nan)
    ok = (bw <= 1.5 * bw.rolling(50, min_periods=50).median()) & (adx <= 30.0)
    tp_l = (mid - c).where(c < mid)
    tp_s = (c - mid).where(c > mid)
    return dict(long_event=_edge(re_l) & ok, short_event=_edge(re_s) & ok,
                long_exit=c >= mid, short_exit=c <= mid,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=48, atr=a)


SPECS["QS-012"] = dict(name="Bollinger Band reversion", build=_qs012)


# ── QS-013 z-score reversion ──────────────────────────────────────────────
def _qs013(df, tf, L=100):
    c = df["close"]
    a = _atr_s(df)
    m = c.rolling(L, min_periods=L).mean()
    sd = c.rolling(L, min_periods=L).std(ddof=0)
    z = (c - m) / sd.replace(0, np.nan)
    vol = c.pct_change().rolling(500, min_periods=500).std(ddof=0)
    vol95 = vol.rolling(500, min_periods=500).quantile(0.95)
    ok = (z.abs() <= 4.0) & (vol < vol95)
    le = _edge(z < -2.0) & ok
    se = _edge(z > 2.0) & ok
    return dict(long_event=le, short_event=se,
                long_exit=_edge(z > 0.0) | (z > 0.0),
                short_exit=_edge(z < 0.0) | (z < 0.0),
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=72, atr=a)


SPECS["QS-013"] = dict(name="Z-score deviation reversion", build=_qs013)


# ── QS-014 anchored VWAP reversion (day / week anchors) ───────────────────
def _avwap(df, anchor):
    """Candle-based AVWAP from UTC-day or ISO-week anchors."""
    ts = pd.to_datetime(df["ts"], utc=True)
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    v = df["volume"].astype(float)
    if anchor == "day":
        key = ts.dt.floor("1D")
    else:
        key = ts.dt.normalize() - pd.to_timedelta(ts.dt.dayofweek, unit="D")
    pv = (tp * v).groupby(key).cumsum()
    vv = v.groupby(key).cumsum()
    return (pv / vv.replace(0, np.nan)).ffill()


def _qs014(df, tf, anchor="day"):
    c = df["close"]
    a = _atr_s(df)
    av = _avwap(df, anchor)
    dev = c - av
    sig = dev.rolling(100, min_periods=100).std(ddof=0)
    mod = _mod(df)
    dow = pd.to_datetime(df["ts"], utc=True).dt.dayofweek
    early = mod < 60
    far = dev.abs() > 4 * sig
    ok = (sig.notna()) & ~early & ~far
    le = _edge(dev < -2.0 * sig) & ok
    se = _edge(dev > 2.0 * sig) & ok
    if anchor == "day":
        eod = mod >= 23 * 60
    else:
        eod = (dow == 4) & (mod >= 23 * 60)     # Friday 23:00+ (last bars)
    return dict(long_event=le, short_event=se,
                long_exit=(c >= av) | eod, short_exit=(c <= av) | eod,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                tp_dist_long=(av - c).where(c < av),
                tp_dist_short=(c - av).where(c > av),
                max_hold=0, atr=a)


def _qs014a(df, tf):
    return _qs014(df, tf, "day")


def _qs014b(df, tf):
    return _qs014(df, tf, "week")


SPECS["QS-014"] = dict(name="Anchored VWAP reversion (day anchor)",
                       build=_qs014a)
SPECS["QS-014W"] = dict(name="Anchored VWAP reversion (week anchor)",
                        build=_qs014b)


# ── QS-015 ATR-normalized VWAP deviation ──────────────────────────────────
def _qs015(df, tf):
    c = df["close"]
    a = _atr_s(df)
    vwap, _ = session_vwap(df, "1d")
    vwap = _s(vwap)
    dev = (c - vwap) / a.replace(0, np.nan)
    vol = c.pct_change().rolling(500, min_periods=500).std(ddof=0)
    vol95 = vol.rolling(500, min_periods=500).quantile(0.95)
    mod = _mod(df)
    ok = (mod >= 60) & (a < vol95)
    le = _edge(dev < -2.0) & ok
    se = _edge(dev > 2.0) & ok
    tp_l = (vwap - c).where(c < vwap)
    tp_s = (c - vwap).where(c > vwap)
    return dict(long_event=le, short_event=se,
                long_exit=c >= vwap, short_exit=c <= vwap,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=48, atr=a)


SPECS["QS-015"] = dict(name="VWAP deviation, ATR-normalized", build=_qs015)


# ── QS-016 displacement fade ──────────────────────────────────────────────
def _qs016(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    v = df["volume"].astype(float)
    ret = c.pct_change()
    sig = ret.rolling(100, min_periods=100).std(ddof=0)
    disp_bar = ret < -3.0 * sig
    vol_ok = v > 2 * v.rolling(20, min_periods=20).mean()
    not_news = ret > -6.0 * sig
    body = (o - c).clip(lower=0.0)
    stop_l = (l - 0.5 * a).where(disp_bar)
    dist_l = (c - stop_l).clip(upper=3.0 * a).where(disp_bar)
    tp_l = (0.5 * body).where(disp_bar)
    # short: up-bar displacement
    disp_up = ret > 3.0 * sig
    stop_s = (h + 0.5 * a).where(disp_up)
    dist_s = (stop_s - c).clip(upper=3.0 * a).where(disp_up)
    tp_s = (0.5 * (c - o).clip(lower=0.0)).where(disp_up)
    ok = not_news
    return dict(long_event=_edge(disp_bar & vol_ok) & ok,
                short_event=_edge(disp_up & vol_ok) & ok,
                long_exit=blank(df), short_exit=blank(df),
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=8, atr=a)


def blank(df):
    return pd.Series(np.zeros(len(df), bool), index=df.index)


SPECS["QS-016"] = dict(name="Displacement-candle fade", build=_qs016)


# ── QS-017 range oscillation ──────────────────────────────────────────────
def _qs017(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    adx = _adx_s(df)
    W = 60
    rhi = h.rolling(W, min_periods=W).max()
    rlo = l.rolling(W, min_periods=W).min()
    rng = rhi - rlo
    is_range = rng < 4.0 * a
    tol = 0.25 * a
    touch_hi = (h >= rhi - tol).rolling(W, min_periods=W).sum()
    touch_lo = (l <= rlo + tol).rolling(W, min_periods=W).sum()
    aged = is_range.rolling(20, min_periods=20).min() == 1
    pos_in_range = (c - rlo) / rng.replace(0, np.nan)
    up_close = c > o
    dn_close = c < o
    long_c = aged & (touch_lo >= 2) & (touch_hi >= 2) & \
        (pos_in_range <= 0.25) & up_close & (c <= rhi) & (c >= rlo)
    short_c = aged & (touch_lo >= 2) & (touch_hi >= 2) & \
        (pos_in_range >= 0.75) & dn_close & (c <= rhi) & (c >= rlo)
    le = _edge(long_c)
    se = _edge(short_c)
    mid = (rhi + rlo) / 2.0
    tp_l = (mid - c).where(c < mid)
    tp_s = (c - mid).where(c > mid)
    stop_l = (rlo - 0.5 * a).where(le)
    stop_s = (rhi + 0.5 * a).where(se)
    dist_l = (c - stop_l).where(le)
    dist_s = (stop_s - c).where(se)
    outside = (c > rhi) | (c < rlo)
    return dict(long_event=le, short_event=se,
                long_exit=(c >= mid) | outside, short_exit=(c <= mid) | outside,
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=40, atr=a)


SPECS["QS-017"] = dict(name="Range-bound oscillation", build=_qs017)


# ── QS-018 vol-spike fade ─────────────────────────────────────────────────
def _qs018(df, tf):
    o, c = df["open"], df["close"]
    a5 = _s(atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
                df["close"].to_numpy(float), 5))
    a50 = _s(atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
                 df["close"].to_numpy(float), 50))
    a14 = _atr_s(df)
    ratio = a5 / a50.replace(0, np.nan)
    ret3 = c - c.shift(3)
    dropped = ret3 < -1.5 * a14
    up_close = c > o
    long_c = (ratio > 2.0) & dropped & up_close
    le = _edge(long_c)
    se = _edge((ratio > 2.0) & (ret3 > 1.5 * a14) & (c < o))
    ok = ratio <= 4.0
    return dict(long_event=le & ok, short_event=se & ok,
                long_exit=ratio < 1.2, short_exit=ratio < 1.2,
                stop_dist_long=_s(2.0 * a14), stop_dist_short=_s(2.0 * a14),
                max_hold=12, atr=a14)


SPECS["QS-018"] = dict(name="Volatility-expansion fade", build=_qs018)


# ── QS-019 OU spread reversion (dollar-neutral pair BTC/ETH) ─────────────
def _ou_target(df_a, df_b, win=500, z_entry=2.0, z_stop=3.5,
               adf_crit=-2.86, hl_lo=5, hl_hi=100):
    """Rolling-OU spread state machine. Returns (target, note)."""
    la = np.log(df_a["close"].to_numpy(float))
    lb = np.log(df_b["close"].to_numpy(float))
    n = len(la)
    tgt = np.zeros(n, dtype=int)
    beta = np.full(n, np.nan)
    zarr = np.full(n, np.nan)
    cur = 0
    since = 0
    last_test = -10 ** 9
    ok_regime = False
    hl = np.nan
    for i in range(n):
        if i >= win and i - last_test >= 100:
            # rolling OLS beta of ln(A) on ln(B) over the past `win` bars
            x = lb[i - win:i]
            y = la[i - win:i]
            xm = x.mean()
            ym = y.mean()
            b = ((x - xm) * (y - ym)).sum() / ((x - xm) ** 2).sum()
            spr = y - b * x
            # ADF-style: d(s) ~ s_{t-1}; t = gamma / se(gamma)
            ds = np.diff(spr)
            s_lag = spr[:-1]
            xm2 = s_lag.mean()
            g = ((s_lag - xm2) * ds).sum() / ((s_lag - xm2) ** 2).sum()
            resid = ds - g * (s_lag - xm2)
            se_g = np.sqrt((resid ** 2).sum() /
                           max((len(ds) - 1) * ((s_lag - xm2) ** 2).sum(), 1e-12))
            t_stat = g / se_g if se_g > 0 else 0.0
            hl = -np.log(2.0) / np.log(1.0 + g) if 0 < 1.0 + g < 1.0 else np.nan
            ok_regime = bool(t_stat < adf_crit and hl_lo <= (hl if np.isfinite(hl) else -1) <= hl_hi)
            mu = spr.mean()
            sd = spr.std()
            beta[i] = b
            last_test = i
        if ok_regime and i >= win:
            b = beta[last_test]
            spr_now = la[i] - b * lb[i]
            # z vs the estimation window's spread moments (recomputed cheaply)
            spr_win = la[i - win:i + 1] - b * lb[i - win:i + 1]
            zz = (spr_now - spr_win.mean()) / max(spr_win.std(), 1e-12)
            zarr[i] = zz
            if cur == 1 and zz >= 0:
                cur = 0
            elif cur == -1 and zz <= 0:
                cur = 0
            if abs(zz) >= z_stop:
                cur = 0
            if cur == 0 and ok_regime:
                if zz <= -z_entry:
                    cur, since = 1, 0
                elif zz >= z_entry:
                    cur, since = -1, 0
            if cur != 0:
                since += 1
                hl_now = hl if np.isfinite(hl) else 100.0
                if since >= 3 * max(1, round(hl_now)):
                    cur, since = 0, 0
        tgt[i] = cur
    note = ("QS-019 OU spread, BTC/ETH, beta+ADF+half-life retested every "
            "100 bars on a 500-bar window; stop |z|>=3.5; exit z=0 or 3xHL")
    return tgt, note


def _qs019(a, b):
    return _ou_target(a, b)


SPECS["QS-019"] = dict(name="OU-process spread reversion (BTC/ETH)",
                       sym="BTCUSDT+ETHUSDT", pair=_qs019)
P.CODE = getattr(P, "CODE", {})


# ── QS-020 liquidity-dislocation wick fade ────────────────────────────────
def _qs020(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    v = df["volume"].astype(float)
    rng = h - l
    lower_wick = np.minimum(o, c) - l
    upper_wick = h - np.maximum(o, c)
    wick_frac_l = lower_wick / rng.replace(0, np.nan)
    wick_frac_s = upper_wick / rng.replace(0, np.nan)
    big = rng > 2.5 * a
    vol_ok = v > 2 * v.rolling(20, min_periods=20).mean()
    sig_r = rng.rolling(100, min_periods=100).std(ddof=0)
    sig_w = lower_wick.rolling(100, min_periods=100).std(ddof=0)
    not_catastrophe = ~((rng > 6 * sig_r) & (lower_wick > 6 * sig_w))
    long_c = (wick_frac_l >= 0.60) & big & vol_ok
    short_c = (wick_frac_s >= 0.60) & big & vol_ok
    stop_l = (l - 0.25 * a).where(long_c)
    dist_l = (c - stop_l).clip(upper=3.0 * a).where(long_c)
    # 50% wick retracement: target = l + 0.5*wick (long) — the DISTANCE
    # from the signal close, not half the wick itself
    tp_l = (c - (l + 0.5 * lower_wick)).where(long_c)
    stop_s = (h + 0.25 * a).where(short_c)
    dist_s = (stop_s - c).clip(upper=3.0 * a).where(short_c)
    tp_s = ((h - 0.5 * upper_wick) - c).where(short_c)
    return dict(long_event=_edge(long_c) & not_catastrophe,
                short_event=_edge(short_c) & not_catastrophe,
                long_exit=blank(df), short_exit=blank(df),
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=10, atr=a)


SPECS["QS-020"] = dict(name="Liquidity-dislocation wick fade", build=_qs020)


def costs_for(sym, tf):
    return 5.0, 2.0
