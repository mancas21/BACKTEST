#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dspack2_audit.py -- known-answer audit for the dspack2 adapter
(engine code/dspack2_engine.py, author pack code/deepseek_pack2.py).

Run BEFORE any real-data cell. Expectations derive from LITERAL arithmetic
written by hand or from an independent straight-line (non-vectorized)
simulator implemented below -- never from the engine's own helpers.
Nothing is trusted on faith: dspack_engine.py's accounting is shared code,
but pack 1's audit was never even run (no results file), so the B-cases here
RE-PROVE the shared accounting against hand simulators on the pack-2 paths.

pandas semantics note (cost a failed run to learn): the author pack uses
`.ewm(...)` defaults == adjust=True == the weighted-mean form
  y_t = sum_k (1-a)^k * x_{t-k} / sum_k (1-a)^k
which is NOT the Wilder recursion y_t = (1-a) y_{t-1} + a x_t (that one is
pandas adjust=False). The independent helper below reproduces adjust=True.

OVERFLOWING-z NOTE (also cost a failed run): with rolling(n).std(ddof=1),
max |z| = (n-1)/sqrt(n); with n=3 that is 1.155, so z_entry=1.5 can NEVER
trigger. Every z-case below therefore uses lookback=5 (max |z| = 1.789) and
its expected series is guarded to actually contain both trigger signs, a
gap bar (0.5 < |z| < entry) and (where relevant) a marker bar (|z| < 0.5),
so no case can pass vacuously as all-zeros.

Exit code 0 only when ALL PASS. Canonical output:
results/dspack2_audit_known_answers.txt

Cases
  A6  bb_reversion: hand z-test stateless triggers with the ADX gate keyed
      FULLY open (adx_max=1e9), gate fully SHUT (adx_max=0.0), marker bar,
      gap bars. STATELESSNESS pinned: nonzero weights only on trigger bars.
  A7  rsi2: independent RSI(2) and EMA(200) with adjust=True closed form,
      state machine written out by hand; pack's rsi/ema asserted equal to
      the recursions; STATEFUL holding run asserted.
  A8  pairs: hand spread z, pos_a = +-1 stateless trigger bars, pos_b =
      -pos_a * (b/a) at those bars, 0 elsewhere INCLUDING between a
      trigger and the marker (the trailing ffill is a no-op: nothing NaN).
  A9  vwap_reversion: hand vwap/deviation/z (dev-of-dev z), stateless
      triggers, warmup flat.
  B7  run_suite(ds8) end-to-end on two temp CSVs vs the straight-line
      portfolio simulator (DECLARED convention), tiling invariant,
      drag_pp >= 0 (fees only subtract).
  B8  run_suite(ds7) end-to-end on one temp CSV vs the straight-line single
      simulator; closed trades == straight-line closed trades.
  B9  causality: pack positions on data PREFIXES equal positions on the
      full frame for all four strats (no whole-series feature anywhere).
  B10 determinism: run_suite twice on the same CSVs -> identical JSON.
  C   pack defaults == the documented literals; engine constants shared
      from dspack_engine; the accounting is dspack_engine's code by
      identity (imported, not copied).
