#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""emaadx_engine.py — port of deepseek_pinescript_20261022_c2f363.txt:
"EMA Cross + ADX Strategy [Quant]" (Pine v6, delivered 2026-10-22).

THE PINE, READ END TO END
    strategy(...) with initial_capital 10000, 100% of equity per entry,
    commission 0.05% (taker) per fill, slippage = 1 tick,
    pyramiding = 0, process_orders_on_close = TRUE.

    LONG   ta.crossover(ema20, ema50) and adx >= 25 and diPlus > diMinus
    SHORT  ta.crossunder(ema20, ema50) and adx >= 25 and diMinus > diPlus
    SL/TP  fixed at the SIGNAL bar from THAT bar's close and ATR(14):
           SL = close -/+ 2.0*atr, TP = close +/- 2.0*atr*2.0 (rr=2.0).
           Brackets are attached whenever a position exists (strategy.exit with
           stop and limit), evaluated INTRABAR on later bars.
    Date filter default OFF (inDate always true for us).

PINE SEMANTICS THAT NEED CARE
    - process_orders_on_close = true means a signal bar's order fills at THAT
      bar's close (not the next open -- this is the author's convention and the
      port keeps it; it differs from the next-open convention of other ports).
    - The bracket anchors use the SIGNAL bar's close/ATR. With same-bar-close
      fills the fill price equals close +/- slippage ticks, so with zero
      slippage anchor == fill.
    - Pine trap reproduced faithfully: the `var float longSLPrice := ...`
      assignments run on EVERY signal bar, even when pyramiding=0 rejects the
      duplicate entry -- so same-direction signals while already long RE-SET
      the brackets (no size change). Port does the same.
    - Reversal: an opposite-direction entry while positioned fills at that
      close and takes the fee on the whole order quantity (old exit + new
      entry, identical either way you decompose it).
    - Stop-first on ties: a bar that spans both SL and TP resolves at SL.
    - Stops fill with adverse slippage ticks; limit fills fill at the limit
      price (TradingView applies slippage to market-type fills only).
    - `not na` is TRUE, na comparisons are falsy: warmup bars cannot signal
      (ADX/DMI are na until ~28 bars; EMAs are gated by min_periods=n, the
      dry-and-reproducible head choice -- an arbitrarily seeded EMA at the
      first recorded bar would otherwise depend on data outside our hash).
    - Unfinished position at the end of data: marked to the last close,
      EXCLUDED from closed-trade statistics (one open trade reported).

COSTS
    author : 0.05% commission per fill + the header's literal 1-tick
             slippage, which on these series is ~1e-4 bps -- declared zero
             with that statement. (The adxhma precedent: judge nothing on the
             flattering version alone.)
    repo6x5: 6 bps commission + 5 bps slippage per fill (repo standard).
    zero   : control pass inside the artifact; drag_pp = ret_zero - ret_cost.

PRIMITIVES
    rma, true_range, atr_pine, fixnan and dmi_pine are copied byte-for-byte in
    spirit from code/adxhma_strategy.py, whose self-test validated them
    (SMA-seeded rma with leading-na skipping -- the all-NaN ADX bug note).
    ema = pandas ewm(span, adjust=False, min_periods=n), the cbpack audited
    convention. All are re-asserted here by code/_emaadx_audit.py before any
    real-data run.
