#!/usr/bin/env python
"""pack50c_strats.py -- the fifty prompts of `Downloads/Qwen_50 strategies.txt`
turned into explicit rules.

READ THIS BEFORE TRUSTING A NUMBER
    Several prompts are not executable as written. Each of those carries a
    `note=` that states the reading chosen here, so the artifact and the report
    can be challenged on the reading rather than on the arithmetic. The list:

    * Data. Q02, Q11, Q23, Q27, Q35, Q36, Q42 and Q47 need NVDA equity data,
      which does not exist on this machine: they are NOT in this file and are
      reported NO DATA, never estimated. "SPCX" is read as the SPXUSDT series
      on disk (plain 1m/1h klines; 5m/15m/30m resampled from the 1m file,
      roughly three months of history). Timeframes map as in the pack50b
      campaign: 3m resampled from the 1m taker files, 30m from the 15m files.
    * Costs. The pack declares "fees 0.05% and slippage 2 ticks": fee 5.0 bps
      per side, and "2 ticks" read as 2.0 bps slippage per side (uniform; a
      literal tick is symbol-specific and would be near-zero on BTC). The repo
      gate cost (5.0 + 0.5 bps) and a zero-cost control are measured inside
      every artifact, plus twice the gate cost and the breakeven.
    * Labels vs mechanisms. Q01, Q05 and Q25 are labelled "breakout" but the
      mechanism named is a VWAP/POC BOUNCE; the mechanism governs. Q12 is
      labelled "mean reversion" but the mechanism is an EMA 9/21 trend cross.
    * "Support and resistance levels for stop loss and take profit" is read as
      the prior 20-bar range: a long stops at the 20-bar low and targets the
      20-bar high; a short mirrors. (Q04, Q19, Q22, Q26, Q31, Q33, Q35, Q50)
    * Trailing stops. The execution core's stop is set at entry, so a trailing
      stop is emulated as a close-cross exit, filling one bar late:
        - "ATR trailing stop": the initial stop works intrabar, and the exit
          fires when close crosses the Chandelier-style line
          (22-bar extreme -/+ the prompt's own stop multiple x ATR(14)).
        - "EMA 50 trailing stop": the initial stop works intrabar, and the
          exit fires when close crosses EMA 50 against the position.
    * "ADX > 25 for trend strength" as the only entry condition is read as a
      DI cross gated by ADX: long when +DI crosses above -DI with ADX > 25,
      short on the reverse cross; the position exits on the opposite cross.
    * "Stochastic Oscillator crossover" is a plain %K/%D cross; the prompts
      labelled mean reversion (Q03) additionally require the cross to start
      from the extremes (below 20 / above 80).
    * Volume Profile POC: the Point of Control is the centre of the
      highest-volume price bin of the PRIOR 100 bars (20 bins, no look-ahead).
      A bounce is a touch of the POC and a close back on the trade side.
    * Q06's entry is RSI(14) < 30 (long) / > 70 (short) with fixed ATR stop
      and a 2x-ATR target; exits are the stop and target only, as written.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pack50_core import (Plan, adx_di, atr, bollinger, donchian, ema, keltner,
                         macd, psar, rsi, session_vwap, supertrend)


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


# ══════════════════════════════════════════════════ primitives (pinned by
# parity tests in _pack50c_audit.py against the pack50b versions)
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


def stoch(h, l, c, n=14, k=3, d=3):
    hh = pd.Series(h).rolling(n, min_periods=n).max()
    ll = pd.Series(l).rolling(n, min_periods=n).min()
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = 100.0 * (pd.Series(c) - ll) / (hh - ll)
    kk = raw.rolling(k, min_periods=k).mean()
    dd = kk.rolling(d, min_periods=d).mean()
    return kk.to_numpy(), dd.to_numpy()


def rolling_poc(h, l, c, v, lookback=100, bins=20):
    """Per-bar Point of Control of the PRIOR `lookback` bars: the centre of the
    highest-volume price bin. No look-ahead: bar i uses bars [i-lookback, i)."""
    n = len(c)
    poc = np.full(n, np.nan)
    for i in range(lookback, n):
        w = slice(i - lookback, i)
        lo, hi = l[w].min(), h[w].max()
        if not np.isfinite(hi - lo) or hi <= lo:
            continue
        edges = np.linspace(lo, hi, bins + 1)
        idx = np.clip(np.digitize(c[w], edges) - 1, 0, bins - 1)
        vol = np.bincount(idx, weights=v[w], minlength=bins)
        b = int(vol.argmax())
        poc[i] = (edges[b] + edges[b + 1]) / 2.0
    return poc


def _atr_trail(df, mult):
    """Chandelier-style ATR trailing line using the prompt's own stop multiple."""
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    hh22 = pd.Series(h).rolling(22, min_periods=22).max().to_numpy()
    ll22 = pd.Series(l).rolling(22, min_periods=22).min().to_numpy()
    return hh22 - mult * a, ll22 + mult * a


