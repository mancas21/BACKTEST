#!/usr/bin/env python
"""pack50_core.py -- shared machinery for the fifty-strategy prompt pack.

Source spec: `Downloads/50_strategies_crypto-claude1.md` (50 numbered prompts).

WHY A SHARED CORE
    The pack is fifty variations on one execution model: a rule evaluated on a
    closed bar, a fill at the next bar's open, an intrabar stop/target, and
    perpetual funding charged while the position is open. Writing fifty separate
    simulators would mean fifty chances to get the fill convention wrong, so the
    fills live here once and each strategy only contributes its signal series.

CONVENTIONS (declared, used by every strategy in the pack)
    * Signals are computed on bar t from data through close(t); the fill is at
      open(t+1). No look-ahead.
    * A signal-driven exit also fills at open(t+1). Stops and targets fill
      intrabar at the level. If a bar's range contains BOTH the stop and the
      target, the STOP is filled first (SL-first on ties).
    * Costs: taker fee and slippage are charged PER SIDE in basis points, taken
      from the pack's own block (0.04% / 0.05% taker, 0.02% / 0.05% slippage).
      The repo gate (5.0 + 0.5 bps) is measured separately inside the artifact.
    * Sizing: full equity, no leverage, compounding. qty = equity / fill price.
      Pairs split equity 50/50 across the two legs.
    * Funding: charged at every settlement instant inside (entry, exit] on the
      open notional, sign-aware (long pays a positive rate, short receives it).
      Settlement price = close of the bar containing the settlement instant.
    * Buy & hold is the same window, first open to last close, no costs.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

BARS_PER_DAY = {"1m": 1440, "3m": 480, "5m": 288, "15m": 96, "30m": 48,
                "1h": 24, "4h": 6, "1d": 1}
BASE_TF = {"1m": ("binance_klines_1m_taker", "1m"),
           "3m": ("binance_klines_1m_taker", "1m"),
           "5m": ("binance_klines_5m_taker", "5m"),
           "15m": ("binance_klines_15m_taker", "15m"),
           "30m": ("binance_klines_15m_taker", "15m"),
           "1h": ("binance_klines_1h_taker", "1h"),
           "4h": ("binance_klines_1h_taker", "1h"),
           "1d": ("binance_klines_1h_taker", "1h")}
RULE = {"1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min",
        "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}


# ══════════════════════════════════════════════════════════ data
def load_tf(path: str, tf: str) -> pd.DataFrame:
    """Load a CSV and, when the file is at a finer base timeframe, resample it."""
    d = pd.read_csv(path)
    cols = {c.lower(): c for c in d.columns}
    d = d.rename(columns={cols[k]: k for k in cols if k in
                          ("open_ts", "open", "high", "low", "close", "volume",
                           "taker_buy_base", "taker_buy_quote", "n_trades")})
    d["ts"] = pd.to_datetime(d["open_ts"], unit="ms", utc=True)
    d = d.sort_values("ts").reset_index(drop=True)
    if "taker_buy_base" not in d.columns:
        d["taker_buy_base"] = np.nan

    base_dir, base_tf = BASE_TF[tf]
    needed = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
              "1h": 60, "4h": 240, "1d": 1440}[tf]
    have = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}[base_tf]
    if needed == have:
        return d

    # Resample on the UTC epoch grid so sessions align across symbols.
    rule = RULE[tf]
    agg = {"open": "first", "high": "max", "low": "min", "close": "last",
           "volume": "sum", "n_trades": "sum"}
    if d["taker_buy_base"].notna().any():
        agg["taker_buy_base"] = "sum"
    g = (d.set_index("ts").resample(rule, label="left", closed="left")
          .agg({k: v for k, v in agg.items() if k in d.columns}).dropna(subset=["open"]))
    g = g.reset_index()
    # `astype("int64")` on a tz-aware column returns the column's own unit
    # (ms or us depending on pandas), so derive the epoch explicitly.
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    g["open_ts"] = ((g["ts"] - epoch) // pd.Timedelta(milliseconds=1)).astype("int64")
    return g


def load_funding(path: str | None):
    """Return (timestamps_ms int64 array, rates float array) or (empty, empty)."""
    if not path or not os.path.exists(path):
        return np.array([], dtype=np.int64), np.array([], dtype=float)
    raw = json.load(open(path, encoding="utf-8"))
    ts = np.array([int(r["t"]) for r in raw], dtype=np.int64)
    rt = np.array([float(r["r"]) for r in raw], dtype=float)
    order = np.argsort(ts)
    return ts[order], rt[order]


# ══════════════════════════════════════════════════════════ indicators
def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def rma(x, n):
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def atr(h, l, c, n=14):
    h, l, c = map(np.asarray, (h, l, c))
    pc = np.concatenate(([np.nan], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return rma(tr, n)


def rsi(c, n=14):
    c = np.asarray(c, dtype=float)
    d = np.diff(c, prepend=c[0])
    up = rma(np.where(d > 0, d, 0.0), n)
    dn = rma(np.where(d < 0, -d, 0.0), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = up / dn
    return 100.0 - 100.0 / (1.0 + rs)


def true_range(h, l, c):
    h, l, c = map(np.asarray, (h, l, c))
    pc = np.concatenate(([np.nan], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return tr


def adx_di(h, l, c, n=14):
    h, l, c = map(np.asarray, (h, l, c))
    up = np.diff(h, prepend=h[0])
    dn = -np.diff(l, prepend=l[0])
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = rma(true_range(h, l, c), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100.0 * rma(plus_dm, n) / tr
        mdi = 100.0 * rma(minus_dm, n) / tr
        dx = 100.0 * np.abs(pdi - mdi) / (pdi + mdi)
    return rma(dx, n), pdi, mdi


def macd(c, fast=12, slow=26, sig=9):
    f, s = ema(c, fast), ema(c, slow)
    m = f - s
    sg = pd.Series(m).ewm(span=sig, adjust=False, min_periods=sig).mean().to_numpy()
    return m, sg, m - sg


def bollinger(c, n=20, k=2.0):
    s = pd.Series(c)
    mid = s.rolling(n, min_periods=n).mean()
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    return (mid - k * sd).to_numpy(), mid.to_numpy(), (mid + k * sd).to_numpy()


def keltner(h, l, c, n=20, k=1.5, atr_n=10):
    mid = ema(c, n)
    a = atr(h, l, c, atr_n)
    return mid - k * a, mid, mid + k * a


def donchian(h, l, n):
    """Rolling max of the PRIOR n bars (shifted by one so the current bar cannot
    be its own breakout level)."""
    hh = pd.Series(h).rolling(n, min_periods=n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n, min_periods=n).min().shift(1).to_numpy()
    return hh, ll


def hma(x, n):
    def wma(v, m):
        w = np.arange(1, m + 1, dtype=float)
        return pd.Series(v).rolling(m, min_periods=m).apply(
            lambda q: float(np.dot(q, w) / w.sum()), raw=True).to_numpy()
    half = max(2, int(n / 2))
    root = max(1, int(np.sqrt(n)))
    a, b = wma(x, half), wma(x, n)
    raw = 2 * a - b
    return wma(raw, root)


def psar(h, l, step=0.02, mx=0.2):
    h, l = np.asarray(h, float), np.asarray(l, float)
    n = len(h)
    out = np.full(n, np.nan)
    if n < 3:
        return out
    up = h[1] >= h[0]
    af = step
    ep = h[1] if up else l[1]
    sar = l[0] if up else h[0]
    for i in range(2, n):
        sar = sar + af * (ep - sar)
        if up:
            sar = min(sar, l[i - 1], l[i - 2])
            if h[i] > ep:
                ep, af = h[i], min(af + step, mx)
            if l[i] < sar:
                up, sar, ep, af = False, ep, l[i], step
        else:
            sar = max(sar, h[i - 1], h[i - 2])
            if l[i] < ep:
                ep, af = l[i], min(af + step, mx)
            if h[i] > sar:
                up, sar, ep, af = True, ep, h[i], step
        out[i] = sar
    return out


def supertrend(h, l, c, period=10, mult=2.0):
    h, l, c = map(np.asarray, (h, l, c))
    a = atr(h, l, c, period)
    hl2 = (h + l) / 2.0
    upper, lower = hl2 + mult * a, hl2 - mult * a
    n = len(c)
    trend = np.zeros(n, dtype=int)
    line = np.full(n, np.nan)
    fu, fl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(1, n):
        if np.isnan(a[i]):
            continue
        fu[i] = upper[i] if (np.isnan(fu[i - 1]) or upper[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lower[i] if (np.isnan(fl[i - 1]) or lower[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if np.isnan(fu[i - 1]):
            trend[i], line[i] = 1, fl[i]
        elif trend[i - 1] == 1:
            trend[i] = -1 if c[i] < fl[i] else 1
            line[i] = fu[i] if trend[i] == -1 else fl[i]
        else:
            trend[i] = 1 if c[i] > fu[i] else -1
            line[i] = fl[i] if trend[i] == 1 else fu[i]
    return trend, line


def williams_r(h, l, c, n=14):
    hh = pd.Series(h).rolling(n, min_periods=n).max().to_numpy()
    ll = pd.Series(l).rolling(n, min_periods=n).min().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return -100.0 * (hh - np.asarray(c)) / (hh - ll)


def stoch_rsi(c, n=14, k=3, d=3):
    r = pd.Series(rsi(c, n))
    lo = r.rolling(n, min_periods=n).min()
    hi = r.rolling(n, min_periods=n).max()
    with np.errstate(divide="ignore", invalid="ignore"):
        st = 100.0 * (r - lo) / (hi - lo)
    kk = st.rolling(k, min_periods=k).mean().to_numpy()
    dd = pd.Series(kk).rolling(d, min_periods=d).mean().to_numpy()
    return kk, dd


def rolling_z(x, n):
    s = pd.Series(np.asarray(x, float))
    m = s.rolling(n, min_periods=n).mean()
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return ((s - m) / sd).to_numpy()


def session_vwap(df, tf):
    """UTC-session VWAP and the session-to-date std of (close - vwap)."""
    ts = pd.to_datetime(df["ts"], utc=True)
    day = ts.dt.floor("1D")
    tp = (df["high"].to_numpy() + df["low"].to_numpy() + df["close"].to_numpy()) / 3.0
    vol = df["volume"].to_numpy()
    pv = pd.Series(tp * vol).groupby(day).cumsum().to_numpy()
    vv = pd.Series(vol).groupby(day).cumsum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = pv / vv
    dev = df["close"].to_numpy() - vwap
    cnt = pd.Series(1).groupby(day).cumsum().to_numpy()
    mean = pd.Series(dev).groupby(day).cumsum().to_numpy() / cnt
    var = (pd.Series(dev ** 2).groupby(day).cumsum().to_numpy() / cnt) - mean ** 2
    sd = np.sqrt(np.maximum(var, 0))
    return vwap, sd


def heikin_ashi(o, h, l, c):
    o, h, l, c = map(np.asarray, (o, h, l, c))
    n = len(c)
    ha_c = (o + h + l + c) / 4.0
    ha_o = np.full(n, np.nan)
    ha_o[0] = (o[0] + c[0]) / 2.0
    for i in range(1, n):
        ha_o[i] = (ha_o[i - 1] + ha_c[i - 1]) / 2.0
    ha_h = np.maximum(np.maximum(h, ha_o), ha_c)
    ha_l = np.minimum(np.minimum(l, ha_o), ha_c)
    return ha_o, ha_h, ha_l, ha_c


def rolling_hurst(c, window=200):
    """Aggregated-variance Hurst estimate on log returns inside each window.

    H = 0.5 * slope of log(var of k-bar returns) vs log(k), for k = 1,2,4,8.
    A trending series gives H > 0.5, a mean-reverting one H < 0.5.
    """
    r = np.diff(np.log(np.asarray(c, float)), prepend=np.log(np.asarray(c, float)[0]))
    n = len(r)
    H = np.full(n, np.nan)
    ks = [1, 2, 4, 8]
    x = np.log(np.array(ks, float))
    xm = x.mean()
    denom = ((x - xm) ** 2).sum()
    for i in range(window, n):
        w = r[i - window + 1:i + 1]
        logs = []
        ok = True
        for k in ks:
            if len(w) < k * 8:
                ok = False
                break
            kk = len(w) // k
            agg = w[:kk * k].reshape(kk, k).sum(axis=1)
            v = agg.var()
            if v <= 0:
                ok = False
                break
            logs.append(np.log(v))
        if not ok:
            continue
        y = np.array(logs)
        slope = ((x - xm) * (y - y.mean())).sum() / denom
        H[i] = slope / 2.0
    return H


def realized_vol(c, n=20):
    r = np.diff(np.log(np.asarray(c, float)), prepend=np.log(np.asarray(c, float)[0]))
    return pd.Series(r).rolling(n, min_periods=n).std(ddof=0).to_numpy()


def rank_pct_within(x, lookback=200):
    """Percentile rank (0..1) of the latest value inside the trailing lookback."""
    s = pd.Series(np.asarray(x, float))
    return s.rolling(lookback, min_periods=lookback).apply(
        lambda w: float((w <= w[-1]).mean()), raw=True).to_numpy()


# ══════════════════════════════════════════════════════════ execution
@dataclass
class Plan:
    """Signal plan for one strategy on one symbol.

    All arrays are aligned to the bars. Entry/exit booleans are evaluated at the
    close of that bar; `stop_long`/`stop_short`/`tp_long`/`tp_short` are PRICE
    levels (NaN = no level). `time_stop` is in bars.
    """
    long_entry: np.ndarray
    short_entry: np.ndarray
    long_exit: np.ndarray
    short_exit: np.ndarray
    stop_long: np.ndarray | None = None
    stop_short: np.ndarray | None = None
    tp_long: np.ndarray | None = None
    tp_short: np.ndarray | None = None
    time_stop: int | None = None
    one_per_day: bool = False
    size_frac: float = 1.0
    note: str = ""


@dataclass
class Costs:
    fee_bps: float
    slip_bps: float


@dataclass
class Trades:
    rows: list = field(default_factory=list)

    def add(self, **kw):
        self.rows.append(kw)

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def _nan_array(n):
    return np.full(n, np.nan)


def _apply_slip(px, side, is_entry, slip_bps):
    s = slip_bps / 1e4
    # A buy always pays up, a sell always gives up.
    buy = (side > 0 and is_entry) or (side < 0 and not is_entry)
    return px * (1 + s) if buy else px * (1 - s)


def _funding_due(f_ts, f_rate, t0, t1):
    if len(f_ts) == 0:
        return 0.0, 0
    lo = np.searchsorted(f_ts, t0, side="right")
    hi = np.searchsorted(f_ts, t1, side="right")
    if hi <= lo:
        return 0.0, 0
    return float(f_rate[lo:hi].sum()), int(hi - lo)


def _funding_cash(f_ts, f_rate, t0, t1, bar_ts, close, qty, side):
    """Signed cash cost of funding for a fixed-size position.

    Each settlement is priced at the close of the bar that CONTAINS it, so a
    settlement is charged on the notional actually open at that moment rather
    than on the exit price of the trade.
    """
    if len(f_ts) == 0:
        return 0.0, 0
    lo = np.searchsorted(f_ts, t0, side="right")
    hi = np.searchsorted(f_ts, t1, side="right")
    if hi <= lo:
        return 0.0, 0
    idx = np.searchsorted(bar_ts, f_ts[lo:hi], side="right") - 1
    idx = np.clip(idx, 0, len(close) - 1)
    px = close[idx]
    cash = -side * qty * float((px * f_rate[lo:hi]).sum())
    return cash, int(hi - lo)


def _funding_cash_notional(f_ts, f_rate, t0, t1, bar_ts, close, notional, side):
    """Same, for a book whose notional is marked in equity terms (pair legs)."""
    if len(f_ts) == 0:
        return 0.0, 0
    lo = np.searchsorted(f_ts, t0, side="right")
    hi = np.searchsorted(f_ts, t1, side="right")
    if hi <= lo:
        return 0.0, 0
    idx = np.searchsorted(bar_ts, f_ts[lo:hi], side="right") - 1
    idx = np.clip(idx, 0, len(close) - 1)
    px = close[idx]
    ref = close[max(idx[0] - 1, 0)]
    cash = -side * notional * float((px / ref * f_rate[lo:hi]).sum())
    return cash, int(hi - lo)


def run_plan(df: pd.DataFrame, plan: Plan, costs: Costs, funding=None,
             init_equity=10000.0) -> dict:
    """Execute one plan. Returns {'trades': DataFrame, 'equity': array}."""
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = (df["open_ts"].to_numpy(np.int64) if "open_ts" in df.columns
          else (df["ts"].astype("int64") // 10**6).to_numpy(np.int64))
    n = len(df)
    ts_dt = pd.to_datetime(ts, unit="ms", utc=True)
    f_ts, f_rate = funding if funding is not None else (np.array([], np.int64), np.array([], float))

    le, se = plan.long_entry, plan.short_entry
    lx, sx = plan.long_exit, plan.short_exit
    sl = plan.stop_long if plan.stop_long is not None else _nan_array(n)
    ss = plan.stop_short if plan.stop_short is not None else _nan_array(n)
    tl = plan.tp_long if plan.tp_long is not None else _nan_array(n)
    ts_ = plan.tp_short if plan.tp_short is not None else _nan_array(n)

    eq = init_equity
    trades = Trades()
    curve = np.full(n, init_equity)
    pos = 0                 # 0 flat, +1 long, -1 short
    qty = 0.0
    entry_px = 0.0
    entry_i = -1
    entry_ts = 0
    cur_stop = np.nan
    cur_tp = np.nan
    pend_entry = 0
    pend_exit = False
    last_entry_day = None
    entry_fee_cur = 0.0
    funding_paid = 0.0
    fees_paid = 0.0
    day = ts_dt.floor("1D").to_numpy()

    for i in range(n):
        # ---- 1. act on yesterday's decision at today's open
        if pos != 0 and pend_exit:
            px = _apply_slip(o[i], pos, False, costs.slip_bps)
            pnl_gross = pos * qty * (px - entry_px)
            fee = qty * abs(px) * costs.fee_bps / 1e4
            fund_cash, nf = _funding_cash(f_ts, f_rate, entry_ts, int(ts[i]), ts, c, qty, pos)
            pnl_eq = pnl_gross - fee + fund_cash
            pnl = pnl_eq - entry_fee_cur
            eq_before = eq
            eq += pnl_eq
            fees_paid += fee
            funding_paid += -fund_cash
            trades.add(entry_ts=entry_ts, exit_ts=int(ts[i]), side=pos,
                       entry_px=entry_px, exit_px=px, qty=qty,
                       pnl=pnl, ret_pct=100.0 * pnl / max(eq_before, 1e-9),
                       bars=i - entry_i, exit_reason="signal",
                       fees=fee + entry_fee_cur, funding=fund_cash, n_funding=nf,
                       equity_after=eq)
            pos, qty, pend_exit = 0, 0.0, False

        if pos == 0 and pend_entry != 0:
            side = pend_entry
            px = _apply_slip(o[i], side, True, costs.slip_bps)
            q = (eq * plan.size_frac) / px
            fee = q * px * costs.fee_bps / 1e4
            eq -= fee
            fees_paid += fee
            entry_fee_cur = fee
            pos, qty, entry_px, entry_i, entry_ts = side, q, px, i, int(ts[i])
            cur_stop = sl[i - 1] if side > 0 else ss[i - 1]
            cur_tp = tl[i - 1] if side > 0 else ts_[i - 1]
            last_entry_day = day[i]
            pend_entry = 0

        # ---- 2. intrabar stop / target on the open position
        if pos != 0:
            if pos > 0:
                hit_stop = (not np.isnan(cur_stop)) and l[i] <= cur_stop
                hit_tp = (not np.isnan(cur_tp)) and h[i] >= cur_tp
            else:
                hit_stop = (not np.isnan(cur_stop)) and h[i] >= cur_stop
                hit_tp = (not np.isnan(cur_tp)) and l[i] <= cur_tp
            # SL-first on ties: the stop wins whenever both are inside the bar.
            if hit_stop or hit_tp:
                lvl, why = (cur_stop, "stop") if hit_stop else (cur_tp, "target")
                px = _apply_slip(lvl, pos, False, costs.slip_bps)
                pnl_gross = pos * qty * (px - entry_px)
                fee = qty * abs(px) * costs.fee_bps / 1e4
                fund_cash, nf = _funding_cash(f_ts, f_rate, entry_ts, int(ts[i]), ts, c, qty, pos)
                pnl_eq = pnl_gross - fee + fund_cash
                pnl = pnl_eq - entry_fee_cur
                eq_before = eq
                eq += pnl_eq
                fees_paid += fee
                funding_paid += -fund_cash
                trades.add(entry_ts=entry_ts, exit_ts=int(ts[i]), side=pos,
                           entry_px=entry_px, exit_px=px, qty=qty,
                           pnl=pnl, ret_pct=100.0 * pnl / max(eq_before, 1e-9),
                           bars=i - entry_i, exit_reason=why,
                           fees=fee + entry_fee_cur, funding=fund_cash, n_funding=nf,
                           equity_after=eq)
                pos, qty = 0, 0.0

        # ---- 3. time stop (decided at this close, filled next open)
        if pos != 0 and plan.time_stop and (i - entry_i) >= plan.time_stop:
            pend_exit = True

        # ---- 4. decisions at this close
        if pos != 0 and not pend_exit:
            if (pos > 0 and lx[i]) or (pos < 0 and sx[i]):
                pend_exit = True
        if pos == 0 and not pend_exit and pend_entry == 0:
            ok_day = True
            if plan.one_per_day and last_entry_day is not None:
                ok_day = day[i] != last_entry_day
            if ok_day:
                if le[i] and not se[i]:
                    pend_entry = 1
                elif se[i] and not le[i]:
                    pend_entry = -1

        # ---- 5. mark to market
        curve[i] = eq + (pos * qty * (c[i] - entry_px) if pos != 0 else 0.0)

    if pos != 0:   # close the tail at the last close, no slippage on the mark
        px = c[-1]
        pnl_gross = pos * qty * (px - entry_px)
        fee = qty * abs(px) * costs.fee_bps / 1e4
        fund_cash, nf = _funding_cash(f_ts, f_rate, entry_ts, int(ts[-1]), ts, c, qty, pos)
        pnl_eq = pnl_gross - fee + fund_cash
        pnl = pnl_eq - entry_fee_cur
        eq_before = eq
        eq += pnl_eq
        fees_paid += fee
        funding_paid += -fund_cash
        trades.add(entry_ts=entry_ts, exit_ts=int(ts[-1]), side=pos,
                   entry_px=entry_px, exit_px=px, qty=qty, pnl=pnl,
                   ret_pct=100.0 * pnl / max(eq_before, 1e-9),
                   bars=len(c) - 1 - entry_i, exit_reason="end_of_data",
                   fees=fee + entry_fee_cur, funding=fund_cash, n_funding=nf,
                   equity_after=eq)
        curve[-1] = eq

    return {"trades": trades.frame(), "equity": curve, "fees": fees_paid,
            "funding": funding_paid, "final_equity": eq}


# ══════════════════════════════════════════════════════════ metrics
def profit_factor(pnl: np.ndarray) -> float:
    if len(pnl) == 0:
        return 0.0
    g = float(pnl[pnl > 0].sum())
    l = float(-pnl[pnl < 0].sum())
    if l <= 0:
        return float("inf") if g > 0 else 0.0
    return g / l


def _finite(x):
    """A ratio with no denominator is not a number; it must not be printed as
    one. `None` here means 'undefined', and the report says so in words."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def max_drawdown_pct(curve: np.ndarray) -> float:
    if len(curve) == 0:
        return 0.0
    peak = np.maximum.accumulate(curve)
    dd = (curve - peak) / np.where(peak > 0, peak, 1.0)
    return float(-100.0 * dd.min())


