#!/usr/bin/env python
"""pack100_strats3.py -- prompts 66..100 (F/G/H families) extending
pack100_strats.SPECS; imported by pack100_strats2."""
from __future__ import annotations

import numpy as np
import pandas as pd

import pack100_strats as P
from pack50b_strats import _day_key, _minute_of_day, _prev_day_hlc, blank
from pack50b_strats import zscore_pair_target

_s = P._s
anyb = P.anyb
xup, xdn = P.xup, P.xdn
_t3 = P._t3
_plan = P._plan
_lvl_plan = P._lvl_plan
S, _std = P.S, P._std
SPECS, CODE = P.SPECS, P.CODE
T2, T3, T21 = P.T2, P.T3, P.T21
nd = "no NVDA series on disk"

rsi = P.rsi_
_roc = P.roc_
atr = P.atr_
ema = P.ema_
sma = P.sma_
don = P.don_
bb = P.bb_
avwap = P._anchored_vwap
from pack50_core import session_vwap
import pack100_strats2 as _P2
_bar_minutes = _P2._bar_minutes




def _pivot_events(lo_or_hi, k=3, high=False):
    """Yield (confirm_bar, center_bar, price) for k-bar fractal pivots."""
    x = lo_or_hi.to_numpy(float)
    n = len(x)
    out = []
    for i in range(2 * k, n):
        j = i - k
        w = x[j - k:j + k + 1]
        if high and x[j] >= w.max() and (w == x[j]).sum() == 1:
            out.append((i, j, x[j]))
        if (not high) and x[j] <= w.min() and (w == x[j]).sum() == 1:
            out.append((i, j, x[j]))
    return out


# ── F. price action / SMC (66-77) ─────────────────────────────────────────
def _f66(d):
    lo20 = d["low"].rolling(20).min()
    hi20 = d["high"].rolling(20).max()
    le = (d["low"] < lo20.shift(1)) & (d["close"] > lo20.shift(1))
    se = (d["high"] > hi20.shift(1)) & (d["close"] < hi20.shift(1))
    return _lvl_plan(d, le, se, d["low"], d["high"], r_mult=2.0,
                     note="66 liquidity sweep; stop beyond the sweep wick; TP 2R")
S("F66", 66, "liquidity sweep reversal", "HYPEUSDT", T3, fn=_f66)


def _f67(d):
    a = P.atr_(*_t3(d), 14)
    disp = (d["high"] - d["low"]) > 1.5 * a
    bull = (d["low"] > d["high"].shift(2)) & disp
    ztop, zbot = P._last_zone(bull, d["low"], d["high"].shift(2))
    zi = pd.Series(np.arange(len(d)), index=d.index).where(bull).ffill()
    mid = (ztop + zbot) / 2.0
    fresh = ((np.arange(len(d)) - zi) <= 100).astype(bool)
    le = (d["low"] <= ztop) & (d["close"] > mid) & fresh
    bear = (d["high"] < d["low"].shift(2)) & disp
    stop, sbot = P._last_zone(bear, d["high"], d["low"].shift(2))
    si = pd.Series(np.arange(len(d)), index=d.index).where(bear).ffill()
    smid = (stop + sbot) / 2.0
    sfresh = ((np.arange(len(d)) - si) <= 100).astype(bool)
    se = (d["high"] >= sbot) & (d["close"] < smid) & sfresh
    return _lvl_plan(d, le, se, zbot, stop, r_mult=2.0,
                     note="67 FVG retest; stop beyond the far gap edge; TP 2R")
S("F67", 67, "Fair Value Gap retest", "SUIUSDT", T3, fn=_f67)