def _atr_plan(df, le, se, stop_mult, tp_mult, trail="atr"):
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    have_stop = np.isfinite(a)      # no entry before the ATR stop exists
    le = le & have_stop
    se = se & have_stop
    lx, sx = blank(n), blank(n)
    if trail == "atr":
        tl, ts = _atr_trail(df, stop_mult)
        lx = c < tl
        sx = c > ts
    elif trail == "ema50":
        e50 = ema(c, 50)
        lx = c < e50
        sx = c > e50
    return Plan(le, se, lx, sx,
                stop_long=c - stop_mult * a, stop_short=c + stop_mult * a,
                tp_long=c + tp_mult * a, tp_short=c - tp_mult * a,
                note=f"trailing emulated as a close-cross exit, one bar late ({trail})")


def _pct_plan(df, le, se, stop_pct, tp_pct, trail="none"):
    n = _n(df)
    c = df["close"].to_numpy(float)
    lx, sx = blank(n), blank(n)
    if trail == "ema50":
        e50 = ema(c, 50)
        lx = c < e50
        sx = c > e50
    elif trail == "atr":
        tl, ts = _atr_trail(df, 1.5)
        lx = c < tl
        sx = c > ts
    return Plan(le, se, lx, sx,
                stop_long=c * (1 - stop_pct), stop_short=c * (1 + stop_pct),
                tp_long=c * (1 + tp_pct), tp_short=c * (1 - tp_pct),
                note=f"fixed {stop_pct * 100:.1f}% stop / {tp_pct * 100:.1f}% target"
                     + (f"; {trail} trail close-cross" if trail != "none" else ""))


def _sr_plan(df, le, se, trail="ema50"):
    """S/R stops and targets from the prior 20-bar range."""
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    hh20, ll20 = donchian(h, l, 20)
    lx, sx = blank(n), blank(n)
    if trail == "ema50":
        e50 = ema(c, 50)
        lx = c < e50
        sx = c > e50
    elif trail == "atr":
        tl, ts = _atr_trail(df, 1.5)
        lx = c < tl
        sx = c > ts
    return Plan(le, se, lx, sx,
                stop_long=ll20, stop_short=hh20,
                tp_long=hh20, tp_short=ll20,
                note="stop at the 20-bar support/resistance, target the opposite "
                     "extreme" + (f"; {trail} trail close-cross" if trail != "none" else ""))


def _di_cross_plan(df, stop_mult, tp_mult, trail="none", adx_min=25.0):
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    adx, pdi, mdi = adx_di(h, l, c, 14)
    up = (pdi > mdi) & (_roll(pdi) <= _roll(mdi)) & (adx > adx_min)
    dn = (pdi < mdi) & (_roll(pdi) >= _roll(mdi)) & (adx > adx_min)
    up[0] = dn[0] = False
    if trail == "ema50":
        return _sr_plan(df, up, dn, trail="ema50")
    return _atr_plan(df, up, dn, stop_mult, tp_mult, trail=trail)


def _vwap_bounce(df, stop_mult=None, stop_pct=None, tp_mult=None, tp_pct=None, trail="none"):
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    vwap, _ = session_vwap(df, "1m")
    le = (l <= vwap) & (c > vwap)
    se = (h >= vwap) & (c < vwap)
    if stop_pct is not None:
        return _pct_plan(df, le, se, stop_pct, tp_pct, trail=trail)
    return _atr_plan(df, le, se, stop_mult, tp_mult, trail=trail)


# ══════════════════════════════════════════════════ the prompts
def q01(df):   # SPCX 5m: VWAP bounce (labelled breakout), 1.5/1.5 ATR
    return _vwap_bounce(df, stop_mult=1.5, tp_mult=1.5)


