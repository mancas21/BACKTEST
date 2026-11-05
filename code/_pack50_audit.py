#!/usr/bin/env python
"""_pack50_audit.py -- known-answer audit for the pack-50 engine.

Nothing in the fifty-strategy report is trusted until every group here passes.
Each group pins a convention that a silent bug would move: the fill bar, the
SL-first tie rule, the fee arithmetic, the funding cash flow, the pair leg split,
the resampler, and the indicators.

    python code/_pack50_audit.py          # exit 0 only if ALL PASS
"""
from __future__ import annotations

import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pack50_core as C
import pack50_strats as S

RESULTS = []


def check(group, name, ok, detail=""):
    RESULTS.append((group, name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {group:12s} {name}  {detail}")


def mkdf(o, h, l, c, start_ms=1600000000000, step_ms=3600000):
    n = len(o)
    ts = start_ms + np.arange(n, dtype=np.int64) * step_ms
    return pd.DataFrame({"open_ts": ts, "open": o, "high": h, "low": l,
                         "close": c, "volume": np.ones(n)})


# ─────────────────────────────────────────────────────── group 1: fills
def g1_fills():
    n = 8
    o = np.array([100, 101, 102, 103, 104, 105, 106, 107], float)
    c = o.copy()
    df = mkdf(o, o + 0.5, o - 0.5, c)
    plan = C.Plan(long_entry=np.zeros(n, bool), short_entry=np.zeros(n, bool),
                  long_exit=np.zeros(n, bool), short_exit=np.zeros(n, bool))
    plan.long_entry[2] = True           # signal on bar 2 -> fill at open of bar 3
    plan.long_exit[5] = True            # exit signal on bar 5 -> fill at open of 6
    costs = C.Costs(fee_bps=0.0, slip_bps=0.0)
    r = C.run_plan(df, plan, costs, None)
    t = r["trades"].iloc[0]
    check("fills", "entry at next open", abs(t["entry_px"] - 103.0) < 1e-9,
          f"entry={t['entry_px']}")
    check("fills", "signal exit at next open", abs(t["exit_px"] - 106.0) < 1e-9,
          f"exit={t['exit_px']}")
    check("fills", "trade length in bars", int(t["bars"]) == 3, f"bars={t['bars']}")


# ─────────────────────────────────────────────────────── group 2: SL-first
def g2_sl_first():
    n = 5
    o = np.full(n, 100.0)
    h = np.array([100, 101, 120, 100, 100], float)
    l = np.array([100, 99, 80, 100, 100], float)
    c = np.array([100, 100, 100, 100, 100], float)
    df = mkdf(o, h, l, c)
    plan = C.Plan(long_entry=np.zeros(n, bool), short_entry=np.zeros(n, bool),
                  long_exit=np.zeros(n, bool), short_exit=np.zeros(n, bool))
    plan.long_entry[1] = True
    plan.stop_long = np.full(n, 90.0)
    plan.tp_long = np.full(n, 110.0)
    costs = C.Costs(fee_bps=0.0, slip_bps=0.0)
    r = C.run_plan(df, plan, costs, None)
    t = r["trades"].iloc[0]
    check("execution", "SL-first on a bar containing both", t["exit_reason"] == "stop",
          f"reason={t['exit_reason']}")
    check("execution", "stop filled at the level", abs(t["exit_px"] - 90.0) < 1e-9,
          f"px={t['exit_px']}")


# ─────────────────────────────────────────────────────── group 3: costs
def g3_costs():
    n = 6
    o = np.full(n, 100.0)
    c = np.full(n, 100.0)
    df = mkdf(o, o, o, c)
    plan = C.Plan(long_entry=np.zeros(n, bool), short_entry=np.zeros(n, bool),
                  long_exit=np.zeros(n, bool), short_exit=np.zeros(n, bool))
    plan.long_entry[1] = True
    plan.long_exit[3] = True
    r = C.run_plan(df, plan, C.Costs(fee_bps=10.0, slip_bps=0.0), None, init_equity=10000.0)
    # flat price: 10 bps once on entry and once on exit, both on the same notional
    expect = 10000.0 - 10000.0 * 0.0010 - 10000.0 * 0.0010
    check("costs", "fee charged per side", abs(r["final_equity"] - expect) < 1e-6,
          f"final={r['final_equity']:.6f} expect={expect:.6f}")
    # slippage: the fill prices move, so the loss is qty * (sell_bid - buy_ask)
    r2 = C.run_plan(df, plan, C.Costs(fee_bps=0.0, slip_bps=5.0), None, init_equity=10000.0)
    q = 10000.0 / (100.0 * 1.0005)
    expect2 = 10000.0 + q * (100.0 * (1 - 0.0005) - 100.0 * (1 + 0.0005))
    check("costs", "slippage charged per side", abs(r2["final_equity"] - expect2) < 1e-4,
          f"final={r2['final_equity']:.6f} expect={expect2:.6f}")


# ─────────────────────────────────────────────────────── group 4: funding
def g4_funding():
    n = 9
    o = np.full(n, 100.0)
    c = np.full(n, 100.0)
    df = mkdf(o, o, o, c, step_ms=3600000)
    f_ts = np.array([1600000000000 + 3 * 3600000, 1600000000000 + 6 * 3600000], dtype=np.int64)
    f_rate = np.array([0.0001, 0.0002])
    plan = C.Plan(long_entry=np.zeros(n, bool), short_entry=np.zeros(n, bool),
                  long_exit=np.zeros(n, bool), short_exit=np.zeros(n, bool))
    plan.long_entry[0] = True
    plan.long_exit[7] = True
    r = C.run_plan(df, plan, C.Costs(0.0, 0.0), (f_ts, f_rate), init_equity=10000.0)
    # two settlements, 1 bp and 2 bp, on 100 units at 100 = 10,000 notional
    check("funding", "long pays the sum of the rates",
          abs(r["funding"] - 3.0) < 1e-6, f"funding={r['funding']:.6f} expect=3")
    plan2 = C.Plan(long_entry=np.zeros(n, bool), short_entry=np.zeros(n, bool),
                   long_exit=np.zeros(n, bool), short_exit=np.zeros(n, bool))
    plan2.short_entry[0] = True
    plan2.short_exit[7] = True
    r2 = C.run_plan(df, plan2, C.Costs(0.0, 0.0), (f_ts, f_rate), init_equity=10000.0)
    check("funding", "short receives the same rates",
          abs(r2["funding"] + 3.0) < 1e-6, f"funding={r2['funding']:.6f} expect=-3")


# ─────────────────────────────────────────────────────── group 5: pair split
def g5_pair():
    n = 20
    oa = 100 * 1.01 ** np.arange(n)
    ob = np.full(n, 50.0)
    da = mkdf(oa, oa, oa, oa)
    db = mkdf(ob, ob, ob, ob)
    target = np.ones(n)
    r = C.run_pair(da, db, target, C.Costs(0.0, 0.0), None, None, init_equity=10000.0)
    # entry at open 1; the entry bar earns open->close (zero here), then
    # bars 2..n-1 compound half of a 1% move
    expect = 10000.0 * (1 + 0.5 * 0.01) ** (n - 2)
    check("pairs", "dollar-neutral 50/50 leg split",
          abs(r["final_equity"] - expect) / expect < 1e-6,
          f"final={r['final_equity']:.2f} expect={expect:.2f}")
    r2 = C.run_pair(da, db, -target, C.Costs(0.0, 0.0), None, None, init_equity=10000.0)
    expect2 = 10000.0 * (1 - 0.5 * 0.01) ** (n - 2)
    check("pairs", "inverse target loses what the first made",
          abs(r2["final_equity"] - expect2) / expect2 < 1e-6,
          f"final={r2['final_equity']:.2f} expect={expect2:.2f}")

    # the entry bar must earn open->close, not the previous bar's close
    oa2 = np.array([100.0, 100.0, 100.0, 100.0])
    ca2 = np.array([100.0, 110.0, 110.0, 110.0])
    d2a = mkdf(oa2, oa2, oa2, ca2)
    d2b = mkdf(np.full(4, 50.0), np.full(4, 50.0), np.full(4, 50.0), np.full(4, 50.0))
    r3 = C.run_pair(d2a, d2b, np.ones(4), C.Costs(0.0, 0.0), None, None, init_equity=10000.0)
    check("pairs", "entry bar earns from its own open",
          abs(r3["final_equity"] - 10500.0) < 1e-6, f"final={r3['final_equity']:.2f}")


# ─────────────────────────────────────────────────────── group 6: resample
def g6_resample(tmp="C:/Users/Lenovo/AppData/Local/Temp/opencode/_a.csv"):
    n = 8
    o = np.arange(100, 100 + n, dtype=float)
    h = o + 2
    l = o - 1
    c = o + 1
    ts = 1600000000000 + np.arange(n, dtype=np.int64) * 3600000
    pd.DataFrame({"open_ts": ts, "open": o, "high": h, "low": l, "close": c,
                  "volume": np.ones(n)}).to_csv(tmp, index=False)
    d = C.load_tf(tmp, "4h")
    check("resample", "4h bar count from 8 x 1h", len(d) == 2, f"n={len(d)}")
    check("resample", "4h open = first 1h open", abs(d["open"].iloc[0] - 100.0) < 1e-9)
    check("resample", "4h high = max of the four", abs(d["high"].iloc[0] - 105.0) < 1e-9)
    check("resample", "4h close = last 1h close", abs(d["close"].iloc[0] - 104.0) < 1e-9)
    os.remove(tmp)


# ─────────────────────────────────────────────────────── group 7: indicators
def g7_indicators():
    c = np.arange(1, 60, dtype=float)
    r = S.rsi(c, 14)
    check("indicators", "RSI of a monotone ramp is 100", abs(r[-1] - 100.0) < 1e-6,
          f"rsi={r[-1]:.6f}")
    h = np.full(40, 101.0)
    l = np.full(40, 99.0)
    cc = np.full(40, 100.0)
    a = S.atr(h, l, cc, 14)
    check("indicators", "ATR of a constant 2.0 range", abs(a[-1] - 2.0) < 1e-9,
          f"atr={a[-1]:.6f}")
    hh, ll = S.donchian(np.arange(1, 11, dtype=float), np.arange(1, 11, dtype=float), 3)
    check("indicators", "Donchian excludes the current bar", abs(hh[3] - 3.0) < 1e-9,
          f"hh[3]={hh[3]}")
    e = S.ema(c, 10)
    check("indicators", "EMA starts where the window is full", np.isnan(e[8]) and not np.isnan(e[9]))
    # Heikin-Ashi: the synthetic close is the four-price mean
    oo, hh2, ll2, cc2 = S.heikin_ashi(np.array([10.0]), np.array([12.0]),
                                      np.array([9.0]), np.array([11.0]))
    check("indicators", "HA close = mean of o/h/l/c", abs(cc2[0] - 10.5) < 1e-9, f"{cc2[0]}")


# ─────────────────────────────────────────────────────── group 8: determinism
def g8_determinism():
    rng = np.random.default_rng(7)
    n = 400
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.003
    l = np.minimum(o, c) * 0.997
    df = mkdf(o, h, l, c)
    a = C.run_plan(df, S.b01(df), C.Costs(4.0, 2.0), None)
    b = C.run_plan(df, S.b01(df), C.Costs(4.0, 2.0), None)
    same = (a["final_equity"] == b["final_equity"] and
            len(a["trades"]) == len(b["trades"]))
    check("determinism", "same input -> same equity and trade count", same,
          f"eq={a['final_equity']:.6f} n={len(a['trades'])}")


# ─────────────────────────────────────────────────────── group 9: no look-ahead
def g9_no_lookahead():
    """A signal computed with data up to bar t must not change when bar t+1 is
    replaced by garbage."""
    rng = np.random.default_rng(11)
    n = 300
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.003
    l = np.minimum(o, c) * 0.997
    df = mkdf(o, h, l, c)
    p1 = S.b01(df)
    df2 = df.copy()
    df2.loc[n - 1, ["open", "high", "low", "close"]] = [1e6, 1e6, 1e6, 1e6]
    p2 = S.b01(df2)
    ok = np.array_equal(p1.long_entry[:n - 1], p2.long_entry[:n - 1])
    check("causality", "signals before the last bar do not move", ok)


def main() -> int:
    for fn in (g1_fills, g2_sl_first, g3_costs, g4_funding, g5_pair,
               g6_resample, g7_indicators, g8_determinism, g9_no_lookahead):
        try:
            fn()
        except Exception as e:
            check(fn.__name__, "raised", False, f"{type(e).__name__}: {e}")
    bad = [r for r in RESULTS if not r[2]]
    print()
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} checks PASS")
    if bad:
        print("FAILED:")
        for g, nm, _, d in bad:
            print(f"  [{g}] {nm} {d}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
