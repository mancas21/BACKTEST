#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smqe_engine.py — port of code/smqe_v2_strategy.pine:
"Smart Money Quant Engine [SMC + MA-OB + CVRMD] v2 — Strategy" (Pine v6,
attachment copied BYTE-IDENTICAL from
Downloads/fingrad-entry scanner/smqe_v2_strategy.pine, sha256 031730fabb9cc289...).

THE PINE, READ END TO END
    strategy(...) initial_capital=10000 USD, commission 0.06% PER SIDE,
    slippage=0 ticks, pyramiding=0, margin 33% (3x), calc_on_every_tick=false,
    process_orders_on_close=TRUE -> signals evaluate on the confirmed bar and
    entries/reversals FILL AT THAT BAR'S CLOSE.

    Three engines are shipped: [A] Smart Money Concepts, [B] MA Order Blocks,
    [C] the CVRMD v1.1 signal core. [A] and [B] feed ONLY the confluence gates
    (gateMaTrend / gateSmc / gateOb / gateZone), and EVERY gate is an opt-in
    input that ships FALSE — the Pine's own tooltips say the gates are "NOT
    part of the validated CVRMD backtest". With the shipped inputs the trading
    logic is therefore exactly:

        coreLong  = bullDiv and nearLowBand  and cvdBull and rsiLongOK
        coreShort = bearDiv and nearHighBand and cvdBear and rsiShortOK

      bullDiv/bearDiv : MACD(12,26,9) histogram divergence on ta.pivotlow/
                        ta.pivothigh(3,3), pivot separation 5..60 bars, price
                        lower-low with higher osc (long; mirrored short),
                        evaluated on the pivot-CONFIRMATION bar (3 bars after
                        the pivot).
      nearLowBand     : session VWAP (UTC day anchor, Welford recursion, hlc3
                        volume-weighted) minus 1.0 x volume-weighted SD; the
                        bar's low traded at/below the band and CLOSED back
                        above it. Requires barsInAnchor >= 5 and sd > 0.
      cvdBull/Bear    : EMA(3) of cum(CLV x volume) minus its value 5 bars
                        ago, strictly > / < 0.
      rsiLongOK       : RSI(14) <= 30+5 or (RSI < 50 and rising)
      rsiShortOK      : RSI(14) >= 70-5 or (RSI > 50 and falling)

    [A] and [B] are DISPLAY engines in the shipped configuration; they are NOT
    ported. This is declared, not hidden: the port covers the shipped (default)
    strategy, and the gates are the Pine author's own unvalidated extras.

EXECUTION LAYER (what makes this different from the repo's cvrmd adapter)
    * Stop distance  stopD = max(ATR(14) x 1.5, close x 0.2%)  — the 0.2% Min
      Stop % floor is NEW vs cvrmd_backtest.py (which used bare ATR x 1.5).
    * Sizing         mult = min(1% risk / stopFrac, 3.0x); qty = equity x mult
      / close, equity = strategy.equity marked at the signal close (includes
      unrealized when reversing). Compounds.
    * Bracket        TP1 = 50% of the position at limit(VWAP if on the far
      side of close, else 1.5R) with the frozen stop as its stop leg; TP2 =
      the remaining 100% at 2R with the same stop. Reversal = strategy.entry
      on the opposite side: TV closes what remains and reopens at the SAME
      close.
    * Risk devices   funding ledger (constant 0.01%/8h, longs pay, shorts
      receive, accrued per bar at tf/8h on the surviving position — the Pine
      books it OUTSIDE strategy.equity: it feeds the daily breaker and the
      reported net return, NOT sizing or the killswitch); daily-loss breaker
      3% of day-start equity net of today's funding (halts new entries for the
      rest of the UTC day); equity-DD killswitch 30% from peak (permanent).

DECLARED PORTING CONVENTIONS (each pinned by a known-answer test in
code/_smqe_audit.py)
    - Fill at the signal bar's close (process_orders_on_close=true). Exit
      orders are live from the NEXT bar.
    - Intra-bar exit order, evaluated per bar: (1) open gapped through the
      stop -> fill AT THE OPEN; (2) the bar touches the stop -> SL-FIRST ON
      TIES (repo convention): a bar touching both the stop and any target
      fills the WHOLE remaining position at the stop, no target fills;
      (3) open gapped through TP2 -> fill at the open (a TV limit gapped
      through fills at the open); (4) otherwise limits fill in price order
      from the entry side: TP1 half at its limit, then TP2 closes whatever
      remains (if the VWAP target sits beyond 2R, TP2 is reached first and
      closes everything — TV's TP2 qty_percent is 100 of the REMAINING
      position). When the open gaps beyond TP2 with TP1 still pending, both
      TV orders fill at the open; the port merges them into one fill at the
      same price — PnL- and fee-identical. Every fill carries adverse
      slippage; bracket levels are anchored at the UN-slipped signal close
      (fingrad precedent: the bracket is anchored at the signal close).
    - Flip: opposite signal while positioned, with cooldown and entry gates
      OK -> close what remains at this close, open the opposite side at the
      SAME close, sized off strategy.equity marked BEFORE the flip fills.
      A flat re-entry on the same bar an intra-bar stop-out happened goes
      through the normal entry branch (same cooldown clock — TV counts from
      the original entry bar). The reversal branches also require a valid
      stop distance (moot: the 0.2% floor makes stopD > 0 by construction).
    - Costs on EVERY fill (entry, each partial, the flip close and the new
      flip entry): notional x fee, adverse slip on the fill price. The Pine
      declares 0.06%/side + 0 slip; the repo gate is 5 bps fee + 0.5 bps slip
      per side. All three views (repo / pine / zero) are measured inside every
      artifact on the SAME signals; drag_pp = zero-cost net return minus the
      primary net return, so it isolates pure transaction costs (funding is
      charged identically in all three views).
    - Funding starts the bar AFTER the entry bar (the Pine accrues at the top
      of the script, before the entry block runs) on the position that
      SURVIVED the bar's intra-bar fills, at that bar's close. Funding is
      tracked OUTSIDE broker equity (Pine design): sizing, the killswitch,
      peak/maxDD use equity net of nothing but fees; funding feeds the daily
      breaker (netted against today) and the reported net return.
    - Day boundary = UTC day of the bar's open time; the first bar counts as
      a day start. Day-start equity is the marked equity at that bar's close
      (after intra-bar fills), and the day's funding accrued before the reset
      is excluded from the breaker's day P&L (Pine order). Breaker before
      killswitch, both before entries, peak/maxDD before entries (Pine order).
    - ta.ema seeds with the first value (recursive from bar 0); ta.rma /
      ta.atr / ta.rsi seed with the SMA of the first `length` values. Pivots
      are STRICT on both sides (ties produce no pivot — the repo's validated
      CVRMD port convention). R expectancy here is computed ALIGNED per cycle
      (pnl / risk-at-entry): the Pine's dashboard R ledger pops one risk per
      closed-trade event, so after a TP1 partial it reads the NEXT trade's
      risk — a dashboard-only quirk, not ported.
    - The Pine's sim window inputs (2024-01-01..2030) are exposed as
      sim_start/sim_end params; default = full data history (the repo
      convention), with a separate campaign pass at the Pine's 2024+ window.
    - Trading starts at warmup=500 bars (cvrmd port precedent); TV's warmup is
      implicit in indicator na values, which gate the signals anyway.

