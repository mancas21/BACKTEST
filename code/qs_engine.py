#!/usr/bin/env python
"""qs_engine.py -- executor for the strategy catalog's family A
(QS-001..QS-010), implementing the catalog's common blocks G1/G2/G3
verbatim. This is NOT pack50_core: the sizing, the stop fills and the risk
devices are all different, and each difference is a known-answer test in
code/_qs_audit.py.

G1 SIZING (verbatim intent)
    quantity = (0.01 * equity) / (|entry_ref - stop| + RT_cost_per_unit)
    with equity = the marked equity at the SIGNAL close, entry_ref = the
    signal close (the fill is the next open, unknowable at signal time;
    declared), RT_cost_per_unit = 2*(fee+slip)*entry_ref. Caps: gross
    notional <= 3x that equity; one open position per symbol (single-symbol
    book by construction). Equity compounds. Risk devices: daily loss limit
    3% of day-start equity -> FLAT AND HALT (exit at the next open, no new
    entries until the next UTC day); halve risk at -15% from peak equity;
    halt for review (exit, no further entries) at -25% from peak.

G2 EXECUTION (verbatim)
    Signals evaluate on the closed bar t; fills at the open of t+1, taker.
    Stops are stop-market: a normal touch fills AT the stop plus adverse
    slippage; a gap through fills at the WORSE of stop and open, plus
    adverse slippage. The Stress scenario doubles the stop slippage. If stop
    and target are both touched inside one candle the STOP fills first
    (conservative). Targets fill at the limit price exactly (no gap
    improvement; declared conservative). Cost ladder (per side, bps):
      base    5.0 fee + 2.0  slip (14 bps RT)   <- the catalog's Base
      adverse 5.0 fee + 6.0  slip (22 bps RT)   <- the catalog's Adverse
      stress  5.0 fee + 12.5 slip (35 bps RT, stop slip doubled)
      gate    5.0 fee + 0.5  slip (11 bps RT)   <- the catalog's extra
                                                  sensitivity point (the
                                                  repo's measured gate)
    A reversal (opposite entry event while positioned) is TWO taker fills at
    the same open: the old position closes (slipped), the new one opens
    (slipped), sized off the same signal-close equity.

G3 FUNDING
    Realized funding charged at the actual settlement instants on the
    position held at the bar whose open first covers the settlement
    timestamp (long pays a positive rate, short receives).

FREQUENCY SEMANTICS (every family-A sheet)
    Entry events are RISING EDGES of the entry condition (one entry per
    episode); 5-bar cool-down after an exit; max 1 open position.

Data: taker klines + funding json per symbol. All plans are precomputed
signal arrays; the executor owns every fill decision.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INIT = 10000.0

COSTS = {
    "base":    dict(fee=0.0005, slip=0.0002, stop_slip_mult=1.0),
    "adverse": dict(fee=0.0005, slip=0.0006, stop_slip_mult=1.0),
    "stress":  dict(fee=0.0005, slip=0.00125, stop_slip_mult=2.0),
    "gate":    dict(fee=0.0005, slip=0.00005, stop_slip_mult=1.0),
}

G1 = dict(risk_frac=0.01, max_gross=3.0, daily_loss=0.03,
          dd_halve=0.15, dd_halt=0.25, cooldown=5)


# ── primitives ─────────────────────────────────────────────────────────────
def ema(x, n):
    return pd.Series(np.asarray(x, float)).ewm(span=n, adjust=False,
                                               min_periods=n).mean()


def rma(x, n):
    """Pine ta.rma: seed with the SMA of the first n VALID values (leading
    NaNs skipped -- Wilder inputs carry NaN warmups), hold the last value
    on a NaN input."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    buf = []
    prev = np.nan
    for i, xi in enumerate(x):
        if np.isnan(prev):
            if np.isnan(xi):
                continue
            buf.append(xi)
            if len(buf) == n:
                prev = float(np.mean(buf))
                out[i] = prev
        else:
            if np.isnan(xi):
                out[i] = prev
            else:
                prev = (prev * (n - 1) + xi) / n
                out[i] = prev
    return out