def q03(df):   # SPCX 1m: stochastic cross from the extremes, 1%/2% fixed
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    k, d = stoch(h, l, c, 14, 3, 3)
    kp, dp = _roll(k), _roll(d)
    le = (k > d) & (kp <= dp) & (kp < 20)
    se = (k < d) & (kp >= dp) & (kp > 80)
    le[0] = se[0] = False
    return _pct_plan(df, le, se, 0.01, 0.02)


def q04(df):   # HYPE 1m: Keltner breakout, S/R stops, ATR trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    return _sr_plan(df, c > ku, c < kl, trail="atr")


def q05(df):   # BTC 15m: VWAP bounce, 2/3 ATR, ATR trail
    return _vwap_bounce(df, stop_mult=2.0, tp_mult=3.0, trail="atr")


def q06(df):   # ETH 1m: RSI(14) < 30 / > 70, 1 ATR stop, 2 ATR target
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    r = rsi(c, 14)
    le = r < 30
    se = r > 70
    return _atr_plan(df, le, se, 1.0, 2.0, trail="none")


def q07(df):   # SOL 1m: DI cross with ADX > 25, 2/3 ATR
    return _di_cross_plan(df, 2.0, 3.0)


def q08(df):   # SUI 1m: PSAR reversal, 1.5/1.5 ATR, EMA50 trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    sar = psar(h, l)
    flip_up = (sar < c) & (_roll(sar) > _roll(c))
    flip_dn = (sar > c) & (_roll(sar) < _roll(c))
    flip_up[0] = flip_dn[0] = False
    return _atr_plan(df, flip_up, flip_dn, 1.5, 1.5, trail="ema50")


def q09(df):   # HYPE 1m: Bollinger breakout, 0.5%/1% fixed
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    return _pct_plan(df, c > bu, c < bl, 0.005, 0.01)


def q10(df):   # SOL 3m: Bollinger breakout, 1%/2% fixed, ATR trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    return _pct_plan(df, c > bu, c < bl, 0.01, 0.02, trail="atr")


def q12(df):   # SPCX 15m: EMA 9/21 cross (labelled mean reversion), 1.5/1.5 ATR, EMA50 trail
    n = _n(df)
    c = df["close"].to_numpy(float)
    e9, e21 = ema(c, 9), ema(c, 21)
    le = (e9 > e21) & (_roll(e9) <= _roll(e21))
    se = (e9 < e21) & (_roll(e9) >= _roll(e21))
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.5, 1.5, trail="ema50")


def q13(df):   # ETH 30m: POC bounce, 1%/2% fixed
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    poc = rolling_poc(h, l, c, v)
    le = (l <= poc) & (c > poc)
    se = (h >= poc) & (c < poc)
    return _pct_plan(df, le, se, 0.01, 0.02)


def q14(df):   # BTC 3m: Bollinger breakout, 2/3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    return _atr_plan(df, c > bu, c < bl, 2.0, 3.0)


def q15(df):   # JUP 15m: stochastic cross, 2/3 ATR
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    k, d = stoch(h, l, c, 14, 3, 3)
    kp, dp = _roll(k), _roll(d)
    le = (k > d) & (kp <= dp)
    se = (k < d) & (kp >= dp)
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 2.0, 3.0)


def q16(df):   # SOL 1m: DI cross with ADX > 25 (labelled breakout), 1.5/1.5 ATR, EMA50 trail
    return _di_cross_plan(df, 1.5, 1.5, trail="ema50")


def q17(df):   # ETH 30m: Supertrend direction, 1 ATR stop, 2 ATR target
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, _ = supertrend(h, l, c, 10, 2.0)
    up = (st == 1) & (_roll(st) == -1)
    dn = (st == -1) & (_roll(st) == 1)
    up[0] = dn[0] = False
    return _atr_plan(df, up, dn, 1.0, 2.0)


def q18(df):   # SOL 1m: Ichimoku cloud breakout, 0.5%/1% fixed, EMA50 trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tenkan, kijun, sa, sb = ichimoku(h, l)
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    le = c > top
    se = c < bot
    return _pct_plan(df, le, se, 0.005, 0.01, trail="ema50")


def q19(df):   # HYPE 30m: Keltner breakout, S/R stops, EMA50 trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    return _sr_plan(df, c > ku, c < kl, trail="ema50")


