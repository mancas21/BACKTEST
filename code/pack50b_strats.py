#!/usr/bin/env python
"""pack50b_strats.py -- the fifty prompts of `crypto_strategy_prompts_50-claude2.md`
turned into explicit rules.

READ THIS BEFORE TRUSTING A NUMBER
    Several prompts are not executable as written. Each of those carries a
    `note=` that states the reading chosen here, so the artifact and the report
    can be challenged on the reading rather than on the arithmetic. The list:

    * Sizing. The pack header says "fixed fractional risk: 1% of equity per
      trade". The engine compounds FULL equity (the repo-wide pack50
      convention), so the two pack reports are comparable. Risk-based sizing
      multiplies returns and drawdowns by a per-trade leverage factor; it does
      not change profit factor, win rate, trade count, or the cost share.
    * Costs. The pack's own block is 0.05% fee and 0.02% slippage per side for
      every prompt; the repo gate cost (5.0 + 0.5 bps) is measured separately
      inside each artifact.
    * S04 "take profit at 2R": R is the 1.5x-ATR stop distance, so the target
      is 3x ATR beyond entry.
    * S06/S24 "take profit at 1.5R / 2R": R is the entry-to-stop distance
      measured on the signal bar's close.
    * S07 "flat by 16:00 UTC" and D11 "flat at 20:00 UTC": the exit fires on
      the first bar at/after the deadline and fills at the NEXT open, one bar
      late, the same no-look-ahead reading every session rule here uses.
    * S16/D17 "exit at z of 0": the book exits when z crosses zero; a fresh
      entry can only happen at |z| >= 2. The 48/72-bar time stop flattens the
      book and allows an immediate re-entry while the entry condition holds.
    * S17 "stop loss at 3 standard deviations": 3 band-widths from the middle
      band, on the adverse side of the entry.
    * S18's volume filter is attached to the LONG side only, as written.
    * D04 the cloud is the one plotted at the current bar (computed 26 bars
      ago), Tenkan/Kijun as written.
    * D05 "12-bar linear regression momentum histogram" is the residual of the
      close against its own fitted 12-bar line (the TTM convention).
    * D07 "flat at the end of the day": the exit fires on the last UTC bar of
      the day and fills at the next day's first open.
    * D13 the swing is FROZEN at the break bar; the retrace must touch the
      0.5-0.618 zone within ten bars of the break and close bullish/bearish.
    * D14 "exit with a Chandelier trailing stop" is emulated as a CLOSE cross
      of the rolling Chandelier line (highest 22-bar high minus 3x ATR(22) for
      longs), with the 2.5x ATR(14) initial stop working intrabar. The
      line-cross exit fills one bar later than a true trailing intrabar stop.
    * D16 the ratio ATR stop/target is measured from the entry ratio against
      ATR(14) of the ratio; a stop flattens the book until the next cross.
    * S08, S23, D08 and D18 are NOT in this file: they need NVDA equity data,
      which does not exist on this machine. They are reported as NO DATA,
      never estimated.
    * S15/S25/D07/D25 read "SPCX" as the SPXUSDT series on disk (1m and 1h
      plain klines; 5m/15m resampled from the 1m file). That series is three
      months long at 1m, which the prompt file itself flags as exploratory.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pack50_core import (Plan, adx_di, atr, bollinger, donchian, ema, heikin_ashi,
                         keltner, macd, rsi, rolling_z, session_vwap, sma,
                         stoch_rsi, supertrend)


def blank(n):
    return np.zeros(n, dtype=bool)


def _n(df):
    return len(df)


def _roll(x, k=1):
    r = np.roll(np.asarray(x, float), k)
    r[:k] = np.nan
    return r


def _rollb(x, k=1):
    """One-bar lag of a BOOLEAN array (False where the lag runs off the start)."""
    r = np.roll(np.asarray(x, bool), k)
    r[:k] = False
    return r


# ══════════════════════════════════════════════════ shared primitives
def stoch(h, l, c, n=14, k=3, d=3):
    """Plain stochastic %K/%D, smoothed."""
    hh = pd.Series(h).rolling(n, min_periods=n).max()
    ll = pd.Series(l).rolling(n, min_periods=n).min()
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = 100.0 * (pd.Series(c) - ll) / (hh - ll)
    kk = raw.rolling(k, min_periods=k).mean()
    dd = kk.rolling(d, min_periods=d).mean()
    return kk.to_numpy(), dd.to_numpy()


def cci(h, l, c, n=20):
    tp = pd.Series((np.asarray(h) + np.asarray(l) + np.asarray(c)) / 3.0)
    sm = tp.rolling(n, min_periods=n).mean()
    md = tp.rolling(n, min_periods=n).apply(
        lambda w: float(np.abs(w - w.mean()).mean()), raw=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        return ((tp - sm) / (0.015 * md)).to_numpy()


def obv(c, v):
    c = np.asarray(c, float)
    direction = np.sign(np.diff(c, prepend=c[0]))
    return np.cumsum(direction * np.asarray(v, float))


def linreg_mom(c, n=12):
    """Residual of the close against its own fitted n-bar line (TTM histogram)."""
    s = pd.Series(np.asarray(c, float))
    t = np.arange(n, dtype=float)
    tm = t.mean()
    denom = ((t - tm) ** 2).sum()

    def fit(w):
        ym = w.mean()
        b = ((t - tm) * (w - ym)).sum() / denom
        return w[-1] - (ym + b * (t[-1] - tm))

    return s.rolling(n, min_periods=n).apply(fit, raw=True).to_numpy()


def ichimoku(h, l, t=9, k=26, s=52):
    hh = lambda n: pd.Series(h).rolling(n, min_periods=n).max().to_numpy()
    ll = lambda n: pd.Series(l).rolling(n, min_periods=n).min().to_numpy()
    tenkan = (hh(t) + ll(t)) / 2.0
    kijun = (hh(k) + ll(k)) / 2.0
    span_a = (tenkan + kijun) / 2.0
    span_b = (hh(s) + ll(s)) / 2.0
    n = len(span_a)
    a_now = np.full(n, np.nan)
    b_now = np.full(n, np.nan)
    a_now[k:] = span_a[:-k]
    b_now[k:] = span_b[:-k]
    return tenkan, kijun, a_now, b_now


def _day_key(df):
    return pd.to_datetime(df["ts"], utc=True).dt.floor("1D")


def _prev_day_hlc(df):
    """Previous UTC day's high / low / close, reindexed onto every bar."""
    day = _day_key(df)
    dly = df.assign(day=day).groupby("day").agg(
        H=("high", "max"), L=("low", "min"), C=("close", "last"))
    px = dly.shift(1).reindex(day).to_numpy()
    return px[:, 0], px[:, 1], px[:, 2]


