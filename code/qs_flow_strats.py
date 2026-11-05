#!/usr/bin/env python
"""qs_flow_strats.py -- the catalog's eight PARTIAL trade-flow hypotheses
(QS-043, QS-044, QS-048, QS-049, QS-050, QS-053, QS-058, QS-093) as exact
signal arrays, registered into qs_strats.SPECS at import so qs_run.run_one
resolves them unchanged.

SHARED BAR-LEVEL FLOW DEFINITIONS (declared, per each sheet's own wording)
    taker_buy  = kline field taker_buy_base
    taker_sell = volume - taker_buy_base
    imbalance  = (taker_buy - taker_sell) / volume = (2*tb - v)/v  in [-1,1]
    CVD delta  = 2*tb - v  (bar-level taker delta); CVD = cumsum
    sell share = (v - tb)/v
  All are BAR-LEVEL approximations of true order flow — the catalog labels
  them PARTIAL for exactly this reason and each sheet declares "bar-level".

DECLARED READINGS not fixed by the sheets:
  * QS-044: pivot k=3 confirmed (known 3 bars after), minimum price
    separation 0.5*ATR (the no_trade rule), stop below the SECOND pivot low,
    2R from that stop, exit when CVD breaks the second pivot's CVD low.
  * QS-048: the run = the last 6 bars (covers the >= 4-bar imbalance run);
    run extreme = the 6-bar high/low; efficiency ratio per bar =
    (|bar return|/ATR) / max(|imbalance|, eps); the 50-bar median of that
    ratio must be beaten DOWN by half; the 50% target = the midpoint of the
    6-bar run range; "volume below its 20th percentile" = 200-bar quantile.
  * QS-049: confirmation is strictly the NEXT bar closing beyond the
    absorption bar's extreme; news filter = volume > 5x SMA(volume,20).
  * QS-050: ATR from the signal bar; up-closing bar = close > open.
  * QS-053: bar return = simple pct change; the impact slope = rolling
    covariance(return, signed volume)/rolling variance(signed volume) over
    100 bars; "its 80th percentile" = a 500-bar rolling quantile of the
    slope (the family's percentile convention); exit median likewise.
  * QS-058: the burst = the last 4 bars containing the 3 imbalance bars;
    burst extreme = the 4-bar high (short fade) with the move measured from
    the close 4 bars back; the 50% target = the midpoint between that prior
    close and the burst extreme; "low volume" flip filter = flip-bar volume
    below SMA(volume,20).
  * QS-093: session VWAP = UTC-day anchored, hlc3, volume-weighted (the
    pack50_core convention); "first 60 minutes" = minute-of-day < 60.

Calibration grids are declared, not swept (the fixed rules run; grid-DSR and
PBO stay pending, the same declared state as family A).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import qs_strats as P
from qs_engine import atr, ema
from pack50_core import session_vwap

SPECS = P.SPECS          # the shared registry (qs_run resolves from here)


def _s(x):
    return pd.Series(np.asarray(x, float))


def _edge(cond):
    c = pd.Series(cond).fillna(False).astype(bool)
    return c & ~c.shift(1, fill_value=False)


def _flow(df):
    tb = df["taker_buy_base"].astype(float)
    v = df["volume"].astype(float)
    imb = ((2.0 * tb - v) / v.replace(0.0, np.nan)).fillna(0.0)
    delta = 2.0 * tb - v
    return tb, v, imb, delta


def _atr_s(df):
    return _s(atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
                  df["close"].to_numpy(float), 14))


def _pct(v, q, win=200):
    return v.rolling(win, min_periods=win).quantile(q)


def _blank(n):
    return pd.Series(np.zeros(n, bool))


# ── QS-043 aggressive imbalance ───────────────────────────────────────────
def _qs043(df, tf):
    c, h, o = df["close"], df["high"], df["open"]
    tb, v, imb, _ = _flow(df)
    a = _atr_s(df)
    run = imb.rolling(3, min_periods=3).min() > 0.20
    brk = c > h.shift(1)
    long_c = run & brk
    run_s = imb.rolling(3, min_periods=3).max() < -0.20
    brk_s = c < df["low"].shift(1)
    short_c = run_s & brk_s
    ok = v >= 0.5 * v.rolling(50, min_periods=50).mean()
    le = _edge(long_c) & ok
    se = _edge(short_c) & ok
    return dict(long_event=le, short_event=se,
                long_exit=imb < 0, short_exit=imb > 0,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=12, atr=a)


P.SPECS["QS-043"] = dict(name="Aggressive buy/sell trade-flow imbalance",
                         build=_qs043)


# ── QS-044 CVD divergence at confirmed pivots ─────────────────────────────
def _qs044(df, tf):
    c, h, l = df["close"], df["high"], df["low"]
    a = _atr_s(df)
    _, _, _, delta = _flow(df)
    cvd = delta.cumsum()
    n = len(c)
    cn = c.to_numpy(float)
    ln = l.to_numpy(float)
    hn = h.to_numpy(float)
    cv = cvd.to_numpy(float)
    an = a.to_numpy(float)
    le = np.zeros(n, bool)
    se = np.zeros(n, bool)
    stop_l = np.full(n, np.nan)
    stop_s = np.full(n, np.nan)
    tp_l = np.full(n, np.nan)
    tp_s = np.full(n, np.nan)
    # confirmed k=3 pivots: center j known at j+3
    K = 3
    piv_lows = []      # (confirm_i, center_j, price, cvd)
    piv_highs = []
    for i in range(2 * K, n):
        j = i - K
        w = ln[j - K:j + K + 1]
        if ln[j] <= w.min() and (w == ln[j]).sum() == 1:
            piv_lows.append((i, j, ln[j], cv[j]))
        w = hn[j - K:j + K + 1]
        if hn[j] >= w.max() and (w == hn[j]).sum() == 1:
            piv_highs.append((i, j, hn[j], cv[j]))
    for k in range(1, len(piv_lows)):
        i2, j2, p2, c2 = piv_lows[k]
        i1, j1, p1, c1 = piv_lows[k - 1]
        if i2 >= len(le):
            break
        if p2 < p1 and c2 > c1 and abs(p2 - p1) >= 0.5 * an[i2]:
            le[i2] = True
            stop_l[i2] = p2
            tp_l[i2] = cn[i2] + 2.0 * (cn[i2] - p2)
    for k in range(1, len(piv_highs)):
        i2, j2, p2, c2 = piv_highs[k]
        i1, j1, p1, c1 = piv_highs[k - 1]
        if i2 >= len(se):
            break
        if p2 > p1 and c2 < c1 and abs(p2 - p1) >= 0.5 * an[i2]:
            se[i2] = True
            stop_s[i2] = p2
            tp_s[i2] = cn[i2] - 2.0 * (p2 - cn[i2])
    # exit: CVD breaks the last pivot's CVD (level ffilled from event bars)
    last_piv_cvd_l = pd.Series(cvd).where(pd.Series(le, index=c.index)).ffill()
    last_piv_cvd_s = pd.Series(cvd).where(pd.Series(se, index=c.index)).ffill()
    cvd_break_l = (cvd < last_piv_cvd_l).fillna(False)
    cvd_break_s = (cvd > last_piv_cvd_s).fillna(False)
    stop_l_s = pd.Series(stop_l, index=c.index)
    stop_s_s = pd.Series(stop_s, index=c.index)
    return dict(long_event=pd.Series(le, index=c.index),
                short_event=pd.Series(se, index=c.index),
                long_exit=cvd_break_l, short_exit=cvd_break_s,
                stop_level_long=stop_l_s, stop_level_short=stop_s_s,
                stop_dist_long=(cn - stop_l_s.where(stop_l_s.notna()).ffill()
                                ).abs().where(stop_l_s.where(le).notna()),
                stop_dist_short=(stop_s_s.where(stop_s_s.notna()).ffill() - cn
                                 ).abs().where(stop_s_s.where(se).notna()),
                tp_dist_long=(2.0 * (cn - stop_l_s.where(stop_l_s.notna()).ffill())
                              ).abs().where(stop_l_s.where(le).notna()),
                tp_dist_short=(2.0 * (stop_s_s.where(stop_s_s.notna()).ffill() - cn)
                               ).abs().where(stop_s_s.where(se).notna()),
                max_hold=80, atr=_s(a))


P.SPECS["QS-044"] = dict(name="Cumulative volume delta divergence",
                         build=_qs044)


# ── QS-048 trade-flow exhaustion ──────────────────────────────────────────
def _qs048(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    tb, v, imb, _ = _flow(df)
    a = _atr_s(df)
    ret = c.pct_change().abs()
    ratio = (ret / a.replace(0, np.nan)) / imb.abs().replace(0, np.nan)
    med50 = ratio.rolling(50, min_periods=50).median()
    inefficient = ratio < 0.5 * med50
    buy_run = imb.rolling(4, min_periods=4).min() > 0.20
    sell_run = imb.rolling(4, min_periods=4).max() < -0.20
    top6 = h.rolling(6, min_periods=6).max()
    bot6 = l.rolling(6, min_periods=6).min()
    mid6 = (top6 + bot6) / 2.0
    blank = pd.Series(np.zeros(len(c), bool), index=c.index)
    ok = v >= _pct(v, 0.20)
    # the EXHAUSTED state is a run whose efficiency has collapsed; the entry
    # is the first down-close (short fade) AFTER that state — the sheet's
    # "enter after a down-closing bar" is a separate trigger bar
    exhausted_buy = (buy_run & inefficient).fillna(False)
    exhausted_sell = (sell_run & inefficient).fillna(False)
    se = _edge(exhausted_buy.shift(1, fill_value=False) & (c < o)) & ok
    stop_s = top6.where(se)
    dist_s = (stop_s - c).clip(upper=3.0 * a).where(se)
    tp_s = (c - mid6).where((c > mid6) & se)          # 50% of the run
    le = _edge(exhausted_sell.shift(1, fill_value=False) & (c > o)) & ok
    stop_l = bot6.where(le)
    dist_l = (c - stop_l).clip(upper=3.0 * a).where(le)
    tp_l = (mid6 - c).where((mid6 > c) & le)
    return dict(long_event=le, short_event=se,
                long_exit=blank, short_exit=blank,
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=10, atr=a)


P.SPECS["QS-048"] = dict(name="Trade-flow exhaustion", build=_qs048)


# ── QS-049 volume absorption ──────────────────────────────────────────────
def _qs049(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    tb, v, imb, _ = _flow(df)
    a = _atr_s(df)
    sma20 = v.rolling(20, min_periods=20).mean()
    sell_share = (v - tb) / v.replace(0, np.nan)
    buy_share = tb / v.replace(0, np.nan)
    rng = h - l
    mid = (h + l) / 2.0
    abs_l = (sell_share > 0.65) & (v > 2 * sma20) & (rng < 0.8 * a) & (c > mid)
    abs_s = (buy_share > 0.65) & (v > 2 * sma20) & (rng < 0.8 * a) & (c < mid)
    news = v > 5 * sma20
    # confirmation: the NEXT bar closes beyond the absorption extreme
    le = _edge(abs_l.shift(1, fill_value=False) & (c > h.shift(1)))         & ~news.shift(1, fill_value=False)
    se = _edge(abs_s.shift(1, fill_value=False) & (c < l.shift(1)))         & ~news.shift(1, fill_value=False)
    abs_low = l.shift(1).where(abs_l.shift(1)).ffill()
    abs_high = h.shift(1).where(abs_s.shift(1)).ffill()
    stop_l = abs_low.where(le)
    stop_s = abs_high.where(se)
    dist_l = (c - stop_l).where(le)
    dist_s = (stop_s - c).where(se)
    tp_l = (2.0 * dist_l).where(le)
    tp_s = (2.0 * dist_s).where(se)
    return dict(long_event=le, short_event=se,
                long_exit=c < abs_low, short_exit=c > abs_high,
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=30, atr=a)


P.SPECS["QS-049"] = dict(name="Volume absorption with price-only confirmation",
                         build=_qs049)


# ── QS-050 flow/price displacement divergence ─────────────────────────────
def _qs050(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    tb, v, imb, delta = _flow(df)
    a = _atr_s(df)
    drop6 = c.shift(6) - c
    rise6 = c - c.shift(6)
    delta6 = delta.rolling(6, min_periods=6).sum()
    vol6 = v.rolling(6, min_periods=6).sum()
    up_close = c > o
    dn_close = c < o
    long_c = (drop6 > 1.5 * a) & (delta6 > 0) & up_close
    short_c = (rise6 > 1.5 * a) & (delta6 < 0) & dn_close
    ok = delta6.abs() >= 0.05 * vol6
    le = _edge(long_c) & ok
    se = _edge(short_c) & ok
    return dict(long_event=le, short_event=se,
                long_exit=delta6 < 0, short_exit=delta6 > 0,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=12, atr=a)


P.SPECS["QS-050"] = dict(name="Trade-flow and price-displacement divergence",
                         build=_qs050)


# ── QS-053 price impact vs signed volume ──────────────────────────────────
def _qs053(df, tf):
    c = df["close"]
    tb, v, imb, delta = _flow(df)
    a = _atr_s(df)
    r = c.pct_change()
    sv = delta
    win = 100
    cov = r.rolling(win, min_periods=win).cov(sv)
    var = sv.rolling(win, min_periods=win).var()
    slope = cov / var.replace(0, np.nan)
    p80 = slope.rolling(500, min_periods=500).quantile(0.80)
    p20 = slope.rolling(500, min_periods=500).quantile(0.20)
    med = slope.rolling(500, min_periods=500).median()
    long_c = (slope > p80) & (sv > 0)
    short_c = (slope < p20) & (sv < 0)   # the MIRROR is the 20th percentile
    le = _edge(long_c)
    se = _edge(short_c)
    return dict(long_event=le, short_event=se,
                long_exit=slope < med, short_exit=slope > -med,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=8, atr=a)


P.SPECS["QS-053"] = dict(name="Price impact versus signed trade volume",
                         build=_qs053)


# ── QS-058 flow reversal after aggressive bursts ──────────────────────────
def _qs058(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    tb, v, imb, _ = _flow(df)
    a = _atr_s(df)
    sma20 = v.rolling(20, min_periods=20).mean()
    imb3 = imb.rolling(3, min_periods=3).min() > 0.30
    imb3s = imb.rolling(3, min_periods=3).max() < -0.30
    prev_c = c.shift(4)
    burst_up = imb3 & ((h.rolling(4, min_periods=4).max() - prev_c) > 2.5 * a)
    burst_dn = imb3s & ((prev_c - l.rolling(4, min_periods=4).min()) > 2.5 * a)
    flip_dn = (imb < 0) & (c < c.shift(1))
    flip_up = (imb > 0) & (c > c.shift(1))
    top4 = h.rolling(4, min_periods=4).max()
    bot4 = l.rolling(4, min_periods=4).min()
    blank = pd.Series(np.zeros(len(c), bool), index=c.index)
    ok = v >= sma20
    se = _edge(flip_dn & burst_up.shift(1, fill_value=False)) & ok
    le = _edge(flip_up & burst_dn.shift(1, fill_value=False)) & ok
    stop_s = top4.where(se)
    dist_s = (stop_s - c).clip(upper=3.0 * a).where(se)
    mid = (top4 + prev_c) / 2.0
    tp_s = (c - mid).where((c > mid) & se)
    stop_l = bot4.where(le)
    dist_l = (c - stop_l).clip(upper=3.0 * a).where(le)
    mid2 = (bot4 + prev_c) / 2.0
    tp_l = (mid2 - c).where((mid2 > c) & le)
    return dict(long_event=le, short_event=se,
                long_exit=blank, short_exit=blank,
                stop_level_long=stop_l, stop_level_short=stop_s,
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=8, atr=a)


P.SPECS["QS-058"] = dict(name="Trade-flow reversal after aggressive execution",
                         build=_qs058)


# ── QS-093 VWAP + flow confluence ─────────────────────────────────────────
def _qs093(df, tf):
    c = df["close"]
    tb, v, imb, _ = _flow(df)
    a = _atr_s(df)
    vwap, _sd = session_vwap(df, "1d")
    vwap = _s(vwap)
    cross_up = (c > vwap) & (c.shift(1) <= vwap.shift(1))
    cross_dn = (c < vwap) & (c.shift(1) >= vwap.shift(1))
    imb2 = imb.rolling(2, min_periods=2).min() > 0.15
    imb2s = imb.rolling(2, min_periods=2).max() < -0.15
    mod = pd.Series((pd.to_datetime(df["ts"], utc=True).dt.hour * 60
                     + pd.to_datetime(df["ts"], utc=True).dt.minute).to_numpy(),
                    index=c.index)
    early = mod < 60
    le = cross_up & imb2 & ~early
    se = cross_dn & imb2s & ~early
    return dict(long_event=le, short_event=se,
                long_exit=c < vwap, short_exit=c > vwap,
                stop_dist_long=_s(2.0 * a), stop_dist_short=_s(2.0 * a),
                max_hold=48, atr=a)


P.SPECS["QS-093"] = dict(name="VWAP plus trade-flow confluence", build=_qs093)


def costs_for(sym, tf):
    return 5.0, 2.0
