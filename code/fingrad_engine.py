#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fingrad_engine.py — port of code/fingrad_hma_ao_adx_strategy.pine:
"Fingrad HMA · AO · ADX Strategy" (Pine v6, attachment copied byte-identical
from Downloads/fingrad_hma_ao_adx_strategy.pine, sha256 d3aabd19a1795f30...).

THE PINE, READ END TO END
    strategy(...) initial_capital=1000, commission 0.05%/side, slippage=2 ticks,
    pyramiding=0, margin 5% (20x), calc_on_every_tick=false,
    process_orders_on_close=FALSE -> signals evaluate on the confirmed bar,
    orders fill at the NEXT bar's open. Same convention as adxhma_strategy.py.

    Two systems over one HMA(21):
      A  LONG  close > HMA and AO > 0 and AO rising
         SHORT close < HMA and AO < 0 and AO falling
      B  LONG  close > HMA and (ADX crossed ABOVE 25 within 3 bars, ADX > 25,
                               +DI > -DI)     <- "Cross (mirrored, fixed)" default
         SHORT close < HMA and (ADX crossed ABOVE 25 within 3 bars, ADX > 25,
                               -DI > +DI)     <- mirrored: BOTH sides use the
                               cross-ABOVE event, direction comes from DI
      Modes: "A + B confluence" (both) | "A only" | "B only" | "A or B".
    EXIT (Auto): "HMA close only" in B mode, else "HMA or AO flip"
      long exits on close < HMA or AO red&below-zero; short mirrored.
      A fresh opposite entry reverses instead (the signal exit is suppressed
      that bar and strategy.entry does the reversal on one fill).
    Triggers are EDGE-triggered on the WHOLE state:
      stL = modeL and htfOkL and costOk and allowLong; entryL = stL and !stL[1].
      A flip of ANY component (HTF filter, cost gate) re-arms the trigger.
    Filters: HTF HMA direction (last CLOSED HTF bar, non-repainting idiom),
      cost gate ATR% >= 1.5 * 2*(0.05% fee + 0.01% slip) = 0.18%,
      daily-loss breaker 3% of day-start equity (closes everything, blocks
      entries for the rest of the UTC day).
    Risk: ATR hard stop 2.0 x ATR(14) of the SIGNAL bar (distance frozen at the
      signal, level re-anchored to the real fill by the every-bar management
      block); TP off by default (tp_r=0); sizing risk-based 1% of equity per
      stop distance, capped at 10x notional/equity; fixed 100% notional when
      the stop is off.

PINE SEMANTICS THAT NEED CARE (each pinned by a known-answer test)
    - Fill at next open; the bracket submitted on the signal bar is live during
      the fill bar anchored at the SIGNAL close; from the next close the
      management block re-anchors stop/TP to position_avg_price every bar with
      the SAME frozen distance. So bar 1 of a trade uses close_sig -/+ dist,
      bars 2+ use fill -/+ dist. (K3a/K3b.)
    - Gap-through: TV turns a stop into a market order at the open, so an open
      beyond the stop fills AT THE OPEN, not at the stop. A limit gapped
      through fills at the open too (better price for the holder). The port
      models both; the adxhma port did not (it always filled at the level).
    - okL = flat or (closeOpp and inShort): a fresh same-direction signal while
      positioned is a NO-OP (pyramiding=0 would reject it and okL already
      blocks the order) — no bracket re-arm happens, unlike emaadx's Pine.
    - takeS = ... and not takeL: on a tie the LONG wins.
    - not na is TRUE and na comparisons are FALSY: warmup states are false.
      aoGreen needs ao AND ao[1]; on ao's first valid bar aoGreen is false, so
      aoDnOK = ao<0 can be true there (not-false = true) while aoUpOK cannot.
    - ta.barssince: 0 on the bar the event fires; na before the first event.
      recUp = not na(sinceUp) and sinceUp <= 3 and adx > thr.
    - HTF filter: request.security(..., [hma[1], hma[2]], lookahead_on) is the
      standard non-repainting idiom: for every chart bar inside HTF bar k it
      returns the HMA of HTF bars k-1 and k-2 — the last two CLOSED HTF bars.
      K11 pins the mapping; K12 proves future HTF bars cannot move it.
    - timeframe.change("D") is true on the first bar; day-start equity is the
      marked equity at that bar's close. The breaker compares the CLOSE equity
      (calc_on_every_tick=false) and close_all fills at the next open.
    - f_qty: strategy.equity at the signal close (including unrealized when
      reversing), q = min(risk_eq/dist, eq*maxLev/close), floored at 0; a
      q of 0 means no order at all (no bracket, no pendStop update).

COSTS
    author : the Pine header, 0.05% commission/side. Slippage = 2 TICKS, which
             on these series is ~1e-5 bps — declared zero (adxhma/emaadx
             precedent: judge nothing on the flattering version alone).
    repo6x5: 6 bps fee + 5 bps slippage per side (repo standard).
    zero   : control pass inside every artifact; drag_pp = ret_zero - ret_cost.
    Funding is NOT charged by the Pine (TradingView strategies have no funding
    model). The adapter can charge it (params funding=true, needs the symbol's
    binance_funding json) for the perp reading; default off mirrors the Pine.

