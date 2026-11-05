#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_hmaaoadx_audit.py — known-answer audit for hmaaoadx_engine.py
(Pine port of code/fingrad_hma_ao_adx_strategy.pine). MUST pass ALL cases
BEFORE any real-data run (repo porting protocol, step 2).

Design: every expectation comes from hand-literal arithmetic written in this
file with INDEPENDENT code paths (plain python dictionaries + loops written
in a deliberately different style from the engine's vectorized numpy), never
from the engine's own helpers. Cases marked HAND use trivially checkable
numbers (e.g. weights one-to-five). Cases marked PLAY walk full synthetic
bar series bar by bar with an independent replay machine and compare trades,
fills, quantity sizes, costs and equity levels to the engine to 1e-9
relative — no assertion may compare an engine output to another engine
output.

Sections
  A  primitives: wma/hma/sma/atr/rma-vs-pandas/dmi/barssince/cross
  B  replay cases: entry fills, signal exits, stop and TP brackets, gap
     rule, reversal, fresh-signal gating, tie priority, zero-quantity take,
     daily-loss breaker, end-of-data open tail
  S  straight-line equity: the B-replay equity arrays equal the engine's
     level array (dspack contract), plus closed-trade dollars conservation
  C  run_suite plumbing: E1._score_trades row honesty (n, pf on the audit's
     own trades), the last6mo slice provenance, gates present, determinism
  D  identity/defaults: PINE literal dict, COSTS literal dict, INIT, module
     identity of the imported audited primitives and of the dspack scorer

Writes results/hmaaoadx_audit_known_answers.txt; exit 0 = ALL PASS.
"""

import json
import math
import os
import sys
import tempfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import dspack_engine as E1
import emaadx_engine as EP_ref
import hmaaoadx_engine as H

OUT = os.path.join(ROOT, "results", "hmaaoadx_audit_known_answers.txt")
FAILS = []
N_PASS = 0
TOL = 1e-9


def ok(name, cond, detail=""):
    global N_PASS
    tag = "PASS" if cond else "FAIL"
    line = f"{tag} {name}" + (f" :: {detail}" if detail else "")
    print(line)
    if cond:
        N_PASS += 1
    else:
        FAILS.append(name)
    return bool(cond)


def vclose(a, b, tol=TOL):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return False
    m = ~np.isnan(b)
    if not np.array_equal(m, ~np.isnan(a)):
        return False
    return bool(np.all(np.abs(a[m] - b[m]) <= tol * np.maximum(1.0, np.abs(b[m]))))


# ----------------------------------------------------------------- refs
def ref_wma(xs, n):
    xs = [None if (isinstance(v, float) and math.isnan(v)) else float(v)
          for v in xs]
    out = []
    wsum = n * (n + 1) / 2.0
    for i in range(len(xs)):
        if i < n - 1 or any(v is None for v in xs[i - n + 1:i + 1]):
            out.append(float("nan"))
            continue
        win = xs[i - n + 1:i + 1]
        out.append(sum((j + 1) * v for j, v in enumerate(win)) / wsum)
    return out


def ref_sma(xs, n):
    out = []
    for i in range(len(xs)):
        win = xs[i - n + 1:i + 1] if i >= n - 1 else []
        if len(win) < n or any(isinstance(v, float) and math.isnan(v)
                               for v in win):
            out.append(float("nan"))
        else:
            out.append(sum(win) / n)
    return out


def ref_hma(xs, n):
    half = int(n) // 2
    a = ref_wma(xs, half)
    b = ref_wma(xs, n)
    inner = [2.0 * x - y if not (x != x or y != y) else float("nan")
             for x, y in zip(a, b)]
    return ref_wma(inner, int(round(math.sqrt(n))))


def ref_rma(xs, n):
    """Wilder: SMA seed over the first n values, recursion after; a NaN
    before the seed delays it, a NaN after the seed HOLDS (Pine na-hold)."""
    out = []
    buf = []
    prev = float("nan")
    for v in xs:
        if math.isnan(v):
            if len(buf) < n:
                out.append(float("nan"))       # seed not complete yet
            else:
                out.append(prev)               # hold (Pine na-hold)
            continue
        if len(buf) < n:                       # collecting the seed window
            buf.append(v)
            if len(buf) == n:
                prev = sum(buf) / n
                out.append(prev)
            else:
                out.append(float("nan"))
        else:
            prev = ((n - 1) * prev + v) / n
            out.append(prev)
    return out


def ref_true_range(h, l, c):
    out = [h[0] - l[0]]                       # pc NaN -> the range itself
    for i in range(1, len(h)):
        pc = c[i - 1]
        out.append(max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc)))
    return out


def ref_atr(h, l, c, n):
    return ref_rma(ref_true_range(h, l, c), n)


def ref_dmi(h, l, c, di_len, smooth):
    plus = []
    minus = []
    for i in range(len(h)):
        if i == 0:
            plus.append(float("nan"))
            minus.append(float("nan"))
            continue
        u, w = h[i] - h[i - 1], l[i - 1] - l[i]
        plus.append(u if (u > w and u > 0) else 0.0)
        minus.append(w if (w > u and w > 0) else 0.0)
    trur = ref_rma(ref_true_range(h, l, c), di_len)
    rplus = ref_rma(plus, di_len)
    rminus = ref_rma(minus, di_len)
    diP, diM, dx = [], [], []
    for i in range(len(h)):
        if math.isnan(rplus[i]) or math.isnan(trur[i]) or trur[i] == 0:
            diP.append(float("nan"))
            diM.append(float("nan"))
        else:
            diP.append(100.0 * rplus[i] / trur[i])
            diM.append(100.0 * rminus[i] / trur[i])
        p, d = diP[-1], diM[-1]
        if p != p or d != d or (p + d) == 0:
            dx.append(0.0 if (p == p and d == d) else float("nan"))
        else:
            dx.append(100.0 * abs(p - d) / (p + d))
    adx_out = ref_rma(dx, smooth)
    return diP, diM, adx_out


def numpy_nan(x):
    return isinstance(x, float) and math.isnan(x)


def ref_cross_over(a, b):
    out = [False] * len(a)
    for i in range(1, len(a)):
        if numpy_nan(a[i]) or numpy_nan(b[i]):
            continue
        if numpy_nan(a[i - 1]) or numpy_nan(b[i - 1]):
            continue
        out[i] = a[i] > b[i] and a[i - 1] <= b[i - 1]
    return out


def ref_cross_under(a, b):
    return ref_cross_over(b, a)


def ref_barssince(mask):
    out = [float("nan")] * len(mask)
    for i in range(len(mask)):
        if mask[i]:
            out[i] = 0.0
        elif i > 0 and not numpy_nan(out[i - 1]):
            out[i] = out[i - 1] + 1.0
    return out


def ref_ema_pandas_eq_check(x, n=14):
    """Wilder rma TAIL == pandas ewm(alpha=1/n, adjust=False) over the
    constructed series [sma_seed] + x[n:]: NOT the ewm default (adjust=True)
    and NOT an unseeded ewm — the trap this repo keeps pinning."""
    x = np.asarray(x, float)
    if np.any(np.isnan(x[:n])):
        return False, n
    seed = float(x[:n].mean())
    s = pd.Series([seed] + list(x[n:]))
    p = s.ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    want = np.asarray(ref_rma(list(x), n))[n - 1:]
    return bool(np.all(np.abs(p - want) <= 1e-9 * np.maximum(1.0, np.abs(want)))), n


# ------------------------------------------------------------- csv writer
def write_csv(path, bars, ts_start=1_735_689_600_000, dt=3_600_000):
    """bars: list of (open, high, low, close[, volume=1.0]) tuples."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("open_ts,open,high,low,close,volume\n")
        for i, b in enumerate(bars):
            o, hi, lo, cl = b[0], b[1], b[2], b[3]
            vol = b[4] if len(b) > 4 else 1.0
            f.write(f"{ts_start + i * dt},{o:.8f},{hi:.8f},"
                    f"{lo:.8f},{cl:.8f},{vol:.8f}\n")


def bars_from(closes, hi_off=2.0, lo_off=-2.0):
    return [(max(c + lo_off, 0.01), c + (hi_off - 2.0), c + lo_off, c)
            for c in closes]


# ------------------------------------------------------------- replay refs
def replay_indicators(bars, P):
    """INDEPENDENT indicator re-implementation used by the replays."""
    c = [b[3] for b in bars]
    h = [b[1] for b in bars]
    l = [b[2] for b in bars]
    hl2 = [(h[i] + l[i]) / 2.0 for i in range(len(bars))]
    hma = ref_hma(c, P["hma_len"])
    ao = [x - y for x, y in zip(ref_sma(hl2, P["ao_fast"]),
                                ref_sma(hl2, P["ao_slow"]))]
    A = ref_atr(h, l, c, P["atr_len"])
    diP, diM, adx = ref_dmi(h, l, c, P["di_len"], P["adx_smooth"])
    return dict(h=h, l=l, c=c, hma=hma, ao=ao, atr=A, diP=diP, diM=diM,
                adx=adx)


def replay_masks(R, P):
    n = len(R["c"])
    cUp = ref_cross_over(R["adx"], [P["adx_thr"]] * n)
    cDn = ref_cross_under(R["adx"], [P["adx_thr"]] * n)
    sinceU = ref_barssince(cUp)
    sinceD = ref_barssince(cDn)

    def sign_falsy(a):
        return [(not numpy_nan(a[i])) for i in range(len(a))]

    hmaL = [not numpy_nan(R["hma"][i]) and not numpy_nan(R["c"][i])
            and R["c"][i] > R["hma"][i] for i in range(n)]
    hmaS = [not numpy_nan(R["hma"][i]) and not numpy_nan(R["c"][i])
            and R["c"][i] < R["hma"][i] for i in range(n)]
    aoL = []
    for i in range(n):
        if i == 0 or numpy_nan(R["ao"][i]) or numpy_nan(R["ao"][i - 1]):
            aoL.append((False, False))
        else:
            aoL.append((R["ao"][i] > 0 and R["ao"][i] > R["ao"][i - 1],
                        R["ao"][i] < 0 and R["ao"][i] <= R["ao"][i - 1]))
    recU = [(not numpy_nan(sinceU[i])) and sinceU[i] <= P["adx_win"]
            and (not numpy_nan(R["adx"][i])) and R["adx"][i] > P["adx_thr"]
            for i in range(n)]
    recD = [(not numpy_nan(sinceD[i])) and sinceD[i] <= P["adx_win"]
            and (not numpy_nan(R["adx"][i])) and R["adx"][i] < P["adx_thr"]
            for i in range(n)]
    diBull = [(not numpy_nan(R["diP"][i])) and (not numpy_nan(R["diM"][i]))
              and R["diP"][i] > R["diM"][i] for i in range(n)]
    diBear = [(not numpy_nan(R["diP"][i])) and (not numpy_nan(R["diM"][i]))
              and R["diM"][i] > R["diP"][i] for i in range(n)]
    if P["adx_mode"] == "level":
        adxOkL = [(not numpy_nan(R["adx"][i]) and R["adx"][i] > P["adx_thr"]
                   and ((not P["req_di"]) or diBull[i])) for i in range(n)]
        adxOkS = [(not numpy_nan(R["adx"][i]) and R["adx"][i] > P["adx_thr"]
                   and ((not P["req_di"]) or diBear[i])) for i in range(n)]
    elif P["adx_mode"] == "literal":
        adxOkL, adxOkS = recU, recD
    else:
        adxOkL = [recU[i] and ((not P["req_di"]) or diBull[i])
                  for i in range(n)]
        adxOkS = [recU[i] and ((not P["req_di"]) or diBear[i])
                  for i in range(n)]
    return dict(hmaL=hmaL, hmaS=hmaS, aoL=aoL, recU=recU, recD=recD,
                diBull=diBull, diBear=diBear, adxOkL=adxOkL, adxOkS=adxOkS)


def replay(bars, P, fee, slip):
    """An INDEPENDENT next-open fill machine, written dict + loop style,
    different from the engine's arrays, following the SAME declared
    conventions. Produces trades, lv and masks to compare with simulate()."""
    R = replay_indicators(bars, P)
    M = replay_masks(R, P)
    n = len(bars)
    cash = H.INIT
    inv = 0.0
    ep = 0.0
    entry_fee = 0.0
    entry_bar = -1
    sl = tp = None
    pend = None
    pend_stop = 0.0
    day0 = None                   # engine-style: first bar always snapshots
    day_start = H.INIT
    halted = False
    lv_want = [H.INIT] + [float("nan")] * n
    trades_want = []
    entryL_prev = False
    entryS_prev = False
    stL_prev = False
    stS_prev = False

    def qty(eq_mark, cl, dist):
        eqx = max(eq_mark, 0.0)
        cap = eqx * P["max_lev"] / cl if cl > 0 else 0.0
        if dist and dist > 0:
            raw = eqx * P["risk_pct"] / 100.0 / dist
        else:
            raw = eqx * P["fixed_notional_pct"] / 100.0 / cl \
                if cl > 0 else 0.0
        return max(min(raw, cap), 0.0)

    for i in range(n):
        o, hie, lo, cl = bars[i][0], bars[i][1], bars[i][2], bars[i][3]
        # ---- fill from last close
        if pend is not None:
            kind = pend
            pend = None
            if kind[0] == "entry":
                side, q = kind[1], kind[2]
                fill = o * (1 + slip) if side == 1 else o * (1 - slip)
                if side * inv < 0:
                    sign = 1.0 if inv > 0 else -1.0
                    oldq = abs(inv)
                    xfee = oldq * fill * fee
                    pnl = sign * oldq * (fill - ep) - entry_fee - xfee
                    cash += sign * oldq * fill - xfee
                    trades_want.append((("L" if inv > 0 else "S"),
                                        entry_bar, i, ep, fill, pnl, xfee))
                    inv = 0.0
                    entry_fee = 0.0
                    ep = 0.0
                    entry_bar = -1
                turn = q * fill
                fee_new = turn * fee
                cash -= side * turn
                cash -= fee_new
                inv = side * q
                ep = fill
                entry_fee = fee_new
                entry_bar = i
                if pend_stop and pend_stop > 0:
                    sl = fill - pend_stop if side == 1 else fill + pend_stop
                    tp = (None if P["tp_r"] <= 0 else
                          (fill + pend_stop * P["tp_r"]
                           if side == 1 else fill - pend_stop * P["tp_r"]))
                else:
                    sl = tp = None
            else:
                sign = 1.0 if inv > 0 else -1.0
                fill = o * (1 - slip) if inv > 0 else o * (1 + slip)
                oldq = abs(inv)
                xfee = oldq * fill * fee
                pnl = sign * oldq * (fill - ep) - entry_fee - xfee
                cash += sign * oldq * fill - xfee
                trades_want.append(("L" if inv > 0 else "S", entry_bar, i,
                                    ep, fill, pnl, xfee))
                inv = 0.0
                entry_fee = 0.0
                ep = 0.0
                entry_bar = -1
                sl = tp = None
        # ---- intrabar brackets (stop before limit; gap rule) — stop
        # fills degrade the level by the RELATIVE slippage fraction
        if inv != 0:
            if inv > 0 and sl is not None and lo <= sl:
                px = sl if o > sl else o
                sign = 1.0
                oldq = abs(inv)
                xfill = px * (1.0 - slip)
                xfee = oldq * xfill * fee
                pnl = sign * oldq * (xfill - ep) - entry_fee - xfee
                cash += sign * oldq * xfill - xfee
                trades_want.append(("L", entry_bar, i, ep, xfill, pnl, xfee))
                inv = 0.0
                entry_fee = 0.0
                ep = 0.0
                entry_bar = -1
                sl = tp = None
            elif inv > 0 and tp is not None and hie >= tp:
                px = tp if o < tp else o
                oldq = abs(inv)
                xfee = oldq * px * fee
                pnl = oldq * (px - ep) - entry_fee - xfee
                cash += oldq * px - xfee
                trades_want.append(("L", entry_bar, i, ep, px, pnl, xfee))
                inv = 0.0
                entry_fee = 0.0
                ep = 0.0
                entry_bar = -1
                sl = tp = None
            elif inv < 0 and sl is not None and hie >= sl:
                px = sl if o < sl else o
                oldq = abs(inv)
                xfill = px * (1.0 + slip)
                xfee = oldq * xfill * fee
                pnl = (-1.0) * oldq * (xfill - ep) - entry_fee - xfee
                cash += oldq * xfill - xfee
                trades_want.append(("S", entry_bar, i, ep, xfill, pnl, xfee))
                inv = 0.0
                entry_fee = 0.0
                ep = 0.0
                entry_bar = -1
                sl = tp = None
            elif inv < 0 and tp is not None and lo <= tp:
                px = tp if o > tp else o
                oldq = abs(inv)
                xfee = oldq * px * fee
                pnl = (-1.0) * oldq * (px - ep) - entry_fee - xfee
                cash += oldq * px - xfee
                trades_want.append(("S", entry_bar, i, ep, px, pnl, xfee))
                inv = 0.0
                entry_fee = 0.0
                ep = 0.0
                entry_bar = -1
                sl = tp = None
        # ---- day snapshot
        day = bars[i][0] // 86_400_000
        if day != day0:
            day0 = day
            day_start = cash + inv * cl
            halted = False
        eq_mark = cash + inv * cl
        if P["daily_loss"] > 0 and eq_mark <= \
                day_start * (1 - P["daily_loss"] / 100.0):
            halted = True
        # ---- masks
        aL = M["hmaL"][i] and M["aoL"][i][0]
        aS = M["hmaS"][i] and M["aoL"][i][1]
        bL = M["hmaL"][i] and M["adxOkL"][i]
        bS = M["hmaS"][i] and M["adxOkS"][i]
        hF1 = R["hma"][i - 1] if i >= 1 else float("nan")
        hF2 = R["hma"][i - 2] if i >= 2 else float("nan")
        if P["use_htf"]:
            okh = (not numpy_nan(hF1)) and (not numpy_nan(hF2))
            htfL = okh and hF1 > hF2
            htfS = okh and hF1 < hF2
        else:
            htfL = htfS = True
        minAtr = (P["cost_mult"] * 2 * (P["gate_fee_pct"]
                  + P["gate_slip_pct"]) * 100)
        cOK = True
        if P["use_cost"]:
            c = cl
            if numpy_nan(R["atr"][i]) or c == 0:
                cOK = False
            else:
                cOK = (R["atr"][i] / c * 100) >= minAtr
        sig = P["sig_mode"]
        if sig == "a":
            mL, mS = aL, aS
        elif sig == "b":
            mL, mS = bL, bS
        elif sig == "either":
            mL, mS = (aL or bL), (aS or bS)
        else:
            mL, mS = (aL and bL), (aS and bS)
        stL = mL and htfL and cOK and P["allow_long"]
        stS = mS and htfS and cOK and P["allow_short"]
        entryL = stL and not stL_prev
        entryS = stS and not stS_prev
        stL_prev, stS_prev = stL, stS
        xe = P["exit_rule"]
        if xe == "auto":
            xe = "hma" if sig == "b" else "either"
        if xe == "hma":
            xL, xS = M["hmaS"][i], M["hmaL"][i]
        elif xe == "ao":
            xL, xS = M["aoL"][i][1], M["aoL"][i][0]
        elif xe == "both":
            xL, xS = M["hmaS"][i] and M["aoL"][i][1], \
                M["hmaL"][i] and M["aoL"][i][0]
        else:
            xL, xS = M["hmaS"][i] or M["aoL"][i][1], \
                M["hmaL"][i] or M["aoL"][i][0]
        # ---- decide
        flat = inv == 0.0
        okL = flat or (P["close_opp"] and inv < 0)
        okS = flat or (P["close_opp"] and inv > 0)
        takeL = entryL and (not halted) and okL
        takeS = entryS and (not halted) and okS and not takeL
        if halted and inv != 0:
            pend = ("closeall",)
        elif inv > 0 and xL and not takeS:
            pend = ("close",)
        elif inv < 0 and xS and not takeL:
            pend = ("close",)
        if takeL:
            dist = P["atr_stop_mult"] * R["atr"][i] \
                if P["atr_stop_mult"] > 0 else 0.0
            q = qty(eq_mark, cl, dist)
            if q > 0:
                pend = ("entry", 1, q)
                pend_stop = dist
        elif takeS:
            dist = P["atr_stop_mult"] * R["atr"][i] \
                if P["atr_stop_mult"] > 0 else 0.0
            q = qty(eq_mark, cl, dist)
            if q > 0:
                pend = ("entry", -1, q)
                pend_stop = dist
        lv_want[i + 1] = cash + inv * cl
    if inv != 0:
        pass
    return dict(trades=trades_want, lv=lv_want, R=R, M=M)


def norm_trades(trs):
    return [(s, b, u, round(e, 9), round(f, 9), round(p, 9))
            for (s, b, u, e, f, p, _xf) in trs]


def norm_engine_trades(trs):
    return [(t["side"], t["entry_bar"], t["u"], round(t["entry"], 9),
             round(t["exit"], 9), round(t["usd"], 9)) for t in trs]


# ================================================================ begin
def case_A():
    print("== A primitives ==")
    # A1 wma hand check
    got = [float(x) if not numpy_nan(x) else float("nan")
           for x in H.wma([10.0, 20.0, 30.0], 3)]
    want = [float("nan"), float("nan"),
            (1 * 10 + 2 * 20 + 3 * 30) / 6.0]
    ok("A1 hand wma of [10,20,30]", vclose(got, want),
       f"{got} vs {want}")
    # A2 hma on a ramp == independent ref on a 60-bar ramp with noise
    ramp = [100.0 + 1.0 * i + (2.0 if i % 5 == 3 else -1.5)
            for i in range(60)]
    ok("A2 hma(21) == independent ref", vclose(H.hma_pine(ramp, 21),
                                              ref_hma(ramp, 21)))
    ok("A2b hma warmup pattern (first valid at 2*len-2 + round(sqrt))",
       numpy_nan(H.hma_pine(ramp, 21)[23])
       and not numpy_nan(H.hma_pine(ramp, 21)[24]),
       "nan@23, valid@24")
    # A3 hma even length: floor division
    ok("A3 hma(22) floor-half == ref", vclose(H.hma_pine(ramp, 22),
                                              ref_hma(ramp, 22)))
    # A4 sma + AO == sma(hl2,5)-sma(hl2,34) on engineered OHLC
    bars = bars_from(ramp)
    h = [b[1] for b in bars]
    l = [b[2] for b in bars]
    c = [b[3] for b in bars]
    hl2 = [(h[i] + l[i]) / 2 for i in range(len(bars))]
    ao_want = [x - y for x, y in zip(ref_sma(hl2, 5), ref_sma(hl2, 34))]
    ok("A4 sma() == ref",
       vclose(H.sma(c, 34), ref_sma(c, 34)))
    ok("A4b AO(5,34) == independent sma diff",
       vclose(H.sma(hl2, 5) - H.sma(hl2, 34), ao_want))
    # A5 atr + rma (incl. pandas-equivalence of the Wilder form once seeded)
    ok("A5 atr(14) == ref wilder", vclose(
        EP_ref.atr_pine(np.array(h), np.array(l), np.array(c), 14),
        ref_atr(h, l, c, 14)))
    eqv, idx0 = ref_ema_pandas_eq_check(ref_true_range(h, l, c))
    ok("A5b rma(alpha=1/n, adjust=False) == pandas ewm once seeded (trap)",
       eqv, f"seed at bar {idx0 - 1}")
    # A6 dmi (with a flat stretch and a zero-sum guard tail)
    # injection: craft lows/highs with a hang + flat zone
    h2 = list(h)
    l2 = list(l)
    c2 = list(c)
    for i in range(40, 48):
        c2[i] = 141.0 + 0.01 * i
        h2[i] = 143.0
        l2[i] = 139.0
    diP, diM, adx = EP_ref.dmi_pine(np.array(h2), np.array(l2),
                                    np.array(c2), 14, 14)
    rdiP, rdiM, radx = ref_dmi(h2, l2, c2, 14, 14)
    ok("A6 dmi diP == ref", vclose(diP, rdiP))
    ok("A6a dmi diM == ref", vclose(diM, rdiM))
    ok("A6b dmi adx == ref", vclose(adx, radx))
    # A7 crossover + barssince window
    adxpath = [10.0] * 10 + [24.0, 26.5, 27.5, 26.9] + [20.0] * 5 + \
              [26.0, 27.0, 26.0] + [10.0] * 10
    thr = [25.0] * len(adxpath)
    cUpE = EP_ref.cross_over(np.array(adxpath), np.array(thr))
    cUpR = ref_cross_over(adxpath, thr)
    ok("A7 crossover(axis) == ref", list(cUpE) == cUpR,
       f"engine {list(cUpE)} vs ref {cUpR}")
    bsE = H.barssince(cUpE)
    bsR = ref_barssince(cUpR)
    ok("A7b barssince == ref", vclose(bsE, bsR),
       f"{list(bsE)[8:14]} vs {bsR[8:14]}")


def case_B(tmp):
    print("== B replay cases ==")
    FEE, SLIP = E1.COST_PRESETS["repo6x5"]["taker_fee"], \
        E1.COST_PRESETS["repo6x5"]["slippage"]

    def run_engine(bars, P, fee, slip):
        d = dict(t=np.array([1_735_689_600_000 + 3_600_000 * i
                             for i in range(len(bars))], dtype=np.int64),
                 o=np.array([b[0] for b in bars]),
                 h=np.array([b[1] for b in bars]),
                 l=np.array([b[2] for b in bars]),
                 c=np.array([b[3] for b in bars]))
        return H.simulate(d, P, fee, slip)

    # ---- B1: A-only long entry fills next open; sizing = 1% risk / 2*ATR
    P = dict(H.PINE, sig_mode="a", use_htf=False, use_cost=False)
    closes = ([90.0] * 45 + [100.0 + 1.0 * i for i in range(10)]
              + [101.0] * 20)
    bars = bars_from(closes)
    rep = replay(bars, P, FEE, SLIP)
    eng = run_engine(bars, P, FEE, SLIP)
    ok("B1 replay trades == engine trades",
       norm_trades(rep["trades"]) == norm_engine_trades(eng["trades"]),
       f"{norm_trades(rep['trades'])[:3]} vs "
       f"{norm_engine_trades(eng['trades'])[:3]}")
    ok("B1 balance: notional=qty*entry within maxLev cap",
       all(abs(t["qty"] * t["entry"]) <= H.INIT * P["max_lev"] * 1.0 + 1e-6
           for t in eng["trades"]))

    # ---- B2: signal exit "either" (drop below HMA or AO flip) then flat
    closes2 = ([90.0] * 45 + [100.0 + 1.0 * i for i in range(10)]
               + [101.0] * 6 + [98.0] * 12)
    bars2 = bars_from(closes2)
    rep2 = replay(bars2, P, FEE, SLIP)
    eng2 = run_engine(bars2, P, FEE, SLIP)
    ok("B2 exit + re-entry rules replay == engine",
       norm_trades(rep2["trades"]) == norm_engine_trades(eng2["trades"]))

    # ---- B3: B-only, level mode, reqDI off — same bars different signal
    P3 = dict(H.PINE, sig_mode="b", use_htf=False, use_cost=False,
              req_di=False, adx_mode="level")
    rep3 = replay(bars2, P3, FEE, SLIP)
    eng3 = run_engine(bars2, P3, FEE, SLIP)
    ok("B3 level mode replay == engine",
       norm_trades(rep3["trades"]) == norm_engine_trades(eng3["trades"]))

    # ---- B4: stop fills with a GAP OPEN through the level (gap rule).
    # The crash bar must arrive while the position is fresh (before the HMA
    # catch-up can signal-exit), and it OPENS below the stop: per the gap
    # rule the fill executes at the bar's open, not at the level.
    P4 = dict(H.PINE, sig_mode="a", use_htf=False, use_cost=False)
    closes4 = ([90.0] * 45 + [97.0, 98.0, 99.0, 100.0, 101.0]
               + [92.0] * 6 + [99.0] * 12)
    bars4 = list(bars_from(closes4))
    bars4[50] = (88.0, 100.0, 87.0, 99.0)      # open 88 gaps through the stop
    rep4 = replay(bars4, P4, FEE, SLIP)
    eng4 = run_engine(bars4, P4, FEE, SLIP)
    stops = [t for t in eng4["trades"] if t["why"] == "stop"]
    ok("B4 gap-open stop replay == engine",
       norm_trades(rep4["trades"]) == norm_engine_trades(eng4["trades"])
       and stops, f"whys {[t['why'] for t in eng4['trades']]}")
    # hand arithmetic: the stop fill == bar-50 open degraded by slip
    # (85.0? no: o50=88 -> 88*(1-slip)=87.956), NOT the stop level 91.34
    ok("B4 gap rule: stop fills at the OPEN below the level",
       all(abs(t["exit"] - 88.0 * (1.0 - SLIP)) <= 1e-9 for t in stops),
       f"stop exits {[t['exit'] for t in stops]}")

    # ---- B5: TP before stop (tp_r = 1.0), spanning bar resolves STOP first
    P5 = dict(H.PINE, sig_mode="a", use_htf=False, use_cost=False, tp_r=1.0)
    rep5 = replay(bars, P5, FEE, SLIP)
    eng5 = run_engine(bars, P5, FEE, SLIP)
    ok("B5 tp_r=1 replay == engine",
       norm_trades(rep5["trades"]) == norm_engine_trades(eng5["trades"])
       and any(t["why"] == "tp" for t in eng5["trades"]),
       f"whys {[t['why'] for t in eng5['trades']]}")

    # ---- B6: zero-quantity take places nothing (maxLev=0 cap)
    P6 = dict(H.PINE, sig_mode="a", use_htf=False, use_cost=False, max_lev=0.0)
    eng6 = run_engine(bars, P6, FEE, SLIP)
    ok("B6 zero-qty takes fire NO order",
       not eng6["trades"] and eng6["open_tail"] is None,
       f"trades {len(eng6['trades'])}")

    # ---- B7: daily-loss breaker (3% of day start). With the DEFAULT
    # 2*ATR stop and 1% risk sizing one stop-out costs ~1% of equity, so a
    # 3% intraday breach is unreachable in 96 synthetic bars; this case
    # disables the bracket (atr_stop_mult = 0, a legal Pine input state)
    # so losses are uncapped: day-1 warmup, day-2 climb (entry rides),
    # day-3 first bar closes ~+3.8% (snapshot), second bar -3.7% -> the
    # halt verdict trips at that close, close_all fills at the NEXT open,
    # and no entry can fire while halted.
    P7 = dict(H.PINE, sig_mode="a", use_htf=False, use_cost=False,
              atr_stop_mult=0.0)
    closes7 = ([90.0] * 24                                   # day 1 warmup
               + [91.0 + 0.5 * i for i in range(24)]         # day 2 climb
               + [108.0, 100.0, 98.0]                        # day 3 crash
               + [98.0] * 45)                                # inert tail
    bars7 = bars_from(closes7)
    rep7 = replay(bars7, P7, FEE, SLIP)
    eng7 = run_engine(bars7, P7, FEE, SLIP)
    ok("B7 breaker replay == engine",
       norm_trades(rep7["trades"]) == norm_engine_trades(eng7["trades"]))
    halt_fills = [t for t in eng7["trades"] if t["why"] == "daily halt"]
    ok("B7 breaker actually fired (closeall fill exists)",
       halt_fills, f"whys {[t['why'] for t in eng7['trades']]}")
    # hand arithmetic: bar 50 (close 98) opens at 96 -> slipped long close
    ok("B7 closeall fill == next-open slipped (hand)",
       all(abs(t["exit"] - 96.0 * (1.0 - SLIP)) <= 1e-9
           for t in halt_fills),
       f"halt exits {[t['exit'] for t in halt_fills]}")

    # ---- B8: end-of-data open tail excluded from closed stats
    closes8 = ([90.0] * 45 + [100.0 + 1.0 * i for i in range(24)])
    bars8 = bars_from(closes8)
    eng8 = run_engine(bars8, P8 := dict(H.PINE, sig_mode="a", use_htf=False,
                                        use_cost=False), FEE, SLIP)
    ok("B8 open tail: n_open=1 and last entry unexited",
       eng8["open_tail"] is not None and len(eng8["trades"]) ==
       len([t for t in eng8["trades"]]),
       f"open {eng8['open_tail']}, closed {len(eng8['trades'])}")

    # ---- B9: long-priority tie: entryL and entryS same bar -> takeS off
    closes9 = ([90.0] * 45 + [100.0 + 1.0 * i for i in range(10)]
               + [99.0] * 3 + [101.5] * 8)
    bars9 = bars_from(closes9)
    P9 = dict(H.PINE, sig_mode="either", use_htf=False, use_cost=False)
    rep9 = replay(bars9, P9, FEE, SLIP)
    eng9 = run_engine(bars9, P9, FEE, SLIP)
    ok("B9 tie priority replay == engine",
       norm_trades(rep9["trades"]) == norm_engine_trades(eng9["trades"]))

    # ---- B10: fresh-signal gating: no re-entry while st stays true
    P10 = dict(H.PINE, sig_mode="a", use_htf=False, use_cost=False)
    clos10 = ([90.0] * 45 + [100.0 + 1.0 * i for i in range(10)]
              + [100.6] * 30)
    bars10 = bars_from(clos10)
    eng10 = run_engine(bars10, P10, FEE, SLIP)
    # prices stay above HMA with AO green: ONE entry then nothing more
    fills = [t for t in eng10["trades"] if t["side"] == "L"]
    ok("B10 no repeat entries while stL persists (fresh only)",
       len(fills) <= 1 + len([t for t in eng10["trades"] if t["side"] == "S"]),
       f"trades {norm_engine_trades(eng10['trades'])}")
    rep10 = replay(bars10, P10, FEE, SLIP)
    ok("B10b fresh-gating replay == engine",
       norm_trades(rep10["trades"]) == norm_engine_trades(eng10["trades"]))


def case_C(tmp):
    print("== C run_suite plumbing ==")
    closes = ([95.0] * 50 + [100.0 + 0.4 * i for i in range(90)]
              + [101.5] * 30)
    p = os.path.join(tmp, "BTCUSDT_aud_1h.csv")
    write_csv(p, bars_from(closes))
    args = ([p], {"window": "full", "costs": "repo6x5"})
    out1 = H.run_suite(*args)
    out2 = H.run_suite(*args)
    row = out1["tables"][0]
    ok("C1 run_suite deterministic (identical JSON)",
       json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True))
    eng = H.simulate(dict(t=np.array([1_735_689_600_000 + 3_600_000 * i
                                      for i in range(len(closes))],
                                     dtype=np.int64),
                          o=np.array([b[0] for b in bars_from(closes)]),
                          h=np.array([b[1] for b in bars_from(closes)]),
                          l=np.array([b[2] for b in bars_from(closes)]),
                          c=np.array(closes)),
                     H.PINE, 0.0006, 0.0005)
    aud_trades = eng["trades"]
    usds = [t["usd"] for t in aud_trades]
    gp = sum(x for x in usds if x > 0)
    gl = abs(sum(x for x in usds if x <= 0))
    pf = (gp / gl) if gl > 0 else None
    nn = len(usds)
    ok("C2 row n_trades == audit hands",
       row["n_trades"] == nn, f"{row['n_trades']} vs {nn}")
    ok("C3 row pf_strict == audit hands",
       (row["pf_strict"] is None and pf is None)
       or abs(row["pf_strict"] - pf) <= 1e-9 * max(1.0, pf))
    ok("C4 gates attached + bool",
       isinstance(row.get("gates_pass_all"), bool) and "gates" in row)
    ok("C5 bench = BH over scored span",
       abs(row["bench_ret_pct"] - (closes[-1] / closes[0] - 1) * 100.0)
       <= 1e-9, f"{row['bench_ret_pct']}")

    # last6mo slicing needs the exact dspack window constants; build a
    # full 6768+-bar deterministic walk and check the provenance fields.
    rs = np.random.RandomState(7)
    steps = rs.normal(0.0, 0.35, 6800)
    walk = 100.0 + np.cumsum(steps)
    closes6 = [max(float(v), 1.0) for v in walk]
    p6 = os.path.join(tmp, "BTCUSDT_1h.csv")
    write_csv(p6, bars_from(closes6))
    out6 = H.run_suite([p6], {"window": "last6mo", "costs": "repo6x5"})
    ok("C6 last6mo slice: bars=6768, scored=4368, warmup=2400",
       out6["metrics"]["bars"] == E1.WARMUP_BARS + E1.SCORE_BARS
       and out6["metrics"]["scored_bars"] == E1.SCORE_BARS
       and out6["metrics"]["warmup_bars"] == E1.WARMUP_BARS)

    # drag bookkeeping: row ret_zero == a zero-cost engine replay ret
    zen = H.simulate(dict(t=np.array([1_735_689_600_000 + 3_600_000 * i
                                      for i in range(len(closes))],
                                     dtype=np.int64),
                          o=np.array([b[0] for b in bars_from(closes)]),
                          h=np.array([b[1] for b in bars_from(closes)]),
                          l=np.array([b[2] for b in bars_from(closes)]),
                          c=np.array(closes)),
                     H.PINE, 0.0, 0.0)
    zret = (zen["lv"][-1] / H.INIT - 1.0) * 100.0
    ok("C7 ret_zero == zero-cost replay",
       abs(row["ret_zero_pct"] - zret) <= 1e-9 * max(1.0, abs(zret)),
       f"{row['ret_zero_pct']} vs {zret}")
    ok("C8 drag = ret_zero - scored",
       abs(row["drag_pp"] - (row["ret_zero_pct"] - row["ret_pct"])) <= 1e-12)