def summarise(tr: pd.DataFrame, curve: np.ndarray, init=10000.0) -> dict:
    n = len(tr)
    out = {
        "n_trades": int(n),
        "return_pct": float(100.0 * (curve[-1] / init - 1.0)),
        "max_dd_pct": max_drawdown_pct(curve),
        "final_equity": float(curve[-1]),
    }
    if n == 0:
        out.update(profit_factor=0.0, win_rate=0.0, avg_trade_pct=0.0,
                   expectancy_R=0.0, conc_top5_share_pct=0.0,
                   conc_net_without_top5_pct=0.0, funding_paid=0.0, fees_paid=0.0)
        return out
    pnl = tr["pnl"].to_numpy(float)
    pf = profit_factor(pnl)
    out["pf_no_losses"] = bool(not np.isfinite(pf) and pnl.sum() > 0)
    out["profit_factor"] = _finite(pf)
    out["win_rate"] = float(100.0 * (pnl > 0).mean())
    out["avg_trade_pct"] = float(tr["ret_pct"].mean())
    loss = -pnl[pnl < 0]
    wins = pnl[pnl > 0]
    out["expectancy_R"] = (_finite(wins.mean() / loss.mean())
                           if len(wins) and len(loss) and loss.mean() > 0 else 0.0)
    s = np.sort(pnl)[::-1]
    tot = pnl.sum()
    out["conc_top5_share_pct"] = float(100.0 * s[:5].sum() / tot) if tot != 0 else 0.0
    out["conc_net_without_top5_pct"] = float(100.0 * (tot - s[:5].sum()) / init)
    out["funding_paid"] = float(tr["funding"].sum())
    out["fees_paid"] = float(tr["fees"].sum())
    return out


