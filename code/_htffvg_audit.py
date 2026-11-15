#!/usr/bin/env python
"""_htffvg_audit.py -- known answers for the htf_ltf_fvg pack port.

Run BEFORE any real-data artifact (repo mandatory order). The pack ships its
own vector/event dual engine with a parity check; this audit adds what the
repo demands on top:
  A. hand-computed cases for every execution rule on a scenario that REALLY
     produces a 4H bull zone (three buckets: dip / rise / gap-down-hold) and
     a REAL 15M bull FVG (third low > first high): zone availability timing,
     limit fill/expiry, market next-open, gap-through-stop skip, SL-first on
     spanning bars, maker/taker fees, max_hold, end-of-data, leverage cap.
  B. the accounting invariant eq[-1] - INIT == sum(pnl) on every run;
  C. vector/event parity on several parameter regimes (non-vacuous);
  D. no-lookahead truncation (prefix signals identical to full-run signals).
Expectation bugs count against the TEST first (the audited lesson: every
failure in this file's first draft was the test's geometry).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import htf_ltf_fvg_strategy as S  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {name}")
    else:
        FAIL += 1
        print(f"FAIL {name}  {detail}")


T0 = pd.Timestamp("2026-01-01 00:00:00")


def mk(bars):
    a = np.asarray(bars, float)
    idx = pd.date_range(T0, periods=len(a), freq="15min")
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1],
                         "low": a[:, 2], "close": a[:, 3]}, index=idx)


def base_scenario():
    """48 bars of 4H zone construction + 16 bars of zone action.

    Buckets (16 x 15m each):
      0: dip around 99.4-100.5          high ~100.5
      1: rise to ~108                   (bucket between)
      2: hold 101.1-101.9               low ~101.1  -> 4H bull FVG [100.5, 101.1]
      3: taps the zone, completes a 15M bull FVG -> signal bar (index 55)
    Returns (ltf, expected signal index)."""
    bars = []
    for i in range(16):        # bucket 0: dip
        bars.append((99.6 + 0.04 * i, 100.0 + 0.04 * i, 99.4 + 0.04 * i,
                     99.8 + 0.04 * i))
    for i in range(16):        # bucket 1: rise
        bars.append((102.0 + 0.4 * i, 102.5 + 0.4 * i, 101.5 + 0.4 * i,
                     102.0 + 0.4 * i))
    for i in range(16):        # bucket 2: hold above the bucket-0 high
        bars.append((101.3 + 0.03 * i, 101.8 + 0.03 * i, 101.1 + 0.03 * i,
                     101.4 + 0.03 * i))
    # bucket 3: bars 48-51 tap the zone [~100.5, ~101.1] (touch on EARLIER bars)
    bars += [(101.0, 101.3, 100.7, 101.1),
             (100.9, 101.2, 100.6, 101.0),
             (100.8, 101.1, 100.55, 100.9),
             (100.9, 101.2, 100.6, 101.0)]
    # bars 52-54: a REAL 15M bull FVG (l2 > h0), closes above zbot (100.6)
    bars += [(100.95, 101.1, 100.7, 100.85),    # h0 = 101.1
             (100.8, 100.95, 100.65, 100.75),   # close 100.75 > zbot: alive
             (101.2, 102.0, 101.15, 101.9)]     # l2 = 101.15 > 101.1 -> FVG
    # signal completes at bar 55 (index 55 == 48+7)... FVG row i uses i-2..i,
    # so the FVG is "at" bar 54; market fill = bar 55's open
    bars += [(101.9, 102.3, 101.7, 102.1)]      # bar 55: the entry bar
    return mk(bars), 55


P_BASE = dict(entry_mode="market", rr=2.0, risk_pct=0.01, max_leverage=5.0,
              fee_taker_bps=5.0, fee_maker_bps=2.0, slippage_bps=0.5,
              sl_buffer_bps=0.0, min_htf_gap_bps=0.0, min_ltf_gap_bps=0.0,
              max_zone_age=0, limit_expiry=8, entry_frac=0.5, max_hold=96,
              init_equity=10_000.0)


def a1_fvg_detection():
    p = S.Params()
    bars = [(100, 102, 99, 101), (101, 103, 100, 102),
            (104, 106, 102.5, 105)]
    df = mk(bars)
    f = S.detect_fvg(df, 0.0)
    check("A1 bull FVG at b2 (l2 > h0)", int(f["dir"].iloc[2]) == 1)
    check("A1 edges top=102.5/bot=102, sl_ref=99",
          abs(f["top"].iloc[2] - 102.5) < 1e-9
          and abs(f["bot"].iloc[2] - 102.0) < 1e-9
          and abs(f["sl_ref"].iloc[2] - 99.0) < 1e-9)
    f2 = S.detect_fvg(df, 100.0)   # gap ~49 bps < 100
    check("A1 min_gap_bps filter kills it", int(f2["dir"].iloc[2]) == 0)
    df_b = mk([(100, 101, 98, 99), (99, 100, 97, 98), (96, 97, 95, 96)])
    f3 = S.detect_fvg(df_b, 0.0)
    # the pack's bear convention: top = l0 (98), bot = h2 (97), and the SL
    # reference is the MAX of the three HIGHS = b0.h = 101 (the candle that
    # must not be reclaimed), NOT the gap edge
    check("A1 bear FVG (h2 < l0): top=98/bot=97/sl_ref=101",
          int(f3["dir"].iloc[2]) == -1
          and abs(f3["top"].iloc[2] - 98.0) < 1e-9
          and abs(f3["bot"].iloc[2] - 97.0) < 1e-9
          and abs(f3["sl_ref"].iloc[2] - 101.0) < 1e-9)


def a2_zone_and_signal_exist():
    """The scenario really produces the 4H zone and exactly one signal, and
    the signal cannot be inside the bucket that built the zone."""
    ltf, sig_i = base_scenario()
    p = S.Params(**P_BASE)
    hf = S.make_htf(ltf, p)
    check("A2 three complete 4H bars", len(hf) == 3, str(len(hf)))
    sig = S.vector_signals(ltf, p)
    check("A2 exactly one signal, at bar 54 (the 15M FVG bar)",
          len(sig) == 1 and int(sig["i"].iloc[0]) == 54,
          str(sig[["i", "side"]].to_dict("records")))
    check("A2 signal side follows the zone (long)", int(sig["side"].iloc[0]) == 1)


def a3_market_fill_and_stop_gap():
    """Market mode fills at the NEXT open (+slippage); an open already beyond
    the stop skips the trade."""
    ltf, _ = base_scenario()
    p = S.Params(**P_BASE)
    tv = S.vector_backtest(ltf, p)
    te = S.event_backtest(ltf, p)
    S.compare(tv, te)
    check("A3 market trade fills at bar 55's open", not tv.empty
          and tv["entry_time"].iloc[0] == ltf.index[55],
          str(tv[["entry_time", "entry"]].to_dict("records")))
    if not tv.empty:
        r = tv.iloc[0]
        exp_entry = ltf["open"].iloc[55] * (1 + 0.5 / 1e4)
        check("A3 entry = next open with taker slippage",
              abs(r["entry"] - exp_entry) < 1e-9,
              f"entry={r['entry']} expected={exp_entry}")
        # SL = sl_ref 100.65 (min low of the FVG trio), TP = entry + 2*risk
        check("A3 SL at the FVG sl_ref (100.65)",
              abs(r["sl"] - 100.65) < 1e-9, f"sl={r['sl']}")
    invariant("A3", tv, p)
    # gap variant: replace the bar after the signal with a crash below the SL
    bars2 = ltf.copy()
    bars2.iloc[55, bars2.columns.get_loc("open")] = 80.0
    bars2.iloc[55, bars2.columns.get_loc("high")] = 81.0
    bars2.iloc[55, bars2.columns.get_loc("low")] = 79.0
    bars2.iloc[55, bars2.columns.get_loc("close")] = 80.5
    tv2 = S.vector_backtest(bars2, p)
    check("A3 open gapped through the stop -> trade skipped", tv2.empty,
          str(tv2[["entry", "sl"]].to_dict("records")))
    invariant("A3 gap", tv2, p)


def a4_limit_expiry_and_tp_cancel():
    """Limit mode at the CE of the 15M FVG: with price drifting away after the
    signal the order never fills -> expired (or TP-first cancel) -> no trade;
    the signal itself must exist (non-vacuous check)."""
    ltf, _ = base_scenario()
    p = S.Params(**{**P_BASE, "entry_mode": "limit", "entry_frac": 0.5,
                    "limit_expiry": 4})
    sig = S.vector_signals(ltf, p)
    check("A4 signal exists (non-vacuous)", len(sig) == 1,
          str(sig[["i"]].to_dict("records")))
    tv = S.vector_backtest(ltf, p)
    check("A4 limit order expires/cancels -> no trade", tv.empty,
          str(tv[["entry", "reason"]].to_dict("records")))
    invariant("A4", tv, p)


def a5_sl_first_on_spanning_bar():
    """A bar spanning both SL and TP fills the SL (stop-first); the stop pays
    taker + slippage; the entry already paid taker."""
    ltf, _ = base_scenario()
    p = S.Params(**{**P_BASE, "rr": 1.0})
    # replace bars 56+ with: one calm bar, then a spanning bar, then flat
    tail = [(101.2, 101.6, 101.1, 101.5),
            (101.5, 104.0, 99.5, 103.5),      # spans SL(100.45) and TP(~102.65)
            (100.4, 100.9, 100.2, 100.6)] * 3
    ltf2 = mk(list(ltf.iloc[:56].to_numpy("float").tolist()) + tail)
    tv = S.vector_backtest(ltf2, p)
    te = S.event_backtest(ltf2, p)
    S.compare(tv, te)
    ok = not tv.empty and tv["reason"].iloc[0] == "sl"
    check("A5 spanning bar resolves SL first", ok,
          str(tv[["reason", "exit"]].to_dict("records")))
    if ok:
        r = tv.iloc[0]
        exp_px = min(101.5, r["sl"]) * (1 - 0.5 / 1e4)
        check("A5 stop exit = min(open, SL) with slippage",
              abs(r["exit"] - exp_px) < 1e-9, f"exit={r['exit']} exp={exp_px}")
        check("A5 loss booked (negative pnl)", r["pnl"] < 0, f"pnl={r['pnl']}")
    invariant("A5", tv, p)


def a6_tp_maker_fee():
    """A clean TP hit pays the MAKER fee on exit (limit-style target)."""
    ltf, _ = base_scenario()
    p = S.Params(**{**P_BASE, "rr": 1.0})
    tail = [(101.2, 101.6, 101.1, 101.5),
            (101.5, 103.5, 101.4, 103.2),      # high >= TP ~103.16, no SL touch
            (102.5, 102.8, 102.3, 102.6)] * 3
    ltf2 = mk(list(ltf.iloc[:56].to_numpy("float").tolist()) + tail)
    tv = S.vector_backtest(ltf2, p)
    te = S.event_backtest(ltf2, p)
    S.compare(tv, te)
    ok = not tv.empty and tv["reason"].iloc[0] == "tp"
    check("A6 clean TP hit", ok, str(tv[["reason", "exit"]].to_dict("records")))
    if ok:
        r = tv.iloc[0]
        exp_exit = max(r["entry"], r["tp"])    # max(open, TP), maker no slip
        check("A6 TP exit at max(open, TP), no slippage",
              abs(r["exit"] - r["tp"]) < 1e-9,
              f"exit={r['exit']} tp={r['tp']}")
        risk_u = abs(r["entry"] - r["sl"])
        exp_fees = r["qty"] * (r["entry"] * 5.0 + r["exit"] * 2.0) / 1e4
        check("A6 fees = taker entry + maker exit",
              abs(r["fees"] - exp_fees) < 1e-9,
              f"fees={r['fees']} expected={exp_fees}")
        # the pack's R is NET of fees (its docstring declares it): the gross
        # R is exactly rr, fees shave it below
        check("A6 net-of-fees R below gross rr but positive",
              0.0 < r["r"] < 1.0, f"r={r['r']}")
    invariant("A6", tv, p)


def a7_max_hold_and_eod():
    """max_hold forces the time exit; an open position at the last bar closes
    with reason eod."""
    ltf, _ = base_scenario()
    p = S.Params(**{**P_BASE, "rr": 50.0, "max_hold": 5})
    tail = [(101.2, 101.6, 101.1, 101.5)] * 30   # TP unreachable
    ltf2 = mk(list(ltf.iloc[:56].to_numpy("float").tolist()) + tail)
    tv = S.vector_backtest(ltf2, p)
    check("A7 max_hold time exit at 5 bars",
          not tv.empty and tv["reason"].iloc[0] == "time"
          and tv["bars"].iloc[0] == 5,
          str(tv[["bars", "reason"]].to_dict("records")))
    invariant("A7", tv, p)
    ltf3 = mk(list(ltf.iloc[:58].to_numpy("float").tolist())
              + [(101.2, 101.6, 101.1, 101.5)])
    tv3 = S.vector_backtest(ltf3, p)
    check("A7 open at end of data -> eod close",
          not tv3.empty and tv3["reason"].iloc[0] == "eod",
          str(tv3[["reason"]].to_dict("records")))


def a8_sizing_and_leverage_cap():
    """qty = min(equity*risk/risk_u, equity*lev/entry); with a tight 15M FVG
    the cap binds and R = rr exactly (zero costs)."""
    ltf, _ = base_scenario()
    p = S.Params(**{**P_BASE, "max_leverage": 1.0, "slippage_bps": 0.0,
                    "fee_taker_bps": 0.0, "fee_maker_bps": 0.0, "rr": 2.0})
    # tighten the FVG: h0=100.85, l2=100.88 -> risk_u small vs entry
    bars = list(ltf.iloc[:54].to_numpy("float").tolist())
    bars += [(100.75, 100.85, 100.5, 100.7),     # h0 = 100.85
             (100.7, 100.8, 100.58, 100.65),     # close > zbot: alive
             (100.95, 101.05, 100.88, 101.0)]    # l2 = 100.88 > 100.85 -> FVG
    bars += [(101.0, 103.0, 100.9, 102.5)]       # bar 55: fill + TP reach
    bars += [(102.4, 102.8, 102.2, 102.6)] * 6
    ltf2 = mk(bars)
    tv = S.vector_backtest(ltf2, p)
    te = S.event_backtest(ltf2, p)
    S.compare(tv, te)
    check("A8 trade exists", not tv.empty,
          str(tv[["entry", "sl", "qty", "reason"]].to_dict("records")))
    if not tv.empty:
        r = tv.iloc[0]
        cap = p.init_equity * p.max_leverage / r["entry"]
        check("A8 leverage cap binds on qty", abs(r["qty"] - cap) < 1e-9,
              f"qty={r['qty']} cap={cap}")
        if r["reason"] == "tp":
            check("A8 R = rr exactly (zero costs, clean TP)",
                  abs(r["r"] - 2.0) < 1e-9, f"r={r['r']}")
    invariant("A8", tv, p)


def invariant(name, tr, p):
    if tr.empty:
        return
    diff = tr["equity"].iloc[-1] - p.init_equity - tr["pnl"].sum()
    check(name + " invariant eq[-1]-INIT == sum(pnl)", abs(diff) < 1e-9,
          f"diff={diff}")


def b1_parity_regimes():
    """The pack's own dual-engine parity on several parameter regimes."""
    df = S.synthetic(180, seed=11)
    for p in (S.Params(), S.Params(entry_mode="market"),
              S.Params(entry_frac=0.0), S.Params(entry_frac=1.0),
              S.Params(min_htf_gap_bps=10.0, min_ltf_gap_bps=5.0),
              S.Params(max_zone_age=48), S.Params(rr=3.0, sl_buffer_bps=10.0)):
        tv = S.vector_backtest(df, p)
        te = S.event_backtest(df, p)
        n = len(tv)
        same = (len(tv) == len(te)
                and (tv[["side", "signal_time", "entry_time", "exit_time",
                         "reason"]].reset_index(drop=True)
                     == te[["side", "signal_time", "entry_time", "exit_time",
                            "reason"]].reset_index(drop=True)).all().all()
                and np.allclose(tv[["entry", "exit", "pnl"]].to_numpy(),
                                te[["entry", "exit", "pnl"]].to_numpy(),
                                rtol=1e-9, atol=1e-9))
        check(f"B1 parity regime n={n} mode={p.entry_mode} frac={p.entry_frac}",
              same)
        invariant(f"B1 [{p.entry_mode}/{p.entry_frac}]", tv, p)