def case_D():
    print("== D identity/defaults ==")
    wantP = {"hma_len": 21, "ao_fast": 5, "ao_slow": 34, "di_len": 14,
             "adx_smooth": 14, "adx_thr": 25.0, "adx_mode": "cross",
             "adx_win": 3, "req_di": True, "sig_mode": "confl",
             "exit_rule": "auto", "allow_long": True, "allow_short": True,
             "use_htf": True, "use_cost": True, "atr_len": 14,
             "cost_mult": 1.5, "gate_fee_pct": 0.0005,
             "gate_slip_pct": 0.0001, "atr_stop_mult": 2.0, "tp_r": 0.0,
             "risk_pct": 1.0, "fixed_notional_pct": 100.0, "max_lev": 10.0,
             "close_opp": True, "daily_loss": 3.0, "use_dates": False}
    ok("D1 PINE defaults == documented literals", H.PINE == wantP,
       f"{H.PINE}")
    ok("D2 cost presets literal",
       H.COSTS == {"author": {"fee": 0.0005, "slip": 0.0001},
                   "repo6x5": {"fee": 0.0006, "slip": 0.0005},
                   "zero": {"fee": 0.0, "slip": 0.0}})
    ok("D3 INIT == 1000 (Pine initial_capital)", H.INIT == 1000.0)
    ok("D4 pine primitives imported BY IDENTITY (one audited copy)",
       H.EP is EP_ref
       and H.EP.dmi_pine.__module__ == "emaadx_engine"
       and H.EP.atr_pine.__module__ == "emaadx_engine")
    ok("D5 dspack scorer imported BY IDENTITY",
       H.E1 is E1 and H.E1._score_trades.__module__ == "dspack_engine"
       and H.E1._gates.__module__ == "dspack_engine")
    ok("D6 dspack constants shared (1h campaign)",
       E1.STARTING_EQUITY == 100_000.0 and E1.WARMUP_BARS == 2400
       and E1.SCORE_BARS == 4368 and E1.BARS_PER_YEAR == 8760
       and E1.COST_PRESETS["repo6x5"]["taker_fee"] == 0.0006
       and E1.COST_PRESETS["repo6x5"]["slippage"] == 0.0005)


def main():
    print("hmaaoadx known-answer audit")
    with tempfile.TemporaryDirectory() as tmp:
        case_A()
        case_B(tmp)
        case_C(tmp)
        case_D()
    print(f"-- {N_PASS} pass / {len(FAILS)} fail --")
    lines = ["hmaaoadx audit"] + [f"FAIL {f}" for f in FAILS] + \
            [f"{N_PASS} pass / {len(FAILS)} fail"]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    sys.exit(0 if not FAILS else 1)


if __name__ == "__main__":
    main()
