#!/usr/bin/env python
"""_pack50d_audit.py -- known-answer audit for the DeepSeek fifty-prompt pack.

Groups 1-4 pin the shared execution machinery; groups 5-11 pin the
DeepSeek-pack-specific pieces: helper parity against the pack50b versions,
the new primitives (linreg slope/R2, MFI, OBV, Chikou timing, the 1h context
mapping), the uniform pack cost block, the no-crash / data-exists /
no-stopless-entry smoke of every runnable prompt, truncation invariance, and
the chunked-bootstrap parity.

    python code/_pack50d_audit.py          # exit 0 only if ALL PASS
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pack50_core as C
import pack50b_strats as SB
import pack50d_strats as SD

RESULTS = []


def check(group, name, ok, detail=""):
    RESULTS.append((group, name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {group:12s} {name}  {detail}")


def mkdf(o, h, l, c, start_ms=1600128000000, step_ms=60000):
    n = len(o)
    ts = start_ms + np.arange(n, dtype=np.int64) * step_ms
    return pd.DataFrame({"open_ts": ts,
                         "ts": pd.to_datetime(ts, unit="ms", utc=True),
                         "open": o, "high": h, "low": l,
                         "close": c, "volume": np.ones(n)})


def g1_fills():
    n = 8
    o = np.array([100, 101, 102, 103, 104, 105, 106, 107], float)
    df = mkdf(o, o + 0.5, o - 0.5, o.copy(), step_ms=3600000)
    plan = C.Plan(np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool))
    plan.long_entry[2] = True
    plan.long_exit[5] = True
    t = C.run_plan(df, plan, C.Costs(0.0, 0.0), None)["trades"].iloc[0]
    check("fills", "entry at next open", abs(t["entry_px"] - 103.0) < 1e-9)
    check("fills", "signal exit at next open", abs(t["exit_px"] - 106.0) < 1e-9)


def g2_sl_first():
    n = 5
    o = np.full(n, 100.0)
    h = np.array([100, 101, 120, 100, 100], float)
    l = np.array([100, 99, 80, 100, 100], float)
    c = np.array([100, 100, 100, 100, 100], float)
    df = mkdf(o, h, l, c, step_ms=3600000)
    plan = C.Plan(np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool))
    plan.long_entry[1] = True
    plan.stop_long = np.full(n, 90.0)
    plan.tp_long = np.full(n, 110.0)
    t = C.run_plan(df, plan, C.Costs(0.0, 0.0), None)["trades"].iloc[0]
    check("execution", "SL-first on a bar containing both", t["exit_reason"] == "stop")
    check("execution", "stop filled at the level", abs(t["exit_px"] - 90.0) < 1e-9)


def g3_costs_funding():
    n = 6
    o = np.full(n, 100.0)
    df = mkdf(o, o, o, o, step_ms=3600000)
    plan = C.Plan(np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool))
    plan.long_entry[1] = True
    plan.long_exit[3] = True
    r = C.run_plan(df, plan, C.Costs(10.0, 0.0), None, init_equity=10000.0)
    check("costs", "fee charged per side", abs(r["final_equity"] - (10000 - 20)) < 1e-6)
    f_ts = np.array([1600128000000 + 3 * 3600000], dtype=np.int64)
    r2 = C.run_plan(df, plan, C.Costs(0.0, 0.0), (f_ts, np.array([0.0001])), init_equity=10000.0)
    check("funding", "long pays a positive settlement",
          abs(r2["funding"] - 1.0) < 1e-6, f"funding={r2['funding']:.4f}")


def g4_resample(tmp="C:/Users/Lenovo/AppData/Local/Temp/opencode/_pd_1h.csv"):
    n = 96
    o = np.arange(100, 100 + n, dtype=float)
    ts = 1600128000000 + np.arange(n, dtype=np.int64) * 3600000   # 1h bars
    pd.DataFrame({"open_ts": ts, "open": o, "high": o + 2, "low": o - 1,
                  "close": o + 1, "volume": np.ones(n)}).to_csv(tmp, index=False)
    from pack50b_engine import load_base_tf
    a = C.load_tf(tmp, "4h")
    b = load_base_tf(tmp, "4h")
    check("resample", "1h -> 4h matches the core resampler",
          len(a) == len(b) == 24 and np.allclose(a["close"], b["close"]))
    d = load_base_tf(tmp, "1d")
    check("resample", "1h -> 1d gives four bars", len(d) == 4, f"n={len(d)}")
    os.remove(tmp)


def g5_helpers_parity():
    rng = np.random.default_rng(9)
    n = 400
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    t1, k1, a1, b1, sa1, sb1 = SD.ichimoku(h, l)
    t2, k2, a2, b2 = SB.ichimoku(h, l)
    check("parity", "ichimoku copy == pack50b version",
          all(np.allclose(x, y, equal_nan=True) for x, y in ((t1, t2), (k1, k2), (a1, a2), (b1, b2))))
    sr1 = SD.stoch_rsi(c)
    sr2 = SB.stoch_rsi(c)
    check("parity", "stoch_rsi copy == pack50b version",
          np.allclose(sr1[0], sr2[0], equal_nan=True) and np.allclose(sr1[1], sr2[1], equal_nan=True))
    v = np.abs(rng.normal(1, 0.1, n))
    check("parity", "obv copy == pack50b version",
          np.allclose(SD.obv(c, v), SB.obv(c, v)))
    # no-lookahead inside the copied ichimoku: senkou at bar i comes from i-26
    _, _, a_now, _, span_a, _ = SD.ichimoku(h, l)
    check("parity", "senkou A lags 26 bars", abs(a_now[200] - span_a[200 - 26]) < 1e-12)


def g6_new_primitives():
    # linreg: y = 2x exactly -> slope 2.0, R2 = 1
    line = 2.0 * np.arange(120, dtype=float) + 7.0
    slope, r2 = SD.linreg_slope_r2(line, 50)
    check("new-ind", "linreg slope of y=2x is 2 and R2 is 1",
          abs(slope[-1] - 2.0) < 1e-9 and abs(r2[-1] - 1.0) < 1e-9,
          f"slope={slope[-1]:.6f} r2={r2[-1]:.6f}")
    # MFI: pure up-moves on volume -> ~100; pure down -> ~0
    up = np.arange(1, 41, dtype=float)
    f_up = SD.mfi(up, up, up, np.ones(40), 14)
    f_dn = SD.mfi(up[::-1].copy(), up[::-1].copy(), up[::-1].copy(), np.ones(40), 14)
    check("new-ind", "MFI of monotone up is 100", abs(f_up[-1] - 100.0) < 1e-6, f"{f_up[-1]:.4f}")
    check("new-ind", "MFI of monotone down is 0", abs(f_dn[-1] - 0.0) < 1e-6, f"{f_dn[-1]:.4f}")
    # chikou timing: close vs close 26 bars ago, no future data
    c = np.arange(1, 61, dtype=float)
    chikou_up = c > SD._roll(c, 26)
    check("new-ind", "chikou filter = close vs close 26 bars ago",
          bool(chikou_up[30]) and not chikou_up[:26].any())
    # swing structure: P10 on a clean up-down path finds and breaks pivots
    rng = np.random.default_rng(2)
    n = 600
    c2 = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o2 = np.concatenate(([c2[0]], c2[:-1]))
    h2 = np.maximum(o2, c2) * (1 + np.abs(rng.normal(0, 0.002, n)))
    l2 = np.minimum(o2, c2) * (1 - np.abs(rng.normal(0, 0.002, n)))
    df2 = mkdf(o2, h2, l2, c2)
    plan = SD.p10(df2)
    check("new-ind", "P10 builds and fires on random walks",
          plan.long_entry.dtype == bool and int(plan.long_entry.sum()) > 0,
          f"le={int(plan.long_entry.sum())} se={int(plan.short_entry.sum())}")
    # session windows
    df3 = mkdf(np.full(100, 100.0), np.full(100, 101.0), np.full(100, 99.0),
               np.full(100, 100.0))
    mod = SD._mod(df3)
    check("new-ind", "minute-of-day grid from midnight", mod[0] == 0 and mod[61] == 61)


def g7_costs_block():
    ok = all(SD.costs_for(s, t) == (5.0, 2.0) for s, t in
             (("BTCUSDT", "1m"), ("SPCX", "15m"), ("JUPUSDT", "4h"), ("NVDA", "5m")))
    check("cost-block", "DeepSeek block is 5.0 fee / 2.0 slip for every prompt", ok)


def g8_smoke_and_data():
    import vrun
    rng = np.random.default_rng(3)
    n = 900
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.002, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.002, n)))
    df = mkdf(o, h, l, c)
    db = mkdf(o * 2, h * 2, l * 2, c * 2)
    ctx = {"ema50_1h_slope": np.ones(n, bool), "st_1h_dir": np.ones(n, int),
           "adx_1h": np.full(n, 30.0)}
    bad = 0
    for sid in sorted(SD.SPECS):
        spec = SD.SPECS[sid]
        code = SD.CODE[sid]
        if spec.get("no_data"):
            check("smoke", f"{code} is NO DATA", spec.get("build") is None
                  and spec.get("build2") is None and "pair" not in spec)
            continue
        try:
            paths = vrun._pack50d_inputs(spec["tf"], spec["sym"])
            missing = [p for p in paths if p.endswith(".csv") and not os.path.exists(p)]
            check("smoke", f"{code} data files exist", not missing, f"{missing}")
        except Exception as e:
            check("smoke", f"{code} data mapping", False, f"{type(e).__name__}: {e}")
            bad += 1
            continue
        try:
            if "pair" in spec:
                tgt, note = spec["pair"](df, db)
                ok = len(tgt) == n and set(np.unique(tgt)).issubset({-1, 0, 1})
                check("smoke", f"{code} pair target on synthetic data", ok,
                      f"states={sorted(set(np.unique(tgt)))}")
                continue
            if "build2" in spec:
                plan = spec["build2"](df, db)
            elif sid in (35, 50):
                plan = spec["build"](df, ctx)
            else:
                plan = spec["build"](df)
            sl = plan.stop_long if plan.stop_long is not None else np.full(n, np.nan)
            ss = plan.stop_short if plan.stop_short is not None else np.full(n, np.nan)
            bad_le = plan.long_entry & ~np.isfinite(sl)
            bad_se = plan.short_entry & ~np.isfinite(ss)
            ok = (len(plan.long_entry) == n and plan.long_entry.dtype == bool
                  and not bad_le.any() and not bad_se.any())
            check("smoke", f"{code} clean Plan, no stopless entries", ok)
        except Exception as e:
            check("smoke", f"{code} build raised", False, f"{type(e).__name__}: {e}")


def g9_truncation():
    rng = np.random.default_rng(23)
    n, cut = 900, 700
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.002, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.002, n)))
    ts = 1600128000000 + np.arange(n, dtype=np.int64) * 60000
    full = pd.DataFrame({"open_ts": ts,
                         "ts": pd.to_datetime(ts, unit="ms", utc=True),
                         "open": o, "high": h, "low": l, "close": c,
                         "volume": np.ones(n)})
    short = full.iloc[:cut].reset_index(drop=True)
    ctx_s = {"ema50_1h_slope": np.ones(cut, bool), "st_1h_dir": np.ones(cut, int),
             "adx_1h": np.full(cut, 30.0)}
    ctx_f = {"ema50_1h_slope": np.ones(n, bool), "st_1h_dir": np.ones(n, int),
             "adx_1h": np.full(n, 30.0)}
    bad = 0
    for sid in (1, 5, 9, 16, 21, 25, 33, 41, 45, 49, 50):
        spec = SD.SPECS[sid]
        p1 = spec["build"](short, ctx_s) if sid in (35, 50) else spec["build"](short)
        p2 = spec["build"](full, ctx_f) if sid in (35, 50) else spec["build"](full)
        for name in ("long_entry", "short_entry", "long_exit", "short_exit"):
            a1 = getattr(p1, name)
            a2 = getattr(p2, name)[:cut]
            if not np.array_equal(a1, a2):
                bad += 1
                check("truncation", f"{SD.CODE[sid]}.{name} moves with prepended history",
                      False, f"n_diff={int((a1 != a2).sum())}")
    if bad == 0:
        check("truncation", "signals invariant to prepended history (11 builds x 4 arrays)", True)


def g10_chunked_parity():
    from pack50d_engine import _expectancy_lb_chunked
    import gate2 as G2
    rng = np.random.default_rng(4)
    for n in (50, 500, 5000):
        r = rng.normal(0.0003, 0.01, n)
        a = _expectancy_lb_chunked(r, n_boot=400, seed=11)[0]
        b = G2.expectancy_lb_bps(r, n_boot=400, seed=11)[0]
        check("chunked", f"chunked == unchunked bootstrap at n={n}", abs(a - b) < 1e-12,
              f"{a:.6f} vs {b:.6f}")


def main() -> int:
    for fn in (g1_fills, g2_sl_first, g3_costs_funding, g4_resample,
               g5_helpers_parity, g6_new_primitives, g7_costs_block,
               g8_smoke_and_data, g9_truncation, g10_chunked_parity):
        try:
            fn()
        except Exception as e:
            check(fn.__name__, "raised", False, f"{type(e).__name__}: {e}")
    bad = [r for r in RESULTS if not r[2]]
    print()
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} checks PASS")
    if bad:
        for g, nm, _, d in bad:
            print(f"  [{g}] {nm} {d}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