def _f68(d):
    a = P.atr_(*_t3(d), 14)
    disp = ((d["close"] - d["open"]) > 2 * a) & (d["close"] > d["open"])
    obc = disp & (d["close"].shift(1) < d["open"].shift(1))
    otop = d["high"].shift(1).where(obc).ffill()
    obot = d["low"].shift(1).where(obc).ffill()
    oi = pd.Series(np.arange(len(d)), index=d.index).where(obc).ffill()
    fresh = ((np.arange(len(d)) - oi) <= 50).astype(bool) & (oi < np.arange(len(d)) - 1)
    le = (d["low"] <= otop) & (d["close"] > d["open"]) & fresh
    dis_s = ((d["open"] - d["close"]) > 2 * a) & (d["close"] < d["open"])
    obs = dis_s & (d["close"].shift(1) > d["open"].shift(1))
    s_bot = d["low"].shift(1).where(obs).ffill()     # zone bottom (target side)
    s_top = d["high"].shift(1).where(obs).ffill()    # zone top = SHORT STOP (above)
    si = pd.Series(np.arange(len(d)), index=d.index).where(obs).ffill()
    sfresh = ((np.arange(len(d)) - si) <= 50).astype(bool) & (si < np.arange(len(d)) - 1)
    se = (d["high"] >= s_bot) & (d["close"] < d["open"]) & sfresh
    return _lvl_plan(d, le, se, obot, s_top, r_mult=2.0,
                     note="68 order-block retest; stop beyond the block extreme; TP 2R")
S("F68", 68, "order-block retest", "ETHUSDT", T3, fn=_f68)


def _f69(d):
    sh, sl = P._fractals(*_t3(d)[:2], 5)
    bos = xup(d["close"], sh)
    leg_hi = sh.where(bos).ffill()
    leg_lo = sl.where(bos).ffill()
    bi = pd.Series(np.arange(len(d)), index=d.index).where(bos).ffill()
    after = (np.arange(len(d)) - bi) >= 1
    mid = (leg_hi + leg_lo) / 2.0
    le = after & (d["low"] <= mid) & (d["close"] > mid)
    bos_s = xdn(d["close"], sl)
    leg_lo_s = sl.where(bos_s).ffill()
    leg_hi_s = sh.where(bos_s).ffill()
    bis = pd.Series(np.arange(len(d)), index=d.index).where(bos_s).ffill()
    afters = (np.arange(len(d)) - bis) >= 1
    mids = (leg_lo_s + leg_hi_s) / 2.0
    se = afters & (d["high"] >= mids) & (d["close"] < mids)
    return _lvl_plan(d, le, se, leg_lo, leg_hi_s, r_mult=2.0,
                     note="69 BOS pullback to the 50% leg; stop at the impulse pivot; TP 2R")
S("F69", 69, "break-of-structure pullback", "BTCUSDT", T3, fn=_f69)


def _f70(d):
    e50 = P.ema_(d["close"], 50)
    e200 = P.ema_(d["close"], 200)
    pin = P._pin_bull(d["open"], d["high"], d["low"], d["close"])
    le = pin & (d["low"] <= e50) & (d["close"] > e200)
    return _lvl_plan(d, le, None, d["low"], None, xl=d["close"] < e50,
                     r_mult=2.0, note="70 pin bar at EMA50; stop below the pin")
S("F70", 70, "pin-bar at EMA(50) (long)", "JUPUSDT", T3, fn=_f70)


def _f71(d):
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    bull, bear = P._engulf(o, h, l, c)
    lo20 = l.rolling(20).min()
    hi20 = h.rolling(20).max()
    le = bull & (l <= lo20)
    se = bear & (h >= hi20)
    sm20 = P.sma_(c, 20)
    return _lvl_plan(d, le, se, l, h, xl=c > sm20, xs=c < sm20,
                     note="71 engulfing at the 20-bar extreme; stop beyond the candle")
S("F71", 71, "engulfing-at-extreme", "SPXUSDT", T3, fn=_f71)
S("F72", 72, "morning/evening star at BB (NVDA)", "NVDAUSDT", T3, no_data=nd)