PRIMITIVES
    wma/hma/rma/atr/dmi are the adxhma_strategy.py implementations whose
    self-test validated them (SMA-seeded rma skipping leading na — the
    all-NaN-ADX bug — and floored hma inner lengths). They are re-asserted by
    code/_fingrad_audit.py before any real-data run.

AUDIT (code/_fingrad_audit.py, results/fingrad_audit_known_answers.txt)
    primitives vs naive references; hand-computed execution known answers
    (next-open fills, edge trigger, first-bar vs fill-anchored brackets,
    stop-first ties, gap-through, reversal economics, risk sizing, leverage
    cap, daily breaker); cash identity; no-lookahead truncation on real data;
    determinism; a vectorized-vs-loop DUAL of the whole signal layer across
    every sig_mode x adx_mode on BTC 1h.
"""

import json
import os
import sys
from collections import defaultdict
import datetime as dt

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INIT = 1000.0                      # the Pine's initial_capital

TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}

# The Pine's shipped presets (tooltip: Scalp HMA 21 / HTF 60m; Day HMA 34 /
# HTF 240m; Custom = the inputs' 21 / "60").
PRESETS = {
    "custom": dict(hma_len=21, htf_minutes=60),
    "scalp":  dict(hma_len=21, htf_minutes=60),
    "day":    dict(hma_len=34, htf_minutes=240),
}

# Everything else is the Pine's shipped defaults; the port does not expose the
# geometry as knobs (emaadx precedent: the audited strategy is fixed).
PINE = dict(
    ao_fast=5, ao_slow=34,
    di_len=14, adx_smooth=14, adx_thr=25.0, adx_win=3, req_di=True,
    use_htf=True, use_cost=True, atr_len=14, cost_mult=1.5,
    fee_pct=0.05, slip_pct=0.01,          # the strategy's own cost-gate inputs
    atr_stop_mult=2.0, tp_r=0.0, risk_pct=1.0, fixed_notional=100.0,
    max_lev=10.0, close_opp=True, daily_loss=3.0,
    allow_long=True, allow_short=True,
)

COSTS = {
    "author":  dict(fee=0.0005, slip=0.0),
    "repo6x5": dict(fee=0.0006, slip=0.0005),
    "zero":    dict(fee=0.0, slip=0.0),
}


# ------------------------------------------------------------- indicators
def sma(x, n):
    """Pine ta.sma: na until n valid values."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    valid = ~np.isnan(x)
    xf = np.where(valid, x, 0.0)
    s = np.convolve(xf, np.ones(n), "valid")
    cnt = np.convolve(valid.astype(float), np.ones(n), "valid")
    out[n - 1:] = np.where(cnt == n, s / n, np.nan)
    return out


def wma(x, n):
    """Weighted MA, newest bar weighted n. Pine ta.wma."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    valid = ~np.isnan(x)
    xf = np.where(valid, x, 0.0)
    num = np.convolve(xf, np.arange(n, 0, -1, dtype=float), "valid")
    cnt = np.convolve(valid.astype(float), np.ones(n), "valid")
    with np.errstate(invalid="ignore"):
        res = np.where(cnt == n, num / (n * (n + 1) / 2.0), np.nan)
    out[n - 1:] = res
    return out


def wma_naive(x, n):
    """Obviously-correct reference used to assert `wma`."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    den = n * (n + 1) / 2.0
    for i in range(n - 1, len(x)):
        win = x[i - n + 1:i + 1]
        if np.isnan(win).any():
            continue
        out[i] = float((win * np.arange(1, n + 1)).sum() / den)
    return out


def hma(x, n):
    """Pine ta.hma: floor(len/2) and floor(sqrt(len)) are FLOORED."""
    n2 = int(np.floor(n / 2.0))
    ns = int(np.floor(np.sqrt(n)))
    inner = 2.0 * wma(x, n2) - wma(x, n)
    return wma(inner, ns)


def rma(x, n):
    """Wilder smoothing, SMA-seeded like Pine's ta.rma; leading na skipped."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    buf = []
    prev = np.nan
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
    """Pine ta.crossover: a>b now and a[1]<=b[1], na-falsy on both bars."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if a.ndim == 0:
        a = np.full(len(b), float(a))
    if b.ndim == 0:
        b = np.full(len(a), float(b))
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


def barssince(x):
    """Pine ta.barssince: bars since x was last true, 0 on the event bar,
    na before the first event."""
    x = np.asarray(x, bool)
    n = len(x)
    out = np.full(n, np.nan)
    idx = np.flatnonzero(x)
    if len(idx) == 0:
        return out
    pos = np.searchsorted(idx, np.arange(n), side="right") - 1
    valid = pos >= 0
    out[valid] = np.arange(n)[valid] - idx[pos[valid]]
    return out


# ------------------------------------------------------------- HTF filter
def htf_hma_pairs(T, c, hma_len, htf_minutes):
    """The security(...) idiom: for every chart bar inside HTF bar k return
    (hh[k-1], hh[k-2]) where hh is the HMA of the HTF closes. na until the
    HTF series has hma_len bars AND the chart bar sits in group k >= 2."""
    period = htf_minutes * 60 * 1000
    g = T // period
    last_of_group = np.flatnonzero(np.r_[g[1:] != g[:-1], True])
    htf_close = c[last_of_group]
    htf_g = g[last_of_group]
    hh = hma(htf_close, hma_len)
    k = np.searchsorted(htf_g, g, side="left")     # group index of each bar
    h1i = np.clip(k - 1, 0, None)
    h2i = np.clip(k - 2, 0, None)
    hH1 = np.where(k >= 1, hh[h1i], np.nan)
    hH2 = np.where(k >= 2, hh[h2i], np.nan)
    return hH1, hH2