def atr(h, l, c, n=14):
    h, l, c = map(np.asarray, (h, l, c))
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(rma(tr, n), index=pd.Series(c).index)


def rsi(c, n=14):
    """Pine ta.rsi: Wilder RMA of gains/losses; down==0 -> 100."""
    c = np.asarray(c, float)
    d = np.diff(c, prepend=c[0])
    up = rma(np.where(d > 0, d, 0.0), n)
    dn = rma(np.where(d < 0, -d, 0.0), n)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = 100.0 - 100.0 / (1.0 + up / np.where(dn == 0, 1.0, dn))
    return np.where(dn == 0, 100.0, out)


def wilder_dmi(h, l, c, n=14):
    h, l, c = map(np.asarray, (h, l, c))
    up = np.diff(h, prepend=h[0])
    dn = -np.diff(l, prepend=l[0])
    pdi_n = np.where((up > dn) & (up > 0), up, 0.0)
    mdi_n = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = rma(np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc))), n)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi = 100.0 * rma(pdi_n, n) / tr
        mdi = 100.0 * rma(mdi_n, n) / tr
        dx = 100.0 * np.abs(pdi - mdi) / (pdi + mdi)
    return pdi, mdi, rma(dx, n)


def load_funding(path):
    if not path or not os.path.exists(path):
        return np.array([], np.int64), np.array([], float)
    recs = json.load(open(path, encoding="utf-8"))
    ts = np.array([int(x["t"]) for x in recs], np.int64)
    rate = np.array([float(x["r"]) for x in recs], float)
    keep = np.argsort(ts)
    return ts[keep], rate[keep]