def _minute_of_day(df):
    ts = pd.to_datetime(df["ts"], utc=True)
    return (ts.dt.hour * 60 + ts.dt.minute).to_numpy()


# ══════════════════════════════════════════════════ stateful pair targets
def zscore_pair_target(z, entry=2.0, stop=3.5, tstop=48):
    """+1 below -entry (long the ratio), -1 above +entry, exit on a zero
    cross, flatten after tstop bars in the book. The |z| >= stop rule
    overrides the entry on the same bar (the p27 convention), so the book is
    flat while the ratio is beyond the stop and re-enters once z is back
    inside the entry band."""
    n = len(z)
    tgt = np.zeros(n, dtype=int)
    cur = 0
    since = 0
    for i in range(n):
        zi = z[i]
        if not np.isnan(zi):
            if cur == 1 and zi > 0:
                cur = 0
            elif cur == -1 and zi < 0:
                cur = 0
            if cur == 0:
                if zi <= -entry:
                    cur, since = 1, 0
                elif zi >= entry:
                    cur, since = -1, 0
            if abs(zi) >= stop:
                cur = 0
        if cur != 0:
            since += 1
            if since >= tstop:
                cur = 0
                since = 0
        tgt[i] = cur
    return tgt


def bband_pair_target(r, bl, bm, bu, sd):
    """Long below the lower band, short above the upper, take profit at the
    middle band. The 3-band-width stop is applied last, so it overrides a
    same-bar entry (the p27 convention)."""
    n = len(r)
    tgt = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        if not (np.isnan(r[i]) or np.isnan(bm[i]) or np.isnan(sd[i])):
            if cur == 1 and r[i] >= bm[i]:
                cur = 0
            elif cur == -1 and r[i] <= bm[i]:
                cur = 0
            if cur == 0:
                if r[i] <= bl[i]:
                    cur = 1
                elif r[i] >= bu[i]:
                    cur = -1
            if abs(r[i] - bm[i]) >= 3.0 * sd[i]:
                cur = 0
        tgt[i] = cur
    return tgt


def trend_pair_target(r, e20, e50, a, stop_atr=2.0, tp_atr=3.0):
    """+1 while EMA20 > EMA50 of the ratio, -1 on the cross down, with the
    ratio ATR stop/target measured from the entry ratio."""
    n = len(r)
    tgt = np.zeros(n, dtype=int)
    cur = 0
    entry = np.nan
    for i in range(1, n):
        if not (np.isnan(e20[i]) or np.isnan(e50[i]) or np.isnan(a[i])
                or np.isnan(r[i]) or np.isnan(e20[i - 1]) or np.isnan(e50[i - 1])):
            up = e20[i] > e50[i]
            dn = e20[i] < e50[i]
            if cur == 1:
                if r[i] <= entry - stop_atr * a[i] or r[i] >= entry + tp_atr * a[i]:
                    cur = 0
            elif cur == -1:
                if r[i] >= entry + stop_atr * a[i] or r[i] <= entry - tp_atr * a[i]:
                    cur = 0
            if cur == 0:
                if up and e20[i - 1] <= e50[i - 1]:
                    cur, entry = 1, r[i]
                elif dn and e20[i - 1] >= e50[i - 1]:
                    cur, entry = -1, r[i]
        tgt[i] = cur
    return tgt


# ══════════════════════════════════════════════════ PART 1: scalping S01-S25
def s01(df):  # BTC 1m: EMA 9/21 cross, EMA200 side, 1x ATR stop, 1.5x ATR target
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e9, e21, e200 = ema(c, 9), ema(c, 21), ema(c, 200)
    a = atr(h, l, c, 14)
    le = (e9 > e21) & (_roll(e9) <= _roll(e21)) & (c > e200)
    se = (e9 < e21) & (_roll(e9) >= _roll(e21)) & (c < e200)
    le[0] = se[0] = False
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - a, stop_short=c + a,
                tp_long=c + 1.5 * a, tp_short=c - 1.5 * a)


def s02(df):  # ETH 5m: pullback to the daily-anchored VWAP, close back above
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e50, e200 = ema(c, 50), ema(c, 200)
    vwap, _ = session_vwap(df, "5m")
    a = atr(h, l, c, 14)
    up = e50 > e200
    dn = e50 < e200        # NOT ~up: during the EMA warmup both must be False
    le = up & (l <= vwap) & (c > vwap)
    se = dn & (h >= vwap) & (c < vwap)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.2 * a, stop_short=c + 1.2 * a,
                tp_long=c + 2 * a, tp_short=c - 2 * a,
                note="'pulls back to' read as the bar trades through the VWAP "
                     "and closes back on the trend side of it")