# ------------------------------------------------------------- signal layer
def _exit_arrays(hmaS, hmaL, aoDnOK, aoUpOK, exit_eff):
    if exit_eff == "hma":
        exitL, exitS = hmaS, hmaL
    elif exit_eff == "ao":
        exitL, exitS = aoDnOK, aoUpOK
    elif exit_eff == "hma_and_ao":
        exitL, exitS = hmaS & aoDnOK, hmaL & aoUpOK
    else:                                        # "hma_or_ao"
        exitL, exitS = hmaS | aoDnOK, hmaL | aoUpOK
    with np.errstate(invalid="ignore"):
        rl = np.where(hmaS & aoDnOK, "hma+ao",
                      np.where(hmaS, "hma", np.where(aoDnOK, "ao", "")))
        rs = np.where(hmaL & aoUpOK, "hma+ao",
                      np.where(hmaL, "hma", np.where(aoUpOK, "ao", "")))
    return exitL, exitS, rl, rs


def signals(d, P, sig_mode="confluence", adx_mode="cross", exit_rule="auto"):
    """Vectorized signal layer -> the executor's input contract.

    sig_mode : confluence | a | b | either   (the Pine's four signal modes)
    adx_mode : cross | level | literal       ("Cross (mirrored, fixed)" default)
    exit_rule: auto | hma | ao | hma_or_ao | hma_and_ao
               auto resolves to "hma" for B-only mode, else "hma_or_ao".
    """
    o, h, l, c, T = d["o"], d["h"], d["l"], d["c"], d["t"]
    n = len(c)
    hma_len = P["hma_len"]
    H = hma(c, hma_len)
    hl2 = (h + l) / 2.0
    ao = sma(hl2, P["ao_fast"]) - sma(hl2, P["ao_slow"])
    diP, diM, adx = dmi_pine(h, l, c, P["di_len"], P["adx_smooth"])
    A = atr_pine(h, l, c, P["atr_len"])

    with np.errstate(invalid="ignore"):
        hmaL = (~np.isnan(H)) & (c > H)
        hmaS = (~np.isnan(H)) & (c < H)
        ao_prev = np.full(n, np.nan)
        ao_prev[1:] = ao[:-1]
        aoGreen = (~np.isnan(ao)) & (~np.isnan(ao_prev)) & (ao > ao_prev)
        aoUpOK = (~np.isnan(ao)) & (ao > 0) & aoGreen
        aoDnOK = (~np.isnan(ao)) & (ao < 0) & (~aoGreen)
        diBull = (~np.isnan(diP)) & (~np.isnan(diM)) & (diP > diM)
        diBear = (~np.isnan(diP)) & (~np.isnan(diM)) & (diM > diP)

    thr = P["adx_thr"]
    crossUp = cross_over(adx, thr)
    crossDn = cross_under(adx, thr)
    sinceUp = barssince(crossUp)
    sinceDn = barssince(crossDn)
    with np.errstate(invalid="ignore"):
        recUp = (~np.isnan(sinceUp)) & (sinceUp <= P["adx_win"]) \
            & (~np.isnan(adx)) & (adx > thr)
        recDn = (~np.isnan(sinceDn)) & (sinceDn <= P["adx_win"]) \
            & (~np.isnan(adx)) & (adx < thr)

    if adx_mode == "level":
        adxOkL = (~np.isnan(adx)) & (adx > thr) & (diBull if P["req_di"] else True)
        adxOkS = (~np.isnan(adx)) & (adx > thr) & (diBear if P["req_di"] else True)
    elif adx_mode == "literal":
        adxOkL, adxOkS = recUp, recDn
    else:                                        # cross (mirrored, fixed)
        adxOkL = recUp & (diBull if P["req_di"] else True)
        adxOkS = recUp & (diBear if P["req_di"] else True)

    if P["use_htf"]:
        hH1, hH2 = htf_hma_pairs(T, c, hma_len, P["htf_minutes"])
        htfOkL = (~np.isnan(hH1)) & (~np.isnan(hH2)) & (hH1 > hH2)
        htfOkS = (~np.isnan(hH1)) & (~np.isnan(hH2)) & (hH1 < hH2)
    else:
        hH1 = hH2 = None
        htfOkL = htfOkS = np.ones(n, bool)

    if P["use_cost"]:
        with np.errstate(invalid="ignore", divide="ignore"):
            atr_pct = A / c * 100.0
        min_atr = P["cost_mult"] * 2.0 * (P["fee_pct"] + P["slip_pct"])
        costOk = (~np.isnan(atr_pct)) & (atr_pct >= min_atr)
    else:
        costOk = np.ones(n, bool)

    aL = hmaL & aoUpOK
    aS = hmaS & aoDnOK
    bL = hmaL & adxOkL
    bS = hmaS & adxOkS
    if sig_mode == "a":
        modeL, modeS = aL, aS
    elif sig_mode == "b":
        modeL, modeS = bL, bS
    elif sig_mode == "either":
        modeL, modeS = aL | bL, aS | bS
    else:                                        # confluence
        modeL, modeS = aL & bL, aS & bS

    stL = modeL & htfOkL & costOk & P["allow_long"]
    stS = modeS & htfOkS & costOk & P["allow_short"]
    entryL = np.zeros(n, bool)
    entryS = np.zeros(n, bool)
    entryL[0] = bool(stL[0])                     # stL[-1] is na -> falsy
    entryS[0] = bool(stS[0])
    entryL[1:] = stL[1:] & ~stL[:-1]
    entryS[1:] = stS[1:] & ~stS[:-1]

    exit_eff = exit_rule
    if exit_eff == "auto":
        exit_eff = "hma" if sig_mode == "b" else "hma_or_ao"
    exitL, exitS, rL, rS = _exit_arrays(hmaS, hmaL, aoDnOK, aoUpOK, exit_eff)

    dist = np.where(np.isnan(A), 0.0, P["atr_stop_mult"] * A)

    return dict(H=H, ao=ao, adx=adx, atr=A, stL=stL, stS=stS,
                entryL=entryL, entryS=entryS, exitL=exitL, exitS=exitS,
                exit_reason_L=rL, exit_reason_S=rS, dist=dist,
                exit_eff=exit_eff, hH1=hH1, hH2=hH2)