# ── the executor ───────────────────────────────────────────────────────────
def run(df, plan, fee, slip, stop_slip_mult=1.0, funding=None,
        g1=None, init=INIT, seed=0, random_entries=False):
    """One pass over df with one plan. Returns trades, equity, counters."""
    g1 = dict(G1, **(g1 or {}))
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["open_ts"].to_numpy(np.int64)
    n = len(df)

    def _b(x):
        return np.asarray(pd.Series(x).fillna(False), bool)

    def _f(x):
        if x is None:
            return np.full(n, np.nan)
        return np.asarray(pd.Series(x), float)

    le = _b(plan["long_event"])
    se = _b(plan["short_event"])
    lx = _b(plan["long_exit"])
    sx = _b(plan["short_exit"])
    sdl = _f(plan.get("stop_dist_long"))
    sds = _f(plan.get("stop_dist_short"))
    sll = _f(plan.get("stop_level_long"))
    sls = _f(plan.get("stop_level_short"))
    tpd = _f(plan.get("tp_dist"))
    atrv = _f(plan.get("atr"))
    max_hold = int(plan.get("max_hold") or 0)
    trail_mult = float(plan.get("trailing_atr_mult") or 0.0)

    if random_entries:
        rng = np.random.default_rng(seed)
        k = int(le.sum() + se.sum())
        idx = rng.choice(np.arange(60, max(61, n)), size=min(k, max(1, n - 60)),
                         replace=False)
        ref_close = c.copy()
        a = atrv.copy()
        le = np.zeros(n, bool); se = np.zeros(n, bool)
        le[idx[idx % 2 == 0]] = True
        se[idx[idx % 2 == 1]] = True
        sdl = np.where(le, 2.0 * a, np.nan)
        sds = np.where(se, 2.0 * a, np.nan)
        sll = np.where(le, ref_close - 2.0 * a, np.nan)
        sls = np.where(se, ref_close + 2.0 * a, np.nan)
        lx = sx = np.zeros(n, bool)
        tpd = np.full(n, np.nan)

    f_ts, f_rate = funding if funding is not None else (np.array([], np.int64),
                                                        np.array([], float))
    f_j = 0

    cash = float(init)
    pos = 0
    qty = 0.0
    entry_px = 0.0
    entry_i = -1
    entry_fee = 0.0
    stop_px = np.nan
    tp_px = np.nan
    best_close = 0.0
    queue = None               # (kind, side, reason) at the NEXT open
    last_exit_i = -10 ** 9
    day = None
    day_start_eq = float(init)
    halted_today = False
    halted_review = False
    risk_mult = 1.0
    peak = float(init)

    trades = []
    eq = np.full(n, np.nan)
    n_fund = 0
    fund_paid = 0.0
    fees_paid = 0.0
    n_daily_halts = 0
    n_review_halt = 0
    n_gap_fills = 0
    n_stop_fills = 0
    n_target_fills = 0
    max_leverage = 0.0

    def close_fill(i, px, why):
        nonlocal cash, pos, qty, stop_px, tp_px, last_exit_i, fees_paid
        f = abs(qty * px) * fee
        cash += pos * qty * (px - entry_px) - f
        fees_paid += f
        pnl = pos * qty * (px - entry_px) - f - entry_fee
        trades.append(dict(entry_ts=int(ts[entry_i]), exit_ts=int(ts[i]),
                           side=pos, entry_px=entry_px, exit_px=px, qty=qty,
                           pnl=pnl, fees=entry_fee + f, why=why,
                           entry_i=entry_i, exit_i=i,
                           ret_pct=100.0 * pnl / max(eq_ref, 1e-9)))
        pos, qty = 0, 0.0
        stop_px = tp_px = np.nan
        last_exit_i = i

    eq_ref = float(init)       # marked equity at the last closed bar

    for i in range(n):
        # ---- 1. execute the queued order at THIS bar's open ----------------
        if queue is not None:
            kind, side, reason = queue
            queue = None
            if kind in ("exit", "rev") and pos != 0:
                px = o[i] * (1.0 - slip * pos)
                close_fill(i, px, reason)
            if kind in ("entry", "rev"):
                side_eff = side if kind == "entry" else side
                if pos == 0 and not halted_review and not halted_today:
                    fill = o[i] * (1.0 + slip * side_eff)
                    sd = (sdl[i - 1] if side_eff > 0 else sds[i - 1])
                    lvl = (sll[i - 1] if side_eff > 0 else sls[i - 1])
                    if not np.isfinite(sd) and np.isfinite(lvl):
                        sd = abs(fill - lvl)
                    if np.isfinite(sd) and sd > 0 and eq_ref > 0:
                        rt_unit = 2.0 * (fee + slip) * fill
                        q = (g1["risk_frac"] * eq_ref * risk_mult) / (sd + rt_unit)
                        q = min(q, g1["max_gross"] * eq_ref / fill)
                        if q > 0:
                            f = q * fill * fee
                            cash -= f
                            fees_paid += f
                            pos, qty = side_eff, q
                            entry_px = fill
                            entry_i = i
                            entry_fee = f
                            stop_px = (fill - sd) if side_eff > 0 else (fill + sd)
                            if np.isfinite(lvl):
                                stop_px = lvl
                            tp_px = np.nan
                            if tpd is not None and np.isfinite(tpd[i - 1]) \
                                    and tpd[i - 1] > 0:
                                tp_px = fill + side_eff * tpd[i - 1]
                            best_close = fill
                            max_leverage = max(max_leverage,
                                               q * fill / max(eq_ref, 1e-9))

        # ---- 2. intrabar: stop first (SL-first on ties), then target -------
        if pos != 0:
            hit_stop = (not np.isnan(stop_px)) and \
                (l[i] <= stop_px if pos > 0 else h[i] >= stop_px)
            hit_tp = (not np.isnan(tp_px)) and \
                (h[i] >= tp_px if pos > 0 else l[i] <= tp_px)
            if hit_stop:
                raw = min(stop_px, o[i]) if pos > 0 else max(stop_px, o[i])
                if (pos > 0 and o[i] < stop_px) or (pos < 0 and o[i] > stop_px):
                    n_gap_fills += 1
                px = raw * (1.0 - stop_slip_mult * slip * pos)
                close_fill(i, px, "stop")
                n_stop_fills += 1
            elif hit_tp:
                close_fill(i, tp_px, "target")
                n_target_fills += 1

        # ---- 3. trailing stop from closes (effective from the next bar) ----
        if pos != 0 and trail_mult > 0 and np.isfinite(atrv[i]):
            best_close = max(best_close, c[i]) if pos > 0 else \
                min(best_close, c[i])
            tr_px = best_close - pos * trail_mult * atrv[i]
            if pos > 0:
                stop_px = max(stop_px if not np.isnan(stop_px) else tr_px, tr_px)
            else:
                stop_px = min(stop_px if not np.isnan(stop_px) else tr_px, tr_px)

        # ---- 4. funding at settlement instants (G3) ------------------------
        while f_j < len(f_ts) and f_ts[f_j] <= ts[i]:
            if pos != 0:
                pay = pos * qty * c[i] * f_rate[f_j]
                cash -= pay
                fund_paid += pay
                n_fund += 1
            f_j += 1

        # ---- 5. mark equity + G1 risk devices ------------------------------
        equity = cash + (pos * qty * (c[i] - entry_px) if pos != 0 else 0.0)
        eq_ref = equity
        d = int(ts[i]) // 86_400_000
        if d != day:
            day = d
            day_start_eq = equity
            halted_today = False
        if not halted_today and day_start_eq > 0 and \
                equity <= day_start_eq * (1.0 - g1["daily_loss"]):
            # flat AND halt: close whatever is open; bar new entries
            # (including a same-day re-entry after an intrabar stop-out)
            # until the next UTC day
            if pos != 0 and queue is None:
                queue = ("exit", 0, "daily halt")
            halted_today = True
            n_daily_halts += 1
        peak = max(peak, equity)
        if risk_mult == 1.0 and peak > 0 and equity <= peak * (1.0 - g1["dd_halve"]):
            risk_mult = 0.5
        if not halted_review and peak > 0 and equity <= peak * (1.0 - g1["dd_halt"]):
            halted_review = True
            n_review_halt += 1
            if pos != 0 and queue is None:
                queue = ("exit", 0, "review halt")
        eq[i] = cash + (pos * qty * (c[i] - entry_px) if pos != 0 else 0.0)

        # ---- 6. decisions at this close (orders fill at the next open) -----
        if i + 1 < n and queue is None:
            if pos != 0:
                rev = se[i] if pos > 0 else le[i]
                exit_sig = lx[i] if pos > 0 else sx[i]
                hold_out = max_hold > 0 and (i - entry_i + 1) >= max_hold
                if rev:
                    queue = ("rev", -pos, "reverse")
                elif exit_sig:
                    queue = ("exit", 0, "signal exit")
                elif hold_out:
                    queue = ("exit", 0, "time stop")
            else:
                can_enter = (not halted_review) and (not halted_today) and \
                    (i - last_exit_i >= g1["cooldown"])
                if can_enter and le[i]:
                    queue = ("entry", 1, "long")
                elif can_enter and se[i]:
                    queue = ("entry", -1, "short")

    if pos != 0:
        close_fill(n - 1, c[-1], "end_of_data")
        eq[-1] = cash

    return dict(eq=eq, trades=trades, fund_paid=fund_paid, n_funding=n_fund,
                fees_paid=fees_paid, n_daily_halts=n_daily_halts,
                n_review_halt=n_review_halt, n_gap_fills=n_gap_fills,
                n_stop_fills=n_stop_fills, n_target_fills=n_target_fills,
                max_leverage=max_leverage, halted_review=halted_review,
                risk_mult_final=risk_mult)


