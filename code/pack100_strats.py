#!/usr/bin/env python
"""pack100_strats.py -- the 100 prompts of
`Downloads/strategy_prompts_100-sonnet-claude.md` (numbered 01..100) turned
into explicit rules on the frozen pack50_core execution machinery (next-open
fills, SL-first ties, funding charged at the settlement instants).

DECLARED READINGS (the pack50 discipline, terse):
* Multi-TF prompts ("5m-15m-1h") expand into one spec per timeframe; the
  pack template itself says the TFs run separately. Sid = "A01-5m".
* Window: prompts say "past 6 months"; runs use the FULL file history (the
  repo convention); the report states each symbol's real window.
* Data: "SPCX" = SPXUSDT (plain 1m/1h klines on disk). NVDA prompts (04, 07,
  16, 24, 28, 32, 42, 48, 51, 56, 64, 72) are NO DATA -- never estimated.
  95 (open interest) and 96 (long/short ratio) need history not on disk:
  NO DATA. 94 needs JUP funding history, not on disk: NO DATA.
* Costs: the pack declares NO cost block; the headline runs at the repo gate
  (5.0 fee + 0.5 slip bps per side); 2x / breakeven / zero-cost controls are
  measured inside every artifact by the pack100 engine.
* Stops: ATR(14) x the prompt's mult from the SIGNAL close (run_plan freezes
  the level at the signal bar, fills at the next open); "exit at 2R" =
  target at 2x the stop distance. Session times are UTC. All indicator
  wrappers here return pd.Series so shift/compare semantics are uniform.
* 51/89 use a BTC aux leg (build2, hashed into the artifact); 90/91 map
  fully-closed 1h context onto the fine book (pack50b convention); 99/100
  are dollar-neutral ratio pairs.
* 65: POC recomputed every tenth bar over the trailing 200 bars (declared
  approximation). 81: hour ranking trained on the FIRST HALF of the file,
  traded on the second half. 73: the double-bottom book keeps at most the
  freshest pattern and discards stale ones (patterns older than 40 bars
  before the neckline break are dead).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pack50_core import (Plan, adx_di, atr, bollinger, donchian, ema, hma,
                         keltner, macd, psar, rank_pct_within, realized_vol,
                         rsi, rolling_z, session_vwap, sma, supertrend,
                         williams_r)
from pack50b_strats import (_day_key, _minute_of_day, _prev_day_hlc, blank,
                            cci, obv, stoch, zscore_pair_target)
from pack50d_strats import linreg_slope_r2, mfi

INIT = 10000.0


# ── Series-coercing wrappers (every builder sees pd.Series only) ──────────
def _s(x):
    return pd.Series(np.asarray(x, float))


def rsi_(c, n=14):
    return _s(rsi(c, n))


def atr_(h, l, c, n=14):
    return _s(atr(h, l, c, n))


def ema_(c, n):
    return _s(ema(c, n))


def sma_(c, n):
    return _s(sma(c, n))


def macd_(c, f=12, s=26, g=9):
    ml, sg, hist = macd(c, f, s, g)
    return _s(ml), _s(sg), _s(hist)


def bb_(c, n=20, k=2.0):
    lo, mid, hi = bollinger(c, n, k)
    return _s(lo), _s(mid), _s(hi)


def kc_(h, l, c, n=20, k=2.0, an=10):
    lo, mid, hi = keltner(h, l, c, n, k, an)
    return _s(lo), _s(mid), _s(hi)


def don_(h, l, n):
    hh, ll = donchian(h, l, n)
    return _s(hh), _s(ll)          # already shifted: PRIOR n bars


def adx_(h, l, c, n=14):
    a, p, m = adx_di(h, l, c, n)
    return _s(a), _s(p), _s(m)


def st_(h, l, c, p=10, m=3.0):
    d, line = supertrend(h, l, c, p, m)   # pack50_core returns (direction, line)
    return _s(line), _s(d)


def sar_(h, l):
    return _s(psar(h, l, 0.02, 0.2))


def wpr_(h, l, c, n=14):
    return _s(williams_r(h, l, c, n))


def stoch_(h, l, c, n=14, k=3, d=3):
    kk, dd = stoch(h, l, c, n, k, d)
    return _s(kk), _s(dd)


def ich_(h, l, t=9, k=26, s=52):
    ten, kij, a, b = ichimoku(h, l, t, k, s) if False else (None,) * 4
    # pack50b.ichimoku returns numpy 4-tuple; re-derive here with plotted spans
    hh = lambda n: _s(h).rolling(n, min_periods=n).max()
    ll = lambda n: _s(l).rolling(n, min_periods=n).min()
    tenkan = (hh(t) + ll(t)) / 2.0
    kijun = (hh(k) + ll(k)) / 2.0
    span_a = ((tenkan + kijun) / 2.0).shift(k)
    span_b = ((hh(s) + ll(s)) / 2.0).shift(k)
    return tenkan, kijun, span_a, span_b


def z_(x, n):
    return _s(rolling_z(x, n))


def anyb(x, k=1):
    return _s(x).fillna(False).astype(bool).rolling(k, min_periods=1).max().astype(bool)


def xup(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def xdn(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


def roc_(c, n):
    return c / c.shift(n) - 1.0


_roc = roc_


def _daywin_hi(df, lo_m, hi_m, col="high"):
    mod = pd.Series(_minute_of_day(df), index=df.index)
    day = _day_key(df)
    w = df[col].where((mod >= lo_m) & (mod < hi_m))
    return w.groupby(day).transform("max").where(mod >= hi_m).ffill()


def _daywin_lo(df, lo_m, hi_m):
    mod = pd.Series(_minute_of_day(df), index=df.index)
    day = _day_key(df)
    w = df["low"].where((mod >= lo_m) & (mod < hi_m))
    return w.groupby(day).transform("min").where(mod >= hi_m).ffill()


# ── plan builders ──────────────────────────────────────────────────────────
def _plan(df, le, se, xl=None, xs=None, slm=None, tpm=None, hold=None,
          note=""):
    n = len(df)
    a = atr_(df["high"], df["low"], df["close"], 14).to_numpy(float)
    c = df["close"].to_numpy(float)

    def _B(x):
        return np.asarray(pd.Series(blank(n) if x is None else x).fillna(False), bool)
    le, se = _B(le), _B(se)

    def B(x):
        return np.asarray(pd.Series(blank(n) if x is None else x).fillna(False), bool)
    xl, xs = B(xl), B(xs)
    ok = np.isfinite(a) & (a > 0)
    le, se = le & ok, se & ok
    stop_l = np.where(le, c - slm * a, np.nan)
    stop_s = np.where(se, c + slm * a, np.nan)
    if tpm is not None:
        tp_l = np.where(le, c + tpm * slm * a, np.nan)
        tp_s = np.where(se, c - tpm * slm * a, np.nan)
    else:
        tp_l = tp_s = None
    return Plan(le, se, xl, xs, stop_l, stop_s, tp_l, tp_s,
                time_stop=hold, note=note)


def _lvl_plan(df, le, se, stop_l_px, stop_s_px, xl=None, xs=None, tp_l_px=None,
              tp_s_px=None, r_mult=None, hold=None, note=""):
    """Explicit level stops (from the SIGNAL bar), optional 2R or level TP."""
    n = len(df)
    c = df["close"].to_numpy(float)
    sl_l = _s(stop_l_px).to_numpy(float)
    sl_s = _s(stop_s_px).to_numpy(float)

    def B(x):
        return np.asarray(pd.Series(blank(n) if x is None else x).fillna(False), bool)
    le = B(le) & np.isfinite(sl_l)
    se = B(se) & np.isfinite(sl_s)
    tp_l = (_s(tp_l_px).to_numpy(float) if tp_l_px is not None else
            (c + r_mult * np.abs(c - sl_l) if r_mult else None))
    tp_s = (_s(tp_s_px).to_numpy(float) if tp_s_px is not None else
            (c - r_mult * np.abs(c - sl_s) if r_mult else None))
    return Plan(le, se, B(xl), B(xs), np.where(le, sl_l, np.nan),
                np.where(se, sl_s, np.nan),
                np.where(le, tp_l, np.nan) if tp_l is not None else None,
                np.where(se, tp_s, np.nan) if tp_s is not None else None,
                time_stop=hold, note=note)


# ── fresh indicators ───────────────────────────────────────────────────────
def _kama(c, n=10, fast=2, slow=30):
    er = ((c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum()).fillna(0.0).clip(0, 1)
    sc = (er * (2.0 / (fast + 1) - 2.0 / (slow + 1)) + 2.0 / (slow + 1)) ** 2
    out = np.empty(len(c))
    prev = float(c.iloc[0])
    cn = c.to_numpy(float); scn = sc.to_numpy(float)
    for i in range(len(c)):
        prev = prev + scn[i] * (cn[i] - prev)
        out[i] = prev
    return pd.Series(out, index=c.index)


def _aroon(h, l, n=25):
    hh = _s(h).rolling(n).apply(np.argmax, raw=True).to_numpy(float)
    ll = _s(l).rolling(n).apply(np.argmin, raw=True).to_numpy(float)
    return _s(100.0 * hh / (n - 1)), _s(100.0 * ll / (n - 1))


def _trix(c, n=15):
    e3 = ema_(ema_(ema_(c, n), n), n)
    return 1e4 * e3.pct_change()


def _tsi(c, r=25, s=13):
    m = c.diff()
    return 100.0 * ema_(ema_(m, r), s) / ema_(ema_(m.abs(), r), s)


def _cmf(h, l, c, v, n=20):
    mfm = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    return (mfm * v).rolling(n).sum() / v.rolling(n).sum()


def _vwma(c, v, n=20):
    return (c * v).rolling(n).sum() / v.rolling(n).sum()


def _ao(h, l):
    return sma_((h + l) / 2.0, 5) - sma_((h + l) / 2.0, 34)


def _force(c, v, n=13):
    return ema_(v * c.diff(), n)


def _ibs(h, l, c):
    return (c - l) / (h - l).replace(0, np.nan)


def _var_ratio(c, q=10, win=200):
    r1 = np.log(c).diff()
    v1 = r1.rolling(win).var()
    qret = np.log(c).diff(q).dropna()
    vq = qret.rolling(max(win // q, 20)).var()
    vr = (vq / (q * v1)).reindex(c.index)
    return _s(vr)


def _poc(h, l, c, v, n=200, bins=50, refresh=10):
    tp = (h + l + c) / 3.0
    out = np.full(len(c), np.nan)
    hv = h.to_numpy(float); lv = l.to_numpy(float)
    tpn = tp.to_numpy(float); vn = v.to_numpy(float)
    for i in range(n, len(c), refresh):
        lo, hi = lv[i - n:i].min(), hv[i - n:i].max()
        if not np.isfinite(lo) or hi <= lo:
            continue
        b = np.clip(((tpn[i - n:i] - lo) / (hi - lo) * bins).astype(int), 0, bins - 1)
        w = np.bincount(b, weights=vn[i - n:i], minlength=bins)
        j = int(w.argmax())
        out[i:i + refresh] = lo + (j + 0.5) * (hi - lo) / bins
    return _s(out).ffill()


def _fractals(h, l, k=3):
    hn = h.to_numpy(float); ln = l.to_numpy(float)
    n = len(hn)
    ph = np.full(n, np.nan); pl = np.full(n, np.nan)
    lasth = lastl = np.nan
    for i in range(2 * k, n):
        j = i - k
        w = hn[j - k:j + k + 1]
        if hn[j] >= w.max() and (w == hn[j]).sum() == 1:
            lasth = hn[j]
        w = ln[j - k:j + k + 1]
        if ln[j] <= w.min() and (w == ln[j]).sum() == 1:
            lastl = ln[j]
        ph[i] = lasth
        pl[i] = lastl
    return _s(ph), _s(pl)


def _pin_bull(o, h, l, c):
    body = (c - o).abs()
    lower = np.minimum(c, o) - l
    rng = (h - l).replace(0, np.nan)
    return (lower > 2.0 * body) & (c > (h + l) / 2.0) & (body / rng < 0.5)


def _engulf(o, h, l, c):
    bull = (c > o) & (c.shift(1) < o.shift(1)) & (c >= o.shift(1)) & (o <= c.shift(1))
    bear = (c < o) & (c.shift(1) > o.shift(1)) & (c <= o.shift(1)) & (o >= c.shift(1))
    return bull.fillna(False), bear.fillna(False)


def _day_open(df):
    return df["open"].groupby(_day_key(df)).transform("first")


def _anchored_vwap(df, look=72):
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    v = df["volume"]
    cs_tp = (tp * v).cumsum().to_numpy(float)
    cs_v = v.cumsum().to_numpy(float)
    lo_idx = _s(df["low"]).rolling(look, min_periods=1).apply(np.argmin, raw=True)
    anchor_i = np.clip(np.arange(len(df)) - (look - 1) + lo_idx.to_numpy(float),
                       0, len(df) - 1).astype(int)
    i = np.arange(len(df))
    num = cs_tp[i] - cs_tp[anchor_i]
    den = cs_v[i] - cs_v[anchor_i]
    return _s(np.where(den > 0, num / np.where(den > 0, den, 1.0),
                       df["close"].to_numpy(float)))


def _last_zone(cond, top_s, bot_s):
    top = top_s.where(cond).ffill()
    bot = bot_s.where(cond).ffill()
    return top, bot


# ═══════════════════════════════ SPECS ═════════════════════════════════════
SPECS = {}
CODE = {}
T3 = ["5m", "15m", "1h"]
T2 = ["5m", "15m"]
T21 = ["15m", "1h"]


def S(pid, num, name, sym, tfs, fn=None, pair=None, build2=None, ctx=False,
      no_data=None):
    for tf in tfs:
        sid = f"{pid}-{tf}"
        spec = dict(pid=pid, num=num, name=name, sym=sym, tf=tf)
        if no_data:
            spec["no_data"] = no_data
        elif pair is not None:
            spec["pair"] = pair
        elif build2 is not None:
            spec["build2"] = build2
        elif ctx:
            spec["ctx"] = ctx
            spec["build"] = fn
        else:
            spec["build"] = fn
        SPECS[sid] = spec
    CODE.setdefault(pid, pid)


def _std(pid, num, name, sym, tfs, le, se, xl, xs, slm=2.0, tpm=None,
         hold=None, note=None):
    def build(df):
        return _plan(df, le(df), se(df) if se else None,
                     xl(df) if xl else None, xs(df) if xs else None,
                     slm=slm, tpm=tpm, hold=hold, note=note or "")
    S(pid, num, name, sym, tfs, fn=build)


def _t3(d):
    return d["high"], d["low"], d["close"]


# ── A. mean reversion (01-15) ─────────────────────────────────────────────
_std("A01", 1, "RSI14 L/S mean-reversion", "SPXUSDT", T3,
     lambda d: anyb(rsi_(d["close"], 14) < 30),
     lambda d: anyb(rsi_(d["close"], 14) > 70),
     lambda d: rsi_(d["close"], 14) > 50, lambda d: rsi_(d["close"], 14) < 50)
_std("A02", 2, "RSI2 Connors pullback (long)", "JUPUSDT", T3,
     lambda d: anyb((rsi_(d["close"], 2) < 10) & (d["close"] > ema_(d["close"], 200))),
     None, lambda d: d["close"] > sma_(d["close"], 5), None, slm=3.0)


def _a03(d):
    lo, mid, hi = bb_(d["close"], 20, 2.0)
    le = anyb(d["close"] < lo).shift(1).fillna(False) & (d["close"] > lo)
    se = anyb(d["close"] > hi).shift(1).fillna(False) & (d["close"] < hi)
    return le, se, d["close"] > mid, d["close"] < mid
_std("A03", 3, "Bollinger(20,2) reversion", "SPXUSDT", T3,
     lambda d: _a03(d)[0], lambda d: _a03(d)[1], lambda d: _a03(d)[2],
     lambda d: _a03(d)[3])
S("A04", 4, "BB %B + RSI (NVDA)", "NVDAUSDT", T3, no_data="no NVDA series on disk")
_std("A05", 5, "price z-score reversion", "JUPUSDT", T3,
     lambda d: anyb(z_(d["close"], 50) < -2), lambda d: anyb(z_(d["close"], 50) > 2),
     lambda d: z_(d["close"], 50) > 0, lambda d: z_(d["close"], 50) < 0, slm=2.5)


def _a06(d):
    k, dd = stoch_(*_t3(d), 14, 3, 3)
    return xup(k, dd) & (k < 20), xdn(k, dd) & (k > 80), k > 80, k < 20
_std("A06", 6, "Stochastic(14,3,3) reversion", "SPXUSDT", T3,
     lambda d: _a06(d)[0], lambda d: _a06(d)[1], lambda d: _a06(d)[2],
     lambda d: _a06(d)[3])
S("A07", 7, "CCI extreme reversion (NVDA)", "NVDAUSDT", T3, no_data="no NVDA series on disk")


def _a08(d):
    w = wpr_(*_t3(d), 14)
    return anyb((w.shift(1) < -90) & (w > -80)), None, w > -20, None
_std("A08", 8, "Williams %R reversal (long)", "HYPEUSDT", T3,
     lambda d: _a08(d)[0], lambda d: _a08(d)[1], lambda d: _a08(d)[2],
     lambda d: _a08(d)[3])


def _a09(d):
    m = mfi(d["high"], d["low"], d["close"], d["volume"], 14)
    return anyb((_s(m) < 20) & (rsi_(d["close"], 14) < 35)), None, _s(m) > 60, None
_std("A09", 9, "MFI+RSI oversold (long)", "SUIUSDT", T3,
     lambda d: _a09(d)[0], lambda d: _a09(d)[1], lambda d: _a09(d)[2],
     lambda d: _a09(d)[3])


def _a10(d):
    ib = _ibs(*_t3(d))
    return anyb((ib < 0.2) & (d["close"] > sma_(d["close"], 100))), None, ib > 0.7, None
_std("A10", 10, "IBS reversion (long)", "ETHUSDT", T3,
     lambda d: _a10(d)[0], lambda d: _a10(d)[1], lambda d: _a10(d)[2],
     lambda d: _a10(d)[3])


def _a11(d):
    v, sd = session_vwap(d, "1d")
    v, sd = _s(v), _s(sd)
    return anyb(d["close"] < v - 2 * sd), anyb(d["close"] > v + 2 * sd), \
        d["close"] >= v, d["close"] <= v
_std("A11", 11, "session-VWAP deviation reversion", "SUIUSDT", T3,
     lambda d: _a11(d)[0], lambda d: _a11(d)[1], lambda d: _a11(d)[2],
     lambda d: _a11(d)[3])


def _a12(d):
    e20 = ema_(d["close"], 20)
    kl, _, ku = kc_(*_t3(d), 20, 2.0, 10)
    le = anyb((d["close"].shift(1) < kl.shift(1)) & (d["close"] > kl))
    se = anyb((d["close"].shift(1) > ku.shift(1)) & (d["close"] < ku))
    return le, se, d["close"] > e20, d["close"] < e20
_std("A12", 12, "Keltner fade", "ETHUSDT", T3,
     lambda d: _a12(d)[0], lambda d: _a12(d)[1], lambda d: _a12(d)[2],
     lambda d: _a12(d)[3])
_std("A13", 13, "consecutive-down-bars bounce (long)", "BTCUSDT", T3,
     lambda d: anyb(d["close"] < d["open"], 4) & (d["close"] > ema_(d["close"], 200)),
     None, lambda d: d["close"] > d["high"].shift(1), None)
_std("A14", 14, "RSI(7) 20-bar-low reversal (long)", "JUPUSDT", T3,
     lambda d: anyb((rsi_(d["close"], 7) < 20)
                    & (d["close"] <= d["close"].rolling(20).min())),
     None, lambda d: rsi_(d["close"], 7) > 60, None)


def _a15(d):
    e50 = ema_(d["close"], 50)
    a = atr_(*_t3(d), 14)
    return anyb(d["close"] < e50 - 3 * a), anyb(d["close"] > e50 + 3 * a), \
        d["close"] > e50, d["close"] < e50
_std("A15", 15, "EMA(50) overextension reversion", "SPXUSDT", T3,
     lambda d: _a15(d)[0], lambda d: _a15(d)[1], lambda d: _a15(d)[2],
     lambda d: _a15(d)[3])

# ── B. trend (16-30) ──────────────────────────────────────────────────────
S("B16", 16, "EMA 9/21 crossover (NVDA)", "NVDAUSDT", T3, no_data="no NVDA series on disk")
_std("B17", 17, "EMA 20/50 trend + EMA200 filter (long)", "HYPEUSDT", T3,
     lambda d: anyb(xup(ema_(d["close"], 20), ema_(d["close"], 50))
                    & (d["close"] > ema_(d["close"], 200))),
     None, lambda d: xdn(ema_(d["close"], 20), ema_(d["close"], 50)), None, slm=3.0)


def _b18(d):
    line, _ = st_(*_t3(d), 10, 3.0)
    up = (line < d["close"]) & (line.shift(1) >= d["close"].shift(1))
    dn = (line > d["close"]) & (line.shift(1) <= d["close"].shift(1))
    return anyb(up), anyb(dn), anyb(dn), anyb(up)


def _b18b(d):
    line, _ = st_(*_t3(d), 10, 3.0)
    return line
def _b18_full(d):
    le, se, xl, xs = _b18(d)
    return _lvl_plan(d, le, se, _b18b(d), _b18b(d), xl, xs, hold=None,
                     note="stop = supertrend line")
S("B18", 18, "Supertrend(10,3) flip", "HYPEUSDT", T3, fn=_b18_full)


def _b19(d):
    hh, ll = don_(d["high"], d["low"], 20)
    ll10 = don_(d["high"], d["low"], 10)[1]
    le = d["close"] > hh
    se = d["close"] < ll
    return le, se, d["close"] < ll10, d["close"] > hh
_std("B19", 19, "Donchian(20/10) breakout", "SUIUSDT", T3,
     lambda d: _b19(d)[0], lambda d: _b19(d)[1], lambda d: _b19(d)[2],
     lambda d: _b19(d)[3])


def _b20(d):
    adx, dip, dim = adx_(*_t3(d), 14)
    le = anyb(xup(dip, dim) & (adx > 25) & (adx > adx.shift(1)))
    return le, None, (adx < 20) | xup(dim, dip), None
_std("B20", 20, "ADX + DI crossover (long)", "ETHUSDT", T3,
     lambda d: _b20(d)[0], lambda d: _b20(d)[1], lambda d: _b20(d)[2],
     lambda d: _b20(d)[3])


def _b21(d):
    ml, sg, _ = macd_(d["close"], 12, 26, 9)
    up = xup(ml, sg) & (ml > 0)
    dn = xdn(ml, sg)
    return anyb(up), anyb(dn), anyb(dn), anyb(up)
_std("B21", 21, "MACD trend (long)", "BTCUSDT", T3,
     lambda d: _b21(d)[0], lambda d: _b21(d)[1], lambda d: _b21(d)[2],
     lambda d: _b21(d)[3])


def _b22(d):
    ten, kij, sa, sb = ich_(d["high"], d["low"], 9, 26, 52)
    cloud = np.maximum(sa, sb)
    le = anyb((d["close"] > cloud) & (ten > kij))
    return le, None, d["close"] < kij, None
_std("B22", 22, "Ichimoku cloud breakout (long)", "JUPUSDT", T3,
     lambda d: _b22(d)[0], lambda d: _b22(d)[1], lambda d: _b22(d)[2],
     lambda d: _b22(d)[3])


def _b23(d):
    sar = sar_(*_t3(d)[:2])
    e100 = ema_(d["close"], 100)
    up = (sar < d["close"]) & (sar.shift(1) >= d["close"].shift(1))
    dn = (sar > d["close"]) & (sar.shift(1) <= d["close"].shift(1))
    le = anyb(up) & (d["close"] > e100)
    return le, None, anyb(dn), None


def _b23_full(d):
    le, se, xl, xs = _b23(d)
    return _lvl_plan(d, le, se, sar_(*_t3(d)[:2]), sar_(*_t3(d)[:2]), xl, xs,
                     note="stop = parabolic SAR")
S("B23", 23, "Parabolic SAR + EMA100 (long)", "SPXUSDT", T3, fn=_b23_full)
S("B24", 24, "Hull MA(55) slope (NVDA)", "NVDAUSDT", T3, no_data="no NVDA series on disk")


def _b25(d):
    e20 = ema_(d["close"], 20)
    _, _, ku = kc_(*_t3(d), 20, 2.0, 10)
    le = anyb(d["close"] > ku)
    return le, None, d["close"] < e20, None
_std("B25", 25, "Keltner breakout (long)", "SOLUSDT", T3,
     lambda d: _b25(d)[0], lambda d: _b25(d)[1], lambda d: _b25(d)[2],
     lambda d: _b25(d)[3])


def _b26(d):
    e8, e21, e55 = ema_(d["close"], 8), ema_(d["close"], 21), ema_(d["close"], 55)
    up = (e8 > e21) & (e21 > e55)
    back = anyb((d["close"] > e21) & (d["close"].shift(1) <= e21.shift(1))) & up
    return back, None, xdn(e8, e21), None
_std("B26", 26, "triple-EMA pullback (long)", "HYPEUSDT", T3,
     lambda d: _b26(d)[0], lambda d: _b26(d)[1], lambda d: _b26(d)[2],
     lambda d: _b26(d)[3])


def _b27(d):
    up, dn = _aroon(*_t3(d)[:2], 25)
    le = anyb((up > 70) & (dn < 30))
    return le, None, up < 50, None
_std("B27", 27, "Aroon(25) trend (long)", "SUIUSDT", T3,
     lambda d: _b27(d)[0], lambda d: _b27(d)[1], lambda d: _b27(d)[2],
     lambda d: _b27(d)[3])
S("B28", 28, "LinReg slope trend (NVDA)", "NVDAUSDT", T3, no_data="no NVDA series on disk")


def _b29(d):
    k = _kama(d["close"], 10)
    le = anyb((d["close"] > k) & (k > k.shift(1)))
    se = anyb((d["close"] < k) & (k < k.shift(1)))
    return le, se, anyb(d["close"] < k), anyb(d["close"] > k)
_std("B29", 29, "KAMA(10,2,30) trend", "BTCUSDT", T3,
     lambda d: _b29(d)[0], lambda d: _b29(d)[1], lambda d: _b29(d)[2],
     lambda d: _b29(d)[3])


def _b30(d):
    hh55, _ = don_(d["high"], d["low"], 55)
    _, ll20 = don_(d["high"], d["low"], 20)
    le = d["close"] > hh55
    se = d["close"] < ll20
    return le, se, d["close"] < ll20, d["close"] > hh55
_std("B30", 30, "Turtle 55/20 breakout", "JUPUSDT", T3,
     lambda d: _b30(d)[0], lambda d: _b30(d)[1], lambda d: _b30(d)[2],
     lambda d: _b30(d)[3])
print("pack100_strats: part 1 loaded")