def signals_loop(d, P, sig_mode="confluence", adx_mode="cross", exit_rule="auto"):
    """Independent per-bar reimplementation of the STATE/EDGE/EXIT logic (the
    dual engine). Indicators come from the same validated primitives; every
    comparison, [1] reference, cross bookkeeping and HTF pair is recomputed
    with scalar ops and running variables — catches shift/alignment bugs."""
    h, l, c, T = d["h"], d["l"], d["c"], d["t"]
    n = len(c)
    H = hma(c, P["hma_len"])
    ao = sma((h + l) / 2.0, P["ao_fast"]) - sma((h + l) / 2.0, P["ao_slow"])
    diP, diM, adx = dmi_pine(h, l, c, P["di_len"], P["adx_smooth"])
    A = atr_pine(h, l, c, P["atr_len"])

    # HTF closes walked scalarly: a group's close is recorded when the NEXT
    # group starts; the last group's close is appended but never read (the
    # forming HTF bar is excluded by the [1]/[2] idiom, both here and in
    # htf_hma_pairs).
    period = P["htf_minutes"] * 60 * 1000
    g = T // period
    grp_closes = []
    k_of_bar = np.empty(n, np.int64)
    for i in range(n):
        if i > 0 and g[i] != g[i - 1]:
            grp_closes.append(c[i - 1])
        k_of_bar[i] = len(grp_closes)
    grp_closes.append(c[n - 1])
    hh = hma(np.array(grp_closes, float), P["hma_len"])

    stL = np.zeros(n, bool); stS = np.zeros(n, bool)
    exitL = np.zeros(n, bool); exitS = np.zeros(n, bool)
    rL = [""] * n; rS = [""] * n
    thr = P["adx_thr"]
    last_up = last_dn = -1                       # -1 = never crossed yet
    exit_eff = exit_rule
    if exit_eff == "auto":
        exit_eff = "hma" if sig_mode == "b" else "hma_or_ao"

    prev_adx = np.nan
    entryL = np.zeros(n, bool)
    entryS = np.zeros(n, bool)
    for i in range(n):
        hma_ = H[i]
        hmaL = (not np.isnan(hma_)) and c[i] > hma_
        hmaS = (not np.isnan(hma_)) and c[i] < hma_
        ao_ = ao[i]
        ao_p = ao[i - 1] if i > 0 else np.nan
        if np.isnan(ao_):
            aoUpOK = aoDnOK = False
        else:
            aoGreen = (not np.isnan(ao_p)) and ao_ > ao_p
            aoUpOK = ao_ > 0 and aoGreen
            aoDnOK = ao_ < 0 and not aoGreen

        # ADX cross bookkeeping (prev <= thr < cur, na-falsy both sides)
        adx_ = adx[i]
        if (not np.isnan(prev_adx)) and (not np.isnan(adx_)):
            if prev_adx <= thr < adx_:
                last_up = i
            if prev_adx >= thr > adx_:
                last_dn = i
        prev_adx = adx_
        recUp = last_up >= 0 and (i - last_up) <= P["adx_win"] \
            and (not np.isnan(adx_)) and adx_ > thr
        recDn = last_dn >= 0 and (i - last_dn) <= P["adx_win"] \
            and (not np.isnan(adx_)) and adx_ < thr

        diBull = (not np.isnan(diP[i])) and (not np.isnan(diM[i])) and diP[i] > diM[i]
        diBear = (not np.isnan(diP[i])) and (not np.isnan(diM[i])) and diM[i] > diP[i]
        if adx_mode == "level":
            adxOkL = (not np.isnan(adx_)) and adx_ > thr and (diBull if P["req_di"] else True)
            adxOkS = (not np.isnan(adx_)) and adx_ > thr and (diBear if P["req_di"] else True)
        elif adx_mode == "literal":
            adxOkL, adxOkS = recUp, recDn
        else:
            adxOkL = recUp and (diBull if P["req_di"] else True)
            adxOkS = recUp and (diBear if P["req_di"] else True)

        if P["use_htf"]:
            k = int(k_of_bar[i])
            h1 = hh[k - 1] if k >= 1 else np.nan
            h2 = hh[k - 2] if k >= 2 else np.nan
            htfOkL = (not np.isnan(h1)) and (not np.isnan(h2)) and h1 > h2
            htfOkS = (not np.isnan(h1)) and (not np.isnan(h2)) and h1 < h2
        else:
            htfOkL = htfOkS = True

        if P["use_cost"]:
            a_ = A[i]
            costOk = (not np.isnan(a_)) and (a_ / c[i] * 100.0 >=
                                             P["cost_mult"] * 2.0 *
                                             (P["fee_pct"] + P["slip_pct"]))
        else:
            costOk = True

        aL = hmaL and aoUpOK
        aS = hmaS and aoDnOK
        bL = hmaL and adxOkL
        bS = hmaS and adxOkS
        if sig_mode == "a":
            modeL, modeS = aL, aS
        elif sig_mode == "b":
            modeL, modeS = bL, bS
        elif sig_mode == "either":
            modeL, modeS = (aL or bL), (aS or bS)
        else:
            modeL, modeS = (aL and bL), (aS and bS)

        prev_l = bool(stL[i - 1]) if i > 0 else False
        prev_s = bool(stS[i - 1]) if i > 0 else False
        stL[i] = modeL and htfOkL and costOk and P["allow_long"]
        stS[i] = modeS and htfOkS and costOk and P["allow_short"]
        entryL[i] = bool(stL[i]) and not prev_l
        entryS[i] = bool(stS[i]) and not prev_s

        if exit_eff == "hma":
            exitL[i], exitS[i] = hmaS, hmaL
        elif exit_eff == "ao":
            exitL[i], exitS[i] = aoDnOK, aoUpOK
        elif exit_eff == "hma_and_ao":
            exitL[i], exitS[i] = (hmaS and aoDnOK), (hmaL and aoUpOK)
        else:
            exitL[i], exitS[i] = (hmaS or aoDnOK), (hmaL or aoUpOK)
        rL[i] = ("hma+ao" if (hmaS and aoDnOK) else
                 "hma" if hmaS else "ao" if aoDnOK else "")
        rS[i] = ("hma+ao" if (hmaL and aoUpOK) else
                 "hma" if hmaL else "ao" if aoUpOK else "")

    dist = np.where(np.isnan(A), 0.0, P["atr_stop_mult"] * A)
    return dict(H=H, ao=ao, adx=adx, atr=A, stL=stL, stS=stS,
                entryL=entryL, entryS=entryS, exitL=exitL, exitS=exitS,
                exit_reason_L=np.array(rL), exit_reason_S=np.array(rS),
                dist=dist, exit_eff=exit_eff)