# ── G4 validation machinery ────────────────────────────────────────────────
def segment_trades(trades, bounds, max_hold):
    """Assign trades to chronological segments with embargo + purge.
    bounds: list of (name, start_i, end_i). A trade belongs to the segment
    containing its ENTRY bar; it is PURGED (dropped) if its exit bar runs
    past the segment end minus the embargo (overlapping labels)."""
    emb = max(1, int(max_hold or 1))
    segs = {name: [] for name, _, _ in bounds}
    for t in trades:
        ei = t["entry_i"]
        for name, a, b in bounds:
            if a <= ei <= b:
                if t["exit_i"] > b - emb:
                    break                     # purged (would leak forward)
                segs[name].append(t)
                break
    return segs


def pf_and_expectancy(trs):
    if not trs:
        return dict(n=0, pf=None, exp_bps=None, wr=None)
    pnl = np.array([t["pnl"] for t in trs], float)
    ret = np.array([t["ret_pct"] for t in trs], float)
    w = pnl[pnl > 0].sum()
    ls = -pnl[pnl <= 0].sum()
    pf = float(w / ls) if ls > 0 else (float("inf") if w > 0 else 0.0)
    return dict(n=len(trs), pf=pf if np.isfinite(pf) else None,
                exp_bps=float(np.mean(ret) * 100.0),
                wr=float(100.0 * (pnl > 0).mean()))


