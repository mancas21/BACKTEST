#!/usr/bin/env python3
"""
scalp_ma_suite.py - 20 MA-family scalping strategies (1m-5m) on one shared backtest engine.

Families: EMA / TEMA / DEMA / HMA / ZLEMA / KAMA crosses, ribbons, pullbacks, VWAP,
Supertrend, MACD, Bollinger squeeze, Keltner, Donchian, RSI / StochRSI, volume-confirmed momentum.

Engine (same conventions as ema_9_21_backtest.py, no lookahead)
  - Signals computed on bar close, filled at NEXT bar open (+slippage).
  - SL / TP in ATR multiples taken at the signal bar. SL checked intrabar, SL wins if both hit.
    Gap through level -> fill at open. TP fills as limit (no slippage).
  - Time stop (max_bars), optional per-strategy signal exits, optional flip on opposite signal.
  - Fee per side on notional, risk-based sizing capped by max_leverage, compounding.
  - Each strategy is run on an in-sample and an out-of-sample segment (signals computed on
    the full series, engine restarted at the split) so decay is visible side by side.

Usage
  python scalp_ma_suite.py --synthetic --selftest
  python scalp_ma_suite.py --csv data/SUIUSDT_1m.csv --tf 5m
  python scalp_ma_suite.py --symbol SUI/USDT:USDT --tf 1m --days 60          (needs ccxt)
  python scalp_ma_suite.py --csv x.csv --tf 1m --fee_bps 2 --sl_atr 1.5 --tp_atr 2.0 --only 03,07,13

CSV columns: timestamp|time|open_time|datetime|date, open, high, low, close, [volume].
Strategies needing volume (VWAP, volume momentum) are skipped when volume is absent.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, asdict
from typing import Callable, Optional

import numpy as np
import pandas as pd

# =============================================================================
# Indicators
# =============================================================================


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def dema(x, n):
    e1 = ema(x, n)
    return 2 * e1 - ema(e1, n)


def tema(x, n):
    e1 = ema(x, n)
    e2 = ema(e1, n)
    e3 = ema(e2, n)
    return 3 * e1 - 3 * e2 + e3


def wma(x, n):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    valid = np.where(~np.isnan(x))[0]
    if len(valid) == 0:
        return out
    k = valid[0]
    y = x[k:]
    if len(y) < n:
        return out
    w = np.arange(1, n + 1, dtype=float)
    out[k + n - 1:] = np.convolve(y, w[::-1], mode="valid") / w.sum()
    return out


def hma(x, n):
    half = max(n // 2, 1)
    sq = max(int(round(np.sqrt(n))), 1)
    return wma(2 * wma(x, half) - wma(x, n), sq)


def zlema(x, n):
    lag = (n - 1) // 2
    s = pd.Series(x)
    return (2 * s - s.shift(lag)).ewm(span=n, adjust=False).mean().to_numpy()


def kama(x, n=10, fast=2, slow=30):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    fa, sa = 2 / (fast + 1), 2 / (slow + 1)
    d = np.abs(np.diff(x, prepend=x[0]))
    vol = pd.Series(d).rolling(n).sum().to_numpy()
    chg = np.abs(x - np.r_[np.full(n, np.nan), x[:-n]])
    er = chg / np.where(vol == 0, np.nan, vol)
    out[n] = x[n]
    for i in range(n + 1, len(x)):
        e = er[i]
        if e != e:
            out[i] = out[i - 1]
            continue
        sc = (e * (fa - sa) + sa) ** 2
        out[i] = out[i - 1] + sc * (x[i] - out[i - 1])
    return out


def efficiency_ratio(x, n=10):
    x = np.asarray(x, float)
    d = pd.Series(np.abs(np.diff(x, prepend=x[0]))).rolling(n).sum().to_numpy()
    chg = np.abs(x - np.r_[np.full(n, np.nan), x[:-n]])
    return chg / np.where(d == 0, np.nan, d)


def rsi(x, n=14):
    s = pd.Series(x)
    dlt = s.diff()
    up = dlt.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dlt.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out[(dn == 0) & (up > 0)] = 100.0
    return out.to_numpy()


def true_range(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    return np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])


def atr(h, l, c, n=14):
    return pd.Series(true_range(h, l, c)).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def adx(h, l, c, n=14):
    up = np.r_[0, h[1:] - h[:-1]]
    dn = np.r_[0, l[:-1] - l[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr_s = pd.Series(true_range(h, l, c)).ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1 / n, adjust=False).mean() / tr_s
    mdi = 100 * pd.Series(mdm).ewm(alpha=1 / n, adjust=False).mean() / tr_s
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def supertrend_dir(h, l, c, n=10, mult=2.0):
    a = atr(h, l, c, n)
    hl2 = (h + l) / 2
    ub, lb = hl2 + mult * a, hl2 - mult * a
    N = len(c)
    fu = np.full(N, np.nan)
    fl = np.full(N, np.nan)
    d = np.zeros(N, int)
    fu[0], fl[0], d[0] = ub[0], lb[0], 1
    for i in range(1, N):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if d[i - 1] == -1 and c[i] > fu[i]:
            d[i] = 1
        elif d[i - 1] == 1 and c[i] < fl[i]:
            d[i] = -1
        else:
            d[i] = d[i - 1]
    return d


def shift(x, k=1):
    x = np.asarray(x, float)
    if k <= 0:
        return x
    return np.r_[np.full(k, np.nan), x[:-k]]


def xup(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(a.size, b.size)
    a, b = np.broadcast_to(a, (n,)), np.broadcast_to(b, (n,))
    r = np.zeros(n, bool)
    r[1:] = (a[1:] > b[1:]) & (a[:-1] <= b[:-1])
    return r


def xdn(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(a.size, b.size)
    a, b = np.broadcast_to(a, (n,)), np.broadcast_to(b, (n,))
    r = np.zeros(n, bool)
    r[1:] = (a[1:] < b[1:]) & (a[:-1] >= b[:-1])
    return r


def first_true(cond):
    cond = np.asarray(cond, bool)
    r = cond.copy()
    r[1:] &= ~cond[:-1]
    return r


# =============================================================================
# Data wrapper (memoized indicators)
# =============================================================================


class Data:
    def __init__(self, df: pd.DataFrame):
        self.idx = df.index
        self.o = df["open"].to_numpy(float)
        self.h = df["high"].to_numpy(float)
        self.l = df["low"].to_numpy(float)
        self.c = df["close"].to_numpy(float)
        self.v = df["volume"].to_numpy(float) if "volume" in df.columns else None
        self.n = len(df)
        self._m: dict = {}
        self.atr = atr(self.h, self.l, self.c, 14)

    def _memo(self, key, fn):
        if key not in self._m:
            self._m[key] = fn()
        return self._m[key]

    def ema(self, n): return self._memo(("ema", n), lambda: ema(self.c, n))
    def tema(self, n): return self._memo(("tema", n), lambda: tema(self.c, n))
    def dema(self, n): return self._memo(("dema", n), lambda: dema(self.c, n))
    def hma(self, n): return self._memo(("hma", n), lambda: hma(self.c, n))
    def zlema(self, n): return self._memo(("zlema", n), lambda: zlema(self.c, n))
    def rsi(self, n): return self._memo(("rsi", n), lambda: rsi(self.c, n))
    def adx(self, n=14): return self._memo(("adx", n), lambda: adx(self.h, self.l, self.c, n))

    def vwap(self):
        def f():
            tp = pd.Series((self.h + self.l + self.c) / 3, index=self.idx)
            v = pd.Series(self.v, index=self.idx)
            day = self.idx.normalize()
            return (tp * v).groupby(day).cumsum().div(v.groupby(day).cumsum()).to_numpy()
        return self._memo(("vwap",), f)


# =============================================================================
# Strategy registry
# =============================================================================


@dataclass
class Sig:
    long: np.ndarray
    short: np.ndarray
    exit_long: Optional[np.ndarray] = None    # signal that closes a LONG
    exit_short: Optional[np.ndarray] = None   # signal that closes a SHORT
    flip: bool = True                         # opposite entry signal closes + reverses
    sl_atr: Optional[float] = None
    tp_atr: Optional[float] = None
    max_bars: Optional[int] = None


STRATS: list[tuple[str, str, bool, Callable[[Data], Sig]]] = []


def strat(sid: str, desc: str, needs_volume: bool = False):
    def deco(fn):
        STRATS.append((sid, desc, needs_volume, fn))
        return fn
    return deco


@strat("01_ema5_13_x_ema50", "EMA 5/13 cross, EMA50 trend filter")
def s01(d):
    e5, e13, e50 = d.ema(5), d.ema(13), d.ema(50)
    return Sig(xup(e5, e13) & (d.c > e50), xdn(e5, e13) & (d.c < e50))


@strat("02_ema8_21_adx", "EMA 8/21 cross, ADX(14) > 20")
def s02(d):
    e8, e21, a = d.ema(8), d.ema(21), d.adx(14)
    return Sig(xup(e8, e21) & (a > 20), xdn(e8, e21) & (a > 20))


@strat("03_ema_ribbon_pullback", "EMA ribbon 5/8/13/21/34 aligned, close re-crosses EMA8", )
def s03(d):
    e = [d.ema(n) for n in (5, 8, 13, 21, 34)]
    up = (e[0] > e[1]) & (e[1] > e[2]) & (e[2] > e[3]) & (e[3] > e[4])
    dn = (e[0] < e[1]) & (e[1] < e[2]) & (e[2] < e[3]) & (e[3] < e[4])
    return Sig(up & xup(d.c, e[1]), dn & xdn(d.c, e[1]),
               exit_long=e[0] < e[2], exit_short=e[0] > e[2], flip=False)


@strat("04_tema9_21_cross", "TEMA 9/21 cross")
def s04(d):
    a, b = d.tema(9), d.tema(21)
    return Sig(xup(a, b), xdn(a, b))


@strat("05_tema20_turn_ema100", "TEMA(20) slope turn, EMA100 filter")
def s05(d):
    t = d.tema(20)
    sl = t - shift(t, 1)
    e100 = d.ema(100)
    tu = (sl > 0) & (shift(sl, 1) <= 0)
    td = (sl < 0) & (shift(sl, 1) >= 0)
    return Sig(tu & (d.c > e100), td & (d.c < e100), exit_long=sl < 0, exit_short=sl > 0, flip=False)


@strat("06_hma9_21_cross", "HMA 9/21 cross")
def s06(d):
    a, b = d.hma(9), d.hma(21)
    return Sig(xup(a, b), xdn(a, b))


@strat("07_hma16_turn_hma55", "HMA(16) turn, HMA(55) direction filter")
def s07(d):
    h16, h55 = d.hma(16), d.hma(55)
    sl = h16 - shift(h16, 1)
    tu = (sl > 0) & (shift(sl, 1) <= 0)
    td = (sl < 0) & (shift(sl, 1) >= 0)
    up55 = h55 > shift(h55, 3)
    dn55 = h55 < shift(h55, 3)
    return Sig(tu & up55, td & dn55, exit_long=sl < 0, exit_short=sl > 0, flip=False)


@strat("08_dema10_30_rsi", "DEMA 10/30 cross, RSI(14) side of 50")
def s08(d):
    a, b, r = d.dema(10), d.dema(30), d.rsi(14)
    return Sig(xup(a, b) & (r > 50), xdn(a, b) & (r < 50))


@strat("09_zlema12_26_cross", "ZLEMA 12/26 cross")
def s09(d):
    a, b = d.zlema(12), d.zlema(26)
    return Sig(xup(a, b), xdn(a, b))


@strat("10_kama10_er", "Price x KAMA(10), efficiency ratio > 0.3")
def s10(d):
    k = kama(d.c, 10, 2, 30)
    er = efficiency_ratio(d.c, 10)
    return Sig(xup(d.c, k) & (er > 0.3), xdn(d.c, k) & (er > 0.3))


@strat("11_ema20_wick_pullback", "EMA20 wick-pullback in EMA20>EMA50 trend, RSI confirm")
def s11(d):
    e20, e50, r = d.ema(20), d.ema(50), d.rsi(14)
    up = (e20 > e50) & (e50 > shift(e50, 5))
    dn = (e20 < e50) & (e50 < shift(e50, 5))
    lo = up & (d.l <= e20) & (d.c > e20) & (d.c > d.o) & (r > 45)
    sh = dn & (d.h >= e20) & (d.c < e20) & (d.c < d.o) & (r < 55)
    return Sig(lo, sh, flip=False)


@strat("12_vwap_cross_ema21", "Price x daily VWAP, EMA21 slope agrees", needs_volume=True)
def s12(d):
    vw, e21 = d.vwap(), d.ema(21)
    up = e21 > shift(e21, 3)
    dn = e21 < shift(e21, 3)
    return Sig(xup(d.c, vw) & up, xdn(d.c, vw) & dn,
               exit_long=xdn(d.c, vw), exit_short=xup(d.c, vw))


@strat("13_supertrend_10_2_ema200", "Supertrend(10, 2.0) flip, EMA200 filter")
def s13(d):
    dr = supertrend_dir(d.h, d.l, d.c, 10, 2.0)
    e200 = d.ema(200)
    flip_up = (dr == 1) & (np.r_[0, dr[:-1]] == -1)
    flip_dn = (dr == -1) & (np.r_[0, dr[:-1]] == 1)
    return Sig(flip_up & (d.c > e200), flip_dn & (d.c < e200))


@strat("14_macd_6_19_5_ema100", "MACD(6,19,5) histogram zero-cross, EMA100 filter")
def s14(d):
    m = ema(d.c, 6) - ema(d.c, 19)
    hist = m - ema(m, 5)
    e100 = d.ema(100)
    return Sig(xup(hist, 0.0) & (d.c > e100), xdn(hist, 0.0) & (d.c < e100))


@strat("15_bb_squeeze_break", "Bollinger squeeze -> band breakout, EMA50 direction")
def s15(d):
    mid = sma(d.c, 20)
    sd = pd.Series(d.c).rolling(20).std(ddof=0).to_numpy()
    up, lo = mid + 2 * sd, mid - 2 * sd
    bw = (up - lo) / mid
    q = pd.Series(bw).rolling(100).quantile(0.2).to_numpy()
    sq = pd.Series(bw < q).astype(float).rolling(5).max().fillna(0).to_numpy() > 0
    e50 = d.ema(50)
    return Sig(sq & xup(d.c, up) & (d.c > e50), sq & xdn(d.c, lo) & (d.c < e50))


@strat("16_keltner_break_hma", "Keltner(EMA20, 1.5 ATR) breakout, HMA16 slope agrees")
def s16(d):
    mid = d.ema(20)
    up, lo = mid + 1.5 * d.atr, mid - 1.5 * d.atr
    h16 = d.hma(16)
    return Sig(xup(d.c, up) & (h16 > shift(h16, 2)), xdn(d.c, lo) & (h16 < shift(h16, 2)))


@strat("17_donchian20_adx", "Donchian(20) breakout, EMA50 + ADX > 18")
def s17(d):
    hh = pd.Series(d.h).rolling(20).max().shift(1).to_numpy()
    ll = pd.Series(d.l).rolling(20).min().shift(1).to_numpy()
    e50, a = d.ema(50), d.adx(14)
    return Sig(xup(d.c, hh) & (d.c > e50) & (a > 18), xdn(d.c, ll) & (d.c < e50) & (a > 18))


@strat("18_rsi7_meanrev_ema200", "RSI(7) dip/rip recovery in EMA200 trend (mean reversion)")
def s18(d):
    r, e200 = d.rsi(7), d.ema(200)
    return Sig(xup(r, 25.0) & (d.c > e200), xdn(r, 75.0) & (d.c < e200),
               exit_long=r > 55, exit_short=r < 45, flip=False, sl_atr=1.5, tp_atr=1.0)


@strat("19_stochrsi_hma34", "StochRSI K/D cross from extremes, HMA34 direction")
def s19(d):
    r = d.rsi(14)
    mn = pd.Series(r).rolling(14).min().to_numpy()
    mx = pd.Series(r).rolling(14).max().to_numpy()
    k = sma((r - mn) / np.where(mx - mn == 0, np.nan, mx - mn), 3)
    dd = sma(k, 3)
    h34 = d.hma(34)
    return Sig(xup(k, dd) & (k < 0.3) & (h34 > shift(h34, 2)),
               xdn(k, dd) & (k > 0.7) & (h34 < shift(h34, 2)), flip=False)


@strat("20_vol_spike_tema_momo", "Volume spike (>2x) + close>TEMA9>TEMA21 first bar", needs_volume=True)
def s20(d):
    t9, t21 = d.tema(9), d.tema(21)
    vr = d.v / sma(d.v, 30)
    up = (vr > 2) & (d.c > t9) & (t9 > t21) & (t9 > shift(t9, 1)) & (d.c > d.o)
    dn = (vr > 2) & (d.c < t9) & (t9 < t21) & (t9 < shift(t9, 1)) & (d.c < d.o)
    return Sig(first_true(up), first_true(dn), flip=False)


# =============================================================================
# Engine
# =============================================================================


@dataclass
class Params:
    sl_atr: float = 1.2
    tp_atr: float = 1.8
    max_bars: int = 40
    min_sl_pct: float = 0.08      # skip if SL distance < this % of price (fees would dominate)
    cooldown: int = 2             # bars after exit before a new entry
    fee_bps: float = 4.0          # per side (Binance USDT-M taker); use ~2 for maker-ish
    slip_bps: float = 1.0
    risk_pct: float = 0.5
    max_leverage: float = 5.0
    initial_equity: float = 10_000.0
    allow_long: bool = True
    allow_short: bool = True
    warm: int = 300


def run_engine(d: Data, s: Sig, p: Params, a: int, b: int):
    a = max(a, p.warm)
    o, h, l, c, at = (x.tolist() for x in (d.o, d.h, d.l, d.c, d.atr))
    L, S = s.long.tolist(), s.short.tolist()
    XL = s.exit_long.tolist() if s.exit_long is not None else None
    XS = s.exit_short.tolist() if s.exit_short is not None else None
    sl_m = p.sl_atr if s.sl_atr is None else s.sl_atr
    tp_m = p.tp_atr if s.tp_atr is None else s.tp_atr
    mb = p.max_bars if s.max_bars is None else s.max_bars
    fee, slip = p.fee_bps / 1e4, p.slip_bps / 1e4
    idx = d.idx

    equity = p.initial_equity
    eq = np.full(b - a, np.nan)
    pos = 0
    qty = entry = sl = tp = risk_amt = entry_fee = 0.0
    entry_i = 0
    last_exit = -10 ** 9
    pend_exit = False
    pend_dir = 0
    pend_sld = pend_tpd = 0.0
    trades: list[dict] = []

    def close_trade(i, px, reason):
        nonlocal pos, equity, qty, last_exit
        exit_fee = qty * px * fee
        gross = qty * (px - entry) * pos
        net = gross - exit_fee - entry_fee
        equity += gross - exit_fee
        trades.append(dict(entry_time=idx[entry_i], exit_time=idx[i],
                           side="long" if pos == 1 else "short", entry=entry, exit=px,
                           sl=sl, tp=tp, qty=qty, bars=i - entry_i, pnl=net,
                           R=net / risk_amt if risk_amt else np.nan, reason=reason))
        pos = 0
        qty = 0.0
        last_exit = i

    for i in range(a, b):
        # 1) pending signal exit at open
        if pos and pend_exit:
            close_trade(i, o[i] * (1 - slip * pos), "signal")
        pend_exit = False

        # 2) pending entry at open
        if pos == 0 and pend_dir:
            if i - last_exit >= p.cooldown:
                dd = pend_dir
                px = o[i] * (1 + slip * dd)
                if pend_sld / px * 100 >= p.min_sl_pct:
                    qty = min(equity * p.risk_pct / 100 / pend_sld, equity * p.max_leverage / px)
                    risk_amt = qty * pend_sld
                    entry_fee = qty * px * fee
                    equity -= entry_fee
                    pos, entry, entry_i = dd, px, i
                    sl = px - dd * pend_sld
                    tp = px + dd * pend_tpd
            pend_dir = 0

        # 3) intrabar SL / TP
        if pos:
            dd = pos
            if i > entry_i:
                if (o[i] - sl) * dd <= 0:
                    close_trade(i, o[i], "SL_gap")
                elif (o[i] - tp) * dd >= 0:
                    close_trade(i, o[i], "TP_gap")
            if pos:
                hit_sl = (l[i] <= sl) if dd == 1 else (h[i] >= sl)
                hit_tp = (h[i] >= tp) if dd == 1 else (l[i] <= tp)
                if hit_sl:
                    close_trade(i, sl * (1 - slip * dd), "SL")
                elif hit_tp:
                    close_trade(i, tp, "TP")

        # 4) bar-close logic
        if pos:
            if (XL is not None and pos == 1 and XL[i]) or (XS is not None and pos == -1 and XS[i]):
                pend_exit = True
            if i - entry_i >= mb:
                pend_exit = True
                # tagged as 'signal'; time stop is visible via bars column
        sd = 0
        if L[i] and not S[i] and p.allow_long:
            sd = 1
        elif S[i] and not L[i] and p.allow_short:
            sd = -1
        if sd and at[i] == at[i]:
            if pos == 0 or (pos == -sd and s.flip):
                pend_dir = sd
                pend_sld = sl_m * at[i]
                pend_tpd = tp_m * at[i]
                if pos == -sd:
                    pend_exit = True

        eq[i - a] = equity + (qty * (c[i] - entry) * pos if pos else 0.0)

    if pos:
        close_trade(b - 1, c[b - 1], "eod")
        eq[-1] = equity
    return pd.DataFrame(trades), pd.Series(eq, index=idx[a:b])


# =============================================================================
# Metrics
# =============================================================================


def summarize(trades: pd.DataFrame, eq: pd.Series, p: Params) -> dict:
    out = dict(n=len(trades), wr=np.nan, pf=np.nan, expR=np.nan, ret=np.nan, dd=np.nan,
               sharpe=np.nan, avg_bars=np.nan)
    if len(eq) < 3:
        return out
    dt = pd.Series(eq.index).diff().dt.total_seconds().median()
    bpy = 365 * 24 * 3600 / dt if dt and dt > 0 else np.nan
    r = eq.pct_change().dropna()
    out["ret"] = (eq.iloc[-1] / p.initial_equity - 1) * 100
    out["dd"] = (eq / eq.cummax() - 1).min() * 100
    out["sharpe"] = r.mean() / r.std() * np.sqrt(bpy) if r.std() > 0 else np.nan
    if len(trades):
        w, ls = trades[trades.pnl > 0], trades[trades.pnl <= 0]
        out["wr"] = len(w) / len(trades) * 100
        out["pf"] = w.pnl.sum() / abs(ls.pnl.sum()) if len(ls) and ls.pnl.sum() != 0 else np.inf
        out["expR"] = trades.R.mean()
        out["avg_bars"] = trades.bars.mean()
    return out


# =============================================================================
# Data loading
# =============================================================================


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    tcol = next(c for c in ("timestamp", "time", "open_time", "datetime", "date") if c in df.columns)
    t = df[tcol]
    if np.issubdtype(t.dtype, np.number):
        df.index = pd.to_datetime(t, unit="ms" if t.iloc[0] > 1e11 else "s", utc=True)
    else:
        df.index = pd.to_datetime(t, utc=True)
    cols = ["open", "high", "low", "close"] + (["volume"] if "volume" in df.columns else [])
    return df[cols].sort_index()[~df.index.duplicated()].astype(float)


def fetch_binance(symbol: str, tf: str, days: int) -> pd.DataFrame:
    import ccxt  # pip install ccxt
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    since = ex.milliseconds() - days * 86_400_000
    rows = []
    while True:
        bch = ex.fetch_ohlcv(symbol, tf, since=since, limit=1500)
        if not bch:
            break
        rows += bch
        since = bch[-1][0] + 1
        if len(bch) < 1500:
            break
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("timestamp"), unit="ms", utc=True)
    return df.iloc[:-1]


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    rule = tf.replace("m", "min") if tf.endswith("m") and not tf.endswith("min") else tf
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    return df.resample(rule).agg(agg).dropna()


def synthetic(n: int = 60_000, seed: int = 11) -> pd.DataFrame:
    """1m regime-switching series (trend / chop / mean-revert). Smoke tests only."""
    rng = np.random.default_rng(seed)
    ret = np.zeros(n)
    i = 0
    while i < n:
        L = int(rng.integers(300, 1500))
        reg = rng.choice(["trend", "chop", "mr"])
        drift = rng.choice([-1, 1]) * 0.00004 if reg == "trend" else 0.0
        sd = 0.0008 if reg == "trend" else 0.0006
        ph = -0.3 if reg == "mr" else 0.0
        for j in range(i, min(i + L, n)):
            prev = ret[j - 1] if j else 0.0
            ret[j] = drift + ph * prev + sd * rng.standard_normal()
        i += L
    close = 100 * np.exp(np.cumsum(ret))
    open_ = np.r_[close[0], close[:-1]]
    wick = np.abs(rng.standard_normal(n)) * 0.0004 * close
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - wick
    vol = rng.lognormal(0, 0.5, n) * 100 * (1 + 400 * np.abs(ret))
    idx = pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


# =============================================================================
# Self-test: signals must be causal (truncating the future must not change the past)
# =============================================================================


def selftest(df: pd.DataFrame, only: Optional[set] = None) -> bool:
    k = int(len(df) * 0.6)
    full, part = Data(df), Data(df.iloc[:k])
    ok = True
    for sid, _, needs_vol, fn in STRATS:
        if only and sid[:2] not in only:
            continue
        if needs_vol and "volume" not in df.columns:
            continue
        a, b = fn(full), fn(part)
        same = np.array_equal(a.long[:k], b.long) and np.array_equal(a.short[:k], b.short)
        for ea, eb in ((a.exit_long, b.exit_long), (a.exit_short, b.exit_short)):
            if ea is not None:
                same &= np.array_equal(ea[:k], eb)
        print(f"  selftest {sid:<28} {'OK' if same else 'LOOKAHEAD!'}")
        ok &= same
    return ok


# =============================================================================
# Runner
# =============================================================================


def main():
    ap = argparse.ArgumentParser(description="20 scalping MA strategies, IS/OOS leaderboard")
    ap.add_argument("--csv")
    ap.add_argument("--symbol", default="SUI/USDT:USDT")
    ap.add_argument("--tf", default="1m", help="1m / 3m / 5m (csv is resampled if finer)")
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--oos", type=float, default=0.3, help="out-of-sample fraction (tail)")
    ap.add_argument("--only", default="", help="comma list of strategy numbers, e.g. 01,04,13")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="scalp_out")
    for k, v in asdict(Params()).items():
        if isinstance(v, bool):
            ap.add_argument(f"--{k}", type=lambda s: s.lower() in ("1", "true", "yes"), default=v)
        else:
            ap.add_argument(f"--{k}", type=type(v), default=v)
    a = ap.parse_args()
    p = Params(**{k: getattr(a, k) for k in asdict(Params())})

    if a.synthetic:
        df = synthetic()
    elif a.csv:
        df = load_csv(a.csv)
    else:
        df = fetch_binance(a.symbol, "1m" if a.tf != "1m" else a.tf, a.days)
    if a.tf != "1m":
        df = resample(df, a.tf)

    only = {x.strip().zfill(2) for x in a.only.split(",") if x.strip()} or None
    print(f"{df.index[0]} -> {df.index[-1]}  {len(df)} bars  tf={a.tf}")
    if a.selftest:
        print("causality self-test:")
        if not selftest(df, only):
            raise SystemExit("lookahead detected, aborting")

    d = Data(df)
    split = p.warm + int((d.n - p.warm) * (1 - a.oos))
    os.makedirs(os.path.join(a.out, "trades"), exist_ok=True)
    rows = []
    for sid, desc, needs_vol, fn in STRATS:
        if only and sid[:2] not in only:
            continue
        if needs_vol and d.v is None:
            print(f"skip {sid}: no volume column")
            continue
        sig = fn(d)
        t_is, e_is = run_engine(d, sig, p, 0, split)
        t_oo, e_oo = run_engine(d, sig, p, split, d.n)
        m_is, m_oo = summarize(t_is, e_is, p), summarize(t_oo, e_oo, p)
        pd.concat([t_is.assign(seg="IS"), t_oo.assign(seg="OOS")]).to_csv(
            os.path.join(a.out, "trades", f"{sid}.csv"), index=False)
        rows.append({"strategy": sid,
                     **{f"IS_{k}": v for k, v in m_is.items()},
                     **{f"OOS_{k}": v for k, v in m_oo.items()}})
    if not rows:
        raise SystemExit("nothing ran")
    lb = pd.DataFrame(rows)
    lb.to_csv(os.path.join(a.out, "leaderboard.csv"), index=False)

    show = lb[["strategy", "IS_n", "IS_wr", "IS_pf", "IS_expR", "IS_ret", "IS_dd",
               "OOS_n", "OOS_wr", "OOS_pf", "OOS_expR", "OOS_ret", "OOS_dd", "OOS_sharpe"]]
    show = show.sort_values("OOS_expR", ascending=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(f"\ncosts: fee {p.fee_bps} bps/side, slip {p.slip_bps} bps | SL {p.sl_atr} ATR, TP {p.tp_atr} ATR, "
          f"time stop {p.max_bars} bars | IS = first {100 - a.oos * 100:.0f}%, OOS = last {a.oos * 100:.0f}%\n")
    print(show.round(2).to_string(index=False))
    print(f"\nsaved: {a.out}/leaderboard.csv, {a.out}/trades/<strategy>.csv")


if __name__ == "__main__":
    main()