# ------------------------------------------------------------- executor
def f_qty(eq, px, dist, P):
    """Pine f_qty: risk-based with the stop, fixed notional without; capped at
    max_lev notional/equity; floored at 0 (a q of 0 means no order)."""
    eq = max(eq, 0.0)
    q_cap = eq * P["max_lev"] / px if px > 0 else 0.0
    if dist > 0:
        q_raw = (eq * P["risk_pct"] / 100.0) / dist
    else:
        q_raw = eq * P["fixed_notional"] / 100.0 / px if px > 0 else 0.0
    return max(min(q_raw, q_cap), 0.0)


def execute(d, S, P, fee, slip, fund_rate=None, fund_ev=None):
    """Bar-by-bar port, process_orders_on_close=false:

    per bar i:
      a) fill the order scheduled at the previous close, at THIS open
         (market fills carry adverse slip; a reversal is one fill that
         closes the old leg and opens the new at the same price)
      b) intrabar bracket on the position (STOP checked BEFORE TP; an open
         gapped through the level fills AT THE OPEN, TV's stop->market rule;
         limit fills carry no slip)
      c) funding on held notional at settlement bars (optional)
      d) decisions at THIS close -> schedule the fill for the next open
    """
    o, h, l, c, T = d["o"], d["h"], d["l"], d["c"], d["t"]
    n = len(c)
    tp_r = P["tp_r"]
    cash = INIT
    inv = 0.0
    entry_px = 0.0
    entry_bar = -1
    entry_fee = 0.0
    trade_stop = 0.0
    sl_base = None
    tp_base = None
    day_start_eq = INIT
    trades = []
    eq = np.zeros(n)
    pending = None
    n_halts = 0
    halt_bars = 0
    fund_paid = 0.0
    n_fund_events = 0

    def close_trade(i, fill, why):
        nonlocal cash, inv, entry_fee, sl_base, tp_base, trade_stop
        exit_fee = abs(inv) * fill * fee
        pnl = inv * (fill - entry_px) - entry_fee - exit_fee
        cash += inv * fill - exit_fee
        trades.append(dict(side="L" if inv > 0 else "S",
                           entry_bar=entry_bar, exit_bar=i,
                           entry=entry_px, exit=fill, pnl=pnl,
                           qty=abs(inv), why=why,
                           entry_fee=entry_fee, exit_fee=exit_fee,
                           fees=entry_fee + exit_fee, bars=i - entry_bar))
        inv = 0.0
        entry_fee = 0.0
        sl_base = tp_base = None
        trade_stop = 0.0

    for i in range(n):
        oi, hi, li, ci = o[i], h[i], l[i], c[i]

        # (a) fill the pending order at this open
        if pending is not None:
            kind = pending["kind"]
            if kind == "close":
                if inv != 0:
                    fill = oi * (1 - slip) if inv > 0 else oi * (1 + slip)
                    close_trade(i, fill, pending["why"])
            elif kind == "close_all":
                if inv != 0:
                    fill = oi * (1 - slip) if inv > 0 else oi * (1 + slip)
                    close_trade(i, fill, "daily halt")
            else:
                side = 1 if kind == "enterL" else -1
                fill = oi * (1 + slip * side)
                if (side > 0 and inv < 0) or (side < 0 and inv > 0):
                    close_trade(i, fill, "reverse")
                q = pending["q"]
                if q > 0:
                    dist = pending["dist"]
                    if side > 0:
                        cash -= q * fill
                        entry_fee = q * fill * fee
                        cash -= entry_fee
                        inv = q
                    else:
                        cash += q * fill
                        entry_fee = q * fill * fee
                        cash -= entry_fee
                        inv = -q
                    entry_px = fill
                    entry_bar = i
                    trade_stop = dist
                    # bracket live DURING this bar: the signal bar's close
                    # anchor (submitted at the signal close, active on fill)
                    cs = pending["close_sig"]
                    if dist > 0:
                        sl_base = cs - dist if side > 0 else cs + dist
                        if tp_r > 0:
                            tp_base = cs + dist * tp_r if side > 0 else cs - dist * tp_r
                        else:
                            tp_base = None
                    else:
                        sl_base = tp_base = None
            pending = None

        # (b) intrabar bracket (stop BEFORE target; gap-through fills at open)
        if inv > 0:
            if sl_base is not None and li <= sl_base:
                px = oi if oi <= sl_base else sl_base
                close_trade(i, px * (1 - slip), "SL")
            elif tp_base is not None and hi >= tp_base:
                px = oi if oi >= tp_base else tp_base
                close_trade(i, px, "TP")
        elif inv < 0:
            if sl_base is not None and hi >= sl_base:
                px = oi if oi >= sl_base else sl_base
                close_trade(i, px * (1 + slip), "SL")
            elif tp_base is not None and li <= tp_base:
                px = oi if oi <= tp_base else tp_base
                close_trade(i, px, "TP")

        # (c) funding on held notional at settlement bars
        if inv != 0 and fund_ev is not None and fund_ev[i]:
            cash -= inv * ci * fund_rate[i]
            fund_paid += inv * ci * fund_rate[i]
            n_fund_events += 1

        eqi = cash + inv * ci
        eq[i] = eqi

        # (d) decisions at this close
        if i == 0 or (T[i] // 86400000) != (T[i - 1] // 86400000):
            day_start_eq = eqi
        halted = P["daily_loss"] > 0 and eqi <= day_start_eq * (1.0 - P["daily_loss"] / 100.0)
        if halted:
            halt_bars += 1
        if i + 1 >= n:
            continue

        can_trade = not halted
        ok_l = (inv == 0) or (P["close_opp"] and inv < 0)
        ok_s = (inv == 0) or (P["close_opp"] and inv > 0)
        take_l = bool(S["entryL"][i]) and can_trade and ok_l
        take_s = bool(S["entryS"][i]) and can_trade and ok_s and not take_l

        if halted and inv != 0:
            pending = {"kind": "close_all"}
            n_halts += 1
        elif take_l:
            q = f_qty(eqi, ci, S["dist"][i], P)
            if q > 0:
                pending = {"kind": "enterL", "q": q, "dist": S["dist"][i],
                           "close_sig": ci}
        elif take_s:
            q = f_qty(eqi, ci, S["dist"][i], P)
            if q > 0:
                pending = {"kind": "enterS", "q": q, "dist": S["dist"][i],
                           "close_sig": ci}
        elif inv > 0 and S["exitL"][i]:
            pending = {"kind": "close", "why": str(S["exit_reason_L"][i])}
        elif inv < 0 and S["exitS"][i]:
            pending = {"kind": "close", "why": str(S["exit_reason_S"][i])}

        # the management block: from the first close after the fill the bracket
        # re-anchors to the real fill price with the same frozen distance
        if inv != 0 and trade_stop > 0:
            d_ = trade_stop
            if inv > 0:
                sl_base = entry_px - d_
                tp_base = entry_px + d_ * tp_r if tp_r > 0 else None
            else:
                sl_base = entry_px + d_
                tp_base = entry_px - d_ * tp_r if tp_r > 0 else None

    return dict(eq=eq, trades=trades, n_open=int(inv != 0),
                open_fee=entry_fee,
                open_pos=dict(qty=abs(inv), entry=entry_px, side=1 if inv > 0 else -1,
                              entry_bar=entry_bar)
                if inv != 0 else None,
                n_halts=n_halts, halt_bars=halt_bars,
                funding_paid=fund_paid, n_funding_events=n_fund_events,
                entryL=S["entryL"], entryS=S["entryS"])


# ------------------------------------------------------------- metrics
def _pf(pnls):
    w = sum(p for p in pnls if p > 0)
    ls = sum(p for p in pnls if p <= 0)
    if ls == 0:
        return (float("inf") if w > 0 else 0.0)
    return w / abs(ls)


def _rd(v, k=4):
    if v is None:
        return None
    if isinstance(v, float) and not np.isfinite(v):
        return None
    return round(float(v), k)


def _stats(eq, T):
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / np.maximum(peak, 1e-12)
    yrs = (T[-1] - T[0]) / (365.25 * 86400000)
    rets = np.diff(eq) / eq[:-1]
    rets = rets[np.isfinite(rets)]
    sp = float(np.median(np.diff(T))) if len(T) > 2 else 3600000.0
    bpy = 365.25 * 86400000.0 / sp
    sharpe = (float(np.mean(rets) / np.std(rets)) * np.sqrt(bpy)
              if len(rets) > 2 and np.std(rets) > 0 else 0.0)
    return dict(ret=(eq[-1] / eq[0] - 1) * 100.0, dd=float(dd.max() * 100.0),
                years=yrs, final=float(eq[-1]), sharpe=sharpe)


def _year_returns(eq, T):
    y = defaultdict(list)
    for i in range(len(eq)):
        yr = dt.datetime.fromtimestamp(T[i] / 1000, dt.timezone.utc).year
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
    """Harness entry: one klines csv (+ optional funding json) -> artifact."""
    p = dict(params or {})
    tf = p.pop("tf", None)
    if tf not in TF_MINUTES:
        raise ValueError(f"fingrad: unsupported tf {tf!r} (use 1h/15m/5m/1m)")
    preset = str(p.pop("preset", "custom"))
    if preset not in PRESETS:
        raise ValueError(f"fingrad: unknown preset {preset!r}")
    sig_mode = str(p.pop("sig_mode", "confluence"))
    if sig_mode not in ("confluence", "a", "b", "either"):
        raise ValueError(f"fingrad: unknown sig_mode {sig_mode!r}")
    adx_mode = str(p.pop("adx_mode", "cross"))
    if adx_mode not in ("cross", "level", "literal"):
        raise ValueError(f"fingrad: unknown adx_mode {adx_mode!r}")
    exit_rule = str(p.pop("exit_rule", "auto"))
    if exit_rule not in ("auto", "hma", "ao", "hma_or_ao", "hma_and_ao"):
        raise ValueError(f"fingrad: unknown exit_rule {exit_rule!r}")
    costs_key = str(p.pop("costs", "author"))
    if costs_key not in COSTS:
        raise ValueError(f"fingrad: unknown costs {costs_key!r}")
    use_funding = bool(p.pop("funding", False))
    if p:
        raise ValueError(f"unknown fingrad params: {sorted(p)}")

    P = dict(PINE)
    P.update(PRESETS[preset])
    P["tf_minutes"] = TF_MINUTES[tf]

    t, o, h, l, c = [], [], [], [], []
    with open(paths[0]) as f:
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
    n = len(d["c"])
    if n < 300:
        raise ValueError(f"fingrad: only {n} bars in {paths[0]}")

    fund_rate = fund_ev = None
    funding_path = paths[1] if len(paths) > 1 else None
    if use_funding:
        if not funding_path:
            raise FileNotFoundError(
                "fingrad funding=true needs binance_funding/<SYM>_funding.json")
        recs = json.load(open(funding_path, encoding="utf-8"))
        ft = np.array([int(x["t"]) for x in recs], np.int64)
        fr = np.array([float(x["r"]) for x in recs])
        fund_rate = np.zeros(n)
        fund_ev = np.zeros(n, bool)
        j = np.searchsorted(d["t"], ft, side="left")
        ok = j < n
        fund_ev[j[ok]] = True
        fund_rate[j[ok]] = fr[ok]
        funding_covers = bool(ft.min() <= d["t"][0] + 8 * 3600 * 1000
                              and ft.max() >= d["t"][-1] - 8 * 3600 * 1000)
    else:
        funding_covers = False

    S = signals(d, P, sig_mode, adx_mode, exit_rule)
    ck = dict(COSTS[costs_key])
    res = execute(d, S, P, ck["fee"], ck["slip"], fund_rate, fund_ev)
    zi = execute(d, S, P, 0.0, 0.0, fund_rate, fund_ev)

    eq = res["eq"]
    trs = res["trades"]
    pnls = [tr["pnl"] for tr in trs]
    n_tr = len(pnls)
    pf = _pf(pnls)
    wr = 100.0 * len([1 for x in pnls if x > 0]) / n_tr if n_tr else 0.0

    st = _stats(eq, d["t"])
    zst = _stats(zi["eq"], d["t"])
    bh = (d["c"][-1] / d["c"][0] - 1.0) * 100.0
    bpeak = np.maximum.accumulate(d["c"])
    bench_dd = float(((d["c"] / bpeak - 1.0).min()) * 100.0)

    mid = n // 2
    h1 = [tr["pnl"] for tr in trs if tr["exit_bar"] < mid]
    h2 = [tr["pnl"] for tr in trs if tr["exit_bar"] >= mid]
    p3 = _thirds(eq)

    gross = sum(x for x in pnls if x > 0)
    fees_total = sum(tr["fees"] for tr in trs) \
        + (res["open_fee"] if res["n_open"] else 0.0)
    srt = sorted(pnls, reverse=True)
    best5 = sum(x for x in srt[:5] if x > 0)
    total = sum(pnls)
    conc_share = 100.0 * best5 / total if total > 0 else None
    conc_without = 100.0 * (total - best5) / total if total > 0 else None

    by_side, by_why = {}, {}
    for tr in trs:
        s = by_side.setdefault(tr["side"], dict(n=0, pnl=0.0, w=0.0, lsum=0.0, nw=0))
        s["n"] += 1
        s["pnl"] += tr["pnl"]
        if tr["pnl"] > 0:
            s["w"] += tr["pnl"]; s["nw"] += 1
        else:
            s["lsum"] += -tr["pnl"]
        w_ = by_why.setdefault(tr["why"], dict(n=0, pnl=0.0, nw=0))
        w_["n"] += 1
        w_["pnl"] += tr["pnl"]
        w_["nw"] += 1 if tr["pnl"] > 0 else 0

    tables = []
    for side in ("L", "S"):
        s = by_side.get(side)
        if not s:
            continue
        tables.append(dict(kind="side", side=side, trades=s["n"],
                           pnl=_rd(s["pnl"], 2),
                           win_rate_pct=_rd(100.0 * s["nw"] / s["n"], 2),
                           PF=_rd(s["w"] / s["lsum"]) if s["lsum"] > 0 else None))
    for why in sorted(by_why):
        w_ = by_why[why]
        tables.append(dict(kind="exit", reason=why, count=w_["n"],
                           closed_pnl=_rd(w_["pnl"], 2),
                           win_rate_pct=_rd(100.0 * w_["nw"] / w_["n"], 2)))
    for k, v in _year_returns(eq, d["t"]).items():
        tables.append(dict(kind="year", year=int(k), ret_pct=_rd(v)))
    tables += [dict(kind="trade", **{k: (_rd(v, 6) if isinstance(v, float) else v)
                                     for k, v in tr.items()})
               for tr in trs[:4000]]

    m = dict(
        preset=preset, sig_mode=sig_mode, adx_mode=adx_mode,
        exit_eff=S["exit_eff"], costs=costs_key,
        hma_len=int(P["hma_len"]), htf_minutes=int(P["htf_minutes"]),
        htf_le_chart=bool(P["htf_minutes"] <= P["tf_minutes"]),
        bars=int(n), years=_rd(st["years"], 2),
        n_trades=n_tr, n_open=res["n_open"],
        return_pct=_rd(st["ret"]), max_dd_pct=_rd(st["dd"]),
        sharpe=_rd(st["sharpe"]), final_equity=_rd(st["final"], 2),
        profit_factor=_rd(pf), win_rate=_rd(wr),
        expectancy=_rd(float(np.mean(pnls)) if pnls else 0.0),
        avg_bars_held=_rd(float(np.mean([tr["bars"] for tr in trs])) if trs else 0.0, 2),
        bh_return_pct=_rd(bh), bench_dd_pct=_rd(bench_dd),
        beats_bh=bool(st["ret"] > bh),
        ret_zero_pct=_rd(zst["ret"]), drag_pp=_rd(zst["ret"] - st["ret"]),
        fees=_rd(fees_total, 2),
        fee_over_gross_pct=_rd(100.0 * fees_total / gross) if gross > 0 else None,
        cost_bp_roundtrip=_rd(2.0 * (ck["fee"] + ck["slip"]) * 1e4, 2),
        fee_bps_per_side=_rd(ck["fee"] * 1e4, 2),
        slip_bps_per_side=_rd(ck["slip"] * 1e4, 2),
        best5_share_pct=_rd(conc_share),
        net_without_best5_pct=_rd(conc_without),
        pf_h1=_rd(_pf(h1)), n_h1=len(h1),
        pf_h2=_rd(_pf(h2)), n_h2=len(h2),
        ret_h1_pct=_rd(100.0 * (eq[mid] / eq[0] - 1.0)),
        ret_h2_pct=_rd(100.0 * (eq[-1] / eq[mid] - 1.0)),
        period1_pct=_rd(p3[0]), period2_pct=_rd(p3[1]), period3_pct=_rd(p3[2]),
        n_periods_green=int(sum(1 for x in p3 if x > 0)),
        year_returns={str(k): _rd(v) for k, v in _year_returns(eq, d["t"]).items()},
        n_signals_long=int(S["entryL"].sum()),
        n_signals_short=int(S["entryS"].sum()),
        n_halts=res["n_halts"], halt_bars=res["halt_bars"],
        funding_charged=bool(use_funding),
        funding_paid=_rd(res["funding_paid"], 2) if use_funding else None,
        funding_covers_bars=bool(funding_covers) if use_funding else None,
        n_funding_events=res["n_funding_events"] if use_funding else 0,
        flag="OK" if n_tr >= 30 else "INSUFFICIENT_SAMPLE",
    )
    return {"metrics": m, "tables": tables}


if __name__ == "__main__":
    print(__doc__)