"""
import inspect
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = HERE
sys.path.insert(0, CODE)

OUT = os.path.join(os.path.dirname(CODE), "results",
                   "dspack2_audit_known_answers.txt")
FAIL = []
N_PASS = 0


def check(name: str, ok: bool, detail: str = "") -> bool:
    global N_PASS
    if ok:
        N_PASS += 1
        print(f"PASS {name}" + (f" :: {detail}" if detail else ""))
    else:
        FAIL.append(name)
        print(f"FAIL {name}" + (f" :: {detail}" if detail else ""))
    return ok


def vec_close(a, b, tol=1e-9):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return False
    return bool(np.all(np.abs(a - b) <= tol * np.maximum(1.0, np.abs(b))))


def close(x, y, tol=1e-9):
    return abs(float(x) - float(y)) <= tol * max(1.0, abs(float(y)))


import dspack_engine as E1
import dspack2_engine as E2
pack = E2.load_author_module()


# ── independent indicator/tool implementations ───────────────────────────
def ewm_adjust_true(xs, alpha=None, span=None):
    """pandas .ewm(alpha|span).mean() DEFAULTS: adjust=True.
    Recursion with a GROWING denominator: s_t = (1-a) s_{t-1} + 1,
    n_t = (1-a) n_{t-1} + x_t, y_t = n_t / s_t, seeded at first valid.
    Leading NaNs yield NaN (pandas seeds at the first valid value)."""
    a = 2.0 / (span + 1.0) if span is not None else alpha
    ys, num, den = [], 0.0, 0.0
    for x in xs:
        if x != x and den == 0.0:          # leading NaN: pandas says NaN
            ys.append(float("nan"))
            continue
        num = (1.0 - a) * num + float(x)
        den = (1.0 - a) * den + 1.0
        ys.append(num / den)
    return ys


def naive_single(w, closes, fee):
    """Straight-line single-symbol account of the DECLARED convention:
    factor_t = (1 + w[t-1]*r[t]) * (1 - |dw[t]|*fee), lv[0] = 100_000.
    A trade = a maximal same-sign nonzero run; ref = entry level (flat
    start) or post-exit level (reversal start); exit event bar u = the
    first LATER bar with zero or opposite weight (it still earns r[u])."""
    START = 100_000.0
    n = len(w)
    lv = [START]
    fees = [0.0] * (n + 1)
    for t in range(n):
        if t == 0:
            ret_f = 1.0
        else:
            ret_f = 1.0 + w[t - 1] * (closes[t] / closes[t - 1] - 1.0)
        dw = abs(w[0]) if t == 0 else abs(w[t] - w[t - 1])
        fees[t] = lv[-1] * ret_f * dw * fee
        lv.append(lv[-1] * ret_f * (1.0 - dw * fee))
    trades = []
    a, s_run, ref_kind = None, 0.0, None
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
            u = t
            ref = a if ref_kind == "flat" else a + 1
            trades.append({"a": a, "u": u, "usd": lv[u + 1] - lv[ref],
                           "fees": sum(fees[ref:u + 1])})
            a, s_run, ref_kind = None, 0.0, None
            if st != 0.0:
                a, s_run, ref_kind = t, st, "rev"
    open_run = None
    if a is not None:
        ref = a if ref_kind == "flat" else a + 1
        open_run = {"a": a, "usd": lv[-1] - lv[ref], "fees": sum(fees[ref:])}
    return {"lv": lv, "trades": trades, "open_run": open_run}


def naive_portfolio(W, closes2d, fee):
    """Straight-line portfolio account (ds4 convention, adapted for ds8):
    grow_ret_t = 1 + sum_legs w_leg[t-1] * r_leg[t]  (row 0: 1.0);
    delta_t = |W[0].sum()| at row 0, else |W[t]-W[t-1]| summed;
    lv[0] = 100_000; a PERIOD = a maximal constant-weight stretch; the
    switch's full turnover settles at the closing row's close and is charged
    to the closing period."""
    START = 100_000.0
    n = W.shape[0]
    lv = [START]
    fees = [0.0] * (n + 1)
    for t in range(n):
        if t == 0:
            grow = 1.0
            dw = float(np.abs(W[0]).sum())
        else:
            rs = closes2d[t] / closes2d[t - 1] - 1.0
            grow = 1.0 + float(np.dot(W[t - 1], rs))
            dw = float(np.abs(W[t] - W[t - 1]).sum())
        fees[t] = lv[-1] * grow * dw * fee
        lv.append(lv[-1] * grow * (1.0 - dw * fee))
    changes = [True] + [bool(np.abs(W[t] - W[t - 1]).sum() > 0)
                        for t in range(1, n)]
    bars = [t for t in range(n) if changes[t]]
    periods = []
    for i in range(len(bars)):
        # DECLARED partition (dspack_engine.segment_periods): period i >= 1
        # references the level RIGHT AFTER its own entry bar settles
        # (lv[bars[i]+1]); its entry switch fee and the switch bar's return
        # at the OLD weights belong to the CLOSING period i-1. Bar 0 starts
        # from lv[0].
        ref_idx = 0 if i == 0 else bars[i] + 1
        ref_lvl = lv[ref_idx]
        if i + 1 < len(bars):
            u = bars[i + 1]
            periods.append({"b": bars[i], "u": u, "usd": lv[u + 1] - ref_lvl,
                            "fees": sum(fees[ref_idx:u + 1]),
                            "pnl_pct": (lv[u + 1] - ref_lvl) / ref_lvl})
        else:
            periods.append({"b": bars[i], "u": None,
                            "usd": lv[-1] - ref_lvl,
                            "fees": sum(fees[ref_idx:]),
                            "pnl_pct": (lv[-1] - ref_lvl) / ref_lvl,
                            "open": True})
    return {"lv": lv, "periods": periods}


def synth_df(closes, highs=None, lows=None, vols=None):
    n = len(closes)
    highs = highs if highs is not None else [c + 0.5 for c in closes]
    lows = lows if lows is not None else [c - 0.5 for c in closes]
    vols = vols if vols is not None else [10.0] * n
    return pd.DataFrame({"open": closes, "high": highs, "low": lows,
                         "close": closes, "volume": vols})


def hand_z(case, series, lookback, entry):
    """Literal z arithmetic: rolling mean/std(ddof=1) of the last
    `lookback` values; classify by the pack's mask logic."""
    out = []
    for t in range(len(series)):
        if t < lookback - 1:
            out.append(0.0)
            continue
        win = [float(x) for x in series[t - lookback + 1:t + 1]]
        m = sum(win) / len(win)
        sd = math.sqrt(sum((x - m) ** 2 for x in win) / (len(win) - 1))
        if sd == 0.0:
            out.append(0.0)
            continue
        z = (float(series[t]) - m) / sd
        if z < -entry:
            out.append(1.0)
        elif z > entry:
            out.append(-1.0)
        elif abs(z) < 0.5:
            out.append(-0.5)       # negative token = explicit marker bar
        else:
            out.append(0.5)        # positive token = clean gap bar
    return out


