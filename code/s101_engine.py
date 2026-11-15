"""s101_engine.py — adapter engine for the STRATEGIES 101-150 pack (2026-11-13).

Source of record: code/prompts_101_150.txt (byte-identical attachment,
sha ba1b3491…). Pre-registration: results/s101_pre_registration.md (triage:
37 cells run, 13 NO-DATA skips declared). Execution core: the audited `Book`
of code/p100_screen_engine.py (next-open fills, stop-first intrabar, gap
fills at the open, funding at real settlements, end-of-data force close,
accounting invariant) + `book_metrics` (the screen battery fields).

DECLARED READINGS (every ambiguity resolved conservatively and identically
across cells):
  * signal on close, entry next open (pack rule #1 = repo rule);
  * stop-first ties, gap-through stop fills at the open (pack rule #2);
  * costs: repo uniform 5 bps fee + 0.5 bps slip per side = 11 bps RT (the
    pack's per-symbol schedule of 10-18 bps brackets it; deviation declared);
  * risk 0.5% equity/trade, no martingale (pack rule #4); daily counters:
    max 3 losing trades per UTC day, max 6 trades per day on 1m/3m books
    (pack rule #5), evaluated causally from the closed ledger; flat-exit
    signals (side 0) bypass the counters (exiting is not a new trade);
  * funding charged at real settlements for the seven perps; NVDA/SPCX have
    no funding file -> not charged, declared;
  * no trailing stop anywhere (pack rule #6);
  * IS/OOS = 70/30 chronological, no purge (pack rule #17);
  * "structure/trend up" = close above the 50-EMA of that timeframe; ADX =
    Wilder 14; fractals = 2 bars each side, confirmed 2 bars later;
  * ATR = Wilder 14; ATR percentile = rank inside the trailing 500 bars;
  * VWAP = UTC-day anchored; prior day = previous UTC calendar day;
  * round numbers (123) = integer dollar levels; NVDA/SPCX "ET" clocks use
    America/New_York on the perp's 24/7 tape (declared);
  * dollar bars (133): $ threshold = 20x the median 1m dollar volume of the
    first 1,000 bars; Renko (134): brick = 0.5x the median 5m ATR of the
    first 2,000 bars (fixed); range bars (135): 0.3x of the same on the 1m
    tape (fixed);
  * pairs (117/118): two-leg dollar-neutral ledger (50% gross per leg), per
    leg 11 bps RT, funding both legs at settlements, z over 200 log-ratio
    bars, cointegration = ADF(1) t-stat of the OLS residual < -2.86
    (declared approximation), half-life = -ln2/ln(phi).
The pack's rule #18 (OOS n < 200 => "fragile") is a REPORT label; the gates
are the repo's screen battery. REGLA 1: one cell = one verdict.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from p100_screen_engine import (  # noqa: E402
    Book, book_metrics, bootstrap_r, load_klines, funding_events)

ENGINE_VERSION = "s101-1"
INIT = 10_000.0
FEE = 0.0005
SLIP = 0.0005
RISK = 0.005
MAXLEV = 3.0
COST_RT_BPS = 11.0


def _atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().values


def _ema(a, n):
    return pd.Series(a).ewm(span=n, adjust=False, min_periods=n).mean().values


def _roll_max(a, w):
    return pd.Series(a).rolling(w).max().values


def _roll_min(a, w):
    return pd.Series(a).rolling(w).min().values


def _roll_mean(a, w):
    return pd.Series(a).rolling(w, min_periods=w).mean().values


def _roll_std(a, w):
    return pd.Series(a).rolling(w, min_periods=w).std(ddof=0).values


def _atr_pctile(atr, look=500):
    out = np.full(len(atr), 50.0)
    for i in range(50, len(atr)):
        w = atr[max(0, i - look):i + 1]
        out[i] = 100.0 * float((w <= atr[i]).mean())
    return out


def _fractals(h, l):
    n = len(h)
    hi_ev = np.full(n, np.nan)
    lo_ev = np.full(n, np.nan)
    for k in range(2, n - 2):
        if h[k] > h[k - 1] and h[k] > h[k - 2] and h[k] > h[k + 1] and h[k] > h[k + 2]:
            hi_ev[k + 2] = h[k]
        if l[k] < l[k - 1] and l[k] < l[k - 2] and l[k] < l[k + 1] and l[k] < l[k + 2]:
            lo_ev[k + 2] = l[k]
    return pd.Series(hi_ev).ffill().values, pd.Series(lo_ev).ffill().values


def _day_id(ms):
    return (ms // 86_400_000).astype(int)


def _day_anchors(ms, h, l, o):
    d = _day_id(ms)
    pdh = np.full(len(ms), np.nan)
    pdl = np.full(len(ms), np.nan)
    do_ = np.full(len(ms), np.nan)
    dh, dl, first = {}, {}, {}
    cur = -1
    for i in range(len(ms)):
        dd = d[i]
        if dd != cur:
            pdh[i] = dh.get(dd - 1, np.nan)
            pdl[i] = dl.get(dd - 1, np.nan)
            dh[dd] = -np.inf
            dl[dd] = np.inf
            cur = dd
        else:
            pdh[i] = dh.get(dd - 1, np.nan)
            pdl[i] = dl.get(dd - 1, np.nan)
        if dd not in first:
            first[dd] = o[i]
        do_[i] = first[dd]
        dh[dd] = max(dh[dd], h[i])
        dl[dd] = min(dl[dd], l[i])
    return pdh, pdl, do_


def _vwap_day(ms, h, l, c, v):
    d = _day_id(ms)
    typ = (h + l + c) / 3.0
    pv = typ * v
    out = np.full(len(ms), np.nan)
    cv = cp = 0.0
    cur = None
    for i in range(len(ms)):
        if d[i] != cur:
            cur, cv, cp = d[i], 0.0, 0.0
        cv += v[i]
        cp += pv[i]
        out[i] = cp / cv if cv > 0 else np.nan
    return out


def _adx(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    up = h - np.r_[h[0], h[:-1]]
    dn = np.r_[l[0], l[:-1]] - l
    up = np.where((up > dn) & (up > 0), up, 0.0)
    dn = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr_ = pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values
    pup = pd.Series(up).ewm(alpha=1 / n, adjust=False).mean().values
    pdn = pd.Series(dn).ewm(alpha=1 / n, adjust=False).mean().values
    dx = 100.0 * np.abs(pup - pdn) / np.maximum(pup + pdn, 1e-12)
    return pd.Series(dx).ewm(alpha=1 / n, adjust=False).mean().values


def _resample(df, rule):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last",
           "volume": "sum"}
    if "delta" in df:
        agg["delta"] = "sum"
    g = df.set_index("timestamp").resample(rule, label="left", closed="left").agg(agg)
    cnt = df.set_index("timestamp")["close"].resample(
        rule, label="left", closed="left").count()
    ok = cnt.reindex(g.index).values == cnt.mode().iloc[0]
    return g[ok].dropna().reset_index()


def _dollar_bars(df, mult=20.0, warm=1000):
    px = df["close"].values
    vol = df["volume"].values
    dlt = df["delta"].values
    ts = df["timestamp"].values
    thr = float(np.median(px[:warm] * vol[:warm])) * mult
    rows = []
    acc = 0.0
    o = h = l = None
    tv = 0.0
    td = 0.0
    t0 = None
    for i in range(len(df)):
        if o is None:
            o, h, l, t0 = px[i], px[i], px[i], ts[i]
        if px[i] > h:
            h = px[i]
        if px[i] < l:
            l = px[i]
        tv += vol[i]
        td += dlt[i]
        acc += px[i] * vol[i]
        if acc >= thr:
            rows.append((t0, o, h, l, px[i], tv, td))
            o = None
            acc = tv = td = 0.0
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low",
                                       "close", "volume", "delta"])


def _renko(df, brick):
    px = df["close"].values
    ts = df["timestamp"].values
    rows = []
    last = px[0]
    t_last = ts[0]
    color_prev = 0
    run = 0
    for i in range(len(px)):
        p = px[i]
        while abs(p - last) >= brick:
            step = brick if p > last else -brick
            new = last + step
            color = 1 if step > 0 else -1
            run = run + 1 if color == color_prev else 1
            color_prev = color
            rows.append((t_last, new - step, max(new, new - step),
                         min(new, new - step), new, 0.0, color, run))
            t_last = ts[i]
            last = new
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low",
                                       "close", "volume", "color", "run"])


def _range_bars(df, brick):
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    v = df["volume"].values
    ts = df["timestamp"].values
    rows = []
    oo = oh = ol = None
    t0 = None
    for i in range(len(df)):
        if oo is None:
            oo, oh, ol, t0 = o[i], h[i], l[i], ts[i]
        if h[i] > oh:
            oh = h[i]
        if l[i] < ol:
            ol = l[i]
        if oh - ol >= brick:
            rows.append((t0, oo, oh, ol, c[i], v[i]))
            oo = None
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low",
                                       "close", "volume"])


def _half_life(spread):
    s = np.asarray(spread, float)
    d = s[1:] - s[:-1]
    lag = s[:-1]
    denom = float(np.dot(lag - lag.mean(), lag - lag.mean()))
    if denom <= 0:
        return np.inf
    phi = float(np.dot(lag, d) / denom)
    phi = min(max(phi, 0.01), 0.99)
    return -np.log(2.0) / np.log(phi)


def _adf_t(resid):
    r = np.asarray(resid, float)
    d = r[1:] - r[:-1]
    lag = r[:-1]
    lag_c = lag - lag.mean()
    denom = float(np.dot(lag_c, lag_c))
    if denom <= 0:
        return 0.0
    b = float(np.dot(lag_c, d) / denom)
    e = d - b * lag_c
    se = float(np.sqrt((e * e).sum() / max(len(e) - 1, 1) / denom))
    return b / se if se > 0 else 0.0


def _make_sig(idn, main, aux, symbol):
    """One FRESH signal machine per pass (FULL / OOS keep separate state).
    Every rolling array is precomputed here: closures are O(1) per bar.
    side 0 = flat-exit instruction (bypasses the daily counters)."""
    o = main["open"].values
    h = main["high"].values
    l = main["low"].values
    c = main["close"].values
    v = main["volume"].values
    ms = main["bar_ms"]
    n = len(o)
    atr_ = _atr(h, l, c)
    st = {}

    def next_open(j):
        return float(o[j + 1]) if j + 1 < n else float(c[j])

    if idn == 101:
        H = aux["BTCUSDT_1h"]
        _, ll1 = _fractals(H["high"].values, H["low"].values)
        hc1 = H["close"].values
        cms1 = H["close_ms"]
        sh5, _ = _fractals(h, l)
        def sig(j):
            if j < 25:
                return None
            k = int(np.searchsorted(cms1, ms[j], "right")) - 1
            up = k >= 0 and np.isfinite(ll1[k]) and hc1[k] > ll1[k]
            brk = st.get("brk")
            if not up:
                st["brk"] = None
                return None
            if brk is None:
                if np.isfinite(sh5[j]) and c[j] > sh5[j]:
                    st["brk"] = dict(lvl=float(sh5[j]), idx=j)
                return None
            if c[j] < brk["lvl"]:
                st["brk"] = None
                return None
            if l[j] <= brk["lvl"]:
                stop = float(np.min(l[brk["idx"]:j + 1])) - 1e-9
                ep = next_open(j)
                risk = ep - stop
                st["brk"] = None
                if risk > 0:
                    return dict(side=1, stop_px=stop, tp_px=ep + 2.0 * risk)
            return None
        return sig

    if idn == 102:
        H = aux["BTCUSDT_1h"]
        adx1 = _adx(H["high"].values, H["low"].values, H["close"].values)
        cms1 = H["close_ms"]
        p20l = _roll_min(l, 20)
        p20h = _roll_max(h, 20)
        def sig(j):
            if j < 25:
                return None
            k = int(np.searchsorted(cms1, ms[j], "right")) - 1
            if k < 0 or adx1[k] >= 20.0:
                return None
            if l[j] < p20l[j - 1] * (1 - 0.0015) and c[j] > p20l[j - 1]:
                ep = next_open(j)
                stop = float(l[j]) - 1e-9
                if stop < ep:
                    tp = float(p20h[j - 1]) if p20h[j - 1] > ep else None
                    return dict(side=1, stop_px=stop, tp_px=tp)
            return None
        return sig

    if idn == 103:
        p20h = _roll_max(h, 20)
        p20l = _roll_min(l, 20)
        vavg = _roll_mean(v, 20)
        def sig(j):
            if j < 25:
                return None
            brk = st.get("brk")
            if brk is None:
                if h[j] > p20h[j - 1]:
                    st["brk"] = dict(hi=float(h[j]), age=0,
                                     p20h=float(p20h[j - 1]),
                                     p20l=float(p20l[j - 1]),
                                     vavg=float(vavg[j - 1]))
                return None
            brk["age"] += 1
            if brk["age"] > 2 or c[j] >= brk["p20h"]:
                st["brk"] = None
                return None
            if v[j] > 1.5 * brk["vavg"]:
                ep = next_open(j)
                stop = brk["hi"] + 1e-9
                tp = brk["p20l"] if brk["p20l"] < ep else None
                st["brk"] = None
                if stop > ep:
                    return dict(side=-1, stop_px=stop, tp_px=tp, max_hold=10)
            return None
        return sig

    if idn == 104:
        hrs = (ms // 3_600_000) % 24
        d_id = _day_id(ms)
        rhi = np.full(n, np.nan)
        rlo = np.full(n, np.nan)
        for dd in np.unique(d_id):
            base = dd * 86_400_000
            w = np.flatnonzero((ms >= base) & (ms < base + 6 * 3_600_000))
            e = np.flatnonzero((d_id == dd) & (hrs >= 7) & (hrs < 12))
            if len(w) >= 5 and len(e):
                rhi[e] = np.max(h[w])
                rlo[e] = np.min(l[w])
        def sig(j):
            if j < 10:
                return None
            if hrs[j] >= 20:
                return dict(side=0)
            if not np.isfinite(rhi[j]):
                return None
            a = st.get("ar")
            if a is None:
                if c[j] > rhi[j]:
                    st["ar"] = dict(side=1, lvl=float(rhi[j]), opp=float(rlo[j]))
                elif c[j] < rlo[j]:
                    st["ar"] = dict(side=-1, lvl=float(rlo[j]), opp=float(rhi[j]))
                return None
            side, lvl, opp = a["side"], a["lvl"], a["opp"]
            ep = next_open(j)
            if side == 1 and l[j] <= lvl:
                risk = max(ep - opp, 1e-9)
                st["ar"] = None
                return dict(side=1, stop_px=opp - 1e-9, tp_px=ep + 1.5 * risk)
            if side == -1 and h[j] >= lvl:
                risk = max(lvl - ep, 1e-9)
                st["ar"] = None
                return dict(side=-1, stop_px=opp + 1e-9, tp_px=ep - 1.5 * risk)
            return None
        return sig

    if idn == 105:
        H = aux["BTCUSDT_1h"]
        ema50h = _ema(H["close"].values, 50)
        cms1 = H["close_ms"]
        vw = _vwap_day(ms, h, l, c, v)
        def sig(j):
            if j < 60:
                return None
            k = int(np.searchsorted(cms1, ms[j], "right")) - 1
            if k < 0 or not np.isfinite(ema50h[k]) or H["close"].values[k] <= ema50h[k]:
                return None
            if not np.isfinite(vw[j]):
                return None
            if l[j] <= vw[j] + 0.25 * atr_[j] and c[j] >= vw[j]:
                ep = next_open(j)
                return dict(side=1, stop_px=ep - atr_[j], tp_px=ep + 2 * atr_[j])
            return None
        return sig

    if idn == 106:
        pct = _atr_pctile(atr_, 500)
        def sig(j):
            if j < 500 or pct[j] >= 40:
                return None
            d = _day_id(ms)[j]
            if st.get("vaday") != d:
                st["vaday"] = d
                base = d * 86_400_000
                w = np.flatnonzero((ms >= base - 86_400_000) & (ms < base))
                if len(w) < 50:
                    st["va"] = None
                else:
                    lo_, hi_ = float(np.min(l[w])), float(np.max(h[w]))
                    if hi_ > lo_:
                        bins = np.clip(((c[w] - lo_) / (hi_ - lo_) * 23).astype(int), 0, 23)
                        volb = np.bincount(bins, weights=v[w], minlength=24)
                        poc_i = int(np.argmax(volb))
                        tot = float(volb.sum())
                        order = np.argsort(-volb)
                        cum = 0.0
                        keep = set()
                        for bi in order:
                            keep.add(int(bi))
                            cum += volb[bi]
                            if cum >= 0.7 * tot:
                                break
                        lo_bin = min(keep) / 23.0 * (hi_ - lo_) + lo_
                        poc = (poc_i + 0.5) / 23.0 * (hi_ - lo_) + lo_
                        st["va"] = (lo_bin, poc)
                    else:
                        st["va"] = None
            va = st.get("va")
            if va is None:
                return None
            vlo, poc = va
            if l[j] <= vlo + 0.1 * atr_[j] and c[j] >= vlo:
                ep = next_open(j)
                stop = vlo - 0.5 * atr_[j] - 1e-9
                if stop < ep and poc > ep:
                    return dict(side=1, stop_px=stop, tp_px=poc)
            return None
        return sig

    if idn == 107:
        A = aux["BTCUSDT_15m"]
        ac = A["close"].values
        aems = _ema(ac, 50)
        acms = A["close_ms"]
        p20h = _roll_max(h, 20)
        def sig(j):
            if j < 30:
                return None
            k = int(np.searchsorted(acms, ms[j], "right")) - 1
            if k < 0 or not np.isfinite(aems[k]) or ac[k] <= aems[k]:
                return None
            imp = st.get("imp")
            if imp is None:
                if c[j] - o[j] >= 1.5 * atr_[j] and h[j] > p20h[j - 1]:
                    dn = None
                    for b in range(j - 1, max(j - 12, -1), -1):
                        if c[b] < o[b]:
                            dn = b
                            break
                    if dn is not None:
                        lo_, hi_ = float(l[dn]), float(h[dn])
                        st["imp"] = dict(lo=lo_, mid=(lo_ + hi_) / 2, born=j)
                    else:
                        st["imp"] = dict(born=j)
                return None
            if j - imp.get("born", j) > 24:
                st["imp"] = None
                return None
            if "mid" in imp and l[j] <= imp["mid"] and c[j] > imp["lo"]:
                ep = next_open(j)
                stop = imp["lo"] - 1e-9
                risk = max(ep - stop, 1e-9)
                st["imp"] = None
                return dict(side=1, stop_px=stop, tp_px=ep + 2 * risk)
            return None
        return sig

    if idn == 108:
        ema50 = _ema(c, 50)
        fvgs = []
        def sig(j):
            if j < 30 or c[j] <= ema50[j]:
                return None
            if l[j] > h[j - 2]:
                fvgs.append(dict(top=float(l[j]), bot=float(h[j - 2]), born=j))
            for g in fvgs[:]:
                if j - g["born"] > 40:
                    fvgs.remove(g)
                    continue
                if l[j] <= (g["top"] + g["bot"]) / 2 and c[j] > g["bot"]:
                    ep = next_open(j)
                    stop = g["bot"] - 1e-9
                    risk = max(ep - stop, 1e-9)
                    fvgs.remove(g)
                    return dict(side=1, stop_px=stop, tp_px=ep + 2 * risk, max_hold=20)
            return None
        return sig

    if idn in (109, 110):
        delta = main["delta"].values
        cvd = np.cumsum(delta)
        M = 30 if idn == 109 else 20
        sh, _ = _fractals(h, l)
        vw = _vwap_day(ms, h, l, c, v)
        pmin = _roll_min(l, M)
        def sig(j):
            if j < M + 10:
                return None
            if l[j] >= pmin[j - 1]:
                return None
            w = np.arange(j - M, j)
            k_prev = int(w[int(np.argmin(l[w]))])
            if cvd[j] <= cvd[k_prev]:
                return None
            if idn == 109:
                if np.isfinite(sh[j]) and c[j] > sh[j]:
                    ep = next_open(j)
                    stop = float(min(l[j], l[k_prev])) - 1e-9
                    risk = max(ep - stop, 1e-9)
                    return dict(side=1, stop_px=stop, tp_px=ep + 1.5 * risk)
            else:
                if c[j] >= l[j] + 0.66 * (h[j] - l[j]):
                    ep = next_open(j)
                    stop = float(min(l[j], l[k_prev])) - 1e-9
                    risk = max(ep - stop, 1e-9)
                    tp = vw[j] if (np.isfinite(vw[j]) and vw[j] > ep) else ep + 1.5 * risk
                    return dict(side=1, stop_px=stop, tp_px=tp)
            return None
        return sig

    if idn == 112:
        rate, isf = aux["rate"], aux["is_fund"]
        vw = _vwap_day(ms, h, l, c, v)
        rates = []
        def sig(j):
            if j < 100:
                return None
            if isf[j]:
                rates.append(float(rate[j]))
                if len(rates) > 90:
                    del rates[:-90]
            if not isf[j] or len(rates) < 50:
                return None
            if float(rate[j]) >= float(np.percentile(rates, 95)) \
                    and np.isfinite(vw[j]) and c[j] < vw[j]:
                ep = next_open(j)
                return dict(side=-1, stop_px=ep + atr_[j], tp_px=float(vw[j]))
            return None
        return sig

    if idn == 115:
        B = aux["BTCUSDT_15m"]
        bc = B["close"].values
        bms = B["bar_ms"]
        ki = np.clip(np.searchsorted(bms, ms, "right") - 1, 0, len(bc) - 1)
        bp20h = _roll_max(B["high"].values, 20)
        ema9 = _ema(c, 9)
        ratio = c / bc[ki]
        rvw = _vwap_day(ms, ratio, ratio, ratio, np.ones(n))
        def sig(j):
            if j < 30:
                return None
            bk = int(ki[j])
            if bk >= 1 and bc[bk] > bp20h[bk - 1]:
                st["armed_until"] = j + 8
            if j > st.get("armed_until", -1):
                return None
            if not (np.isfinite(rvw[j]) and ratio[j] > rvw[j]):
                return None
            if np.isfinite(ema9[j]) and l[j] <= ema9[j]:
                ep = next_open(j)
                st["armed_until"] = -1
                return dict(side=1, stop_px=ep - 1.5 * atr_[j],
                            tp_px=ep + 2.5 * atr_[j])
            return None
        return sig

    if idn == 116:
        B = aux["BTCUSDT_5m"]
        bc = B["close"].values
        bms = B["bar_ms"]
        ki = np.clip(np.searchsorted(bms, ms, "right") - 1, 0, len(bc) - 1)
        ratio = c / bc[ki]
        rs20 = _roll_max(ratio, 20)
        vw = _vwap_day(ms, h, l, c, v)
        p10h = _roll_max(h, 10)
        def sig(j):
            if j < 30:
                return None
            if not (np.isfinite(rs20[j - 1]) and ratio[j] > rs20[j - 1]):
                return None
            if not (np.isfinite(vw[j]) and c[j] > vw[j]):
                return None
            if np.isfinite(p10h[j - 1]) and c[j] > p10h[j - 1]:
                ep = next_open(j)
                return dict(side=1, stop_px=ep - 1.5 * atr_[j], tp_px=ep + 3 * atr_[j])
            return None
        return sig

    if idn == 119:
        B = aux["BTCUSDT_1m"]
        bc = B["close"].values
        bms = B["bar_ms"]
        ki = np.clip(np.searchsorted(bms, ms, "right") - 1, 0, len(bc) - 1)
        r_sol = np.r_[0.0, np.diff(np.log(c))]
        r_btc = np.r_[0.0, np.diff(np.log(bc))][ki]
        corr = pd.Series(r_sol).rolling(60, min_periods=60).corr(
            pd.Series(r_btc)).values
        sh, _ = _fractals(h, l)
        def sig(j):
            if j < 80 or not np.isfinite(corr[j]) or corr[j] >= 0.2:
                return None
            if np.isfinite(sh[j]) and c[j] > sh[j]:
                ep = next_open(j)
                stop = float(l[j]) - atr_[j]
                if stop < ep:
                    return dict(side=1, stop_px=stop, tp_px=ep + 2 * (ep - stop))
            return None
        return sig

    if idn == 120:
        rng = h - l
        pct = _atr_pctile(atr_, 500)
        vavg = _roll_mean(v, 20)
        def sig(j):
            if j < 30 or pct[j] >= 30:
                return None
            w = rng[j - 7:j - 1]
            if len(w) == 6 and rng[j - 1] > w.min():
                return None
            if not np.isfinite(vavg[j - 1]) or v[j] <= 1.5 * vavg[j - 1]:
                return None
            nr_hi, nr_lo = float(h[j - 1]), float(l[j - 1])
            ep = next_open(j)
            if c[j] > nr_hi and nr_lo < ep:
                return dict(side=1, stop_px=nr_lo - 1e-9, tp_px=ep + 2 * (ep - nr_lo))
            if c[j] < nr_lo and nr_hi > ep:
                return dict(side=-1, stop_px=nr_hi + 1e-9, tp_px=ep - 2 * (nr_hi - ep))
            return None
        return sig

    if idn == 121:
        def sig(j):
            if j < 25:
                return None
            if abs(c[j - 2] - o[j - 2]) < 1.5 * atr_[j - 2]:
                return None
            if not (h[j - 1] <= h[j - 2] and l[j - 1] >= l[j - 2]):
                return None
            ib_hi, ib_lo = float(h[j - 1]), float(l[j - 1])
            side = 1 if c[j - 2] > o[j - 2] else -1
            ep = next_open(j)
            if side == 1 and c[j] > ib_hi and ib_lo < ep:
                return dict(side=1, stop_px=ib_lo - 1e-9, tp_px=ep + 2 * (ep - ib_lo))
            if side == -1 and c[j] < ib_lo and ib_hi > ep:
                return dict(side=-1, stop_px=ib_hi + 1e-9, tp_px=ep - 2 * (ib_hi - ep))
            return None
        return sig

    if idn == 122:
        pdh, pdl, _ = _day_anchors(ms, h, l, o)
        def sig(j):
            if j < 30 or not np.isfinite(pdl[j]):
                return None
            if not (h[j] > h[j - 1] and l[j] < l[j - 1]):
                return None
            ep = next_open(j)
            if l[j] < pdl[j] and c[j] > pdl[j] and float(l[j]) < ep:
                return dict(side=1, stop_px=float(l[j]) - 1e-9,
                            tp_px=ep + 1.5 * (ep - float(l[j])))
            if h[j] > pdh[j] and c[j] < pdh[j] and float(h[j]) > ep:
                return dict(side=-1, stop_px=float(h[j]) + 1e-9,
                            tp_px=ep - 1.5 * (float(h[j]) - ep))
            return None
        return sig

    if idn == 123:
        pct = _atr_pctile(atr_, 500)
        def sig(j):
            if j < 30 or pct[j] <= 50:
                return None
            lvl = float(round(c[j]))
            if l[j] <= lvl * (1 - 0.002) and c[j] > lvl:
                ep = next_open(j)
                stop = float(l[j]) - 1e-9
                if stop < ep:
                    return dict(side=1, stop_px=stop, tp_px=ep + 2 * (ep - stop))
            return None
        return sig

    if idn == 124:
        pdh, pdl, pdo = _day_anchors(ms, h, l, o)
        def sig(j):
            if j < 30 or not np.isfinite(pdh[j]) or not np.isfinite(pdo[j]):
                return None
            if h[j] > pdh[j] and c[j] < pdh[j]:
                ep = next_open(j)
                stop = float(h[j]) + 1e-9
                tp = float(pdo[j]) if pdo[j] < ep else None
                if stop > ep:
                    return dict(side=-1, stop_px=stop, tp_px=tp)
            return None
        return sig

    if idn == 125:
        dti = pd.DatetimeIndex(pd.to_datetime(ms, unit="ms", utc=True))
        iso = dti.isocalendar()
        wk = iso["year"].values * 100 + iso["week"].values
        wo = np.full(n, np.nan)
        first = {}
        for i in range(n):
            k = wk[i]
            if k not in first:
                first[k] = o[i]
            wo[i] = first[k]
        dow = dti.dayofweek.values
        def sig(j):
            if j < 30 or dow[j] > 1:
                return None
            if c[j] <= wo[j]:
                return None
            if l[j] <= wo[j] + 0.2 * atr_[j] and c[j] > wo[j]:
                ep = next_open(j)
                stop = float(l[j]) - 1e-9
                if stop < ep:
                    return dict(side=1, stop_px=stop, tp_px=ep + 2 * (ep - stop))
            return None
        return sig

    if idn == 126:
        _, _, do_ = _day_anchors(ms, h, l, o)
        d_id = _day_id(ms)
        dh_sofar = np.full(n, np.nan)
        cur = -1
        mx = -np.inf
        for i in range(n):
            if d_id[i] != cur:
                cur, mx = d_id[i], -np.inf
            if h[i] > mx:
                mx = h[i]
            dh_sofar[i] = mx
        def sig(j):
            if j < 10 or not np.isfinite(do_[j]):
                return None
            if l[j] < do_[j] and c[j] > do_[j]:
                ep = next_open(j)
                stop = float(l[j]) - 1e-9
                if stop >= ep:
                    return None
                risk = ep - stop
                tp2 = ep + 2 * risk
                tp = min(dh_sofar[j], tp2) if dh_sofar[j] > ep else tp2
                return dict(side=1, stop_px=stop, tp_px=tp, max_hold=15)
            return None
        return sig

    if idn == 127:
        pct = _atr_pctile(atr_, 500)
        p20h = _roll_max(h, 20)
        p20l = _roll_min(l, 20)
        def sig(j):
            if j < 60:
                return None
            ep = next_open(j)
            if pct[j] > 70 and np.isfinite(p20h[j - 1]) and c[j] > p20h[j - 1]:
                stop = ep - 1.5 * atr_[j]
                return dict(side=1, stop_px=stop, tp_px=ep + 2 * 1.5 * atr_[j])
            if pct[j] < 30 and np.isfinite(p20h[j - 1]) and h[j] >= p20h[j - 1] \
                    and np.isfinite(p20l[j - 1]):
                mid = (p20h[j - 1] + p20l[j - 1]) / 2
                stop = p20h[j - 1] + atr_[j]
                if mid < ep and stop > ep:
                    return dict(side=-1, stop_px=stop, tp_px=mid)
            return None
        return sig

    if idn == 128:
        body_lo = np.minimum(o, c)
        def sig(j):
            if j < 30:
                return None
            wick = body_lo[j] - l[j]
            rng = h[j] - l[j]
            if wick < 2 * atr_[j] or rng <= 0 or c[j] >= l[j] + 0.66 * rng:
                return None
            ep = next_open(j)
            stop = float(l[j]) - 1e-9
            tp = l[j] + 0.5 * (body_lo[j] - l[j])
            if stop < ep and tp > ep:
                return dict(side=1, stop_px=stop, tp_px=tp)
            return None
        return sig

    if idn == 129:
        tmin = (ms // 60_000) % 1440
        p20h = _roll_max(h, 20)
        vavg = _roll_mean(v, 20)
        def sig(j):
            if j < 25:
                return None
            if not (810 <= tmin[j] < 960):
                return None
            if np.isfinite(p20h[j - 1]) and c[j] > p20h[j - 1] \
                    and v[j] > 1.5 * vavg[j - 1]:
                ep = next_open(j)
                return dict(side=1, stop_px=ep - atr_[j], tp_px=ep + 2 * atr_[j])
            return None
        return sig

    if idn == 130:
        dow = pd.DatetimeIndex(pd.to_datetime(ms, unit="ms", utc=True)).dayofweek.values
        vw = _vwap_day(ms, h, l, c, v)
        p20h = _roll_max(h, 20)
        p20l = _roll_min(l, 20)
        def sig(j):
            if j < 30 or dow[j] < 5:
                return None
            if not np.isfinite(vw[j]):
                return None
            ep = next_open(j)
            if np.isfinite(p20h[j - 1]) and h[j] >= p20h[j - 1] and vw[j] < ep:
                return dict(side=-1, stop_px=p20h[j - 1] + atr_[j], tp_px=float(vw[j]))
            if np.isfinite(p20l[j - 1]) and l[j] <= p20l[j - 1] and vw[j] > ep:
                return dict(side=1, stop_px=p20l[j - 1] - atr_[j], tp_px=float(vw[j]))
            return None
        return sig

    if idn == 131:
        sess_ms = (ms // 3_600_000) * 3_600_000
        rhi = np.full(n, np.nan)
        rlo = np.full(n, np.nan)
        for j in range(n):
            if (ms[j] % 3_600_000) == 0 and ((ms[j] // 3_600_000) % 8) == 0:
                w = np.flatnonzero((ms >= sess_ms[j]) & (ms < sess_ms[j] + 900_000))
                if len(w) >= 3:
                    rhi[w] = np.max(h[w])
                    rlo[w] = np.min(l[w])
        rhi = pd.Series(rhi).ffill().values
        rlo = pd.Series(rlo).ffill().values
        def sig(j):
            if j < 15:
                return None
            if (ms[j] % 3_600_000) == 0 and ((ms[j] // 3_600_000) % 8) == 0:
                st["sess"] = sess_ms[j]  # arm at each session's first bar
            if ms[j] - sess_ms[j] >= 4 * 3_600_000:
                if st.get("sess") == sess_ms[j]:
                    st["sess"] = None
                    return dict(side=0)
                return None
            if st.get("sess") != sess_ms[j]:
                return None
            key = ("state", sess_ms[j])
            a = st.get(key, {})
            side = a.get("side")
            if side is None:
                if c[j] > rhi[j]:
                    a["side"] = 1
                    st[key] = a
                elif c[j] < rlo[j]:
                    a["side"] = -1
                    st[key] = a
                return None
            ep = next_open(j)
            if side == 1 and l[j] <= rhi[j]:
                risk = max(ep - rlo[j], 1e-9)
                st[key] = {}
                return dict(side=1, stop_px=rlo[j] - 1e-9, tp_px=ep + 1.5 * risk)
            if side == -1 and h[j] >= rlo[j]:
                risk = max(rhi[j] - ep, 1e-9)
                st[key] = {}
                return dict(side=-1, stop_px=rhi[j] + 1e-9, tp_px=ep - 1.5 * risk)
            return None
        return sig

    if idn == 133:
        dstd = _roll_std(main["delta"].values, 200)
        dmean = _roll_mean(main["delta"].values, 200)
        sh, _ = _fractals(h, l)
        def sig(j):
            if j < 220 or not (np.isfinite(dmean[j]) and dstd[j] > 0):
                return None
            if main["delta"].values[j] >= dmean[j] + 2 * dstd[j] \
                    and np.isfinite(sh[j]) and c[j] > sh[j]:
                ep = next_open(j)
                return dict(side=1, stop_px=ep - atr_[j], tp_px=ep + 2 * atr_[j])
            return None
        return sig

    if idn == 134:
        color = main["color"].values
        run = main["run"].values
        brick = float(aux["brick"])
        def sig(j):
            if j < 8:
                return None
            ep = next_open(j)
            if color[j] == 1 and run[j] >= 2 and color[j - 2] == -1:
                return dict(side=1, stop_px=float(c[j]) - 2 * brick, tp_px=ep + 4 * brick)
            if color[j] == -1 and run[j] >= 2 and color[j - 2] == 1:
                return dict(side=-1, stop_px=float(c[j]) + 2 * brick, tp_px=ep - 4 * brick)
            return None
        return sig

    if idn == 135:
        p5h = _roll_max(h, 5)
        p5l = _roll_min(l, 5)
        def sig(j):
            if j < 10:
                return None
            ep = next_open(j)
            if np.isfinite(p5h[j - 1]) and c[j] > p5h[j - 1] \
                    and np.isfinite(p5l[j - 1]) and p5l[j - 1] < ep:
                return dict(side=1, stop_px=p5l[j - 1] - 1e-9,
                            tp_px=ep + 2 * (ep - p5l[j - 1]))
            if np.isfinite(p5l[j - 1]) and c[j] < p5l[j - 1] \
                    and np.isfinite(p5h[j - 1]) and p5h[j - 1] > ep:
                return dict(side=-1, stop_px=p5h[j - 1] + 1e-9,
                            tp_px=ep - 2 * (p5h[j - 1] - ep))
            return None
        return sig

    if idn == 138:
        p20l = _roll_min(l, 20)
        p20h = _roll_max(h, 20)
        def sig(j):
            if j < 45:
                return None
            sweep = st.get("sweep")
            if sweep is None:
                if l[j] < p20l[j - 1]:
                    st["sweep"] = dict(lo=float(l[j]), hi=float(p20h[j - 1]), at=j)
                return None
            if j - sweep["at"] > 20:
                st["sweep"] = None
                return None
            if l[j] < sweep["lo"]:
                st["sweep"] = dict(lo=float(l[j]), hi=sweep["hi"], at=j)
                return None
            if c[j] > sweep["hi"]:
                ep = next_open(j)
                risk = max(ep - sweep["lo"], 1e-9)
                st["sweep"] = None
                return dict(side=1, stop_px=sweep["lo"] - 1e-9, tp_px=ep + 2 * risk)
            return None
        return sig

    if idn == 139:
        sh, _ = _fractals(h, l)
        def sig(j):
            if j < 30:
                return None
            s = st.get("sfp")
            if s is not None:
                st["sfp"] = None
                if c[j] < c[s["bar"]]:
                    ep = next_open(j)
                    stop = s["hi"] + 1e-9
                    if stop > ep:
                        return dict(side=-1, stop_px=stop,
                                    tp_px=ep - 2 * (stop - ep))
                return None
            if np.isfinite(sh[j - 1]) and h[j] > sh[j - 1] and c[j] < sh[j - 1]:
                st["sfp"] = dict(hi=float(h[j]), bar=j)
            return None
        return sig

    if idn == 140:
        pdh, pdl, _ = _day_anchors(ms, h, l, o)
        def sig(j):
            if j < 30 or not np.isfinite(pdl[j]):
                return None
            if not (c[j - 3] < o[j - 3] and c[j - 2] < o[j - 2] and c[j - 1] < o[j - 1]):
                return None
            if (c[j] > o[j] and o[j] <= min(o[j - 1], c[j - 1])
                    and c[j] >= max(o[j - 1], c[j - 1])):
                pl = float(np.min(l[j - 3:j + 1]))
                if pl <= pdl[j] + 0.1 * atr_[j]:
                    ep = next_open(j)
                    stop = pl - 1e-9
                    if stop < ep:
                        return dict(side=1, stop_px=stop, tp_px=ep + 2 * (ep - stop))
            return None
        return sig

    if idn in (141, 144):
        ny = pd.DatetimeIndex(pd.to_datetime(ms, unit="ms", utc=True)).tz_convert(
            "America/New_York")
        met = ny.hour.values * 60 + ny.minute.values
        pre = (met >= 240) & (met < 570)
        daym = (met >= 570) & (met < 955)
        pw = (met >= 900) & (met < 955)
        flatm = (met >= 955) & (met < 960)
        d_id = _day_id(ms)
        vavg = _roll_mean(v, 20)
        pre_hi = np.full(n, np.nan)
        pre_lo = np.full(n, np.nan)
        for dd in np.unique(d_id):
            w = np.flatnonzero((d_id == dd) & pre)
            e = np.flatnonzero((d_id == dd) & daym)
            if len(w) >= 5 and len(e):
                pre_hi[e] = np.max(h[w])
                pre_lo[e] = np.min(l[w])
        def sig(j):
            if j < 30:
                return None
            if flatm[j]:
                return dict(side=0)
            ep = next_open(j)
            if idn == 141 and daym[j] and np.isfinite(pre_hi[j]):
                if not (np.isfinite(vavg[j - 1]) and v[j] > 1.5 * vavg[j - 1]):
                    return None
                if c[j] > pre_hi[j] and pre_lo[j] < ep:
                    return dict(side=1, stop_px=pre_lo[j] - 1e-9,
                                tp_px=ep + 2 * (ep - pre_lo[j]))
                if c[j] < pre_lo[j] and pre_hi[j] > ep:
                    return dict(side=-1, stop_px=pre_hi[j] + 1e-9,
                                tp_px=ep - 2 * (pre_hi[j] - ep))
                return None
            if idn == 144 and pw[j]:
                w = np.flatnonzero((d_id[:j + 1] == d_id[j]) & daym[:j + 1]
                                   & (met[:j + 1] < 900))
                if len(w) < 10:
                    return None
                if not (np.isfinite(vavg[j - 1]) and v[j] > 1.5 * vavg[j - 1]):
                    return None
                day_hi = float(np.max(h[w]))
                day_lo = float(np.min(l[w]))
                if c[j] > day_hi:
                    return dict(side=1, stop_px=ep - atr_[j], tp_px=ep + 2 * atr_[j])
                if c[j] < day_lo:
                    return dict(side=-1, stop_px=ep + atr_[j], tp_px=ep - 2 * atr_[j])
                return None
            return None
        return sig

    if idn == 150:
        vw = _vwap_day(ms, h, l, c, v)
        _, _, pdo = _day_anchors(ms, h, l, o)
        d_id = _day_id(ms)
        a_lo = np.full(n, np.nan)
        for dd in np.unique(d_id):
            base = dd * 86_400_000
            w = np.flatnonzero((ms >= base) & (ms < base + 900_000))
            if len(w) >= 3:
                a_lo[w] = np.min(l[w])
        a_lo = pd.Series(a_lo).ffill().values
        def sig(j):
            if j < 40 or not np.isfinite(vw[j]) or not np.isfinite(a_lo[j]):
                return None
            if j >= 1 and c[j - 1] <= vw[j - 1] and c[j] > vw[j] \
                    and float(l[j]) <= a_lo[j] + 2 * atr_[j]:
                stop = float(a_lo[j]) - 1e-9
                ep = next_open(j)
                if stop >= ep:
                    return None
                tp_c = float(pdo[j]) if np.isfinite(pdo[j]) else np.inf
                tp = min(vw[j], tp_c) if tp_c > ep else vw[j]
                if tp > ep:
                    return dict(side=1, stop_px=stop, tp_px=float(tp))
            return None
        return sig

    return None


CELLS = {
    101: ("BTCUSDT", "5m", 5), 102: ("BTCUSDT", "15m", 15),
    103: ("BTCUSDT", "1m", 1), 104: ("BTCUSDT", "5m", 5),
    105: ("BTCUSDT", "15m", 15), 106: ("BTCUSDT", "3m", 3),
    107: ("BTCUSDT", "5m", 5), 108: ("BTCUSDT", "3m", 3),
    109: ("ETHUSDT", "1m", 1), 110: ("ETHUSDT", "3m", 3),
    112: ("ETHUSDT", "15m", 15), 115: ("ETHUSDT", "15m", 15),
    116: ("SOLUSDT", "5m", 5), 117: ("SOLUSDT", "15m", 15),
    118: ("SOLUSDT", "3m", 3), 119: ("SOLUSDT", "1m", 1),
    120: ("SOLUSDT", "5m", 5), 121: ("SOLUSDT", "15m", 15),
    122: ("SOLUSDT", "3m", 3), 123: ("HYPEUSDT", "5m", 5),
    124: ("HYPEUSDT", "15m", 15), 125: ("HYPEUSDT", "3m", 3),
    126: ("HYPEUSDT", "1m", 1), 127: ("HYPEUSDT", "15m", 15),
    128: ("HYPEUSDT", "5m", 5), 129: ("SUIUSDT", "1m", 1),
    130: ("SUIUSDT", "3m", 3), 131: ("SUIUSDT", "5m", 5),
    133: ("SUIUSDT", "dbars", 3), 134: ("SUIUSDT", "renko", 5),
    135: ("JUPUSDT", "range", 1), 138: ("JUPUSDT", "15m", 15),
    139: ("JUPUSDT", "3m", 3), 140: ("JUPUSDT", "5m", 5),
    141: ("NVDAUSDT", "5m", 5), 144: ("NVDAUSDT", "5m", 5),
    150: ("SPCXUSDT", "5m", 5),
}

NO_DATA = {
    111: "liquidation tape (~2 months only)",
    113: "open interest (~20 days)",
    114: "no ETH spot series on disk",
    132: "no macro calendar",
    136: "no tick data",
    137: "no order-book data",
    142: "no NVDA 1m series",
    143: "no NVDA 1m series (3m resample needs it)",
    145: "no SMH series",
    146: "no SPCX 1m series",
    147: "no SPY series (trigger symbol)",
    148: "no VIX series",
    149: "no breadth series",
}


def _pick(paths, suffix, want_dir=None):
    out = []
    for p in paths:
        b = os.path.basename(p)
        if b.endswith(suffix + ".csv"):
            d = os.path.basename(os.path.dirname(p))
            if want_dir is None or want_dir in d:
                out.append(p)
    return out


def _frame_from(path):
    # explicit-path loader: p100's load_klines resolves via its own TF_DIRS,
    # which does not carry every timeframe this pack needs (1m etc.)
    df = pd.read_csv(path)
    df.columns = [str(cc).strip().lower() for cc in df.columns]
    ts_col = "open_ts" if "open_ts" in df.columns else "timestamp"
    df["timestamp"] = pd.to_datetime(df[ts_col], unit="ms", utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df.reset_index(drop=True)


def build_frame(idn, paths):
    sym = CELLS[idn][0]
    aux = {}
    if idn == 101:
        m = _frame_from(_pick(paths, "5m")[0])
        h1 = _frame_from(_pick(paths, "1h")[0])
        h1["bar_ms"] = (h1["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
                        .to_numpy().astype("datetime64[ms]").astype("int64"))
        h1["close_ms"] = h1["bar_ms"] + 3_600_000
        aux["BTCUSDT_1h"] = h1
        return m, aux
    if idn in (102, 105, 107):
        tfm = "15m" if idn in (102, 105) else "5m"
        m = _frame_from(_pick(paths, tfm)[0])
        src_tf = "1h" if idn in (102, 105) else "15m"
        h1 = _frame_from(_pick(paths, src_tf)[0])
        h1["bar_ms"] = (h1["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
                        .to_numpy().astype("datetime64[ms]").astype("int64"))
        h1["close_ms"] = h1["bar_ms"] + (3_600_000 if src_tf == "1h" else 900_000)
        key = "BTCUSDT_1h" if idn in (102, 105) else "BTCUSDT_15m"
        aux[key] = h1
        return m, aux
    if idn == 103:
        return _frame_from(_pick(paths, "1m")[0]), aux
    if idn in (106, 108):
        return _resample(_frame_from(_pick(paths, "1m")[0]), "3min"), aux
    if idn == 109:
        m1 = _frame_from(_pick(paths, "1m")[0])
        tcol = "taker_buy_base_vol" if "taker_buy_base_vol" in m1.columns             else "taker_buy_base"  # 5m_taker vs 1m_taker column names
        m1["delta"] = 2.0 * m1[tcol] - m1["volume"]
        return m1, aux
    if idn == 110:
        m1 = _frame_from(_pick(paths, "1m")[0])
        tcol = "taker_buy_base_vol" if "taker_buy_base_vol" in m1.columns             else "taker_buy_base"  # 5m_taker vs 1m_taker column names
        m1["delta"] = 2.0 * m1[tcol] - m1["volume"]
        return _resample(m1, "3min"), aux
    if idn == 112:
        m = _frame_from(_pick(paths, "15m")[0])
        bms = (m["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
               .to_numpy().astype("datetime64[ms]").astype("int64"))
        r, e, _ = funding_events(sym, bms)
        aux["rate"], aux["is_fund"] = r, e
        return m, aux
    if idn == 115:
        m = _frame_from(_pick(paths, "15m")[0])
        b = _frame_from([q for q in paths if "BTCUSDT_15m" in q][0])
        b["bar_ms"] = (b["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
                       .to_numpy().astype("datetime64[ms]").astype("int64"))
        b["close_ms"] = b["bar_ms"] + 900_000
        aux["BTCUSDT_15m"] = b
        return m, aux
    if idn in (116, 119):
        tfm = "5m" if idn == 116 else "1m"
        m = _frame_from(_pick(paths, tfm)[0])
        b = _frame_from([q for q in paths if f"BTCUSDT_{tfm}" in q][0])
        b["bar_ms"] = (b["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
                       .to_numpy().astype("datetime64[ms]").astype("int64"))
        aux[f"BTCUSDT_{tfm}"] = b
        return m, aux
    if idn in (122, 125, 130, 139):  # 3m cells: resampled from the 1m tape
        wd = "1m_taker" if idn == 139 else "binance_klines_1m"
        return _resample(_frame_from(_pick(paths, "1m")[0]),
                         "3min"), aux
    if idn in (104, 120, 121, 123, 124, 126, 127, 128, 129, 131,
               138, 140, 141, 144, 150):
        tfm = CELLS[idn][1]
        return _frame_from(_pick(paths, tfm)[0]), aux
    if idn == 133:
        m1 = _frame_from(_pick(paths, "1m")[0])
        tcol = "taker_buy_base_vol" if "taker_buy_base_vol" in m1.columns             else "taker_buy_base"  # 5m_taker vs 1m_taker column names
        m1["delta"] = 2.0 * m1[tcol] - m1["volume"]
        return _dollar_bars(m1), aux
    if idn == 134:
        m5 = _frame_from(_pick(paths, "5m")[0])
        a = _atr(m5["high"].values, m5["low"].values, m5["close"].values)
        brick = 0.5 * float(np.median(a[14:2014][np.isfinite(a[14:2014])]))
        rk = _renko(m5, brick)
        aux["brick"] = brick
        return rk, aux
    if idn == 135:
        m1 = _frame_from(_pick(paths, "1m")[0])
        a = _atr(m1["high"].values, m1["low"].values, m1["close"].values)
        brick = 0.3 * float(np.median(a[14:2014][np.isfinite(a[14:2014])]))
        return _range_bars(m1, brick), aux
    raise ValueError(f"cell {idn} not runnable")


def _prepare_main(df):
    df = df.copy()
    ts = df["timestamp"]
    if ts.dt.tz is None:  # _renko/_range_bars emit tz-naive stamps
        ts = ts.dt.tz_localize("UTC")
    df["timestamp"] = ts.dt.tz_convert("UTC")  # re-assign: Book needs tz-aware
    df["bar_ms"] = (ts.dt.tz_convert("UTC").dt.tz_localize(None)
                    .to_numpy().astype("datetime64[ms]").astype("int64"))
    if "volume" not in df:
        df["volume"] = 0.0
    return df


def _daily_ok(book, j, ms):
    """O(1) amortized: the trades list is append-only and exit-ordered, so
    the counters are updated incrementally from a pointer instead of
    rescanning the whole ledger every bar (the O(n x trades) version hung
    the 1m cells for >10 minutes)."""
    day = int(ms[j] // 86_400_000)
    if not hasattr(book, "_dailycache"):
        book._dailycache = {"seen": 0, "losses": {}, "entries": {}}
    cc = book._dailycache
    while cc["seen"] < len(book.trades):
        t = book.trades[cc["seen"]]
        cc["seen"] += 1
        ed = int(pd.Timestamp(t["entry_time"]).value // 86_400_000_000_000)
        xd = int(pd.Timestamp(t["exit_time"]).value // 86_400_000_000_000)
        cc["entries"][ed] = cc["entries"].get(ed, 0) + 1
        if t["pnl"] < 0 and xd == ed:
            cc["losses"][ed] = cc["losses"].get(ed, 0) + 1
    if cc["losses"].get(day, 0) >= 3:
        return False
    entries = cc["entries"].get(day, 0)
    if book.pos is not None:
        pd_ = int(pd.Timestamp(book.pos["entry_ts"]).value // 86_400_000_000_000)
        if pd_ == day:
            entries += 1
    return entries < 6


def run(paths, params):
    p = dict(params)
    idn = int(p.pop("id"))
    if p:
        raise ValueError(f"unknown s101 params: {sorted(p)}")
    if idn in NO_DATA:
        raise ValueError(f"NO DATA: {idn}: {NO_DATA[idn]}")
    if idn not in CELLS:
        raise ValueError(f"unknown s101 cell: {idn}")
    if idn in (117, 118):
        return run_spread(idn, paths, {"id": idn})

    symbol, tf_label, tf_minutes = CELLS[idn]
    main, aux = build_frame(idn, paths)
    main = _prepare_main(main)
    n = int(len(main["open"]))
    ms = main["bar_ms"]
    oos_start = int(n * 0.7)

    def make_book():
        return Book(symbol, tf_label, main, init=INIT, fee=FEE, slip=SLIP,
                    risk_pct=RISK, max_leverage=MAXLEV, charge_funding=True)

    results = {}
    for tag in ("full", "oos"):
        book = make_book()
        sig_core = _make_sig(idn, main, aux, symbol)

        def signal(j, book=book, sig_core=sig_core):
            if j + 1 >= n:
                return None
            s = sig_core(j)
            if s is None:
                return None
            if s.get("side", 0) == 0:
                return s
            if tag == "oos" and j + 1 < oos_start:
                return None
            if not _daily_ok(book, j, ms, ):
                return None
            ep = float(main["open"][j + 1])
            sp = float(s["stop_px"])
            side = s["side"]
            if (side == 1 and sp >= ep) or (side == -1 and sp <= ep):
                return None
            return s

        if tag == "full":
            book.run(signal, start_idx=0, end_idx=n - 1)
        else:
            book.run(signal, start_idx=0, end_idx=n - 1, trade_from=oos_start)
        results[tag] = (book, book_metrics(book))

    book, full_m = results["full"]
    _, oos_m = results["oos"]
    metrics = dict(full_m)
    metrics.update({
        "oos_profit_factor": oos_m["profit_factor"],
        "oos_return_pct": oos_m["return_pct"],
        "oos_n_trades": oos_m["n_trades"],
        "oos_max_dd_pct": oos_m["max_dd_pct"],
        "oos_boot_ci_lo": oos_m["boot_ci_lo"],
        "id": idn, "symbol": symbol, "tf": tf_label,
        "engine_version": ENGINE_VERSION,
        "fragile_label": bool(oos_m["n_trades"] < 200),
        "fee_per_side_bps": FEE * 1e4, "slip_per_side_bps": SLIP * 1e4,
        "pack_rules": "signal close/enter next open; stop-first; 0.5% risk; "
                      "3 losses/day cap; 6 trades/day cap on 1m-3m; "
                      "no trailing; funding at settlements (perps only)",
    })
    trades = [{"entry_time": t["entry_time"], "exit_time": t["exit_time"],
               "side": t["side"], "entry": float(t["entry"]),
               "exit": float(t["exit"]), "pnl": float(t["pnl"]),
               "reason": t["reason"]} for t in book.trades]
    # bt.py's metric resolver walks tables as a LIST of rows keyed by "id"
    tables = [{"id": f"s101_{idn}", "symbol": symbol, "tf": tf_label,
               "trades": trades}]
    prov = {"engine_version": ENGINE_VERSION,
            "sources_of_record": ["code/prompts_101_150.txt"],
            "core": "p100_screen_engine.Book (audited by the p100 campaign)",
            "conventions": {"signal": "close of bar j, fill at open of j+1",
                            "ties": "stop first",
                            "gap": "gap-through stop fills at the open",
                            "costs": "5 bps fee + 0.5 bps slip per side "
                                     "(repo uniform 11 bps RT; the pack's "
                                     "own 10-18 bps schedule deviates, "
                                     "declared)",
                            "risk": "0.5% equity/trade, max 3x leverage",
                            "daily": "max 3 losing trades per UTC day; max 6 "
                                     "trades/day on 1m-3m books",
                            "funding": "at real settlements for the perps; "
                                       "NVDA/SPCX not charged (no file)",
                            "split": "70/30 chronological, no purge "
                                     "(pack rule #17)",
                            "fragile": "pack rule #18 label when OOS n < 200"}}
    return metrics, prov, tables


def run_spread(idn, paths, params):
    """117 / 118: two-leg dollar-neutral ledger (declared)."""
    if idn == 117:
        A = _frame_from(_pick(paths, "15m")[0])
        B = _frame_from([q for q in paths if "BTCUSDT_15m" in q][0])
        tf_minutes = 15
    else:
        A = _resample(_frame_from(_pick(paths, "1m")[0]), "3min")
        B = _resample(_frame_from([q for q in paths if "ETHUSDT_1m" in q][0]),
                      "3min")
        tf_minutes = 3
    a = A.set_index("timestamp")["close"]
    b = B.set_index("timestamp")["close"]
    idx = a.index.intersection(b.index)
    a = a.reindex(idx).values
    b = b.reindex(idx).values
    n = len(idx)
    ms = (idx.tz_convert("UTC").tz_localize(None).to_numpy()
          .astype("datetime64[ms]").astype("int64"))
    la = np.log(a)
    lb = np.log(b)
    sym_a, sym_b = ("SOLUSDT", "BTCUSDT") if idn == 117 else ("SOLUSDT", "ETHUSDT")
    ra, isa, _ = funding_events(sym_a, ms)
    rb, isb, _ = funding_events(sym_b, ms)

    cash = INIT
    pos = None
    trades = []
    curve = []
    funding_paid = 0.0
    fees_paid = 0.0
    sp_seen = [0]
    sp_day = [{"entries": {}, "losses": {}}]
    oos_start = int(n * 0.7)
    ZWIN = 200

    def stats(j):
        la_, lb_ = la[j - ZWIN:j], lb[j - ZWIN:j]
        if idn == 117:
            A_ = np.polyfit(lb_, la_, 1)
            sp = la_ - A_[0] * lb_
        else:
            sp = la_ - lb_
        m = float(sp.mean())
        s = float(sp.std(ddof=0))
        z = (la[j] - (A_[0] * lb[j] + A_[1]) - m) / s if idn == 117 else \
            ((la[j] - lb[j]) - m) / s
        ok = True
        if idn == 117:
            resid = la_ - (A_[0] * lb_ + A_[1])
            ok = _adf_t(resid) < -2.86
        return float(z), ok, _half_life(sp - m)

    for j in range(ZWIN, n):
        day = int(ms[j] // 86_400_000)
        if pos is not None:
            if isa[j]:
                f = pos["sa"] * pos["qa"] * a[j] * ra[j]
                cash -= f
                funding_paid += f
            if isb[j]:
                f = pos["sb"] * pos["qb"] * b[j] * rb[j]
                cash -= f
                funding_paid += f
            z, ok, hl = stats(j)
            exit_hit = abs(z) <= (0.0 if idn == 117 else 0.5)
            stop_hit = abs(z) >= 3.0
            if exit_hit or stop_hit:
                fa = abs(pos["qa"]) * a[j] * (FEE + SLIP)
                fb = abs(pos["qb"]) * b[j] * (FEE + SLIP)
                pnl = (pos["sa"] * pos["qa"] * (a[j] - pos["pa"]) - fa) \
                    + (pos["sb"] * pos["qb"] * (b[j] - pos["pb"]) - fb) \
                    - pos["fee_in"]
                cash += pnl
                fees_paid += fa + fb
                tr = dict(entry_time=str(pos["t"]), exit_time=str(idx[j]),
                          side=pos["sa"], pnl=float(pnl),
                          reason="stop" if stop_hit else "z_exit",
                          day_entry=pos["day"], day_exit=int(ms[j] // 86_400_000))
                trades.append(tr)
                pos = None
        if pos is None:
            while sp_seen[0] < len(trades):
                t = trades[sp_seen[0]]
                sp_seen[0] += 1
                de, dx = t["day_entry"], t["day_exit"]
                sp_day[0]["entries"][de] = sp_day[0]["entries"].get(de, 0) + 1
                if t["pnl"] < 0 and dx == de:
                    sp_day[0]["losses"][de] = sp_day[0]["losses"].get(de, 0) + 1
            losses = sp_day[0]["losses"].get(day, 0)
            entries = sp_day[0]["entries"].get(day, 0)
            if losses < 3 and entries < 6:
                z, ok, hl = stats(j)
                want = 0
                if idn == 117:
                    if ok and z <= -2.0:
                        want = 1
                    elif ok and z >= 2.0:
                        want = -1
                else:
                    if hl < 50:
                        if z <= -2.0:
                            want = 1
                        elif z >= 2.0:
                            want = -1
                if want != 0 and cash > 0:  # ruin guard: no entries on a
                    notional = cash * 0.5   # blown account (negative notional
                    qa = notional / a[j]    # would flip the spread signs)
                    qb = notional / b[j]
                    fa = qa * a[j] * (FEE + SLIP)
                    fb = qb * b[j] * (FEE + SLIP)
                    # the entry fee is NOT charged to cash here: the exit pnl
                    # below is net of BOTH fees (repo doctrine), so the cash
                    # and the reported PnL describe the same money
                    fees_paid += fa + fb
                    pos = dict(sa=want, qa=qa, pa=a[j], sb=-want, qb=qb,
                               pb=b[j], t=idx[j], fee_in=fa + fb,
                               day=int(ms[j] // 86_400_000))
        curve.append(cash)
    if pos is not None:
        j = n - 1
        fa = abs(pos["qa"]) * a[j] * (FEE + SLIP)
        fb = abs(pos["qb"]) * b[j] * (FEE + SLIP)
        pnl = (pos["sa"] * pos["qa"] * (a[j] - pos["pa"]) - fa) \
            + (pos["sb"] * pos["qb"] * (b[j] - pos["pb"]) - fb) \
            - pos["fee_in"]
        cash += pnl
        fees_paid += fa + fb
        trades.append(dict(entry_time=str(pos["t"]), exit_time=str(idx[j]),
                           side=pos["sa"], pnl=float(pnl),
                           reason="end_of_data"))
        if curve:
            curve[-1] = cash

    pnls = np.array([t["pnl"] for t in trades], float)
    gp = float(pnls[pnls > 0].sum()) if len(pnls) else 0.0
    gl = float(-pnls[pnls < 0].sum()) if len(pnls) else 0.0
    pf = (gp / gl) if gl > 0 else (None if gp > 0 else 0.0)
    eq = np.array(curve, float)
    peak = np.maximum.accumulate(eq) if len(eq) else np.array([INIT])
    mdd = float((eq / peak - 1).min()) if len(eq) else 0.0
    resid = (cash - INIT) - (float(pnls.sum()) - funding_paid)
    if abs(resid) > max(1e-6, abs(float(pnls.sum())) * 1e-9):
        raise AssertionError(f"spread ledger invariant broken: {resid}")
    boot = bootstrap_r([t["pnl"] / (INIT * 0.005) for t in trades])
    thirds = []
    for i in range(3):
        aa, bb = len(eq) * i // 3, len(eq) * (i + 1) // 3
        thirds.append(100.0 * (eq[bb - 1] / eq[aa] - 1) if bb > aa and eq[aa] > 0
                      else 0.0)
    oos_day = int(ms[oos_start] // 86_400_000)
    oos_pnls = [t["pnl"] for t in trades if t["day_exit"] >= oos_day]
    op = np.array(oos_pnls, float)
    ogp = float(op[op > 0].sum()) if len(op) else 0.0
    ogl = float(-op[op < 0].sum()) if len(op) else 0.0
    opf = (ogp / ogl) if ogl > 0 else (None if ogp > 0 else 0.0)
    top5 = float(np.sort(pnls)[::-1][:5].sum()) if len(pnls) >= 5 else 0.0
    metrics = {
        "return_pct": 100 * (cash / INIT - 1),
        "profit_factor": pf, "n_trades": int(len(trades)),
        "win_rate": 100 * float((pnls > 0).sum() / len(pnls)) if len(pnls) else 0.0,
        "max_dd_pct": 100 * mdd,
        "n_periods_green": int(sum(1 for t in thirds if t > 0)),
        "boot_ci_lo": float(boot["ci_low"]), "boot_ci_hi": float(boot["ci_high"]),
        "oos_profit_factor": opf,
        "oos_return_pct": 100 * float(sum(oos_pnls) / INIT),
        "oos_n_trades": int(len(oos_pnls)),
        "top5_pnl_share": (100.0 * top5 / float(pnls.sum())) if pnls.sum() > 0 else None,
        "net_without_top5_pct": 100.0 * (float(pnls.sum()) - top5) / INIT if len(pnls) else None,
        "fees_paid_usdt": fees_paid, "funding_paid_usdt": funding_paid,
        "id": idn, "tf": "15m" if idn == 117 else "3m",
        "fragile_label": bool(len(oos_pnls) < 200),
        "fee_per_side_bps": FEE * 1e4, "slip_per_side_bps": SLIP * 1e4,
        "pnl_identity_resid": float(resid),
    }
    prov = {"engine_version": ENGINE_VERSION,
            "sources_of_record": ["code/prompts_101_150.txt"],
            "conventions": {"ledger": "two-leg dollar-neutral (50% gross per "
                                      "leg), per-leg 11 bps RT, funding both "
                                      "legs at settlements",
                            "z": "log-ratio z over 200 bars; cointegration = "
                                 "ADF(1) t-stat of the OLS residual < -2.86 "
                                 "(declared approximation); half-life "
                                 "-ln2/ln(phi)",
                            "split": "70/30 chronological"}}
    tables = [{"id": f"s101_{idn}", "trades": trades}]
    return metrics, prov, tables


def dispatch(paths, params):
    p = dict(params)
    idn = int(p["id"])
    if idn in (117, 118):
        return run_spread(idn, paths, p)
    return run(paths, p)