def c1_no_lookahead_truncation():
    df = S.synthetic(180, seed=11)
    full = S.vector_signals(df, S.Params(entry_mode="market"))
    k = len(df) - 500
    part = S.vector_signals(df.iloc[:k], S.Params(entry_mode="market"))
    fp = full[full["i"] < k].reset_index(drop=True)
    pp = part.reset_index(drop=True)
    same = len(fp) == len(pp) and (
        fp.empty or (fp[["i", "side"]].to_numpy() == pp[["i", "side"]].to_numpy()).all()
        and np.allclose(fp[["top", "bot", "sl_ref"]].to_numpy(),
                        pp[["top", "bot", "sl_ref"]].to_numpy()))
    check("C1 prefix signals identical to the full run", same,
          f"full_prefix={len(fp)} prefix_run={len(pp)}")


if __name__ == "__main__":
    for fn in (a1_fvg_detection, a2_zone_and_signal_exist,
               a3_market_fill_and_stop_gap, a4_limit_expiry_and_tp_cancel,
               a5_sl_first_on_spanning_bar, a6_tp_maker_fee,
               a7_max_hold_and_eod, a8_sizing_and_leverage_cap,
               b1_parity_regimes, c1_no_lookahead_truncation):
        fn()
    print(f"\n{PASS} PASS, {FAIL} FAIL")
    raise SystemExit(1 if FAIL else 0)
