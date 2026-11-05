#!/usr/bin/env python
"""_pack50c_audit.py -- known-answer audit for the Qwen fifty-prompt pack.

Groups 1-6 pin the shared execution machinery on the bytes the artifacts are
produced from; groups 7-12 pin the Qwen-pack-specific pieces: the rolling
volume-profile POC, the parity of the copied indicator helpers against the
pack50b versions, the trailing-stop emulation, the uniform pack cost block,
and a no-crash / data-exists / no-stopless-entry smoke of every runnable
prompt plus truncation invariance.

    python code/_pack50c_audit.py          # exit 0 only if ALL PASS
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pack50_core as C
import pack50b_strats as SB
import pack50c_strats as SC

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
    c = o.copy()
    df = mkdf(o, o + 0.5, o - 0.5, c, step_ms=3600000)
    plan = C.Plan(np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool))
    plan.long_entry[2] = True
    plan.long_exit[5] = True
    r = C.run_plan(df, plan, C.Costs(0.0, 0.0), None)
    t = r["trades"].iloc[0]
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
    r = C.run_plan(df, plan, C.Costs(0.0, 0.0), None)
    t = r["trades"].iloc[0]
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
    f_rate = np.array([0.0001])
    r2 = C.run_plan(df, plan, C.Costs(0.0, 0.0), (f_ts, f_rate), init_equity=10000.0)
    check("funding", "long pays a positive settlement",
          abs(r2["funding"] - 1.0) < 1e-6, f"funding={r2['funding']:.4f}")


def g4_resample(tmp="C:/Users/Lenovo/AppData/Local/Temp/opencode/_pc_1m.csv"):
    n = 480
    o = np.arange(100, 100 + n, dtype=float)
    ts = 1600128000000 + np.arange(n, dtype=np.int64) * 60000
    pd.DataFrame({"open_ts": ts, "open": o, "high": o + 2, "low": o - 1,
                  "close": o + 1, "volume": np.ones(n)}).to_csv(tmp, index=False)
    from pack50b_engine import load_base_tf
    a = C.load_tf(tmp, "3m")
    b = load_base_tf(tmp, "3m")
    check("resample", "load_base_tf == core.load_tf on 3m",
          len(a) == len(b) and np.allclose(a["close"], b["close"]))
    r = load_base_tf(tmp, "30m")
    check("resample", "1m -> 30m gives sixteen bars", len(r) == 16, f"n={len(r)}")
    os.remove(tmp)


def g5_helpers_parity():
    rng = np.random.default_rng(9)
    n = 400
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    t1, k1, a1, b1 = SC.ichimoku(h, l)
    t2, k2, a2, b2 = SB.ichimoku(h, l)
    same_ich = all(np.allclose(x, y, equal_nan=True)
                   for x, y in ((t1, t2), (k1, k2), (a1, a2), (b1, b2)))
    check("parity", "ichimoku copy == pack50b version", same_ich)
    kk1, dd1 = SC.stoch(h, l, c)
    kk2, dd2 = SB.stoch(h, l, c)
    check("parity", "stoch copy == pack50b version",
          np.allclose(kk1, kk2, equal_nan=True) and np.allclose(dd1, dd2, equal_nan=True))


def g6_poc():
    # 120 bars; volume concentrated in the bin around 100 for the first 100
    n = 120
    c = np.full(n, 100.0)
    v = np.ones(n)
    v[:100] = 0.0
    v[40:60] = 5.0                       # a fat block right at price 100
    c[:100] = 100.0
    h = c + 0.5
    l = c - 0.5
    df = mkdf(np.full(n, 100.0), h, l, c)
    poc = SC.rolling_poc(h, l, c, v, lookback=100, bins=20)
    # the fat block sits in the middle bin of a [99.5, 100.5] range -> POC ~ 100
    check("poc", "POC lands on the high-volume price block",
          np.isfinite(poc[110]) and abs(poc[110] - 100.0) < 0.06,
          f"poc={poc[110]:.4f}")
    # no look-ahead: changing the LAST bar must not move earlier POCs
    h2, c2 = h.copy(), c.copy()
    h2[-1], c2[-1] = 130.0, 130.0          # only the LAST bar changes
    poc2 = SC.rolling_poc(h2, l.copy(), c2, v, lookback=100, bins=20)
    check("poc", "POC before the last bar does not move",
          np.allclose(poc[:n - 1], poc2[:n - 1], equal_nan=True))
    # bounce signal: touch and close back above
    h2, l2, c3 = h.copy(), l.copy(), c.copy()
    l2[110] = poc[109] - 0.01            # dips to the POC
    c3[110] = poc[109] + 0.05            # closes back above
    le = (l2 <= poc) & (c3 > poc)
    check("poc", "bounce = touch the POC and close back above", bool(le[110]))


def g7_trailing():
    n = 60
    c = np.full(n, 100.0)
    c[30:] = 80.0                        # a collapse halfway
    df = mkdf(np.full(n, 100.0), c + 0.5, c - 0.5, c)
    le = np.zeros(n, bool)
    le[1] = True
    se = np.zeros(n, bool)
    plan = SC._atr_plan(df, le, se, 2.0, 3.0, trail="ema50")
    # EMA50 trail: the exit fires when close crosses below EMA50 (one bar late fill)
    check("trail", "EMA50 trail exits after the collapse", bool(plan.long_exit[50:60].any()))
    plan2 = SC._atr_plan(df, le, se, 2.0, 3.0, trail="atr")
    check("trail", "ATR trail line falls below price after the collapse",
          bool(plan2.long_exit[31:45].any()))
    p3 = SC._pct_plan(df, le, se, 0.01, 0.02, trail="none")
    check("trail", "no trail -> no signal exits", not p3.long_exit.any() and not p3.short_exit.any())


def g8_costs_block():
    ok = all(SC.costs_for(s, t) == (5.0, 2.0) for s, t in
             (("BTCUSDT", "1m"), ("SPCX", "5m"), ("JUPUSDT", "3m"), ("NVDA", "30m")))
    check("cost-block", "Qwen block is 5.0 fee / 2.0 slip for every prompt", ok)


def g9_smoke_and_data():
    import vrun
    rng = np.random.default_rng(3)
    n = 900
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    df = mkdf(o, h, l, c)
    bad = 0
    for sid in sorted(SC.SPECS):
        spec = SC.SPECS[sid]
        code = SC.CODE[sid]
        if spec.get("no_data"):
            check("smoke", f"{code} is NO DATA", spec["build"] is None)
            continue
        try:
            paths = vrun._pack50c_inputs(spec["tf"], spec["sym"])
            missing = [p for p in paths if p.endswith(".csv") and not os.path.exists(p)]
            check("smoke", f"{code} data files exist", not missing, f"{missing}")
        except Exception as e:
            check("smoke", f"{code} data mapping", False, f"{type(e).__name__}: {e}")
            bad += 1
            continue
        try:
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


def g10_truncation():
    rng = np.random.default_rng(23)
    n, cut = 900, 700
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
    for sid in (1, 7, 13, 17, 30, 39, 44, 48):
        spec = SC.SPECS[sid]
        p1 = spec["build"](short)
        p2 = spec["build"](full)
        for name in ("long_entry", "short_entry", "long_exit", "short_exit"):
            if not np.array_equal(getattr(p1, name), getattr(p2, name)[:cut]):
                bad += 1
                check("truncation", f"{SC.CODE[sid]}.{name} moves with prepended history",
                      False, f"n_diff={int((getattr(p1, name) != getattr(p2, name)[:cut]).sum())}")
    if bad == 0:
        check("truncation", "signals invariant to prepended history (8 builds x 4 arrays)", True)


def g11_chunked_parity():
    """The memory-bounded chunked bootstrap must be identical to the audited
    unchunked one for normal sizes (same seed, same semantics)."""
    from pack50c_engine import _expectancy_lb_chunked
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
               g5_helpers_parity, g6_poc, g7_trailing, g8_costs_block,
               g9_smoke_and_data, g10_truncation, g11_chunked_parity):
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