"""

import json
import os
import sys
from collections import defaultdict
import datetime as dt

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INIT = 10000.0

WARMUP_6MO = 600        # warmup bars before the scored tail of window last6mo
SCORED_6MO = 4368       # scored bars of the last6mo window

# The Pine's inputs, as shipped (no --set can widen the strategy geometry; the
# strategy itself is audited as fixed; only costs and window are CLI knobs).
PINE = dict(
    ema_fast_len=20, ema_slow_len=50,
    adx_len=14, adx_smooth=14, adx_threshold=25.0, use_di=True,
    use_sl=True, atr_len=14, atr_mult=2.0,
    use_tp=True, rr_ratio=2.0,
    allow_long=True, allow_short=True,
    use_date=False,
)
TICK_SLIP = 0.0          # header slippage = 1 tick, declared zero (see docstring)

COSTS = {
    "author": dict(fee=0.0005, slip=TICK_SLIP),
    "repo6x5": dict(fee=0.0006, slip=0.0005),
    "zero": dict(fee=0.0, slip=0.0),
}


# ------------------------------------------------------------- indicators
def ema(x, n):
    """Pine ta.ema gated to full length (min_periods=n), pandas convention."""
    import pandas as pd
    return pd.Series(np.asarray(x, float)).ewm(
        span=n, adjust=False, min_periods=n).mean().to_numpy()


def rma(x, n):
    """Wilder smoothing, SMA-seeded like Pine's ta.rma; leading na skipped."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    buf, prev = [], np.nan
    seeded = False
    for i in range(len(x)):
        xi = x[i]
        if not seeded:
            if not np.isnan(xi):
                buf.append(xi)
                if len(buf) == n:
                    prev = float(np.mean(buf))
                    out[i] = prev
                    seeded = True
        else:
            if np.isnan(xi):
                out[i] = prev           # Pine holds the last value on na input
            else:
                prev = (prev * (n - 1) + xi) / n
                out[i] = prev
    return out


def true_range(h, l, c):
    pc = np.roll(c, 1)
    pc[0] = np.nan
    a = h - l
    b = np.abs(h - pc)
    d = np.abs(l - pc)
    # fmax ignores NaN votes pairwise: identical to nanmax of the stack, no warning
    return np.fmax(a, np.fmax(b, d))


def atr_pine(h, l, c, n):
    return rma(true_range(h, l, c), n)


def fixnan(x):
    out = np.array(x, float)
    last = np.nan
    for i in range(len(out)):
        if np.isnan(out[i]):
            out[i] = last
        else:
            last = out[i]
    return out


def dmi_pine(h, l, c, di_len, smooth):
    """Pine ta.dmi -> (diPlus, diMinus, adx). Wilder, RMA everywhere."""
    up = np.full(len(h), np.nan)
    dn = np.full(len(h), np.nan)
    up[1:] = h[1:] - h[:-1]
    dn[1:] = -(l[1:] - l[:-1])
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    plus_dm[0] = np.nan
    minus_dm[0] = np.nan
    trur = rma(true_range(h, l, c), di_len)
    with np.errstate(invalid="ignore", divide="ignore"):
        plus = fixnan(100.0 * rma(plus_dm, di_len) / trur)
        minus = fixnan(100.0 * rma(minus_dm, di_len) / trur)
    s = plus + minus
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = np.where(s == 0, 1.0, s)
        adx = 100.0 * rma(np.abs(plus - minus) / denom, smooth)
    return plus, minus, adx


