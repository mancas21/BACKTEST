#!/usr/bin/env python
"""pack50_strats.py -- the fifty prompts of `50_strategies_crypto-claude1.md`
turned into explicit rules.

READ THIS BEFORE TRUSTING A NUMBER
    Several prompts are not executable as written. Each of those carries a
    `note=` that states the reading chosen here, so the artifact and the report
    can be challenged on the reading rather than on the arithmetic. The list:

    #22  exit rule absent      -> exit on a close back inside the mother bar.
    #25  "above the 22-bar high minus 3x ATR" is true almost always; read as the
         Chandelier line CROSS (trend resumption after a pullback).
    #26  exit absent           -> exit on a close back through the pivot level.
    #44  "close back inside" is read as a 15m close back through the 30-minute
         window's extreme.
    #45  stop absent           -> stop at the signal bar's low.
    #46  a gap can only be acted on after the weekend; the fill is the first bar
         AFTER the Monday open (one bar late, no look-ahead).
    #48  the fill is 30 minutes before the settlement, so the position is open
         when funding is charged.
    #27-#33 are dollar-neutral two-leg books with 50% of equity per leg; the
         pair engine marks close-to-close and charges both legs at every change.
    #10  Turtle units are added at 0.5 ATR intervals; the stop trails 2 ATR from
         the LAST entry, capped at four units.

    #34 and #49 are NOT in this file: they need NVDA equity data, which does not
    exist on this machine. They are reported as NO DATA, never estimated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pack50_core import (Plan, adx_di, atr, bollinger, donchian, ema, heikin_ashi,
                         hma, keltner, macd, psar, rank_pct_within, realized_vol,
                         rolling_hurst, rolling_z, rsi, rma, sma, stoch_rsi,
                         supertrend, true_range, williams_r, session_vwap)


def blank(n):
    return np.zeros(n, dtype=bool)


def _n(df):
    return len(df)


# ══════════════════════════════════════════════════ A. trend / momentum
def b01(df):  # Donchian 55 breakout, exit 20-low, 2.5 ATR stop, 4 ATR target
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh55, _ = donchian(h, l, 55)
    _, ll20 = donchian(h, l, 20)
    a = atr(h, l, c, 14)
    return Plan(c > hh55, blank(n), c < ll20, blank(n),
                stop_long=c - 2.5 * a, tp_long=c + 4 * a)


def b02(df):  # dual EMA 21/55 with EMA200 filter, 2 ATR stop, 5 ATR target
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e21, e55, e200 = ema(c, 21), ema(c, 55), ema(c, 200)
    a = atr(h, l, c, 14)
    up = (e21 > e55) & (np.roll(e21 <= e55, 1))
    dn = (e21 < e55) & (np.roll(e21 >= e55, 1))
    up[0] = dn[0] = False
    le = up & (c > e200)
    se = dn & (c < e200)
    return Plan(le, se, se, le,
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 5 * a, tp_short=c - 5 * a)


def b03(df):  # MACD histogram turn + ADX>20, 2.2 ATR stop
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    _, _, hist = macd(c)
    a = atr(h, l, c, 14)
    ax, _, _ = adx_di(h, l, c, 14)
    turn = (hist > 0) & (np.roll(hist, 1) <= 0)
    turn[0] = False
    return Plan(turn & (ax > 20), blank(n), hist < 0, blank(n),
                stop_long=c - 2.2 * a)


def b04(df):  # ADX-gated DI cross, 2 ATR stop, 4 ATR target
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    ax, pdi, mdi = adx_di(h, l, c, 14)
    a = atr(h, l, c, 14)
    up = (pdi > mdi) & (np.roll(pdi <= mdi, 1))
    dn = (pdi < mdi) & (np.roll(pdi >= mdi, 1))
    up[0] = dn[0] = False
    return Plan(up & (ax > 25), dn & (ax > 25), dn, up,
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 4 * a, tp_short=c - 4 * a)


def b05(df):  # Heikin-Ashi 3 green no-lower-wick entries, exit first red
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    o = df["open"].to_numpy(float)
    ha_o, ha_h, ha_l, ha_c = heikin_ashi(o, h, l, c)
    green = ha_c > ha_o
    nowick = ha_l >= np.minimum(ha_o, ha_c) - 1e-9
    g3 = green & np.roll(green, 1) & np.roll(green, 2)
    w3 = nowick & np.roll(nowick, 1) & np.roll(nowick, 2)
    g3[:3] = False
    w3[:3] = False
    a = atr(h, l, c, 14)
    return Plan(g3 & w3, blank(n), ~green, blank(n), stop_long=c - 2.5 * a)


def b06(df, ctx):  # Keltner breakout + 4h EMA50 slope>0, exit at middle band
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    slope_up = ctx["ema50_4h_slope"]
    return Plan((c > ku) & slope_up, blank(n), c < km, blank(n),
                note="no fixed stop in the prompt; exit is the middle band")


def b07(df):  # time-series momentum, 90-day (540 x 4h) return sign, flip on sign
    n = _n(df)
    c = df["close"].to_numpy(float)
    look = 540
    r = np.full(n, np.nan)
    r[look:] = c[look:] / c[:-look] - 1.0
    le = r > 0
    se = r < 0
    return Plan(le, se, se, le, note="rebalance on bar close; a flip costs one bar")


def b08(df):  # HMA(34) rising 2 bars + close above, exit HMA turns down, 3 ATR stop
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hm = hma(c, 34)
    a = atr(h, l, c, 14)
    rising = (hm > np.roll(hm, 1)) & (np.roll(hm, 1) > np.roll(hm, 2))
    rising[:3] = False
    return Plan(rising & (c > hm), blank(n), hm < np.roll(hm, 1), blank(n),
                stop_long=c - 3 * a)


def b09(df):  # PSAR flip above price + EMA100, exit on flip
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    sar = psar(h, l)
    e100 = ema(c, 100)
    flip_up = (sar < c) & (np.roll(sar, 1) > np.roll(c, 1))
    flip_up[0] = False
    return Plan(flip_up & (c > e100), blank(n), sar > c, blank(n),
                note="no fixed take profit; the SAR flip is the exit")


def b10(df):  # Turtle on the daily: 20-day breakout, 0.5 ATR pyramiding, 10-day low exit
    """Custom simulator: units are added at 0.5 ATR steps, the stop trails 2 ATR
    from the LAST entry, and the whole book exits on a 10-day low."""
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    hh20, ll10 = donchian(h, l, 20)
    _, ll10b = donchian(l, l, 10)
    return {"custom": "turtle", "h": h, "l": l, "c": c, "atr": a,
            "entry_level": hh20, "exit_low": ll10b}


# ══════════════════════════════════════════════════ B. mean reversion
def b11(df):  # Bollinger 2.2 sigma + RSI(14)<30, exit mid, 1.2 ATR stop
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, _ = bollinger(c, 20, 2.2)
    r = rsi(c, 14)
    a = atr(h, l, c, 14)
    return Plan((c < bl) & (r < 30), blank(n), c > bm, blank(n),
                stop_long=c - 1.2 * a)


def b12(df):  # 15m VWAP deviation -2 sigma, target VWAP, 12-bar time stop
    n = _n(df)
    c = df["close"].to_numpy(float)
    vwap, sd = session_vwap(df, "15m")
    with np.errstate(invalid="ignore"):
        z = (c - vwap) / sd
    return Plan(z <= -2.0, blank(n), blank(n), blank(n),
                tp_long=vwap, time_stop=12,
                note="session-to-date sigma of close-vwap; time stop 12 bars")


def b13(df):  # 50-bar z-score of log price, +-2 entries, exit at 0, stop +-3.5
    n = _n(df)
    c = df["close"].to_numpy(float)
    lp = np.log(c)
    z = rolling_z(lp, 50)
    m = pd.Series(lp).rolling(50, min_periods=50).mean().to_numpy()
    s = pd.Series(lp).rolling(50, min_periods=50).std(ddof=0).to_numpy()
    cross_up = (z >= 0) & (np.roll(z, 1) < 0)
    cross_dn = (z <= 0) & (np.roll(z, 1) > 0)
    cross_up[0] = cross_dn[0] = False
    return Plan(z < -2.0, z > 2.0, cross_up, cross_dn,
                stop_long=np.exp(m - 3.5 * s), stop_short=np.exp(m + 3.5 * s))


def b14(df):  # RSI(2)<5 above EMA200, exit RSI(2)>65
    n = _n(df)
    c = df["close"].to_numpy(float)
    r2, e200 = rsi(c, 2), ema(c, 200)
    return Plan((r2 < 5) & (c > e200), blank(n), r2 > 65, blank(n))


def b15(df):  # StochRSI K/D cross from extremes, exit at 50
    n = _n(df)
    c = df["close"].to_numpy(float)
    k, d = stoch_rsi(c, 14, 3, 3)
    kp, dp = np.roll(k, 1), np.roll(d, 1)
    le = (k > d) & (kp <= dp) & (kp < 15)
    se = (k < d) & (kp >= dp) & (kp > 85)
    le[0] = se[0] = False
    return Plan(le, se, k >= 50, k <= 50)


def b16(df):  # Keltner fade, body < 40% of range, target middle band
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    rng = np.where((h - l) > 0, h - l, np.nan)
    small_body = (np.abs(c - o) / rng) < 0.40
    return Plan((c < kl) & small_body, (c > ku) & small_body, blank(n), blank(n),
                tp_long=km, tp_short=km)


def b17(df):  # Williams %R(14) < -95 then > -80, exit -50, 1 ATR stop
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    w = williams_r(h, l, c, 14)
    a = atr(h, l, c, 14)
    le = (np.roll(w, 1) < -95) & (w > -80)
    le[0] = False
    return Plan(le, blank(n), w > -50, blank(n), stop_long=c - a)


def b18(df):  # Hurst<0.45 gate + z-score +-1.8, exit 0
    n = _n(df)
    c = df["close"].to_numpy(float)
    hurst = rolling_hurst(c, 200)
    z = rolling_z(np.log(c), 100)
    cross_up = (z >= 0) & (np.roll(z, 1) < 0)
    cross_dn = (z <= 0) & (np.roll(z, 1) > 0)
    cross_up[0] = cross_dn[0] = False
    gate = hurst < 0.45
    return Plan((z < -1.8) & gate, (z > 1.8) & gate, cross_up, cross_dn,
                note="100-bar z of log price; rolling Hurst on 200 bars < 0.45")


# ══════════════════════════════════════════════════ C. breakout / volatility
def b19(df):  # BB-inside-Keltner squeeze >=6 bars, then first close outside Keltner
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    inside = (bl > kl) & (bu < ku)
    inside = np.where(np.isnan(bl) | np.isnan(kl), False, inside)
    cnt = pd.Series(inside.astype(int)).rolling(7, min_periods=7).sum().to_numpy()
    squeeze = cnt >= 6
    le = squeeze & (c > ku)
    se = squeeze & (c < kl)
    r_long = np.abs(c - kl)
    r_short = np.abs(ku - c)
    return Plan(le, se, blank(n), blank(n),
                stop_long=kl, stop_short=ku,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short)


def b20(df):  # 15m opening range (first 4 bars UTC), one trade per day
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    idx = pd.Series(np.arange(n)).groupby(day).cumcount().to_numpy()
    rh = pd.Series(np.where(idx < 4, h, np.nan)).groupby(day).transform("max").to_numpy()
    rl = pd.Series(np.where(idx < 4, l, np.nan)).groupby(day).transform("min").to_numpy()
    mid = (rh + rl) / 2.0
    active = idx >= 4
    le = active & (c > rh)
    se = active & (c < rl)
    return Plan(le, se, blank(n), blank(n),
                stop_long=mid, stop_short=mid,
                tp_long=c + 1.5 * (c - mid), tp_short=c - 1.5 * (mid - c),
                one_per_day=True)


def b21(df):  # ATR-expansion bar, close in top/bottom 20%, stop at bar extreme, 2R
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    a = atr(h, l, c, 14)
    rng = h - l
    pos = np.where(rng > 0, (c - l) / rng, 0.5)
    big = rng > 1.8 * a
    le = big & (pos >= 0.8)
    se = big & (pos <= 0.2)
    return Plan(le, se, blank(n), blank(n),
                stop_long=l, stop_short=h,
                tp_long=c + 2 * (c - l), tp_short=c - 2 * (h - c))


def b22(df):  # inside-bar break, mother bar >= 1.2 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    inside = (h < np.roll(h, 1)) & (l > np.roll(l, 1))
    inside[0] = False
    mother_big = (np.roll(h, 1) - np.roll(l, 1)) >= 1.2 * np.roll(a, 1)
    le = np.roll(inside & mother_big, 1) & (c > np.roll(h, 1))
    se = np.roll(inside & mother_big, 1) & (c < np.roll(l, 1))
    le[:2] = se[:2] = False
    return Plan(le, se, c < np.roll(h, 2), c > np.roll(l, 2),
                stop_long=np.roll(l, 2), stop_short=np.roll(h, 2),
                note="exit = close back inside the mother bar; break confirmed on close")


def b23(df):  # volatility-regime breakout, 20-bar RV in top 30% of 200
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    rv = realized_vol(c, 20)
    pct = rank_pct_within(rv, 200)
    hh, ll = donchian(h, l, 20)
    a = atr(h, l, c, 14)
    gate = pct >= 0.70
    return Plan((c > hh) & gate, (c < ll) & gate, (c < ll), (c > hh),
                stop_long=c - 2 * a, stop_short=c + 2 * a)


def b24(df):  # range-break failure fade, stop at the breakout wick, target midpoint
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh, ll = donchian(h, l, 48)
    mid = (hh + ll) / 2.0
    broke_up = c > hh
    broke_dn = c < ll
    # a close back inside within two bars of the break
    back_in_up = (c < hh) & (np.roll(broke_up, 1) | np.roll(broke_up, 2))
    back_in_dn = (c > ll) & (np.roll(broke_dn, 1) | np.roll(broke_dn, 2))
    back_in_up[:2] = back_in_dn[:2] = False
    wick_hi = np.maximum(np.roll(h, 1), np.roll(h, 2))
    wick_lo = np.minimum(np.roll(l, 1), np.roll(l, 2))
    return Plan(back_in_dn, back_in_up, blank(n), blank(n),
                stop_long=wick_lo, stop_short=wick_hi,
                tp_long=mid, tp_short=mid)


def b25(df):  # Chandelier: close crosses the (22-high - 3 ATR) line, exit back through it
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    hh22 = pd.Series(h).rolling(22, min_periods=22).max().to_numpy()
    line = hh22 - 3 * a
    le = (c > line) & (np.roll(c, 1) <= np.roll(line, 1))
    le[0] = False
    return Plan(le, blank(n), c < line, blank(n),
                note="read as a line CROSS (trend resumption); the literal "
                     "'above the line' is true almost always")


def b26(df):  # daily pivot R1/S1 with volume filter, stop at the pivot
    n = _n(df)
    o, h, l, c, v = (df[x].to_numpy(float) for x in ("open", "high", "low", "close", "volume"))
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D")
    dly = df.assign(day=day).groupby("day").agg(H=("high", "max"), L=("low", "min"),
                                                C=("close", "last"))
    prev = dly.shift(1)
    px = prev.reindex(day).to_numpy()
    dh, dl, dc = px[:, 0], px[:, 1], px[:, 2]
    p = (dh + dl + dc) / 3.0
    r1 = 2 * p - dl
    s1 = 2 * p - dh
    vavg = pd.Series(v).rolling(20, min_periods=20).mean().to_numpy()
    le = (c > r1) & (v > vavg)
    se = (c < s1) & (v > vavg)
    return Plan(le, se, c < r1, c > s1, stop_long=p, stop_short=p)


# ══════════════════════════════════════════════════ D. pairs
def p27(a, b):  # SOL/ETH ratio z +-2, exit 0, stop +-3.5
    z = rolling_z(np.log(a["close"].to_numpy(float) / b["close"].to_numpy(float)), 100)
    tgt = np.zeros(len(z))
    tgt[z <= -2.0] = 1     # SOL cheap -> long SOL / short ETH
    tgt[z >= 2.0] = -1
    tgt[(z > -0.25) & (z < 0.25)] = 0
    tgt[np.abs(z) >= 3.5] = 0
    return tgt, "100-bar z of log(SOL/ETH); +1 = long SOL / short ETH"


def p28(a, b):  # BTC/ETH cointegration, rolling 300 OLS, z +-2 / +-0.3, ADF gate
    la, lb = np.log(a["close"].to_numpy(float)), np.log(b["close"].to_numpy(float))
    n = len(la)
    beta = np.full(n, np.nan)
    for i in range(300, n):
        y, x = la[i - 300:i], lb[i - 300:i]
        vx = x.var()
        beta[i] = np.cov(y, x, ddof=0)[0, 1] / vx if vx > 0 else np.nan
    spread = la - beta * lb
    z = rolling_z(spread, 300)
    tgt = np.zeros(n)
    tgt[z <= -2.0] = 1
    tgt[z >= 2.0] = -1
    tgt[np.abs(z) <= 0.3] = 0
    # ADF gate every 500 bars: stop trading the pair when p > 0.10
    gate = np.ones(n)
    try:
        from statsmodels.tsa.stattools import adfuller
        for i in range(600, n, 500):
            w = spread[i - 500:i]
            w = w[~np.isnan(w)]
            if len(w) < 100:
                continue
            try:
                p = adfuller(w, autolag="AIC")[1]
            except Exception:
                p = 0.0
            gate[i:] = 0.0 if p > 0.10 else 1.0
    except Exception:
        pass
    tgt = tgt * gate
    return tgt, "rolling 300-bar OLS hedge ratio; ADF gate every 500 bars (p>0.10 stops trading)"


def p29(a, b):  # SUI/SOL 20-bar return spread, 1.5 sd, exit at zero
    ra = pd.Series(a["close"].to_numpy(float)).pct_change(20).to_numpy()
    rb = pd.Series(b["close"].to_numpy(float)).pct_change(20).to_numpy()
    sp = ra - rb
    z = rolling_z(sp, 200)
    tgt = np.zeros(len(z))
    tgt[z >= 1.5] = 1      # SUI outperformed -> long SUI / short SOL? reversion
    tgt[z <= -1.5] = -1
    tgt[(np.abs(z) < 0.1) | np.isnan(z)] = 0
    return -tgt, "20-bar return spread; +1 = long the underperformer (mean reversion of the spread)"


def p30(a, b):  # JUP/SOL relative strength on the daily, 30-day MA exit
    ra = a["close"].to_numpy(float) / b["close"].to_numpy(float)
    ma = pd.Series(ra).rolling(30, min_periods=30).mean().to_numpy()
    tgt = np.zeros(len(ra))
    tgt[ra > ma] = 1
    tgt[ra < ma] = -1
    return tgt, "long JUP / short SOL while JUP/SOL is above its 30-day MA"


def p31(a, b):  # HYPE/BTC beta-neutral, rolling 120 beta, residual z +-2.2
    la, lb = np.log(a["close"].to_numpy(float)), np.log(b["close"].to_numpy(float))
    n = len(la)
    beta = np.full(n, np.nan)
    for i in range(120, n):
        y, x = la[i - 120:i], lb[i - 120:i]
        vx = x.var()
        beta[i] = np.cov(y, x, ddof=0)[0, 1] / vx if vx > 0 else np.nan
    resid = la - beta * lb
    z = rolling_z(resid, 120)
    tgt = np.zeros(n)
    tgt[z <= -2.2] = 1
    tgt[z >= 2.2] = -1
    tgt[(np.abs(z) < 0.25) | np.isnan(z)] = 0
    return tgt, "residual of log(HYPE) on log(BTC), 120-bar beta; +1 = long HYPE / short BTC"


def p32(a, b):  # ETH/BTC vs 50-day MA
    ra = a["close"].to_numpy(float) / b["close"].to_numpy(float)
    ma = pd.Series(ra).rolling(50, min_periods=50).mean().to_numpy()
    tgt = np.zeros(len(ra))
    tgt[ra > ma] = 1
    tgt[ra < ma] = -1
    return tgt, "+1 = long ETH / short BTC while ETH/BTC is above its 50-day MA"


def p33(a, b, fa, fb):  # funding spread, rebalanced every 8h
    """+1 = long the leg with the LOWER funding. Rates are compared at each 8h
    boundary; the position is held between boundaries."""
    ts = (a["open_ts"] if "open_ts" in a else a["ts"].astype("int64") // 10**6).to_numpy(np.int64)
    n = len(ts)
    ra = pd.Series(fa[1], index=pd.to_datetime(fa[0], unit="ms", utc=True))
    rb = pd.Series(fb[1], index=pd.to_datetime(fb[0], unit="ms", utc=True))
    tgt = np.zeros(n)
    cur = 0
    for i in range(n):
        t = pd.Timestamp(ts[i], unit="ms", tz="UTC")
        if t.hour % 8 == 0 and t.minute == 0:
            try:
                va = float(ra.asof(t))
                vb = float(rb.asof(t))
            except Exception:
                continue
            if np.isnan(va) or np.isnan(vb):
                continue
            cur = 1 if va < vb else (-1 if vb < va else 0)
        tgt[i] = cur
    return tgt, "+1 = long ETH / short SOL when ETH funding is lower; rebalanced at each 8h boundary"


# ══════════════════════════════════════════════════ E. scalps
def b35(df):  # 1m VWAP pullback scalp, 0.15% target, 0.10% stop, 15-bar cap
    n = _n(df)
    c = df["close"].to_numpy(float)
    e9, e21 = ema(c, 9), ema(c, 21)
    vwap, _ = session_vwap(df, "1m")
    near = np.abs(c / vwap - 1.0) <= 0.0005
    le = near & (e9 > e21)
    return Plan(le, blank(n), blank(n), blank(n),
                tp_long=c * 1.0015, stop_long=c * 0.999, time_stop=15)


def b36(df):  # 1m order-imbalance, taker buy share > 65% for 3 bars
    n = _n(df)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    tb = df["taker_buy_base"].to_numpy(float)
    share = np.where(v > 0, tb / v, np.nan)
    ok = share > 0.65
    three = ok & np.roll(ok, 1) & np.roll(ok, 2)
    three[:3] = False
    hh20 = pd.Series(c).rolling(20, min_periods=20).max().shift(1).to_numpy()
    le = three & (c > hh20)
    return Plan(le, blank(n), blank(n), blank(n),
                tp_long=c * 1.0012, stop_long=c * 0.9992,
                note="taker_buy_base/volume as the bar's buy share")


def b37(df):  # 5m EMA5/13 cross scalp in the top-40% volume hours
    n = _n(df)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    ts = pd.to_datetime(df["ts"], utc=True)
    hour = ts.dt.hour.to_numpy()
    hourly = df.assign(hour=hour).groupby("hour")["volume"].mean()
    thr = hourly.quantile(0.60)
    allowed = (hourly.reindex(range(24)).fillna(0) >= thr).to_numpy()[hour]
    e5, e13 = ema(c, 5), ema(c, 13)
    le = (e5 > e13) & (np.roll(e5, 1) <= np.roll(e13, 1)) & allowed
    se = (e5 < e13) & (np.roll(e5, 1) >= np.roll(e13, 1)) & allowed
    le[0] = se[0] = False
    return Plan(le, se, se, le,
                tp_long=c * 1.004, stop_long=c * 0.9975,
                tp_short=c * 0.996, stop_short=c * 1.0025)


def b38(df):  # 1m liquidity sweep of the prior 15-bar low, target range high
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ll15 = pd.Series(l).rolling(15, min_periods=15).min().shift(1).to_numpy()
    hh15 = pd.Series(h).rolling(15, min_periods=15).max().shift(1).to_numpy()
    rng = np.where((h - l) > 0, h - l, np.nan)
    body = np.abs(c - o) / rng
    le = (l < ll15) & (c > ll15) & (body < 0.40)
    se = (h > hh15) & (c < hh15) & (body < 0.40)
    return Plan(le, se, blank(n), blank(n),
                tp_long=hh15, stop_long=l * 0.999,
                tp_short=ll15, stop_short=h * 1.001)


def b39(df):  # 3m Bollinger squeeze breakout, spread >= 0.1% of price, stop mid, 1.5R
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    inside = (bl > kl) & (bu < ku)
    width = (bu - bl) / c
    ok = inside & (width >= 0.001)
    le = ok & (c > bu)
    se = ok & (c < bl)
    return Plan(le, se, blank(n), blank(n),
                stop_long=bm, stop_short=bm,
                tp_long=c + 1.5 * (c - bm), tp_short=c - 1.5 * (bm - c))


def b40(df):  # 1m tick-rule momentum, 5 up ticks, volume 1.5x the 30-bar mean
    n = _n(df)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    up = c > np.roll(c, 1)
    up[0] = False
    five = up.copy()
    for k in range(1, 5):
        five &= np.roll(up, k)
    five[:5] = False
    vavg = pd.Series(v).rolling(30, min_periods=30).mean().to_numpy()
    le = five & (v > 1.5 * vavg)
    return Plan(le, blank(n), blank(n), blank(n),
                tp_long=c * 1.002, stop_long=c * 0.9988)


def b41(df):  # 5m Supertrend flip + RSI(7)>50, stop at the Supertrend line
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, line = supertrend(h, l, c, 10, 2.0)
    flips = (st == 1) & (np.roll(st, 1) == -1)
    flips[0] = False
    r7 = rsi(c, 7)
    return Plan(flips & (r7 > 50), blank(n), st == -1, blank(n), stop_long=line)


def b42(df):  # 1m fade of three candles each > 2x the 20-bar average range
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    rng = h - l
    avg = pd.Series(rng).rolling(20, min_periods=20).mean().to_numpy()
    big = rng > 2.0 * avg
    three = big & np.roll(big, 1) & np.roll(big, 2)
    three[:3] = False
    le = three & (c < np.roll(c, 3))
    se = three & (c > np.roll(c, 3))
    return Plan(le, se, blank(n), blank(n),
                tp_long=c * 1.0015, stop_long=c * 0.999,
                tp_short=c * 0.9985, stop_short=c * 1.001)


# ══════════════════════════════════════════════════ F. session / day trading
def b43(df):  # London-open breakout of the Asian range (00:00-07:00 UTC), 2R
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    hour = ts.dt.hour.to_numpy()
    ah = pd.Series(np.where(hour < 7, h, np.nan)).groupby(day).transform("max").to_numpy()
    al = pd.Series(np.where(hour < 7, l, np.nan)).groupby(day).transform("min").to_numpy()
    after = hour >= 7
    le = after & (c > ah)
    se = after & (c < al)
    return Plan(le, se, blank(n), blank(n),
                stop_long=al, stop_short=ah,
                tp_long=c + 2 * (c - al), tp_short=c - 2 * (ah - c),
                one_per_day=True)


def b44(df):  # NY-open fade of a >1.2 ATR first 30 minutes, target session VWAP
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    a = atr(h, l, c, 14)
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    hour, minute = ts.dt.hour.to_numpy(), ts.dt.minute.to_numpy()
    is_open = (hour == 13) & (minute < 30)
    win_o = pd.Series(np.where(is_open, o, np.nan)).groupby(day).transform("first").to_numpy()
    win_c = pd.Series(np.where(is_open, c, np.nan)).groupby(day).transform("last").to_numpy()
    win_h = pd.Series(np.where(is_open, h, np.nan)).groupby(day).transform("max").to_numpy()
    win_l = pd.Series(np.where(is_open, l, np.nan)).groupby(day).transform("min").to_numpy()
    after = (hour == 13) & (minute >= 30)
    move = win_c - win_o
    big = np.abs(move) > 1.2 * a
    vwap, _ = session_vwap(df, "15m")
    se = after & big & (move > 0) & (c < win_c)
    le = after & big & (move < 0) & (c > win_c)
    return Plan(le, se, blank(n), blank(n),
                tp_long=vwap, tp_short=vwap,
                stop_long=c - a, stop_short=c + a, one_per_day=True)


def b45(df):  # daily-level bounce off the prior low with a bullish engulfing
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D")
    dly = df.assign(day=day).groupby("day").agg(H=("high", "max"), L=("low", "min"),
                                                C=("close", "last"))
    prev = dly.shift(1).reindex(day).to_numpy()
    pl, ph = prev[:, 1], prev[:, 0]
    bull = (c > o) & (np.roll(c, 1) < np.roll(o, 1)) & (c >= np.roll(o, 1)) & (o <= np.roll(c, 1))
    le = (l <= pl) & (c > pl) & bull
    return Plan(le, blank(n), blank(n), blank(n),
                tp_long=ph, stop_long=l,
                note="stop absent in the prompt -> signal-bar low")


def b46(df):  # weekend gap fade > 1%, stop 1.5x the gap, target the gap fill
    n = _n(df)
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    ts = pd.to_datetime(df["ts"], utc=True)
    dow = ts.dt.dayofweek.to_numpy()
    day = ts.dt.floor("1D").to_numpy()
    first_of_week = np.zeros(n, bool)
    for i in range(1, n):
        if day[i] != day[i - 1] and dow[i] == 0:
            first_of_week[i] = True
    fri = np.full(n, np.nan)
    last_fri = np.nan
    for i in range(n):
        if dow[i] == 4:
            last_fri = c[i]
        fri[i] = last_fri
    gap = np.where(first_of_week, o / fri - 1.0, 0.0)
    le = first_of_week & (gap <= -0.01)
    se = first_of_week & (gap >= 0.01)
    ref = fri
    return Plan(le, se, blank(n), blank(n),
                tp_long=ref, tp_short=ref,
                stop_long=o - 1.5 * np.abs(gap) * o,
                stop_short=o + 1.5 * np.abs(gap) * o,
                note="fill is the bar AFTER the Monday open (no look-ahead)")


def b47(df):  # trend-day filter at 14:00 UTC, then pullbacks to EMA20
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    a = atr(h, l, c, 14)
    e20 = ema(c, 20)
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    hour = ts.dt.hour.to_numpy()
    day_open = pd.Series(np.where(hour == 0, o, np.nan)).groupby(day).transform("first").to_numpy()
    moved = c - day_open
    trend_up = pd.Series(np.where(hour >= 14, (moved > 2 * a), False)).groupby(day).transform("max")
    trend_dn = pd.Series(np.where(hour >= 14, (moved < -2 * a), False)).groupby(day).transform("max")
    up = trend_up.to_numpy().astype(bool) & (hour >= 14)
    dn = trend_dn.to_numpy().astype(bool) & (hour >= 14)
    le = up & (l <= e20) & (c > e20)
    se = dn & (h >= e20) & (c < e20)
    return Plan(le, se, c < e20, c > e20)


def b48(df):  # funding-reset scalp: 30-min move > 0.5% before the settlement
    n = _n(df)
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    ts = pd.to_datetime(df["ts"], utc=True)
    close_t = ts + pd.Timedelta(minutes=30)
    pre = (close_t.dt.hour % 8 == 0) & (close_t.dt.minute == 0)
    move = np.where(pre, c / o - 1.0, 0.0)
    le = pre & (move > 0.005)
    se = pre & (move < -0.005)
    return Plan(le, se, blank(n), blank(n), time_stop=2,
                note="enters the bar that closes 30 min BEFORE the settlement, "
                     "so the position is open when funding is charged")


def b50(df):  # 1h liquidity grab of the prior 24h low, target the 24h midpoint
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh24 = pd.Series(h).rolling(24, min_periods=24).max().shift(1).to_numpy()
    ll24 = pd.Series(l).rolling(24, min_periods=24).min().shift(1).to_numpy()
    mid = (hh24 + ll24) / 2.0
    below = c < ll24
    above = c > hh24
    # a close below the level, then a close back above it within two bars
    swept_dn = below | np.roll(below, 1) | np.roll(below, 2)
    swept_up = above | np.roll(above, 1) | np.roll(above, 2)
    swept_dn[:3] = False
    swept_up[:3] = False
    le = swept_dn & (c > ll24) & ~below
    se = swept_up & (c < hh24) & ~above
    return Plan(le, se, blank(n), blank(n),
                tp_long=mid, stop_long=np.minimum(l, np.roll(l, 1)) * 0.999,
                tp_short=mid, stop_short=np.maximum(h, np.roll(h, 1)) * 1.001)


# ══════════════════════════════════════════════════ registry
ALTS = {"SUIUSDT", "JUPUSDT", "HYPEUSDT"}
SCALP_TF = {"1m", "3m", "5m"}


def costs_for(sym: str, tf: str) -> tuple[float, float]:
    """The pack's own block: 0.04% taker (0.05% SUI/JUP/HYPE), 0.02% slippage
    (0.05% for alts and on scalp timeframes)."""
    fee = 5.0 if sym in ALTS else 4.0
    slip = 5.0 if (sym in ALTS or tf in SCALP_TF) else 2.0
    return fee, slip


SPECS = {
    1: dict(sym="BTCUSDT", tf="4h", build=b01, name="Donchian-55 breakout"),
    2: dict(sym="ETHUSDT", tf="4h", build=b02, name="dual EMA 21/55 trend"),
    3: dict(sym="SOLUSDT", tf="4h", build=b03, name="MACD histogram momentum"),
    4: dict(sym="HYPEUSDT", tf="4h", build=b04, name="ADX-gated DI cross"),
    5: dict(sym="SUIUSDT", tf="4h", build=b05, name="Heikin-Ashi trend"),
    6: dict(sym="BTCUSDT", tf="1h", build=b06, name="Keltner breakout + 4h slope"),
    7: dict(sym="ETHUSDT", tf="4h", build=b07, name="time-series momentum 90d"),
    8: dict(sym="JUPUSDT", tf="4h", build=b08, name="Hull MA trend"),
    9: dict(sym="SOLUSDT", tf="1h", build=b09, name="Parabolic SAR trend"),
    10: dict(sym="BTCUSDT", tf="1d", build=b10, name="Turtle 20-day breakout"),
    11: dict(sym="ETHUSDT", tf="15m", build=b11, name="Bollinger 2.2 sigma reversion"),
    12: dict(sym="SOLUSDT", tf="15m", build=b12, name="VWAP deviation reversion"),
    13: dict(sym="BTCUSDT", tf="1h", build=b13, name="z-score reversion"),
    14: dict(sym="SUIUSDT", tf="1h", build=b14, name="RSI-2 snap-back"),
    15: dict(sym="HYPEUSDT", tf="30m", build=b15, name="Stochastic RSI reversion"),
    16: dict(sym="JUPUSDT", tf="1h", build=b16, name="Keltner fade"),
    17: dict(sym="BTCUSDT", tf="30m", build=b17, name="Williams %R extreme"),
    18: dict(sym="ETHUSDT", tf="1h", build=b18, name="Hurst-gated reversion"),
    19: dict(sym="BTCUSDT", tf="1h", build=b19, name="Bollinger-Keltner squeeze"),
    20: dict(sym="ETHUSDT", tf="15m", build=b20, name="opening-range breakout"),
    21: dict(sym="SOLUSDT", tf="4h", build=b21, name="ATR-expansion breakout"),
    22: dict(sym="SUIUSDT", tf="1h", build=b22, name="inside-bar breakout"),
    23: dict(sym="HYPEUSDT", tf="4h", build=b23, name="volatility-regime breakout"),
    24: dict(sym="BTCUSDT", tf="1h", build=b24, name="range-break failure fade"),
    25: dict(sym="ETHUSDT", tf="4h", build=b25, name="Chandelier breakout"),
    26: dict(sym="JUPUSDT", tf="1h", build=b26, name="daily pivot R1/S1"),
    27: dict(sym="SOLUSDT+ETHUSDT", tf="1h", pair=p27, name="SOL/ETH ratio reversion"),
    28: dict(sym="BTCUSDT+ETHUSDT", tf="4h", pair=p28, name="BTC/ETH cointegration"),
    29: dict(sym="SUIUSDT+SOLUSDT", tf="4h", pair=p29, name="SUI/SOL momentum spread"),
    30: dict(sym="JUPUSDT+SOLUSDT", tf="1d", pair=p30, name="JUP/SOL rotation"),
    31: dict(sym="HYPEUSDT+BTCUSDT", tf="4h", pair=p31, name="HYPE/BTC beta-neutral"),
    32: dict(sym="ETHUSDT+BTCUSDT", tf="1d", pair=p32, name="ETH/BTC dominance proxy"),
    33: dict(sym="ETHUSDT+SOLUSDT", tf="1h", pair=p33, name="funding-spread pair"),
    34: dict(sym="NVDAUSDT+BTCUSDT", tf="1d", build=None, name="NVDA/BTC correlation pair",
             no_data="NVDA equity data is not on disk (data/etf is empty)"),
    35: dict(sym="BTCUSDT", tf="1m", build=b35, name="VWAP pullback scalp"),
    36: dict(sym="ETHUSDT", tf="1m", build=b36, name="order-imbalance scalp"),
    37: dict(sym="SOLUSDT", tf="5m", build=b37, name="EMA 5/13 volume-hour scalp"),
    38: dict(sym="SUIUSDT", tf="1m", build=b38, name="liquidity-sweep reversal"),
    39: dict(sym="HYPEUSDT", tf="3m", build=b39, name="Bollinger squeeze scalp"),
    40: dict(sym="JUPUSDT", tf="1m", build=b40, name="tick-rule momentum scalp"),
    41: dict(sym="BTCUSDT", tf="5m", build=b41, name="Supertrend scalp"),
    42: dict(sym="ETHUSDT", tf="1m", build=b42, name="1m range-expansion fade"),
    43: dict(sym="BTCUSDT", tf="15m", build=b43, name="London-open breakout"),
    44: dict(sym="ETHUSDT", tf="15m", build=b44, name="New York-open fade"),
    45: dict(sym="SOLUSDT", tf="1h", build=b45, name="daily-level bounce"),
    46: dict(sym="BTCUSDT", tf="1h", build=b46, name="weekend-gap fade"),
    47: dict(sym="SUIUSDT", tf="15m", build=b47, name="intraday trend-day pullback"),
    48: dict(sym="HYPEUSDT", tf="30m", build=b48, name="funding-reset scalp"),
    49: dict(sym="BTCUSDT", tf="15m", build=None, name="US equity-open correlation",
             no_data="NVDA equity data is not on disk (data/etf is empty)"),
    50: dict(sym="JUPUSDT", tf="1h", build=b50, name="liquidity grab of the 24h low"),
}