METHODOLOGY VIEWS (added 2026-10-25 after the repo methodology audit; every
campaign artifact carries them so the audit's M4/M8 questions are measured,
not asserted):
    * fill_mode="next_open": identical signals decided at identical closes,
      filled at the NEXT bar's open (slipped). Bracket levels, the TP1 VWAP
      comparison and sizing stay anchored at the SIGNAL close (the levels the
      Pine's orders carry); the bracket is live during the fill bar. The
      metric timing_drag_pp = primary net return minus this view's net
      return IS the same-close execution assumption, priced.
    * exposure_pct / bh_inmarket_pct: fraction of scored bars in position at
      the close, and the compounded passive return of holding the asset over
      EXACTLY those bars — the exposure-matched comparator the raw B&H gate
      lacks (M4). excess_vs_inmarket_pp is the strategy's return over it.

NOT modelled: TV margin (exposure is bounded by the 3x notional cap), the
Premium bar magnifier (exits are bar-level, stop-first on ties), the
dashboard's votes/labels, and the alert plumbing.

Data: harness klines CSV (open_ts,open,high,low,close,volume), any tf.
"""

import os
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INIT = 10000.0                       # the Pine's initial_capital

TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}

# The Pine's shipped inputs; the audited strategy is FIXED at these (emaadx /
# fingrad precedent: geometry is not a knob). Only the window and the cost
# view are parameters.
PINE = dict(
    # signal core
    cvd_smooth=3, cvd_slope_len=5, band_mult=1.0,
    rsi_len=14, rsi_os=30.0, rsi_ob=70.0,
    macd_fast=12, macd_slow=26, macd_sig=9,
    piv_l=3, piv_r=3, min_div_bars=5, max_div_bars=60,
    # execution
    risk_pct=1.0, max_lev=3.0, atr_len=14, atr_mult=1.5,
    tp1_r=1.5, tp2_r=2.0, cooldown=3, min_stop_pct=0.2,
    fund_rate_8h_pct=0.01, daily_loss_pct=3.0, max_dd_limit=30.0,
    allow_long=True, allow_short=True,
    warmup=500,
)

COSTS = {
    "repo": dict(fee=0.0005, slip=0.00005),  # repo 2026-10-25: 5 + 0.5 = 11 bps RT
    "pine": dict(fee=0.0006, slip=0.0),      # the Pine header: 0.06%/side
    "zero": dict(fee=0.0, slip=0.0),
}


# ------------------------------------------------------------- primitives
def ema_pine(x, n):
    """Pine ta.ema: recursive from bar 0, seeded with the first value."""
    x = np.asarray(x, float)
    a = 2.0 / (n + 1.0)
    out = np.empty_like(x)
    prev = x[0]
    out[0] = prev
    for i in range(1, len(x)):
        prev = a * x[i] + (1.0 - a) * prev
        out[i] = prev
    return out


def rma_pine(x, n):
    """Pine ta.rma: SMA-seeded over the first `n` values, then Wilder."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    s = 0.0
    prev = np.nan
    for i in range(len(x)):
        if i + 1 < n:
            s += x[i]
        elif i + 1 == n:
            s += x[i]
            prev = s / n
            out[i] = prev
        else:
            prev = (prev * (n - 1) + x[i]) / n
            out[i] = prev
    return out


def true_range(h, l, c):
    pc = np.roll(c, 1)
    pc[0] = c[0]
    a = h - l
    b = np.abs(h - pc)
    d = np.abs(l - pc)
    return np.fmax(a, np.fmax(b, d))


def atr_pine(h, l, c, n):
    """Pine ta.atr = ta.rma(ta.tr, n)."""
    return rma_pine(true_range(h, l, c), n)


def rsi_pine(c, n):
    """Pine ta.rsi: Wilder RMA of gains/losses; down-average == 0 -> 100
    (the cvrmd port's convention, pinned by the audit's Wilder case)."""
    c = np.asarray(c, float)
    d = np.diff(c, prepend=c[0])
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    au = rma_pine(up, n)
    ad = rma_pine(dn, n)
    out = np.full(len(c), np.nan)
    ok = ~np.isnan(au) & ~np.isnan(ad)
    with np.errstate(invalid="ignore", divide="ignore"):
        rs = au[ok] / np.where(ad[ok] == 0, 1.0, ad[ok])
        out[ok] = np.where(ad[ok] == 0, 100.0, 100.0 - 100.0 / (1.0 + rs))
    return out


# ------------------------------------------------------------- signals
def session_vwap(t, h, l, c, v):
    """Pine's Welford recursion, UTC-day anchor ('Session'), verbatim order:
    on the anchor bar vSumV = volume_i, vMean = hlc3_i, vM2 = 0; else the
    running update. Returns (vwap, sd, barsInAnchor, ready)."""
    n = len(t)
    vwap = np.full(n, np.nan)
    vsd = np.zeros(n)
    ina = np.zeros(n, dtype=np.int64)
    day = t // 86400000
    cur = None
    vsum = vmean = vm2 = 0.0
    cnt = 0
    for i in range(n):
        hlc3 = (h[i] + l[i] + c[i]) / 3.0
        if day[i] != cur:
            cur = day[i]
            vsum = v[i]
            vmean = hlc3
            vm2 = 0.0
            cnt = 1
        else:
            vv = v[i]
            vsum += vv
            d = hlc3 - vmean
            vmean += (d * vv / vsum) if vsum > 0 else 0.0
            vm2 += vv * d * (hlc3 - vmean)
            cnt += 1
        ina[i] = cnt
        if vsum > 0:
            vwap[i] = vmean
            vsd[i] = np.sqrt(max(vm2 / vsum, 0.0))
    ready = (ina >= 5) & (vsd > 0)
    return vwap, vsd, ina, ready


def _rolling_extreme(x, n, side, shift):
    """min/max of the n bars ending at i+shift (strict pivot tests). NaN
    where the window is incomplete."""
    import pandas as pd
    s = pd.Series(np.asarray(x, float))
    r = s.rolling(n).min() if side == "min" else s.rolling(n).max()
    return r.shift(shift).to_numpy()


def _divergence(h, l, osc, P):
    """MACD-histogram divergence on strict 3/3 pivots, sep 5..60, evaluated
    on the pivot-CONFIRMATION bar (piv_r after the pivot). Pine: lastLowPx <
    prev and lastLowOsc > prev (long); mirrored short. Ties -> no pivot."""
    pl_, pr_ = P["piv_l"], P["piv_r"]
    mind, maxd = P["min_div_bars"], P["max_div_bars"]
    n = len(l)
    lo_l = _rolling_extreme(l, pl_, "min", 1)      # min of l[i-pl_ .. i-1]
    lo_r = _rolling_extreme(l, pr_, "min", -pr_)   # min of l[i+1 .. i+pr_]
    hi_l = _rolling_extreme(h, pl_, "max", 1)
    hi_r = _rolling_extreme(h, pr_, "max", -pr_)
    with np.errstate(invalid="ignore"):
        piv_low = (l < lo_l) & (l < lo_r)
        piv_high = (h > hi_l) & (h > hi_r)
    bull = np.zeros(n, bool)
    bear = np.zeros(n, bool)
    n_l = n_h = 0
    lastLP = lastLO = lastLB = None
    prevLP = prevLO = prevLB = None
    lastHP = lastHO = lastHB = None
    prevHP = prevHO = prevHB = None
    for i in range(n):
        j = i - pr_
        if j >= 0 and piv_low[j]:
            prevLP, prevLO, prevLB = lastLP, lastLO, lastLB
            lastLP, lastLO, lastLB = l[j], osc[j], j
            n_l += 1
            if (prevLP is not None and lastLP < prevLP and lastLO > prevLO
                    and mind <= (lastLB - prevLB) <= maxd):
                bull[i] = True
        if j >= 0 and piv_high[j]:
            prevHP, prevHO, prevHB = lastHP, lastHO, lastHB
            lastHP, lastHO, lastHB = h[j], osc[j], j
            n_h += 1
            if (prevHP is not None and lastHP > prevHP and lastHO < prevHO
                    and mind <= (lastHB - prevHB) <= maxd):
                bear[i] = True
    return bull, bear, n_l, n_h


def signals(t, o, h, l, c, v, P):
    """The CVRMD core with every confluence gate at its shipped (off) value."""
    n = len(c)
    hl_r = np.maximum(h - l, 1e-7)
    clv = ((c - l) - (h - c)) / hl_r
    d_proxy = clv * np.nan_to_num(v, nan=0.0)
    cvd_cum = np.cumsum(d_proxy)
    cvd_sm = ema_pine(cvd_cum, P["cvd_smooth"])
    k = P["cvd_slope_len"]
    slope = np.zeros(n)
    slope[k:] = cvd_sm[k:] - cvd_sm[:-k]
    cvd_bull = slope > 0
    cvd_bear = slope < 0

    vwap, vsd, _ina, ready = session_vwap(t, h, l, c, v)
    b = P["band_mult"]
    vb_l = vwap - vsd * b
    vb_u = vwap + vsd * b
    with np.errstate(invalid="ignore"):
        near_low = ready & (l <= vb_l) & (vb_l < c)
        near_high = ready & (h >= vb_u) & (c < vb_u)

    rsi = rsi_pine(c, P["rsi_len"])
    rsi_prev = np.roll(rsi, 1)
    rsi_prev[0] = np.nan
    with np.errstate(invalid="ignore"):
        rsi_long_ok = (rsi <= P["rsi_os"] + 5.0) | ((rsi < 50.0) & (rsi > rsi_prev))
        rsi_short_ok = (rsi >= P["rsi_ob"] - 5.0) | ((rsi > 50.0) & (rsi < rsi_prev))

    macd_line = ema_pine(c, P["macd_fast"]) - ema_pine(c, P["macd_slow"])
    macd_sig = ema_pine(macd_line, P["macd_sig"])
    osc = macd_line - macd_sig

    bull_div, bear_div, n_pl, n_ph = _divergence(h, l, osc, P)

    long_ok = bull_div & near_low & cvd_bull & rsi_long_ok
    short_ok = bear_div & near_high & cvd_bear & rsi_short_ok

    atr_x = atr_pine(h, l, c, P["atr_len"])
    stop_d = np.maximum(atr_x * P["atr_mult"], c * P["min_stop_pct"] / 100.0)

    return dict(long_ok=long_ok, short_ok=short_ok, vwap=vwap, stop_d=stop_d,
                atr_x=atr_x, cvd_bull=cvd_bull, cvd_bear=cvd_bear,
                near_low=near_low, near_high=near_high,
                rsi_long_ok=rsi_long_ok, rsi_short_ok=rsi_short_ok,
                bull_div=bull_div, bear_div=bear_div, osc=osc, rsi=rsi,
                n_piv_l=n_pl, n_piv_h=n_ph)


# ------------------------------------------------------------- executor
def execute(t, o, h, l, c, S, P, fee, slip, tf_minutes,
            sim_start_ms=None, sim_end_ms=None, fill_mode="close"):
    """The strategy layer. One position at a time; conventions as declared in
    the module docstring.

    fill_mode="close"     entries/reversals fill at the SIGNAL bar's close
                          (the Pine's process_orders_on_close=true).
    fill_mode="next_open" the same signals, decided at the same closes, fill
                          at the NEXT bar's open (slipped); bracket levels,
                          TP1's VWAP comparison and sizing stay anchored at
                          the SIGNAL bar's close (the levels TV's orders
                          would carry); the bracket is live during the fill
                          bar itself (the order predates the open). This is
                          the METHODOLOGY SENSITIVITY VIEW (audit M8): it
                          measures how much of the result depends on
                          same-close execution."""
    n = len(c)
    fund_frac = (tf_minutes * 60.0) / 28800.0
    fund_rate = P["fund_rate_8h_pct"] / 100.0
    warm = P["warmup"]
    cooldown = P["cooldown"]

    long_ok, short_ok = S["long_ok"], S["short_ok"]
    vwap, stop_d, atr_x = S["vwap"], S["stop_d"], S["atr_x"]

    cash = INIT
    pos = 0                 # 0 flat, +1 long, -1 short
    qty = 0.0
    ep = sl = tp1 = tp2 = 0.0
    tp1_done = False
    last_entry_bar = -10 ** 9

    # per-cycle bookkeeping
    tr_bar = -1
    tr_qty0 = 0.0
    tr_risk = 0.0
    tr_mult = 0.0
    tr_floor = False
    cyc_entry_fee = 0.0
    cyc_exit_fees = 0.0
    cyc_real = 0.0          # realized net-of-fee from exit fills
    cyc_not_out = 0.0       # sum of exit-fill notionals (fee-identity audit)

    day_start_eq = INIT
    fund_today = 0.0
    daily_halt = False
    killed = False
    cur_day = None

    peak = INIT
    max_dd = 0.0

    fund_paid = 0.0
    fees_total = 0.0
    halt_bars = 0
    n_floor_hits = 0
    max_mult_seen = 0.0
    sum_mult = 0.0
    n_entries = 0

    trades = []
    eq_curve = np.empty(n)
    pos_at_close = np.zeros(n, bool)
    pending = None                 # next_open mode: order submitted at the
                                   # previous close, filling at this bar's open

    def mark(px):
        return cash + (pos * qty * (px - ep) if pos != 0 else 0.0)

    def open_pos(i, side, sig_i, fill_px=None, eqsz_in=None):
        """Open a position. Everything anchor-shaped (stop distance, floor
        test, sizing fraction, TP1's VWAP comparison, bracket levels) reads
        the SIGNAL bar sig_i; the fill price defaults to the signal close
        slipped (close mode) and is explicit in next_open mode."""
        nonlocal cash, pos, qty, ep, sl, tp1, tp2, tp1_done, last_entry_bar
        nonlocal fees_total, tr_qty0, tr_risk, tr_mult, tr_floor, tr_bar
        nonlocal cyc_entry_fee, cyc_exit_fees, cyc_real, cyc_not_out, n_entries
        nonlocal n_floor_hits, max_mult_seen, sum_mult
        ci = float(c[sig_i])
        vw = float(vwap[sig_i])
        sd = float(stop_d[sig_i])
        if not (np.isfinite(sd) and sd > 0):
            return
        floor_val = ci * P["min_stop_pct"] / 100.0
        atr_val = atr_x[sig_i]
        floor_bound = bool(np.isfinite(atr_val) and floor_val > atr_val * P["atr_mult"])
        stop_frac = sd / ci
        m = min(P["risk_pct"] / 100.0 / stop_frac, P["max_lev"])
        eqsz = mark(ci) if eqsz_in is None else eqsz_in
        q = eqsz * m / ci
        if not (q > 0 and np.isfinite(q)):
            return
        if fill_px is None:
            fill_px = ci * (1.0 + slip) if side == 1 else ci * (1.0 - slip)
        px = float(fill_px)
        f = q * px * fee
        cash -= f
        fees_total += f
        pos = side
        qty = q
        ep = px
        sl = ci - sd if side == 1 else ci + sd
        if side == 1:
            tp1 = vw if (np.isfinite(vw) and vw > ci) else ci + sd * P["tp1_r"]
            tp2 = ci + sd * P["tp2_r"]
        else:
            tp1 = vw if (np.isfinite(vw) and vw < ci) else ci - sd * P["tp1_r"]
            tp2 = ci - sd * P["tp2_r"]
        tp1_done = False
        last_entry_bar = i
        tr_bar = i
        tr_qty0 = q
        tr_risk = sd * q
        tr_mult = m
        tr_floor = floor_bound
        cyc_entry_fee = f
        cyc_exit_fees = 0.0
        cyc_real = 0.0
        cyc_not_out = 0.0
        n_entries += 1
        n_floor_hits += 1 if floor_bound else 0
        max_mult_seen = max(max_mult_seen, m)
        sum_mult += m

    n_tp1_partials = 0

    def partial_fill(i, px, frac, reason):
        """Realize `frac` of the current position at px."""
        nonlocal cash, qty, fees_total, cyc_real, cyc_exit_fees
        nonlocal cyc_not_out, n_tp1_partials
        fq = qty * frac
        pnl = (px - ep) * fq if pos == 1 else (ep - px) * fq
        f = fq * px * fee
        cash += pnl - f
        fees_total += f
        cyc_real += pnl - f
        cyc_exit_fees += f
        cyc_not_out += fq * px
        qty -= fq
        n_tp1_partials += 1
        return pnl - f

    def close_fill(i, px, reason):
        """Close the whole remaining position at px; book the cycle."""
        nonlocal cash, qty, pos, fees_total, cyc_real, tp1_done, cyc_exit_fees
        nonlocal cyc_not_out
        pnl = (px - ep) * qty if pos == 1 else (ep - px) * qty
        f = qty * px * fee
        cash += pnl - f
        fees_total += f
        cyc_real += pnl - f
        cyc_exit_fees += f
        cyc_not_out += qty * px
        trades.append(dict(
            side="L" if pos == 1 else "S",
            entry_bar=tr_bar, exit_bar=i, entry_px=ep, exit_px=px,
            qty0=tr_qty0, notional_in=tr_qty0 * ep, notional_out=cyc_not_out,
            pnl=cyc_real - cyc_entry_fee,
            fees=cyc_entry_fee + cyc_exit_fees,
            reason=reason, bars=i - tr_bar, risk=tr_risk, mult=tr_mult,
            floor=tr_floor,
        ))
        pos = 0
        qty = 0.0
        tp1_done = False

    for i in range(n):
        ci, oi, hi_, li_ = c[i], o[i], h[i], l[i]

        # ---- next_open mode: the previous close's order fills at the open --
        # (submitted before this bar; the bracket is live during THIS bar)
        if pending is not None:
            p_side, p_rev, p_eqsz, p_sig = pending
            pending = None
            fpx = oi * (1.0 + slip) if p_side == 1 else oi * (1.0 - slip)
            if p_rev and pos != 0:
                rpx = oi * (1.0 - slip) if pos == 1 else oi * (1.0 + slip)
                close_fill(i, rpx, "flip")
            open_pos(i, p_side, p_sig, fill_px=fpx, eqsz_in=p_eqsz)

        # ---- broker: intra-bar fills on the carried position -------------
        # next_open entries fill at the open, so their bracket already runs
        # on the fill bar (i == last_entry_bar); close-mode entries filled at
        # the close, so theirs starts the next bar.
        if pos != 0 and (i > last_entry_bar
                         or (fill_mode == "next_open" and i == last_entry_bar)):
            if pos == 1:
                if oi <= sl:                       # gap through stop
                    close_fill(i, oi * (1.0 - slip), "stop")
                elif li_ <= sl:                    # SL-first on ties
                    close_fill(i, sl * (1.0 - slip), "stop")
                elif oi >= tp2:                    # gap through TP2
                    close_fill(i, oi * (1.0 - slip), "tp2")
                else:
                    if not tp1_done and hi_ >= tp1:
                        px = oi if oi > tp1 else tp1
                        partial_fill(i, px * (1.0 - slip), 0.5, "tp1")
                        tp1_done = True
                    if pos != 0 and hi_ >= tp2:
                        px = oi if oi > tp2 else tp2
                        close_fill(i, px * (1.0 - slip), "tp2")
            else:
                if oi >= sl:
                    close_fill(i, oi * (1.0 + slip), "stop")
                elif hi_ >= sl:
                    close_fill(i, sl * (1.0 + slip), "stop")
                elif oi <= tp2:
                    close_fill(i, oi * (1.0 + slip), "tp2")
                else:
                    if not tp1_done and li_ <= tp1:
                        px = oi if oi < tp1 else tp1
                        partial_fill(i, px * (1.0 + slip), 0.5, "tp1")
                        tp1_done = True
                    if pos != 0 and li_ <= tp2:
                        px = oi if oi < tp2 else tp2
                        close_fill(i, px * (1.0 + slip), "tp2")

        # ---- script at this bar's close (Pine order) ---------------------
        if pos != 0:
            fpay = (1.0 if pos == 1 else -1.0) * qty * ci * fund_rate * fund_frac
            fund_paid += fpay
            fund_today += fpay
        day = t[i] // 86400000
        if day != cur_day:
            cur_day = day
            day_start_eq = mark(ci)
            fund_today = 0.0
            daily_halt = False
        eq_now = mark(ci)
        if (P["daily_loss_pct"] > 0 and day_start_eq > 0
                and (eq_now - day_start_eq - fund_today)
                / day_start_eq * 100.0 <= -P["daily_loss_pct"]):
            daily_halt = True
        peak = max(peak, eq_now)
        if (P["max_dd_limit"] > 0 and peak > 0
                and (peak - eq_now) / peak * 100.0 >= P["max_dd_limit"]):
            killed = True
        if peak > 0:
            max_dd = max(max_dd, (peak - eq_now) / peak)
        if daily_halt:
            halt_bars += 1

        in_range = ((sim_start_ms is None or t[i] >= sim_start_ms)
                    and (sim_end_ms is None or t[i] <= sim_end_ms))
        gate_ok = in_range and not killed and not daily_halt
        cool_ok = i - last_entry_bar >= cooldown
        sd = stop_d[i]
        stop_ok = bool(np.isfinite(sd) and sd > 0 and i >= warm)

        if fill_mode == "next_open":
            # decide at this close, fill at the NEXT bar's open; sizing equity
            # is the mark at the decision close (pre-flip for reversals)
            if pos == 0:
                if gate_ok and cool_ok and stop_ok:
                    if long_ok[i] and P["allow_long"]:
                        pending = (1, False, mark(ci), i)
                    elif short_ok[i] and P["allow_short"]:
                        pending = (-1, False, mark(ci), i)
            elif (pos == 1 and short_ok[i] and P["allow_short"]
                  and gate_ok and cool_ok and stop_ok):
                pending = (-1, True, mark(ci), i)
            elif (pos == -1 and long_ok[i] and P["allow_long"]
                  and gate_ok and cool_ok and stop_ok):
                pending = (1, True, mark(ci), i)
        elif pos == 0:
            if gate_ok and cool_ok and stop_ok:
                if long_ok[i] and P["allow_long"]:
                    open_pos(i, 1, i)
                elif short_ok[i] and P["allow_short"]:
                    open_pos(i, -1, i)
        elif (pos == 1 and short_ok[i] and P["allow_short"]
              and gate_ok and cool_ok and stop_ok):
            eqsz = mark(ci)                        # strategy.equity pre-flip
            close_fill(i, ci * (1.0 - slip), "flip")
            open_pos(i, -1, i, eqsz_in=eqsz)
        elif (pos == -1 and long_ok[i] and P["allow_long"]
              and gate_ok and cool_ok and stop_ok):
            eqsz = mark(ci)
            close_fill(i, ci * (1.0 + slip), "flip")
            open_pos(i, 1, i, eqsz_in=eqsz)

        eq_curve[i] = mark(ci)
        pos_at_close[i] = pos != 0

    # fix the trade records' fee field (cyc bookkeeping is closed over)
    return dict(eq_curve=eq_curve, trades=trades, fund_paid=fund_paid,
                fees_total=fees_total, max_dd=max_dd, halt_bars=halt_bars,
                killed=killed, n_floor_hits=n_floor_hits,
                n_entries=n_entries, max_mult=max_mult_seen,
                n_tp1_partials=n_tp1_partials,
                pos_at_close=pos_at_close,
                avg_mult=(sum_mult / n_entries) if n_entries else 0.0,
                open_pos=(dict(side=pos, qty=qty, entry_px=ep,
                               entry_bar=tr_bar) if pos != 0 else None),
                n_signals_long=int(long_ok[:].sum()),
                n_signals_short=int(short_ok[:].sum()))


# ------------------------------------------------------------- metrics
def _pf(pnls):
    if not len(pnls):
        return 0.0
    w = sum(p for p in pnls if p > 0)
    ls = sum(p for p in pnls if p <= 0)
    if ls == 0:
        return float("inf") if w > 0 else 0.0
    return w / abs(ls)


def _rd(v, k=4):
    if v is None:
        return None
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return round(float(v), k)


def _year_returns(eq, T):
    y = defaultdict(list)
    for i in range(len(eq)):
        yr = datetime.fromtimestamp(int(T[i]) / 1000, timezone.utc).year
        y[yr].append(eq[i])
    return {k: (v[-1] / v[0] - 1.0) * 100.0 for k, v in sorted(y.items())
            if len(v) >= 2 and v[0] > 0}


def _thirds(eq):
    e = np.asarray(eq, float)
    out = []
    for i in range(3):
        a, b = int(len(e) * i / 3), int(len(e) * (i + 1) / 3)
        out.append(100.0 * (e[b - 1] / e[a] - 1.0) if b > a and e[a] > 0 else 0.0)
    return out


def run_symbol(paths, params):
    """Harness entry: one klines csv -> artifact (three cost views inside)."""
    p = dict(params or {})
    tf = p.pop("tf", None)
    if tf not in TF_MINUTES:
        raise ValueError(f"smqe: unsupported tf {tf!r} (use 1h/15m/5m/1m)")
    cost_mode = str(p.pop("cost_mode", "repo"))
    if cost_mode not in COSTS:
        raise ValueError(f"smqe: unknown cost_mode {cost_mode!r}")
    sim_start = p.pop("sim_start", None)
    sim_end = p.pop("sim_end", None)
    if p:
        raise ValueError(f"unknown smqe params: {sorted(p)}")

    P = dict(PINE)

    t, o, h, l, c, v = [], [], [], [], [], []
    with open(paths[0]) as f:
        f.readline()
        for line in f:
            a = line.split(",")
            if len(a) < 6:
                continue
            try:
                t.append(int(a[0]))
                o.append(float(a[1]))
                h.append(float(a[2]))
                l.append(float(a[3]))
                c.append(float(a[4]))
                v.append(float(a[5]))
            except ValueError:
                continue
    t = np.array(t, np.int64)
    o = np.array(o, float)
    h = np.array(h, float)
    l = np.array(l, float)
    c = np.array(c, float)
    v = np.array(v, float)
    n = len(c)
    if n < 300:
        raise ValueError(f"smqe: only {n} bars in {paths[0]}")

    def _ms(s):
        if s is None:
            return None
        d = datetime.fromisoformat(str(s)).replace(tzinfo=timezone.utc)
        return int(d.timestamp() * 1000)

    ss, se = _ms(sim_start), _ms(sim_end)

    S = signals(t, o, h, l, c, v, P)

    def run_view(fee, slip):
        return execute(t, o, h, l, c, S, P, fee, slip, TF_MINUTES[tf],
                       sim_start_ms=ss, sim_end_ms=se)

    ck = COSTS[cost_mode]
    res = run_view(ck["fee"], ck["slip"])
    res_pine = run_view(COSTS["pine"]["fee"], COSTS["pine"]["slip"])
    res_zero = run_view(0.0, 0.0)
    # METHODOLOGY VIEWS (audit M8/M4): same signals, executable timing; and a
    # time-in-market-matched passive comparator.
    res_no = execute(t, o, h, l, c, S, P, ck["fee"], ck["slip"], TF_MINUTES[tf],
                     sim_start_ms=ss, sim_end_ms=se, fill_mode="next_open")

    # window slice (sim gate): everything before the first in-range bar is
    # flat INIT equity, so performance metrics are computed on the slice
    if ss is not None:
        st = int(np.searchsorted(t, ss, side="left"))
    else:
        st = 0
    if se is not None:
        en = int(np.searchsorted(t, se, side="right")) - 1
    else:
        en = n - 1
    st = max(0, min(st, n - 1))
    en = max(st, min(en, n - 1))
    eq = res["eq_curve"]
    eqw = eq[st:en + 1]

    trs = res["trades"]
    pnls = [tr["pnl"] for tr in trs]
    n_tr = len(pnls)
    pf = _pf(pnls)
    wr = 100.0 * len([1 for x in pnls if x > 0]) / n_tr if n_tr else 0.0

    total = float(sum(pnls))
    srt = sorted(pnls, reverse=True)
    best5 = sum(x for x in srt[:5] if x > 0)
    conc_share = 100.0 * best5 / total if total > 0 else None
    conc_without = 100.0 * (total - best5) / total if total > 0 else None

    gross = sum(x for x in pnls if x > 0)
    fees_total = res["fees_total"]   # every fill's fee, incl. the open entry
    closed_fees = float(sum(tr["fees"] for tr in trs))   # closed cycles only

    # exposure and the in-market passive comparator: the compounded return of
    # holding the asset ONLY over the bars the strategy was in position at
    # the close (methodology audit M4 — the raw B&H gate ignores exposure)
    pmask = res["pos_at_close"]
    exposure_pct = 100.0 * float(pmask[st:en + 1].mean()) if en >= st else 0.0
    held = 1.0
    for i in range(st, en):
        if pmask[i]:
            held *= float(c[i + 1]) / float(c[i])
    bh_inmarket_pct = (held - 1.0) * 100.0

    no_pnls = [x["pnl"] for x in res_no["trades"]]
    ret_no = (res_no["eq_curve"][en] - res_no["fund_paid"] - INIT) / INIT * 100.0

    net_ret = (eq[en] - res["fund_paid"] - INIT) / INIT * 100.0
    broker_ret = (eq[en] / INIT - 1.0) * 100.0
    bh = (c[en] / c[st] - 1.0) * 100.0
    bpk = np.maximum.accumulate(c[st:en + 1])
    bench_dd = float(((c[st:en + 1] / bpk - 1.0).min()) * 100.0)

    rets = np.diff(eqw) / eqw[:-1]
    rets = rets[np.isfinite(rets)]
    sp = float(np.median(np.diff(t[st:en + 1]))) if en - st > 2 else 3600000.0
    bpy = 365.25 * 86400000.0 / sp
    sharpe = (float(np.mean(rets) / np.std(rets)) * np.sqrt(bpy)
              if len(rets) > 2 and np.std(rets) > 0 else 0.0)

    thirds = _thirds(eqw)

    # frozen split at 2023-01-01 (full-history runs only)
    split_ms = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    tr_exit_t = np.array([t[tr["exit_bar"]] for tr in trs], np.int64) \
        if trs else np.zeros(0, np.int64)
    if st == 0 and en == n - 1 and np.any(t >= split_ms):
        idx = int(np.searchsorted(t, split_ms, side="left"))
        train_ret = 100.0 * (eq[idx - 1] / eq[0] - 1.0) if idx > 0 else 0.0
        test_ret = 100.0 * (eq[en] / eq[idx - 1] - 1.0) if idx > 0 else 0.0
        tmask = tr_exit_t >= split_ms
        tpnls = [pnls[k] for k in range(n_tr) if tmask[k]]
        seg = eq[idx:en + 1]
        if len(seg) > 1:
            pk = np.maximum.accumulate(seg)
            seg_mdd = float(np.max((pk - seg) / np.maximum(pk, 1e-9)) * 100.0)
        else:
            seg_mdd = 0.0
        split = dict(split_date="2023-01-01",
                     train_return_pct=_rd(train_ret),
                     test_return_pct=_rd(test_ret),
                     test_n_trades=len(tpnls),
                     test_profit_factor=_rd(_pf(tpnls)),
                     test_max_dd_pct=_rd(seg_mdd))
    else:
        split = dict(split_date=None, train_return_pct=None,
                     test_return_pct=None, test_n_trades=0,
                     test_profit_factor=None, test_max_dd_pct=None)

    by_side, by_why = {}, {}
    for tr in trs:
        s = by_side.setdefault(tr["side"], dict(n=0, pnl=0.0, w=0.0, ls=0.0, nw=0))
        s["n"] += 1
        s["pnl"] += tr["pnl"]
        if tr["pnl"] > 0:
            s["w"] += tr["pnl"]
            s["nw"] += 1
        else:
            s["ls"] += -tr["pnl"]
        w_ = by_why.setdefault(tr["reason"], dict(n=0, pnl=0.0, nw=0))
        w_["n"] += 1
        w_["pnl"] += tr["pnl"]
        w_["nw"] += 1 if tr["pnl"] > 0 else 0

    # compact views for the pine-cost and zero-cost controls
    def view(r):
        p_ = [x["pnl"] for x in r["trades"]]
        e_ = r["eq_curve"]
        return dict(
            n_trades=len(p_), profit_factor=_rd(_pf(p_)),
            win_rate=_rd(100.0 * len([1 for x in p_ if x > 0]) / len(p_)) if p_ else 0.0,
            net_return_pct=_rd((e_[en] - r["fund_paid"] - INIT) / INIT * 100.0),
            max_dd_pct=_rd(r["max_dd"] * 100.0),
            fees=_rd(r["fees_total"], 2), funding_paid=_rd(r["fund_paid"], 2))

    tables = []
    for side in ("L", "S"):
        s = by_side.get(side)
        if not s:
            continue
        tables.append(dict(kind="side", side=side, trades=s["n"],
                           pnl=_rd(s["pnl"], 2),
                           win_rate_pct=_rd(100.0 * s["nw"] / s["n"], 2),
                           PF=_rd(s["w"] / s["ls"]) if s["ls"] > 0 else None))
    for why in sorted(by_why):
        w_ = by_why[why]
        tables.append(dict(kind="exit", reason=why, count=w_["n"],
                           closed_pnl=_rd(w_["pnl"], 2),
                           win_rate_pct=_rd(100.0 * w_["nw"] / w_["n"], 2)))
    for k_, v_ in _year_returns(eqw, t[st:en + 1]).items():
        ytr = [pnls[k2] for k2 in range(n_tr)
               if k2 < len(tr_exit_t)
               and datetime.fromtimestamp(int(tr_exit_t[k2]) / 1000,
                                          timezone.utc).year == k_]
        tables.append(dict(kind="year", year=int(k_), ret_pct=_rd(v_),
                           n_trades=len(ytr), PF=_rd(_pf(ytr))))
    tables += [dict(kind="trade", **{k_: (_rd(v_, 8) if isinstance(v_, float) else v_)
                                     for k_, v_ in tr.items()})
               for tr in trs[:4000]]

    m = dict(
        cost_mode=cost_mode,
        bars=int(n), tf_minutes=TF_MINUTES[tf],
        window_start_utc=str(sim_start) if sim_start else None,
        window_end_utc=str(sim_end) if sim_end else None,
        years=_rd((t[en] - t[st]) / (365.25 * 86400000.0), 2),
        n_trades=n_tr, n_open=1 if res["open_pos"] is not None else 0,
        return_pct=_rd(net_ret), broker_return_pct=_rd(broker_ret),
        funding_paid_usd=_rd(res["fund_paid"], 2),
        max_dd_pct=_rd(res["max_dd"] * 100.0),
        final_equity=_rd(eq[en], 2),
        profit_factor=_rd(pf), win_rate=_rd(wr),
        expectancy=_rd(float(np.mean(pnls)) if pnls else 0.0, 6),
        expectancy_R=_rd(float(np.mean([tr["pnl"] / tr["risk"] for tr in trs
                                        if tr["risk"] > 0])) if trs else 0.0, 4),
        avg_bars_held=_rd(float(np.mean([tr["bars"] for tr in trs])) if trs else 0.0, 2),
        sharpe=_rd(sharpe),
        bh_return_pct=_rd(bh), bench_dd_pct=_rd(bench_dd),
        beats_bh=bool(net_ret > bh),
        exposure_pct=_rd(exposure_pct),
        bh_inmarket_pct=_rd(bh_inmarket_pct),
        excess_vs_inmarket_pp=_rd(net_ret - bh_inmarket_pct),
        ret_nextopen_pct=_rd(ret_no),
        pf_nextopen=_rd(_pf(no_pnls)),
        n_trades_nextopen=len(no_pnls),
        timing_drag_pp=_rd(net_ret - ret_no),
        fees=_rd(fees_total, 2),
        fee_over_gross_pct=_rd(100.0 * closed_fees / gross) if gross > 0 else None,
        cost_bp_roundtrip=_rd(2.0 * (ck["fee"] + ck["slip"]) * 1e4, 2),
        fee_bps_per_side=_rd(ck["fee"] * 1e4, 2),
        slip_bps_per_side=_rd(ck["slip"] * 1e4, 2),
        best5_share_pct=_rd(conc_share),
        net_without_best5_pct=_rd(conc_without),
        ret_zero_pct=view(res_zero)["net_return_pct"],
        pf_zero=view(res_zero)["profit_factor"],
        drag_pp=_rd(view(res_zero)["net_return_pct"] - net_ret),
        ret_pine_pct=view(res_pine)["net_return_pct"],
        pf_pine=view(res_pine)["profit_factor"],
        period1_pct=_rd(thirds[0]), period2_pct=_rd(thirds[1]),
        period3_pct=_rd(thirds[2]),
        n_periods_green=int(sum(1 for x in thirds if x > 0)),
        year_returns={str(k_): _rd(v_) for k_, v_ in
                      _year_returns(eqw, t[st:en + 1]).items()},
        **split,
        n_signals_long=int(S["long_ok"].sum()),
        n_signals_short=int(S["short_ok"].sum()),
        n_entries=res["n_entries"],
        n_stop_exits=int(sum(1 for x in trs if x["reason"] == "stop")),
        n_tp2_exits=int(sum(1 for x in trs if x["reason"] == "tp2")),
        n_flip_exits=int(sum(1 for x in trs if x["reason"] == "flip")),
        n_tp1_partials=res["n_tp1_partials"],
        avg_entry_mult=_rd(res["avg_mult"], 4),
        max_entry_mult=_rd(res["max_mult"], 4),
        min_stop_floor_hits=res["n_floor_hits"],
        halt_bars=res["halt_bars"],
        killed=bool(res["killed"]),
        open_pnl_usd=_rd(
            ((1 if res["open_pos"]["side"] == 1 else -1)
             * res["open_pos"]["qty"] * (c[en] - res["open_pos"]["entry_px"]))
            if res["open_pos"] else None, 2) if res["open_pos"] else None,
        flag="OK" if n_tr >= 30 else "INSUFFICIENT_SAMPLE",
    )
    return {"metrics": m, "tables": tables}


if __name__ == "__main__":
    print(__doc__)
