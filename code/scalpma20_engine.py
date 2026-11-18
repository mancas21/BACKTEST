#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""scalpma20_engine.py -- 20 DECLARED MA-family scalp strategies (1m / 5m) as a
harness adapter (`scalpma20`), executed by the repo's own audited book.

WHAT THIS IS
    Twenty rule-based strategies built from moving-average families (EMA, TEMA,
    DEMA, HMA, ZLEMA, KAMA), ribbons, pullbacks, VWAP, Supertrend, MACD,
    Bollinger squeeze, Keltner, Donchian, RSI / StochRSI and a volume-confirmed
    momentum rule. Selected with `--set id=1..20`.

    THE SIGNAL SET IS AN INVENTION OF THIS ENGINE, not a port. Every constant
    below is DECLARED BEFORE any market run and is never tuned: there is no
    source file to be faithful to, so the declaration IS the specification.
    Per AGENTS.md REGLA 1 each id is judged ONLY on its own artifacts; twenty
    ids on one dataset is a multiple-testing family -- the report must say so
    and must not cite the best id as a result of the family.

    The only geometry knobs exposed through --set (so `bt.py` neighborhood jobs
    can step them) are: sl_atr, tp_atr, max_hold, cost_gate_mult, atr_len.
    Strategy rules themselves are FIXED (they cannot be widened by --set).

