#!/usr/bin/env python
"""pack50d_strats.py -- the fifty prompts of
`Downloads/deepseek_markdown_20261027_68930c.md` turned into explicit rules.

READ THIS BEFORE TRUSTING A NUMBER
    Several prompts are not executable as written. Each of those carries a
    `note=` that states the reading chosen here. The list:

    * Data. P30 and P46 need NVDA equity data, which does not exist on this
      machine: they are NOT in this file and are reported NO DATA, never
      estimated. "SPCX" (P47) is the SPXUSDT series on disk (plain 1m klines,
      15m resampled, about three months). Timeframes map as in the pack50b/c
      campaigns: 4H and 1D resampled from the 1h taker files, 30m from 15m,
      3m from 1m.
    * Costs. The pack's own block is explicit: fee 5.0 bps and slippage 2.0 bps
      per side. The repo gate cost (5.0 + 0.5), twice the gate cost, the
      measured breakeven and a zero-cost control are inside every artifact.
    * P31 says "SL = 5 pts, TP = 10 pts (or 1xATR / 2xATR)": the ATR reading
      is used (points are unitless on a perp).
    * Chikou span filter (P05, P49), no look-ahead: the Chikou plotted at bar
      i-26 is close[i], so "Chikou above price" is close[i] > close[i-26].
    * Kumo twist (P49): the Senkou A/B cross is detected on the RAW span
      series at the bar where it is computed (the cloud it projects appears
      26 bars later) -- the no-look-ahead timing.
    * P10 swing structure: a 3-bar fractal pivot (center high above one bar
      each side) is CONFIRMED one bar after the center; the last confirmed
      pivot high/low are tracked forward. Long = close breaks the last
      confirmed swing high while the last confirmed swing low is HIGHER than
      the previous one (an HL), stop at that HL, target 3x ATR; short mirrors.
    * P20 MFI divergence: the low of the last 10 bars is lower than the lowest
      low of the 10 bars before it (price LL) while MFI at that newer low is
      HIGHER than MFI at the older low (MFI HL); short mirrors. Divergence
      window is the 10 bars the prompt allows.
    * P25 NR7 on 15m: "yesterday's high" is the prior BAR's high (crypto has
      no session close); the range filter uses the 7 bars before the NR bar.
    * P31's volume/spread filters: spread < 1 bp is not measurable on klines
      and is dropped (declared); the volume > 2x average filter is kept.
    * P32's "max 3 trades/hour" is enforced by suppressing entry candidates
      beyond the third in any rolling 60-bar window.
    * P34's "skip if the 1m trend is strong" is read as: skip when the EMA50
      slope over the last 5 bars exceeds 1x ATR in magnitude.
    * P44 gap fade: crypto has no CME close, so the gap is Friday's last 1h
      close vs Monday's first 1h open (the weekend gap, as in the pack50
      campaign), measured in 1h ATR(14) units.
    * P50 multi-timeframe: the 1H Supertrend(10,3) direction and the 1H
      ADX(14) > 20 filter are computed on 1h-resampled bars and mapped onto
      the 15m book with only fully closed 1h bars (the pack50b convention).
      P35's "direction of the 1H EMA50" uses the same mapping.
    * Session windows are UTC throughout: Asian 00:00-08:00, London 08:00,
      New York 13:30.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pack50_core import (Plan, adx_di, atr, bollinger, donchian, ema, keltner,
                         macd, psar, rsi, session_vwap, sma, supertrend)


def blank(n):
    return np.zeros(n, dtype=bool)


def _n(df):
    return len(df)


def _roll(x, k=1):
    r = np.roll(np.asarray(x, float), k)
    r[:k] = np.nan
    return r


def _rollb(x, k=1):
    r = np.roll(np.asarray(x, bool), k)
    r[:k] = False
    return r


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
    return tenkan, kijun, a_now, b_now, span_a, span_b


def obv(c, v):
    c = np.asarray(c, float)
    return np.cumsum(np.sign(np.diff(c, prepend=c[0])) * np.asarray(v, float))


def stoch_rsi(c, n=14, k=3, d=3):
    r = pd.Series(rsi(c, n))
    lo = r.rolling(n, min_periods=n).min()
    hi = r.rolling(n, min_periods=n).max()
    with np.errstate(divide="ignore", invalid="ignore"):
        st = 100.0 * (r - lo) / (hi - lo)
    kk = st.rolling(k, min_periods=k).mean().to_numpy()
    dd = pd.Series(kk).rolling(d, min_periods=d).mean().to_numpy()
    return kk, dd


def linreg_slope_r2(c, n=50):
    """Slope of the n-bar linear regression and its R-squared (corr^2 form)."""
    s = pd.Series(np.asarray(c, float))
    t = np.arange(n, dtype=float)
    tm = t.mean()
    denom = ((t - tm) ** 2).sum()
    slope = s.rolling(n, min_periods=n).apply(
        lambda w: float(((t - tm) * (w - w.mean())).sum() / denom), raw=True).to_numpy()
    r2 = s.rolling(n, min_periods=n).apply(
        lambda w: float(np.corrcoef(t, w)[0, 1] ** 2) if np.std(w) > 0 else 0.0,
        raw=True).to_numpy()
    return slope, r2


def mfi(h, l, c, v, n=14):
    tp = (np.asarray(h) + np.asarray(l) + np.asarray(c)) / 3.0
    raw = tp * np.asarray(v, float)
    d = np.diff(tp, prepend=tp[0])
    pos = pd.Series(np.where(d > 0, raw, 0.0)).rolling(n, min_periods=n).sum()
    neg = pd.Series(np.where(d < 0, raw, 0.0)).rolling(n, min_periods=n).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        return (100.0 - 100.0 / (1.0 + pos / neg)).to_numpy()


def _mod(df):
    ts = pd.to_datetime(df["ts"], utc=True)
    return (ts.dt.hour * 60 + ts.dt.minute).to_numpy()


def _atr_plan(df, le, se, stop_mult, tp_mult, trail=None, note=None):
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    have_stop = np.isfinite(a)
    le, se = le & have_stop, se & have_stop
    lx, sx = blank(n), blank(n)
    if trail == "chandelier3":
        hh22 = pd.Series(h).rolling(22, min_periods=22).max().to_numpy()
        ll22 = pd.Series(l).rolling(22, min_periods=22).min().to_numpy()
        a22 = atr(h, l, c, 22)
        lx, sx = c < hh22 - 3.0 * a22, c > ll22 + 3.0 * a22
    return Plan(le, se, lx, sx,
                stop_long=c - stop_mult * a, stop_short=c + stop_mult * a,
                tp_long=c + tp_mult * a, tp_short=c - tp_mult * a,
                note=(" ".join(x for x in (
                    "chandelier 3xATR(22) close-cross trail, one bar late" if trail else "",
                    note or "")) if (trail or note) else ""))


# ══════════════════════════════════════════ A. trend following
def p01(df):   # BTC 4H: Supertrend(10,3) flip on EMA200 side, ADX>20, 2/4 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, _ = supertrend(h, l, c, 10, 3.0)
    e200 = ema(c, 200)
    adx, _, _ = adx_di(h, l, c, 14)
    up = (st == 1) & (_roll(st) == -1) & (c > e200) & (adx > 20)
    dn = (st == -1) & (_roll(st) == 1) & (c < e200) & (adx > 20)
    up[0] = dn[0] = False
    return _atr_plan(df, up, dn, 2.0, 4.0)


def p02(df):   # ETH 1H: EMA 20/50 cross with EMA200 side, 1.5/3 ATR
    n = _n(df)
    c = df["close"].to_numpy(float)
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)
    le = (e20 > e50) & (_roll(e20) <= _roll(e50)) & (c > e200)
    se = (e20 < e50) & (_roll(e20) >= _roll(e50)) & (c < e200)
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.5, 3.0)


def p03(df):   # SOL 15m: Donchian 20 breakout, ADX>25, volume; SL Donchian-10 mid, TP 3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    hh20, ll20 = donchian(h, l, 20)
    hh10, ll10 = donchian(h, l, 10)
    adx, _, _ = adx_di(h, l, c, 14)
    ok = (adx > 25) & (v > 1.5 * sma(v, 20))
    mid10 = (hh10 + ll10) / 2.0
    a = atr(h, l, c, 14)
    le = (c > hh20) & ok
    se = (c < ll20) & ok
    return Plan(le, se, blank(n), blank(n),
                stop_long=mid10, stop_short=mid10,
                tp_long=c + 3 * a, tp_short=c - 3 * a,
                note="SL at the Donchian-10 midpoint")


def p04(df):   # HYPE 1H: MACD histogram zero-cross + EMA50 side, 1.5/3 ATR
    n = _n(df)
    c = df["close"].to_numpy(float)
    m, sg, hist = macd(c, 12, 26, 9)
    hp = _roll(hist)
    e50 = ema(c, 50)
    le = (hist > 0) & (hp <= 0) & (c > e50)
    se = (hist < 0) & (hp >= 0) & (c < e50)
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.5, 3.0)


def p05(df):   # SUI 30m: Ichimoku breakout + Tenkan/Kijun + Chikou, SL Kijun, TP 2x
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tenkan, kijun, sa, sb, _, _ = ichimoku(h, l)
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    chikou_up = c > _roll(c, 26)
    chikou_dn = c < _roll(c, 26)
    r_long = np.where(np.isnan(kijun), np.nan, np.maximum(c - kijun, 1e-9))
    r_short = np.where(np.isnan(kijun), np.nan, np.maximum(kijun - c, 1e-9))
    return Plan((c > top) & (tenkan > kijun) & chikou_up,
                (c < bot) & (tenkan < kijun) & chikou_dn,
                blank(n), blank(n),
                stop_long=kijun, stop_short=kijun,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short,
                note="Chikou read no-look-ahead: close vs the close 26 bars ago")


def p06(df):   # JUP 4H: Supertrend(10,3) trend + RSI(14) pullback through 40/60, 2/4 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, _ = supertrend(h, l, c, 10, 3.0)
    r = rsi(c, 14)
    rp = _roll(r)
    le = (st == 1) & (r > 40) & (rp <= 40) & (r < 70)
    se = (st == -1) & (r < 60) & (rp >= 60) & (r > 30)
    return _atr_plan(df, le, se, 2.0, 4.0)


def p07(df):   # BTC 1D: EMA 50/200 golden/death cross, 0.5-ATR confirm, exit on reverse
    n = _n(df)
    c = df["close"].to_numpy(float)
    e50, e200 = ema(c, 50), ema(c, 200)
    a = atr(c, c, c, 14)
    le = (e50 > e200) & (_roll(e50) <= _roll(e200)) & (c > e50 + 0.5 * a)
    se = (e50 < e200) & (_roll(e50) >= _roll(e200)) & (c < e50 - 0.5 * a)
    le[0] = se[0] = False
    return Plan(le, se, se, le, stop_long=c - 3 * a, stop_short=c + 3 * a,
                note="exit on the opposite cross; TP none, as written")


def p08(df):   # ETH 1H: Keltner(20, 2xATR10) breakout with EMA20 slope, 1.5/3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 2.0, 10)
    e20 = ema(c, 20)
    slope_up = e20 > _roll(e20)
    le = (c > ku) & slope_up
    se = (c < kl) & (~slope_up)
    return _atr_plan(df, le, se, 1.5, 3.0)


def p09(df):   # SOL 1H: LinReg(50) slope + R2 > 0.5, 1.5/3 ATR
    n = _n(df)
    c = df["close"].to_numpy(float)
    slope, r2 = linreg_slope_r2(c, 50)
    fit = pd.Series(c).rolling(50, min_periods=50).apply(
        lambda w: float(np.polyfit(np.arange(50), w, 1)[1]), raw=True).to_numpy()
    le = (slope > 0) & (c > fit) & (r2 > 0.5)
    se = (slope < 0) & (c < fit) & (r2 > 0.5)
    return _atr_plan(df, le, se, 1.5, 3.0, )


def p10(df, piv=1):  # HYPE 4H: HH/HL structure break with 3-bar fractals, SL at HL/LH, TP 3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    is_ph = (h > _roll(h)) & (h > np.roll(h, -1))
    is_pl = (l < _roll(l)) & (l < np.roll(l, -1))
    # pivot at bar i is confirmed at bar i+1 -> usable from i+1
    ph_i = np.where(is_ph[:-1], np.arange(n - 1), -1)
    pl_i = np.where(is_pl[:-1], np.arange(n - 1), -1)
    last_ph = last_pl = prev_pl = prev_ph = -1
    le = blank(n)
    se = blank(n)
    stop_long = np.full(n, np.nan)
    stop_short = np.full(n, np.nan)
    for i in range(n):
        j = i - 1                       # pivots confirmed by bar i
        if j >= 0:
            if ph_i[j] >= 0:
                prev_ph, last_ph = last_ph, ph_i[j]
            if pl_i[j] >= 0:
                prev_pl, last_pl = last_pl, pl_i[j]
        if last_ph >= 0 and last_pl >= 0 and prev_pl >= 0:
            if c[i] > h[last_ph] and l[last_pl] > l[prev_pl]:
                le[i] = True
                stop_long[i] = l[last_pl]
        if last_ph >= 0 and last_pl >= 0 and prev_ph >= 0:
            if c[i] < l[last_pl] and h[last_ph] < h[prev_ph]:
                se[i] = True
                stop_short[i] = h[last_ph]
    tp_long = np.where(le, c + 3 * a, np.nan)
    tp_short = np.where(se, c - 3 * a, np.nan)
    return Plan(le, se, blank(n), blank(n),
                stop_long=stop_long, stop_short=stop_short,
                tp_long=tp_long, tp_short=tp_short,
                note="3-bar fractal pivots, confirmed one bar after the center")


# ══════════════════════════════════════════ B. mean reversion
def p11(df):   # BTC 15m: BB bounce + RSI, ADX<30, TP mid, SL 1.5 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    r = rsi(c, 14)
    adx, _, _ = adx_di(h, l, c, 14)
    a = atr(h, l, c, 14)
    ok = adx < 30
    return Plan((c < bl) & (r < 30) & ok, (c > bu) & (r > 70) & ok,
                blank(n), blank(n), tp_long=bm, tp_short=bm,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a)


def p12(df):   # ETH 5m: RSI 30/70 cross, Asian session only, 1/2 ATR
    n = _n(df)
    c = df["close"].to_numpy(float)
    r = rsi(c, 14)
    rp = _roll(r)
    asian = _mod(df) < 8 * 60
    le = (r > 30) & (rp <= 30) & asian
    se = (r < 70) & (rp >= 70) & asian
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.0, 2.0)


def p13(df):   # SOL 1H: VWAP +2σ reversion with trend filter, TP VWAP, SL 2 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    vwap, sd = session_vwap(df, "1h")
    e20, e50 = ema(c, 20), ema(c, 50)
    a = atr(h, l, c, 14)
    flat = np.abs(e20 - e50) < 0.5 * a
    le = (c < vwap - 2 * sd) & flat
    se = (c > vwap + 2 * sd) & flat
    return Plan(le, se, blank(n), blank(n), tp_long=vwap, tp_short=vwap,
                stop_long=c - 2 * a, stop_short=c + 2 * a,
                note="session VWAP with session-to-date sigma")


def p14(df):   # SUI 15m: Keltner fade 2.5x with RSI extreme, TP EMA20, SL 1.5 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 2.5, 10)
    r = rsi(c, 14)
    a = atr(h, l, c, 14)
    return Plan((c < kl) & (r < 25), (c > ku) & (r > 75),
                blank(n), blank(n), tp_long=km, tp_short=km,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a)


def p15(df):   # JUP 5m: z-score vs SMA50, quiet-market filter, TP SMA50, SL 2 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    m50 = sma(c, 50)
    s50 = pd.Series(c).rolling(50, min_periods=50).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore"):
        z = (c - m50) / s50
    quiet = v < 1.2 * sma(v, 20)
    a = atr(h, l, c, 14)
    return Plan((z < -2) & quiet, (z > 2) & quiet,
                blank(n), blank(n), tp_long=m50, tp_short=m50,
                stop_long=c - 2 * a, stop_short=c + 2 * a)


def p16(df):   # BTC 1H: RSI(2) Connors with EMA200 filter, exit RSI2 cross 50, SL 2 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    r2 = rsi(c, 2)
    e200 = ema(c, 200)
    a = atr(h, l, c, 14)
    le = (r2 < 10) & (c > e200)
    se = (r2 > 90) & (c < e200)
    return Plan(le, se, r2 > 50, r2 < 50,
                stop_long=c - 2 * a, stop_short=c + 2 * a)


def p17(a, b):  # ETH/SOL 30m pair z-score, correlation gate
    from pack50_core import rolling_z
    ra = a["close"].to_numpy(float)
    rb = b["close"].to_numpy(float)
    n = min(len(ra), len(rb))
    ra, rb = ra[-n:], rb[-n:]
    z = rolling_z(ra / rb, 100)
    ca = pd.Series(ra).rolling(100, min_periods=100).corr(pd.Series(rb))
    corr = ca.to_numpy()
    tgt = np.zeros(n)
    ok = corr > 0.8
    tgt[(z < -2) & ok] = 1
    tgt[(z > 2) & ok] = -1
    tgt[(np.abs(z) < 0.25) | (np.abs(z) >= 3.5) | ~ok] = 0
    return tgt, "100-bar z of ETH/SOL with a >0.8 correlation gate; +1 = long ETH / short SOL"


def p18(df):   # HYPE 15m: Bollinger %B extremes, ATR filter, TP mid, SL 1.5 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    with np.errstate(invalid="ignore"):
        pb = (c - bl) / np.where(bu - bl > 0, bu - bl, np.nan)
    a = atr(h, l, c, 14)
    ok = a / c > 0.005
    return Plan((pb < 0.05) & ok, (pb > 0.95) & ok,
                blank(n), blank(n), tp_long=bm, tp_short=bm,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a)


def p19(df):   # SOL 5m: London first-15m spike fade, TP session open, SL 1.5 ATR
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    mod = _mod(df)
    day = pd.to_datetime(df["ts"], utc=True).dt.floor("1D").to_numpy()
    in_win = (mod >= 8 * 60) & (mod < 8 * 60 + 15)
    w_o = pd.Series(np.where(in_win, o, np.nan)).groupby(day).transform("first").to_numpy()
    w_c = pd.Series(np.where(in_win, c, np.nan)).groupby(day).transform("last").to_numpy()
    a = atr(h, l, c, 14)
    move = w_c - w_o
    after = mod >= 8 * 60 + 15
    se = after & (move > a) & (c < w_c)
    le = after & (move < -a) & (c > w_c)
    return Plan(le, se, blank(n), blank(n),
                tp_long=w_o, tp_short=w_o,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a,
                one_per_day=True, note="the first 15m candle is the first three 5m bars")


def p20(df):   # SUI 30m: MFI divergence within 10 bars, 1.5/3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    f = mfi(h, l, c, v, 14)
    a = atr(h, l, c, 14)
    L = pd.Series(l)
    recent_i = L.rolling(10, min_periods=10).apply(lambda w: int(np.argmin(w)), raw=True)
    prior_i = L.shift(10).rolling(10, min_periods=10).apply(lambda w: int(np.argmin(w)), raw=True)
    low_rec = L.rolling(10, min_periods=10).min().to_numpy()
    low_pri = L.shift(10).rolling(10, min_periods=10).min().to_numpy()
    idx_rec = (np.arange(n) - 10 + np.nan_to_num(recent_i)).astype(int)
    idx_pri = (np.arange(n) - 20 + np.nan_to_num(prior_i)).astype(int)
    valid = np.isfinite(recent_i) & np.isfinite(prior_i)
    idx_rec = np.clip(idx_rec, 0, n - 1)
    idx_pri = np.clip(idx_pri, 0, n - 1)
    bull = valid & (low_rec < low_pri) & (f[idx_rec] > f[idx_pri])
    H = pd.Series(h)
    rrec_i = H.rolling(10, min_periods=10).apply(lambda w: int(np.argmax(w)), raw=True)
    hpri_i = H.shift(10).rolling(10, min_periods=10).apply(lambda w: int(np.argmax(w)), raw=True)
    hi_rec = H.rolling(10, min_periods=10).max().to_numpy()
    hi_pri = H.shift(10).rolling(10, min_periods=10).max().to_numpy()
    jrec = np.clip((np.arange(n) - 10 + np.nan_to_num(rrec_i)).astype(int), 0, n - 1)
    jpri = np.clip((np.arange(n) - 20 + np.nan_to_num(hpri_i)).astype(int), 0, n - 1)
    validh = np.isfinite(rrec_i) & np.isfinite(hpri_i)
    bear = validh & (hi_rec > hi_pri) & (f[jrec] < f[jpri])
    return _atr_plan(df, bull, bear, 1.5, 3.0)


# ══════════════════════════════════════════ C. breakout / momentum
def p21(df):   # BTC 1H: Asian range breakout with width filter, TP 2x width
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    hour = ts.dt.hour.to_numpy()
    asian = hour < 8
    rh = pd.Series(np.where(asian, h, np.nan)).groupby(day).transform("max").to_numpy()
    rl = pd.Series(np.where(asian, l, np.nan)).groupby(day).transform("min").to_numpy()
    width = rh - rl
    ok = (width > 0.5 * a) & (width < 2 * a)
    after = hour >= 8
    le = after & (c > rh) & ok
    se = after & (c < rl) & ok
    return Plan(le, se, blank(n), blank(n),
                stop_long=rl, stop_short=rh,
                tp_long=c + 2 * width, tp_short=c - 2 * width, one_per_day=True)


def p22(df):   # ETH 15m: ORB first 30m after 13:30, width filter, TP 1.5x width
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    mod = _mod(df)
    day = pd.to_datetime(df["ts"], utc=True).dt.floor("1D").to_numpy()
    in_or = (mod >= 13 * 60 + 30) & (mod < 14 * 60)
    rh = pd.Series(np.where(in_or, h, np.nan)).groupby(day).transform("max").to_numpy()
    rl = pd.Series(np.where(in_or, l, np.nan)).groupby(day).transform("min").to_numpy()
    width = rh - rl
    ok = width <= 2 * a
    after = mod >= 14 * 60
    le = after & (c > rh) & ok
    se = after & (c < rl) & ok
    return Plan(le, se, blank(n), blank(n),
                stop_long=rl, stop_short=rh,
                tp_long=c + 1.5 * width, tp_short=c - 1.5 * width, one_per_day=True)


def p23(dfa, dfb):  # SOL 5m: 20-bar high + 3x volume, BTC-up-on-the-day filter
    n = _n(dfa)
    h, l, c = (dfa[x].to_numpy(float) for x in ("high", "low", "close"))
    v = dfa["volume"].to_numpy(float)
    hh20 = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy()
    ll20 = pd.Series(l).rolling(20, min_periods=20).min().shift(1).to_numpy()
    vok = v > 3.0 * sma(v, 20)
    # BTC up on the UTC day, mapped bar-by-bar from the second leg
    tb = pd.to_datetime(dfb["ts"], utc=True)
    day_b = tb.dt.floor("1D")
    ob = dfb["open"].to_numpy(float)
    cb = dfb["close"].to_numpy(float)
    day_open_b = pd.Series(np.where(tb.dt.hour == 0, ob, np.nan)).groupby(day_b).transform("first").to_numpy()
    btc_up_b = cb > day_open_b
    ts_a = dfa["open_ts"].to_numpy(np.int64)
    ts_b = dfb["open_ts"].to_numpy(np.int64)
    btc_up = btc_up_b[np.searchsorted(ts_b, ts_a)]
    btc_up = np.where(np.isnan(day_open_b[np.clip(np.searchsorted(ts_b, ts_a), 0, len(ts_b) - 1)]),
                      False, btc_up)
    a = atr(h, l, c, 14)
    return _atr_plan(dfa, (c > hh20) & vok & btc_up, (c < ll20) & vok & (~btc_up), 1.0, 2.0,
                     )


def p24(df):   # HYPE 1H: 52-bar high breakout, long-only, ATR expanding, 2/4 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh52 = pd.Series(c).rolling(52, min_periods=52).max().shift(1).to_numpy()
    a = atr(h, l, c, 14)
    expanding = a > sma(a, 20)
    return _atr_plan(df, (c > hh52) & expanding, blank(n), 2.0, 4.0)


def p25(df):   # SUI 15m: NR7 contraction + prior-bar break, 1/2.5 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    rng = h - l
    rng7 = pd.Series(rng).rolling(7, min_periods=7).mean().to_numpy()
    nr = rng == pd.Series(rng).rolling(7, min_periods=7).min().to_numpy()
    tight = _roll(rng7) < 0.8 * _roll(a)     # avg bar range of the prior 7 < 0.8x ATR
    ph, pl = _roll(h), _roll(l)
    le = _rollb(nr) & (c > ph) & tight
    se = _rollb(nr) & (c < pl) & tight
    le[:8] = se[:8] = False
    return _atr_plan(df, le, se, 1.0, 2.5,
                     note="'yesterday's high' = the prior bar's high; range filter = "
                          "mean range of the 7 bars before the NR bar < 0.8x ATR")


def p26(df):   # JUP 1H: BB-width squeeze release + volume, 1/3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    w = bu - bl
    tight = w == pd.Series(w).rolling(20, min_periods=20).min().to_numpy()
    vok = v > 1.5 * sma(v, 20)
    a = atr(h, l, c, 14)
    return _atr_plan(df, _rollb(tight) & (c > bu) & vok,
                     _rollb(tight) & (c < bl) & vok, 1.0, 3.0)


def p27(df):   # BTC 1D: 20-day high breakout, Chandelier trail ON, 3/6 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh20 = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy()
    return _atr_plan(df, c > hh20, blank(n), 3.0, 6.0, trail="chandelier3")


def p28(df):   # ETH 5m: momentum ignition, first 2h of NY, SL candle mid, TP 3x body
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy(float)
    a = atr(h, l, c, 14)
    body = np.abs(c - o)
    big = (body > 2 * a) & (v > 3.0 * sma(v, 20))
    mod = _mod(df)
    win = (mod >= 13 * 60 + 30) & (mod < 15 * 60 + 30)
    bull = c > o
    le = big & bull & win
    se = big & (~bull) & (c < o) & win
    mid = (o + c) / 2.0
    return Plan(le, se, blank(n), blank(n),
                stop_long=np.where(le, mid, np.nan), stop_short=np.where(se, mid, np.nan),
                tp_long=np.where(le, c + 3 * body, np.nan),
                tp_short=np.where(se, c - 3 * body, np.nan),
                note="SL at the signal candle midpoint, TP three candle bodies")


def p29(df):   # SOL 30m: VWAP cross with volume and slope, 1/2 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    vwap, _ = session_vwap(df, "30m")
    vslope = vwap > _roll(vwap)
    vok = v > 2.0 * sma(v, 20)
    le = (c > vwap) & (_roll(c) <= _roll(vwap)) & vok & vslope
    se = (c < vwap) & (_roll(c) >= _roll(vwap)) & vok & (~vslope)
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.0, 2.0)


def p30_no_data():
    raise RuntimeError("P30 cannot be run: no NVDA series exists on this machine")


# ══════════════════════════════════════════ D. scalping
def p31(df):   # BTC 1m: EMA 9/21 cross + VWAP side, 1/2 ATR (points reading dropped)
    n = _n(df)
    c = df["close"].to_numpy(float)
    e9, e21 = ema(c, 9), ema(c, 21)
    vwap, _ = session_vwap(df, "1m")
    v = df["volume"].to_numpy(float)
    vok = v > 2.0 * sma(v, 20)
    le = (e9 > e21) & (_roll(e9) <= _roll(e21)) & (c > vwap) & vok
    se = (e9 < e21) & (_roll(e9) >= _roll(e21)) & (c < vwap) & vok
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.0, 2.0,
                     )


def p32(df):   # ETH 1m: BB squeeze breakout, max 3 trades/hour, SL mid, TP 1 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    a = atr(h, l, c, 14)
    tight = (bu - bl) < 0.5 * a
    le = _rollb(tight) & (c > bu)
    se = _rollb(tight) & (c < bl)
    le[0] = se[0] = False
    # enforce max 3 entry candidates per rolling hour
    any_le = le | se
    cnt = pd.Series(any_le.astype(int)).rolling(60, min_periods=1).sum().to_numpy()
    over = cnt > 3
    le = le & (~over)
    se = se & (~over)
    return Plan(le, se, blank(n), blank(n),
                stop_long=bm, stop_short=bm,
                tp_long=c + a, tp_short=c - a,
                note="max three trades per rolling hour, enforced on candidates")


def p33(df):   # SOL 3m: RSI 50 cross with EMA stack and ADX>20, 0.75/1.5 ATR
    n = _n(df)
    c = df["close"].to_numpy(float)
    r = rsi(c, 14)
    rp = _roll(r)
    e20, e50 = ema(c, 20), ema(c, 50)
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    adx, _, _ = adx_di(h, l, c, 14)
    le = (r > 50) & (rp <= 50) & (e20 > e50) & (adx > 20)
    se = (r < 50) & (rp >= 50) & (e20 < e50) & (adx > 20)
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 0.75, 1.5)


def p34(df):   # HYPE 1m: micro mean reversion 2xATR beyond SMA20, TP SMA20
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    m20 = sma(c, 20)
    e50 = ema(c, 50)
    a = atr(h, l, c, 14)
    slope5 = np.abs(e50 - _roll(e50, 5))
    calm = slope5 < a
    le = (c < m20 - 2 * a) & calm
    se = (c > m20 + 2 * a) & calm
    return Plan(le, se, blank(n), blank(n), tp_long=m20, tp_short=m20,
                stop_long=c - 1.5 * a, stop_short=c + 1.5 * a,
                note="'strong trend' = |EMA50 slope over 5 bars| > 1x ATR -> skip")


def p35(df, ctx):  # SUI 5m: Supertrend(10,2) flip in the 1H EMA50 direction, 1/2 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, _ = supertrend(h, l, c, 10, 2.0)
    up_flip = (st == 1) & (_roll(st) == -1)
    dn_flip = (st == -1) & (_roll(st) == 1)
    up_flip[0] = dn_flip[0] = False
    slope_up = ctx["ema50_1h_slope"]
    return _atr_plan(df, up_flip & slope_up, dn_flip & (~slope_up), 1.0, 2.0)


def p36(df):   # JUP 1m: 10-bar micro breakout with volume, 0.5/1 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    hh10 = pd.Series(h).rolling(10, min_periods=10).max().shift(1).to_numpy()
    ll10 = pd.Series(l).rolling(10, min_periods=10).min().shift(1).to_numpy()
    vok = v > 2.0 * sma(v, 20)
    return _atr_plan(df, (c > hh10) & vok, (c < ll10) & vok, 0.5, 1.0)


def p37(df):   # BTC 3m: VWAP wick bounce, SL beyond wick, TP 1 ATR
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    vwap, _ = session_vwap(df, "3m")
    a = atr(h, l, c, 14)
    vslope = np.abs(vwap - _roll(vwap)) < 2 * a      # per-bar slope cap
    le = (l < vwap) & (c > vwap) & (c > o) & vslope
    se = (h > vwap) & (c < vwap) & (c < o) & vslope
    return Plan(le, se, blank(n), blank(n),
                stop_long=np.where(le, l - 0.5 * a, np.nan),
                stop_short=np.where(se, h + 0.5 * a, np.nan),
                tp_long=np.where(le, c + a, np.nan),
                tp_short=np.where(se, c - a, np.nan),
                note="VWAP slope filter read as < 2x ATR per bar")


def p38(df):   # ETH 5m: StochRSI 20/80 cross, first 4h of London, 1/2 ATR
    n = _n(df)
    c = df["close"].to_numpy(float)
    k, d = stoch_rsi(c, 14, 3, 3)
    kp, dp = _roll(k), _roll(d)
    mod = _mod(df)
    win = (mod >= 8 * 60) & (mod < 12 * 60)
    le = (k > d) & (kp <= dp) & (kp < 20) & win
    se = (k < d) & (kp >= dp) & (kp > 80) & win
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.0, 2.0)


def p39(df):   # SOL 1m: CVD proxy (sign(close-open)*volume, 20-bar sum) + EMA20 side
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy(float)
    cvd = pd.Series(np.sign(c - o) * v).rolling(20, min_periods=20).sum().to_numpy()
    e20 = ema(c, 20)
    a = atr(h, l, c, 14)
    vexp = v > _roll(v)
    le = (cvd > 0) & (c > e20) & vexp
    se = (cvd < 0) & (c < e20) & vexp
    return _atr_plan(df, le, se, 0.5, 1.0,
                     )


def p40(df):   # HYPE 3m: ATR envelope fade in low-vol, TP EMA20, SL 3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    e20 = ema(c, 20)
    a = atr(h, l, c, 14)
    lowvol = a / c < 0.01
    le = (c < e20 - 2 * a) & lowvol
    se = (c > e20 + 2 * a) & lowvol
    return Plan(le, se, blank(n), blank(n), tp_long=e20, tp_short=e20,
                stop_long=c - 3 * a, stop_short=c + 3 * a)


# ══════════════════════════════════════════ E. day trading / session
def p41(df):   # BTC 15m: first-candle momentum at 08:00 and 13:30, SL candle extreme, TP 2R
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    a = atr(h, l, c, 14)
    mod = _mod(df)
    is_open = (mod == 8 * 60) | (mod == 13 * 60 + 30)
    body = np.abs(c - o)
    big = body >= 0.5 * a
    bull = c > o
    le = is_open & big & bull
    se = is_open & big & (~bull)
    return Plan(le, se, blank(n), blank(n),
                stop_long=np.where(le, l, np.nan), stop_short=np.where(se, h, np.nan),
                tp_long=np.where(le, c + 2 * np.maximum(c - l, 1e-9), np.nan),
                tp_short=np.where(se, c - 2 * np.maximum(h - c, 1e-9), np.nan),
                note="signal candle = the 08:00 and 13:30 15m bars; entry fills next open")


def p42(df):   # ETH 30m: overnight range breakout at London, TP 1.5x width
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D").to_numpy()
    hour = ts.dt.hour.to_numpy()
    asian = hour < 8
    rh = pd.Series(np.where(asian, h, np.nan)).groupby(day).transform("max").to_numpy()
    rl = pd.Series(np.where(asian, l, np.nan)).groupby(day).transform("min").to_numpy()
    width = rh - rl
    ok = width < 1.5 * a
    le = (hour >= 8) & (c > rh) & ok
    se = (hour >= 8) & (c < rl) & ok
    return Plan(le, se, blank(n), blank(n),
                stop_long=rl, stop_short=rh,
                tp_long=c + 1.5 * width, tp_short=c - 1.5 * width, one_per_day=True)


def p43(df):   # SOL 15m: 14:00 UTC fade of a 2-ATR day-open extension
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    a = atr(h, l, c, 14)
    mod = _mod(df)
    day = pd.to_datetime(df["ts"], utc=True).dt.floor("1D").to_numpy()
    day_open = pd.Series(np.where(mod == 0, o, np.nan)).groupby(day).transform("first").to_numpy()
    adx, _, _ = adx_di(h, l, c, 14)
    at_time = mod == 14 * 60
    ext = c - day_open
    le = at_time & (ext < -2 * a) & (adx < 25)
    se = at_time & (ext > 2 * a) & (adx < 25)
    return Plan(le, se, blank(n), blank(n),
                tp_long=day_open, tp_short=day_open,
                stop_long=c - 2 * a, stop_short=c + 2 * a, one_per_day=True)


def p44(df):   # SUI 1H: weekend gap fade, SL 1 ATR beyond gap, TP prior close
    n = _n(df)
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    a = atr(h, l, c, 14)
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
    gap = np.where(first_of_week, o - fri, 0.0)
    ga = np.where(first_of_week, a, np.nan)
    le = first_of_week & (gap < -a)
    se = first_of_week & (gap > a)
    return Plan(le, se, blank(n), blank(n),
                tp_long=fri, tp_short=fri,
                stop_long=np.where(le, o - ga, np.nan),
                stop_short=np.where(se, o + ga, np.nan),
                note="gap = Monday first 1h open vs Friday last 1h close, in 1h ATR units")


def p45(df):   # JUP 15m: VWAP band mode switch (fade 2σ / continue 3σ)
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    vwap, sd = session_vwap(df, "15m")
    adx, _, _ = adx_di(h, l, c, 14)
    a = atr(h, l, c, 14)
    up2, dn2 = vwap + 2 * sd, vwap - 2 * sd
    up3, dn3 = vwap + 3 * sd, vwap - 3 * sd
    cross_up2 = (c > up2) & (_roll(c) <= _roll(up2))
    cross_dn2 = (c < dn2) & (_roll(c) >= _roll(dn2))
    fade_le = cross_dn2 & (adx < 25)          # fade the 2-sigma down-cross
    fade_se = cross_up2 & (adx < 25)
    cont_le = (c > up3) & (adx > 30)          # continue beyond 3 sigma
    cont_se = (c < dn3) & (adx > 30)
    le = fade_le | cont_le
    se = fade_se | cont_se
    return Plan(le, se, blank(n), blank(n),
                tp_long=vwap, tp_short=vwap,
                stop_long=c - a, stop_short=c + a,
                note="mode switch: fade 2-sigma crosses when ADX<25, continue 3-sigma breaks when ADX>30")


def p47(df):   # SPCX 15m: EMA20 pullback + bullish reversal candle, TP 2R
    n = _n(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    e20, e50 = ema(c, 20), ema(c, 50)
    a = atr(h, l, c, 14)
    bull = (c > o) & (c > _roll(c))
    bear = (c < o) & (c < _roll(c))
    expand = a > _roll(a)
    le = (e20 > e50) & (l <= e20) & (c > e20) & bull & expand
    se = (e20 < e50) & (h >= e20) & (c < e20) & bear & expand
    r_long = np.maximum(c - l, 1e-9)
    r_short = np.maximum(h - c, 1e-9)
    return Plan(le, se, blank(n), blank(n),
                stop_long=l, stop_short=h,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short,
                note="stop below the pullback low, TP twice the risk")


def p48(df):   # BTC 30m: EMA50 + OBV 20-bar high + RSI>50, volume filter, 1.5/3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    e50 = ema(c, 50)
    r = rsi(c, 14)
    ob = obv(c, v)
    ob_hi = pd.Series(ob).rolling(20, min_periods=20).max().to_numpy()
    ob_lo = pd.Series(ob).rolling(20, min_periods=20).min().to_numpy()
    vok = v > sma(v, 20)
    le = (c > e50) & (ob >= ob_hi) & (r > 50) & vok
    se = (c < e50) & (ob <= ob_lo) & (r < 50) & vok
    return _atr_plan(df, le, se, 1.5, 3.0)


def p49(df):   # ETH 1H: Ichimoku + Kumo twist + Chikou, SL Kijun, TP 2x
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tenkan, kijun, sa, sb, span_a, span_b = ichimoku(h, l)
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    chikou_up = c > _roll(c, 26)
    chikou_dn = c < _roll(c, 26)
    twist_up = (span_a > span_b) & (_roll(span_a) <= _roll(span_b))
    twist_dn = (span_a < span_b) & (_roll(span_a) >= _roll(span_b))
    r_long = np.where(np.isnan(kijun), np.nan, np.maximum(c - kijun, 1e-9))
    r_short = np.where(np.isnan(kijun), np.nan, np.maximum(kijun - c, 1e-9))
    return Plan((c > top) & twist_up & (tenkan > kijun) & chikou_up,
                (c < bot) & twist_dn & (tenkan < kijun) & chikou_dn,
                blank(n), blank(n),
                stop_long=kijun, stop_short=kijun,
                tp_long=c + 2 * r_long, tp_short=c - 2 * r_short,
                note="twist on the raw span series (computed now, cloud plots 26 bars later)")


def p50(df, ctx):  # SOL 15m: 1H Supertrend + 15m EMA/RSI confluence, 1H ADX gate
    n = _n(df)
    c = df["close"].to_numpy(float)
    e9, e21 = ema(c, 9), ema(c, 21)
    r = rsi(c, 14)
    st_dir = ctx["st_1h_dir"]
    adx1h = ctx["adx_1h"]
    le = (st_dir == 1) & (e9 > e21) & (r > 50) & (adx1h > 20)
    se = (st_dir == -1) & (e9 < e21) & (r < 50) & (adx1h > 20)
    return _atr_plan(df, le, se, 1.0, 2.0)


# ══════════════════════════════════════════ registry
def costs_for(sym: str, tf: str) -> tuple[float, float]:
    """The pack's own block, explicit: 5 bps fee, 2 bps slippage per side."""
    return 5.0, 2.0