def q20(df):   # JUP 3m: POC bounce, 1%/2% fixed, EMA50 trail
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    poc = rolling_poc(h, l, c, v)
    le = (l <= poc) & (c > poc)
    se = (h >= poc) & (c < poc)
    return _pct_plan(df, le, se, 0.01, 0.02, trail="ema50")


def q21(df):   # ETH 5m: stochastic cross, 2/3 ATR
    return q15(df)


def q22(df):   # BTC 3m: Bollinger breakout, S/R stops, ATR trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    return _sr_plan(df, c > bu, c < bl, trail="atr")


def q24(df):   # SPX 30m: POC bounce, 2/3 ATR
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    poc = rolling_poc(h, l, c, v)
    le = (l <= poc) & (c > poc)
    se = (h >= poc) & (c < poc)
    return _atr_plan(df, le, se, 2.0, 3.0)


def q25(df):   # ETH 3m: POC bounce (labelled breakout), 0.5%/1% fixed
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    poc = rolling_poc(h, l, c, v)
    le = (l <= poc) & (c > poc)
    se = (h >= poc) & (c < poc)
    return _pct_plan(df, le, se, 0.005, 0.01)


def q26(df):   # JUP 15m: Ichimoku, S/R stops, EMA50 trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tenkan, kijun, sa, sb = ichimoku(h, l)
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    return _sr_plan(df, c > top, c < bot, trail="ema50")


def q28(df):   # HYPE 15m: Ichimoku, 2/3 ATR, ATR trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tenkan, kijun, sa, sb = ichimoku(h, l)
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    return _atr_plan(df, c > top, c < bot, 2.0, 3.0, trail="atr")


def q29(df):   # JUP 30m: DI cross with ADX > 25, 2/3 ATR
    return _di_cross_plan(df, 2.0, 3.0)


def q30(df):   # BTC 1m: Ichimoku, 1.5/1.5 ATR, ATR trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tenkan, kijun, sa, sb = ichimoku(h, l)
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    return _atr_plan(df, c > top, c < bot, 1.5, 1.5, trail="atr")


def q31(df):   # SOL 15m: MACD histogram zero-cross, S/R stops, EMA50 trail
    n = _n(df)
    c = df["close"].to_numpy(float)
    m, sg, hist = macd(c, 12, 26, 9)
    hp = _roll(hist)
    le = (hist > 0) & (hp <= 0)
    se = (hist < 0) & (hp >= 0)
    le[0] = se[0] = False
    return _sr_plan(df, le, se, trail="ema50")


def q32(df):   # ETH 1m: VWAP bounce, 0.5%/1% fixed, ATR trail
    return _vwap_bounce(df, stop_pct=0.005, tp_pct=0.01, trail="atr")


def q33(df):   # SUI 1m: Bollinger breakout, S/R stops, ATR trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    return _sr_plan(df, c > bu, c < bl, trail="atr")


def q34(df):   # JUP 30m: VWAP bounce, 0.5%/1% fixed
    return _vwap_bounce(df, stop_pct=0.005, tp_pct=0.01)


def q37(df):   # SOL 30m: Keltner breakout, 0.5%/1% fixed
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    kl, km, ku = keltner(h, l, c, 20, 1.5, 10)
    return _pct_plan(df, c > ku, c < kl, 0.005, 0.01)


def q38(df):   # HYPE 5m: POC bounce, 1.5/1.5 ATR
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    poc = rolling_poc(h, l, c, v)
    le = (l <= poc) & (c > poc)
    se = (h >= poc) & (c < poc)
    return _atr_plan(df, le, se, 1.5, 1.5)


def q39(df):   # JUP 1m: EMA 9/21 cross, 1 ATR stop, 2 ATR target, ATR trail
    n = _n(df)
    c = df["close"].to_numpy(float)
    e9, e21 = ema(c, 9), ema(c, 21)
    le = (e9 > e21) & (_roll(e9) <= _roll(e21))
    se = (e9 < e21) & (_roll(e9) >= _roll(e21))
    le[0] = se[0] = False
    return _atr_plan(df, le, se, 1.0, 2.0, trail="atr")