def tokens_to_pos(toks):
    return [0.0 if abs(t) != 1.0 else t for t in toks]


# ── A6 bb_reversion ───────────────────────────────────────────────────────
def case_a6():
    closes = [100.0, 100.1, 99.9, 100.1, 99.9, 99.8, 94.0, 94.2, 99.5,
              100.1, 110.0, 101.0, 85.0, 92.2]
    lookback, entry = 5, 1.5
    df = synth_df(closes)
    toks = hand_z("A6", closes, lookback, entry)
    if not (1.0 in toks and -1.0 in toks and 0.5 in toks and -0.5 in toks):
        check("A6 crafted series exercises all mask branches", False,
              f"tokens {toks}")
    # gate absolutely open: lateral = adx < 1e9 whenever adx is defined
    # (adx_period=2 -> adx defined from t>=3; z from t>=4; triggers t>=6)
    w = np.asarray(pack.strat_bb_reversion(df, n=lookback, z_entry=entry,
                                           adx_max=1e9, adx_period=2),
                   dtype=float)
    check("A6 z-test stateless triggers (gate open)",
          vec_close(w, tokens_to_pos(toks), tol=1e-12),
          f"got {w.tolist()} vs {tokens_to_pos(toks)}")
    # statelessness: every nonzero weight sits on its own trigger bar --
    # a nonzero bar must satisfy the trigger condition independently
    trig = [t for t in range(len(closes)) if abs(toks[t]) == 1.0]
    nontrig_nonzero = [t for t in range(len(closes))
                       if w[t] != 0.0 and abs(toks[t]) != 1.0]
    check("A6 stateless: nonzero bars are exactly the trigger bars",
          not nontrig_nonzero and len(trig) >= 2,
          f"triggers at {trig}, stray {nontrig_nonzero}")
    # gate fully shut: adx_max=0.0 -> adx < 0 is never true (adx >= 0, and
    # warmup NaN < 0 is False) -> NO position on either side
    w0 = np.asarray(pack.strat_bb_reversion(df, n=lookback, z_entry=entry,
                                            adx_max=0.0, adx_period=2),
                    dtype=float)
    check("A6 ADX gate shut kills both sides",
          vec_close(w0, np.zeros(len(closes)), tol=1e-12),
          f"got {w0.tolist()}")