def s03(df):  # SOL 1m: RSI(2) mean reversion above/below EMA 200
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    r2, e200 = rsi(c, 2), ema(c, 200)
    a = atr(h, l, c, 14)
    le = (r2 < 10) & (c > e200)
    se = (r2 > 90) & (c < e200)
    return Plan(le, se, r2 > 70, r2 < 30,
                stop_long=c - 1.2 * a, stop_short=c + 1.2 * a, time_stop=15)


def s04(df):  # HYPE 5m: BB width squeeze (lowest 20% of 100), breakout
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    width = (bu - bl) / c
    from pack50_core import rank_pct_within
    tight = rank_pct_within(width, 100) <= 0.20
    a = atr(h, l, c, 14)
    return Plan(tight & (c > bu), tight & (c < bl), blank(n), blank(n),
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a,
                tp_long=c + 3.0 * a, tp_short=c - 3.0 * a,
                note="2R = twice the 1.5x-ATR risk")


def s05(df):  # SUI 3m: Donchian 20 breakout with a volume filter
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    hh20, ll20 = donchian(h, l, 20)
    vok = v > 1.5 * sma(v, 20)
    a = atr(h, l, c, 14)
    return Plan((c > hh20) & vok, (c < ll20) & vok, blank(n), blank(n),
                stop_long=c - a, stop_short=c + a,
                tp_long=c + 2 * a, tp_short=c - 2 * a)


def s06(df):  # JUP 5m: StochRSI pullback in trend, stop at the 10-bar low
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    k, d = stoch_rsi(c, 14, 3, 3)
    kp, dp = _roll(k), _roll(d)
    e50 = ema(c, 50)
    ll10 = pd.Series(l).rolling(10, min_periods=10).min().shift(1).to_numpy()
    hh10 = pd.Series(h).rolling(10, min_periods=10).max().shift(1).to_numpy()
    le = (c > e50) & (k > d) & (kp <= dp) & (kp < 20)
    se = (c < e50) & (k < d) & (kp >= dp) & (kp > 80)
    le[0] = se[0] = False
    return Plan(le, se, blank(n), blank(n),
                stop_long=ll10, stop_short=hh10,
                tp_long=c + 1.5 * (c - ll10), tp_short=c - 1.5 * (hh10 - c))


def s07(df):  # BTC 5m: NY-open (13:30 UTC) 15-minute range breakout
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    mod = _minute_of_day(df)
    in_range = (mod >= 13 * 60 + 30) & (mod < 13 * 60 + 45)
    after = mod >= 13 * 60 + 45
    flat = mod >= 16 * 60
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    rh = pd.Series(np.where(in_range, h, np.nan)).groupby(day).transform("max").to_numpy()
    rl = pd.Series(np.where(in_range, l, np.nan)).groupby(day).transform("min").to_numpy()
    le = after & (mod < 16 * 60) & (c > rh)
    se = after & (mod < 16 * 60) & (c < rl)
    lx = blank(n)
    lx[flat] = True                      # exit fills at the next open
    return Plan(le, se, lx, lx.copy(),
                stop_long=rl, stop_short=rh,
                tp_long=c + 1.5 * (c - rl), tp_short=c - 1.5 * (rh - c),
                one_per_day=True,
                note="flat-by-16:00 fills one bar late; R is entry-to-opposite-side")


def s09(df):  # ETH 1m: MACD histogram zero-cross with ADX(14) > 20
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    m, sg, hist = macd(c, 12, 26, 9)
    adx, _, _ = adx_di(h, l, c, 14)
    hp = _roll(hist)
    ok = adx > 20
    le = (hist > 0) & (hp <= 0) & ok
    se = (hist < 0) & (hp >= 0) & ok
    le[0] = se[0] = False
    a = atr(h, l, c, 14)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - a, stop_short=c + a,
                tp_long=c + 1.5 * a, tp_short=c - 1.5 * a)


def s10(df, ctx):  # SOL 5m: Supertrend(10,2) flip with the 1h EMA50 slope
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, line = supertrend(h, l, c, 10, 2.0)
    up_flip = (st == 1) & (_roll(st) == -1)
    dn_flip = (st == -1) & (_roll(st) == 1)
    up_flip[0] = dn_flip[0] = False
    slope_up = ctx["ema50_1h_slope"]
    le = up_flip & slope_up
    se = dn_flip & (~slope_up)
    a = atr(h, l, c, 14)
    r_long = np.where(np.isnan(line), a, np.maximum(c - line, a))
    r_short = np.where(np.isnan(line), a, np.maximum(line - c, a))
    return Plan(le, se, st == -1, st == 1,
                stop_long=line, stop_short=line,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short,
                note="stop at the Supertrend line at entry; 2R from that line")


def s11(df):  # BTC 1m: fade a poke through BB(20, 2.5) when ADX < 18
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.5)
    adx, _, _ = adx_di(h, l, c, 14)
    calm = adx < 18
    a = atr(h, l, c, 14)
    le = calm & (_roll(c) < _roll(bl)) & (c > bl)
    se = calm & (_roll(c) > _roll(bu)) & (c < bu)
    return Plan(le, se, blank(n), blank(n),
                tp_long=bm, tp_short=bm,
                stop_long=c - 1.2 * a, stop_short=c + 1.2 * a,
                note="poke read close-based: the prior close was outside the band")


def s12(df):  # HYPE 1m: expansion-bar momentum continuation
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy(float)
    a = atr(h, l, c, 14)
    big = ((h - l) > 2.5 * a) & (v > 3.0 * sma(v, 20))
    bull = c > o
    le = big & bull
    se = big & (~bull) & (c < o)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - a, stop_short=c + a,
                tp_long=c + 1.5 * a, tp_short=c - 1.5 * a, time_stop=10)