_NO_NVDA = "no NVDA series exists on this machine"

SPECS = {
    1: dict(sym="BTCUSDT", tf="4h", build=p01, name="Supertrend + EMA200"),
    2: dict(sym="ETHUSDT", tf="1h", build=p02, name="EMA 20/50 cross"),
    3: dict(sym="SOLUSDT", tf="15m", build=p03, name="Donchian 20 breakout"),
    4: dict(sym="HYPEUSDT", tf="1h", build=p04, name="MACD histogram + EMA50"),
    5: dict(sym="SUIUSDT", tf="30m", build=p05, name="Ichimoku Kumo breakout"),
    6: dict(sym="JUPUSDT", tf="4h", build=p06, name="Supertrend + RSI pullback"),
    7: dict(sym="BTCUSDT", tf="1d", build=p07, name="EMA 50/200 cross"),
    8: dict(sym="ETHUSDT", tf="1h", build=p08, name="Keltner breakout"),
    9: dict(sym="SOLUSDT", tf="1h", build=p09, name="LinReg slope + R2"),
    10: dict(sym="HYPEUSDT", tf="4h", build=p10, name="HH/HL structure break"),
    11: dict(sym="BTCUSDT", tf="15m", build=p11, name="BB bounce + RSI"),
    12: dict(sym="ETHUSDT", tf="5m", build=p12, name="RSI 30/70, Asian only"),
    13: dict(sym="SOLUSDT", tf="1h", build=p13, name="VWAP reversion"),
    14: dict(sym="SUIUSDT", tf="15m", build=p14, name="Keltner fade"),
    15: dict(sym="JUPUSDT", tf="5m", build=p15, name="z-score reversion"),
    16: dict(sym="BTCUSDT", tf="1h", build=p16, name="RSI(2) Connors"),
    17: dict(sym="ETHUSDT+SOLUSDT", tf="30m", pair=p17, name="ETH/SOL z-score pair"),
    18: dict(sym="HYPEUSDT", tf="15m", build=p18, name="Bollinger %B"),
    19: dict(sym="SOLUSDT", tf="5m", build=p19, name="London open fade"),
    20: dict(sym="SUIUSDT", tf="30m", build=p20, name="MFI divergence"),
    21: dict(sym="BTCUSDT", tf="1h", build=p21, name="Asian range breakout"),
    22: dict(sym="ETHUSDT", tf="15m", build=p22, name="ORB 13:30"),
    23: dict(sym="SOLUSDT+BTCUSDT", tf="5m", build2=p23, name="volume breakout + BTC filter"),
    24: dict(sym="HYPEUSDT", tf="1h", build=p24, name="52-bar high, long-only"),
    25: dict(sym="SUIUSDT", tf="15m", build=p25, name="NR7 contraction"),
    26: dict(sym="JUPUSDT", tf="1h", build=p26, name="squeeze release"),
    27: dict(sym="BTCUSDT", tf="1d", build=p27, name="20-day high, Chandelier"),
    28: dict(sym="ETHUSDT", tf="5m", build=p28, name="momentum ignition"),
    29: dict(sym="SOLUSDT", tf="30m", build=p29, name="VWAP breakout"),
    30: dict(sym="NVDA", tf="15m", build=None, name="gap and go", no_data=_NO_NVDA),
    31: dict(sym="BTCUSDT", tf="1m", build=p31, name="EMA 9/21 + VWAP"),
    32: dict(sym="ETHUSDT", tf="1m", build=p32, name="BB squeeze scalper"),
    33: dict(sym="SOLUSDT", tf="3m", build=p33, name="RSI 50 cross"),
    34: dict(sym="HYPEUSDT", tf="1m", build=p34, name="micro mean reversion"),
    35: dict(sym="SUIUSDT", tf="5m", build=p35, name="Supertrend 10/2 + 1H filter"),
    36: dict(sym="JUPUSDT", tf="1m", build=p36, name="micro breakout"),
    37: dict(sym="BTCUSDT", tf="3m", build=p37, name="VWAP wick bounce"),
    38: dict(sym="ETHUSDT", tf="5m", build=p38, name="StochRSI cross"),
    39: dict(sym="SOLUSDT", tf="1m", build=p39, name="CVD proxy"),
    40: dict(sym="HYPEUSDT", tf="3m", build=p40, name="ATR envelope fade"),
    41: dict(sym="BTCUSDT", tf="15m", build=p41, name="session open momentum"),
    42: dict(sym="ETHUSDT", tf="30m", build=p42, name="overnight range breakout"),
    43: dict(sym="SOLUSDT", tf="15m", build=p43, name="session extreme fade"),
    44: dict(sym="SUIUSDT", tf="1h", build=p44, name="weekend gap fade"),
    45: dict(sym="JUPUSDT", tf="15m", build=p45, name="VWAP band mode switch"),
    46: dict(sym="NVDA", tf="5m", build=None, name="NVDA ORB", no_data=_NO_NVDA),
    47: dict(sym="SPCX", tf="15m", build=p47, name="trend pullback"),
    48: dict(sym="BTCUSDT", tf="30m", build=p48, name="momentum + OBV"),
    49: dict(sym="ETHUSDT", tf="1h", build=p49, name="Ichimoku + Kumo twist"),
    50: dict(sym="SOLUSDT", tf="15m", build=p50, name="MTF confluence"),
}

CODE = {i: f"P{i:02d}" for i in SPECS}
CTX_STRATS = {35, 50}