def split_metrics(tr: pd.DataFrame, split_ts: int, init=10000.0) -> dict:
    """70/30 in-sample / out-of-sample, split on the ENTRY timestamp."""
    if len(tr) == 0:
        return {"is_n": 0, "os_n": 0, "is_pf": 0.0, "os_pf": 0.0,
                "is_ret_pct": 0.0, "os_ret_pct": 0.0}
    ins = tr[tr["entry_ts"] < split_ts]
    oos = tr[tr["entry_ts"] >= split_ts]
    return {
        "is_n": int(len(ins)), "os_n": int(len(oos)),
        "is_pf": _finite(profit_factor(ins["pnl"].to_numpy(float))),
        "os_pf": _finite(profit_factor(oos["pnl"].to_numpy(float))),
        "is_ret_pct": float(100.0 * ins["pnl"].sum() / init),
        "os_ret_pct": float(100.0 * oos["pnl"].sum() / init),
    }


def buy_and_hold(df: pd.DataFrame, split_frac=0.7) -> dict:
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(c)
    first = int(n * split_frac)
    tot = 100.0 * (c[-1] / o[0] - 1.0)
    # B&H over the OOS slice only, entered at the first open of that slice.
    oos = 100.0 * (c[-1] / o[first] - 1.0) if first < n else 0.0
    return {"bh_return_pct": float(tot), "bh_oos_return_pct": float(oos),
            "bh_max_dd_pct": max_drawdown_pct(c)}