def _f73(d):
    """Double bottom: two pivot lows within 1%, 10..40 bars apart; entry on
    the neckline break, target = the pattern height, stop below the 2nd low.
    Stateful over pivot events (few); only the FRESHEST pattern is armed."""
    n = len(d)
    le = np.zeros(n, bool)
    stop_l = np.full(n, np.nan)
    tp_l = np.full(n, np.nan)
    ev = _pivot_events(d["low"], 3, high=False)
    armed = None
    c = d["close"].to_numpy(float)
    h = d["high"].to_numpy(float)
    for k in range(1, len(ev)):
        i2, j2, p2 = ev[k]
        i1, j1, p1 = ev[k - 1]
        if abs(p2 - p1) / p1 <= 0.01 and 10 <= (j2 - j1) <= 40:
            neck = h[j1:j2 + 1].max()
            armed = dict(i=i2, neck=neck, stop=p2, tp=neck + (neck - p2))
        if armed and i2 > armed["i"]:
            pass
    # arm from each pattern's confirmation until the neckline breaks or 40 bars pass
    for k in range(1, len(ev)):
        i2, j2, p2 = ev[k]
        i1, j1, p1 = ev[k - 1]
        if abs(p2 - p1) / p1 <= 0.01 and 10 <= (j2 - j1) <= 40:
            neck = h[j1:j2 + 1].max()
            end = min(n, i2 + 40)
            for i in range(i2, end):
                if c[i] > neck and not le[max(0, i - 1):i].any():
                    le[i] = True
                    stop_l[i] = p2
                    tp_l[i] = neck + (neck - p2)
                    break
    Plan = P.Plan
    return Plan(le, np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool),
                np.where(le, stop_l, np.nan), None,
                np.where(le, tp_l, np.nan), None,
                note="73 double-bottom breakout; first touch of the neckline")
S("F73", 73, "double-bottom breakout", "SOLUSDT", T3, fn=_f73)


def _f74(d):
    """HH/HL structure: enter on the confirmation of the second consecutive
    higher pivot high (with a higher pivot low); exit on a lower low."""
    n = len(d)
    le = np.zeros(n, bool)
    stop_l = np.full(n, np.nan)
    ev = _pivot_events(d["high"], 3, high=True)
    evl = _pivot_events(d["low"], 3, high=False)
    # merge by confirm bar
    import bisect
    bars = sorted(set([e[0] for e in ev] + [e[0] for e in evl]))
    lastH = prevH = lastL = prevL = None
    up = False
    c = d["close"].to_numpy(float)
    l = d["low"].to_numpy(float)
    evmap_h = {e[0]: e for e in ev}
    evmap_l = {e[0]: e for e in evl}
    for b in bars:
        if b in evmap_h:
            _, j, px = evmap_h[b]
            prevH, lastH = lastH, px
        if b in evmap_l:
            _, j, px = evmap_l[b]
            prevL, lastL = lastL, px
        if None not in (prevH, lastH, prevL, lastL):
            was = up
            up = (lastH > prevH) and (lastL > prevL)
            if up and not was:
                le[b] = True
                stop_l[b] = lastL
    le = pd.Series(le, index=d.index)
    stop_l = _s(stop_l).ffill()
    lows = d["low"]
    # exit: a lower low forms (lastL < prevL) — recompute forward as a mask
    ll = l < pd.Series(l).rolling(1).min()  # placeholder; simple trailing exit:
    return P.Plan(le.to_numpy(bool), np.zeros(n, bool),
                  np.zeros(n, bool), np.zeros(n, bool),
                  np.where(le.to_numpy(bool), stop_l.to_numpy(float), np.nan),
                  None, None, None,
                  note="74 HH/HL trend; stop at the last higher low; structural exit approximated by the stop")
S("F74", 74, "market-structure HH/HL trend", "HYPEUSDT", T3, fn=_f74)


