#!/usr/bin/env python
"""qs_d_strats.py — strategy-catalog family D (QS-031..QS-040, market
structure and price action). Signal plans registered into qs_strats.SPECS
at import (the qsd adapter resolves from there). Same plan interface as
families A-C; executor semantics in qs_engine.run.

PIVOT MACHINERY (shared): bar i is a pivot high when its high strictly
exceeds the k=3 highs on each side; the pivot is KNOWN only at bar i+k
(confirmation delay, the sheet's own fixed rule) — every consumer below
reads pivots through the confirmation-bar series, never through a rolling
extremum (the ta.pivothigh-is-not-rolling_max class of bug). "Last two
confirmed pivots" state comes from a positional scan over confirmation
bars. Ties produce no pivot (measure-zero on float prices).

Declared gap-fillings (the sheets are silent; nothing swept):
  * QS-031: "stop between 1*ATR and 3*ATR" is enforced as a distance
    band on the swing-low stop: dist = clip(c - last_swing_low, 1, 3)*ATR.
    "Pivot distance under 0.5*ATR" blocks entries closer than half an ATR
    above the broken swing high.
  * QS-032: the impulse leg is the last confirmed up-leg (from the last
    confirmed swing low to the last confirmed swing high, in time order);
    the retracement is measured from the swing high; the TP is the retest
    of that swing high (distance to it) PLUS the 3*ATR trailing stop, both
    wired (the executor carries a target and a ratcheting stop together);
    the stop keeps a 0.1*ATR floor so sizing stays finite.
  * QS-033: the break's own volume (>= 0.7*SMA20) and ADX(14) <= 35 are
    evaluated on the BREAK bar and carried as state; the retest touch is
    a low at or below the CHoCH level within 8 bars of the break, and the
    retest bar closes above the level; TP is 2R (the sheet's primary).
  * QS-034: the zone is the last two confirmed pivot lows (support) or
    highs (resistance) within 0.5*ATR of each other, level = their mean,
    edges = level +- 0.25*ATR; "wicks into the zone" = low <= upper edge;
    touch count = bars whose low reached the upper edge in the last 50
    bars (more than four = exhausted); the stop sits one width beyond the
    far edge (level - 0.5*ATR); TP 2R primary, opposite-zone close as the
    signal exit.
  * QS-035: the range is the 60-bar window ending 20 bars ago (both
    extremes are then at least 20 bars old by construction); qualified
    when height >= 1.5*ATR and each edge has >= 2 touches at the
    0.1*ATR tolerance inside that window; the sweep is a low beyond the
    bottom edge by >= 0.1*ATR closing back inside; the stop is the sweep
    extreme capped at 3*ATR.
  * QS-036: H is the broken confirmed swing high; the retest low must sit
    within 1*ATR of H (the no_trade rule); the trigger bar closes above H
    with a low strictly above the retest low; the entry stop is the
    retest low, the exit is close below H - 0.5*ATR, and the TP is the
    native 3*ATR trailing stop.
  * QS-037: the prior range is the 60 bars before the 8-bar
    consolidation (bars t-68..t-9); the consolidation must sit in its
    upper third (long side); the TP is the prior range high; the stop is
    the consolidation low capped at 3*ATR.
  * QS-038: the run state is evaluated on the bar BEFORE the trigger (the
    sheet's trigger is a down-close AFTER the exhausted run — the same
    sequencing fix the flow audit forced on QS-048); total move = close
    minus the close 5 bars back (the minimal run window); the 50% target
    is the midpoint between the run extreme and the extreme of the five
    bars before the run; the single-bar>3*ATR no_trade uses the 5-bar
    range maximum.
  * QS-039: HTF structure = higher highs and higher lows on confirmed
    HTF pivots (k=3 on the resampled frame, 5m/15m -> 1h, 1h -> 4h),
    mapped back only after the HTF bar closes; both HTF pivot histories
    must exist (the no_trade rule); the LTF break is QS-031's trigger;
    the exit is an LTF lower low or an HTF structure flip; TP is the
    native 3*ATR trailing stop.
  * QS-040: the displacement 50% level is the displacement bar's
    (high+low)/2; the hold window is the 3 bars after it with every low
    above that level; the consolidation high is the highest high of the
    holding bars before the trigger; the stop is the 50% level capped at
    3*ATR; the exits are the native 2*ATR trailing stop and a close below
    the 50% level; the 2.5R take-profit stays the sheet's declared
    variant, not the fixed run.
  * Time stops are the sheets' own max_hold values throughout.
Calibration grids are declared, not swept (the fixed rules run; grid-DSR
and PBO stay pending, the same declared state as families A-C).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import qs_strats as P
from qs_engine import atr, wilder_dmi

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


def _confirmed_pivots(df, k=3):
    """Pivot highs/lows with k-bar confirmation. Returns four Series in df
    row order: the pivot VALUE becomes known (non-NaN) at the confirmation
    bar i+k, never earlier."""
    hi = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    n = len(hi)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(k, n - k):
        if hi[i] > hi[i - k:i].max() and hi[i] > hi[i + 1:i + k + 1].max():
            ph[i + k] = hi[i]
        if lo[i] < lo[i - k:i].min() and lo[i] < lo[i + 1:i + k + 1].min():
            pl[i + k] = lo[i]
    return pd.Series(ph, index=df.index), pd.Series(pl, index=df.index)


def _last_two(conf):
    """(last, prev) values carried forward from a confirmation-bar series:
    last[t] = the newest pivot value known at t, prev[t] = the one before
    it. Positional scan over confirmation bars."""
    v = conf.to_numpy(float)
    n = len(v)
    last = np.full(n, np.nan)
    prev = np.full(n, np.nan)
    l1 = l2 = np.nan
    for j in range(n):
        if not np.isnan(v[j]):
            l2 = l1
            l1 = v[j]
        last[j] = l1
        prev[j] = l2
    return pd.Series(last, index=conf.index), pd.Series(prev, index=conf.index)


def _bars_since(flag):
    """Bars since the most recent True of `flag` (0 on the flag bar itself,
    NaN before the first True). Positional; keeps the input's index."""
    src = pd.Series(flag)
    f = src.fillna(False).astype(bool).to_numpy()
    pos = np.arange(len(f))
    last = pd.Series(np.where(f, pos, np.nan)).ffill().to_numpy()
    out = pos - last
    out[np.isnan(last)] = np.nan
    return pd.Series(out, index=src.index)