def s13(df):  # SUI 5m: fade a close outside the 2-sigma VWAP band
    n = _n(df)
    c = df["close"].to_numpy(float)
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    vwap, sd = session_vwap(df, "5m")
    up = vwap + 2 * sd
    dn = vwap - 2 * sd
    a = atr(h, l, c, 14)
    have_stop = np.isfinite(a)   # no entry before the ATR stop exists
    le = (_roll(c) < _roll(dn)) & (c > dn) & have_stop
    se = (_roll(c) > _roll(up)) & (c < up) & have_stop
    return Plan(le, se, blank(n), blank(n),
                tp_long=vwap, tp_short=vwap,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a,
                note="session-to-date sigma of close-vwap, as in the core's VWAP")


def s14(df):  # JUP 3m: EMA 8/20/50 ribbon with an RSI(7) 50-cross trigger
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e8, e20, e50 = ema(c, 8), ema(c, 20), ema(c, 50)
    r7 = rsi(c, 7)
    stacked_up = (e8 > e20) & (e20 > e50)
    stacked_dn = (e8 < e20) & (e20 < e50)
    le = stacked_up & (r7 > 50) & (_roll(r7) <= 50)
    se = stacked_dn & (r7 < 50) & (_roll(r7) >= 50)
    le[0] = se[0] = False
    a = atr(h, l, c, 14)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.2 * a, stop_short=c + 1.2 * a,
                tp_long=c + 2 * a, tp_short=c - 2 * a)


def s15(df):  # SPX 5m: EMA20 pullback inside an EMA20>EMA50 trend
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e20, e50 = ema(c, 20), ema(c, 50)
    a = atr(h, l, c, 14)
    le = (e20 > e50) & (l <= e20) & (c > e20)
    se = (e20 < e50) & (h >= e20) & (c < e20)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - a, stop_short=c + a,
                tp_long=c + 1.8 * a, tp_short=c - 1.8 * a)


def s16(a, b):  # ETH/BTC 15m: 100-bar z of the log ratio, +-2 / 0 / 3.5 / 48 bars
    z = rolling_z(np.log(a["close"].to_numpy(float) / b["close"].to_numpy(float)), 100)
    tgt = zscore_pair_target(z, 2.0, 3.5, 48)
    return tgt, "100-bar z of log(ETH/BTC); +1 = long ETH / short BTC"


def s17(a, b):  # SOL/ETH 15m: Bollinger(50,2) on the ratio
    r = a["close"].to_numpy(float) / b["close"].to_numpy(float)
    s = pd.Series(r)
    bm = s.rolling(50, min_periods=50).mean()
    sd = s.rolling(50, min_periods=50).std(ddof=0)
    bl = (bm - 2 * sd).to_numpy()
    bu = (bm + 2 * sd).to_numpy()
    tgt = bband_pair_target(r, bl, bm.to_numpy(), bu, sd.to_numpy())
    return tgt, "+1 = long SOL / short ETH below the lower band"


def s18(df):  # BTC 3m: Keltner breakout, volume filter on the long side
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    vok = v > sma(v, 20)
    le = (c > ku) & vok
    se = c < kl
    r_long = np.where(np.isnan(km), np.nan, np.abs(c - km))
    r_short = np.where(np.isnan(km), np.nan, np.abs(km - c))
    return Plan(le, se, blank(n), blank(n),
                stop_long=km, stop_short=km,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short,
                note="the volume filter attaches to the long side only, as written")


def s19(df):  # ETH 1m: liquidity sweep of the prior 20-bar extreme
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy(float)
    ll20 = pd.Series(l).rolling(20, min_periods=20).min().shift(1).to_numpy()
    hh20 = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy()
    vok = v > 2.0 * sma(v, 20)
    le = (l < ll20) & (c > ll20) & vok
    se = (h > hh20) & (c < hh20) & vok
    return Plan(le, se, blank(n), blank(n),
                stop_long=l * 0.999, stop_short=h * 1.001,
                tp_long=c + 2 * (c - l), tp_short=c - 2 * (h - c),
                note="stop 10 bps beyond the sweep extreme")


def s20(df):  # SOL 3m: Heikin-Ashi flip with an EMA50 filter
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ha_o, ha_h, ha_l, ha_c = heikin_ashi(o, h, l, c)
    green, red = ha_c > ha_o, ha_c < ha_o
    e50 = ema(c, 50)
    a = atr(h, l, c, 14)
    le = green & _rollb(red) & (c > e50)
    se = red & _rollb(green) & (c < e50)
    le[0] = se[0] = False
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.2 * a, stop_short=c + 1.2 * a,
                tp_long=c + 2 * a, tp_short=c - 2 * a)


def s21(df):  # HYPE 15m: CCI(20) reclaim of -100 / rejection of +100
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    x = cci(h, l, c, 20)
    e100 = ema(c, 100)
    a = atr(h, l, c, 14)
    le = (_roll(x) <= -100) & (x > -100) & (c > e100)
    se = (_roll(x) >= 100) & (x < 100) & (c < e100)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a,
                tp_long=c + 2.5 * a, tp_short=c - 2.5 * a)


def s22(df):  # SUI 1m: conviction candle through EMA 20
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy(float)
    e20 = ema(c, 20)
    rng = h - l
    body = np.where(rng > 0, np.abs(c - o) / rng, 0.0)
    conv = (body >= 0.60) & (v > sma(v, 20))
    a = atr(h, l, c, 14)
    le = conv & (c > e20)
    se = conv & (c < e20)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - a, stop_short=c + a,
                tp_long=c + 1.5 * a, tp_short=c - 1.5 * a, time_stop=12)