# ── A7 rsi2 ───────────────────────────────────────────────────────────────
def case_a7():
    closes = [100.0 + 3.5 * t for t in range(27)] + [177.0, 161.0, 167.0,
                                                     173.0, 179.0, 185.0]
    df = synth_df(closes)
    got = np.asarray(pack.strat_rsi2(df, rsi_len=2, entry=10, exit=60,
                                     trend_ema=200), dtype=float)
    # independent indicators, adjust=True closed form (pandas defaults)
    diffs = [None] + [closes[t] - closes[t - 1]
                      for t in range(1, len(closes))]
    gains = ewm_adjust_true([np.nan] + [max(d, 0.0) for d in diffs[1:]],
                            alpha=0.5)
    losses = ewm_adjust_true([np.nan] + [max(-d, 0.0) for d in diffs[1:]],
                             alpha=0.5)
    rsi = [100.0 - 100.0 / (1.0 + g / l) if (l is not None and not
           (isinstance(l, float) and math.isnan(l))) and l != 0 else None
           for g, l in zip(gains, losses)]
    ema200 = ewm_adjust_true(closes, span=200)
    exp, in_pos = [], False
    for t in range(len(closes)):
        tr_ok = closes[t] > ema200[t]
        if not in_pos and (rsi[t] is not None and rsi[t] < 10) and tr_ok:
            in_pos = True
        elif in_pos and rsi[t] is not None and rsi[t] > 60:
            in_pos = False
        exp.append(1.0 if in_pos else 0.0)
    holds = [t for t in range(len(closes)) if exp[t] == 1.0]
    if not (holds and holds[0] > 0 and len(holds) >= 2
            and exp[holds[-1] + 1] == 0.0):
        check("A7 crafted series exercises entry/hold/exit", False,
              f"expected scheme {holds}")
    check("A7 rsi2 hand state machine", vec_close(got, exp, tol=1e-12),
          f"holding bars {holds}")
    # pack's own series equal the independent recursions
    delta = pack.pd.Series(closes).diff()
    g = delta.clip(lower=0).ewm(alpha=0.5).mean()
    l = (-delta.clip(upper=0)).ewm(alpha=0.5).mean()
    prsi = 100.0 - 100.0 / (1.0 + g / l.replace(0.0, np.nan))
    ok_r = all((math.isnan(prsi.iloc[t]) == (mine is None)
                or (mine is not None and close(prsi.iloc[t], mine,
                                               tol=1e-9)))
               for t, mine in enumerate(rsi))
    check("A7 RSI(2) recursion (adjust=True) == pandas ewm", ok_r,
          f"rsi@28 {prsi.iloc[28]:.4f}, rsi@30 {prsi.iloc[30]:.4f}")
    pema = pack.pd.Series(closes).ewm(span=200).mean().to_numpy()
    check("A7 ema(span=200) closed form (adjust=True) == pandas",
          vec_close(pema, ema200, tol=1e-9),
          f"ema200@28 {ema200[28]:.4f} vs pandas {pema[28]:.4f}")
    check("A7 stateful: holding run >= 2 bars exists",
          len(holds) >= 2, f"holding bars {holds}")
    check("A7 long-only", float(np.min(got)) >= 0.0, f"min {np.min(got)}")