def _spaced_edges(flag, window):
    """Rising edges of `flag` that arrive more than `window` bars after
    the previous kept edge; a re-arming edge inside the window continues
    the same episode instead of restarting it."""
    f = pd.Series(flag).fillna(False).astype(bool).to_numpy()
    out = np.zeros(len(f), bool)
    last = -10 ** 9
    for i, v in enumerate(f):
        if v and i - last > window:
            out[i] = True
            last = i
    return pd.Series(out, index=pd.Series(flag).index)


def _htf_ohlc(df, htf_min):
    """Closed-HTF-bar OHLC resampled from the same klines."""
    ts = pd.to_datetime(df["ts"], utc=True)
    g = (df.set_index(ts)
           .resample(f"{htf_min}min", label="left", closed="left")
           .agg({"open": "first", "high": "max", "low": "min",
                 "close": "last"}).dropna())
    return g


# ── QS-031 confirmed swing breakout ───────────────────────────────────────
def _qs031(df, tf):
    c = df["close"]
    a = _atr_s(df)
    ph_conf, pl_conf = _confirmed_pivots(df, 3)
    last_ph, _ = _last_two(ph_conf)
    last_pl, _ = _last_two(pl_conf)
    far_enough = (c - last_ph) > 0.5 * a          # no noise-pivot entries
    long_c = (c > last_ph) & far_enough
    short_c = (c < last_pl) & ((last_pl - c) > 0.5 * a)
    dist_l = (c - last_pl).clip(lower=1.0 * a, upper=3.0 * a).where(long_c)
    dist_s = (last_ph - c).clip(lower=1.0 * a, upper=3.0 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=c < last_pl, short_exit=c > last_ph,
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                max_hold=150, atr=a)