def buy_and_hold_pair(df_a: pd.DataFrame, df_b: pd.DataFrame) -> dict:
    """Equal-weight buy & hold of the two legs, plus each leg on its own.

    A dollar-neutral book is judged against the pair it is trading, not against
    one leg, so the equal-weight number is the benchmark and the single-leg
    numbers are reported next to it.
    """
    ca = df_a["close"].to_numpy(float)
    cb = df_b["close"].to_numpy(float)
    oa = df_a["open"].to_numpy(float)
    ob = df_b["open"].to_numpy(float)
    n = min(len(ca), len(cb))
    ra = ca[n - 1] / oa[0] - 1.0
    rb = cb[n - 1] / ob[0] - 1.0
    eq = 0.5 * (1.0 + ra) + 0.5 * (1.0 + rb) - 1.0
    curve = 0.5 * (ca[:n] / oa[0]) + 0.5 * (cb[:n] / ob[0])
    return {"bh_return_pct": float(100.0 * eq),
            "bh_leg_a_return_pct": float(100.0 * ra),
            "bh_leg_b_return_pct": float(100.0 * rb),
            "bh_max_dd_pct": max_drawdown_pct(curve)}


# ══════════════════════════════════════════════════════════ pairs
def run_pair(df_a: pd.DataFrame, df_b: pd.DataFrame, target: np.ndarray,
             costs: Costs, fund_a=None, fund_b=None, init_equity=10000.0,
             leg_frac: float = 0.5) -> dict:
    """Dollar-neutral two-leg book marked close-to-close.

    `target[i]` is the wanted position +1 (long A / short B) or -1 or 0, decided
    on the close of bar i and executed at the open of bar i+1. Each leg carries
    `leg_frac` of equity, so the book is dollar-neutral by construction. Fees and
    slippage are charged on BOTH legs at every change; funding is charged on both
    legs at each settlement inside the holding period.
    """
    a = df_a.reset_index(drop=True)
    b = df_b.reset_index(drop=True)
    n = min(len(a), len(b))
    a, b = a.iloc[:n], b.iloc[:n]
    ca, cb = a["close"].to_numpy(float), b["close"].to_numpy(float)
    oa, ob = a["open"].to_numpy(float), b["open"].to_numpy(float)
    tsa = (a["open_ts"] if "open_ts" in a else a["ts"].astype("int64") // 10**6).to_numpy(np.int64)
    fa_ts, fa_r = fund_a if fund_a else (np.array([], np.int64), np.array([], float))
    fb_ts, fb_r = fund_b if fund_b else (np.array([], np.int64), np.array([], float))

    eq = init_equity
    curve = np.full(n, init_equity)
    pos = 0
    entry_i = -1
    entry_ts = 0
    eq_open = init_equity
    cost_in = 0.0
    fees_paid = 0.0
    funding_paid = 0.0
    rows = []
    cost_rate = (costs.fee_bps + costs.slip_bps) / 1e4   # per leg, per side
    pend = 0
    have_pend = False
    if n > 0 and target[0] != 0:
        pend, have_pend = int(target[0]), True

    for i in range(1, n):
        # execute a change decided at i-1, at this open
        if have_pend and pend != pos:
            if pos != 0:
                # unwind the old book at this open, then charge its funding
                ret_a = oa[i] / ca[i - 1] - 1.0
                ret_b = ob[i] / cb[i - 1] - 1.0
                pnl = eq * leg_frac * pos * (ret_a - ret_b)
                eq += pnl
                cost = eq * leg_frac * 2 * cost_rate
                eq -= cost
                fees_paid += cost
                fa_c, nfa = _funding_cash_notional(fa_ts, fa_r, entry_ts, int(tsa[i]), tsa, ca, eq * leg_frac, pos)
                fb_c, nfb = _funding_cash_notional(fb_ts, fb_r, entry_ts, int(tsa[i]), tsa, cb, eq * leg_frac, -pos)
                fcash = fa_c + fb_c
                eq += fcash
                funding_paid += -fcash
                seg = eq - eq_open
                rows.append(dict(entry_ts=entry_ts, exit_ts=int(tsa[i]), side=pos,
                                 entry_px=float(ca[entry_i]), exit_px=float(ca[i]),
                                 qty=eq * leg_frac / max(ca[entry_i], 1e-12),
                                 pnl=seg, ret_pct=100.0 * seg / max(eq_open, 1e-9),
                                 bars=i - entry_i, exit_reason="rebalance",
                                 fees=cost + cost_in, funding=fcash,
                                 n_funding=nfa + nfb, equity_after=eq))
                pos = 0
            if pend != 0:
                cost = eq * leg_frac * 2 * cost_rate
                eq -= cost
                fees_paid += cost
                pos, entry_i, entry_ts = pend, i, int(tsa[i])
                eq_open = eq + cost      # the segment must carry its entry cost
                cost_in = cost
            have_pend = False

        # mark to market; a book opened on this bar earns from its own fill
        if pos != 0:
            if entry_i == i:
                ret_a = ca[i] / oa[i] - 1.0
                ret_b = cb[i] / ob[i] - 1.0
            else:
                ret_a = ca[i] / ca[i - 1] - 1.0
                ret_b = cb[i] / cb[i - 1] - 1.0
            eq *= (1.0 + leg_frac * pos * (ret_a - ret_b))
        curve[i] = eq

        if target[i] != pos:
            pend, have_pend = int(target[i]), True

    if pos != 0:
        fa_c, nfa = _funding_cash_notional(fa_ts, fa_r, entry_ts, int(tsa[-1]), tsa, ca, eq * leg_frac, pos)
        fb_c, nfb = _funding_cash_notional(fb_ts, fb_r, entry_ts, int(tsa[-1]), tsa, cb, eq * leg_frac, -pos)
        fcash = fa_c + fb_c
        cost = eq * leg_frac * 2 * cost_rate
        eq += fcash - cost
        funding_paid += -fcash
        fees_paid += cost
        seg = eq - eq_open
        rows.append(dict(entry_ts=entry_ts, exit_ts=int(tsa[-1]), side=pos,
                         entry_px=float(ca[entry_i]), exit_px=float(ca[-1]),
                         qty=eq * leg_frac / max(ca[entry_i], 1e-12),
                         pnl=seg, ret_pct=100.0 * seg / max(eq_open, 1e-9),
                         bars=n - 1 - entry_i, exit_reason="end_of_data",
                         fees=cost + cost_in, funding=fcash, n_funding=nfa + nfb,
                         equity_after=eq))
        curve[-1] = eq

    tr = pd.DataFrame(rows)
    return {"trades": tr, "equity": curve, "fees": fees_paid,
            "funding": funding_paid, "final_equity": eq}
