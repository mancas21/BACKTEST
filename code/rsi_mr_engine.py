#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rsi_mr_engine.py — RSI mean-reversion on SOL/USDC spot, 1h (the user's
prespecified strategy, backtested under the repo harness).

THE SPEC, AS ASKED AND AS DECLARED (nothing tuned):
    Entry : flat AND RSI(14) < 30 at a bar close  -> market buy at the NEXT open
    Exit  : RSI(14) > 70 at a bar close           -> market sell at the NEXT open
    Stop  : ATR(14) * 2 below the FILL price, distance frozen at the signal bar
            (2 * ATR of the signal bar); intrabar, stop FIRST, an open gapped
            through the stop fills AT THE OPEN (TV stop->market rule)
    Sizing: 1% of equity risked to the stop distance -> qty = eq * 0.01 / dist;
            capped at full-equity notional (SPOT: no leverage, long only)
    Costs : repo standard, 5 bps fee + 0.5 bps slippage per side (11 bps round
            trip); a zero-cost control runs inside every artifact (drag_pp
            measured there, never derived)
    Window: the scored region is the LAST `window_days` days (default 180);
            indicators warm up on everything before it and the warmup is
            excluded from every metric (equity marked nan there).
    End of data: an open position is force-closed at the last close with
            reason `end_of_data` and counted as a closed trade (cbpack's
            convention, pinned by the audit).
    State-based entry: while RSI keeps printing < 30 the book re-enters as
            soon as it is flat (a stop-out in a prolonged oversold regime
            re-enters on the next signal bar) — the literal reading of
            "entry when RSI < 30"; no cooldown is invented.

PRIMITIVES: rma (SMA-seeded Wilder, leading-na skipped — the all-NaN bug
class), true_range/atr and the Pine-faithful RSI built on that rma; the same
validated implementations carried by adxhma/emaadx/fingrad. Re-asserted by
code/_rsi_mr_audit.py together with executor known answers, the no-lookahead
truncation proof and determinism, BEFORE any real-data artifact.
"""
import os
from collections import defaultdict
import datetime as dt

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INIT = 10_000.0

PINE = dict(rsi_len=14, lo=30.0, hi=70.0, atr_len=14, sl_mult=2.0,
            risk_pct=1.0, window_days=180)
COSTS = {"repo": dict(fee=0.0005, slip=0.00005),   # 5 bps + 0.5 bps = 11 bps RT
         "zero": dict(fee=0.0, slip=0.0)}


# ------------------------------------------------------------- indicators
def rma(x, n):
    """Wilder smoothing, SMA-seeded like Pine's ta.rma; leading na skipped."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    buf, prev, seeded = [], np.nan, False
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
                out[i] = prev
            else:
                prev = (prev * (n - 1) + xi) / n
                out[i] = prev
    return out


def true_range(h, l, c):
    pc = np.roll(c, 1)
    pc[0] = np.nan
    return np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))


def atr_pine(h, l, c, n):
    return rma(true_range(h, l, c), n)