def q40(df):   # SUI 30m: DI cross with ADX > 25, 0.5%/1% fixed
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    adx, pdi, mdi = adx_di(h, l, c, 14)
    up = (pdi > mdi) & (_roll(pdi) <= _roll(mdi)) & (adx > 25)
    dn = (pdi < mdi) & (_roll(pdi) >= _roll(mdi)) & (adx > 25)
    up[0] = dn[0] = False
    return _pct_plan(df, up, dn, 0.005, 0.01)


def q41(df):   # ETH 3m: PSAR reversal, 2/3 ATR, EMA50 trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    sar = psar(h, l)
    flip_up = (sar < c) & (_roll(sar) > _roll(c))
    flip_dn = (sar > c) & (_roll(sar) < _roll(c))
    flip_up[0] = flip_dn[0] = False
    return _atr_plan(df, flip_up, flip_dn, 2.0, 3.0, trail="ema50")


def q43(df):   # SOL 15m: PSAR reversal, 1.5/1.5 ATR, ATR trail
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    sar = psar(h, l)
    flip_up = (sar < c) & (_roll(sar) > _roll(c))
    flip_dn = (sar > c) & (_roll(sar) < _roll(c))
    flip_up[0] = flip_dn[0] = False
    return _atr_plan(df, flip_up, flip_dn, 1.5, 1.5, trail="atr")


def q44(df):   # JUP 1m: VWAP bounce, 2/3 ATR, ATR trail
    return _vwap_bounce(df, stop_mult=2.0, tp_mult=3.0, trail="atr")


def q45(df):   # SOL 3m: Supertrend direction, 2/3 ATR
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    st, _ = supertrend(h, l, c, 10, 2.0)
    up = (st == 1) & (_roll(st) == -1)
    dn = (st == -1) & (_roll(st) == 1)
    up[0] = dn[0] = False
    return _atr_plan(df, up, dn, 2.0, 3.0)


def q46(df):   # BTC 5m: DI cross with ADX > 25, 2/3 ATR
    return _di_cross_plan(df, 2.0, 3.0)


def q48(df):   # ETH 15m: POC bounce, 1%/2% fixed, ATR trail
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    poc = rolling_poc(h, l, c, v)
    le = (l <= poc) & (c > poc)
    se = (h >= poc) & (c < poc)
    return _pct_plan(df, le, se, 0.01, 0.02, trail="atr")


def q49(df):   # SUI 3m: Bollinger breakout, 1 ATR stop, 2 ATR target
    n = _n(df)
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    bl, bm, bu = bollinger(c, 20, 2.0)
    return _atr_plan(df, c > bu, c < bl, 1.0, 2.0)


def q50(df):   # SOL 15m: stochastic cross, S/R stops, EMA50 trail
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    k, d = stoch(h, l, c, 14, 3, 3)
    kp, dp = _roll(k), _roll(d)
    le = (k > d) & (kp <= dp)
    se = (k < d) & (kp >= dp)
    le[0] = se[0] = False
    return _sr_plan(df, le, se, trail="ema50")


# ══════════════════════════════════════════════════ registry
def costs_for(sym: str, tf: str) -> tuple[float, float]:
    """The pack's own block: 0.05% fee and '2 ticks' read as 2.0 bps slippage
    per side, uniform. The repo gate cost is measured separately."""
    return 5.0, 2.0


_NO_NVDA = "no NVDA series exists on this machine"