def s24(df):  # BTC 5m: NR4 inside-bar break with an EMA50 slope filter
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    rng = h - l
    narrow = rng == pd.Series(rng).rolling(4, min_periods=4).min().to_numpy()
    inside = (h < _roll(h)) & (l > _roll(l))
    nr4 = _rollb(narrow & inside)
    e50 = ema(c, 50)
    up_slope = e50 > _roll(e50)
    ph, pl = _roll(h), _roll(l)
    le = nr4 & (c > ph) & up_slope
    se = nr4 & (c < pl) & (~up_slope)
    le[:5] = se[:5] = False
    r_long = np.maximum(c - pl, 1e-9)
    r_short = np.maximum(ph - c, 1e-9)
    return Plan(le, se, blank(n), blank(n),
                stop_long=pl, stop_short=ph,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short)


def s25(df):  # SPX 1m: BB(20,2) reversion with an RSI(7) trigger
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    r7 = rsi(c, 7)
    a = atr(h, l, c, 14)
    le = (c < bl) & (r7 < 25)
    se = (c > bu) & (r7 > 75)
    return Plan(le, se, blank(n), blank(n),
                tp_long=bm, tp_short=bm,
                stop_long=c - 1.3 * a, stop_short=c + 1.3 * a, time_stop=20)


# ══════════════════════════════════════════════════ PART 2: day trading D01-D25
def d01(df):  # BTC 1h: Supertrend(10,3) on the EMA200 side
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, _ = supertrend(h, l, c, 10, 3.0)
    e200 = ema(c, 200)
    up_flip = (st == 1) & (_roll(st) == -1)
    dn_flip = (st == -1) & (_roll(st) == 1)
    up_flip[0] = dn_flip[0] = False
    a = atr(h, l, c, 14)
    return Plan(up_flip & (c > e200), dn_flip & (c < e200), blank(n), blank(n),
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


def d02(df):  # ETH 30m: Donchian 55 breakout
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh55, ll55 = donchian(h, l, 55)
    a = atr(h, l, c, 14)
    return Plan(c > hh55, c < ll55, blank(n), blank(n),
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


def d03(df):  # SOL 1h: EMA 21/55 cross with ADX(14) > 25
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e21, e55 = ema(c, 21), ema(c, 55)
    adx, _, _ = adx_di(h, l, c, 14)
    le = (e21 > e55) & (_roll(e21) <= _roll(e55)) & (adx > 25)
    se = (e21 < e55) & (_roll(e21) >= _roll(e55)) & (adx > 25)
    le[0] = se[0] = False
    a = atr(h, l, c, 14)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 3.5 * a, tp_short=c - 3.5 * a)


def d04(df):  # HYPE 30m: Ichimoku cloud breakout, stop at the Kijun
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tenkan, kijun, sa, sb = ichimoku(h, l)
    top = np.fmax(sa, sb)
    bot = np.fmin(sa, sb)
    a = atr(h, l, c, 14)
    le = (c > top) & (tenkan > kijun)
    se = (c < bot) & (tenkan < kijun)
    r_long = np.where(np.isnan(kijun), a, np.maximum(c - kijun, a))
    r_short = np.where(np.isnan(kijun), a, np.maximum(kijun - c, a))
    return Plan(le, se, blank(n), blank(n),
                stop_long=kijun, stop_short=kijun,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short)


def d05(df):  # SUI 1h: TTM squeeze release in the direction of the momentum
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, _, bu = bollinger(c, 20, 2.0)
    kl, _, ku = keltner(h, l, c, 20, 1.5, 10)
    inside = (bl > kl) & (bu < ku)
    inside = np.where(np.isnan(bl) | np.isnan(kl), False, inside)
    release = inside & (~np.roll(inside, 1).astype(bool))
    release[0] = False
    mom = linreg_mom(c, 12)
    a = atr(h, l, c, 14)
    return Plan(release & (mom > 0), release & (mom < 0), blank(n), blank(n),
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a,
                note="momentum = residual of the close against its 12-bar line")


def d06(df):  # JUP 30m: RSI(14) pullback through 50 inside a trend
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    r = rsi(c, 14)
    e100 = ema(c, 100)
    rp = _roll(r)
    le = (c > e100) & (rp >= 40) & (rp <= 50) & (r > 50)
    se = (c < e100) & (rp >= 50) & (rp <= 60) & (r < 50)
    a = atr(h, l, c, 14)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


def d07(df):  # SPX 1h: previous-day high/low breakout, flat at the day's end
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ph, pl, _ = _prev_day_hlc(df)
    mid = (ph + pl) / 2.0
    le = c > ph
    se = c < pl
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    last_bar = np.zeros(n, dtype=bool)
    last_bar[:-1] = day[:-1] != day[1:]
    last_bar[-1] = True
    lx = blank(n)
    lx[last_bar] = True                  # exit fills at the next day's first open
    return Plan(le, se, lx, lx.copy(),
                stop_long=mid, stop_short=mid,
                tp_long=c + 2 * (c - mid), tp_short=c - 2 * (mid - c),
                one_per_day=True,
                note="flat-at-EOD fills at the next day's open, one bar late")


def d09(df):  # BTC 15m: reclaim of the 00:00-UTC anchored VWAP
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    vwap, _ = session_vwap(df, "15m")
    e50, e200 = ema(c, 50), ema(c, 200)
    below = c < vwap
    above = c > vwap
    a = atr(h, l, c, 14)
    le = (~below) & _roll_all_true(below, 4) & (e50 > e200)
    se = (~above) & _roll_all_true(above, 4) & (e50 < e200)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a,
                tp_long=c + 2.5 * a, tp_short=c - 2.5 * a)


def _roll_all_true(x, k):
    """True where the PREVIOUS k bars were all True (the current bar may be either)."""
    out = np.ones(len(x), dtype=bool)
    for j in range(1, k + 1):
        out &= np.roll(np.asarray(x, bool), j)
    out[:k] = False
    return out