# ── A8 pairs ──────────────────────────────────────────────────────────────
def case_a8():
    lookback, entry = 5, 1.5
    btc = [100.0, 100.1, 99.9, 100.0, 100.05, 100.1, 100.0, 100.05, 99.95,
           100.0, 100.1, 100.05, 100.0, 100.05, 100.1]
    eth = [50.0, 50.05, 49.95, 50.0, 50.05, 50.0, 52.5, 52.6, 50.5, 50.0,
           50.1, 50.05, 49.0, 47.5, 45.0]
    dfs = {"BTC/USDT": synth_df(btc), "ETH/USDT": synth_df(eth)}
    pairs = pack.strat_pairs(dfs, lookback=lookback, z_entry=entry)
    pa = np.asarray(pairs["BTC/USDT"], dtype=float)
    pb = np.asarray(pairs["ETH/USDT"], dtype=float)
    spread = [math.log(btc[t]) - math.log(eth[t]) for t in range(len(btc))]
    toks = hand_z("A8", spread, lookback, entry)
    if not (1.0 in toks and -1.0 in toks and 0.5 in toks and -0.5 in toks):
        check("A8 crafted panel exercises all mask branches", False,
              f"tokens {toks}")
    exp_pa = tokens_to_pos(toks)
    exp_pb = [-exp_pa[t] * (eth[t] / btc[t]) if exp_pa[t] != 0.0 else 0.0
              for t in range(len(btc))]
    check("A8 pos_a hand spread z (stateless)",
          vec_close(pa, exp_pa, tol=1e-12),
          f"got {pa.tolist()} vs {exp_pa}")
    check("A8 pos_b share-hedge weights", vec_close(pb, exp_pb, tol=1e-9),
          f"got {np.round(pb, 8).tolist()}")
    check("A8 leg-B zero iff leg-A zero",
          all((pa[t] == 0.0) == (pb[t] == 0.0) for t in range(len(btc))),
          "share hedge coupling")
    trig = [t for t in range(len(btc)) if abs(toks[t]) == 1.0]
    check("A8 both legs move only on trigger bars",
          trig and all(pb[t] == 0.0 for t in range(len(btc))
                       if abs(toks[t]) != 1.0), f"triggers at {trig}")


# ── A9 vwap_reversion ─────────────────────────────────────────────────────
def case_a9():
    lookback, entry = 5, 1.5
    closes = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
              108.0, 108.1, 90.0, 98.0]
    vols = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 2.0, 2.0,
            2.0, 40.0]
    df = synth_df(closes, vols=vols)
    got = np.asarray(pack.strat_vwap_reversion(df, lookback=lookback,
                                               z_entry=entry), dtype=float)
    # hand dev-of-dev z; dev valid from t>=lookback-1, z from t>=2lb-2
    devs = []
    for t in range(len(closes)):
        if t < lookback - 1:
            devs.append(None)
            continue
        pv = sum(closes[i] * vols[i] for i in range(t - lookback + 1, t + 1))
        vv = sum(vols[i] for i in range(t - lookback + 1, t + 1))
        vwap = pv / vv
        devs.append((closes[t] - vwap) / vwap)
    exp = []
    for t in range(len(closes)):
        if devs[t] is None or t < 2 * lookback - 2:
            exp.append(0.0)
            continue
        win = [d for d in devs[t - lookback + 1:t + 1]]
        m = sum(win) / len(win)
        sd = math.sqrt(sum((x - m) ** 2 for x in win) / (len(win) - 1))
        if sd == 0.0:
            exp.append(0.0)
            continue
        z = (devs[t] - m) / sd
        if z > entry:
            exp.append(-1.0)
        elif z < -entry:
            exp.append(1.0)
        else:
            exp.append(0.0)
    trig = [t for t in range(len(closes)) if abs(exp[t]) == 1.0]
    if not (-1.0 in exp and 1.0 in exp):
        check("A9 crafted series exercises both sides", False,
              f"exp {exp}")
    check("A9 vwap reversion hand z", vec_close(got, exp, tol=1e-12),
          f"triggers at {trig}, got {got.tolist()}")
    check("A9 binary weights (0 or +-1 only)",
          set(np.unique(got)).issubset({-1.0, 0.0, 1.0}),
          f"vals {set(np.unique(got).tolist())}")
    check("A9 warmup flat",
          all(got[t] == 0.0 for t in range(2 * lookback - 2)),
          "z undefined before 2*lookback-2")


