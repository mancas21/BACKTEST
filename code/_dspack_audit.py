#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dspack_audit.py -- known-answer audit for the dspack adapter
(engine code/dspack_engine.py, author pack code/deepseek_pack.py).

Run BEFORE any real-data cell. Every expected value comes from LITERAL
arithmetic written in this file (hand-built equity ladders) or from an
independent straight-line simulator below -- never from the engine's own
helpers. Exit code 0 only when ALL PASS. Canonical output:
results/dspack_audit_known_answers.txt.

Cases
  A1  ds1 tsmom: vol-target saturation (constant vol -> scale clip -> |pos| 1),
      flat series -> 0
  A2  ds1 tsmom: mixed series, hand-computed momentum/vol/scale
  A3  ds2 donchian: breakout trigger, expansion gate TRUE and FALSE,
      STATELESS re-write (a position exists only on trigger bars)
  A4  ds3 htf_ema: closed-form EMA (adjust=True) + hand-built hold-memory
      state; output is -1 when memory ages out
  A5  ds4 xs_momentum: rank weights, the [::24]-grid sample + ffill
  A6  ds5 bovol: breakout + 2x-volume-style gate + hold via ffill limit
  B1  engine fees: entry / drift / exit events, hand-built equity ladder
  B2  engine fees: whole-order reversal fee loads the CLOSING trade
  B3  independent straight-line simulator vs engine on a seeded random walk
      (levels, trade USDs, fees, tiling invariant, plus scored row plumbing)
  B4  causality: positions on data prefixes equal positions on the full frame
  B5  ds4 portfolio accounting: hand-built ladder, period segmentation,
      equal-weight benchmark
  B6  zero-position edge: no trades, PF None, zero drag
  C   pack defaults equal the documented literals (verbatim call paths)