SPECS = {
    1: dict(sym="SPCX", tf="5m", build=q01, name="VWAP bounce"),
    2: dict(sym="NVDA", tf="30m", build=None, name="Ichimoku breakout", no_data=_NO_NVDA),
    3: dict(sym="SPCX", tf="1m", build=q03, name="stochastic reversion"),
    4: dict(sym="HYPEUSDT", tf="1m", build=q04, name="Keltner breakout, S/R"),
    5: dict(sym="BTCUSDT", tf="15m", build=q05, name="VWAP bounce"),
    6: dict(sym="ETHUSDT", tf="1m", build=q06, name="RSI extremes"),
    7: dict(sym="SOLUSDT", tf="1m", build=q07, name="DI cross, ADX>25"),
    8: dict(sym="SUIUSDT", tf="1m", build=q08, name="PSAR reversal"),
    9: dict(sym="HYPEUSDT", tf="1m", build=q09, name="Bollinger breakout"),
    10: dict(sym="SOLUSDT", tf="3m", build=q10, name="Bollinger breakout"),
    11: dict(sym="NVDA", tf="15m", build=None, name="Keltner breakout", no_data=_NO_NVDA),
    12: dict(sym="SPCX", tf="15m", build=q12, name="EMA 9/21 cross"),
    13: dict(sym="ETHUSDT", tf="30m", build=q13, name="POC bounce"),
    14: dict(sym="BTCUSDT", tf="3m", build=q14, name="Bollinger breakout"),
    15: dict(sym="JUPUSDT", tf="15m", build=q15, name="stochastic cross"),
    16: dict(sym="SOLUSDT", tf="1m", build=q16, name="DI cross, ADX>25"),
    17: dict(sym="ETHUSDT", tf="30m", build=q17, name="Supertrend"),
    18: dict(sym="SOLUSDT", tf="1m", build=q18, name="Ichimoku breakout"),
    19: dict(sym="HYPEUSDT", tf="30m", build=q19, name="Keltner breakout, S/R"),
    20: dict(sym="JUPUSDT", tf="3m", build=q20, name="POC bounce"),
    21: dict(sym="ETHUSDT", tf="5m", build=q21, name="stochastic cross"),
    22: dict(sym="BTCUSDT", tf="3m", build=q22, name="Bollinger breakout, S/R"),
    23: dict(sym="NVDA", tf="15m", build=None, name="Bollinger breakout", no_data=_NO_NVDA),
    24: dict(sym="SPCX", tf="30m", build=q24, name="POC bounce"),
    25: dict(sym="ETHUSDT", tf="3m", build=q25, name="POC bounce"),
    26: dict(sym="JUPUSDT", tf="15m", build=q26, name="Ichimoku, S/R"),
    27: dict(sym="NVDA", tf="3m", build=None, name="POC bounce", no_data=_NO_NVDA),
    28: dict(sym="HYPEUSDT", tf="15m", build=q28, name="Ichimoku breakout"),
    29: dict(sym="JUPUSDT", tf="30m", build=q29, name="DI cross, ADX>25"),
    30: dict(sym="BTCUSDT", tf="1m", build=q30, name="Ichimoku breakout"),
    31: dict(sym="SOLUSDT", tf="15m", build=q31, name="MACD histogram, S/R"),
    32: dict(sym="ETHUSDT", tf="1m", build=q32, name="VWAP bounce"),
    33: dict(sym="SUIUSDT", tf="1m", build=q33, name="Bollinger breakout, S/R"),
    34: dict(sym="JUPUSDT", tf="30m", build=q34, name="VWAP bounce"),
    35: dict(sym="NVDA", tf="15m", build=None, name="stochastic, S/R", no_data=_NO_NVDA),
    36: dict(sym="NVDA", tf="3m", build=None, name="POC bounce", no_data=_NO_NVDA),
    37: dict(sym="SOLUSDT", tf="30m", build=q37, name="Keltner breakout"),
    38: dict(sym="HYPEUSDT", tf="5m", build=q38, name="POC bounce"),
    39: dict(sym="JUPUSDT", tf="1m", build=q39, name="EMA 9/21 cross"),
    40: dict(sym="SUIUSDT", tf="30m", build=q40, name="DI cross, ADX>25"),
    41: dict(sym="ETHUSDT", tf="3m", build=q41, name="PSAR reversal"),
    42: dict(sym="NVDA", tf="30m", build=None, name="POC bounce", no_data=_NO_NVDA),
    43: dict(sym="SOLUSDT", tf="15m", build=q43, name="PSAR reversal"),
    44: dict(sym="JUPUSDT", tf="1m", build=q44, name="VWAP bounce"),
    45: dict(sym="SOLUSDT", tf="3m", build=q45, name="Supertrend"),
    46: dict(sym="BTCUSDT", tf="5m", build=q46, name="DI cross, ADX>25"),
    47: dict(sym="NVDA", tf="30m", build=None, name="stochastic cross", no_data=_NO_NVDA),
    48: dict(sym="ETHUSDT", tf="15m", build=q48, name="POC bounce"),
    49: dict(sym="SUIUSDT", tf="3m", build=q49, name="Bollinger breakout"),
    50: dict(sym="SOLUSDT", tf="15m", build=q50, name="stochastic cross, S/R"),
}

CODE = {i: f"Q{i:02d}" for i in SPECS}