def rsi_pine(c, n):
    """Pine ta.rsi: Wilder-smoothed gains/losses, 100 when avg loss is 0,
    na until 2*n-ish warmup resolved through rma."""
    d = np.diff(c, prepend=np.nan)
    up = np.where(np.isnan(d), np.nan, np.maximum(d, 0.0))
    dn = np.where(np.isnan(d), np.nan, np.maximum(-d, 0.0))
    au, ad = rma(up, n), rma(dn, n)
    out = np.full(len(c), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        rs = au / ad
        v = 100.0 - 100.0 / (1.0 + rs)
    out = np.where(ad == 0, 100.0, v)
    out[~np.isfinite(out) & ~(ad == 0)] = np.nan
    return out


def rsi_loop(c, n):
    """Independent per-bar reimplementation (the dual engine)."""
    out = np.full(len(c), np.nan)
    ag = al = 0.0
    seeded = 0
    for i in range(1, len(c)):
        d = c[i] - c[i - 1]
        g, l = max(d, 0.0), max(-d, 0.0)
        if seeded < n:
            ag += g
            al += l
            seeded += 1
            if seeded == n:
                ag, al = ag / n, al / n
                out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
        else:
            ag = (ag * (n - 1) + g) / n
            al = (al * (n - 1) + l) / n
            out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


# ------------------------------------------------------------- executor
def execute(d, sig, dist, fee, slip):
    """sig: dict(buy, sell) bool arrays; dist: stop distance array.
    All state local (the costed and zero-cost passes must not share any)."""
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    n = len(c)
    cash = INIT
    qty = 0.0
    entry = 0.0
    entry_i = -1
    entry_fee = 0.0
    sl = None
    pend_close = False
    pend_buy = False
    pend_q = 0.0
    pend_d = 0.0
    eq = np.full(n, np.nan)
    trades = []

    def close_pos(i, px, why, adverse):
        nonlocal cash, qty, entry_fee, sl
        fill = px * (1 - adverse) if qty > 0 else px * (1 + adverse)
        xf = qty * fill * fee
        pnl = qty * (fill - entry) - entry_fee - xf
        cash += qty * fill - xf
        trades.append(dict(entry_i=entry_i, exit_i=i, entry=entry, exit=fill,
                           qty=qty, pnl=pnl, why=why,
                           fees=entry_fee + xf, bars=i - entry_i))
        qty, entry_fee, sl = 0.0, 0.0, None

    for i in range(n):
        # 1) fill the pending order at this open (market, adverse slip)
        if pend_close and qty > 0:
            close_pos(i, o[i], "rsi_exit", slip)
        if pend_buy and qty == 0:
            fill = o[i] * (1 + slip)
            cash -= pend_q * fill
            entry_fee = pend_q * fill * fee
            cash -= entry_fee
            qty, entry, entry_i = pend_q, fill, i
            sl = fill - pend_d if pend_d > 0 else None
        pend_close, pend_buy = False, False

        # 2) intrabar stop on the position carried into this bar
        if qty > 0 and sl is not None and l[i] <= sl:
            px = o[i] if o[i] <= sl else sl          # gap-through fills at open
            close_pos(i, px, "SL", slip)

        # 3) decisions at this close, scheduled for the next open
        eq[i] = cash + qty * c[i]
        if i + 1 >= n:
            continue
        if qty > 0:
            if sig["sell"][i]:
                pend_close = True
        elif sig["buy"][i] and np.isfinite(dist[i]) and dist[i] > 0:
            eqv = cash
            fill_est = o[i + 1] * (1 + slip)
            q = min(eqv * PINE["risk_pct"] / 100.0 / dist[i], eqv / fill_est)
            if q > 0:
                pend_buy, pend_q, pend_d = True, q, float(dist[i])
    # end of data: force-close at the last close (cbpack convention; fee, no slip)
    if qty > 0:
        close_pos(n - 1, c[n - 1], "end_of_data", 0.0)
        eq[n - 1] = cash
    return dict(eq=eq, trades=trades)


# ------------------------------------------------------------- metrics
def _pf(pnls):
    w = sum(p for p in pnls if p > 0)
    ls = sum(p for p in pnls if p <= 0)
    return (float("inf") if w > 0 else 0.0) if ls == 0 else w / abs(ls)


def run_symbol(path, params):
    params = dict(params or {})
    costs_key = str(params.pop("costs", "repo"))
    window_days = int(params.pop("window_days", PINE["window_days"]))
    if params:
        raise ValueError(f"unknown rsimr params: {sorted(params)}")
    fee, slip = COSTS[costs_key]["fee"], COSTS[costs_key]["slip"]

    t, o, h, l, c = [], [], [], [], []
    with open(path) as f:
        f.readline()
        for line in f:
            a = line.split(",")
            if len(a) < 6:
                continue
            try:
                t.append(int(a[0])); o.append(float(a[1])); h.append(float(a[2]))
                l.append(float(a[3])); c.append(float(a[4]))
            except ValueError:
                continue
    d = dict(t=np.array(t, np.int64), o=np.array(o), h=np.array(h),
             l=np.array(l), c=np.array(c))
    n = len(d["c"])
    sf = max(0, n - window_days * 24)             # scored region start

    r = rsi_pine(d["c"], PINE["rsi_len"])
    A = atr_pine(d["h"], d["l"], d["c"], PINE["atr_len"])
    dist = np.where(np.isnan(A), 0.0, PINE["sl_mult"] * A)
    sig = dict(buy=(r < PINE["lo"]) & ~np.isnan(r),
               sell=(r > PINE["hi"]) & ~np.isnan(r))

    res = execute(d, sig, dist, fee, slip)
    zres = execute(d, sig, dist, 0.0, 0.0)

    eq = res["eq"].copy()
    eq[:sf] = np.nan
    trs = [tr for tr in res["trades"] if tr["exit_i"] >= sf]
    pnls = [x["pnl"] for x in trs]
    n_tr = len(pnls)
    pf = _pf(pnls)
    wr = 100.0 * sum(1 for x in pnls if x > 0) / n_tr if n_tr else 0.0
    peak = np.maximum.accumulate(eq[np.isfinite(eq)])   # scored segment only:
    dd = np.full(n, np.nan)                             # accumulate never
    dd[np.isfinite(eq)] = (eq[np.isfinite(eq)] / peak - 1.0) * 100.0  # recovers from leading nan
    rets = np.diff(eq[np.isfinite(eq)]) / eq[np.isfinite(eq)][:-1]
    bpy = 24 * 365
    sharpe = (float(np.mean(rets) / np.std(rets, ddof=1)) * np.sqrt(bpy)
              if len(rets) > 2 and np.std(rets, ddof=1) > 0 else 0.0)
    seg = eq[np.isfinite(eq)]
    net = (seg[-1] / seg[0] - 1.0) * 100.0
    bh = (d["c"][-1] / d["c"][sf] - 1.0) * 100.0
    gross = sum(x for x in pnls if x > 0)
    fees_total = sum(x["fees"] for x in trs)

    mid = sf + (n - sf) // 2
    h1 = [x["pnl"] for x in trs if x["exit_i"] < mid]
    h2 = [x["pnl"] for x in trs if x["exit_i"] >= mid]
    by_why = defaultdict(lambda: [0, 0.0, 0])
    for x in trs:
        b = by_why[x["why"]]
        b[0] += 1
        b[1] += x["pnl"]
        b[2] += 1 if x["pnl"] > 0 else 0

    # curve tables for the chart (scored region, hourly)
    curve = [dict(kind="curve", i=int(j),
                  t=int(d["t"][j]),
                  eq=(None if not np.isfinite(eq[j]) else round(float(eq[j]), 4)),
                  dd=(None if not np.isfinite(dd[j]) else round(float(dd[j]), 4)),
                  close=float(d["c"][j]))
             for j in range(sf, n)]

    m = dict(
        symbol=os.path.basename(path).split("_")[0], bars=int(n),
        window_days=window_days, scored_bars=int(n - sf),
        first=str(dt.datetime.fromtimestamp(d["t"][sf] / 1000, dt.timezone.utc)),
        last=str(dt.datetime.fromtimestamp(d["t"][-1] / 1000, dt.timezone.utc)),
        rsi_len=PINE["rsi_len"], lo=PINE["lo"], hi=PINE["hi"],
        atr_len=PINE["atr_len"], sl_mult=PINE["sl_mult"], risk_pct=PINE["risk_pct"],
        costs=costs_key, cost_bp_roundtrip=2.0 * (fee + slip) * 1e4,
        n_trades=n_tr, return_pct=round(net, 4), profit_factor=(None if pf == float("inf") else round(pf, 4)),
        win_rate=round(wr, 4), sharpe=round(sharpe, 4),
        max_dd_pct=round(float(np.nanmin(dd)), 4),
        expectancy=round(float(np.mean(pnls)) if pnls else 0.0, 4),
        avg_bars=round(float(np.mean([x["bars"] for x in trs])) if trs else 0.0, 2),
        exposure_pct=round(100.0 * sum(x["bars"] for x in trs) / (n - sf), 4),
        bh_return_pct=round(bh, 4), beats_bh=bool(net > bh),
        ret_zero_pct=None, drag_pp=None,        # filled below
        pf_h1=(None if _pf(h1) == float("inf") else round(_pf(h1), 4)), n_h1=len(h1),
        pf_h2=(None if _pf(h2) == float("inf") else round(_pf(h2), 4)), n_h2=len(h2),
        fees=round(fees_total, 4),
        fee_over_gross_pct=(round(100.0 * fees_total / gross, 4) if gross > 0 else None),
        exit_reasons={k: dict(n=v[0], pnl=round(v[1], 4), wins=v[2])
                      for k, v in sorted(by_why.items())},
        flag="OK" if n_tr >= 30 else "INSUFFICIENT_SAMPLE",
    )
    zeq = zres["eq"].copy()
    zeq[:sf] = np.nan
    zs = zeq[np.isfinite(zeq)]
    m["ret_zero_pct"] = round((zs[-1] / zs[0] - 1.0) * 100.0, 4)
    m["drag_pp"] = round(m["ret_zero_pct"] - net, 4)
    tables = curve + [dict(kind="trade", **{k: (round(v, 6) if isinstance(v, float) else v)
                                            for k, v in tr.items()}) for tr in trs]
    return {"metrics": m, "tables": tables}


if __name__ == "__main__":
    print(__doc__)