def block_bootstrap_exp_lb(ret_pct, n_boot=1000, seed=7):
    """Moving-block bootstrap lower bound (2.5%) of mean trade return, in bps."""
    x = np.asarray(ret_pct, float) * 100.0
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return float("nan")
    block = max(1, min(int(round(n ** (1.0 / 3.0))), n))
    nb = int(np.ceil(n / block))
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for s in range(n_boot):
        starts = rng.integers(0, n - block + 1, size=nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
        means[s] = x[idx].mean()
    return float(np.percentile(means, 2.5))


def deflated_sharpe(sharpes, n_obs, skew=0.0, kurt=3.0):
    """Bailey-Lopez de Prado DSR: P that the TRUE SR > 0 given the best
    observed SR among N trials and the cross-trial variance."""
    sr = np.asarray([s for s in sharpes if np.isfinite(s)], float)
    N = len(sr)
    if N == 0 or n_obs < 2:
        return float("nan")
    v = float(np.var(sr, ddof=1)) if N > 1 else 0.0
    sr_max = float(np.max(sr))
    from math import sqrt, log, exp, pi, erf
    def z(p):
        return 1.4142135623730951 * _erfinv(2 * p - 1)
    gamma = 0.5772156649015329
    if N > 1 and v > 0:
        emc = 0.5772156649015329
        sr0 = sqrt(v) * ((1 - emc) * z(1 - 1.0 / N) + emc * z(1 - 1.0 / (N * exp(1))))
    else:
        sr0 = 0.0
    denom = sqrt(max(1.0e-12, (1.0 - skew * sr_max + (kurt - 1) / 4.0 * sr_max ** 2) / max(n_obs - 1, 1)))
    t = (sr_max - sr0) / denom
    return 0.5 * (1.0 + erf(t / sqrt(2.0)))


def _erfinv(y):
    # small-series inverse erf (Abramowitz-Stegun style bisection on erf)
    from math import erf
    lo, hi = -6.0, 6.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if erf(mid) < y:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def cscv_pbo(train_sharpes_by_variant, val_sharpes_by_variant):
    """Combinatorially symmetric cross-validation PBO over the grid's
    train/val Sharpe matrix (one row per variant)."""
    tr = np.asarray(train_sharpes_by_variant, float)
    va = np.asarray(val_sharpes_by_variant, float)
    N = len(tr)
    if N < 4:
        return float("nan")
    from itertools import combinations
    wins = 0
    total = 0
    for k in range(2, N // 2 + 1):
        for sub in combinations(range(N), k):
            sub = list(sub)
            best_in = sub[int(np.nanargmax(tr[sub]))]
            oos = [j for j in range(N) if j not in sub]
            best_oos = oos[int(np.nanargmax(va[oos]))]
            total += 1
            if va[best_in] <= np.nanmedian(va[oos]):
                wins += 1
    return float(wins / total) if total else float("nan")