EXECUTION (the repo's Book, imported from code/p100_screen_engine.py unchanged)
    * signal on the CLOSED bar i -> fill at bar i+1 OPEN (next-open), taker.
    * SL / TP are ATR multiples of the SIGNAL bar's ATR(atr_len), frozen at the
      signal (SL = close -/+ sl_atr*ATR, TP = close +/- tp_atr*ATR).
    * stop-first on ties; an open that gaps through the stop fills AT THE OPEN
      (`stop_gap`); TP is a resting limit (Book charges the repo slip on it too).
    * time stop: close at the OPEN of the bar after `max_hold` bars held.
    * opposite entry signal while positioned: flips (close + open at the same
      next open) ONLY for strategies declared flip=True; flip=False ignores it.
      A GATED opposite signal on a flip=True strategy closes without reversing.
    * per-strategy signal exits (exit_long / exit_short) close at the next open.
    * one position at a time, no pyramiding, end of data: force close at the last
      close (counted as `end_of_data`).
    * sizing: 1% of equity risked to the stop, notional capped at 20x equity.
    * costs: repo standard 5 bps fee + 0.5 bps slip per side (11 bps round
      trip), charged on entry AND exit. Zero-cost control runs INSIDE the
      artifact on the same signals (drag_pp is measured, never derived).
    * funding: charged at the real settlements (the harness serves
      data/binance_funding/<SYM>_funding.json when it exists; no file -> NOT
      charged and `funding_charged` says so).
    * COST GATE (declared, measured): a signal is skipped when its TP distance
      is < cost_gate_mult x 11 bps (default 3.0 -> a win must clear 3x the round
      trip, i.e. cost <= ~33% of a winning trade's gross, the repo's "cost <
      30%" gate spirit). `signal_rows` vs `signal_gate_pass` publish how many
      signals the gate removed -- at 1m on low-vol majors that is most of them,
      which is itself a finding, not a bug. cost_gate_mult=0 switches it off.
    * warmup: the first 300 bars are never traded (EMA200 / HMA55 seeds).
    * OOS: frozen 70/30 split by bar index on the TRADED window (warm..end),
      measured in-artifact (oos_profit_factor / oos_return_pct), like
      htffvg_engine / pack20_wrap. Thirds, best-5 concentration and a seeded
      (7) 20,000-draw bootstrap of mean PnL are also in the artifact.
    * accounting invariant: (cash - INIT) == sum(pnl) - funding_paid, asserted
      inside every run; a broken ledger fails loudly.

DATA
    1m: data/binance_klines_1m ; 5m: data/binance_klines_5m (the REAL history,
    NOT the data/binance_klines 30-day stub) -- the same dirs as `scalpwave`.
    Columns: open_ts (ms), open, high, low, close, volume. Strategies 12 (VWAP)
    and 20 (volume spike) need `volume` and refuse to run without it.
    `slice_from` / `slice_to` bound the window (a memory / time decision that
    lands in the params and therefore in run_id, never a silent cherry-pick).

SELF-TEST  (REQUIRED BEFORE ANY REAL-DATA RUN)
    python code/scalpma20_engine.py
    known answers on synthetic bars (stop, TP, short mirror, gap-through, time
    stop, signal exit, flip / no-flip, cost gate, funding, no signal) + indicator
    identities (WMA, TEMA/HMA on a ramp) + a CAUSALITY truncation test over all
    20 strategies. Synthetic scenarios carry NO run_id.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_VERSION = "scalpma20-1"
INIT = 10_000.0
FEE_BPS = 5.0           # per side (repo standard)
SLIP_BPS = 0.5          # per side
COST_RT_BPS = 2 * (FEE_BPS + SLIP_BPS)
WARM = 300
OOS_FRAC = 0.30

# declared geometry defaults (NOT tuned; exposed through --set for neighborhood)
GEO_DEFAULT = dict(sl_atr=1.2, tp_atr=1.8, max_hold=40, cost_gate_mult=3.0, atr_len=14)


def _p100():
    """The repo's audited Book, by path (module bytes are part of run_id via
    the adapter's `sources`)."""
    name = "p100_screen_engine"
    if name in sys.modules:
        return sys.modules[name]
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ═════════════════════════════ indicators ═════════════════════════════════
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


def _cross(a, b, up: bool):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(a.size, b.size)
    a, b = np.broadcast_to(a, (n,)), np.broadcast_to(b, (n,))
    r = np.zeros(n, bool)
    if up:
        r[1:] = (a[1:] > b[1:]) & (a[:-1] <= b[:-1])
    else:
        r[1:] = (a[1:] < b[1:]) & (a[:-1] >= b[:-1])
    return r


def xup(a, b):
    return _cross(a, b, True)


def xdn(a, b):
    return _cross(a, b, False)


def first_true(cond):
    cond = np.asarray(cond, bool)
    r = cond.copy()
    r[1:] &= ~cond[:-1]
    return r


class Data:
    """Arrays + memoized indicators for one kline frame."""

    def __init__(self, df: pd.DataFrame, atr_len: int = 14):
        self.idx = df["timestamp"] if "timestamp" in df.columns else df.index
        self.o = df["open"].to_numpy(float)
        self.h = df["high"].to_numpy(float)
        self.l = df["low"].to_numpy(float)
        self.c = df["close"].to_numpy(float)
        self.v = df["volume"].to_numpy(float) if "volume" in df.columns else None
        self.n = len(df)
        self._m: dict = {}
        self.atr = atr(self.h, self.l, self.c, atr_len)

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
            ts = pd.DatetimeIndex(self.idx)
            tp = pd.Series((self.h + self.l + self.c) / 3, index=ts)
            v = pd.Series(self.v, index=ts)
            day = ts.normalize()
            return (tp * v).groupby(day).cumsum().div(v.groupby(day).cumsum()).to_numpy()
        return self._memo(("vwap",), f)


# ═════════════════════════════ strategy registry ══════════════════════════
@dataclass
class Sig:
    long: np.ndarray
    short: np.ndarray
    exit_long: Optional[np.ndarray] = None     # closes a LONG position
    exit_short: Optional[np.ndarray] = None    # closes a SHORT position
    flip: bool = True                          # opposite entry closes + reverses
    sl_atr: Optional[float] = None             # per-strategy declared override
    tp_atr: Optional[float] = None


# id -> (name, description, needs_volume, fn)
STRATS: dict[int, tuple[str, str, bool, Callable[[Data], Sig]]] = {}


def strat(sid: int, name: str, desc: str, needs_volume: bool = False):
    def deco(fn):
        STRATS[sid] = (name, desc, needs_volume, fn)
        return fn
    return deco


@strat(1, "ema5_13_x_ema50", "EMA 5/13 cross, EMA50 trend filter")
def s01(d):
    e5, e13, e50 = d.ema(5), d.ema(13), d.ema(50)
    return Sig(xup(e5, e13) & (d.c > e50), xdn(e5, e13) & (d.c < e50))


@strat(2, "ema8_21_adx", "EMA 8/21 cross, ADX(14) > 20")
def s02(d):
    e8, e21, a = d.ema(8), d.ema(21), d.adx(14)
    return Sig(xup(e8, e21) & (a > 20), xdn(e8, e21) & (a > 20))


@strat(3, "ema_ribbon_pullback", "EMA ribbon 5/8/13/21/34 aligned, close re-crosses EMA8")
def s03(d):
    e = [d.ema(n) for n in (5, 8, 13, 21, 34)]
    up = (e[0] > e[1]) & (e[1] > e[2]) & (e[2] > e[3]) & (e[3] > e[4])
    dn = (e[0] < e[1]) & (e[1] < e[2]) & (e[2] < e[3]) & (e[3] < e[4])
    return Sig(up & xup(d.c, e[1]), dn & xdn(d.c, e[1]),
               exit_long=e[0] < e[2], exit_short=e[0] > e[2], flip=False)


@strat(4, "tema9_21_cross", "TEMA 9/21 cross")
def s04(d):
    a, b = d.tema(9), d.tema(21)
    return Sig(xup(a, b), xdn(a, b))


@strat(5, "tema20_turn_ema100", "TEMA(20) slope turn, EMA100 filter")
def s05(d):
    t = d.tema(20)
    sl = t - shift(t, 1)
    e100 = d.ema(100)
    tu = (sl > 0) & (shift(sl, 1) <= 0)
    td = (sl < 0) & (shift(sl, 1) >= 0)
    return Sig(tu & (d.c > e100), td & (d.c < e100), exit_long=sl < 0, exit_short=sl > 0, flip=False)


@strat(6, "hma9_21_cross", "HMA 9/21 cross")
def s06(d):
    a, b = d.hma(9), d.hma(21)
    return Sig(xup(a, b), xdn(a, b))


@strat(7, "hma16_turn_hma55", "HMA(16) turn, HMA(55) direction filter")
def s07(d):
    h16, h55 = d.hma(16), d.hma(55)
    sl = h16 - shift(h16, 1)
    tu = (sl > 0) & (shift(sl, 1) <= 0)
    td = (sl < 0) & (shift(sl, 1) >= 0)
    return Sig(tu & (h55 > shift(h55, 3)), td & (h55 < shift(h55, 3)),
               exit_long=sl < 0, exit_short=sl > 0, flip=False)


@strat(8, "dema10_30_rsi", "DEMA 10/30 cross, RSI(14) side of 50")
def s08(d):
    a, b, r = d.dema(10), d.dema(30), d.rsi(14)
    return Sig(xup(a, b) & (r > 50), xdn(a, b) & (r < 50))


@strat(9, "zlema12_26_cross", "ZLEMA 12/26 cross")
def s09(d):
    a, b = d.zlema(12), d.zlema(26)
    return Sig(xup(a, b), xdn(a, b))


@strat(10, "kama10_er", "Price x KAMA(10), efficiency ratio > 0.3")
def s10(d):
    k = kama(d.c, 10, 2, 30)
    er = efficiency_ratio(d.c, 10)
    return Sig(xup(d.c, k) & (er > 0.3), xdn(d.c, k) & (er > 0.3))


@strat(11, "ema20_wick_pullback", "EMA20 wick-pullback in EMA20>EMA50 trend, RSI confirm")
def s11(d):
    e20, e50, r = d.ema(20), d.ema(50), d.rsi(14)
    up = (e20 > e50) & (e50 > shift(e50, 5))
    dn = (e20 < e50) & (e50 < shift(e50, 5))
    lo = up & (d.l <= e20) & (d.c > e20) & (d.c > d.o) & (r > 45)
    sh = dn & (d.h >= e20) & (d.c < e20) & (d.c < d.o) & (r < 55)
    return Sig(lo, sh, flip=False)


@strat(12, "vwap_cross_ema21", "Price x daily VWAP, EMA21 slope agrees", needs_volume=True)
def s12(d):
    vw, e21 = d.vwap(), d.ema(21)
    return Sig(xup(d.c, vw) & (e21 > shift(e21, 3)), xdn(d.c, vw) & (e21 < shift(e21, 3)),
               exit_long=xdn(d.c, vw), exit_short=xup(d.c, vw))


@strat(13, "supertrend_10_2_ema200", "Supertrend(10, 2.0) flip, EMA200 filter")
def s13(d):
    dr = supertrend_dir(d.h, d.l, d.c, 10, 2.0)
    e200 = d.ema(200)
    prev = np.r_[0, dr[:-1]]
    return Sig(((dr == 1) & (prev == -1)) & (d.c > e200), ((dr == -1) & (prev == 1)) & (d.c < e200))


@strat(14, "macd_6_19_5_ema100", "MACD(6,19,5) histogram zero-cross, EMA100 filter")
def s14(d):
    m = ema(d.c, 6) - ema(d.c, 19)
    hist = m - ema(m, 5)
    e100 = d.ema(100)
    return Sig(xup(hist, 0.0) & (d.c > e100), xdn(hist, 0.0) & (d.c < e100))


@strat(15, "bb_squeeze_break", "Bollinger squeeze -> band breakout, EMA50 direction")
def s15(d):
    mid = sma(d.c, 20)
    sd = pd.Series(d.c).rolling(20).std(ddof=0).to_numpy()
    up, lo = mid + 2 * sd, mid - 2 * sd
    bw = (up - lo) / mid
    q = pd.Series(bw).rolling(100).quantile(0.2).to_numpy()
    sq = pd.Series(bw < q).astype(float).rolling(5).max().fillna(0).to_numpy() > 0
    e50 = d.ema(50)
    return Sig(sq & xup(d.c, up) & (d.c > e50), sq & xdn(d.c, lo) & (d.c < e50))


@strat(16, "keltner_break_hma", "Keltner(EMA20, 1.5 ATR) breakout, HMA16 slope agrees")
def s16(d):
    mid = d.ema(20)
    up, lo = mid + 1.5 * d.atr, mid - 1.5 * d.atr
    h16 = d.hma(16)
    return Sig(xup(d.c, up) & (h16 > shift(h16, 2)), xdn(d.c, lo) & (h16 < shift(h16, 2)))


@strat(17, "donchian20_adx", "Donchian(20) breakout, EMA50 + ADX > 18")
def s17(d):
    hh = pd.Series(d.h).rolling(20).max().shift(1).to_numpy()
    ll = pd.Series(d.l).rolling(20).min().shift(1).to_numpy()
    e50, a = d.ema(50), d.adx(14)
    return Sig(xup(d.c, hh) & (d.c > e50) & (a > 18), xdn(d.c, ll) & (d.c < e50) & (a > 18))


@strat(18, "rsi7_meanrev_ema200", "RSI(7) dip/rip recovery in EMA200 trend (mean reversion)")
def s18(d):
    r, e200 = d.rsi(7), d.ema(200)
    return Sig(xup(r, 25.0) & (d.c > e200), xdn(r, 75.0) & (d.c < e200),
               exit_long=r > 55, exit_short=r < 45, flip=False, sl_atr=1.5, tp_atr=1.0)


@strat(19, "stochrsi_hma34", "StochRSI K/D cross from extremes, HMA34 direction")
def s19(d):
    r = d.rsi(14)
    mn = pd.Series(r).rolling(14).min().to_numpy()
    mx = pd.Series(r).rolling(14).max().to_numpy()
    k = sma((r - mn) / np.where(mx - mn == 0, np.nan, mx - mn), 3)
    dd = sma(k, 3)
    h34 = d.hma(34)
    return Sig(xup(k, dd) & (k < 0.3) & (h34 > shift(h34, 2)),
               xdn(k, dd) & (k > 0.7) & (h34 < shift(h34, 2)), flip=False)


@strat(20, "vol_spike_tema_momo", "Volume spike (>2x) + close>TEMA9>TEMA21 first bar", needs_volume=True)
def s20(d):
    t9, t21 = d.tema(9), d.tema(21)
    vr = d.v / sma(d.v, 30)
    up = (vr > 2) & (d.c > t9) & (t9 > t21) & (t9 > shift(t9, 1)) & (d.c > d.o)
    dn = (vr > 2) & (d.c < t9) & (t9 < t21) & (t9 < shift(t9, 1)) & (d.c < d.o)
    return Sig(first_true(up), first_true(dn), flip=False)


# ═════════════════════════════ book + signal bridge ═══════════════════════
def _make_book_cls():
    P = _p100()

    class ScalpBook(P.Book):
        """The repo's Book with the funding arrays injected from the SERVED
        funding file (never from data/ on disk), so the artifact hash covers
        exactly the bytes the engine used."""

        def __init__(self, *a, funding_arrays=None, **kw):
            super().__init__(*a, **kw)
            if funding_arrays is None:
                self.rate = np.zeros(self.n)
                self.is_fund = np.zeros(self.n, bool)
                self.n_settlements = 0
            else:
                self.rate, self.is_fund, self.n_settlements = funding_arrays

    return ScalpBook


def funding_arrays_from_file(path, bar_ms):
    """(rate, is_event, n) per bar; a settlement at t maps to the first bar
    whose OPEN is at or after t (repo convention, same as p100.funding_events)."""
    rate = np.zeros(len(bar_ms))
    ev = np.zeros(len(bar_ms), bool)
    n = 0
    recs = json.load(open(path, encoding="utf-8"))
    for x in recs:
        j = int(np.searchsorted(bar_ms, int(x["t"]), side="left"))
        if j < len(bar_ms):
            ev[j] = True
            rate[j] = float(x["r"])
            n += 1
    first = int(recs[0]["t"]) if recs else None
    last = int(recs[-1]["t"]) if recs else None
    return (rate, ev, n), first, last


def make_signal_fn(book, d: Data, sig: Sig, geo: dict, counters: dict):
    L, S = sig.long, sig.short
    XL, XS = sig.exit_long, sig.exit_short
    atr_a, close = d.atr, d.c
    sl_m, tp_m = geo["sl_atr"], geo["tp_atr"]
    mh, gate = int(geo["max_hold"]), float(geo["cost_gate_mult"])

    def fn(j):
        pos = book.pos
        if pos is not None:
            if pos["side"] == 1 and XL is not None and XL[j]:
                return {"side": 0}
            if pos["side"] == -1 and XS is not None and XS[j]:
                return {"side": 0}
        if L[j] and not S[j]:
            sd = 1
        elif S[j] and not L[j]:
            sd = -1
        else:
            return None
        counters["rows"] += 1
        if pos is not None and (sd == pos["side"] or not sig.flip):
            return None
        a = atr_a[j]
        if a != a or a <= 0:
            return None
        c = close[j]
        tp_d = tp_m * a
        if gate > 0 and tp_d / c * 1e4 < gate * COST_RT_BPS:
            counters["gated"] += 1
            # a gated OPPOSITE signal on a flip strategy still closes the book
            return {"side": 0} if pos is not None else None
        return {"side": sd, "stop_px": c - sd * sl_m * a, "tp_px": c + sd * tp_d, "max_hold": mh}

    return fn


def run_book(df: pd.DataFrame, d: Data, sig: Sig, geo: dict, *, fee: float, slip: float,
             funding_arrays=None, warm: int = WARM, symbol="SYM", tf="1m"):
    Book = _make_book_cls()
    book = Book(symbol, tf, df, init=INIT, fee=fee, slip=slip,
                charge_funding=funding_arrays is not None, funding_arrays=funding_arrays)
    counters = {"rows": 0, "gated": 0}
    fn = make_signal_fn(book, d, sig, geo, counters)
    book.run(fn, start_idx=warm, end_idx=d.n - 1)
    return book, counters


# ═════════════════════════════ metrics ════════════════════════════════════
def _pf(pnls):
    gp = float(pnls[pnls > 0].sum()) if len(pnls) else 0.0
    gl = float(-pnls[pnls < 0].sum()) if len(pnls) else 0.0
    return gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)


def _thirds(e):
    out = []
    for k in range(3):
        a, b = int(len(e) * k / 3), int(len(e) * (k + 1) / 3)
        out.append(100.0 * (e[b - 1] / e[a] - 1.0) if b > a and e[a] > 0 else 0.0)
    return out


def book_summary(book, warm: int, split_i: int) -> dict:
    tr = book.trades
    pnls = np.array([t["pnl"] for t in tr], float)
    n = len(pnls)
    eq = np.array(book.equity_curve, float)
    pnl_sum = float(pnls.sum()) if n else 0.0
    resid = (book.cash - INIT) - (pnl_sum - book.funding_paid)
    if abs(resid) > max(1e-6, abs(pnl_sum) * 1e-9):
        raise AssertionError(
            f"accounting invariant broken: cash-INIT={book.cash - INIT:.8f} vs "
            f"sum(pnl)-funding={pnl_sum - book.funding_paid:.8f} (residual {resid:.8f})")
    peak = np.maximum.accumulate(eq) if len(eq) else np.array([INIT])
    mdd = float((eq / peak - 1).min()) if len(eq) else 0.0
    th = _thirds(eq) if len(eq) else [0.0, 0.0, 0.0]
    entry_idx = np.array([t["entry_idx"] for t in tr], int)
    oos_mask = entry_idx >= split_i if n else np.zeros(0, bool)
    opn = pnls[oos_mask] if n else np.zeros(0)
    k = max(0, min(len(eq) - 1, split_i - warm))
    oos_ret = 100.0 * (eq[-1] / eq[k] - 1.0) if len(eq) and eq[k] > 0 else 0.0
    srt = np.sort(pnls)[::-1] if n else np.zeros(0)
    best5 = float(srt[:5].sum()) if n else 0.0
    reasons = {}
    for t in tr:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    out = dict(
        return_pct=100.0 * (book.cash / INIT - 1.0),
        profit_factor=_pf(pnls),
        n_trades=int(n),
        win_rate=100.0 * float((pnls > 0).sum()) / n if n else 0.0,
        max_dd_pct=100.0 * mdd,
        thirds_net_pct=th,
        n_periods_green=int(sum(1 for x in th if x > 0)),
        oos_split_bar=int(split_i),
        oos_return_pct=oos_ret,
        oos_n_trades=int(oos_mask.sum()) if n else 0,
        oos_profit_factor=_pf(opn),
        best5_share_pct=(100.0 * best5 / pnl_sum) if pnl_sum > 0 else float("nan"),
        fees_paid_usdt=float(book.fees_paid),
        funding_paid_usdt=float(book.funding_paid),
        n_settlements=int(book.n_settlements),
        inv_gap_usd=float(resid),
        exits=reasons,
        n_long=int(sum(1 for t in tr if t["side"] == "long")),
        n_short=int(sum(1 for t in tr if t["side"] == "short")),
        avg_bars_held=float(np.mean([t["exit_idx"] - t["entry_idx"] for t in tr])) if n else 0.0,
    )
    if n > 1:
        rng = np.random.default_rng(7)
        boot = np.array([rng.choice(pnls, n, replace=True).mean() for _ in range(20000)])
        out["boot_ci_lo"] = float(np.percentile(boot, 2.5))
        out["boot_ci_hi"] = float(np.percentile(boot, 97.5))
        out["boot_p_le_zero"] = float((boot <= 0).mean())
        out["boot_draws"] = 20000
        out["boot_seed"] = 7
    return out, pnls


# ═════════════════════════════ adapter entry point ════════════════════════
def _load_frame(paths):
    frames = [pd.read_csv(x) for x in paths if str(x).lower().endswith(".csv")]
    if not frames:
        raise FileNotFoundError("scalpma20: no kline CSV among the inputs")
    df = pd.concat(frames, ignore_index=True)
    df.columns = [str(x).strip().lower() for x in df.columns]
    ts_col = "open_ts" if "open_ts" in df.columns else ("timestamp" if "timestamp" in df.columns else "open_time")
    df[ts_col] = pd.to_numeric(df[ts_col], errors="coerce")
    df = df.dropna(subset=[ts_col])
    df["timestamp"] = pd.to_datetime(df[ts_col].astype(np.int64), unit="ms", utc=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    return df


def run_symbol(paths, params):
    """Harness contract: (metrics, prov, tables)."""
    p = dict(params)
    sid = int(p.pop("id"))
    if sid not in STRATS:
        raise ValueError(f"scalpma20: unknown id {sid} (valid 1..20)")
    geo, explicit = dict(GEO_DEFAULT), set()
    for k in GEO_DEFAULT:
        if k in p:
            geo[k] = type(GEO_DEFAULT[k])(p.pop(k))
            explicit.add(k)
    use_funding = bool(p.pop("funding", True))
    slice_from = p.pop("slice_from", None)
    slice_to = p.pop("slice_to", None)
    sym_p = p.pop("symbol", None)
    tf_p = p.pop("tf", None)
    if p:
        raise ValueError(f"unknown scalpma20 params: {sorted(p)}")

    stem = os.path.basename(str(next(x for x in paths if str(x).lower().endswith(".csv"))))[:-4]
    sym, tf = (sym_p, tf_p) if (sym_p and tf_p) else stem.rsplit("_", 1)
    sym = str(sym).upper()

    df = _load_frame(paths)
    if slice_from:
        df = df[df["timestamp"] >= pd.Timestamp(slice_from, tz="UTC")]
    if slice_to:
        df = df[df["timestamp"] < pd.Timestamp(slice_to, tz="UTC")]
    df = df.reset_index(drop=True)
    if len(df) < WARM + 500:
        raise ValueError(f"scalpma20: only {len(df)} bars after slicing; need >= {WARM + 500}")

    name, desc, needs_vol, fn = STRATS[sid]
    if needs_vol and "volume" not in df.columns:
        raise ValueError(f"scalpma20 id {sid} ({name}) needs a volume column")
    d = Data(df, atr_len=geo["atr_len"])
    sig = fn(d)
    # declared per-strategy geometry override applies ONLY if --set did not pin it
    geo_eff = dict(geo)
    if sig.sl_atr is not None and "sl_atr" not in explicit:
        geo_eff["sl_atr"] = sig.sl_atr
    if sig.tp_atr is not None and "tp_atr" not in explicit:
        geo_eff["tp_atr"] = sig.tp_atr

    bar_ms = (df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
              .to_numpy().astype("datetime64[ms]").astype("int64"))
    fund_path = next((x for x in paths if str(x).lower().endswith(".json")), None)
    f_arr, f_first, f_last = None, None, None
    if use_funding and fund_path:
        f_arr, f_first, f_last = funding_arrays_from_file(fund_path, bar_ms)
    funding_covers = bool(f_arr is not None and f_first is not None
                          and f_first <= bar_ms[WARM] and f_last >= bar_ms[-1] - 8 * 3600 * 1000)

    split_i = WARM + int((d.n - WARM) * (1.0 - OOS_FRAC))
    fee, slip = FEE_BPS / 1e4, SLIP_BPS / 1e4
    book, cnt = run_book(df, d, sig, geo_eff, fee=fee, slip=slip, funding_arrays=f_arr,
                         symbol=sym, tf=tf)
    m, pnls = book_summary(book, WARM, split_i)
    zbook, _ = run_book(df, d, sig, geo_eff, fee=0.0, slip=0.0, funding_arrays=f_arr,
                        symbol=sym, tf=tf)
    zm, zp = book_summary(zbook, WARM, split_i)

    m.update(
        strategy_id=sid, strategy_name=name, symbol=sym, timeframe=tf,
        cost_bp_roundtrip=COST_RT_BPS, fee_bps_per_side=FEE_BPS, slippage_bps_per_side=SLIP_BPS,
        signal_rows=int(cnt["rows"]), signal_gated=int(cnt["gated"]),
        signal_gate_pass=int(cnt["rows"] - cnt["gated"]),
        ret_zero_pct=zm["return_pct"], pf_zero=zm["profit_factor"], n_zero=zm["n_trades"],
        drag_pp=zm["return_pct"] - m["return_pct"],
        funding_charged=bool(f_arr is not None), funding_covers_bars=funding_covers,
        funding_model=("real settlements" if f_arr is not None else "off (no funding file served)"),
        n_bars=int(d.n), warm_bars=WARM, oos_frac=OOS_FRAC,
        geometry=geo_eff,
    )
    m["gate_pf"] = bool(m["profit_factor"] > 1.2)
    m["gate_n"] = bool(m["n_trades"] >= 30)
    m["gate_net"] = bool(m["return_pct"] > 0)
    m["gate_thirds"] = bool(m["n_periods_green"] >= 2)
    m["gate_oos"] = bool(m["oos_profit_factor"] > 1.2 and m["oos_return_pct"] > 0)
    m["gate_conc"] = bool(np.isfinite(m["best5_share_pct"]) and m["best5_share_pct"] <= 100.0)
    m["gate_boot_ci"] = bool(m["n_trades"] > 1 and m.get("boot_ci_lo", 0.0) > 0)
    m["gate_all"] = bool(m["gate_pf"] and m["gate_n"] and m["gate_net"] and m["gate_thirds"]
                         and m["gate_oos"] and m["gate_conc"] and m["gate_boot_ci"])
    m["closed_pnl"] = [float(x) for x in pnls]

    prov = {"adapter": "scalpma20", "engine_version": ENGINE_VERSION,
            "fill_model": "taker_next_open",
            "signal_source": "DECLARED in this engine (no external source); see docstring",
            "strategy": f"{sid:02d}_{name}", "description": desc, "flip": sig.flip,
            "executor": "code/p100_screen_engine.py Book (unchanged)",
            "multiple_testing": "20-id family on one dataset: cite per-id artifacts only",
            "note": "ATR-based SL/TP frozen at the signal bar; cost gate declared; zero-cost "
                    "control and accounting invariant asserted inside the artifact"}
    tables = [dict(id="repo", kind="cost", cost="repo", net_pct=m["return_pct"], pf=m["profit_factor"],
                   n=m["n_trades"], maxDD_pct=m["max_dd_pct"]),
              dict(id="zero", kind="cost", cost="zero", net_pct=zm["return_pct"], pf=zm["profit_factor"],
                   n=zm["n_trades"], maxDD_pct=zm["max_dd_pct"])]
    return m, prov, tables


# ═════════════════════════════ known answers ══════════════════════════════
def _bars(n, o=100.0, h=101.0, l=99.0, c=100.0, edits=None):
    t0 = 1_700_000_000_000
    rows = []
    for i in range(n):
        r = dict(open=o, high=h, low=l, close=c, volume=10.0)
        if edits and i in edits:
            r.update(edits[i])
        rows.append(r)
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(t0 + np.arange(n) * 60_000, unit="ms", utc=True)
    return df


def _sig(n, long_at=(), short_at=(), xl=(), xs=(), flip=True):
    L, S = np.zeros(n, bool), np.zeros(n, bool)
    XL, XS = np.zeros(n, bool), np.zeros(n, bool)
    for i in long_at:
        L[i] = True
    for i in short_at:
        S[i] = True
    for i in xl:
        XL[i] = True
    for i in xs:
        XS[i] = True
    return Sig(L, S, exit_long=XL, exit_short=XS, flip=flip)


def _expect(entry_open, exit_px, stop, side, fee=FEE_BPS / 1e4, slip=SLIP_BPS / 1e4):
    """Hand arithmetic of one round trip (1% risk to |stop-open|, equity INIT)."""
    dist = abs(stop - entry_open)
    qty = INIT * 0.01 / dist
    efill = entry_open * (1 + side * slip)
    xfill = exit_px * (1 - side * slip)
    fee_in, fee_out = qty * efill * fee, qty * xfill * fee
    return qty * side * (xfill - efill) - fee_in - fee_out


def _run_case(df, sig, geo=None, funding=None):
    g = dict(GEO_DEFAULT)
    g.update(geo or {})
    d = Data(df, atr_len=g["atr_len"])
    book, cnt = run_book(df, d, sig, g, fee=FEE_BPS / 1e4, slip=SLIP_BPS / 1e4,
                         funding_arrays=funding, warm=30)
    return book, cnt


def known_answers():
    N = 80
    cases = []

    def check(name, cond, detail=""):
        cases.append((name, bool(cond), detail))

    # flat market, no signal -> flat equity
    book, _ = _run_case(_bars(N), _sig(N))
    check("no signal -> flat", len(book.trades) == 0 and abs(book.cash - INIT) < 1e-9)

    # LONG stop-out: ATR=2 -> stop 97.6 on signal close 100; bar 41 low 96
    book, _ = _run_case(_bars(N, edits={41: dict(low=96.0)}), _sig(N, long_at=[40]))
    t = book.trades[0] if book.trades else {}
    exp = _expect(100.0, 97.6, 97.6, 1)
    check("long stop-out", len(book.trades) == 1 and t.get("reason") == "stop"
          and abs(t["pnl"] - exp) < 1e-9 and abs(book.cash - (INIT + exp)) < 1e-9,
          f"pnl={t.get('pnl')} exp={exp}")

    # LONG TP: tp 103.6, bar 41 high 104
    book, _ = _run_case(_bars(N, edits={41: dict(high=104.0)}), _sig(N, long_at=[40]))
    t = book.trades[0] if book.trades else {}
    exp = _expect(100.0, 103.6, 97.6, 1)
    check("long TP", len(book.trades) == 1 and t.get("reason") == "tp" and abs(t["pnl"] - exp) < 1e-9,
          f"pnl={t.get('pnl')} exp={exp}")

    # SHORT stop-out: stop 102.4, bar 41 high 104
    book, _ = _run_case(_bars(N, edits={41: dict(high=104.0)}), _sig(N, short_at=[40]))
    t = book.trades[0] if book.trades else {}
    exp = _expect(100.0, 102.4, 102.4, -1)
    check("short stop-out", len(book.trades) == 1 and t.get("reason") == "stop" and t["side"] == "short"
          and abs(t["pnl"] - exp) < 1e-9, f"pnl={t.get('pnl')} exp={exp}")

    # SHORT TP: tp 96.4, bar 41 low 96
    book, _ = _run_case(_bars(N, edits={41: dict(low=96.0)}), _sig(N, short_at=[40]))
    t = book.trades[0] if book.trades else {}
    exp = _expect(100.0, 96.4, 102.4, -1)
    check("short TP", len(book.trades) == 1 and t.get("reason") == "tp" and abs(t["pnl"] - exp) < 1e-9,
          f"pnl={t.get('pnl')} exp={exp}")

    # gap-through: bar 42 opens at 95 (below the 97.6 stop) -> fill AT THE OPEN
    book, _ = _run_case(_bars(N, edits={42: dict(open=95.0, high=96.0, low=94.0, close=95.0)}),
                        _sig(N, long_at=[40]))
    t = book.trades[0] if book.trades else {}
    exp = _expect(100.0, 95.0, 97.6, 1)
    check("gap-through fills at open", len(book.trades) == 1 and t.get("reason") == "stop_gap"
          and abs(t["pnl"] - exp) < 1e-9, f"pnl={t.get('pnl')} exp={exp}")

    # stop-first on a bar spanning both stop and TP
    book, _ = _run_case(_bars(N, edits={41: dict(high=110.0, low=90.0)}), _sig(N, long_at=[40]))
    t = book.trades[0] if book.trades else {}
    check("stop wins ties", len(book.trades) == 1 and t.get("reason") == "stop")

    # time stop: entry idx 41, max_hold 5 -> close at OPEN of bar 46
    book, _ = _run_case(_bars(N), _sig(N, long_at=[40]), geo=dict(max_hold=5))
    t = book.trades[0] if book.trades else {}
    check("time stop", len(book.trades) == 1 and t.get("reason") == "time" and t["exit_idx"] == 46,
          f"{t}")

    # signal exit: exit_long on bar 43 -> close at open of 44
    book, _ = _run_case(_bars(N), _sig(N, long_at=[40], xl=[43]))
    t = book.trades[0] if book.trades else {}
    check("signal exit next open", len(book.trades) == 1 and t.get("reason") == "signal"
          and t["exit_idx"] == 44, f"{t}")

    # flip=True: short signal at 44 closes the long at open 45 and opens a short
    book, _ = _run_case(_bars(N), _sig(N, long_at=[40], short_at=[44], flip=True))
    rs = [t["reason"] for t in book.trades]
    check("flip reverses", rs[:1] == ["reverse"] and len(book.trades) == 2
          and book.trades[1]["side"] == "short", f"{rs}")

    # flip=False: the opposite signal is ignored, position ends at end_of_data
    book, _ = _run_case(_bars(N), _sig(N, long_at=[40], short_at=[44], flip=False), geo=dict(max_hold=500))
    check("no-flip ignores opposite", len(book.trades) == 1 and book.trades[0]["reason"] == "end_of_data",
          f"{[t['reason'] for t in book.trades]}")

    # cost gate: TP distance 360 bps; gate 40x11=440 -> skipped and counted
    book, cnt = _run_case(_bars(N), _sig(N, long_at=[40]), geo=dict(cost_gate_mult=40.0))
    check("cost gate skips + counts", len(book.trades) == 0 and cnt["rows"] == 1 and cnt["gated"] == 1,
          f"{cnt}")
    book, cnt = _run_case(_bars(N), _sig(N, long_at=[40]), geo=dict(cost_gate_mult=20.0))
    check("cost gate passes at 20x", len(book.trades) == 1 and cnt["gated"] == 0, f"{cnt}")

    # funding: settlement on bar 43 rate 0.001 against a long -> cash falls by qty*close*rate
    rate = np.zeros(N)
    ev = np.zeros(N, bool)
    rate[43], ev[43] = 0.001, True
    book, _ = _run_case(_bars(N), _sig(N, long_at=[40]), funding=(rate, ev, 1), geo=dict(max_hold=5))
    qty = INIT * 0.01 / 2.4
    exp_fund = qty * 100.0 * 0.001
    check("funding charged at settlement", abs(book.funding_paid - exp_fund) < 1e-9,
          f"paid={book.funding_paid} exp={exp_fund}")
    summ, _ = book_summary(book, 30, 60)
    check("accounting invariant", abs(summ["inv_gap_usd"]) < 1e-9, f"{summ['inv_gap_usd']}")

    # indicator identities
    check("wma([1,2,3],3) = 14/6", abs(wma(np.array([1.0, 2.0, 3.0]), 3)[-1] - 14 / 6) < 1e-12)
    ramp = np.arange(400, dtype=float)
    check("TEMA(9) of a ramp = ramp (zero steady lag)", abs(tema(ramp, 9)[-1] - ramp[-1]) < 1e-6,
          f"{tema(ramp, 9)[-1]}")
    # WMA(m) of a ramp lags exactly (m-1)/3. HMA(21): half=10, sqrt=5 ->
    # raw = 2*(x-3) - (x-20/3) = x + 2/3 ; final WMA(5) lags 4/3 -> x - 2/3.
    check("HMA(21) of a ramp = ramp - 2/3 (hand-derived residual lag)",
          abs(hma(ramp, 21)[-1] - (ramp[-1] - 2.0 / 3.0)) < 1e-9, f"{hma(ramp, 21)[-1]}")
    check("EMA of a constant is that constant", abs(ema(np.full(50, 7.0), 9)[-1] - 7.0) < 1e-12)
    check("xup detects one cross", list(np.where(xup(np.array([1, 2, 3, 2.0]), np.array([2, 2, 2, 2.0])))[0]) == [2])
    return cases


def causality_check(n=6000, seed=3):
    """Signals on a truncated series must equal the full-series signals on the
    shared prefix, for every id (no lookahead in any indicator)."""
    rng = np.random.default_rng(seed)
    ret = 0.0007 * rng.standard_normal(n) + 0.00002 * np.sin(np.arange(n) / 400)
    close = 100 * np.exp(np.cumsum(ret))
    openp = np.r_[close[0], close[:-1]]
    wick = np.abs(rng.standard_normal(n)) * 0.0004 * close
    df = pd.DataFrame(dict(open=openp, high=np.maximum(openp, close) + wick,
                           low=np.minimum(openp, close) - wick, close=close,
                           volume=rng.lognormal(0, 0.5, n) * 100 * (1 + 400 * np.abs(ret))))
    df["timestamp"] = pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC")
    k = int(n * 0.6)
    full, part = Data(df), Data(df.iloc[:k].reset_index(drop=True))
    res = []
    for sid, (name, _, _nv, fn) in STRATS.items():
        a, b = fn(full), fn(part)
        same = np.array_equal(a.long[:k], b.long) and np.array_equal(a.short[:k], b.short)
        for ea, eb in ((a.exit_long, b.exit_long), (a.exit_short, b.exit_short)):
            if ea is not None:
                same &= np.array_equal(ea[:k], eb)
        res.append((f"causal {sid:02d}_{name}", same, ""))
    return res


def _selftest() -> int:
    fails = 0
    rows = known_answers() + causality_check()
    for name, ok, detail in rows:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if (not ok and detail) else ""))
        fails += (not ok)
    print(f"\n{len(rows)} known answers, {fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