# ── QS-032 trend structure continuation ───────────────────────────────────
def _qs032(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    ph_conf, pl_conf = _confirmed_pivots(df, 3)
    ph_last, ph_prev = _last_two(ph_conf)
    pl_last, pl_prev = _last_two(pl_conf)
    ups = (ph_last > ph_prev) & (pl_last > pl_prev)
    enough = ph_last.notna() & ph_prev.notna() & pl_last.notna() & pl_prev.notna()
    # last confirmed up-leg: the swing low as of the bar where the last
    # swing high was CONFIRMED (the trough before the peak), carried forward
    lo_v = pl_last.where(ph_conf.notna()).ffill()
    hi_v = ph_last
    rng = (hi_v - lo_v).replace(0, np.nan)
    retr = (hi_v - c) / rng
    in_band = (retr >= 0.38) & (retr <= 0.62)
    not_deep = retr <= 0.78
    trig = c > h.shift(1)
    long_c = enough & ups & lo_v.notna() & in_band & not_deep & trig
    # mirror: down-leg (the rally peak as of the last low's confirmation),
    # bounce 38-62% off the low, close below the prior bar's low
    hi_v2 = ph_last.where(pl_conf.notna()).ffill()
    lo_v2 = pl_last
    rng2 = (hi_v2 - lo_v2).replace(0, np.nan)
    retr2 = (c - lo_v2) / rng2
    mirror_ok = (retr2 >= 0.38) & (retr2 <= 0.62) & (retr2 <= 0.78)
    trig2 = c < l.shift(1)
    short_c = enough & (ph_last < ph_prev) & (pl_last < pl_prev) & \
        hi_v2.notna() & mirror_ok & trig2
    tp_l = (hi_v - c).where(long_c & (hi_v > c))
    tp_s = (c - lo_v2).where(short_c & (c > lo_v2))
    dist_l = (c - pl_last).clip(lower=0.1 * a).where(long_c)
    dist_s = (ph_last - c).clip(lower=0.1 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=c < pl_last, short_exit=c > ph_last,
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                trailing_atr_mult=3.0, max_hold=150, atr=a)


# ── QS-033 confirmed change-of-character ──────────────────────────────────
def _qs033(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    v = df["volume"].astype(float)
    ph_conf, pl_conf = _confirmed_pivots(df, 3)
    ph_last, ph_prev = _last_two(ph_conf)
    pl_last, pl_prev = _last_two(pl_conf)
    adx = _adx_s(df, 14)
    # downtrend: lower highs and lower lows
    dn = (ph_last < ph_prev) & (pl_last < pl_prev)
    choch = ph_last                      # the last confirmed lower high
    brk = dn & (c > choch)
    vol_ok = v >= 0.7 * v.rolling(20, min_periods=20).mean()
    adx_ok = adx <= 35.0
    brk_ok = brk & vol_ok & adx_ok
    lvl = choch.where(brk_ok).ffill()    # the CHoCH level in force
    stop_ref = pl_last.where(brk_ok).ffill()   # swing low before the break
    anchor = _spaced_edges(brk_ok, 8)
    since = _bars_since(anchor)
    touch = l <= lvl
    touched = touch.where(since >= 1).astype(float).groupby(anchor.cumsum()).cummax() > 0.5
    long_c = (c > lvl) & touched.astype(bool) & since.between(1, 8)
    dist_l = (c - stop_ref).clip(lower=0.5 * a).where(long_c)
    tp_l = (2.0 * dist_l).where(long_c)
    # mirror: uptrend CHoCH down, retest from below
    up = (ph_last > ph_prev) & (pl_last > pl_prev)
    choch_s = pl_last
    brk_s = up & (c < choch_s)
    brk_s_ok = brk_s & vol_ok & adx_ok
    lvl_s = choch_s.where(brk_s_ok).ffill()
    stop_ref_s = ph_last.where(brk_s_ok).ffill()
    anchor_s = _spaced_edges(brk_s_ok, 8)
    since_s = _bars_since(anchor_s)
    touch_s = h >= lvl_s
    touched_s = touch_s.where(since_s >= 1).astype(float).groupby(anchor_s.cumsum()).cummax() > 0.5
    short_c = (c < lvl_s) & touched_s.astype(bool) & since_s.between(1, 8)
    dist_s = (stop_ref_s - c).clip(lower=0.5 * a).where(short_c)
    tp_s = (2.0 * dist_s).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=c < lvl - 0.5 * a, short_exit=c > lvl_s + 0.5 * a,
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=100, atr=a)


# ── QS-034 support/resistance rejection ───────────────────────────────────
def _qs034(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    ph_conf, pl_conf = _confirmed_pivots(df, 3)
    ph_last, ph_prev = _last_two(ph_conf)
    pl_last, pl_prev = _last_two(pl_conf)
    # support zone: last two confirmed pivot lows within 0.5*ATR
    sup_ok = (pl_last - pl_prev).abs() <= 0.5 * a
    sup_lvl = (pl_last + pl_prev) / 2.0
    sup_top = sup_lvl + 0.25 * a
    # resistance zone: last two confirmed pivot highs within 0.5*ATR
    res_ok = (ph_last - ph_prev).abs() <= 0.5 * a
    res_lvl = (ph_last + ph_prev) / 2.0
    res_bot = res_lvl - 0.25 * a
    wick_in = l <= sup_top
    closes_above = c > sup_lvl
    body = (c - o).abs()
    lower_wick = np.minimum(o, c) - l
    hammer = lower_wick >= 1.5 * body
    # touch exhaustion counts only bars SINCE the zone formed (its second
    # pivot's confirmation) — a zone cannot be "touched" before it exists
    sup_birth = sup_ok & ~sup_ok.shift(1, fill_value=False)
    sup_gid = sup_birth.cumsum()
    touches = ((l <= sup_top) & (sup_gid > 0)).astype(float).groupby(sup_gid).cumsum()
    not_exhausted = touches <= 4
    long_c = sup_ok & wick_in & closes_above & hammer & not_exhausted
    wick_in_s = h >= res_bot
    closes_below = c < res_lvl
    upper_wick = h - np.maximum(o, c)
    shoot = upper_wick >= 1.5 * body
    res_birth = res_ok & ~res_ok.shift(1, fill_value=False)
    res_gid = res_birth.cumsum()
    touches_s = ((h >= res_bot) & (res_gid > 0)).astype(float).groupby(res_gid).cumsum()
    long_ok_vol = touches_s <= 4
    short_c = res_ok & wick_in_s & closes_below & shoot & long_ok_vol
    dist_l = (c - (sup_lvl - 0.5 * a)).where(long_c)
    dist_s = ((res_lvl + 0.5 * a) - c).where(short_c)
    tp_l = (2.0 * dist_l).where(long_c)
    tp_s = (2.0 * dist_s).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=res_ok & (c >= res_lvl),
                short_exit=sup_ok & (c <= sup_lvl),
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=60, atr=a)


# ── QS-035 range sweep and reversal ───────────────────────────────────────
def _qs035(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    # the range window ends 20 bars ago: both extremes are >= 20 bars old
    hh = h.rolling(60, min_periods=60).max().shift(20)
    ll = l.rolling(60, min_periods=60).min().shift(20)
    height = hh - ll
    tol = 0.1 * a
    top_touches = ((h >= hh - tol).rolling(60, min_periods=1).sum())
    bot_touches = ((l <= ll + tol).rolling(60, min_periods=1).sum())
    qualified = (height >= 1.5 * a) & (top_touches >= 2) & (bot_touches >= 2)
    sweep_l = (l < ll - tol) & (c > ll)
    sweep_s = (h > hh + tol) & (c < hh)
    outside2 = ((c < ll) | (c > hh)).rolling(2, min_periods=2).sum() >= 2
    long_c = qualified & sweep_l & ~outside2
    short_c = qualified & sweep_s & ~outside2
    mid = (hh + ll) / 2.0
    sweep_ext_l = l.where(sweep_l).ffill()
    sweep_ext_s = h.where(sweep_s).ffill()
    dist_l = (c - sweep_ext_l).clip(upper=3.0 * a).where(long_c)
    dist_s = (sweep_ext_s - c).clip(upper=3.0 * a).where(short_c)
    tp_l = (mid - c).where(long_c & (mid > c))
    tp_s = (c - mid).where(short_c & (c > mid))
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=30, atr=a)


# ── QS-036 breakout retest on pivots ──────────────────────────────────────
def _qs036(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    ph_conf, _ = _confirmed_pivots(df, 3)
    pl_conf, _ = _confirmed_pivots(df, 3)
    last_ph, _ = _last_two(ph_conf)
    last_pl, _ = _last_two(pl_conf)
    brk = c > last_ph
    lvl = last_ph.where(brk).ffill()
    anchor = _spaced_edges(brk, 10)          # a re-arm inside the window
    since = _bars_since(anchor)              # continues the same episode
    grp = anchor.cumsum()
    # the retest low excludes the trigger bar's own low (a higher low is
    # measured against PRIOR bars' lows only): within-group shift of the
    # running minimum
    retr_low = l.where(since >= 1).groupby(grp).cummin().groupby(grp).shift(1)
    touched = (l <= lvl + 0.25 * a).where(since >= 1).astype(float).groupby(grp).cummax() > 0.5
    not_too_deep = retr_low >= lvl - 1.0 * a
    trig = (c > lvl) & (l > retr_low)
    long_c = trig & touched & not_too_deep & since.between(1, 10)
    brk_s = c < last_pl
    lvl_s = last_pl.where(brk_s).ffill()
    anchor_s = _spaced_edges(brk_s, 10)
    since_s = _bars_since(anchor_s)
    grp_s = anchor_s.cumsum()
    retr_high = h.where(since_s >= 1).groupby(grp_s).cummax().groupby(grp_s).shift(1)
    touched_s = (h >= lvl_s - 0.25 * a).where(since_s >= 1).astype(float).groupby(grp_s).cummax() > 0.5
    not_too_far = retr_high <= lvl_s + 1.0 * a
    trig_s = (c < lvl_s) & (h < retr_high)
    short_c = trig_s & touched_s & not_too_far & since_s.between(1, 10)
    dist_l = (c - retr_low).clip(lower=0.1 * a).where(long_c)
    dist_s = (retr_high - c).clip(lower=0.1 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=c < lvl - 0.5 * a, short_exit=c > lvl_s + 0.5 * a,
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                trailing_atr_mult=3.0, max_hold=120, atr=a)


# ── QS-037 compression inside a prior range ───────────────────────────────
def _qs037(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    # prior range: the 60 bars before the 8-bar consolidation
    pr_hh = h.shift(8).rolling(60, min_periods=60).max()
    pr_ll = l.shift(8).rolling(60, min_periods=60).min()
    pr_rng = pr_hh - pr_ll
    co_hh = h.rolling(8, min_periods=8).max().shift(1)
    co_ll = l.rolling(8, min_periods=8).min().shift(1)
    co_rng = co_hh - co_ll
    compressed = co_rng < 0.4 * pr_rng
    upper_third = co_ll >= pr_ll + (2.0 / 3.0) * pr_rng
    big_range = pr_rng >= 2.0 * a
    long_c = compressed & upper_third & big_range & (c > co_hh)
    lower_third = co_hh <= pr_hh - (2.0 / 3.0) * pr_rng
    short_c = compressed & lower_third & big_range & (c < co_ll)
    dist_l = (c - co_ll).clip(upper=3.0 * a).where(long_c)
    dist_s = (co_hh - c).clip(upper=3.0 * a).where(short_c)
    tp_l = (pr_hh - c).where(long_c & (pr_hh > c))
    tp_s = (c - pr_ll).where(short_c & (c > pr_ll))
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=c < co_ll, short_exit=c > co_hh,
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=60, atr=a)


# ── QS-038 momentum exhaustion reversal ───────────────────────────────────
def _qs038(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    v = df["volume"].astype(float)
    rng = h - l
    up = (c > c.shift(1)).astype(float)
    dn = (c < c.shift(1)).astype(float)
    up_run = up.rolling(5, min_periods=5).min() >= 1.0     # 5 straight up closes
    dn_run = dn.rolling(5, min_periods=5).min() >= 1.0
    move_up = (c - c.shift(5)) > 4.0 * a
    move_dn = (c.shift(5) - c) > 4.0 * a
    decel = rng < 0.6 * rng.shift(1)
    vol_fall = v < v.shift(1)
    not_one_bar = rng.rolling(5, min_periods=5).max() <= 3.0 * a
    # the run state is evaluated on the PRIOR bar; the trigger is a close
    # against the run (down-close after an up-run, up-close after a down-run)
    state_l = up_run & move_up & decel & vol_fall & not_one_bar   # fade short
    state_s = dn_run & move_dn & decel & vol_fall & not_one_bar   # fade long
    run_top = h.rolling(5, min_periods=5).max()
    run_bot = l.rolling(5, min_periods=5).min()
    base_bot = run_bot.shift(5)
    base_top = run_top.shift(5)
    mid_up = (run_top + base_bot) / 2.0
    mid_dn = (run_bot + base_top) / 2.0
    long_c = state_s.shift(1).fillna(False).astype(bool) & (c > c.shift(1))
    short_c = state_l.shift(1).fillna(False).astype(bool) & (c < c.shift(1))
    # the stop sits beyond the RUN extreme (the run's own low/high)
    dist_l = (c - run_bot.shift(1)).clip(upper=3.0 * a).where(long_c)
    dist_s = (run_top.shift(1) - c).clip(upper=3.0 * a).where(short_c)
    tp_l = (mid_dn.shift(1) - c).where(long_c & (mid_dn.shift(1) > c))
    tp_s = (c - mid_up.shift(1)).where(short_c & (c > mid_up.shift(1)))
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=_blank(df), short_exit=_blank(df),
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                tp_dist_long=tp_l, tp_dist_short=tp_s,
                max_hold=20, atr=a)


# ── QS-039 multi-timeframe structural alignment ───────────────────────────
def _htf_structure(df, htf_min):
    """HTF structure state from CONFIRMED HTF pivots (k=3), mapped back to
    the LTF rows only after the HTF bar closes. Returns (up, down, ready)
    boolean arrays in LTF row order."""
    g = _htf_ohlc(df, htf_min)
    gh = pd.DataFrame(dict(open_ts=(g.index.asi8 // 10**6).astype(np.int64),
                           open=g["open"], high=g["high"], low=g["low"],
                           close=g["close"],
                           ts=pd.to_datetime(g.index, utc=True)))
    ph_conf, pl_conf = _confirmed_pivots(gh, 3)
    ph_last, ph_prev = _last_two(ph_conf)
    pl_last, pl_prev = _last_two(pl_conf)
    up = ((ph_last > ph_prev) & (pl_last > pl_prev)).fillna(False)
    dn = ((ph_last < ph_prev) & (pl_last < pl_prev)).fillna(False)
    ready = ph_prev.notna() & pl_prev.notna()
    ts = pd.to_datetime(df["ts"], utc=True)
    idx = pd.DatetimeIndex(ts)
    out = {}
    for nm, ser in (("up", up), ("dn", dn), ("ready", ready)):
        s = pd.Series(ser.to_numpy(), index=g.index + pd.Timedelta(minutes=htf_min))
        out[nm] = s.reindex(idx, method="ffill").fillna(False).to_numpy()
    return out["up"], out["dn"], out["ready"]


def _qs039(df, tf):
    h, l, c = df["high"], df["low"], df["close"]
    a = _atr_s(df)
    up, dn, ready = _htf_structure(df, {"5m": 60, "15m": 60, "1h": 240}[tf])
    ph_conf, pl_conf = _confirmed_pivots(df, 3)
    last_ph, _ = _last_two(ph_conf)
    last_pl, _ = _last_two(pl_conf)
    long_c = pd.Series(up & (c.to_numpy() > last_ph.to_numpy()), index=df.index)
    short_c = pd.Series(dn & (c.to_numpy() < last_pl.to_numpy()), index=df.index)
    dist_l = (c - last_pl).clip(lower=0.5 * a).where(long_c)
    dist_s = (last_ph - c).clip(lower=0.5 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=c < last_pl, short_exit=c > last_ph,
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                trailing_atr_mult=3.0, max_hold=200, atr=a)


# ── QS-040 displacement with continuation ─────────────────────────────────
def _qs040(df, tf):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    a = _atr_s(df)
    rng = h - l
    body_frac = (c - o) / rng.replace(0, np.nan)
    disp_up = (rng > 2.0 * a) & (body_frac > 0.7)
    disp_dn = (rng > 2.0 * a) & (body_frac < -0.7)
    lvl_up = ((h + l) / 2.0).where(disp_up).ffill()
    lvl_dn = ((h + l) / 2.0).where(disp_dn).ffill()
    since_u = _bars_since(disp_up)
    since_d = _bars_since(disp_dn)
    grp_u = disp_up.cumsum()
    grp_d = disp_dn.cumsum()
    # hold: every low since the displacement stayed above its 50% level
    # hold: every bar AFTER the displacement stayed above its 50% level —
    # the displacement bar's own low sits below the midpoint by construction
    # and must not poison the group minimum
    hold_u = (l > lvl_up).where(since_u >= 1).astype(float).groupby(grp_u).cummin() > 0.5
    hold_d = (h < lvl_dn).where(since_d >= 1).astype(float).groupby(grp_d).cummax() > 0.5
    consol_u = h.where(since_u >= 1).groupby(grp_u).cummax()
    consol_d = l.where(since_d >= 1).groupby(grp_d).cummin()
    long_c = hold_u & since_u.between(1, 3) & (c > consol_u.shift(1))
    short_c = hold_d & since_d.between(1, 3) & (c < consol_d.shift(1))
    dist_l = (c - lvl_up).clip(upper=3.0 * a).where(long_c)
    dist_s = (lvl_dn - c).clip(upper=3.0 * a).where(short_c)
    return dict(long_event=_edge(long_c), short_event=_edge(short_c),
                long_exit=c < lvl_up, short_exit=c > lvl_dn,
                stop_level_long=(c - dist_l).where(long_c),
                stop_level_short=(c + dist_s).where(short_c),
                stop_dist_long=dist_l, stop_dist_short=dist_s,
                trailing_atr_mult=2.0, max_hold=60, atr=a)


P.register("QS-031", "Confirmed swing-high/swing-low breakout", _qs031)
P.register("QS-032", "Trend structure continuation", _qs032)
P.register("QS-033", "Confirmed change-of-character reversal", _qs033)
P.register("QS-034", "Support/resistance rejection", _qs034)
P.register("QS-035", "Range sweep and reversal", _qs035)
P.register("QS-036", "Breakout retest (pivot level + higher low)", _qs036)
P.register("QS-037", "Compression inside a prior range", _qs037)
P.register("QS-038", "Momentum exhaustion reversal", _qs038)
P.register("QS-039", "Multi-timeframe structural alignment", _qs039)
P.register("QS-040", "Price displacement with continuation", _qs040)