def _f75(d):
    """Equal highs: two pivot highs within 0.1%; short the wick-above-and-
    close-back-below; stop above the wick; TP 2R."""
    n = len(d)
    se = np.zeros(n, bool)
    stop_s = np.full(n, np.nan)
    h = d["high"].to_numpy(float)
    c = d["close"].to_numpy(float)
    ev = _pivot_events(d["high"], 3, high=True)
    for k in range(1, len(ev)):
        i2, j2, p2 = ev[k]
        i1, j1, p1 = ev[k - 1]
        if abs(p2 - p1) / p1 <= 0.001:
            lvl = max(p1, p2)
            for i in range(i2 + 1, min(n, i2 + 40)):
                if h[i] > lvl and c[i] < lvl:
                    se[i] = True
                    stop_s[i] = h[i]
                    break
    se = pd.Series(se, index=d.index)
    return _lvl_plan(d, np.zeros(n, bool), se, np.nan, _s(stop_s),
                     r_mult=2.0,
                     note="75 equal-highs grab; stop above the wick; TP 2R")


S("F75", 75, "equal-highs liquidity grab (short)", "SUIUSDT", T3, fn=_f75)


def _f76(d):
    res = d["close"].rolling(50).max().shift(1)
    brk = xup(d["close"], res)
    lvl = res.where(brk).ffill()
    bi = pd.Series(np.arange(len(d)), index=d.index).where(brk).ffill()
    fresh = ((np.arange(len(d)) - bi) <= 30).astype(bool)
    a = P.atr_(*_t3(d), 14)
    le = fresh & (d["low"] <= lvl * 1.001) & (d["close"] > d["open"]) \
        & (d["close"] > lvl)
    stop = lvl - 0.5 * a
    return _lvl_plan(d, le, None, stop, np.nan, r_mult=2.0,
                     note="76 S/R flip retest; stop 0.5 ATR under the level; TP 2R")
S("F76", 76, "support/resistance flip (long)", "ETHUSDT", T3, fn=_f76)


def _f77(d):
    ph, pl, _pc = _prev_day_hlc(d)
    pl, ph = _s(pl), _s(ph)
    pmid = (pl + ph) / 2.0
    le = (d["low"] < pl) & (d["close"] > pl)
    se = (d["high"] > ph) & (d["close"] < ph)
    return _lvl_plan(d, le, se, d["low"], d["high"],
                     tp_l_px=pmid, tp_s_px=pmid,
                     note="77 prev-day extreme sweep; exit at the day midpoint")
S("F77", 77, "previous-day low sweep", "BTCUSDT", T3, fn=_f77)

# ── G. sessions (78-85) ───────────────────────────────────────────────────
S("G80", 80, "New York open momentum (NVDA)", "NVDAUSDT", T2, no_data=nd)


def _g78(d):
    ahi = P._daywin_hi(d, 0, 420)
    alo = P._daywin_lo(d, 0, 420)
    mod = pd.Series(_minute_of_day(d), index=d.index)
    le = (mod >= 420) & (d["close"] > ahi)
    se = (mod >= 420) & (d["close"] < alo)
    off = mod >= 960
    return _lvl_plan(d, le, se, alo, ahi, xl=off, xs=off,
                     note="78 Asia-range breakout; entry after 07:00; flat 16:00")
S("G78", 78, "Asia-range breakout at London", "ETHUSDT", T2, fn=_g78)


def _g79(d):
    mod = pd.Series(_minute_of_day(d), index=d.index)
    day = _day_key(d)
    a_close = d["close"].where(mod < 420).groupby(day).transform("last")
    a = P.atr_(*_t3(d), 14)
    av, _ = session_vwap(d, "1d")
    av = _s(av)
    sig = mod == 450
    se = sig & (d["close"] > a_close + 1.5 * a)
    le = sig & (d["close"] < a_close - 1.5 * a)
    xl = (d["close"] <= av) | (mod >= 720)
    xs = (d["close"] >= av) | (mod >= 720)
    return le, se, xl, xs
_std("G79", 79, "London-open fade", "SOLUSDT", T2,
     lambda d: _g79(d)[0], lambda d: _g79(d)[1], lambda d: _g79(d)[2],
     lambda d: _g79(d)[3], slm=2.0)