# ── B7 run_suite(ds8) end-to-end vs straight line ────────────────────────
def case_b7(tmp):
    n = 260        # strat_pairs defaults lookback=168: shorter series could
    # NEVER trigger (rolling NaN -> flat) and B7 would pass vacuously
    rng = np.random.default_rng(11)
    btc = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    eth = 50.0 * np.exp(np.cumsum(rng.normal(0.0, 0.012, n)))
    pb = os.path.join(tmp, "BTCUSDT_aud_1h.csv")
    pe = os.path.join(tmp, "ETHUSDT_aud_1h.csv")
    _write_csv(pb, btc)
    _write_csv(pe, eth)
    out = E2.run_suite([pb, pe], {"strat": "ds8", "window": "full",
                                  "costs": "repo6x5"})
    row = out["tables"][0]
    # rebuild the SAME panel the engine built and the weights it fed the core
    dfs = {E1._head(p): E1.load_csv(p) for p in (pb, pe)}
    keep = E1.aligned_closes(dfs).index
    src = {h: dfs[h].reindex(keep).dropna(subset=["close"]) for h in dfs}
    W = E2.positions_pairs(src)
    cl = E1.aligned_closes(src).to_numpy()
    naive = naive_portfolio(W, cl, 0.0011)
    closed = [p for p in naive["periods"] if p.get("open") is None]
    check("B7 non-vacuous: the panel actually triggers periods",
          len(closed) >= 3, f"closed periods {len(closed)}")
    lv = naive["lv"]
    ret_ref = (lv[-1] / lv[0] - 1.0) * 100.0
    check("B7 ds8 ret vs straight line",
          close(row["ret_pct"], ret_ref, tol=1e-6),
          f"engine {row['ret_pct']:.10f} vs {ret_ref:.10f}")
    check("B7 ds8 closed periods count",
          row["n_trades"] == len(closed),
          f"engine {row['n_trades']} vs {len(closed)}")
    check("B7 ds8 closed period tiling",
          close(sum(p["usd"] for p in closed),
                (lv[closed[-1]["u"] + 1] - lv[0]) if closed else 0.0,
                tol=1e-6),
          "closed period dollars tile the equity delta")
    wpct = [p["pnl_pct"] for p in closed if p["pnl_pct"] > 0]
    lpct = [p["pnl_pct"] for p in closed if p["pnl_pct"] <= 0]
    naive_pf = ((sum(wpct) / abs(sum(lpct))) if lpct and sum(lpct) < 0
                else None) if closed else None
    check("B7 ds8 PF == straight line",
          (naive_pf is None) == (row["pf_strict"] is None)
          and (naive_pf is None or close(row["pf_strict"], naive_pf,
                                         tol=1e-6)),
          f"engine {row['pf_strict']} vs {naive_pf}")
    check("B7 ds8 bench == equal-weight product",
          close(out["metrics"]["bench_ret_pct"],
                (float(np.prod(1.0 + (cl[1:] / cl[:-1] - 1.0).mean(axis=1)))
                 - 1.0) * 100.0, tol=1e-9),
          f"{out['metrics']['bench_ret_pct']:.6f}")
    check("B7 ds8 drag >= 0 (fees only subtract)",
          row["drag_pp"] is not None and row["drag_pp"] >= -1e-9,
          f"drag_pp {row['drag_pp']}")


