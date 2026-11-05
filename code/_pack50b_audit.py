#!/usr/bin/env python
"""_pack50b_audit.py -- known-answer audit for the claude2 fifty-prompt pack.

Nothing in the pack50b report is trusted until every group here passes.
Groups 1-9 pin the shared execution machinery (fills, tie-breaks, fees,
funding sign, pair leg split, resampler, indicators, determinism, causality)
on the same bytes the artifacts are produced from. Groups 10-14 pin the
claude2-specific pieces: the new indicators, the uniform pack cost block, the
file-name-driven resampler used for SPX, the stateful pair targets, and a
no-crash smoke of every runnable prompt against synthetic data plus a check
that every runnable prompt's data files exist.

    python code/_pack50b_audit.py          # exit 0 only if ALL PASS
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pack50_core as C
import pack50b_strats as SB

RESULTS = []


def check(group, name, ok, detail=""):
    RESULTS.append((group, name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {group:12s} {name}  {detail}")


def mkdf(o, h, l, c, start_ms=1600000000000, step_ms=3600000):
    n = len(o)
    ts = start_ms + np.arange(n, dtype=np.int64) * step_ms
    return pd.DataFrame({"open_ts": ts,
                         "ts": pd.to_datetime(ts, unit="ms", utc=True),
                         "open": o, "high": h, "low": l,
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
    expect = 10000.0 - 10000.0 * 0.0010 - 10000.0 * 0.0010
    check("costs", "fee charged per side", abs(r["final_equity"] - expect) < 1e-6,
          f"final={r['final_equity']:.6f} expect={expect:.6f}")
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
    expect = 10000.0 * (1 + 0.5 * 0.01) ** (n - 2)
    check("pairs", "dollar-neutral 50/50 leg split",
          abs(r["final_equity"] - expect) / expect < 1e-6,
          f"final={r['final_equity']:.2f} expect={expect:.2f}")
    r2 = C.run_pair(da, db, -target, C.Costs(0.0, 0.0), None, None, init_equity=10000.0)
    expect2 = 10000.0 * (1 - 0.5 * 0.01) ** (n - 2)
    check("pairs", "inverse target loses what the first made",
          abs(r2["final_equity"] - expect2) / expect2 < 1e-6,
          f"final={r2['final_equity']:.2f} expect={expect2:.2f}")
    oa2 = np.array([100.0, 100.0, 100.0, 100.0])
    ca2 = np.array([100.0, 110.0, 110.0, 110.0])
    d2a = mkdf(oa2, oa2, oa2, ca2)
    d2b = mkdf(np.full(4, 50.0), np.full(4, 50.0), np.full(4, 50.0), np.full(4, 50.0))
    r3 = C.run_pair(d2a, d2b, np.ones(4), C.Costs(0.0, 0.0), None, None, init_equity=10000.0)
    check("pairs", "entry bar earns from its own open",
          abs(r3["final_equity"] - 10500.0) < 1e-6, f"final={r3['final_equity']:.2f}")


# ─────────────────────────────────────────────────────── group 6: resampler
def g6_resample(tmp="C:/Users/Lenovo/AppData/Local/Temp/opencode/_pb_1m.csv"):
    n = 480
    o = np.arange(100, 100 + n, dtype=float)
    ts = 1600128000000 + np.arange(n, dtype=np.int64) * 60000   # 1m bars from 00:00 UTC
    pd.DataFrame({"open_ts": ts, "open": o, "high": o + 2, "low": o - 1,
                  "close": o + 1, "volume": np.ones(n)}).to_csv(tmp, index=False)
    d = C.load_tf(tmp, "4h")
    check("resample", "core resampler unchanged", len(d) == 2, f"n={len(d)}")
    # 3m has a 1m base in the core's own mapping, so the two loaders must agree
    a = C.load_tf(tmp, "3m")
    b = SB_LOAD(tmp, "3m")
    same = (len(a) == len(b) and np.allclose(a["open"], b["open"]) and
            np.allclose(a["close"], b["close"]) and
            np.allclose(a["open_ts"], b["open_ts"]))
    check("resample", "load_base_tf == core.load_tf on 3m", same,
          f"n_core={len(a)} n_base={len(b)}")
    # 15m/30m: the core expects native 15m files, so pin load_base_tf directly
    for tf, want, wmin in (("15m", 32, 15), ("30m", 16, 30)):
        r = SB_LOAD(tmp, tf)
        ok = (len(r) == want and abs(r["open"].iloc[0] - 100.0) < 1e-9 and
              abs(r["high"].iloc[0] - np.max(o[:wmin] + 2)) < 1e-9 and
              abs(r["close"].iloc[-1] - (o[-1] + 1)) < 1e-9)
        check("resample", f"load_base_tf resamples 1m -> {tf} ({want} bars)", ok,
              f"n={len(r)}")
    os.remove(tmp)


def SB_LOAD(path, tf):
    from pack50b_engine import load_base_tf
    return load_base_tf(path, tf)


# ─────────────────────────────────────────────────────── group 7: indicators
def g7_indicators():
    c = np.arange(1, 60, dtype=float)
    r = C.rsi(c, 14)
    check("indicators", "RSI of a monotone ramp is 100", abs(r[-1] - 100.0) < 1e-6,
          f"rsi={r[-1]:.6f}")
    h = np.full(40, 101.0)
    l = np.full(40, 99.0)
    cc = np.full(40, 100.0)
    a = C.atr(h, l, cc, 14)
    check("indicators", "ATR of a constant 2.0 range", abs(a[-1] - 2.0) < 1e-9,
          f"atr={a[-1]:.6f}")
    e = C.ema(c, 10)
    check("indicators", "EMA starts where the window is full", np.isnan(e[8]) and not np.isnan(e[9]))


# ─────────────────────────────────────────────────────── group 8: determinism
def g8_determinism():
    rng = np.random.default_rng(7)
    n = 400
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.003
    l = np.minimum(o, c) * 0.997
    df = mkdf(o, h, l, c)
    a = C.run_plan(df, SB.s01(df), C.Costs(5.0, 2.0), None)
    b = C.run_plan(df, SB.s01(df), C.Costs(5.0, 2.0), None)
    same = (a["final_equity"] == b["final_equity"] and
            len(a["trades"]) == len(b["trades"]))
    check("determinism", "same input -> same equity and trade count", same,
          f"eq={a['final_equity']:.6f} n={len(a['trades'])}")


# ─────────────────────────────────────────────────────── group 9: no look-ahead
def g9_no_lookahead():
    rng = np.random.default_rng(11)
    n = 300
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.003
    l = np.minimum(o, c) * 0.997
    df = mkdf(o, h, l, c)
    p1 = SB.s01(df)
    df2 = df.copy()
    df2.loc[n - 1, ["open", "high", "low", "close"]] = [1e6, 1e6, 1e6, 1e6]
    p2 = SB.s01(df2)
    ok = np.array_equal(p1.long_entry[:n - 1], p2.long_entry[:n - 1])
    check("causality", "signals before the last bar do not move", ok)


# ─────────────────────────────── group 10: the new claude2 primitives
def g10_new_indicators():
    h = np.arange(10, 130, dtype=float)          # monotone up
    l = h - 1.0
    c = h                                        # close prints at the high
    k, d = SB.stoch(h, l, c, 14, 3, 3)
    check("new-ind", "stoch %K with close at the high is 100", abs(k[-1] - 100.0) < 1e-9,
          f"k={k[-1]:.6f}")
    check("new-ind", "%D is the smoothed %K", abs(d[-1] - 100.0) < 1e-9, f"d={d[-1]:.6f}")
    # CCI known answer: nineteen flats and one spike 30 above the mean 1.5
    flat = np.full(40, 100.0)
    spike = np.concatenate([flat, [130.0]])
    x = SB.cci(spike, spike, spike, 20)
    check("new-ind", "CCI known answer on a 19-flat + 30 spike",
          abs(x[-1] - 666.6667) < 1e-3, f"cci={x[-1]:.4f}")
    cs = np.array([10.0, 11.0, 10.0, 11.0])
    ob = SB.obv(cs, np.ones(4))
    check("new-ind", "OBV accumulates signed volume",
          np.allclose(ob, [0.0, 1.0, 0.0, 1.0]), f"ob={ob}")
    perfect = np.arange(200, dtype=float)          # exactly linear
    mom = SB.linreg_mom(perfect, 12)
    check("new-ind", "linreg residual of a perfect line is 0",
          np.nanmax(np.abs(mom[11:])) < 1e-6, f"max={np.nanmax(np.abs(mom[11:])):.9f}")
    tenkan, kijun, sa, sb = SB.ichimoku(h, l)
    # kijun over the 26 bars ending at 35 (bars 10..35) is that window's mid-range
    expect = (h[35] + l[10]) / 2.0
    check("new-ind", "Kijun(26) at bar 35 = mid of bars 10..35",
          abs(kijun[35] - expect) < 1e-9, f"kijun={kijun[35]:.4f} expect={expect:.4f}")
    # the cloud plotted at bar 61 was computed from bars 9..34 (26-bar lag)
    expect_a = (tenkan[35] + kijun[35]) / 2.0
    check("new-ind", "Senkou A at bar 61 lags 26 bars",
          abs(sa[61] - expect_a) < 1e-9, f"sa={sa[61]:.4f}")
    df = mkdf(np.full(100, 100.0), np.full(100, 101.0), np.full(100, 99.0),
              np.full(100, 100.0), start_ms=1600128000000, step_ms=60000)
    mod = SB._minute_of_day(df)
    check("new-ind", "minute-of-day grid from midnight", mod[0] == 0 and mod[61] == 61,
          f"mod={mod[0]},{mod[61]}")


# ─────────────────────────────── group 11: the pack cost block
def g11_costs_block():
    ok = all(SB.costs_for(sym, tf) == (5.0, 2.0)
             for sym, tf in [("BTCUSDT", "1m"), ("JUPUSDT", "5m"),
                             ("SUIUSDT", "3m"), ("SPXUSDT", "15m"),
                             ("ETHUSDT+BTCUSDT", "1h")])
    check("cost-block", "claude2 block is 5.0 fee / 2.0 slip for every prompt", ok)


# ─────────────────────────────── group 12: stateful pair targets
def g12_pair_targets():
    z = np.array([0.0, -1.0, -2.5, -1.0, 0.5, 2.5, 3.6, 1.0, -3.0, -2.2])
    t = SB.zscore_pair_target(z, 2.0, 3.5, 48)
    check("pair-tgt", "entry at z <= -2", t[2] == 1, f"t={t}")
    check("pair-tgt", "zero-cross exits", t[4] == 0, f"t={t}")
    check("pair-tgt", "entry at z >= +2", t[5] == -1, f"t={t}")
    check("pair-tgt", "beyond the stop the book is flat (p27 override)",
          t[6] == 0, f"t={t}")
    check("pair-tgt", "re-entry once back inside the stop",
          t[8] == 1 and t[9] == 1, f"t={t}")
    z2 = np.full(60, -2.5)
    t2 = SB.zscore_pair_target(z2, 2.0, 3.5, 48)
    check("pair-tgt", "time stop flattens after 48 bars held",
          t2[46] == 1 and t2[47] == 0 and t2[48] == 1, f"t[46:49]={t2[46:49]}")

    n = 10
    r = np.array([100.0, 98.0, 97.5, 99.0, 100.0, 102.5, 101.0, 100.5, 103.2, 99.8])
    bl, bm, bu, sd = (np.full(n, v) for v in (98.0, 100.0, 102.0, 1.0))
    t3 = SB.bband_pair_target(r, bl, bm, bu, sd)
    check("pair-tgt", "bband long below the lower band", t3[1] == 1, f"t={t3}")
    check("pair-tgt", "bband take profit at the middle band", t3[4] == 0, f"t={t3}")
    check("pair-tgt", "bband short above the upper band", t3[5] == -1, f"t={t3}")
    check("pair-tgt", "bband 3-sd stop overrides (r 3.2 above the mean)",
          t3[8] == 0, f"t={t3}")

    r4 = 100.0 + 0.1 * np.arange(14)
    e20 = np.array([0.0] * 5 + [1.0] * 9)
    e50 = np.full(14, 0.5)
    a4 = np.full(14, 1.0)
    t4 = SB.trend_pair_target(r4, e20, e50, a4)
    check("pair-tgt", "trend pair enters on the cross up", t4[5] == 1, f"t={t4}")
    r5 = r4.copy()
    r5[9] = r4[5] - 3.0                  # 3 ATR below the entry
    t5 = SB.trend_pair_target(r5, e20, e50, a4)
    check("pair-tgt", "trend pair ratio stop flattens", t5[9] == 0, f"t={t5}")
    e20b = np.array([1.0] * 5 + [0.0] * 9)
    e50b = np.full(14, 0.5)
    t6 = SB.trend_pair_target(r4, e20b, e50b, a4)
    check("pair-tgt", "trend pair enters short on the cross down", t6[5] == -1, f"t={t6}")


def _fin(a):
    """A level the prompt does not define is None, and None is correct, not dirty."""
    if a is None:
        return True
    a = np.asarray(a, float)
    return bool(np.all(np.isfinite(a[~np.isnan(a)])))


# ─────────────────────────────── group 13: every runnable prompt exists
def g13_data_and_smoke(tmp="C:/Users/Lenovo/AppData/Local/Temp/opencode/_pbsmk.csv"):
    import vrun
    rng = np.random.default_rng(3)
    n = 900
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    df = mkdf(o, h, l, c, step_ms=60000)
    db = mkdf(o * 0.5, h * 0.5, l * 0.5, c * 0.5, step_ms=60000)
    bad = 0
    for sid in sorted(SB.SPECS):
        spec = SB.SPECS[sid]
        code = SB.CODE[sid]
        if spec.get("no_data"):
            check("smoke", f"{code} is NO DATA", spec["build"] is None)
            continue
        try:
            paths = vrun._pack50b_inputs(spec["tf"], spec["sym"])
            missing = [p for p in paths if p.endswith(".csv") and not os.path.exists(p)]
            check("smoke", f"{code} data files exist", not missing, f"{missing}")
        except Exception as e:
            check("smoke", f"{code} data mapping", False, f"{type(e).__name__}: {e}")
            bad += 1
            continue
        try:
            if "pair" in spec:
                tgt, note = spec["pair"](df, db)
                ok = (len(tgt) == len(df) and set(np.unique(tgt)).issubset({-1, 0, 1}))
                check("smoke", f"{code} pair target on synthetic data", ok,
                      f"n={len(tgt)} states={sorted(set(np.unique(tgt)))}")
            else:
                plan = spec["build"](df, {"ema50_1h_slope": np.ones(len(df), bool)}) \
                    if sid == 10 else spec["build"](df)
                ok = (len(plan.long_entry) == len(df) and
                      plan.long_entry.dtype == bool and
                      _fin(plan.stop_long) and _fin(plan.stop_short) and
                      _fin(plan.tp_long) and _fin(plan.tp_short))
                check("smoke", f"{code} builds a clean Plan on synthetic data", ok)
        except Exception as e:
            check("smoke", f"{code} build raised", False, f"{type(e).__name__}: {e}")


# ─────────────────────────────── group 14: no stopless entries (warmup bug)
def g14_no_nan_stop_entries():
    """An entry on a bar whose stop level is NaN produces a stopless position
    (S02's negated-NaN downtrend gate did exactly that). Every entry bar must
    carry a finite stop, and no entry may fire before the indicators warm up."""
    rng = np.random.default_rng(5)
    n = 900
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    df = mkdf(o, h, l, c, step_ms=60000)
    bad = 0
    for sid in sorted(SB.SPECS):
        spec = SB.SPECS[sid]
        if spec.get("no_data") or "pair" in spec:
            continue
        plan = spec["build"](df, {"ema50_1h_slope": np.ones(n, bool)}) \
            if sid == 10 else spec["build"](df)
        sl = plan.stop_long if plan.stop_long is not None else np.full(n, np.nan)
        ss = plan.stop_short if plan.stop_short is not None else np.full(n, np.nan)
        bad_le = plan.long_entry & ~np.isfinite(sl)
        bad_se = plan.short_entry & ~np.isfinite(ss)
        if bad_le.any() or bad_se.any():
            bad += 1
            check("warmup", f"{SB.CODE[sid]} entry with a NaN stop", False,
                  f"le@{np.where(bad_le)[0][:3]} se@{np.where(bad_se)[0][:3]}")
    if bad == 0:
        check("warmup", "every entry bar carries a finite stop", True)


# ─────────────────────────────── group 15: truncation invariance
def g15_truncation_invariance():
    """Signals computed on data[:T] must equal the signals computed on a LONGER
    frame restricted to the first T bars. Recursive indicators (EMA) carry a
    warmup-seed effect that decays geometrically; a real mismatch here means a
    frame-relative anchor (the classic higher-timeframe merge on open_time)."""
    rng = np.random.default_rng(23)
    n, cut, extra = 900, 700, 200
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    ts = 1600128000000 + np.arange(n, dtype=np.int64) * 60000
    full = pd.DataFrame({"open_ts": ts,
                         "ts": pd.to_datetime(ts, unit="ms", utc=True),
                         "open": o, "high": h, "low": l, "close": c,
                         "volume": np.ones(n)})
    short = full.iloc[:cut].reset_index(drop=True)
    bad = 0
    for sid in (1, 5, 7, 11, 20, 34, 44, 48):
        spec = SB.SPECS[sid]
        p1 = spec["build"](short, {"ema50_1h_slope": np.ones(cut, bool)}) \
            if sid == 10 else spec["build"](short)
        p2 = spec["build"](full, {"ema50_1h_slope": np.ones(n, bool)}) \
            if sid == 10 else spec["build"](full)
        for name in ("long_entry", "short_entry", "long_exit", "short_exit"):
            a1 = getattr(p1, name)
            a2 = getattr(p2, name)[:cut]
            if not np.array_equal(a1, a2):
                bad += 1
                check("truncation", f"{SB.CODE[sid]}.{name} changes when history is prepended",
                      False, f"n_diff={int((a1 != a2).sum())}")
    if bad == 0:
        check("truncation", "signals invariant to prepended history (8 builds x 4 arrays)", True)


def main() -> int:
    for fn in (g1_fills, g2_sl_first, g3_costs, g4_funding, g5_pair,
               g6_resample, g7_indicators, g8_determinism, g9_no_lookahead,
               g10_new_indicators, g11_costs_block, g12_pair_targets,
               g13_data_and_smoke, g14_no_nan_stop_entries,
               g15_truncation_invariance):
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