def d10(df):  # ETH 1h: MACD line/signal cross with the EMA200 side
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    m, sg, _ = macd(c, 12, 26, 9)
    e200 = ema(c, 200)
    le = (m > sg) & (_roll(m) <= _roll(sg)) & (c > e200)
    se = (m < sg) & (_roll(m) >= _roll(sg)) & (c < e200)
    le[0] = se[0] = False
    a = atr(h, l, c, 14)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


def d11(df):  # SOL 15m: Asian range (00:00-08:00 UTC) breakout, window 08-20
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    mod = _minute_of_day(df)
    asian = mod < 8 * 60
    active = (mod >= 8 * 60) & (mod < 20 * 60)
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    rh = pd.Series(np.where(asian, h, np.nan)).groupby(day).transform("max").to_numpy()
    rl = pd.Series(np.where(asian, l, np.nan)).groupby(day).transform("min").to_numpy()
    height = np.where(np.isnan(rh) | np.isnan(rl), np.nan, rh - rl)
    le = active & (c > rh)
    se = active & (c < rl)
    lx = blank(n)
    lx[mod >= 20 * 60] = True            # exit fills at the next open
    return Plan(le, se, lx, lx.copy(),
                stop_long=(rh + rl) / 2.0, stop_short=(rh + rl) / 2.0,
                tp_long=c + 1.5 * height, tp_short=c - 1.5 * height,
                one_per_day=True,
                note="flat-at-20:00 fills one bar late")