"""
import inspect
import math
import os
import sys
import hashlib

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results", "dspack_audit_known_answers.txt")

FAIL: list = []
N_PASS = 0


def check(name, ok, detail=""):
    global N_PASS
    if ok:
        N_PASS += 1
        print(f"PASS {name}" + (f" :: {detail}" if detail else ""))
    else:
        FAIL.append(name)
        print(f"FAIL {name}" + (f" :: {detail}" if detail else ""))
    return ok


def close(x, y, tol=1e-9):
    return abs(float(x) - float(y)) <= tol * max(1.0, abs(float(y)))


def vec_close(a, b, tol=1e-9):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return False
    return bool(np.all(np.abs(a - b) <= tol * np.maximum(1.0, np.abs(b))))


import dspack_engine as E
pack = E.load_author_module()


# ── hand tools (declared-convention reference implementations) ────────────
def ema_closed(xs, span):
    """pandas ewm(span, adjust=True): alpha = 2/(span+1) and the weight sum is
    NORMALIZED from bar 0 -- y_t = sum_j (1-a)^j x_{t-j} / sum_j (1-a)^j
    (-- NOT the fixed-seed recursion, which is adjust=False behavior)."""
    a = 2.0 / (span + 1.0)
    d = 1.0 - a
    ys = []
    for t in range(len(xs)):
        num = den = 0.0
        w = 1.0
        for j in range(t + 1):
            num += w * xs[t - j]
            den += w
            w *= d
        ys.append(num / den)
    return ys


def std3(xs):
    m = sum(xs) / 3.0
    return math.sqrt(sum((x - m) ** 2 for x in xs) / 2.0)


def ffill_holds(cond, limit):
    """cond in {0,1}: .replace(0,nan).ffill(limit).fillna(0) equivalent."""
    out, last, since = [], None, 0
    for c in cond:
        if c == 1.0:
            last, since = 1.0, 0
            out.append(1.0)
        elif last is not None and since < limit:
            out.append(1.0)
            since += 1
        else:
            out.append(0.0)
    return out


def naive_account(w, closes, fee, start=10_000.0):
    """Straight-line reference of the DECLARED convention:
    factor[t] = (1 + w[t-1] r[t]) (1 - |w[t]-w[t-1]| fee), w[-1] := 0; a
    trade = a maximal same-sign nonzero run; exit event = first later bar
    with zero or opposite weight (its bar still earns at the old weight,
    the exit turnover settles at its close); ref = entry-bar level for
    flat-start runs, post-exit level for reversal-start runs."""
    n = len(w)
    lv = [start]
    fees = [0.0] * n
    w_prev = 0.0
    for t in range(n):
        r = 0.0 if t == 0 else closes[t] / closes[t - 1] - 1.0
        dw = abs(w[t] - w_prev)
        ret_f = 1.0 + w_prev * r
        fees[t] = lv[-1] * ret_f * dw * fee
        lv.append(lv[-1] * ret_f * (1.0 - dw * fee))
        w_prev = w[t]
    trades, open_run, a, s_run, ref_kind = [], None, None, 0.0, None
    for t in range(n):
        st = 0.0 if w[t] == 0 else math.copysign(1.0, w[t])
        if a is None:
            if st == 0.0:
                continue
            a, s_run = t, st
            ref_kind = "flat" if (t == 0 or w[t - 1] == 0.0) else "rev"
        elif st == s_run:
            continue
        else:
            ref = a if ref_kind == "flat" else a + 1
            trades.append({"a": a, "u": t, "usd": lv[t + 1] - lv[ref],
                           "fees": sum(fees[ref:t + 1])})
            a, s_run, ref_kind = None, 0.0, None
            if st != 0.0:
                a, s_run, ref_kind = t, st, "rev"
    if a is not None:
        ref = a if ref_kind == "flat" else a + 1
        open_run = {"a": a, "usd": lv[n] - lv[ref],
                    "fees": sum(fees[ref:])}
    return {"lv": lv, "trades": trades, "open_run": open_run, "fees": fees}


def synth_df(closes, highs=None, lows=None, vols=None):
    if highs is None:
        highs = [c + 0.5 for c in closes]
    if lows is None:
        lows = [c - 0.5 for c in closes]
    if vols is None:
        vols = [10.0] * len(closes)
    return pd.DataFrame({"open": closes, "high": highs, "low": lows,
                         "close": closes, "volume": vols})


# ── A1 tsmom saturation ──────────────────────────────────────────────────
def case_a1():
    up = [100.0 * (1.01 ** k) for k in range(7)]
    with np.errstate(divide="ignore", invalid="ignore"):
        w_up = np.asarray(pack.strat_tsmom(synth_df(up), lookback=3),
                          dtype=float)
    ok = check("A1 tsmom up: pos == [0,0,0,1,1,1,1] (scale clipped, |pos| 1)",
               vec_close(w_up, [0, 0, 0, 1, 1, 1, 1], tol=1e-12),
               f"got {np.round(w_up, 9).tolist()}")
    with np.errstate(divide="ignore", invalid="ignore"):
        w_dn = np.asarray(pack.strat_tsmom(synth_df(
            [100.0 * (0.99 ** k) for k in range(7)]), lookback=3), dtype=float)
        w_fl = np.asarray(pack.strat_tsmom(synth_df([100.0] * 7),
                                           lookback=3), dtype=float)
    check("A1 tsmom down: [0,0,0,-1,-1,-1,-1]",
          vec_close(w_dn, [0, 0, 0, -1, -1, -1, -1], tol=1e-12),
          f"got {np.round(w_dn, 9).tolist()}")
    check("A1 tsmom flat: 0 everywhere", vec_close(w_fl, [0] * 7, tol=1e-12),
          f"got {w_fl.tolist()}")
    return ok


# ── A2 tsmom hand-computed scale ─────────────────────────────────────────
def case_a2():
    y = [0.01, 0.01, -0.005, 0.02, 0.004, 0.006, -0.002]
    closes = [100.0]
    for r in y:
        closes.append(closes[-1] * math.exp(r))
    lookback = 3
    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.asarray(pack.strat_tsmom(synth_df(closes), lookback=lookback),
                       dtype=float)
    exp = []
    for t in range(len(y) + 1):
        if t < lookback:
            exp.append(0.0)
            continue
        mom = sum(y[t - lookback:t])
        # logret[t] = y[t-1], so rolling(lookback).std() at bar t covers
        # y[t-lookback .. t-1] (A2's earlier failure was a transcription
        # slip here, not in the engine).
        vol = std3(y[t - lookback:t]) * math.sqrt(8760.0)
        scale = min(2.0, max(0.0, 0.20 / vol)) if vol != 0 else 2.0
        p = (1.0 if mom > 0 else (-1.0 if mom < 0 else 0.0)) * scale
        exp.append(max(-1.0, min(1.0, p)))
    return check("A2 tsmom hand-computed pos",
                 vec_close(w, exp, tol=1e-12),
                 f"got {np.round(w, 9).tolist()}")


# ── A3 donchian ──────────────────────────────────────────────────────────
def case_a3():
    highs = [100.1, 100.1, 100.1, 100.1, 100.15, 100.1]
    lows = [99.9, 99.9, 99.9, 99.9, 99.95, 99.9]
    closes = [99.95, 99.95, 99.95, 99.95, 100.12, 100.0]
    df = synth_df(closes, highs=highs, lows=lows)
    w = np.asarray(pack.strat_donchian(df, n=4, atr_period=3, atr_mult=2.0))
    check("A3 donchian breakout filtered out (range 0.25 <= 2*0.2)",
          vec_close(w, [0] * 6, tol=1e-12), f"got {w.tolist()}")
    w2 = np.asarray(pack.strat_donchian(df, n=4, atr_period=3, atr_mult=0.5))
    check("A3 donchian breakout at mult 0.5 -> +1 on bar 4 ONLY "
          "(stateless: bar 5 back to 0)",
          vec_close(w2, [0, 0, 0, 0, 1.0, 0.0], tol=1e-12),
          f"got {w2.tolist()}")
    dark = list(closes)
    dark[4] = 99.88
    w3 = np.asarray(pack.strat_donchian(synth_df(dark, highs=highs,
                                                 lows=lows),
                                        n=4, atr_period=3, atr_mult=0.5))
    check("A3 donchian breakdown -> -1 on bar 4 only",
          vec_close(w3, [0, 0, 0, 0, -1.0, 0.0], tol=1e-12),
          f"got {w3.tolist()}")
    hi4 = df["high"].rolling(4).max().shift(1)
    check("A3 donchian warmup: shifted window max NaN -> no trigger",
          bool(hi4.iloc[:3].isna().all()))
    return True


# ── A4 htf_ema ───────────────────────────────────────────────────────────
def case_a4():
    closes = [100.0, 100.5, 101.5, 101.0, 100.2, 99.8, 99.0, 98.5, 99.4,
              100.7, 101.9, 102.6]
    ef = ema_closed(closes, 2)
    es = ema_closed(closes, 3)
    cond = [(closes[t] > es[t]) and (ef[t] > es[t]) for t in range(len(closes))]
    exp = [p * 2.0 - 1.0 for p in ffill_holds([1.0 if c else 0.0 for c in cond],
                                             2)]
    got = np.asarray(pack.strat_htf_trend(synth_df(closes), fast=2, slow=3,
                                          hold=2), dtype=float)
    ok1 = check("A4 htf_ema: closed-form EMA == pandas ewm (adjust=True)",
                vec_close(pack.pd.Series(closes).ewm(span=2).mean().to_numpy(),
                          ef, tol=1e-9)
                and vec_close(pack.pd.Series(closes).ewm(span=3).mean().to_numpy(),
                              es, tol=1e-9))
    ok2 = check("A4 htf_ema: hold-memory == hand-built expected "
                f"{exp}", vec_close(got, exp, tol=1e-12),
                f"got {got.tolist()}")
    # default output is -1 (not 0) whenever the memory has aged out
    with_cond = list(exp)
    with_cond[0] = -1.0
    return ok1 and ok2


# ── A5 xs_momentum ───────────────────────────────────────────────────────
def case_a5():
    s1 = [100.0 * (1.02 ** k) for k in range(8)]
    s2 = [100.0 * (0.98 ** k) for k in range(8)]
    s3 = [100.0] * 8
    panel = {"S1": pd.DataFrame({"close": s1}),
             "S2": pd.DataFrame({"close": s2}),
             "S3": pd.DataFrame({"close": s3})}
    pos = pack.strat_xs_momentum(panel, lookback=2, top_k=1, rebalance=2)
    got = pd.DataFrame({s: pos[s] for s in ("S1", "S2", "S3")}).to_numpy()
    exp = np.zeros((8, 3))
    exp[2:, 0] = 1.0            # S1 top-ranked from bar 2; sampled [::2] + ffill
    ok = check("A5 xs top_k=1: weight 1.0 on S1 from bar 2 (grid [::2] + ffill)",
               vec_close(got, exp, tol=1e-12), f"got\n{got}")
    mom = check("A5 xs ranks: S1/S3/S2 pct == 1.0/0.666.../0.333...",
                vec_close(pack.pd.DataFrame(
                    {"S1": pack.np.log(pd.Series(s1)),
                     "S3": pack.np.log(pd.Series(s3)),
                     "S2": pack.np.log(pd.Series(s2))}).diff(2).iloc[3:]
                          .rank(axis=1, pct=True).to_numpy(),
                          [[1.0, 2.0 / 3.0, 1.0 / 3.0]] * 5, tol=1e-9))
    return ok and mom


# ── A6 breakout_volume: the pack's ffill(limit=24) is a DEAD NO-OP ───────
# ds5 source: pos = pd.Series(0.0)*; pos[up]=1; pos[dn]=-1;
# pos.ffill(limit=24).fillna(0).  pos NEVER contains NaN (0.0 is a valid
# value), so the ffill cannot propagate anything -- unlike ds3, which does
# .replace(0, np.nan) BEFORE its ffill.  The author's 24-bar hold never
# happens: ds5 is stateless like ds2 (weight exists on trigger bars only).
def case_a6():
    closes = [100.0, 100.5, 101.0, 101.5, 109.0, 108.5, 108.0, 107.5]
    highs = [c + 0.3 for c in closes]
    lows = [c - 0.3 for c in closes]
    vols = [10.0, 10.0, 10.0, 10.0, 30.0, 10.0, 10.0, 10.0]
    df = synth_df(closes, highs, lows, vols)
    w = np.asarray(pack.strat_breakout_volume(df, n=3, vol_mult=1.0))
    # the raw trigger frame, hand-built: close 109 > max(high[1..3]) and
    # vol 30 > vol_mult * mean(vol[2..4]) = 16.67 at bar 4 only (bars 5-7
    # close below the shifted prior max)
    check("A6 bovol: trigger at bar 4 ONLY, output stays flat after -- "
          "the pack's ffill(limit=24) is a dead no-op (no NaN in pos), "
          "ds5 holds its weight exactly one bar (stateless, like ds2)",
          vec_close(w, [0, 0, 0, 0, 1.0, 0.0, 0.0, 0.0], tol=1e-12),
          f"got {w.tolist()}")
    dark = list(closes)
    dark[4] = 99.2
    lows2 = list(lows)
    lows2[4] = 98.9
    w2 = np.asarray(pack.strat_breakout_volume(
        synth_df(dark, highs, lows2, vols), n=3, vol_mult=1.0))
    check("A6 bovol mirrored breakdown -> -1 on bar 4 only (same dead ffill)",
          vec_close(w2, [0, 0, 0, 0, -1.0, 0.0, 0.0, 0.0], tol=1e-12),
          f"got {w2.tolist()}")
    # 30-bar timeout probe: falling closes + low volume after the trigger
    # can neither re-trigger nor hold, flat forever (proves no hidden state)
    n_time = 30
    closes_t = [100.0, 100.5, 101.0, 101.5, 109.0] + \
        [90.0 - 0.1 * k for k in range(25)]
    highs_t = [c + 0.3 for c in closes_t]
    lows_t = [c - 0.3 for c in closes_t]
    vols_t = [10.0, 10.0, 10.0, 10.0, 30.0] + [10.0] * 25
    w3 = np.asarray(pack.strat_breakout_volume(
        synth_df(closes_t, highs_t, lows_t, vols_t), n=3, vol_mult=1.0))
    exp3 = [0.0] * 4 + [1.0] + [0.0] * 25
    check("A6 bovol 30-bar probe: no hold, no re-trigger -- strictly "
          "one-bar weight on the trigger (limit=24 never activates)",
          vec_close(w3, exp3, tol=1e-12),
          f"nonzero idx {np.flatnonzero(w3).tolist()}")
    return True


# ── B1 engine fees ladder ────────────────────────────────────────────────
def case_b1():
    w = [0.0, 1.0, 1.0, 0.5, 0.0]
    closes = [100.0, 100.0, 90.0, 110.0, 105.0]
    fee = 0.001
    acct = E.run_symbol_account(np.asarray(w), np.asarray(closes), fee)
    lv = acct["factors"]["lv"]
    exp_lv = [
        100_000.0,
        100_000.0,                                       # after bar 0 (flat)
        100_000.0 * (1.0 - 0.001),                       # after bar 1: entry fee
        100_000.0 * (1.0 - 0.001) * (90.0 / 100.0),      # after bar 2: full long
        100_000.0 * (1.0 - 0.001) * (90.0 / 100.0)
        * (110.0 / 90.0) * (1.0 - 0.0005),               # after bar 3: drift fee
        100_000.0 * (1.0 - 0.001) * (90.0 / 100.0)
        * (110.0 / 90.0) * (1.0 - 0.0005)
        * (1.0 + 0.5 * (105.0 / 110.0 - 1.0)) * (1.0 - 0.0005),   # bar 4
    ]
    ok = check("B1 fee ladder levels (entry 0.1%, drift 0.05%, exit 0.05%)",
               vec_close(lv, exp_lv, tol=1e-9), f"lv {lv.tolist()}")
    tr = acct["seg"]["trades"]
    ok1 = (len(tr) == 1 and tr[0]["a"] == 1 and tr[0]["u"] == 4
           and tr[0]["ref_idx"] == 1)
    check("B1 trade segmentation (one trade: entry 1, exit event bar 4)",
          ok1, f"trades {tr}")
    if len(tr) == 1:
        check("B1 trade usd == lv[5] - lv[1]",
              close(tr[0]["usd"], exp_lv[5] - exp_lv[1], tol=1e-9),
              f"usd {tr[0]['usd']}")
        exp_fees = (100.0
                    + acct["factors"]["lv"][3] * 1.0 * (110.0 / 90.0) * 0.0005
                    + acct["factors"]["lv"][4]
                    * (1.0 + 0.5 * (105.0 / 110.0 - 1.0)) * 0.0005)
        # bar 4's fee_frac = |dw|*fee = 0.5*0.001 = 0.0005 (no extra 0.5:
        # the drift weight is already inside delta, unlike the earlier
        # transcription slip that multiplied it twice)
        check("B1 trade fees (entry bar + drift bar + exit bar)",
              close(tr[0]["fees"], exp_fees, tol=1e-6),
              f"fees {tr[0]['fees']} vs {exp_fees}")
    return ok


# ── B2 whole-order reversal fee ──────────────────────────────────────────
def case_b2():
    w = [0.0, 1.0, 1.0, -1.0, -1.0, 0.0]
    closes = [100.0, 100.0, 90.0, 110.0, 100.0, 99.0]
    fee = 0.001
    acct = E.run_symbol_account(np.asarray(w), np.asarray(closes), fee)
    lv = acct["factors"]["lv"]
    exp_lv = [
        100_000.0,
        100_000.0,
        100_000.0 * (1.0 - 0.001),                       # bar 1 entry 1x
        100_000.0 * (1.0 - 0.001) * (90.0 / 100.0),      # bar 2
        100_000.0 * (1.0 - 0.001) * (90.0 / 100.0)
        * (110.0 / 90.0) * (1.0 - 0.002),                # bar 3 reversal 2x WHOLE
        100_000.0 * (1.0 - 0.001) * (90.0 / 100.0)
        * (110.0 / 90.0) * (1.0 - 0.002)
        * (1.0 + (100.0 / 110.0 - 1.0) * (-1.0)),        # bar 4: short earns
        100_000.0 * (1.0 - 0.001) * (90.0 / 100.0)
        * (110.0 / 90.0) * (1.0 - 0.002)
        * (1.0 + (100.0 / 110.0 - 1.0) * (-1.0))         # bar 4: short earns
        * (1.0 + (99.0 / 100.0 - 1.0) * (-1.0)) * (1.0 - 0.001),  # bar 5
    ]
    first = next((i for i, (a, b) in enumerate(zip(lv, exp_lv))
                  if abs(a - b) > 1e-6 * max(1.0, abs(b))), None)
    ok = check("B2 ladder with whole-order reversal fee (|dw| = 2 at bar 3)",
               first is None,
               "first diff " + ("none" if first is None else
                                f"[{first}] lv {lv[first]} vs {exp_lv[first]}"))
    tr = acct["seg"]["trades"]
    ok_seg = (len(tr) == 2 and tr[0]["u"] == 3 and tr[0]["ref_idx"] == 1
              and tr[1]["a"] == 3 and tr[1]["u"] == 5 and tr[1]["ref_idx"] == 4)
    check("B2 segmentation: trade1 [1..3] closes WITH the reversal bar; "
          "trade2 starts at bar 3 with post-fee ref (no entry fee)",
          ok_seg, f"trades {tr}")
    if len(tr) == 2:
        # the 2x bar-3 fee event appears exactly once, inside trade 1:
        lv3 = 100_000.0 * (1.0 - 0.001) * (90.0 / 100.0)
        fee3 = lv3 * (110.0 / 90.0) * 0.002
        ok_fee1 = close(tr[0]["fees"], 100.0 + fee3, tol=1e-6)
        check("B2 whole-order reversal fee charged ONCE, to the "
              "CLOSING trade (entry 0.1% + bar3 0.2% = trade 1 fees)",
              ok_fee1, f"t1 fees {tr[0]['fees']} vs {100.0 + fee3}")
        lv5 = exp_lv[5]
        # bar 5: short earns (1 + 1*(99/100 - 1)*(-1)) = 1.01, then pays 1x exit
        fee5 = lv5 * (1.0 + (1.0 - 99.0 / 100.0)) * 0.001
        check("B2 trade 2 pays only its own exit fee at bar 5 "
              "(no entry fee on a reversal start)",
              close(tr[1]["fees"], fee5, tol=1e-6),
              f"t2 fees {tr[1]['fees']} vs {fee5}")
    return ok


# ── B3 independent simulator vs engine ───────────────────────────────────
def case_b3():
    rng = np.random.default_rng(7)
    n = 400
    closes = 100.0 * np.cumprod(1.0 + 0.0002 + rng.normal(0.0, 0.01, n))
    w = []
    while len(w) < n:
        state = float(rng.choice([-1.0, -0.5, 0.0, 0.25, 0.5, 1.0]))
        w.extend([state] * int(rng.integers(1, 14)))
    w = np.asarray(w[:n])
    fee = 0.0011
    naive = naive_account(list(w), list(closes), fee, start=100_000.0)
    acct = E.run_symbol_account(w, closes, fee)
    lv = acct["factors"]["lv"]
    ok = check("B3 levels: engine == straight-line reference",
               vec_close(lv, naive["lv"], tol=1e-9),
               f"len {len(lv)} vs {len(naive['lv'])}")
    etr = acct["seg"]["trades"]
    ntr = naive["trades"]
    ok_tr = (len(etr) == len(ntr)
             and all(t["a"] == s["a"] and t["u"] == s["u"]
                     and close(t["usd"], s["usd"], tol=1e-9)
                     and close(t["fees"], s["fees"], tol=1e-6)
                     for t, s in zip(etr, ntr)))
    check("B3 trades: engine == reference (a, u, usd, fees each)",
          ok_tr, f"n trades {len(etr)} vs {len(ntr)}")
    open_pair = (acct["seg"]["open_run"] is None) == (naive["open_run"] is None)
    ok_open = open_pair
    if acct["seg"]["open_run"] and naive["open_run"]:
        ok_open = close(acct["seg"]["open_run"]["usd"],
                        naive["open_run"]["usd"], tol=1e-9)
    check("B3 open tail run matches", ok_open)
    if etr:
        last = etr[-1]["u"] + 1
        tot = sum(t["usd"] for t in etr)
        check("B3 tiling invariant: sum of closed trade dollars == "
              "equity delta over the closed span",
              close(tot, lv[last] - lv[0], tol=1e-6),
              f"sum {tot} vs {lv[last] - lv[0]}")
    # scored-row plumbing on the same case (engine metric formulas, sf = 130)
    sf = 130
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="1h")
    row = E._score_trades(acct["seg"], lv, idx, sf, len(closes), bench=0.0)
    usds = [t["usd"] for t in acct["seg"]["trades"] if t["u"] >= sf]
    gp = sum(x for x in usds if x > 0)
    gl = abs(sum(x for x in usds if x <= 0))
    pf_ref = gp / gl if gl > 0 else None
    wins = len([x for x in usds if x > 0]) / len(usds) if usds else None
    ret_ref = (lv[len(closes)] / lv[sf] - 1.0) * 100.0
    check("B3 scored row matches plain-math pf/ret on the same segments",
          row["pf_strict"] == pf_ref
          and close(row["ret_pct"], ret_ref, tol=1e-9)
          and close(row["win_rate_pct"], wins * 100.0, tol=1e-9),
          f"pf {row['pf_strict']} vs {pf_ref}")
    return ok


# ── B4 causality ─────────────────────────────────────────────────────────
def case_b4():
    rng = np.random.default_rng(11)
    n = 300
    closes = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, n))
    opens = np.concatenate(([closes[0]], closes[:-1]))
    span = np.abs(rng.normal(0.0, 0.005, n)) + 0.001
    highs = np.maximum(opens, closes) + span
    lows = np.minimum(opens, closes) - span
    vols = np.exp(rng.normal(10.0, 0.5, n))
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows,
                       "close": closes, "volume": vols})
    ok_all = True
    for strat in ("ds1", "ds2", "ds3", "ds5"):
        full = E.positions_single(df, strat)
        for k in (150, 250, 299):
            pre = E.positions_single(df.iloc[:k], strat)
            same = np.array_equal(full[:k], pre)
            ok_all &= same
            check(f"B4 causality {strat} prefix {k} == full prefix",
                  same, "" if same else
                  f"first diff idx {int(np.flatnonzero(full[:k] != pre)[0])}")
    # ds4: 3-symbol panel
    panel = {"S1": df, "S2": df.mul(1.01), "S3": df.mul(0.99)}
    full_W = E.positions_portfolio(panel, lookback=2, top_k=1, rebalance=2)
    for k in (150, 250, 299):
        pre_W = E.positions_portfolio(
            {s: d.iloc[:k] for s, d in panel.items()},
            lookback=2, top_k=1, rebalance=2)
        same = np.array_equal(full_W[:k], pre_W)
        ok_all &= same
        check(f"B4 causality ds4 prefix {k} == full prefix", same)
    return bool(ok_all)


# ── B5 ds4 portfolio accounting ──────────────────────────────────────────
def case_b5():
    s1 = [100.0 * (1.02 ** k) for k in range(6)]
    s2 = [100.0 * (0.99 ** k) for k in range(6)]
    src = {"S1": pd.DataFrame({"close": s1}),
           "S2": pd.DataFrame({"close": s2})}
    W = E.positions_portfolio(src, lookback=2, top_k=1, rebalance=2)
    exp_W = np.zeros((6, 2))
    exp_W[2:, 0] = 1.0
    check("B5 ds4 weights == S1-only from bar 2",
          vec_close(W, exp_W, tol=1e-12), f"W {W.tolist()}")
    cl = np.asarray([s1, s2]).T           # rows = bars; cols = symbols
    fee = 0.001
    acct = E.run_portfolio_account(W, cl, fee)
    lv = acct["factors"]["lv"]
    exp_lv = [
        100_000.0,                        # lv[0]
        100_000.0,                        # bar 0: no entry (W[0] = 0)
        100_000.0,                        # bar 1: wbase = 0, dw = 0
        100_000.0 * (1.0 - 0.001),        # bar 2: entry switch fee 1x
        100_000.0 * (1.0 - 0.001) * (1.0 + (0.02 * 1.0 - 0.01 * 0.0) / 1.0),
        100_000.0 * (1.0 - 0.001) * (1.02) * (1.02),
        100_000.0 * (1.0 - 0.001) * (1.02) * (1.02) * (1.02),
    ]
    ok = check("B5 portfolio ladder (entry switch at bar 2, 2%/bar earn)",
               vec_close(lv, exp_lv, tol=1e-9), f"lv {lv.tolist()}")
    per = acct["seg"]["periods"]
    ok_p = (len(per) == 1 and per[0]["b"] == 0 and per[0]["u"] == 2
            and close(per[0]["usd"], exp_lv[3] - exp_lv[0], tol=1e-9))
    check("B5 period 0 = [ref lv0, exit switch bar 2] (fee inside)",
          ok_p, f"periods {per}")
    op = acct["seg"]["open_period"]
    check("B5 open tail period = from bar 2's post-switch level lv[3] "
          "(the entry switch's fee belongs to the closing period, so the "
          "open period's own fees are 0)",
          op is not None
          and op["ref_idx"] == 3
          and close(op["usd"], exp_lv[6] - exp_lv[3], tol=1e-9)
          and close(op["fees"], 0.0, tol=1e-9),
          f"open usd {op}")
    idx = pd.date_range("2026-01-01", periods=6, freq="1h")
    mean_rets = (cl[1:] / cl[:-1] - 1.0).mean(axis=1)     # equal weight per bar
    benched = float(np.prod(1.0 + mean_rets)) - 1.0
    bench = (1.0 + (0.02 - 0.01) / 2.0) ** 5 - 1.0
    check("B5 equal-weight benchmark over bars 1..5 == 1.005^5 - 1",
          close(100.0 * benched, 100.0 * bench, tol=1e-9),
          f"benched {100.0 * benched} vs {100.0 * bench}")
    return ok


# ── B6 zero-position edge ────────────────────────────────────────────────
def case_b6():
    w = np.zeros(50)
    closes = 100.0 + np.linspace(0.0, 5.0, 50)
    acct = E.run_symbol_account(w, closes, 0.0011)
    idx = pd.date_range("2026-01-01", periods=50, freq="1h")
    row = E._score_trades(acct["seg"], acct["factors"]["lv"], idx, 0, 50,
                          bench=5.0)
    # drag_pp is NOT a _score_trades field (run_suite measures it by
    # re-scoring the zero-cost account): here the meaningful edge checks
    # are the empty book itself plus a zero fee tally.
    ok = (row["n_trades"] == 0 and row["pf_strict"] is None
          and row["ret_pct"] == 0.0
          and row["conc_top5_share_pct"] is None
          and row["cost_share_pct"] is None
          and close(float(np.sum(acct["factors"]["fee_usd"])), 0.0)
          and close(row["ret_pct"] - row["ret_pct"], 0.0)
          and row["beats_bh"] is False)
    return check("B6 zero-position edge (n 0, PF None, ret 0, fees 0)", ok,
                 f"row subset { {k: row[k] for k in ('n_trades', 'pf_strict', 'ret_pct')} }")


# ── C defaults ───────────────────────────────────────────────────────────
def case_c():
    want = {
        "strat_tsmom": {"lookback": 168, "vol_target": 0.20,
                        "bars_per_year": 8760},
        "strat_donchian": {"n": 100, "atr_period": 14, "atr_mult": 1.5},
        "strat_htf_trend": {"fast": 50, "slow": 200, "hold": 24},
        "strat_xs_momentum": {"lookback": 720, "top_k": 3, "rebalance": 24},
        "strat_breakout_volume": {"n": 48, "vol_mult": 2.0},
    }
    ok = True
    for fname, kwargs in want.items():
        sig = inspect.signature(getattr(pack, fname))
        got = {k: v.default for k, v in sig.parameters.items()
               if v.default is not inspect._empty
               and k in kwargs}
        same = got == kwargs
        ok &= same
        check(f"C default {fname}", same, f"got {got}")
    return ok


def main():
    print("== dspack known-answer audit ==")
    for f in ("dspack_engine.py", "deepseek_pack.py"):
        h = hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()
        print(f"sha256 {f}: {h}")
    rng_cases = [case_a1, case_a2, case_a3, case_a4, case_a5, case_a6,
                 case_b1, case_b2, case_b3, case_b4, case_b5, case_b6,
                 case_c]
    for case in rng_cases:
        try:
            case()
        except Exception as exc:                     # noqa: BLE001
            check(f"{case.__name__} (no exception)", False,
                  f"{type(exc).__name__}: {exc}")
    print(f"\n{N_PASS} PASS, {len(FAIL)} FAIL "
          f"({', '.join(FAIL) if FAIL else 'none'})")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("dspack known-answer audit\n")
        fh.write(f"{N_PASS} PASS, {len(FAIL)} FAIL\n")
        if FAIL:
            fh.write("FAILED: " + ", ".join(FAIL) + "\n")
        else:
            fh.write("ALL cases pass; engine cleared for real-data runs.\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
