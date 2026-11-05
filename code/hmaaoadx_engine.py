#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hmaaoadx_engine.py — port of code/fingrad_hma_ao_adx_strategy.pine
("Fingrad HMA · AO · ADX Strategy", Pine v6; author file copied BYTE-IDENTICAL
from C:/Users/Lenovo/Downloads/fingrad_hma_ao_adx_strategy.pine, sha256
d3aabd19a1795f3020f0b26f659e1710e60c1dc5c4e3db66eb65f2b02f58b860 — source of
record; audited by code/_hmaaoadx_audit.py BEFORE any real-data run).

THE PINE, READ END TO END
    strategy(...) with initial_capital 1000, commission 0.05 %/side,
    slippage 2 ticks, pyramiding 0, margin 5 % (20x), maxLev 10 (script
    input), process_orders_on_close = FALSE -> signals evaluate on bar
    close; orders fill at the NEXT bar's open.

    Two systems share the HMA spine:
      System A  LONG  = close > HMA  and AO > 0 and AO rising (green)
                SHORT = close < HMA  and AO < 0 and AO falling (red)
      System B  LONG  = close > HMA  and ADX rule (mode) — direction via +DI
                SHORT = close < HMA  and ADX rule (mode) — direction via -DI
    Default sigMode "A + B confluence": aL AND bL / aS AND bS.
    Default adxMode "Cross (mirrored, fixed)": the SAME recent-up-cross rule
    (ADX crossed above 25 within the last adxWin=3 bars AND ADX still above
    25) arms BOTH sides; direction comes from DI (+DI > -DI for longs,
    -DI > +DI for shorts).
    Entries fire only on a FRESH signal (st flips false -> true), long wins
    ties (takeS := ... and not takeL), closeOpp reverses on the opposite
    entry signal.

    Exit rules (exitEff): "Auto" resolves to "HMA close only" in mode B,
    otherwise "HMA or AO flip" — for the default modes a long exits when
    close < hma OR the AO has flipped red-below-zero (aoDnOK); a short is
    mirrored. Exits are market orders: they fill the NEXT bar's open.

    Optional bracket (default ON: atr_stop_mult 2.0, tp_r 0 -> no TP):
      stop distance = the SIGNAL bar's atr_stop_mult * atr(14);
      sizing is risk-based with the bracket: q = eq*1%/dist; without a stop
      q = eq*fixedNotional%/close; both capped at eq*maxLev/close; floor 0
      (a zero q places NO order — the Pine `if q > 0` guard; the take flags
      themselves stay true, so a zero-size take still suppresses the signal
      exit, exactly like the Pine).
      strategy.exit re-anchors to the real average fill price once the
      position exists (lvlSL = ep -/+ dist); the port arms the bracket from
      the FILL price at the fill bar.
    Daily-loss breaker 3 % of day-start equity default ON: entry ban while
    halted, close_all fills at the next open; the breaker resets on the
    first bar of each new UTC day (dayStartEq = equity at that bar's close).
    Date-range filter default OFF (the port refuses enabling it — out of
    scope for the campaign; the artifact names the refusal).

PINE SEMANTICS THE PORT KEEPS (declared conventions)
    - Chart timeframe = the bars fed (1h campaign; the adapter refuses
      others). HTF filter htfTF = "60" == the 1h bars themselves: on a
      60-minute chart request.security(...,"60",[hma[1],hma[2]],
      lookahead_on) returns the two PREVIOUS chart bars' HMA values —
      hH1 = hma[t-1], hH2 = hma[t-2] — which the strategy's own dashboard
      flags as "HTF <= chart TF". Port reproduces it.
    - `na` comparisons are falsy: no signal can fire before its indicators
      exist; aoGreen uses ao > ao[1] with an NaN previous bar.
    - barssince: 0 on the trigger bar itself (recUp stays armed adxWin bars
      INCLUDING the cross bar, requiring ADX still above the threshold).
    - At most one actionable order per bar here (entry needs flat/opposite;
      the signal exit is suppressed exactly when a reversal entry will
      fire; the halt's close_all overrides). Pine's per-bar script order:
      day snapshot -> halt -> signal exits -> entries.
    - Reversal = one fill of |old|+new quantity at the same open: the closed
      leg pays the whole-order fee (its exit fee), the new leg pays its
      entry fee — the dollar total is identical either way it decomposes.
    - Intrabar brackets: stop BEFORE limit on a bar spanning both
      (conservative; the emaadx port audit proved the same convention), gap
      rule: a bar opening beyond the level fills at its open; stop fills
      carry adverse slippage, limit fills fill clean (TV slippage applies
      to market-type fills only). The bracket may fire on the very bar the
      position opened.
    - NaN-ATR corner reproduced: `dist > 0` with dist = NaN is false, so the
      no-stop sizing branch and NO bracket result (Pine's own NaN flow on
      use_cost=false warmups); the default cost gate makes it unreachable.
    - Unfinished position at the end of data: marked to the last close,
      EXCLUDED from closed-trade statistics (one open trade reported).
    - INIT = 1000.0 (the Pine initial_capital); results are percents of
      equity; fractional crypto sizing carries no rounding dependency.
    - The cost GATE uses the Pine INPUT literals forever (feePct 0.05 % +
      slipPct 0.01 % -> min ATR%% = 1.5 * 2 * 0.06 = 0.18 %), independent of
      the accounting preset chosen for the run.

COSTS
    author  : 0.05 % commission + 0.01 % slippage per side (the input
              mirror; the header's literal 2-tick slippage is ~1e-4 bps on
              these series — declared negligible, the input fraction stands).
    repo6x5 : 6 bps commission + 5 bps slippage per side (repo standard).
    zero    : control pass inside every artifact; drag_pp = ret_zero − scored.

PRIMITIVES
    rma / true_range / atr_pine / dmi_pine / cross_over / cross_under are
    IMPORTED from code/emaadx_engine.py (known-answer audited there:
    results/emaadx_audit_known_answers.txt). wma / hma_pine / sma /
    barssince / the HTF pair and the state machine are new here; everything
    is re-proven by code/_hmaaoadx_audit.py with hand-literal arithmetic
    BEFORE any real-data run.

    Trade rows and equity LEVELS follow the dspack_engine contract (lv
    length n+1; trades carry usd/u/fees), so dspack_engine._score_trades and
    dspack_engine._gates (G1..G6 + gates_pass_all) score every cell
    identically to the dspack family; dspack_engine.load_csv stays the only
    reader (1h spacing gate; WARMUP_BARS=2400 / SCORE_BARS=4368 windows;
    BARS_PER_YEAR=8760 sharpe scaling).
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dspack_engine as E1
import emaadx_engine as EP     # audited Pine primitives (rma/atr/dmi/cross)

INIT = 1000.0                  # Pine initial_capital

# Pine inputs as shipped (no knobs widen the strategy geometry; only
# `window` and `costs` are CLI parameters — the audit pins the rest).
PINE = dict(
    hma_len=21,
    ao_fast=5, ao_slow=34,
    di_len=14, adx_smooth=14, adx_thr=25.0,
    adx_mode="cross",          # "cross" | "level" | "literal"
    adx_win=3, req_di=True,
    sig_mode="confl",          # "confl" | "a" | "b" | "either"
    exit_rule="auto",          # "auto" | "hma" | "ao" | "both" | "either"
    allow_long=True, allow_short=True,
    use_htf=True,
    use_cost=True, atr_len=14, cost_mult=1.5,
    gate_fee_pct=0.0005, gate_slip_pct=0.0001,   # cost-gate input mirror
    atr_stop_mult=2.0, tp_r=0.0, risk_pct=1.0,
    fixed_notional_pct=100.0, max_lev=10.0, close_opp=True,
    daily_loss=3.0,
    use_dates=False,
)

COSTS = {
    "author": dict(fee=0.0005, slip=0.0001),
    "repo6x5": dict(fee=0.0006, slip=0.0005),
    "zero": dict(fee=0.0, slip=0.0),
}


# ------------------------------------------------------------- indicators
def sma(x, n):
    """Plain rolling mean, min_periods=n (NaN before the first full window)."""
    import pandas as pd
    return pd.Series(np.asarray(x, float)).rolling(n).mean().to_numpy()


def wma(x, n):
    """Linearly weighted mean, weights 1..n; NaN before the first full
    window (a window holding any NaN stays NaN)."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    w = np.arange(1.0, n + 1.0)
    for i in range(n - 1, len(x)):
        win = x[i - n + 1:i + 1]
        if not np.isnan(win).any():
            out[i] = float(np.dot(win, w) / w.sum())
    return out


def hma_pine(x, n):
    """Pine ta.hma: wma(2*wma(x, n//2) - wma(x, n), round(sqrt(n)))."""
    half = int(n) // 2
    inner = 2.0 * wma(x, half) - wma(x, n)
    return wma(inner, int(round(float(np.sqrt(n)))))


def htf_hma_pair(hma_series):
    """request.security(chart, "60", [hma[1], hma[2]], lookahead_on) on a
    60-minute chart == the two previous chart bars' HMA."""
    h = np.asarray(hma_series, float)
    h1 = np.full(len(h), np.nan)
    h2 = np.full(len(h), np.nan)
    if len(h) > 1:
        h1[1:] = h[:-1]
    if len(h) > 2:
        h2[2:] = h[:-2]
    return h1, h2


def barssince(mask):
    """ta.barssince: bars since the last TRUE (0 on the trigger bar), NaN
    until the first true ever."""
    mask = np.asarray(mask, bool)
    out = np.full(len(mask), np.nan)
    for i in range(len(mask)):
        if mask[i]:
            out[i] = 0.0
        elif i > 0 and not np.isnan(out[i - 1]):
            out[i] = out[i - 1] + 1.0
    return out


# ------------------------------------------------------------- simulation
def simulate(d, P, fee, slip):
    """Bar-by-bar port with process_orders_on_close=false.

    Per bar i, in exact order:
      (1) the ONE order the previous close submitted fills at THIS bar's
          open (entry / signal exit / halt close / reversal — the fill
          slips against the side; the whole-order fee applies on the fill
          notional; a reversal closes the old leg then opens the new leg
          at the same fill price);
      (2) intrabar brackets on the live position (stop before limit, gap
          rule, entry-bar stop possible);
      (3) new UTC day -> dayStartEq := equity here (after the fills, at the
          close of the day's first bar) and the breaker re-arms;
      (4) close processing in Pine's script order: halt verdict from the
          CLOSE equity -> signal exits (suppressed exactly when a reversal
          entry fires; long wins ties) -> fresh-signal entries sized from
          the equity marked at THIS close;
      (5) equity marked at close.
    """
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    t = d["t"]
    n = len(c)
    hl2 = (h + l) / 2.0
    hma = hma_pine(c, P["hma_len"])
    ao = sma(hl2, P["ao_fast"]) - sma(hl2, P["ao_slow"])
    A = EP.atr_pine(h, l, c, P["atr_len"])
    diP, diM, adx = EP.dmi_pine(h, l, c, P["di_len"], P["adx_smooth"])

    with np.errstate(invalid="ignore"):
        okh = (~np.isnan(c)) & (~np.isnan(hma))
        hmaL = okh & (c > hma)
        hmaS = okh & (c < hma)
        ao_prev = np.full(n, np.nan)
        ao_prev[1:] = ao[:-1]
        aoGreen = (~np.isnan(ao)) & (~np.isnan(ao_prev)) & (ao > ao_prev)
        aoUpOK = (~np.isnan(ao)) & (ao > 0.0) & aoGreen
        aoDnOK = (~np.isnan(ao)) & (ao < 0.0) & ~aoGreen
        cUp = EP.cross_over(adx, np.full(n, float(P["adx_thr"])))
        cDn = EP.cross_under(adx, np.full(n, float(P["adx_thr"])))
        sinceU = barssince(cUp)
        sinceD = barssince(cDn)
        okA = ~np.isnan(adx)
        recUp = okA & ~np.isnan(sinceU) & (sinceU <= float(P["adx_win"])) \
            & (adx > P["adx_thr"])
        recDn = okA & ~np.isnan(sinceD) & (sinceD <= float(P["adx_win"])) \
            & (adx < P["adx_thr"])
        diIsOk = (~np.isnan(diP)) & (~np.isnan(diM))
        diBull = diIsOk & (diP > diM)
        diBear = diIsOk & (diM > diP)

        if P["adx_mode"] == "level":
            adxOkL = okA & (adx > P["adx_thr"]) & \
                (diBull if P["req_di"] else True)
            adxOkS = okA & (adx > P["adx_thr"]) & \
                (diBear if P["req_di"] else True)
        elif P["adx_mode"] == "literal":
            adxOkL, adxOkS = recUp, recDn
        else:                                  # "Cross (mirrored, fixed)"
            adxOkL = recUp & (diBull if P["req_di"] else True)
            adxOkS = recUp & (diBear if P["req_di"] else True)

        if P["use_htf"]:
            h1, h2 = htf_hma_pair(hma)
            okh1 = (~np.isnan(h1)) & (~np.isnan(h2))
            htfOkL = okh1 & (h1 > h2)
            htfOkS = okh1 & (h1 < h2)
        else:
            htfOkL = np.ones(n, bool)
            htfOkS = np.ones(n, bool)

        atrPct = np.full(n, np.nan)
        mok = (~np.isnan(c)) & (c != 0) & ~np.isnan(A)
        atrPct[mok] = A[mok] / c[mok] * 100.0
        minAtr = (float(P["cost_mult"]) * 2.0 *
                  (P["gate_fee_pct"] + P["gate_slip_pct"]) * 100.0)
        costOk = (~np.isnan(atrPct)) & (atrPct >= minAtr)
        if not P["use_cost"]:
            costOk = np.ones(n, bool)

        aL = hmaL & aoUpOK
        aS = hmaS & aoDnOK
        bL = hmaL & adxOkL
        bS = hmaS & adxOkS
        if P["sig_mode"] == "a":
            modeL, modeS = aL, aS
        elif P["sig_mode"] == "b":
            modeL, modeS = bL, bS
        elif P["sig_mode"] == "either":
            modeL, modeS = aL | bL, aS | bS
        else:                                  # "A + B confluence"
            modeL, modeS = aL & bL, aS & bS

        stL = modeL & htfOkL & costOk & bool(P["allow_long"])
        stS = modeS & htfOkS & costOk & bool(P["allow_short"])
        stL_prev = np.zeros(n, bool)
        stS_prev = np.zeros(n, bool)
        stL_prev[1:] = stL[:-1]
        stS_prev[1:] = stS[:-1]
        entryL = stL & ~stL_prev
        entryS = stS & ~stS_prev

        xe = P["exit_rule"]
        if xe == "auto":
            xe = "hma" if P["sig_mode"] == "b" else "either"
        if xe == "hma":
            exitL, exitS = hmaS, hmaL
        elif xe == "ao":
            exitL, exitS = aoDnOK, aoUpOK
        elif xe == "both":
            exitL, exitS = hmaS & aoDnOK, hmaL & aoUpOK
        else:                                  # "either"
            exitL, exitS = hmaS | aoDnOK, hmaL | aoUpOK

    cash = INIT
    inv = 0.0
    entry_px = 0.0
    entry_fee = 0.0
    entry_bar = -1
    pendStop = 0.0                 # stop distance frozen at the signal bar
    slP = tpP = None               # absolute bracket prices (re-anchored)
    prev_day = None
    dayStartEq = INIT
    halted = False
    pending = ()                   # the single order slot
    trades = []
    open_tail = None
    lv = np.full(n + 1, np.nan)
    lv[0] = INIT
    n_sigL = n_sigS = 0

    def close_trade(i_exit, fill, why, exit_fee):
        nonlocal cash, inv, slP, tpP, entry_fee, entry_px, entry_bar
        sign = 1.0 if inv > 0 else -1.0
        qty = abs(inv)
        pnl = sign * qty * (fill - entry_px) - entry_fee - exit_fee
        cash += sign * qty * fill - exit_fee
        trades.append(dict(side="L" if inv > 0 else "S",
                           entry_bar=entry_bar, u=i_exit,
                           entry=entry_px, exit=fill, usd=pnl,
                           qty=qty, why=why,
                           entry_fee=entry_fee, exit_fee=exit_fee,
                           fees=entry_fee + exit_fee))
        inv = 0.0
        entry_fee = 0.0
        entry_px = 0.0
        entry_bar = -1
        slP = tpP = None

    for i in range(n):
        # (1) the previous close's order fills at THIS bar's open
        if pending:
            kind = pending
            pending = ()
            fo = o[i]
            if kind[0] == "entry":
                side, q = kind[1], kind[2]
                fill = fo * (1.0 + slip) if side == 1 else fo * (1.0 - slip)
                if side * inv < 0:            # reversal: old leg closes first
                    old_fee = abs(inv) * fill * fee
                    close_trade(i, fill, "reverse", old_fee)
                turn = q * fill
                f_new = turn * fee
                cash -= side * turn            # buy pays; short credits
                cash -= f_new
                inv = side * q
                entry_px = fill
                entry_fee = f_new
                entry_bar = i
                dist = pendStop
                if dist > 0:                   # NaN>0 false -> no bracket
                    slP = fill + dist if side < 0 else fill - dist
                    tpP = None
                    if P["tp_r"] > 0:
                        tpP = fill - dist * P["tp_r"] if side < 0 \
                            else fill + dist * P["tp_r"]
            else:
                fill = fo * (1.0 - slip) if inv > 0 else fo * (1.0 + slip)
                why = "daily halt" if kind[0] == "closeall" else kind[1]
                close_trade(i, fill, why, abs(inv) * fill * fee)

        # (2) intrabar brackets (stop before limit; gap rule) — stop fills
        # degrade the level by the RELATIVE slippage fraction
        if inv != 0:
            if inv > 0 and slP is not None and l[i] <= slP:
                px = slP if o[i] > slP else o[i]
                close_trade(i, px * (1.0 - slip), "stop",
                            abs(inv) * px * (1.0 - slip) * fee)
            elif inv > 0 and tpP is not None and h[i] >= tpP:
                px = tpP if o[i] < tpP else o[i]
                close_trade(i, px, "tp", abs(inv) * px * fee)
            elif inv < 0 and slP is not None and h[i] >= slP:
                px = slP if o[i] < slP else o[i]
                close_trade(i, px * (1.0 + slip), "stop",
                            abs(inv) * px * (1.0 + slip) * fee)
            elif inv < 0 and tpP is not None and l[i] <= tpP:
                px = tpP if o[i] > tpP else o[i]
                close_trade(i, px, "tp", abs(inv) * px * fee)

        # (3) UTC day snapshot (fresh day re-arms the breaker)
        day = int(t[i]) // 86_400_000
        if day != prev_day:
            prev_day = day
            dayStartEq = cash + inv * c[i]
            halted = False

        eq_mark = cash + inv * c[i]

        # (4) close processing: halt -> exits -> entries (Pine script order)
        if P["daily_loss"] > 0 and eq_mark <= \
                dayStartEq * (1.0 - P["daily_loss"] / 100.0):
            halted = True
        can_trade = not halted
        flat = inv == 0.0
        inL = inv > 0.0
        inS = inv < 0.0
        okL = flat or (P["close_opp"] and inS)
        okS = flat or (P["close_opp"] and inL)
        takeL = bool(entryL[i]) and can_trade and okL
        takeS = bool(entryS[i]) and can_trade and okS and not takeL

        if halted and (inL or inS):
            pending = ("closeall",)
        else:
            if inL and exitL[i] and not takeS:
                pending = ("close", "signal exit")
            elif inS and exitS[i] and not takeL:
                pending = ("close", "signal exit")
        if takeL:
            dist = (P["atr_stop_mult"] * A[i]
                    if P["atr_stop_mult"] > 0 else 0.0)
            q = qty_from_eq(eq_mark, c[i], dist, P)
            if q > 0:
                pending = ("entry", 1, q)
                pendStop = dist
                n_sigL += 1
        elif takeS:
            dist = (P["atr_stop_mult"] * A[i]
                    if P["atr_stop_mult"] > 0 else 0.0)
            q = qty_from_eq(eq_mark, c[i], dist, P)
            if q > 0:
                pending = ("entry", -1, q)
                pendStop = dist
                n_sigS += 1

        # (5) mark
        lv[i + 1] = cash + inv * c[i]

    if inv != 0.0:
        open_tail = {"entry_bar": entry_bar, "qty": abs(inv),
                     "side": "L" if inv > 0 else "S"}
    return dict(lv=lv, trades=trades, open_tail=open_tail,
                entryL=entryL, entryS=entryS, n_sigL=n_sigL, n_sigS=n_sigS,
                hma=hma, ao=ao, atr=A, diP=diP, diM=diM, adx=adx,
                stL=stL, stS=stS, exitL=exitL, exitS=exitS,
                aL=aL, aS=aS, bL=bL, bS=bS, modeL=modeL, modeS=modeS,
                adxOkL=adxOkL, adxOkS=adxOkS,
                htfOkL=htfOkL, htfOkS=htfOkS, costOk=costOk)


def qty_from_eq(eq, close_px, dist, P):
    """Pine f_qty(dist): equity-based size with the maxLev cap; NaN dist
    falls into the no-stop sizing branch (Pine's `dist > 0` is falsy on
    NaN); q==0 places no order."""
    eq = max(eq, 0.0)
    if close_px > 0:
        q_cap = eq * P["max_lev"] / close_px
    else:
        q_cap = 0.0
    if dist > 0:
        q_raw = (eq * P["risk_pct"] / 100.0) / dist
    elif close_px > 0:
        q_raw = eq * P["fixed_notional_pct"] / 100.0 / close_px
    else:
        q_raw = 0.0
    return max(min(q_raw, q_cap), 0.0)


# ------------------------------------------------------------- run entry
def run_suite(paths, params):
    """One 1h symbol file -> {"metrics": ..., "tables": [row]} artifact."""
    params = dict(params or {})
    window = params.get("window", "full")
    costs_key = params.get("costs", "repo6x5")
    if window not in ("full", "last6mo"):
        raise ValueError(f"window {window!r} not supported")
    if costs_key not in COSTS:
        raise ValueError(f"costs {costs_key!r} not supported")
    df = E1.load_csv(paths[0])

    sf = 0
    if window == "last6mo":
        need = E1.WARMUP_BARS + E1.SCORE_BARS          # 2400 + 4368 = 6768
        if len(df) < need:
            raise ValueError(f"{paths[0]}: {len(df)} bars; last6mo needs {need}")
        df = df.iloc[-need:]
        sf = E1.WARMUP_BARS
    d = dict(t=df.index.view("int64").astype(np.int64),
             o=df["open"].to_numpy(), h=df["high"].to_numpy(),
             l=df["low"].to_numpy(), c=df["close"].to_numpy())
    n = len(d["c"])
    idx = df.index

    ck = COSTS[costs_key]
    res = simulate(d, PINE, ck["fee"], ck["slip"])
    seg = {"trades": res["trades"], "open_run": res["open_tail"]}
    bref = d["c"][sf - 1] if sf > 0 else d["c"][0]
    bench = (float(d["c"][-1] / bref) - 1.0) * 100.0

    zres = simulate(d, PINE, 0.0, 0.0)
    zseg = {"trades": zres["trades"], "open_run": zres["open_tail"]}

    row = E1._score_trades(seg, res["lv"], idx, sf, n, bench)
    zrow = E1._score_trades(zseg, zres["lv"], idx, sf, n, bench)
    row["strat"] = "hmaaoadx"
    row["window"] = window
    row["costs"] = costs_key
    row["n_signals_long"] = int(res["entryL"][sf:].sum())
    row["n_signals_short"] = int(res["entryS"][sf:].sum())
    row["ret_zero_pct"] = zrow["ret_pct"]
    row["pf_zero"] = zrow["pf_strict"]
    row["drag_pp"] = row["ret_zero_pct"] - row["ret_pct"]
    row["bench_ret_pct"] = bench
    E1._gates(row, window)

    metrics = dict(
        strat="hmaaoadx", window=window, costs=costs_key,
        bars=int(n), scored_bars=int(n - sf), warmup_bars=int(sf),
        n_signals_long=row["n_signals_long"],
        n_signals_short=row["n_signals_short"],
        n_trades_reported=int(row["n_trades"]),
        n_open_at_end=int(row["n_open_at_end"]) if
        row.get("n_open_at_end") is not None else 0,
        bench_ret_pct=round(bench, 6),
    )
    return {"metrics": metrics, "tables": [row]}


if __name__ == "__main__":
    print(__doc__)