def d12(df):  # HYPE 1h: Parabolic SAR flip with ADX(14) > 20
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    from pack50_core import psar
    sar = psar(h, l, 0.02, 0.2)
    adx, _, _ = adx_di(h, l, c, 14)
    flip_up = (sar < c) & (_roll(sar) > _roll(c))
    flip_dn = (sar > c) & (_roll(sar) < _roll(c))
    flip_up[0] = flip_dn[0] = False
    a = atr(h, l, c, 14)
    return Plan(flip_up & (adx > 20), flip_dn & (adx > 20), blank(n), blank(n),
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


def d13(df):  # SUI 30m: Fibonacci retrace of a fresh 20-bar swing break
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    hh20, ll20 = donchian(h, l, 20)
    le = blank(n)
    se = blank(n)
    stop_long = np.full(n, np.nan)
    stop_short = np.full(n, np.nan)
    tp_long = np.full(n, np.nan)
    tp_short = np.full(n, np.nan)
    arm = 0                              # +1 long armed, -1 short armed, 0 none
    since = 0
    f_hi = f_lo = np.nan
    for i in range(n):
        if arm != 0:
            since += 1
            rng = f_hi - f_lo
            if arm == 1:
                z = (c[i] - f_lo) / rng if rng > 0 else np.nan
                if c[i] < f_lo or since > 10:
                    arm = 0
                elif 0.5 <= z <= 0.618 and c[i] > o[i]:
                    le[i] = True
                    stop_long[i] = f_lo
                    tp_long[i] = f_lo + 1.272 * rng
                    arm = 0
            else:
                z = (c[i] - f_lo) / rng if rng > 0 else np.nan
                if c[i] > f_hi or since > 10:
                    arm = 0
                elif 0.382 <= z <= 0.5 and c[i] < o[i]:
                    se[i] = True
                    stop_short[i] = f_hi
                    tp_short[i] = f_hi - 1.272 * rng
                    arm = 0
        if arm == 0:
            if not np.isnan(hh20[i]) and c[i] > hh20[i]:
                arm, since, f_hi, f_lo = 1, 0, hh20[i], ll20[i]
            elif not np.isnan(ll20[i]) and c[i] < ll20[i]:
                arm, since, f_hi, f_lo = -1, 0, hh20[i], ll20[i]
    return Plan(le, se, blank(n), blank(n),
                stop_long=stop_long, stop_short=stop_short,
                tp_long=tp_long, tp_short=tp_short,
                note="the 0.5-0.618 zone is measured on the FROZEN swing; "
                     "the short mirror is the 0.382-0.5 zone from the top")


def d14(df):  # JUP 1h: 30-bar-high entry, Chandelier(22, 3x ATR22) exit
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh30 = pd.Series(h).rolling(30, min_periods=30).max().shift(1).to_numpy()
    ll30 = pd.Series(l).rolling(30, min_periods=30).min().shift(1).to_numpy()
    e100 = ema(c, 100)
    a14 = atr(h, l, c, 14)
    a22 = atr(h, l, c, 22)
    hh22 = pd.Series(h).rolling(22, min_periods=22).max().to_numpy()
    ll22 = pd.Series(l).rolling(22, min_periods=22).min().to_numpy()
    chand_long = hh22 - 3.0 * a22
    chand_short = ll22 + 3.0 * a22
    le = (c > hh30) & (c > e100)
    se = (c < ll30) & (c < e100)
    return Plan(le, se, c < chand_long, c > chand_short,
                stop_long=c - 2.5 * a14, stop_short=c + 2.5 * a14,
                note="the Chandelier exit is a close cross of the rolling line; "
                     "the 2.5x ATR(14) initial stop works intrabar")


def d15(df):  # BTC 30m: range reversion with ADX(14) < 20
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    r14 = rsi(c, 14)
    adx, _, _ = adx_di(h, l, c, 14)
    calm = adx < 20
    a = atr(h, l, c, 14)
    le = calm & (c < bl) & (r14 < 30)
    se = calm & (c > bu) & (r14 > 70)
    return Plan(le, se, blank(n), blank(n),
                tp_long=bm, tp_short=bm,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a)


def d16(a, b):  # ETH/BTC 1h: EMA 20/50 of the ratio, ATR(14) stop/target
    r = a["close"].to_numpy(float) / b["close"].to_numpy(float)
    e20 = pd.Series(r).ewm(span=20, adjust=False, min_periods=20).mean().to_numpy()
    e50 = pd.Series(r).ewm(span=50, adjust=False, min_periods=50).mean().to_numpy()
    ar = atr(r, r, r, 14)
    tgt = trend_pair_target(r, e20, e50, ar)
    return tgt, "+1 = long ETH / short BTC while EMA20(ETH/BTC) > EMA50; " \
                "stop 2x / target 3x ATR(14) of the ratio from entry"


def d17(a, b):  # SOL/BTC 1h: 120-bar z of the log ratio, 72-bar time stop
    z = rolling_z(np.log(a["close"].to_numpy(float) / b["close"].to_numpy(float)), 120)
    tgt = zscore_pair_target(z, 2.0, 3.5, 72)
    return tgt, "120-bar z of log(SOL/BTC); +1 = long SOL / short BTC"


def d19(df):  # BTC 1h: previous-day extreme sweep reversal
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    ph, pl, _ = _prev_day_hlc(df)
    mid = (ph + pl) / 2.0
    le = (l < pl) & (c > pl)
    se = (h > ph) & (c < ph)
    return Plan(le, se, blank(n), blank(n),
                stop_long=l * 0.999, stop_short=h * 1.001,
                tp_long=mid, tp_short=mid, one_per_day=True,
                note="stop 10 bps beyond the sweep extreme; TP at the day midpoint")


def d20(df):  # ETH 15m: 40-bar price breakout confirmed by OBV at its own high
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    ob = obv(c, v)
    hh40, ll40 = donchian(h, l, 40)
    ob_hi = pd.Series(ob).rolling(40, min_periods=40).max().to_numpy()
    ob_lo = pd.Series(ob).rolling(40, min_periods=40).min().to_numpy()
    a = atr(h, l, c, 14)
    le = (c > hh40) & (ob >= ob_hi)
    se = (c < ll40) & (ob <= ob_lo)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.8 * a, stop_short=c + 1.8 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


def d21(df):  # SOL 30m: fast Supertrend(7, 2.5) on the EMA100 side
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, _ = supertrend(h, l, c, 7, 2.5)
    e100 = ema(c, 100)
    up_flip = (st == 1) & (_roll(st) == -1)
    dn_flip = (st == -1) & (_roll(st) == 1)
    up_flip[0] = dn_flip[0] = False
    a = atr(h, l, c, 14)
    return Plan(up_flip & (c > e100), dn_flip & (c < e100), blank(n), blank(n),
                stop_long=c - 1.8 * a, stop_short=c + 1.8 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


def d22(df):  # HYPE 15m: Keltner-width squeeze, breakout of the channel
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    from pack50_core import rank_pct_within
    tight = rank_pct_within(ku - kl, 150) <= 0.15
    a = atr(h, l, c, 14)
    r_long = np.where(np.isnan(km), a, np.maximum(c - km, a))
    r_short = np.where(np.isnan(km), a, np.maximum(km - c, a))
    return Plan(tight & (c > ku), tight & (c < kl), blank(n), blank(n),
                stop_long=km, stop_short=km,
                tp_long=c + 2.5 * r_long, tp_short=c - 2.5 * r_short)


def d23(df):  # SUI 15m: daily pivot S1/R1 bounce toward the pivot point
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    ph, pl, pc = _prev_day_hlc(df)
    p = (ph + pl + pc) / 3.0
    r1 = 2 * p - pl
    s1 = 2 * p - ph
    e100 = ema(c, 100)
    a = atr(h, l, c, 14)
    le = (c > e100) & (l <= s1) & (c > s1)
    se = (c < e100) & (h >= r1) & (c < r1)
    return Plan(le, se, blank(n), blank(n),
                tp_long=p, tp_short=p,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a)


def d24(df):  # JUP 15m: stochastic cross with the EMA200 side
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    k, d = stoch(h, l, c, 14, 3, 3)
    kp, dp = _roll(k), _roll(d)
    e200 = ema(c, 200)
    le = (k > d) & (kp <= dp) & (kp < 20) & (c > e200)
    se = (k < d) & (kp >= dp) & (kp > 80) & (c < e200)
    le[0] = se[0] = False
    a = atr(h, l, c, 14)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a,
                tp_long=c + 2.5 * a, tp_short=c - 2.5 * a)


def d25(df):  # SPX 15m: EMA 10/20/50 ribbon with a pullback to EMA20
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e10, e20, e50 = ema(c, 10), ema(c, 20), ema(c, 50)
    a = atr(h, l, c, 14)
    stacked_up = (e10 > e20) & (e20 > e50)
    stacked_dn = (e10 < e20) & (e20 < e50)
    le = stacked_up & (l <= e20) & (c > e10)
    se = stacked_dn & (h >= e20) & (c < e10)
    return Plan(le, se, blank(n), blank(n),
                stop_long=c - 1.8 * a, stop_short=c + 1.8 * a,
                tp_long=c + 3 * a, tp_short=c - 3 * a)


# ══════════════════════════════════════════════════ registry
def costs_for(sym: str, tf: str) -> tuple[float, float]:
    """The claude2 pack's own block, uniform: 0.05% fee and 0.02% slippage
    per side. The repo gate cost is measured separately inside the artifact."""
    return 5.0, 2.0


SPECS = {
    1: dict(sym="BTCUSDT", tf="1m", build=s01, name="EMA 9/21 cross, EMA200 filter"),
    2: dict(sym="ETHUSDT", tf="5m", build=s02, name="daily-VWAP pullback"),
    3: dict(sym="SOLUSDT", tf="1m", build=s03, name="RSI(2) mean reversion"),
    4: dict(sym="HYPEUSDT", tf="5m", build=s04, name="Bollinger squeeze breakout"),
    5: dict(sym="SUIUSDT", tf="3m", build=s05, name="Donchian 20 + volume"),
    6: dict(sym="JUPUSDT", tf="5m", build=s06, name="StochRSI pullback"),
    7: dict(sym="BTCUSDT", tf="5m", build=s07, name="NY-open range breakout"),
    8: dict(sym="NVDA", tf="5m", build=None, name="NVDA opening range breakout",
            no_data="no NVDA series exists on this machine"),
    9: dict(sym="ETHUSDT", tf="1m", build=s09, name="MACD zero-cross + ADX"),
    10: dict(sym="SOLUSDT", tf="5m", build=s10, name="Supertrend + 1h EMA50 slope"),
    11: dict(sym="BTCUSDT", tf="1m", build=s11, name="Bollinger range fade, ADX<18"),
    12: dict(sym="HYPEUSDT", tf="1m", build=s12, name="momentum ignition continuation"),
    13: dict(sym="SUIUSDT", tf="5m", build=s13, name="VWAP deviation fade"),
    14: dict(sym="JUPUSDT", tf="3m", build=s14, name="EMA ribbon + RSI(7)"),
    15: dict(sym="SPXUSDT", tf="5m", build=s15, name="EMA 20 pullback"),
    16: dict(sym="ETHUSDT+BTCUSDT", tf="15m", pair=s16, name="ETH/BTC z-score pair"),
    17: dict(sym="SOLUSDT+ETHUSDT", tf="15m", pair=s17, name="SOL/ETH Bollinger pair"),
    18: dict(sym="BTCUSDT", tf="3m", build=s18, name="Keltner breakout"),
    19: dict(sym="ETHUSDT", tf="1m", build=s19, name="liquidity sweep reversal"),
    20: dict(sym="SOLUSDT", tf="3m", build=s20, name="Heikin-Ashi flip"),
    21: dict(sym="HYPEUSDT", tf="15m", build=s21, name="CCI pullback"),
    22: dict(sym="SUIUSDT", tf="1m", build=s22, name="conviction candle through EMA20"),
    23: dict(sym="NVDA", tf="1m", build=None, name="NVDA session VWAP reclaim",
            no_data="no NVDA series exists on this machine"),
    24: dict(sym="BTCUSDT", tf="5m", build=s24, name="NR4 inside-bar breakout"),
    25: dict(sym="SPXUSDT", tf="1m", build=s25, name="Bollinger mean reversion"),
    26: dict(sym="BTCUSDT", tf="1h", build=d01, name="Supertrend(10,3) + EMA200"),
    27: dict(sym="ETHUSDT", tf="30m", build=d02, name="Donchian 55 breakout"),
    28: dict(sym="SOLUSDT", tf="1h", build=d03, name="EMA 21/55 cross + ADX"),
    29: dict(sym="HYPEUSDT", tf="30m", build=d04, name="Ichimoku cloud breakout"),
    30: dict(sym="SUIUSDT", tf="1h", build=d05, name="TTM squeeze release"),
    31: dict(sym="JUPUSDT", tf="30m", build=d06, name="RSI pullback in trend"),
    32: dict(sym="SPXUSDT", tf="1h", build=d07, name="previous-day high/low breakout"),
    33: dict(sym="NVDA", tf="15m", build=None, name="NVDA 30-minute ORB",
            no_data="no NVDA series exists on this machine"),
    34: dict(sym="BTCUSDT", tf="15m", build=d09, name="anchored VWAP reclaim"),
    35: dict(sym="ETHUSDT", tf="1h", build=d10, name="MACD cross + EMA200"),
    36: dict(sym="SOLUSDT", tf="15m", build=d11, name="Asian range breakout"),
    37: dict(sym="HYPEUSDT", tf="1h", build=d12, name="Parabolic SAR + ADX"),
    38: dict(sym="SUIUSDT", tf="30m", build=d13, name="Fibonacci pullback"),
    39: dict(sym="JUPUSDT", tf="1h", build=d14, name="Chandelier trend follower"),
    40: dict(sym="BTCUSDT", tf="30m", build=d15, name="range reversion, ADX<20"),
    41: dict(sym="ETHUSDT+BTCUSDT", tf="1h", pair=d16, name="ETH/BTC ratio trend pair"),
    42: dict(sym="SOLUSDT+BTCUSDT", tf="1h", pair=d17, name="SOL/BTC z-score pair"),
    43: dict(sym="NVDA", tf="1h", build=None, name="NVDA EMA trend + RSI",
            no_data="no NVDA series exists on this machine"),
    44: dict(sym="BTCUSDT", tf="1h", build=d19, name="previous-day sweep reversal"),
    45: dict(sym="ETHUSDT", tf="15m", build=d20, name="OBV volume breakout"),
    46: dict(sym="SOLUSDT", tf="30m", build=d21, name="fast Supertrend(7,2.5)"),
    47: dict(sym="HYPEUSDT", tf="15m", build=d22, name="Keltner squeeze breakout"),
    48: dict(sym="SUIUSDT", tf="15m", build=d23, name="daily pivot bounce"),
    49: dict(sym="JUPUSDT", tf="15m", build=d24, name="stochastic cross + EMA200"),
    50: dict(sym="SPXUSDT", tf="15m", build=d25, name="EMA ribbon trend"),
}

# report codes: artifact sid -> the prompt's own label
CODE = {}
for _i in range(1, 26):
    CODE[_i] = f"S{_i:02d}"
for _i in range(26, 51):
    CODE[_i] = f"D{_i - 25:02d}"
