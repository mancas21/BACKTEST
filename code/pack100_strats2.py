#!/usr/bin/env python
"""pack100_strats2.py -- prompts 31..100 of the Sonnet pack, extending
pack100_strats.SPECS in place (same plan builders, same conventions)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import pack100_strats as P
from pack50_core import Plan, atr, session_vwap
from pack50b_strats import _day_key, _minute_of_day, _prev_day_hlc, blank

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

rsi = P.rsi_            # builders below use the bare names
_roc = P.roc_
atr = P.atr_
ema = P.ema_
sma = P.sma_
don = P.don_
bb = P.bb_
from pack50_core import session_vwap as _session_vwap



def _bar_minutes(df):
    ts = pd.to_datetime(df["ts"], utc=True)
    return int(pd.Series(ts).diff().dt.total_seconds().dropna().median()) // 60


# ── C. breakouts & volatility (31-45) ─────────────────────────────────────
def _c31(d):
    ahi = P._daywin_hi(d, 0, 60)
    alo = P._daywin_lo(d, 0, 60)
    mod = pd.Series(_minute_of_day(d), index=d.index)
    le = (mod >= 60) & (d["close"] > ahi)
    se = (mod >= 60) & (d["close"] < alo)
    off = mod >= 1435
    return _lvl_plan(d, le, se, alo, ahi, xl=off, xs=off,
                     note="31 ORB 00:00-01:00 UTC; flat 23:55; stop opposite range end")
S("C31", 31, "opening-range breakout", "SPXUSDT", T2, fn=_c31)
S("C32", 32, "Bollinger squeeze breakout (NVDA)", "NVDAUSDT", T3, no_data=nd)


def _c33(d):
    lo, mid, hi = P.bb_(d["close"], 20, 2.0)
    kl, _, ku = P.kc_(*_t3(d), 20, 1.5, 10)
    sq = (hi < ku) & (lo > kl)
    ml, sg, hist = P.macd_(d["close"], 12, 26, 9)
    up = anyb(sq.shift(1)) & (hist > 0)
    dn = anyb(sq.shift(1)) & (hist < 0)
    return up, dn, hist < 0, hist > 0
_std("C33", 33, "TTM squeeze momentum", "SOLUSDT", T3,
     lambda d: _c33(d)[0], lambda d: _c33(d)[1], lambda d: _c33(d)[2],
     lambda d: _c33(d)[3])


def _c34(d):
    rng = d["high"] - d["low"]
    nr = rng == rng.rolling(7).min()
    nr_hi = d["high"].where(nr).ffill()
    nr_lo = d["low"].where(nr).ffill()
    nr_i = pd.Series(np.arange(len(d)), index=d.index).where(nr).ffill()
    fresh = ((np.arange(len(d)) - nr_i) <= 10).astype(bool)
    le = anyb(d["close"] > nr_hi) & fresh
    se = anyb(d["close"] < nr_lo) & fresh
    return _lvl_plan(d, le, se, nr_lo, nr_hi, hold=10,
                     note="34 NR7; stop at the opposite end of the NR bar")
S("C34", 34, "NR7 breakout", "HYPEUSDT", T3, fn=_c34)


def _c35(d):
    inside = (d["high"] < d["high"].shift(1)) & (d["low"] > d["low"].shift(1))
    m_hi = d["high"].shift(1).where(inside).ffill()
    m_lo = d["low"].shift(1).where(inside).ffill()
    m_mid = (m_hi + m_lo) / 2.0
    m_i = pd.Series(np.arange(len(d)), index=d.index).where(inside).ffill()
    fresh = ((np.arange(len(d)) - m_i) <= 10).astype(bool)
    le = anyb(d["close"] > m_hi) & fresh
    se = anyb(d["close"] < m_lo) & fresh
    return _lvl_plan(d, le, se, m_lo, m_hi, xl=d["close"] < m_mid,
                     xs=d["close"] > m_mid, r_mult=2.0,
                     note="35 inside bar; stop mother extreme; TP 2R; exit mother mid")
S("C35", 35, "inside-bar breakout", "SUIUSDT", T3, fn=_c35)
_std("C36", 36, "ATR expansion momentum (long)", "ETHUSDT", T3,
     lambda d: anyb(((d["high"] - d["low"]) > 2 * P.atr_(*_t3(d), 14))
                    & ((d["close"] - d["low"]) / (d["high"] - d["low"]).replace(0, np.nan) > 0.75)),
     None, lambda d: d["close"] < P.ema_(d["close"], 20), None, slm=2.0, hold=8)


def _c37(d):
    a = P.atr_(*_t3(d), 14)
    hh48 = d["high"].rolling(48).max()
    ll48 = d["low"].rolling(48).min()
    box = (hh48 - ll48) < 3 * a
    v = d["volume"] > 1.5 * P.sma_(d["volume"], 20)
    le = anyb((d["close"] > hh48.shift(1)) & box.shift(1) & v)
    se = anyb((d["close"] < ll48.shift(1)) & box.shift(1) & v)
    stop_l = ll48.where(box).ffill()
    stop_s = hh48.where(box).ffill()
    mid = (hh48 + ll48) / 2.0
    return _lvl_plan(d, le, se, stop_l, stop_s, xl=d["close"] < mid,
                     xs=d["close"] > mid, note="37 box breakout; stop at the box extreme")
S("C37", 37, "range-box breakout + volume", "BTCUSDT", T3, fn=_c37)
_std("C38", 38, "20-bar high breakout + volume (long)", "JUPUSDT", T3,
     lambda d: (d["close"] > P.don_(d["high"], d["low"], 20)[0])
     & (d["volume"] > 2 * P.sma_(d["volume"], 20)),
     None, lambda d: d["close"] < P.ema_(d["close"], 20), None, slm=2.0)


def _c39(d):
    ph, pl, _ = _prev_day_hlc(d)
    ph, pl = _s(ph), _s(pl)
    mod = pd.Series(_minute_of_day(d), index=d.index)
    off = mod >= 1435
    le = anyb(d["close"] > ph)
    se = anyb(d["close"] < pl)
    return _plan(d, le, se, off, off, slm=2.0, note="39 prev-day H/L; flat 23:55")
_std("C39", 39, "previous-day high/low breakout", "SPXUSDT", T3,
     lambda d: anyb(d["close"] > _s(_prev_day_hlc(d)[0])),
     lambda d: anyb(d["close"] < _s(_prev_day_hlc(d)[1])),
     lambda d: pd.Series(_minute_of_day(d), index=d.index) >= 1435,
     lambda d: pd.Series(_minute_of_day(d), index=d.index) >= 1435, slm=2.0)


def _c40(d):
    ts = pd.to_datetime(d["ts"], utc=True)
    wk = ts.dt.normalize() - pd.to_timedelta(ts.dt.dayofweek, unit="D")
    wmap_hi = d["high"].groupby(wk).first().groupby(wk).max()
    whi = d["high"].groupby(wk).transform("max")
    wlo = d["low"].groupby(wk).transform("min")
    # previous week's extremes: shift the WEEKLY aggregates back one week
    wk_uni = wk.drop_duplicates().sort_values()
    prev = pd.Series(index=wk_uni, dtype=float)
    wser_hi = whi.groupby(wk).first()
    wser_lo = wlo.groupby(wk).first()
    ph = wk.map(wser_hi.shift(1))
    pl = wk.map(wser_lo.shift(1))
    le = anyb(d["close"] > ph)
    se = anyb(d["close"] < pl)
    return le, se, d["close"] < ph, d["close"] > pl
_std("C40", 40, "previous-week high/low breakout", "BTCUSDT", ["1h"],
     lambda d: _c40(d)[0], lambda d: _c40(d)[1], lambda d: _c40(d)[2],
     lambda d: _c40(d)[3], slm=3.0)


def _c41(d):
    _, mid, hi = P.bb_(d["close"], 20, 2.0)
    adx, _, _ = P.adx_(*_t3(d), 14)
    walk = anyb((d["close"] > hi) & (d["close"].shift(1) > hi.shift(1)))
    return walk & (adx > 25), None, d["close"] < mid, None
_std("C41", 41, "Bollinger Band walk (long)", "SOLUSDT", T3,
     lambda d: _c41(d)[0], lambda d: _c41(d)[1], lambda d: _c41(d)[2],
     lambda d: _c41(d)[3])
S("C42", 42, "vol-contraction breakout (NVDA)", "NVDAUSDT", T3, no_data=nd)


def _c43(d):
    a = P.atr_(*_t3(d), 14)
    hot = a > a.rolling(100).median()
    hh, ll = P.don_(d["high"], d["low"], 55)
    ll20 = P.don_(d["high"], d["low"], 20)[1]
    le = (d["close"] > hh) & hot
    se = (d["close"] < ll) & hot
    return le, se, d["close"] < ll20, d["close"] > hh
_std("C43", 43, "Donchian(55) + volatility filter", "SUIUSDT", T3,
     lambda d: _c43(d)[0], lambda d: _c43(d)[1], lambda d: _c43(d)[2],
     lambda d: _c43(d)[3], slm=2.5)


def _c44(d):
    fh, fl = P._fractals(*_t3(d)[:2], 5)
    le = anyb(d["close"] > fh)
    se = anyb(d["close"] < fl)
    return _lvl_plan(d, le, se, fl, fh, xl=anyb(d["close"] < fl),
                     xs=anyb(d["close"] > fh),
                     note="44 fractal breakout; stop at the last opposite fractal")
S("C44", 44, "fractal breakout", "ETHUSDT", T3, fn=_c44)
_std("C45", 45, "impulse-bar continuation", "BTCUSDT", T3,
     lambda d: (d["close"].pct_change().abs()
                > 3 * d["close"].pct_change().rolling(100).std())
     & (d["close"].pct_change() > 0),
     lambda d: (d["close"].pct_change().abs()
                > 3 * d["close"].pct_change().rolling(100).std())
     & (d["close"].pct_change() < 0),
     None, None, slm=2.0, hold=6)

# ── D. momentum (46-55) ───────────────────────────────────────────────────
_std("D46", 46, "ROC(24) momentum (long)", "JUPUSDT", T3,
     lambda d: (_roc(d["close"], 24) > 0)
     & (_roc(d["close"], 24) > P.sma_(_roc(d["close"], 24), 10)),
     None, lambda d: _roc(d["close"], 24) < 0, None)
_std("D47", 47, "time-series momentum (long)", "SPXUSDT", T3,
     lambda d: (_roc(d["close"], 100) > 0) & (_roc(d["close"], 20) > 0),
     None, lambda d: _roc(d["close"], 20) < 0, None, slm=3.0)
S("D48", 48, "RSI momentum (NVDA)", "NVDAUSDT", T3, no_data=nd)


def _d49(d):
    ao = P._ao(d["high"], d["low"])
    z = ao * 0.0
    return anyb(xup(ao, z)), anyb(xdn(ao, z)), anyb(xdn(ao, z)), anyb(xup(ao, z))
_std("D49", 49, "Awesome Oscillator zero-cross", "SOLUSDT", T3,
     lambda d: _d49(d)[0], lambda d: _d49(d)[1], lambda d: _d49(d)[2],
     lambda d: _d49(d)[3])


def _d50(d):
    e13 = P.ema_(d["close"], 13)
    _, _, hist = P.macd_(d["close"], 12, 26, 9)
    le = (e13 > e13.shift(1)) & (hist > hist.shift(1))
    xe = (e13 < e13.shift(1)) | (hist < hist.shift(1))
    return le, None, xe, None
_std("D50", 50, "Elder Impulse (long)", "HYPEUSDT", T3,
     lambda d: _d50(d)[0], lambda d: _d50(d)[1], lambda d: _d50(d)[2],
     lambda d: _d50(d)[3])


def _d51(dfa, dfb):
    rb = dfb["close"].reset_index(drop=True)
    a = dfa.reset_index(drop=True)
    rel = _roc(a["close"], 24) - _roc(rb, 24)
    r14 = P.rsi_(a["close"], 14)
    btc_up = rb > P.ema_(rb, 50)
    le = (rel > 0) & (r14 > 55) & btc_up
    xl = rel < 0
    return _plan(a, le, None, xl, None, slm=2.0,
                 note="51 relative strength vs BTC (24-bar); BTC leg hashed")
S("D51", 51, "relative-strength-vs-BTC (long)", "SUIUSDT+BTCUSDT", T3,
  build2=_d51)


def _d52(d):
    t = P._trix(d["close"], 15)
    z = t * 0.0
    return anyb(xup(t, z)), anyb(xdn(t, z)), anyb(xdn(t, z)), anyb(xup(t, z))
_std("D52", 52, "TRIX(15) zero-cross", "ETHUSDT", T3,
     lambda d: _d52(d)[0], lambda d: _d52(d)[1], lambda d: _d52(d)[2],
     lambda d: _d52(d)[3])


def _d53(d):
    t = P._tsi(d["close"], 25, 13)
    sig = t.ewm(span=13, adjust=False).mean()
    le = xup(t, sig) & (t > 0)
    return le, None, xdn(t, sig), None
_std("D53", 53, "True Strength Index (long)", "BTCUSDT", T3,
     lambda d: _d53(d)[0], lambda d: _d53(d)[1], lambda d: _d53(d)[2],
     lambda d: _d53(d)[3])
_std("D54", 54, "MACD histogram acceleration (long)", "JUPUSDT", T3,
     lambda d: anyb((d["close"] > P.ema_(d["close"], 200))
                    & (P.macd_(d["close"], 12, 26, 9)[2]
                       > P.macd_(d["close"], 12, 26, 9)[2].shift(1))
                    & (P.macd_(d["close"], 12, 26, 9)[2].shift(1)
                       > P.macd_(d["close"], 12, 26, 9)[2].shift(2))
                    & (P.macd_(d["close"], 12, 26, 9)[2].shift(2)
                       > P.macd_(d["close"], 12, 26, 9)[2].shift(3))),
     None,
     lambda d: anyb((P.macd_(d["close"], 12, 26, 9)[2]
                     < P.macd_(d["close"], 12, 26, 9)[2].shift(1))
                    & (P.macd_(d["close"], 12, 26, 9)[2].shift(1)
                       < P.macd_(d["close"], 12, 26, 9)[2].shift(2)), 2),
     None, slm=2.0)
_std("D55", 55, "momentum acceleration", "SPXUSDT", T3,
     lambda d: (_roc(d["close"], 10) > 0)
     & ((_roc(d["close"], 10) - _roc(d["close"], 10).shift(5)) > 0),
     lambda d: (_roc(d["close"], 10) < 0)
     & ((_roc(d["close"], 10) - _roc(d["close"], 10).shift(5)) < 0),
     lambda d: (_roc(d["close"], 10) - _roc(d["close"], 10).shift(5)) < 0,
     lambda d: (_roc(d["close"], 10) - _roc(d["close"], 10).shift(5)) > 0)

# ── E. volume / VWAP / flow (56-65) ───────────────────────────────────────
S("E56", 56, "VWAP trend (NVDA)", "NVDAUSDT", T3, no_data=nd)


def _e57(d):
    av = P._anchored_vwap(d, 72)
    a = P.atr_(*_t3(d), 14)
    le = anyb((d["low"] <= av) & (d["close"] > av) & (d["close"] > d["open"]))
    xl = d["close"] < av - 0.5 * a
    return _plan(d, le, None, xl, None, slm=2.0,
                 note="57 anchored VWAP (72h lowest low), long only")
_std("E57", 57, "anchored-VWAP pullback (long)", "SOLUSDT", T3,
     lambda d: anyb((d["low"] <= P._anchored_vwap(d, 72))
                    & (d["close"] > P._anchored_vwap(d, 72))
                    & (d["close"] > d["open"])),
     None,
     lambda d: d["close"] < P._anchored_vwap(d, 72) - 0.5 * P.atr_(*_t3(d), 14),
     None, slm=2.0)


def _e58(d):
    o = _s(P.obv(d["close"], d["volume"]))
    le = anyb((o > o.rolling(50).max().shift(1)) & (d["close"] > P.ema_(d["close"], 50)))
    xl = o < P.ema_(o, 20)
    return _plan(d, le, None, xl, None, slm=2.0, note="58 OBV breakout (long)")
_std("E58", 58, "OBV breakout (long)", "HYPEUSDT", T3,
     lambda d: anyb((_s(P.obv(d["close"], d["volume"]))
                     > _s(P.obv(d["close"], d["volume"])).rolling(50).max().shift(1))
                    & (d["close"] > P.ema_(d["close"], 50))),
     None,
     lambda d: _s(P.obv(d["close"], d["volume"])) < P.ema_(_s(P.obv(d["close"], d["volume"])), 20),
     None, slm=2.0)


def _e59(d):
    cmf = P._cmf(*_t3(d), d["volume"], 20)
    le = xup(cmf, cmf * 0 + 0.1) & (d["close"] > P.ema_(d["close"], 50))
    return le, None, cmf < 0, None
_std("E59", 59, "Chaikin Money Flow (long)", "SUIUSDT", T3,
     lambda d: xup(P._cmf(*_t3(d), d["volume"], 20), P._cmf(*_t3(d), d["volume"], 20) * 0 + 0.1)
     & (d["close"] > P.ema_(d["close"], 50)),
     None, lambda d: P._cmf(*_t3(d), d["volume"], 20) < 0, None, slm=2.0)


def _e60(d):
    green = d["close"] > d["open"]
    clim = green & (d["volume"] > 3 * P.sma_(d["volume"], 20)) \
        & (P.rsi_(d["close"], 14).shift(1) < 25)
    le = anyb(clim)
    r = P.rsi_(d["close"], 14)
    return _plan(d, le, None, r > 55, None, slm=2.0, hold=12,
                 note="60 volume-climax reversal")
_std("E60", 60, "volume-climax reversal (long)", "ETHUSDT", T3,
     lambda d: anyb((d["close"] > d["open"])
                    & (d["volume"] > 3 * P.sma_(d["volume"], 20))
                    & (P.rsi_(d["close"], 14).shift(1) < 25)),
     None, lambda d: P.rsi_(d["close"], 14) > 55, None, slm=2.0, hold=12)


def _e61(d):
    dp = (d["close"] - d["open"]) / (d["high"] - d["low"]).replace(0, np.nan) * d["volume"]
    s10 = dp.rolling(10).sum()
    sd = s10.rolling(100).std()
    le = (s10 > 2 * sd) & (d["close"] > P.ema_(d["close"], 20))
    return le, None, s10 < 0, None
_std("E61", 61, "delta-proxy momentum (long)", "BTCUSDT", T3,
     lambda d: ((d["close"] - d["open"]) / (d["high"] - d["low"]).replace(0, np.nan)
                * d["volume"]).rolling(10).sum()
     > 2 * ((d["close"] - d["open"]) / (d["high"] - d["low"]).replace(0, np.nan)
            * d["volume"]).rolling(10).sum().rolling(100).std(),
     None,
     lambda d: ((d["close"] - d["open"]) / (d["high"] - d["low"]).replace(0, np.nan)
                * d["volume"]).rolling(10).sum() < 0,
     None, slm=2.0)


def _e62(d):
    vw = P._vwma(d["close"], d["volume"], 20)
    sm = P.sma_(d["close"], 20)
    le = (vw > sm) & (d["close"] > vw)
    se = (vw < sm) & (d["close"] < vw)
    return le, se, vw < sm, vw > sm
_std("E62", 62, "VWMA vs SMA volume trend", "JUPUSDT", T3,
     lambda d: _e62(d)[0], lambda d: _e62(d)[1], lambda d: _e62(d)[2],
     lambda d: _e62(d)[3])


def _e63(d):
    f = P._force(d["close"], d["volume"], 13)
    le = xup(f, f * 0.0) & (d["close"] > P.ema_(d["close"], 50))
    return le, None, xdn(f, f * 0.0), None
_std("E63", 63, "Force Index trend (long)", "SPXUSDT", T3,
     lambda d: xup(P._force(d["close"], d["volume"], 13), P._force(d["close"], d["volume"], 13) * 0.0)
     & (d["close"] > P.ema_(d["close"], 50)),
     None,
     lambda d: xdn(P._force(d["close"], d["volume"], 13), P._force(d["close"], d["volume"], 13) * 0.0),
     None, slm=2.0)
S("E64", 64, "low-volume pullback (NVDA)", "NVDAUSDT", T3, no_data=nd)


def _e65(d):
    poc = P._poc(*_t3(d), d["volume"], 200, 50, 10)
    v = d["volume"] > P.sma_(d["volume"], 20)
    le = xup(d["close"], poc) & v
    se = xdn(d["close"], poc) & v
    return le, se, xdn(d["close"], poc), xup(d["close"], poc)
_std("E65", 65, "volume-profile POC", "SOLUSDT", T3,
     lambda d: _e65(d)[0], lambda d: _e65(d)[1], lambda d: _e65(d)[2],
     lambda d: _e65(d)[3])
print("pack100_strats2: part 2a loaded (31-65)")

import pack100_strats3  # noqa: E402,F401  (extends SPECS in place)

from pack100_strats3 import costs_for  # noqa: E402,F401