def _g81(d):
    hour = pd.Series(_minute_of_day(d), index=d.index) // 60
    r = d["close"].pct_change()
    half = len(d) // 2
    tr = r.iloc[:half].groupby(hour.iloc[:half]).mean()
    best = list(tr.nlargest(3).index)
    worst = list(tr.nsmallest(3).index)
    oos = pd.Series(np.arange(len(d)) >= half, index=d.index)
    le = oos & hour.isin(best)
    se = oos & hour.isin(worst)
    return le, se, None, None
_std("G81", 81, "hour-of-day seasonality", "BTCUSDT", ["1h"],
     lambda d: _g81(d)[0], lambda d: _g81(d)[1], lambda d: _g81(d)[2],
     lambda d: _g81(d)[3], slm=2.0, hold=1)


def _g82(d):
    ts = pd.to_datetime(d["ts"], utc=True)
    dow = ts.dt.dayofweek
    mod = pd.Series(_minute_of_day(d), index=d.index)
    le = (dow == 4) & (mod == 1260)
    xl = (dow == 0) & (mod == 0)
    return _plan(d, le, None, xl, None, slm=3.0,
                 note="82 weekend effect: Friday 21:00 UTC to Monday 00:00 UTC")
_std("G82", 82, "weekend effect (long)", "BTCUSDT", ["1h"],
     lambda d: (pd.to_datetime(d["ts"], utc=True).dt.dayofweek == 4)
     & (pd.Series(_minute_of_day(d), index=d.index) == 1260),
     None,
     lambda d: (pd.to_datetime(d["ts"], utc=True).dt.dayofweek == 0)
     & (pd.Series(_minute_of_day(d), index=d.index) == 0),
     None, slm=3.0)


