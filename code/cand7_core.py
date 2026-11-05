#!/usr/bin/env python
"""cand7_core.py -- execution machinery for the seven prespecified candidates
in `Downloads/strategy_candidates_v2-claude.md` (copied to `code/cand7_spec.md`).

WHY A NEW CORE
    pack50_core is built around one-position, full-equity, stop-from-signal-close
    books.  These candidates declare a different contract:

      * risk-based sizing (stop = 0.5% of equity, 3x notional cap) for the four
        directional books, and fixed gross exposure for the basket/pair books;
      * stops measured from the FILL price, not from the signal close;
      * an asymmetric funding convention at the entry instant (charged when the
        position pays, not credited when it receives);
      * multi-leg books (five-asset rotation, two-leg funding pair) with
        per-leg stops, turnover costs and per-leg funding.

    Reusing the pack core would silently change the declared rules, so the
    fills live here and every deviation is stated in `cand7_strats.py`.

CONVENTIONS (declared, used by all seven)
    * Signals are evaluated on closed bar t; the fill is at open(t+1), except
      the funding candidates, whose decision is made AT the settlement-bar open
      from rates that settled strictly before that instant.
    * Entry and signal exits pay the adverse slippage on the fill price and the
      taker fee on the notional.  A stop fills at the stop price adverse by the
      slip; a gap through the stop fills at the bar open adverse by the slip.
      Stop and target in one bar: STOP first.
    * Funding: every settlement instant with entry_ts <= t < exit_ts is charged
      on the open notional at the close of the bar containing it.  At exactly
      entry_ts the settlement is charged only when the position PAYS it; a
      receiving settlement at the entry instant is not credited (declared).
    * Sizing, directional: qty = risk_frac * equity / stop_distance, capped at
      max_leverage * equity / price.  Basket/pair books use the declared
      exposure fractions instead.
    * Buy & hold is the same window, first open to last close, no costs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BPS = 1e-4


@dataclass
class Costs:
    fee_bps: float
    slip_bps: float

    @property
    def side_bps(self) -> float:
        return float(self.fee_bps + self.slip_bps)


# ══════════════════════════════════════════════════════ funding
def funding_cash(f_ts, f_rate, t0, t1, bar_ts, close, qty, side, at_entry_pays_only=True):
    """Signed funding cash for a FIXED-size position.

    Settlements in [t0, t1) are charged.  A settlement exactly at t0 is
    included only when it is a payment (side*rate > 0), per the declared
    convention.  Mark price = close of the bar containing the settlement.
    """
    if len(f_ts) == 0:
        return 0.0, 0
    lo = int(np.searchsorted(f_ts, t0, side="left"))
    hi = int(np.searchsorted(f_ts, t1, side="left"))
    if hi <= lo:
        return 0.0, 0
    ts = f_ts[lo:hi]
    rt = f_rate[lo:hi]
    keep = np.ones(len(ts), dtype=bool)
    if at_entry_pays_only:
        at_entry = ts == t0
        keep &= (~at_entry) | (side * rt > 0)
    if not keep.any():
        return 0.0, 0
    ts, rt = ts[keep], rt[keep]
    idx = np.searchsorted(bar_ts, ts, side="right") - 1
    idx = np.clip(idx, 0, len(close) - 1)
    px = close[idx]
    cash = -side * qty * float((px * rt).sum())
    return float(cash), int(len(ts))


def funding_cash_notional(f_ts, f_rate, t0, t1, bar_ts, close, notional, side,
                          at_entry_pays_only=True):
    """Same for a book whose leg is marked as a notional fraction of equity."""
    if len(f_ts) == 0:
        return 0.0, 0
    lo = int(np.searchsorted(f_ts, t0, side="left"))
    hi = int(np.searchsorted(f_ts, t1, side="left"))
    if hi <= lo:
        return 0.0, 0
    ts = f_ts[lo:hi]
    rt = f_rate[lo:hi]
    keep = np.ones(len(ts), dtype=bool)
    if at_entry_pays_only:
        at_entry = ts == t0
        keep &= (~at_entry) | (side * rt > 0)
    if not keep.any():
        return 0.0, 0
    ts, rt = ts[keep], rt[keep]
    idx = np.searchsorted(bar_ts, ts, side="right") - 1
    idx = np.clip(idx, 0, len(close) - 1)
    px = close[idx]
    ref = close[max(int(idx[0]) - 1, 0)]
    cash = -side * notional * float((px / max(ref, 1e-12) * rt).sum())
    return float(cash), int(len(ts))


def funding_charges(f_ts, f_rate, t0, t1, bar_ts, close, qty, side):
    """Per-settlement cash list, for audits (same filter as funding_cash)."""
    out = []
    if len(f_ts) == 0:
        return out
    lo = int(np.searchsorted(f_ts, t0, side="left"))
    hi = int(np.searchsorted(f_ts, t1, side="left"))
    for j in range(lo, hi):
        t, r = int(f_ts[j]), float(f_rate[j])
        if t == t0 and not (side * r > 0):
            continue
        idx = int(np.searchsorted(bar_ts, t, side="right") - 1)
        idx = min(max(idx, 0), len(close) - 1)
        px = float(close[idx])
        out.append(dict(t=t, rate=r, px=px, cash=-side * qty * px * r))
    return out


# ══════════════════════════════════════════════════════ single-position book
def sim_single(df, *, long_entry, short_entry, long_exit=None, short_exit=None,
               stop_dist=None, tp_dist=None, levels_fn=None, time_stop_bars=None,
               cooldown_after_entry=0, cooldown_after_exit=0,
               one_per_day=False, risk_frac=None, max_leverage=3.0,
               size_frac=1.0, costs: Costs, funding=None, init_equity=10000.0):
    """Execute one directional book.

    `stop_dist` / `tp_dist` are PRICE distances evaluated on the signal bar and
    applied to the FILL price (the declared 'from entry' reading).  `time_stop_bars`
    is bars held: the exit fills at the open of entry_i + time_stop_bars, so the
    decision is taken at the close of the previous bar.
    """
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["open_ts"].to_numpy(np.int64)
    n = len(df)
    day = pd.to_datetime(ts, unit="ms", utc=True).floor("1D").to_numpy()
    le = np.asarray(long_entry, bool)
    se = np.asarray(short_entry, bool)
    lx = np.zeros(n, bool) if long_exit is None else np.asarray(long_exit, bool)
    sx = np.zeros(n, bool) if short_exit is None else np.asarray(short_exit, bool)
    sd = np.full(n, np.nan) if stop_dist is None else np.asarray(stop_dist, float)
    td = np.full(n, np.nan) if tp_dist is None else np.asarray(tp_dist, float)
    f_ts, f_rate = funding if funding is not None else (np.array([], np.int64),
                                                        np.array([], float))

    eq = float(init_equity)
    curve = np.zeros(n)
    rows = []
    pos = 0
    qty = 0.0
    entry_px = 0.0
    entry_i = -1
    entry_ts = 0
    stop_px = np.nan
    tp_px = np.nan
    entry_fee = 0.0
    eq_at_entry = 0.0
    pend_entry = 0
    pend_signal_i = -1
    pend_exit = False
    pend_why = "signal"
    last_entry_i = -10**9
    last_exit_i = -10**9
    last_entry_day = None
    fees_paid = 0.0
    funding_paid = 0.0
    same_bar = 0
    mae = 0.0

    def close_trade(i, px, why):
        nonlocal eq, pos, qty, entry_fee, fees_paid, funding_paid
        gross = pos * qty * (px - entry_px)
        fee = qty * abs(px) * costs.fee_bps * BPS
        fcash, nf = funding_cash(f_ts, f_rate, entry_ts, int(ts[i]), ts, c, qty, pos)
        pnl = gross - fee + fcash - entry_fee
        eq += gross - fee + fcash
        fees_paid += fee
        funding_paid += -fcash
        rows.append(dict(entry_ts=entry_ts, exit_ts=int(ts[i]), side=pos,
                         entry_px=entry_px, exit_px=px, qty=qty, pnl=pnl,
                         ret_pct=100.0 * pnl / max(eq_at_entry, 1e-9),
                         bars=i - entry_i, exit_reason=why,
                         fees=fee + entry_fee, funding=fcash, n_funding=nf,
                         equity_after=eq, mae_pct=mae))
        pos, qty, entry_fee = 0, 0.0, 0.0

    for i in range(n):
        # 1. act on the prior close's decision at this open
        if pos != 0 and pend_exit:
            close_trade(i, o[i] * (1 - pos * costs.slip_bps * BPS), pend_why)
            pend_exit = False
            pend_why = "signal"
            last_exit_i = i

        if pos == 0 and pend_entry != 0:
            side = pend_entry
            fill = o[i] * (1 + side * costs.slip_bps * BPS)
            sig_i = pend_signal_i
            sdist = sd[sig_i]
            tdist = td[sig_i]
            eq_before = eq
            if levels_fn is not None:
                lv_stop, lv_tp = levels_fn(side, fill, sig_i)
                stop_px = float(lv_stop)
                tp_px = float(lv_tp)
                sdist = abs(fill - stop_px) if np.isfinite(stop_px) else np.nan
                tdist = abs(tp_px - fill) if np.isfinite(tp_px) else np.nan
            else:
                stop_px = fill - side * sdist if np.isfinite(sdist) else np.nan
                tp_px = fill + side * tdist if np.isfinite(tdist) else np.nan
            # a stop already through the fill makes the setup invalid
            invalid = bool(np.isfinite(stop_px) and (
                (side > 0 and stop_px >= fill) or
                (side < 0 and stop_px <= fill)))
            if invalid:
                pend_entry, pend_signal_i = 0, -1
            else:
                if risk_frac is not None and np.isfinite(sdist) and sdist > 0:
                    q = (risk_frac * eq_before) / sdist
                    q = min(q, max_leverage * eq_before / fill)
                else:
                    q = size_frac * eq_before / fill
                fee = q * fill * costs.fee_bps * BPS
                eq -= fee
                fees_paid += fee
                pos, qty, entry_px, entry_i, entry_ts = side, q, fill, i, int(ts[i])
                eq_at_entry = eq_before
                entry_fee = fee
                last_entry_i = i
                last_entry_day = day[i]
                pend_entry = 0
                pend_signal_i = -1
                mae = 0.0

        # 2. intrabar stop / target, SL first
        if pos != 0:
            if pos > 0:
                hit_s = np.isfinite(stop_px) and l[i] <= stop_px
                hit_t = np.isfinite(tp_px) and h[i] >= tp_px
                adverse = min(0.0, 100.0 * (l[i] / entry_px - 1.0))
            else:
                hit_s = np.isfinite(stop_px) and h[i] >= stop_px
                hit_t = np.isfinite(tp_px) and l[i] <= tp_px
                adverse = min(0.0, 100.0 * (h[i] / entry_px - 1.0))
            mae = min(mae, adverse)
            if hit_s or hit_t:
                if hit_s and hit_t:
                    same_bar += 1
                if hit_s:
                    # gap through the stop fills at the open, adverse
                    raw = o[i] if (pos > 0 and o[i] <= stop_px) or \
                                   (pos < 0 and o[i] >= stop_px) else stop_px
                    px = raw * (1 - pos * costs.slip_bps * BPS)
                    close_trade(i, px, "stop")
                else:
                    raw = o[i] if (pos > 0 and o[i] >= tp_px) or \
                                   (pos < 0 and o[i] <= tp_px) else tp_px
                    px = raw * (1 - pos * costs.slip_bps * BPS)
                    close_trade(i, px, "target")
                last_exit_i = i

        # 3. time stop, decided at this close, filled next open
        if (pos != 0 and time_stop_bars and (i - entry_i) >= time_stop_bars - 1
                and not pend_exit):
            pend_exit, pend_why = True, "time_stop"

        # 4. signal exit at this close
        if pos != 0 and not pend_exit:
            if (pos > 0 and lx[i]) or (pos < 0 and sx[i]):
                pend_exit, pend_why = True, "signal"

        # 5. entry decision at this close
        if pos == 0 and not pend_exit and pend_entry == 0:
            ok = True
            if one_per_day and last_entry_day is not None and i + 1 < n:
                ok = day[i + 1] != last_entry_day
            if cooldown_after_entry and (i - last_entry_i) < cooldown_after_entry:
                ok = False
            if cooldown_after_exit and (i - last_exit_i) < cooldown_after_exit:
                ok = False
            if ok:
                if le[i] and not se[i]:
                    pend_entry, pend_signal_i = 1, i
                elif se[i] and not le[i]:
                    pend_entry, pend_signal_i = -1, i

        curve[i] = eq + (pos * qty * (c[i] - entry_px) if pos != 0 else 0.0)

    if pos != 0:
        close_trade(n - 1, c[-1], "end_of_data")
        curve[-1] = eq

    tr = pd.DataFrame(rows)
    return {"trades": tr, "equity": curve, "fees": fees_paid,
            "funding": funding_paid, "final_equity": eq,
            "same_bar_stop_target": int(same_bar)}


# ══════════════════════════════════════════════════════ two-leg funding pair
def sim_pair(df_a, df_b, *, entry_at_open, exit_at_open, stop_at_close,
             entry_frac, costs: Costs, fund_a=None, fund_b=None,
             max_hold_bars=None, spread_stop=None, init_equity=10000.0):
    """Dollar-neutral pair entered/exited at bar opens, marked bar by bar.

    `entry_at_open[i]` = +1 long A / short B, -1 the reverse, 0 none.
    `exit_at_open[i]` = True closes the book at this open (time or D exit).
    `stop_at_close[i]` = True schedules a close at the NEXT open (spread stop).
    """
    a, b = df_a.reset_index(drop=True), df_b.reset_index(drop=True)
    n = min(len(a), len(b))
    a, b = a.iloc[:n], b.iloc[:n]
    oa, ob = a["open"].to_numpy(float), b["open"].to_numpy(float)
    ca, cb = a["close"].to_numpy(float), b["close"].to_numpy(float)
    ts = a["open_ts"].to_numpy(np.int64)
    fa_ts, fa_r = fund_a if fund_a else (np.array([], np.int64), np.array([], float))
    fb_ts, fb_r = fund_b if fund_b else (np.array([], np.int64), np.array([], float))
    ea = np.asarray(entry_at_open, int)
    xo = np.asarray(exit_at_open, bool)
    sc = np.asarray(stop_at_close, bool)

    eq = float(init_equity)
    curve = np.zeros(n)
    rows = []
    pos = 0
    qa = qb = 0.0
    pa = pb = 0.0
    entry_i = -1
    entry_ts = 0
    eq_at_entry = 0.0
    fee_in = 0.0
    pending_exit = False
    pending_why = "signal"
    fees_paid = 0.0
    funding_paid = 0.0

    def close_pair(i, why):
        nonlocal eq, pos, qa, qb, fee_in, fees_paid, funding_paid
        # pos = +1 long A / short B, -1 the reverse: the whole book flips sign
        pnl_gross = pos * (qa * (oa[i] - pa) - qb * (ob[i] - pb))
        fee = (qa * oa[i] + qb * ob[i]) * costs.fee_bps * BPS
        slip = (qa * oa[i] + qb * ob[i]) * costs.slip_bps * BPS
        fa_c, nfa = funding_cash(fa_ts, fa_r, entry_ts, int(ts[i]), ts, ca, qa, pos)
        fb_c, nfb = funding_cash(fb_ts, fb_r, entry_ts, int(ts[i]), ts, cb, qb, -pos)
        fcash = fa_c + fb_c
        # the entry cost was already deducted from equity at the fill
        pnl = pnl_gross - fee - slip + fcash - fee_in
        eq += pnl_gross - fee - slip + fcash
        fees_paid += fee + slip
        funding_paid += -fcash
        rows.append(dict(entry_ts=entry_ts, exit_ts=int(ts[i]), side=pos,
                         entry_px=pa, exit_px=oa[i], qty=qa, pnl=pnl,
                         ret_pct=100.0 * pnl / max(eq_at_entry, 1e-9),
                         bars=i - entry_i, exit_reason=why,
                         fees=fee + slip + fee_in, funding=fcash,
                         funding_a=fa_c, funding_b=fb_c,
                         n_funding=nfa + nfb, equity_after=eq))
        pos, qa, qb, fee_in = 0, 0.0, 0.0, 0.0

    for i in range(n):
        if pos != 0 and (pending_exit or xo[i]):
            close_pair(i, "signal" if xo[i] else pending_why)
            pending_exit = False
            pending_why = "signal"
        if pos == 0 and ea[i] != 0:
            pos = int(ea[i])
            pa, pb = oa[i], ob[i]
            qa = entry_frac * eq / pa
            qb = entry_frac * eq / pb
            fee = (qa * pa + qb * pb) * (costs.fee_bps + costs.slip_bps) * BPS
            eq -= fee
            fees_paid += fee
            fee_in = fee
            entry_i, entry_ts = i, int(ts[i])
            eq_at_entry = eq + fee
        if pos != 0 and sc[i] and not pending_exit:
            pending_exit, pending_why = True, "signal"
        if pos != 0 and max_hold_bars and (i - entry_i) >= max_hold_bars - 1 \
                and not pending_exit:
            pending_exit, pending_why = True, "max_hold"
        if pos != 0 and spread_stop is not None and not pending_exit:
            # the document's spread is (long-leg return - short-leg return), so
            # the sign flips with the direction of the pair
            spread = pos * ((ca[i] / pa - 1.0) - (cb[i] / pb - 1.0))
            if spread <= -spread_stop:
                pending_exit, pending_why = True, "spread_stop"
        curve[i] = eq + (pos * (qa * (ca[i] - pa) - qb * (cb[i] - pb)) if pos != 0 else 0.0)

    if pos != 0:
        close_pair(n - 1, "end_of_data")
        curve[-1] = eq
    return {"trades": pd.DataFrame(rows), "equity": curve, "fees": fees_paid,
            "funding": -funding_paid, "final_equity": eq}


# ══════════════════════════════════════════════════════ multi-leg basket
def sim_basket(dfs, target_at_open, *, costs: Costs, fundings=None,
               per_leg_stop=None, book_stop=None, init_equity=10000.0):
    """Equal-weight-style rotation book with per-leg stops and a book kill.

    `target_at_open` is a (T x N) matrix of signed equity fractions to hold
    AFTER the open of each bar (NaN = leave the book unchanged).  A rebalance
    row is any row where the matrix is finite.  Weights are fractions of
    equity, so gross exposure is sum(|w|).

    Costs: (fee + slip) bps on the traded notional |w_new - w_old| * equity.
    Funding: per leg, per settlement, on |w| * equity at the bar close.
    Per-leg stop: price distance from the leg's entry fill; the leg is closed
    intrabar and stays flat until the next rebalance.
    Book kill: if equity falls `book_stop` below its level at the period start,
    the book is flattened at the next open and stays flat until the next
    rebalance.
    """
    n = min(len(d) for d in dfs)
    dfs = [d.iloc[:n].reset_index(drop=True) for d in dfs]
    N = len(dfs)
    O = np.column_stack([d["open"].to_numpy(float) for d in dfs])
    C = np.column_stack([d["close"].to_numpy(float) for d in dfs])
    H = np.column_stack([d["high"].to_numpy(float) for d in dfs])
    L = np.column_stack([d["low"].to_numpy(float) for d in dfs])
    ts = dfs[0]["open_ts"].to_numpy(np.int64)
    T = np.asarray(target_at_open, float)
    fundings = fundings or [None] * N
    fdata = []
    for f in fundings:
        fdata.append(f if f else (np.array([], np.int64), np.array([], float)))

    eq = float(init_equity)
    curve = np.zeros(n)
    w = np.zeros(N)
    entry_px = np.full(N, np.nan)
    rows = []
    period_start_eq = eq
    period_start_i = 0
    period_ret = 0.0
    had_pos = False
    flatten_pending = False
    book_kill_fired = 0
    fees_paid = 0.0
    funding_paid = 0.0
    funding_gross_paid = 0.0
    funding_gross_received = 0.0
    period_fee = 0.0
    period_fund = 0.0
    turnover = 0.0
    traded_notional = 0.0

    for i in range(n):
        # segment 1: previous close -> this open on the carried book
        if i > 0:
            r_open = O[i] / C[i - 1] - 1.0
            eq *= 1.0 + float(np.dot(w, r_open))

        rebalance = np.isfinite(T[i]).any()
        if flatten_pending:
            close_cost = abs(w).sum() * eq * costs.side_bps * BPS
            eq -= close_cost
            fees_paid += close_cost
            period_fee += close_cost
            turnover += abs(w).sum()
            traded_notional += abs(w).sum() * eq
            w[:] = 0.0
            entry_px[:] = np.nan
            flatten_pending = False

        if rebalance:
            tgt = np.where(np.isfinite(T[i]), T[i], 0.0)
            delta = tgt - w
            pre = eq
            # All traded notional is |target - w|, including a sign flip
            # (close the old leg, open the new one).  Every cost is counted once.
            cost = float(np.abs(delta).sum()) * eq * costs.side_bps * BPS
            traded = float(np.abs(delta).sum())
            eq -= cost
            fees_paid += cost
            period_fee += cost
            turnover += traded
            traded_notional += traded * eq
            for j in range(N):
                if tgt[j] == 0.0:
                    entry_px[j] = np.nan
                elif w[j] == 0.0 or np.sign(tgt[j]) != np.sign(w[j]):
                    entry_px[j] = O[i, j]
            # finalize the old period (its costs to date included)
            pnl = eq - period_start_eq
            if had_pos:
                rows.append(dict(entry_ts=int(ts[period_start_i]),
                                 exit_ts=int(ts[i]), side=0,
                                 entry_px=float(period_start_eq), exit_px=float(eq),
                                 qty=0.0, pnl=float(pnl),
                                 ret_pct=100.0 * pnl / max(period_start_eq, 1e-9),
                                 bars=i - period_start_i, exit_reason="rebalance",
                                 fees=float(period_fee), funding=float(period_fund),
                                 n_funding=0,
                                 equity_after=float(eq), period_ret=float(period_ret)))
                period_start_eq = eq
                period_fee = 0.0
                period_fund = 0.0
            else:
                # opening from flat: the cost belongs to the period that is
                # starting, so its pnl begins at the pre-cost equity
                period_start_eq = pre
            period_start_i = i
            period_ret = 0.0
            had_pos = False
            w = tgt.copy()
            if abs(w).sum() > 0:
                had_pos = True

        # segment 2: this open -> this close, with per-leg stops intrabar
        r_seg = C[i] / O[i] - 1.0
        contrib = 0.0
        for j in range(N):
            if w[j] == 0.0:
                continue
            hit = False
            r_leg = r_seg[j]
            if per_leg_stop is not None and np.isfinite(entry_px[j]):
                if w[j] > 0:
                    stop_px = entry_px[j] * (1.0 - per_leg_stop)
                    if O[i, j] <= stop_px:
                        # gapped through the stop at the open: the gap loss was
                        # already carried by the previous-close -> open segment
                        r_leg, hit = 0.0, True
                    elif L[i, j] <= stop_px:
                        r_leg, hit = stop_px / O[i, j] - 1.0, True
                else:
                    stop_px = entry_px[j] * (1.0 + per_leg_stop)
                    if O[i, j] >= stop_px:
                        r_leg, hit = 0.0, True
                    elif H[i, j] >= stop_px:
                        r_leg, hit = stop_px / O[i, j] - 1.0, True
            contrib += w[j] * r_leg
            if hit:
                cost = abs(w[j]) * eq * costs.side_bps * BPS
                eq -= cost
                fees_paid += cost
                period_fee += cost
                turnover += abs(w[j])
                traded_notional += abs(w[j]) * eq
                entry_px[j] = np.nan
                w[j] = 0.0
        eq *= 1.0 + contrib

        # funding, per leg, settlements inside this bar
        if i > 0:
            for j in range(N):
                if w[j] == 0.0:
                    continue
                f_ts, f_r = fdata[j]
                if len(f_ts) == 0:
                    continue
                lo = int(np.searchsorted(f_ts, int(ts[i - 1]), side="right"))
                hi = int(np.searchsorted(f_ts, int(ts[i]), side="right"))
                if hi <= lo:
                    continue
                # the leg is a fixed fraction of equity, so the notional at the
                # settlement mark is |w| * equity; no price re-scaling is applied
                cash = -float(np.sign(w[j])) * abs(w[j]) * eq * float(f_r[lo:hi].sum())
                eq += cash
                period_fund += cash
                funding_paid += -cash
                if cash < 0:
                    funding_gross_paid += -cash
                else:
                    funding_gross_received += cash

        period_ret = eq / max(period_start_eq, 1e-9) - 1.0
        if (book_stop is not None and period_ret <= -book_stop
                and abs(w).sum() > 0 and not flatten_pending):
            flatten_pending = True
            book_kill_fired += 1
        curve[i] = eq

    pnl = eq - period_start_eq
    if had_pos:
        rows.append(dict(entry_ts=int(ts[period_start_i]), exit_ts=int(ts[-1]), side=0,
                         entry_px=float(period_start_eq), exit_px=float(eq), qty=0.0,
                         pnl=float(pnl), ret_pct=100.0 * pnl / max(period_start_eq, 1e-9),
                         bars=n - period_start_i, exit_reason="end_of_data",
                         fees=float(period_fee), funding=float(period_fund),
                         n_funding=0, equity_after=float(eq),
                         period_ret=float(period_ret)))
    tr = pd.DataFrame(rows)
    return {"trades": tr, "equity": curve, "fees": fees_paid,
            "funding": -funding_paid, "final_equity": eq,
            "funding_gross_paid": float(funding_gross_paid),
            "funding_gross_received": float(funding_gross_received),
            "turnover_units": float(turnover),
            "traded_notional_frac": float(traded_notional / max(init_equity, 1e-9)),
            "book_kill_fired": int(book_kill_fired)}