def cross_over(a, b):
    """Pine ta.crossover: a>b now and a[1]<=b[1] with na-falsy semantics."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    out = np.zeros(len(a), bool)
    if len(a) < 2:
        return out
    va, vb = ~np.isnan(a), ~np.isnan(b)
    prev_ok = np.zeros(len(a), bool)
    prev_ok[1:] = va[:-1] & vb[:-1] & (a[:-1] <= b[:-1])
    now_ok = va & vb & (a > b)
    return prev_ok & now_ok


def cross_under(a, b):
    return cross_over(b, a)


# ------------------------------------------------------------- simulation
def simulate(d, P, fee, slip):
    """Bar-by-bar port with process_orders_on_close=true.

    Per bar i:
      (a) intrabar brackets on the open position (SL before TP on spanning bars;
          stop fills carry adverse slip ticks, limit fills fill at the limit);
      (b) close processing: same-bar-close fills for signals and reversals.
      (c) equity mark at close.
    """
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    n = len(c)
    ef = ema(c, P["ema_fast_len"])
    es = ema(c, P["ema_slow_len"])
    diP, diM, adx = dmi_pine(h, l, c, P["adx_len"], P["adx_smooth"])
    A = atr_pine(h, l, c, P["atr_len"])

    with np.errstate(invalid="ignore"):
        trend_strong = (~np.isnan(adx)) & (adx >= P["adx_threshold"])
        di_bull = (~np.isnan(diP)) & (~np.isnan(diM)) & (diP > diM)
        di_bear = (~np.isnan(diP)) & (~np.isnan(diM)) & (diM > diP)
    cUp = cross_over(ef, es)
    cDn = cross_under(ef, es)
    long_cond = cUp & trend_strong & (di_bull if P["use_di"] else True) & P["allow_long"]
    short_cond = cDn & trend_strong & (di_bear if P["use_di"] else True) & P["allow_short"]

    cash = INIT
    inv = 0.0                 # signed quantity (shares of the symbol)
    entry_px = 0.0
    entry_bar = -1
    entry_fee = 0.0
    sl_px = tp_px = None
    trades = []
    n_open_trades = 0
    eq = np.full(n, np.nan)

    def close_trade(i_exit, fill, why, exit_fee):
        nonlocal cash, inv, sl_px, tp_px, entry_fee
        pnl = inv * (fill - entry_px) - entry_fee - exit_fee
        cash += inv * fill - exit_fee
        trades.append(dict(side="L" if inv > 0 else "S",
                           entry_bar=entry_bar, exit_bar=i_exit,
                           entry=entry_px, exit=fill, pnl=pnl,
                           qty=abs(inv), why=why,
                           entry_fee=entry_fee, exit_fee=exit_fee,
                           fees=entry_fee + exit_fee))
        inv = 0.0
        entry_fee = 0.0
        sl_px = tp_px = None

    for i in range(n):
        # (a) intrabar brackets on the position carried INTO this bar
        if inv != 0 and (sl_px is not None or tp_px is not None):
            hit = None
            if inv > 0:
                if sl_px is not None and l[i] <= sl_px:
                    # stop fills carry adverse slippage ticks
                    hit = (sl_px - slip, "SL", abs(inv) * (sl_px - slip) * fee)
                elif tp_px is not None and h[i] >= tp_px:
                    hit = (tp_px, "TP", abs(inv) * tp_px * fee)
            else:
                if sl_px is not None and h[i] >= sl_px:
                    hit = (sl_px + slip, "SL", abs(inv) * (sl_px + slip) * fee)
                elif tp_px is not None and l[i] <= tp_px:
                    hit = (tp_px, "TP", abs(inv) * tp_px * fee)
            if hit is not None:
                px, why, exit_fee = hit[0], hit[1], hit[2]
                close_trade(i, px, why, exit_fee)

        # (b) processing AT this bar's close
        if long_cond[i] or short_cond[i]:
            equity_mark = cash + inv * c[i]
            fill = c[i] * (1 + slip) if long_cond[i] else c[i] * (1 - slip)
            if long_cond[i]:
                if inv > 0:
                    # duplicate entry rejected by pyramiding=0, but the Pine's
                    # var-block still re-sets the brackets from THIS bar
                    sd = A[i] * P["atr_mult"]
                    sl_px = c[i] - sd if P["use_sl"] else None
                    tp_px = c[i] + sd * P["rr_ratio"] if P["use_tp"] else None
                else:
                    if inv < 0:   # reversal: close the short leg first
                        old_exit_fee = abs(inv) * fill * fee
                        close_trade(i, fill, "reverse", old_exit_fee)
                    q = max(equity_mark, 0.0) / fill if fill > 0 else 0.0
                    if q > 0:
                        sd = A[i] * P["atr_mult"]
                        inv = q
                        entry_fee = q * fill * fee
                        cash -= q * fill + entry_fee
                        entry_px = fill
                        entry_bar = i
                        sl_px = min(c[i] - sd, fill) if P["use_sl"] else None
                        tp_px = c[i] + sd * P["rr_ratio"] if P["use_tp"] else None
            else:
                if inv < 0:
                    sd = A[i] * P["atr_mult"]
                    sl_px = c[i] + sd if P["use_sl"] else None
                    tp_px = c[i] - sd * P["rr_ratio"] if P["use_tp"] else None
                else:
                    if inv > 0:
                        old_exit_fee = abs(inv) * fill * fee
                        close_trade(i, fill, "reverse", old_exit_fee)
                    q = max(equity_mark, 0.0) / fill if fill > 0 else 0.0
                    if q > 0:
                        sd = A[i] * P["atr_mult"]
                        inv = -q
                        entry_fee = q * fill * fee
                        cash += q * fill - entry_fee   # credit sale proceeds, pay entry fee
                        entry_px = fill
                        entry_bar = i
                        sl_px = max(c[i] + sd, fill) if P["use_sl"] else None
                        tp_px = c[i] - sd * P["rr_ratio"] if P["use_tp"] else None

        eq[i] = cash + inv * c[i]

    if inv != 0:
        n_open_trades = 1
        # mark: unrealised entry fee is sunk; do not open a sandbox trade row

    return dict(eq=eq, trades=trades, n_open=n_open_trades,
                long_cond=long_cond, short_cond=short_cond)


# ------------------------------------------------------------- metrics
def _pf(pnls):
    w = sum(p for p in pnls if p > 0)
    ls = sum(p for p in pnls if p <= 0)
    pf = (float("inf") if w > 0 else 0.0) if ls == 0 else w / abs(ls)
    return pf, len(pnls)


def _conc_top5(pnls):
    if not pnls:
        return None, None
    total = sum(pnls)
    if total <= 0:
        return None, None
    top = sorted((p for p in pnls if p > 0), reverse=True)[:5]
    top_sum = sum(top)
    share = 100.0 * top_sum / total
    without = 100.0 * (total - top_sum) / total
    return share, without


def _year_returns(eq, T):
    y = defaultdict(list)
    for i in range(len(eq)):
        yr = dt.datetime.fromtimestamp(T[i] / 1000, dt.timezone.utc).year
        y[yr].append(eq[i])
    out = {}
    for k in sorted(y):
        seg = y[k]
        if len(seg) >= 2 and seg[0] > 0:
            out[k] = (seg[-1] / seg[0] - 1.0) * 100.0
    return out


def _stats(eq, T):
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / peak
    yrs = (T[-1] - T[0]) / (365.25 * 86400000)
    rets = np.diff(eq) / eq[:-1]
    rets = rets[np.isfinite(rets)]
    sp = float(np.median(np.diff(T))) if len(T) > 2 else 3600000.0
    bpy = 365.25 * 86400000.0 / sp
    sharpe = (float(np.mean(rets) / np.std(rets)) * np.sqrt(bpy)
              if len(rets) > 2 and np.std(rets) > 0 else 0.0)
    return dict(ret=(eq[-1] / eq[0] - 1) * 100.0,
                dd=float(dd.max() * 100.0), years=yrs,
                final=float(eq[-1]), sharpe=sharpe)


def run_symbol(path, params):
    """One symbol x tf file -> metrics + tables (harness artifact shape)."""
    import csv as _csv
    t, o, h, l, c = [], [], [], [], []
    with open(path) as f:
        f.readline()
        for line in f:
            a = line.split(",")
            if len(a) < 6:
                continue
            try:
                t.append(int(a[0]))
                o.append(float(a[1])); h.append(float(a[2]))
                l.append(float(a[3])); c.append(float(a[4]))
            except ValueError:
                continue
    d = dict(t=np.array(t, np.int64), o=np.array(o), h=np.array(h),
             l=np.array(l), c=np.array(c))
    n = len(c)

    P = dict(PINE)
    window = (params or {}).get("window", "full")
    if window == "last6mo":
        warm, scored = WARMUP_6MO, SCORED_6MO
        if n < warm + scored:
            raise ValueError("insufficient bars for last6mo window: %d" % n)
        start = n - warm - scored
        d = {k: v[start:] for k, v in d.items()}
        sf = warm                      # scored bars start at index sf
        n = len(d["c"])
    else:
        sf = 0                         # scored region = whole series

    costs_key = (params or {}).get("costs", "author")
    ck = dict(COSTS[costs_key])
    res = simulate(d, P, ck["fee"], ck["slip"])
    # the equity row's convention elsewhere in the repo is view-return:
    res["eq"][:sf] = np.nan

    eq = res["eq"]
    trs = [tr for tr in res["trades"] if tr["exit_bar"] >= sf]
    pnls = [tr["pnl"] for tr in trs]
    pf_s, n_tr = _pf(pnls)
    wr = 100.0 * len([1 for p in pnls if p > 0]) / len(pnls) if pnls else 0.0

    mid = sf + (n - sf) // 2
    h1 = [tr["pnl"] for tr in trs if sf <= tr["exit_bar"] < mid]
    h2 = [tr["pnl"] for tr in trs if tr["exit_bar"] >= mid]
    pf_h1, n_h1 = _pf(h1)
    pf_h2, n_h2 = _pf(h2)

    c3, c4 = _conc_top5(pnls)

    # zero-cost control on the same window (drag measured inside the artifact)
    zi = simulate(d, P, 0.0, 0.0)
    zi["eq"][:sf] = np.nan
    zeq = zi["eq"]
    ztr = [tr for tr in zi["trades"] if tr["exit_bar"] >= sf]

    bH = d["c"][sf - 1] if sf > 0 else d["c"][0]
    bench_ret = (d["c"][-1] / bH - 1.0) * 100.0
    bpeak = np.maximum.accumulate(d["c"][sf:])
    bench_dd = float(((d["c"][sf:] / bpeak - 1.0).min()) * 100.0)

    st = _stats(eq[sf:], d["t"][sf:]) if n - sf > 2 else dict(
        ret=0.0, dd=0.0, years=0.0, final=INIT, sharpe=0.0)
    zst = _stats(zeq[sf:], d["t"][sf:])

    fees_total = sum(abs(tr["qty"]) * tr["entry"] * ck["fee"] for tr in trs)
    gross_pos = sum(p for p in pnls if p > 0)
    fee_over_gross = 100.0 * fees_total / gross_pos if gross_pos > 0 else None

    m = dict(
        window=window, costs=costs_key,
        bars=int(n), scored_bars=int(n - sf),
        ret_pct=round(st["ret"], 4),
        dd_pct=round(st["dd"], 4),
        sharpe=round(st["sharpe"], 4),
        final=round(st["final"], 2),
        n=int(n_tr), n_open=int(res["n_open"]),
        pf_strict=(None if pf_s in (float("inf"), float("-inf"))
                   else round(pf_s, 4)),
        win_rate_strict_pct=round(wr, 4),
        pf_h1=(None if pf_h1 in (float("inf"),) else round(pf_h1, 4)),
        n_h1=int(n_h1),
        pf_h2=(None if pf_h2 in (float("inf"),) else round(pf_h2, 4)),
        n_h2=int(n_h2),
        ret_h1_pct=None if mid <= sf else
            round((eq[mid] / eq[sf] - 1.0) * 100.0, 4),
        ret_h2_pct=None if mid <= sf else
            round((eq[-1] / eq[mid] - 1.0) * 100.0, 4),
        conc_top5_share_pct=None if c3 is None else round(c3, 4),
        conc_net_without_top5_pct=None if c4 is None else round(c4, 4),
        bench_ret_pct=round(bench_ret, 4),
        bench_dd_pct=round(bench_dd, 4),
        beats_bh=bool(st["ret"] > bench_ret),
        ret_zero_pct=round(zst["ret"], 4),
        drag_pp=round(zst["ret"] - st["ret"], 4),
        fee_over_gross_pct=(None if fee_over_gross is None
                            else round(fee_over_gross, 4)),
        fee_total=round(fees_total, 4),
        n_signals_long=int(res["long_cond"][sf:].sum()),
        n_signals_short=int(res["short_cond"][sf:].sum()),
        year_returns={str(k): round(v, 4) for k, v in
                      _year_returns(eq[sf:], d["t"][sf:]).items()},
        n_trades_zero=len(ztr),
    )

    tables = [dict(kind="trade", **{k: (round(v, 6) if isinstance(v, float) else v)
                                    for k, v in tr.items()})
              for tr in trs[:4000]]
    return {"metrics": m, "tables": tables}


if __name__ == "__main__":
    print(__doc__)