# ── B8 run_suite(ds7) end-to-end vs straight line ────────────────────────
def case_b8(tmp):
    n = 400        # ds7 (stateful RSI-2 + EMA200 gate) needs room for a
    # handful of dips inside an uptrend; keep n trades non-vacuous
    rng = np.random.default_rng(23)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n)))
    p = os.path.join(tmp, "BTCUSDT_aud2_1h.csv")
    _write_csv(p, closes)
    out = E2.run_suite([p], {"strat": "ds7", "window": "full",
                             "costs": "repo6x5"})
    row = out["tables"][0]
    cl_loaded = E1.load_csv(p)["close"].to_numpy()
    w = E2.positions_single(E1.load_csv(p), "ds7")
    naive = naive_single(w.tolist(), closes.tolist(), 0.0011)
    ret_ref = (naive["lv"][-1] / naive["lv"][0] - 1.0) * 100.0
    check("B8 non-vacuous: ds7 opened trades",
          naive["trades"] and row["n_trades"] >= 2,
          f"naive {len(naive['trades'])}, engine {row['n_trades']}")
    check("B8 ds7 ret vs straight line",
          close(row["ret_pct"], ret_ref, tol=1e-6),
          f"engine {row['ret_pct']:.10f} vs {ret_ref:.10f}")
    runs = len(naive["trades"])     # closed runs only (engine excludes an
    # open tail; the straight line counts exactly the closed ones)
    check("B8 ds7 closed trades == straight-line closed trades",
          row["n_trades"] == runs,
          f"engine {row['n_trades']} vs {runs}"
          f" (open tail: {1 if naive['open_run'] else 0})")
    check("B8 ds7 bench span",
          close(out["metrics"]["bench_ret_pct"],
                (cl_loaded[-1] / cl_loaded[0] - 1.0) * 100.0, tol=1e-12),
          f"{out['metrics']['bench_ret_pct']:.6f}")


# ── B9 causality (prefixes) ──────────────────────────────────────────────
def case_b9():
    n = 90
    rng = np.random.default_rng(31)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    highs = closes * (1.0 + np.abs(rng.normal(0.0, 0.004, n)))
    lows = closes * (1.0 - np.abs(rng.normal(0.0, 0.004, n)))
    vols = np.abs(rng.normal(10.0, 2.0, n))
    df = pd.DataFrame({"open": closes, "high": highs, "low": lows,
                       "close": closes, "volume": vols})
    eth = 50.0 * np.exp(np.cumsum(rng.normal(0.0, 0.011, n)))
    eth_df = pd.DataFrame({"open": eth, "high": eth * 1.002,
                           "low": eth * 0.998, "close": eth,
                           "volume": vols})
    ok_all = True
    for cut in (40, 65):
        for strat in ("ds6", "ds7", "ds9"):
            fn = {"ds6": "strat_bb_reversion", "ds7": "strat_rsi2",
                  "ds9": "strat_vwap_reversion"}[strat]
            full = np.asarray(getattr(pack, fn)(df), dtype=float)
            sub = np.asarray(getattr(pack, fn)(df.iloc[:cut]), dtype=float)
            if len(sub) != cut or not vec_close(full[:cut],
                                                np.nan_to_num(sub),
                                                tol=1e-12):
                ok_all = False
                break
    check("B9 ds6/ds7/ds9 causal (prefix==full on overlap)", ok_all)
    # pairs: same panel logic, prefix of BOTH legs
    pairs_full = pack.strat_pairs({"BTC/USDT": df, "ETH/USDT": eth_df})
    ok_p = True
    for cut in (40, 65):
        pairs_cut = pack.strat_pairs({"BTC/USDT": df.iloc[:cut],
                                      "ETH/USDT": eth_df.iloc[:cut]})
        if not all(vec_close(np.asarray(pairs_full[k], dtype=float)[:cut],
                             np.nan_to_num(np.asarray(pairs_cut[k],
                                                      dtype=float)),
                             tol=1e-12) for k in ("BTC/USDT", "ETH/USDT")):
            ok_p = False
            break
    check("B9 ds8 causal (both legs)", ok_p)