def _g83(d):
    bm = _bar_minutes(d)
    hold = max(1, 45 // bm)
    mod = pd.Series(_minute_of_day(d), index=d.index)
    sig = mod.isin([450, 930, 1410])
    return _plan(d, sig, None, None, None, slm=2.0, hold=hold,
                 note="83 funding-timestamp run-up: enter 30m before 00/08/16, exit 15m after")
def _g83(d):
    sig = pd.Series(_minute_of_day(d), index=d.index).isin([450, 930, 1410])
    return _plan(d, sig, None, None, None, slm=2.0,
                 hold=max(1, 45 // _bar_minutes(d)),
                 note="83 funding run-up: 30m before 00/08/16 UTC, out 15m after")
S("G83", 83, "funding-timestamp run-up (long)", "SOLUSDT", T2, fn=_g83)


def _g84(d):
    do = P._day_open(d)
    a = P.atr_(*_t3(d), 14)
    mod = pd.Series(_minute_of_day(d), index=d.index)
    se = (mod >= 720) & (d["close"] > do + 1.5 * a)
    le = (mod >= 720) & (d["close"] < do - 1.5 * a)
    off = mod >= 1435
    xl = (d["close"] <= do) | off
    xs = (d["close"] >= do) | off
    return le, se, xl, xs
_std("G84", 84, "daily-open reversion", "HYPEUSDT", T3,
     lambda d: _g84(d)[0], lambda d: _g84(d)[1], lambda d: _g84(d)[2],
     lambda d: _g84(d)[3], slm=2.0)


def _g85(d):
    mod = pd.Series(_minute_of_day(d), index=d.index)
    win = (mod >= 1020) & (mod < 1260)
    r = P.rsi_(d["close"], 14)
    av, _ = session_vwap(d, "1d")
    av = _s(av)
    le = win & (r < 25)
    se = win & (r > 75)
    return le, se, d["close"] >= av, d["close"] <= av
_std("G85", 85, "mid-day-lull mean-reversion", "SUIUSDT", T2,
     lambda d: _g85(d)[0], lambda d: _g85(d)[1], lambda d: _g85(d)[2],
     lambda d: _g85(d)[3], slm=2.0)

# ── H. regimes / confluence / derivatives (86-100) ────────────────────────
def _h86(d):
    adx, _, _ = P.adx_(*_t3(d), 14)
    lo, mid, hi = P.bb_(d["close"], 20, 2.0)
    e20, e50 = P.ema_(d["close"], 20), P.ema_(d["close"], 50)
    le = ((adx < 20) & anyb(d["close"] < lo)) | (xup(e20, e50) & (adx > 25))
    se = ((adx < 20) & anyb(d["close"] > hi)) | (xdn(e20, e50) & (adx > 25))
    xl = (d["close"] > mid) | xdn(e20, e50)
    xs = (d["close"] < mid) | xup(e20, e50)
    return le, se, xl, xs
_std("H86", 86, "ADX regime-switching", "JUPUSDT", T3,
     lambda d: _h86(d)[0], lambda d: _h86(d)[1], lambda d: _h86(d)[2],
     lambda d: _h86(d)[3])
S("H87", 87, "volatility-percentile regime (NVDA)", "NVDAUSDT", T3, no_data=nd)
S("H88", 88, "variance-ratio regime (NVDA)", "NVDAUSDT", T3, no_data=nd)


def _h89(dfa, dfb):
    a = dfa.reset_index(drop=True)
    btc = dfb["close"].reset_index(drop=True)
    e20, e50 = P.ema_(a["close"], 20), P.ema_(a["close"], 50)
    reg = btc > P.ema_(btc, 200)
    le = xup(e20, e50) & reg
    xl = xdn(e20, e50) | (btc < P.ema_(btc, 200))
    return _plan(a, le, None, xl, None, slm=2.0,
                 note="89 BTC-regime-filtered trend; BTC leg hashed")
S("H89", 89, "BTC-regime-filtered trend (long)", "SOLUSDT+BTCUSDT", T3,
  build2=_h89)


def _h90(d, ctx):
    filt = _s(ctx["ema_up_1h"]).reindex(d.index).fillna(False).astype(bool)
    r = P.rsi_(d["close"], 14)
    dip = anyb(r < 35, 10)
    le = anyb((r > 40) & (r.shift(1) <= 40)) & dip & filt
    return _plan(d, le, None, r > 65, None, slm=2.0,
                 note="90 MTF trend+pullback; 1h EMA50>EMA200 filter (closed bars)")


def _h91(d, ctx):
    hi = _s(ctx["don_hi_1h"]).reindex(d.index)
    lo = _s(ctx["don_lo_1h"]).reindex(d.index)
    e21 = P.ema_(d["close"], 21)
    le = d["close"] > hi
    se = d["close"] < lo
    return _plan(d, le, se, d["close"] < e21, d["close"] > e21, slm=2.0,
                 note="91 15m breakout of the 1h Donchian(20)")


def _h92(d):
    r = P.rsi_(d["close"], 14) > 50
    _, _, hist = P.macd_(d["close"], 12, 26, 9)
    h_ok = hist > 0
    e_ok = d["close"] > P.ema_(d["close"], 50)
    all3 = r & h_ok & e_ok
    newly = all3 & ~all3.shift(1).fillna(False)
    le = anyb(newly, 3)
    fails = (~r).astype(int) + (~h_ok).astype(int) + (~e_ok).astype(int)
    return le, None, fails >= 2, None
_std("H92", 92, "RSI + MACD + EMA confluence (long)", "SOLUSDT", T3,
     lambda d: _h92(d)[0], lambda d: _h92(d)[1], lambda d: _h92(d)[2],
     lambda d: _h92(d)[3])


def _h93(d):
    lo, mid, hi = P.bb_(d["close"], 20, 2.0)
    r = P.rsi_(d["close"], 14)
    v = d["volume"] > 1.5 * P.sma_(d["volume"], 20)
    le = (d["close"] < lo) & (r < 30) & v
    return le, None, d["close"] > mid, None
_std("H93", 93, "Bollinger + RSI + volume confluence (long)", "BTCUSDT", T3,
     lambda d: _h93(d)[0], lambda d: _h93(d)[1], lambda d: _h93(d)[2],
     lambda d: _h93(d)[3])
S("H94", 94, "funding-rate extreme fade", "JUPUSDT", T21,
  no_data="no JUP funding history on disk")
S("H95", 95, "open-interest divergence", "SOLUSDT", T21,
  no_data="no OI history on disk (Binance serves days, not months)")
S("H96", 96, "long/short-ratio contrarian", "ETHUSDT", T21,
  no_data="no long/short ratio history on disk")


def _h97(d):
    a = P.atr_(*_t3(d), 14)
    cascade = ((d["open"] - d["close"]) > 3 * a) \
        & (d["volume"] > 3 * P.sma_(d["volume"], 20))
    av, _ = session_vwap(d, "1d")
    le = anyb(cascade)
    return _plan(d, le, None, d["close"] >= _s(av), None, slm=2.0, hold=8,
                 note="97 liquidation-cascade bounce (proxy); exit session VWAP or 8 bars")
_std("H97", 97, "liquidation-cascade bounce (long)", "HYPEUSDT", T3,
     lambda d: anyb(((d["open"] - d["close"]) > 3 * P.atr_(*_t3(d), 14))
                    & (d["volume"] > 3 * P.sma_(d["volume"], 20))),
     None,
     lambda d: d["close"] >= _s(session_vwap(d, "1d")[0]), None,
     slm=2.0, hold=8)


def _h98(d):
    rv = _s(P.realized_vol(d["close"], 24))
    hot = P.rank_pct_within(rv, 200) > 0.9
    hh, ll = P.don_(d["high"], d["low"], 20)
    ll10 = P.don_(d["high"], d["low"], 10)[1]
    le = (d["close"] > hh) & ~hot
    se = (d["close"] < ll) & ~hot
    return le, se, d["close"] < ll10, d["close"] > hh
S("H90", 90, "multi-timeframe trend + pullback (long)", "HYPEUSDT", T2,
  fn=_h90, ctx=True)
S("H91", 91, "multi-timeframe Donchian breakout", "SUIUSDT", ["15m"],
  fn=_h91, ctx=True)
_std("H98", 98, "volatility-filtered Donchian trend", "HYPEUSDT", T3,
     lambda d: _h98(d)[0], lambda d: _h98(d)[1], lambda d: _h98(d)[2],
     lambda d: _h98(d)[3])


def _h99(a, b):
    ra = a["close"].reset_index(drop=True)
    rb = b["close"].reset_index(drop=True)
    r = ra / rb
    z = (r - r.rolling(100).mean()) / r.rolling(100).std()
    tgt = zscore_pair_target(z, entry=2.0, stop=3.5, tstop=48)
    return tgt, ("99 ETH/BTC ratio z reversion; hard stop at |z|>=3.5 "
                 "(the prompt's ATR-on-ratio stop, declared reading)")


def _h100(a, b):
    ra = a["close"].reset_index(drop=True)
    rb = b["close"].reset_index(drop=True)
    r = ra / rb
    e50 = P.ema_(r, 50)
    up = xup(r, e50) & (e50 > e50.shift(1))
    tgt = pd.Series(np.where(up, 1.0, np.where(xdn(r, e50), -1.0, np.nan)),
                    index=r.index).ffill().fillna(0.0)
    return tgt.to_numpy(), ("100 HYPE/BTC ratio trend: long above a rising "
                            "EMA50, short below; flips on the cross")


def costs_for(sym: str, tf: str) -> tuple[float, float]:
    # the pack declares NO cost block: the primary headline IS the repo gate
    return 5.0, 0.5


print("pack100_strats3: complete")


S("H99", 99, "ETH/BTC ratio mean-reversion (dollar-neutral)", "ETHUSDT+BTCUSDT",
  T3, pair=_h99)
S("H100", 100, "HYPE/BTC relative-strength trend (dollar-neutral)",
  "HYPEUSDT+BTCUSDT", T3, pair=_h100)
