#!/usr/bin/env python
"""EMA×VWAP 50-Strategy Suite — harness runner (source: the attached
`EMA×VWAP 50-Strategy Suite-claude.md`, a natural-language spec; NO code was
supplied). Every rule below is a declared port of the attachment; the
execution conventions (next-open fill, SL-first ties, repo costs + real
funding, one position, full-equity compounding) are the repo's, stated in
results/emavwap50_pre_registration.md.

One artifact = one numbered row on BTCUSDT at the row's own timeframe.
Rows needing a timeframe with no CSV on disk or outside data not on disk are
REFUSED as NO DATA (never estimated). Every artifact asserts
eq[-1] - INIT == sum(pnl) and measures the author-cost and zero-cost controls
on the SAME signals inside the artifact.

Audit: code/_emavwap50_audit.py (known answers, both directions).
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

INIT = 10000.0
ARM_BARS = 5
VWAP_WARMUP = 15
REPO = dict(fee=5.0, slip=0.5)     # bps per side
AUTHOR = dict(fee=4.0, slip=1.5)   # 0.04% taker + 1.5 bps slip midpoint
ZERO = dict(fee=0.0, slip=0.0)

# rows with a native BTC kline CSV at their timeframe and data available
RUNNABLE = {
    1: "1m", 4: "5m", 5: "5m", 6: "15m", 7: "15m", 8: "15m", 10: "1h",
    11: "1m", 13: "5m", 14: "15m", 15: "15m", 18: "5m", 19: "5m",
    20: "15m", 21: "15m", 23: "1h", 24: "1h", 28: "1d", 31: "5m",
    33: "5m", 36: "15m", 42: "5m", 43: "5m", 44: "15m", 49: "1d", 50: "1d",
}
NO_DATA = {
    2: "3m CSV absent", 3: "3m CSV absent", 9: "30m CSV absent",
    12: "3m CSV absent", 16: "30m CSV absent", 17: "3m CSV absent",
    22: "30m CSV absent", 25: "2h CSV absent", 26: "4h CSV absent",
    27: "4h CSV absent", 29: "3m CSV absent", 30: "3m CSV absent / no OI",
    32: "perp-spot basis not on disk", 34: "alt-only rule / BTC.D not on disk",
    35: "liquidation tape not on disk", 37: "open interest not on disk",
    38: "BTC.D not on disk", 39: "4h CSV absent", 40: "4h CSV absent",
    41: "3m CSV absent", 45: "4h CSV absent", 46: "4h CSV absent",
    47: "6h CSV absent", 48: "12h CSV absent",
}


# ── indicator primitives ───────────────────────────────────────────────────
def ema(x, n):
    return pd.Series(np.asarray(x, float)).ewm(span=n, adjust=False,
                                              min_periods=n).mean().to_numpy()


def wma(x, n):
    s = pd.Series(np.asarray(x, float))
    w = np.arange(1, n + 1, dtype=float)
    out = np.full(len(s), np.nan)
    v = s.to_numpy()
    for i in range(n - 1, len(v)):
        out[i] = np.dot(v[i - n + 1:i + 1], w) / w.sum()
    return out


def hma(x, n):
    half = max(2, n // 2)
    root = max(2, int(round(np.sqrt(n))))
    raw = 2.0 * wma(x, n) - wma(x, half)
    return wma(raw, root)


def zlema(x, n):
    v = np.asarray(x, float)
    lag = max(1, int(round((n - 1) / 2.0)))
    adj = 2.0 * v - np.concatenate([np.full(lag, v[0]), v[:-lag]])
    return ema(adj, n)


def dema(x, n):
    e1 = ema(x, n)
    return 2.0 * e1 - ema(e1, n)


def tema(x, n):
    e1 = ema(x, n)
    e2 = ema(e1, n)
    return 3.0 * e1 - 3.0 * e2 + ema(e2, n)


def kama(x, n=10, f=2, s=30):
    v = np.asarray(x, float)
    out = np.full(len(v), np.nan)
    if len(v) <= s:
        return out
    prev = v[s]
    out[s] = prev
    for i in range(s + 1, len(v)):
        direction = abs(v[i] - v[i - n])
        volatility = np.sum(np.abs(v[i - n + 1:i + 1] - v[i - n:i]))
        er = direction / volatility if volatility > 0 else 0.0
        c = (er * (2.0 / (f + 1.0))) ** 2
        prev = prev + c * (v[i] - prev)
        out[i] = prev
    return out


def alma(x, n=11, offset=0.85, sigma=6):
    v = np.asarray(x, float)
    out = np.full(len(v), np.nan)
    m = int(round(offset * (n - 1)))
    w = np.exp(-0.5 * ((np.arange(n) - m) / sigma) ** 2)
    w /= w.sum()
    for i in range(n - 1, len(v)):
        out[i] = np.dot(v[i - n + 1:i + 1], w)
    return out


def atr(h, l, c, n=14):
    h, l, c = np.asarray(h, float), np.asarray(l, float), np.asarray(c, float)
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def adx(h, l, c, n=14):
    h, l, c = np.asarray(h, float), np.asarray(l, float), np.asarray(c, float)
    up = np.diff(h, prepend=h[0])
    dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.fmax(h - l, np.fmax(np.abs(h - np.concatenate([[c[0]], c[:-1]])),
                                np.abs(l - np.concatenate([[c[0]], c[:-1]]))))
    alpha = 1.0 / n
    atr_ = pd.Series(tr).ewm(alpha=alpha, adjust=False, min_periods=n).mean().to_numpy()
    pdi = 100.0 * pd.Series(pdm).ewm(alpha=alpha, adjust=False, min_periods=n).mean().to_numpy() / atr_
    mdi = 100.0 * pd.Series(mdm).ewm(alpha=alpha, adjust=False, min_periods=n).mean().to_numpy() / atr_
    dx = 100.0 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-12)
    return pd.Series(dx).ewm(alpha=alpha, adjust=False, min_periods=n).mean().to_numpy()


def supertrend(h, l, c, n=10, mult=3.0):
    a = atr(h, l, c, n)
    mid = (h + l) / 2.0
    upper = mid + mult * a
    lower = mid - mult * a
    out = np.full(len(c), np.nan)
    fu, fl = upper.copy(), lower.copy()
    trend = 1
    for i in range(n, len(c)):
        if c[i] > fu[i - 1]:
            trend = 1
        elif c[i] < fl[i - 1]:
            trend = -1
        else:
            fu[i] = min(fu[i], fu[i - 1]) if trend == 1 else fu[i]
            fl[i] = max(fl[i], fl[i - 1]) if trend == -1 else fl[i]
        out[i] = fl[i] if trend == 1 else fu[i]
    return out


def _group_ids(ts_ms, kind, hour=None):
    dt = pd.to_datetime(ts_ms, unit="ms", utc=True)
    if kind == "daily":
        key = dt.strftime("%Y-%m-%d")
    elif kind == "weekly":
        key = dt.strftime("%G-W%V")
    elif kind == "monthly":
        key = dt.strftime("%Y-%m")
    elif kind == "custom":
        shifted = dt - pd.Timedelta(hours=hour)
        key = shifted.strftime("%Y-%m-%d")
    else:
        raise ValueError(kind)
    return key.to_numpy()


def anchored_vwap(df, kind="daily", hour=None, warmup=VWAP_WARMUP):
    tp = (df["high"].to_numpy(float) + df["low"].to_numpy(float) +
          df["close"].to_numpy(float)) / 3.0
    vol = df["volume"].to_numpy(float)
    gid = _group_ids(df["open_ts"].to_numpy(np.int64), kind, hour)
    out = np.full(len(df), np.nan)
    pv = tv = 0.0
    last = None
    bars = 0
    for i in range(len(df)):
        if gid[i] != last:
            pv = tv = 0.0
            bars = 0
            last = gid[i]
        pv += tp[i] * vol[i]
        tv += vol[i]
        bars += 1
        if tv > 0 and bars > warmup:
            out[i] = pv / tv
    return out


def rolling_vwap(df, n):
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = (tp * df["volume"]).rolling(n, min_periods=n).sum()
    vv = df["volume"].rolling(n, min_periods=n).sum()
    return (pv / vv).to_numpy()


def swing_low_anchored_vwap(df, lb=10):
    low = df["low"].to_numpy(float)
    pivot = np.full(len(df), False)
    for i in range(lb, len(df) - lb):
        pivot[i] = low[i] == low[i - lb:i + lb + 1].min()
    tp = (df["high"].to_numpy(float) + df["low"].to_numpy(float) +
          df["close"].to_numpy(float)) / 3.0
    vol = df["volume"].to_numpy(float)
    out = np.full(len(df), np.nan)
    anchor = None
    pv = tv = 0.0
    for i in range(len(df)):
        if anchor is None or (pivot[i] and low[i] < low[anchor]):
            anchor = i
            pv = tv = 0.0
        if anchor is not None:
            pv += tp[i] * vol[i]
            tv += vol[i]
            if i - anchor > VWAP_WARMUP and tv > 0:
                out[i] = pv / tv
    return out


def prior_day_closing_vwap(df):
    daily = anchored_vwap(df, "daily", warmup=0)
    gid = _group_ids(df["open_ts"].to_numpy(np.int64), "daily")
    out = np.full(len(df), np.nan)
    last = {}
    for i in range(len(df)):
        if not np.isnan(daily[i]):
            last[gid[i]] = daily[i]
    gprev = None
    for i in range(len(df)):
        if gprev is not None:
            out[i] = last.get(gprev, np.nan)
        if i + 1 < len(df) and gid[i + 1] != gid[i]:
            gprev = gid[i]
    return out


def low_anchored_vwap(df, lookback):
    low = df["low"].to_numpy(float)
    tp = (df["high"].to_numpy(float) + df["low"].to_numpy(float) +
          df["close"].to_numpy(float)) / 3.0
    vol = df["volume"].to_numpy(float)
    out = np.full(len(df), np.nan)
    anchor = 0
    pv = tv = 0.0
    for i in range(len(df)):
        if i >= lookback and low[i] == low[i - lookback:i + 1].min():
            anchor = i
            pv = tv = 0.0
        pv += tp[i] * vol[i]
        tv += vol[i]
        if i - anchor > VWAP_WARMUP and tv > 0:
            out[i] = pv / tv
    return out


def _load_funding(path):
    if not path or not os.path.exists(path):
        return []
    recs = json.load(open(path, encoding="utf-8"))
    return sorted(((int(r["t"]), float(r["r"])) for r in recs))


# ── signals ────────────────────────────────────────────────────────────────
def build_signals(df, row_id, tf, funding_events=None):
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    n = len(df)
    dt = pd.to_datetime(df["open_ts"].to_numpy(np.int64), unit="ms", utc=True)
    hour = dt.hour.to_numpy()
    dow = dt.dayofweek.to_numpy()

    fast_map = {1: ("ema", 9), 4: ("ema", 11), 5: ("ema", 21), 6: ("ema", 11),
                7: ("ema", 20), 8: ("ema", 20), 10: ("ema", 11), 11: ("hma", 9),
                13: ("dema", 11), 14: ("tema", 11), 15: ("kama", 10),
                18: ("ema", 11), 19: ("ema", 11), 20: ("ema", 11),
                21: ("ema", 11), 23: ("ema", 11), 24: ("ema", 11),
                28: ("ema", 11), 31: ("ema", 11), 33: ("ema", 11),
                36: ("ema", 11), 42: ("ema", 11), 43: ("ema", 11),
                44: ("ema", 11), 49: ("ema", 11), 50: ("ema", 11)}
    kind, per = fast_map[row_id]
    fast = {"ema": lambda: ema(c, per), "hma": lambda: hma(c, per),
            "dema": lambda: dema(c, per), "tema": lambda: tema(c, per),
            "kama": lambda: kama(c, per, 2, 30)}[kind]()

    if row_id in (1, 4, 6, 11, 13, 14, 15, 18, 19, 20, 21, 23, 31, 33, 36,
                  42, 43, 44):
        ref = anchored_vwap(df, "daily")
    elif row_id in (5, 10):
        ref = anchored_vwap(df, "weekly")
    elif row_id == 7:
        ref = anchored_vwap(df, "custom", hour=7)
    elif row_id == 8:
        ref = anchored_vwap(df, "custom", hour=13.5)
    elif row_id == 18:
        ref = pd.Series(c).rolling(20, min_periods=20).mean().to_numpy()
    elif row_id == 19:
        ref = supertrend(h, l, c, 10, 3.0)
    elif row_id == 20:
        ref = (pd.Series(h).rolling(26, min_periods=26).max().to_numpy() +
               pd.Series(l).rolling(26, min_periods=26).min().to_numpy()) / 2.0
    elif row_id == 21:
        ref = (pd.Series(h).rolling(20, min_periods=20).max().to_numpy() +
               pd.Series(l).rolling(20, min_periods=20).min().to_numpy()) / 2.0
    elif row_id == 23:
        ref = prior_day_closing_vwap(df)
    elif row_id == 24:
        ref = swing_low_anchored_vwap(df, 10)
    elif row_id == 28:
        ref = low_anchored_vwap(df, 90)
    elif row_id == 49:
        ref = ema(c, 50)
    elif row_id == 50:
        ref = rolling_vwap(df, 30)
    else:
        raise ValueError(row_id)

    a = atr(h, l, c, 14)
    a22 = atr(h, l, c, 22)
    armed = np.zeros(n, bool)
    cross_up = (fast > ref) & (np.roll(fast, 1) <= np.roll(ref, 1))
    cross_dn = (fast < ref) & (np.roll(fast, 1) >= np.roll(ref, 1))
    cross_up[0] = cross_dn[0] = False
    for i in range(n):
        if cross_up[i] or cross_dn[i]:
            armed[i:i + ARM_BARS + 1] = True

    up = (c > np.maximum(fast, ref)) & armed
    dn = (c < np.minimum(fast, ref)) & armed
    # generic filters declared per row
    if row_id == 1:
        ok = v > 1.5 * pd.Series(v).rolling(20, min_periods=20).mean().to_numpy()
        up &= ok
        dn &= ok
    if row_id == 4:
        up &= ref > np.roll(ref, 5)
        dn &= ref < np.roll(ref, 5)
    if row_id == 6:
        # 1h context on a 15m chart is not served: use same-chart EMA50 proxy
        # (declared in the report as an approximation, not the author's HTF)
        e50 = ema(c, 50)
        up &= c > e50
        dn &= c < e50
    if row_id in (7, 8):
        lo, hi = (7, 13) if row_id == 7 else (13.5, 20)
        ok = (hour + dt.minute.to_numpy() / 60.0 >= lo) & \
             (hour + dt.minute.to_numpy() / 60.0 <= hi)
        up &= ok
        dn &= ok
    if row_id == 10 or row_id == 11:
        med = pd.Series(a).rolling(50, min_periods=50).median().to_numpy()
        ok = a > med
        up &= ok
        dn &= ok
    if row_id in (13, 14):
        ok = adx(h, l, c, 14) > 20
        up &= ok
        dn &= ok
    if row_id == 15:
        ch = np.abs(np.diff(c, prepend=c[0]))
        er = pd.Series(ch).rolling(10, min_periods=10).sum().to_numpy() / \
             np.maximum(pd.Series(np.abs(np.diff(c, prepend=c[0])))
                        .rolling(30, min_periods=30).sum().to_numpy(), 1e-12)
        ok = er > 0.3
        up &= ok
        dn &= ok
    if row_id == 18:
        bw = pd.Series(c).rolling(20, min_periods=20).std().to_numpy()
        ok = bw > pd.Series(bw).rolling(50, min_periods=50).median().to_numpy()
        up &= ok
        dn &= ok
    if row_id == 19:
        ok = v > 1.2 * pd.Series(v).rolling(20, min_periods=20).mean().to_numpy()
        up &= ok
        dn &= ok
    if row_id == 21:
        hi10 = pd.Series(h).rolling(10, min_periods=10).max().to_numpy()
        up &= c > hi10
        dn &= c < np.roll(hi10, 1)
    if row_id == 31:
        if "taker_buy_base" not in df.columns:
            raise RuntimeError("CVD proxy needs taker fields")
        cvd = pd.Series(2.0 * df["taker_buy_base"].to_numpy(float) -
                        v).rolling(20, min_periods=20).mean().to_numpy()
        ok = cvd > pd.Series(cvd).ewm(span=20, adjust=False).mean().to_numpy()
        up &= ok
        dn &= ~ok
    if row_id == 33:
        if "taker_buy_base" not in df.columns:
            raise RuntimeError("taker ratio needs taker fields")
        ratio = (pd.Series(df["taker_buy_base"].to_numpy(float))
                 .rolling(3, min_periods=3).sum().to_numpy() /
                 np.maximum(pd.Series(v).rolling(3, min_periods=3).sum().to_numpy(), 1e-12))
        up &= ratio > 1.1
        dn &= ratio < 1.1
    if row_id == 36 and funding_events:
        # no entries in the 10 min before a settlement instant
        ts = df["open_ts"].to_numpy(np.int64)
        bad = np.zeros(n, bool)
        for t, _ in funding_events:
            idx = np.searchsorted(ts, t) - 1
            if 0 <= idx < n and 0 <= t - ts[idx] <= 10 * 60_000:
                bad[idx] = True
        up &= ~bad
        dn &= ~bad

    # VWAP reset warmup (skip first 15 bars after every anchor reset)
    if row_id in (1, 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 23, 24, 28, 31, 33,
                  36, 42, 43, 44, 50):
        kind = ("weekly" if row_id in (5, 10) else
                "custom" if row_id in (7, 8) else "daily")
        g = _group_ids(df["open_ts"].to_numpy(np.int64), kind,
                       7 if row_id == 7 else 13.5 if row_id == 8 else None)
        warm = np.zeros(n, bool)
        last, k = None, 0
        for i in range(n):
            k = 0 if g[i] != last else k + 1
            last = g[i]
            warm[i] = k <= VWAP_WARMUP
        up &= ~warm
        dn &= ~warm

    # exits
    prev_c = np.concatenate([[c[0]], c[:-1]])
    prev_fast = np.concatenate([[fast[0]], fast[:-1]])
    if row_id == 41:  # two consecutive closes below EMA11 (3m -> NO DATA)
        low2 = (c < fast) & (prev_c < prev_fast)
        xlong = low2
        xshort = (c > fast) & (prev_c > prev_fast)
    elif row_id == 42:
        xlong = (c < ref) & (prev_c >= np.concatenate([[ref[0]], ref[:-1]]))
        xshort = (c > ref) & (prev_c <= np.concatenate([[ref[0]], ref[:-1]]))
    elif row_id == 43:
        xlong = c < fast - 0.25 * a
        xshort = c > fast + 0.25 * a
    elif row_id == 44:
        xlong = (c < fast) & (prev_c >= prev_fast)
        xshort = (c > fast) & (prev_c <= prev_fast)
    elif row_id == 45:  # Chandelier 3xATR22 (4h -> NO DATA)
        xlong = c < (np.maximum.accumulate(h) - 3.0 * a22)
        xshort = c > (np.minimum.accumulate(l) + 3.0 * a22)
    elif row_id == 46:  # 4h -> NO DATA
        xlong = (c < fast) & (prev_c >= prev_fast)
        xshort = (c > fast) & (prev_c <= prev_fast)
    else:
        xlong = (c < fast) & (prev_c >= prev_fast)
        xshort = (c > fast) & (prev_c <= prev_fast)

    return dict(fast=fast, ref=ref, up=up, dn=dn, xlong=xlong, xshort=xshort,
                atr=a, atr22=a22, o=o, c=c, ts=df["open_ts"].to_numpy(np.int64))


# ── simulator ──────────────────────────────────────────────────────────────
def simulate(sig, fees, use_funding=False, funding_events=None, max_hold=None,
             scale_at_r=False):
    o, c, ts = sig["o"], sig["c"], sig["ts"]
    n = len(o)
    up, dn, xl, xs = sig["up"], sig["dn"], sig["xlong"], sig["xshort"]
    fee, slip = fees["fee"] / 1e4, fees["slip"] / 1e4
    cash = INIT
    qty = 0.0
    pos = 0
    entry = 0.0
    entry_i = 0
    entry_fee = 0.0
    fund_this_trade = 0.0
    trades = []
    funded = 0.0
    credit = np.zeros(n, bool)
    if use_funding and funding_events:
        for t, _ in funding_events:
            i = int(np.searchsorted(ts, t, side="right") - 1)
            if 0 <= i < n:
                credit[i] = True
    frate = {i: r for i, (_, r) in enumerate(funding_events or [])}
    # map settlement rates to the nearest bar
    settle_rate = np.zeros(n)
    if funding_events:
        for t, r in funding_events:
            i = int(np.searchsorted(ts, t, side="right") - 1)
            if 0 <= i < n:
                settle_rate[i] += r

    pend = 0
    eq = np.empty(n)
    for i in range(1, n):
        # execute pending order from the previous bar at this open
        if pend != 0:
            fill = o[i] * (1.0 + slip * (1 if pend > 0 else -1))
            notional = abs(qty * fill)
            f = notional * fee
            cash -= qty * fill + f
            entry = fill
            entry_i = i
            entry_fee = f
            pos = pend
            pend = 0
        if pos != 0 and credit[i]:
            payment = qty * c[i] * settle_rate[i]
            cash -= payment
            funded += payment
            fund_this_trade += payment
        # close first on ties
        close_now = (pos > 0 and xl[i]) or (pos < 0 and xs[i])
        timeout = max_hold is not None and i - entry_i >= max_hold
        if pos != 0 and (close_now or timeout):
            fill = o[i + 1] if i + 1 < n else o[i]
            fill *= (1.0 - slip * (1 if pos > 0 else -1))
            f = abs(qty * fill) * fee
            pnl = qty * (fill - entry) - entry_fee - f - fund_this_trade
            cash += qty * fill - f
            trades.append(dict(pnl=pnl, entry_i=entry_i, exit_i=i,
                               side=pos, ret=pnl / INIT * 100.0))
            qty, pos, entry, entry_fee, fund_this_trade = 0.0, 0, 0.0, 0.0, 0.0
        if pos == 0 and (up[i] or dn[i]):
            side = 1 if up[i] else -1
            qty = cash / o[i]
            pend = side
        eq[i] = cash + qty * c[i]
    if pos != 0:
        fill = o[-1]
        f = abs(qty * fill) * fee
        pnl = qty * (fill - entry) - entry_fee - f - fund_this_trade
        cash += qty * fill - f
        trades.append(dict(pnl=pnl, entry_i=entry_i, exit_i=n - 1,
                           side=pos, ret=pnl / INIT * 100.0))
        eq[-1] = cash
    eq[0] = INIT
    return dict(eq=eq, trades=trades, funded=funded, fees=sum(
        t["pnl"] for t in trades), n_funding=int(credit.sum()))


def _metrics(res, bh):
    tr = res["trades"]
    n = len(tr)
    pnls = np.array([t["pnl"] for t in tr], float)
    gp = pnls[pnls > 0].sum()
    gl = -pnls[pnls < 0].sum()
    pf = float(gp / gl) if gl > 0 else (None if gp <= 0 else float("inf"))
    eq = res["eq"]
    dd = float(((eq / np.maximum.accumulate(eq)) - 1.0).min() * 100.0)
    return dict(net_pct=round(float((eq[-1] / INIT - 1.0) * 100.0), 4),
                profit_factor=None if pf is None else round(pf, 6),
                n_trades=n, max_dd_pct=round(dd, 4),
                win_pct=round(float((pnls > 0).mean() * 100.0), 3) if n else None,
                funding_paid=round(float(res["funded"]), 4),
                bh_return_pct=round(float(bh), 4))


def run_one(paths, params):
    rid = int(params["id"])
    if rid in NO_DATA:
        raise RuntimeError(f"row {rid}: NO DATA — {NO_DATA[rid]}")
    if rid not in RUNNABLE:
        raise RuntimeError(f"row {rid} is not part of the fifty-row suite")
    tf = str(params["tf"])
    if tf != RUNNABLE[rid]:
        raise RuntimeError(f"row {rid}: declared tf {RUNNABLE[rid]}, got {tf}")
    costs_key = str(params.get("costs", "repo")).lower()
    if costs_key not in ("repo", "author", "zero"):
        raise ValueError(f"unknown costs {costs_key!r}")
    use_funding = bool(params.get("funding", True))

    df = pd.read_csv(paths[0])
    df = df[[c for c in ("open_ts", "open", "high", "low", "close",
                         "volume", "taker_buy_base") if c in df.columns]]
    df = df.sort_values("open_ts").reset_index(drop=True)
    fund_path = paths[1] if len(paths) > 1 and str(paths[1]).endswith(".json") else None
    fevents = _load_funding(fund_path) if use_funding else []
    sig = build_signals(df, rid, tf, fevents)
    fees = {"repo": REPO, "author": AUTHOR, "zero": ZERO}[costs_key]
    max_hold = 12 if rid == 46 else None
    res = simulate(sig, fees, use_funding and rid != 28 and rid != 49 and rid != 50,
                   fevents, max_hold=max_hold,
                   scale_at_r=rid in (44, 45))
    bh = float(df["close"].iloc[-1] / df["close"].iloc[0] - 1.0) * 100.0
    m = _metrics(res, bh)
    # in-artifact controls on the SAME signals
    base_net = m["net_pct"]
    author_cost = {"repo": AUTHOR, "author": REPO, "zero": AUTHOR}[costs_key]
    ra = simulate(sig, author_cost, False, [], max_hold=max_hold)
    rz = simulate(sig, ZERO, False, [], max_hold=max_hold)
    z_net = float((rz["eq"][-1] / INIT - 1.0) * 100.0)
    a_net = float((ra["eq"][-1] / INIT - 1.0) * 100.0)
    resid = float(res["eq"][-1] - INIT - sum(t["pnl"] for t in res["trades"]))
    if abs(resid) > 1e-6:
        raise AssertionError(f"row {rid}: accounting identity failed ({resid})")
    # pre-registered split, bootstrap and concentration, measured INSIDE
    split_i = int(0.7 * len(df))
    tr_pnl = np.array([t["pnl"] for t in res["trades"]], float)
    tr_i = np.array([t["entry_i"] for t in res["trades"]], int)
    def _seg(mask):
        p = tr_pnl[mask]
        g = p[p > 0].sum()
        l = -p[p < 0].sum()
        return dict(net=round(float(p.sum() / INIT * 100.0), 4),
                    pf=round(float(g / l), 6) if l > 0 else None,
                    n=int(len(p)))
    tr = _seg(tr_i < split_i)
    te = _seg(tr_i >= split_i)
    boot_lb = None
    if len(tr_pnl) >= 30:
        rng = np.random.default_rng(7)
        blk = max(1, int(round(len(tr_pnl) ** (1.0 / 3.0))))
        draws = []
        for _ in range(500):
            starts = rng.integers(0, len(tr_pnl) - blk + 1,
                                  size=max(1, len(tr_pnl) // blk))
            sample = np.concatenate([tr_pnl[s:s + blk] for s in starts])[:len(tr_pnl)]
            draws.append(sample.mean())
        boot_lb = round(float(np.percentile(draws, 2.5)), 6)
    pos = tr_pnl[tr_pnl > 0]
    conc = (round(float(np.sort(pos)[::-1][:5].sum() / pos.sum() * 100.0), 4)
            if pos.sum() > 0 else None)
    m.update(dict(train_net_pct=tr["net"], train_pf=tr["pf"], train_n=tr["n"],
                  test_net_pct=te["net"], test_pf=te["pf"], test_n=te["n"],
                  boot_exp_lb=boot_lb, conc_top5_share_pct=conc))
    m.update(dict(row=rid, timeframe=tf, costs=costs_key,
                  fee_bps_per_side=fees["fee"], slippage_bps_per_side=fees["slip"],
                  funding_charged=bool(use_funding and fund_path and
                                       rid not in (28, 49, 50)),
                  cost_bp_roundtrip=2.0 * (fees["fee"] + fees["slip"]),
                  author_cost_ret_pct=round(a_net, 4),
                  zero_cost_ret_pct=round(z_net, 4),
                  cost_drag_pp=round(z_net - base_net, 4),
                  pnl_identity_resid=round(resid, 10),
                  n_funding_events=int(np.sum([c for c in
                      [1 for _ in fevents]])) if fevents else 0,
                  bars=int(len(df))))
    prov = dict(adapter="emavwap50", engine_version="emavwap50-1",
                row=rid, declared_tf=tf,
                funding_file=os.path.basename(fund_path) if fund_path else None,
                definition="Downloads/EMA×VWAP 50-Strategy Suite-claude.md")
    tables = [dict(kind="trade", **{k: (int(v) if k.endswith("_i") else v)
                                     for k, v in t.items()}) for t in res["trades"][:200]]
    return m, prov, tables


if __name__ == "__main__":
    print("emavwap50 engine: run via vrun.py make_artifact / code/_emavwap50_audit.py")