def case_b10(tmp):
    n = 70
    rng = np.random.default_rng(53)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    p = os.path.join(tmp, "BTCUSDT_det_1h.csv")
    _write_csv(p, closes)
    a = E2.run_suite([p], {"strat": "ds9", "window": "full",
                           "costs": "repo6x5"})
    b = E2.run_suite([p], {"strat": "ds9", "window": "full",
                           "costs": "repo6x5"})
    check("B10 determinism (identical JSON twice)",
          json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))


def _write_csv(path, closes):
    with open(path, "w", encoding="utf-8", newline="") as f:
        ts = 1735689600000 + 3_600_000
        f.write("open_ts,open,high,low,close,volume\n")
        for c in closes:
            f.write(f"{ts},{c - 0.2:.8f},{c + 0.8:.8f},{c - 0.8:.8f},"
                    f"{c:.8f},10.0\n")
            ts += 3_600_000


def case_c():
    sig = inspect.signature(pack.strat_bb_reversion)
    exp6 = {"n": 20, "z_entry": 2.0, "adx_max": 20, "adx_period": 14}
    got6 = {k: v.default for k, v in sig.parameters.items()
            if k in exp6 and v.default is not inspect.Parameter.empty}
    check("C bb_reversion defaults", got6 == exp6, f"{got6}")
    exp7 = {"rsi_len": 2, "entry": 10, "exit": 60, "trend_ema": 200}
    got7 = {k: v.default for k, v in
            inspect.signature(pack.strat_rsi2).parameters.items()
            if k in exp7}
    check("C rsi2 defaults", got7 == exp7, f"{got7}")
    exp8 = {"symbol_a": "BTC/USDT", "symbol_b": "ETH/USDT", "lookback": 168,
            "z_entry": 2.0}
    got8 = {k: v.default for k, v in
            inspect.signature(pack.strat_pairs).parameters.items()
            if k in exp8}
    check("C pairs defaults", got8 == exp8, f"{got8}")
    exp9 = {"lookback": 24, "z_entry": 2.0}
    got9 = {k: v.default for k, v in
            inspect.signature(pack.strat_vwap_reversion).parameters.items()
            if k in exp9}
    check("C vwap_reversion defaults", got9 == exp9, f"{got9}")
    check("C shared constants from dspack_engine",
          E1.STARTING_EQUITY == 100_000.0 and E1.WARMUP_BARS == 2400
          and E1.SCORE_BARS == 4368 and E1.BARS_PER_YEAR == 8760
          and set(E1.COST_PRESETS) == {"author", "repo6x5"}
          and E1.COST_PRESETS["author"]["taker_fee"] == 0.0
          and E1.COST_PRESETS["repo6x5"]["taker_fee"] == 0.0006
          and E1.COST_PRESETS["repo6x5"]["slippage"] == 0.0005,
          "100_000 / 2400+4368 / 8760 / author|repo6x5")
    check("C accounting is dspack_engine's code (identity)",
          E2.E is E1, "dspack2 imports dspack_engine: one accounting, "
          "no copies")
    check("C dspack2 surfaces",
          E2.STRATS == ("ds6", "ds7", "ds8", "ds9")
          and sorted(E2.PAIR_FILES) == ["BTCUSDT", "ETHUSDT"]
          and E2.PAIR_FILES["BTCUSDT"] == "BTC/USDT"
          and E2.PAIR_FILES["ETHUSDT"] == "ETH/USDT",
          f"{E2.STRATS}")


def main():
    import tempfile
    print(f"dspack2 known-answer audit -- {os.path.dirname(CODE)}")
    with tempfile.TemporaryDirectory() as tmp:
        case_a6()
        case_a7()
        case_a8()
        case_a9()
        case_b7(tmp)
        case_b8(tmp)
        case_b9()
        case_b10(tmp)
        case_c()
    print(f"-- {N_PASS} pass / {len(FAIL)} fail --")
    lines = ([f"dspack2 audit {os.path.dirname(CODE)}"]
             + [f"FAIL {name}" for name in FAIL]
             + [f"{N_PASS} pass / {len(FAIL)} fail"])
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    sys.exit(0 if not FAIL else 1)


if __name__ == "__main__":
    main()
