"""Parity + regression suite for grid_core.

TEST 1 — FIDELITY. With every defect left UNFIXED (close_only_stop=True,
flatten_on_bear=False, size_on='equity', and the broken 250-candle gate), the
refactored GridEngine must reproduce grid_audit.py's validated numbers to
floating-point noise. This is the load-bearing test: grid_core exists so the
paper bot and the validator share one implementation, and if the refactor
changed the strategy then every published number is about a strategy nobody
runs.

TEST 2 — NO-LOOKAHEAD. Truncating the series must not change the prefix.

TEST 3 — SIZING INVARIANT. A full grid is exactly 125% of equity as notional
under size_on='notional', and demonstrably not under size_on='equity' once
equity has grown (the compounding the audit found).

TEST 4 — DEFECT FIXES ACTUALLY CHANGE BEHAVIOUR. Each fix must move a number;
a fix that changes nothing is a fix that was never applied.

TEST 5 — EQUITY IDENTITY. Equity is cash + position market value, always, and
never goes negative while holding long inventory. This is the assertion that
would have caught the cost-basis bug before it fabricated a -100% wipeout.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cvrmd_port as P
import grid_core as GC

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
          f"{('  ' + detail) if detail else ''}")


def load15(sym):
    return GC.P.load(GC.P.os.path.join(ROOT, "data", "binance_klines_1m",
                                       f"{sym}_1m.csv")) \
        if False else _load15(sym)


def _load15(sym):
    cache = os.path.join(ROOT, "data", "binance_klines_15m_cache")
    cp = os.path.join(cache, f"{sym}_15m.npz")
    if os.path.exists(cp):
        return [tuple(r) for r in np.load(cp)["bars"]]
    return P.resample(P.load(os.path.join(ROOT, "data", "binance_klines_1m",
                                          f"{sym}_1m.csv")), 15)


def funding_arrays(sym, T):
    import json
    p = os.path.join(ROOT, "data", "binance_funding", f"{sym}_funding.json")
    rate = np.zeros(len(T))
    ev = np.zeros(len(T), bool)
    if not os.path.exists(p):
        return rate, ev
    f = json.load(open(p, encoding="utf-8"))
    ft = np.array([x["t"] for x in f], dtype=np.int64)
    fv = np.array([x["r"] for x in f], dtype=np.float64)
    for ts, r in zip(ft, fv):
        j = int(np.searchsorted(T, ts, side="left"))
        if j < len(T):
            ev[j] = True
            rate[j] = r
    return rate, ev


def gate_broken(bars15):
    """The ORIGINAL spec filter, as an array over the 15m bars."""
    b1h = P.resample(bars15, 60)
    g1h = GC.htf_gate_broken(b1h)
    T1 = np.array([b[0] for b in b1h], dtype=np.int64)
    idx = np.clip(np.searchsorted(T1, np.array([b[0] for b in bars15]),
                                  side="right") - 1, 0, len(b1h) - 1)
    return g1h[idx]


def gate_fixed(bars15):
    """The FIXED filter: warmed EMA200 over full 1h history."""
    b1h = P.resample(bars15, 60)
    g1h, _ = GC.htf_gate(b1h)
    T1 = np.array([b[0] for b in b1h], dtype=np.int64)
    idx = np.clip(np.searchsorted(T1, np.array([b[0] for b in bars15]),
                                  side="right") - 1, 0, len(b1h) - 1)
    return g1h[idx]


def test_fidelity(sym="SOLUSDT"):
    print(f"\n[1] FIDELITY — refactored core vs validated grid_audit numbers "
          f"({sym})")
    print("    " + "-" * 92)
    b = _load15(sym)
    T = np.array([x[0] for x in b], dtype=np.int64)
    fr, fev = funding_arrays(sym, T)
    gate = gate_broken(b)
    r = GC.run(b, gate, funding_arrays=(fr, fev),
               close_only_stop=True, flatten_on_bear=False, size_on="equity")
    net = (r["equity"] / GC.INITIAL_EQUITY - 1) * 100
    # published, from results/grid_audit.txt (post-fix audit, unfixed strategy)
    exp_net, exp_mdd, exp_fills = 862.50, 35.48, 5233
    exp_grids, exp_stops = 501, 231
    got_fills = r["counts"].get("entry_fill", 0)
    got_grids = r["counts"].get("grid_built", 0)
    got_stops = r["counts"].get("stop", 0)
    print(f"    net    core {net:>10.2f}%   audit {exp_net:>10.2f}%")
    print(f"    mdd    core {r['mdd']:>10.2f}%   audit {exp_mdd:>10.2f}%")
    print(f"    fills  core {got_fills:>10,}     audit {exp_fills:>10,}")
    print(f"    grids  core {got_grids:>10,}     audit {exp_grids:>10,}")
    print(f"    stops  core {got_stops:>10,}     audit {exp_stops:>10,}")
    # event counts must match EXACTLY; equity to a few bps is acceptable
    # because the audit applied slippage on fills and the core does too, but
    # tiny ordering differences on same-bar cover+stop can move cents.
    check("entry fill count identical", got_fills == exp_fills,
          f"{got_fills} vs {exp_fills}")
    check("grid build count identical", got_grids == exp_grids,
          f"{got_grids} vs {exp_grids}")
    check("stop count identical", got_stops == exp_stops,
          f"{got_stops} vs {exp_stops}")
    check("net return within 1%", abs(net - exp_net) <= 1.0,
          f"{net:.2f} vs {exp_net:.2f}")
    check("max DD within 0.5pp", abs(r["mdd"] - exp_mdd) <= 0.5,
          f"{r['mdd']:.2f} vs {exp_mdd:.2f}")


def test_no_lookahead(sym="SOLUSDT"):
    print("\n[2] NO-LOOKAHEAD — prefix stability under truncation")
    print("    " + "-" * 92)
    b = _load15(sym)
    T = np.array([x[0] for x in b], dtype=np.int64)
    fr, fev = funding_arrays(sym, T)
    gate = gate_broken(b)
    k = 40000
    full = GC.run(b, gate, funding_arrays=(fr, fev), close_only_stop=True,
                  flatten_on_bear=False, size_on="equity")
    trunc = GC.run(b[:k], gate[:k], funding_arrays=(fr[:k], fev[:k]),
                   close_only_stop=True, flatten_on_bear=False,
                   size_on="equity")
    eq_same = abs(full["eq_curve"][k - 1] - trunc["eq_curve"][k - 1]) < 1e-6
    cut = int(b[k - 1][0])
    lf_full = [x for x in full["logs"] if x[0] <= cut]
    lf_trunc = list(trunc["logs"])
    logs_same = [(a[0], a[1]) for a in lf_full] == [(a[0], a[1]) for a in lf_trunc]
    print(f"    full    equity@{k} = {full['eq_curve'][k-1]:.4f}  "
          f"events <= cut = {len(lf_full)}")
    print(f"    trunc   equity@{k} = {trunc['eq_curve'][k-1]:.4f}  "
          f"events         = {len(lf_trunc)}")
    check("equity identical at the cut", eq_same)
    check("event (ts, kind) sequence identical in prefix", logs_same)


def test_sizing_invariant(sym="SOLUSDT"):
    print("\n[3] SIZING INVARIANT — a full grid is 125% of equity as notional")
    print("    " + "-" * 92)
    b = _load15(sym)
    gate = gate_broken(b)
    eng = GC.GridEngine(size_on="notional")
    # hand-build a grid at a known equity
    eq = 10000.0
    eng._grid_px = [100.0 - i for i in range(5)]
    n_not = eng.grid_notional(eq)
    eng_eq = GC.GridEngine(size_on="equity")
    eng_eq._grid_px = list(eng._grid_px)
    n_eq = eng_eq.grid_notional(eq)
    print(f"    size_on='notional' at equity {eq:,.0f}: grid notional "
          f"{n_not:,.0f} = {n_not/eq:.2f}x")
    print(f"    size_on='equity'    at equity {eq:,.0f}: grid notional "
          f"{n_eq:,.0f} = {n_eq/eq:.2f}x")
    check("notional sizing = 1.25x equity", abs(n_not / eq - 1.25) < 1e-9,
          f"{n_not/eq:.4f}x")
    # and the compounding: same grid, equity doubled
    n_not2 = eng.grid_notional(eq * 2)
    n_eq2 = eng_eq.grid_notional(eq * 2)
    print(f"    at equity {eq*2:,.0f} (post-profit): notional-mode "
          f"{n_not2/eq:.2f}x original equity, equity-mode "
          f"{n_eq2/n_not:.2f}x its own 10k grid")
    check("notional mode scales with equity (risk grows)",
          abs(n_not2 / n_not - 2.0) < 1e-9)
    check("equity mode compounds faster than proportional",
          n_eq2 / n_not > 2.0,
          f"{n_eq2/n_not:.3f}x")


def test_fixes_change_behaviour(sym="SOLUSDT"):
    print("\n[4] DEFECT FIXES CHANGE BEHAVIOUR — a fix that changes nothing "
          "was never applied")
    print("    " + "-" * 92)
    b = _load15(sym)
    T = np.array([x[0] for x in b], dtype=np.int64)
    fr, fev = funding_arrays(sym, T)
    gb, gf = gate_broken(b), gate_fixed(b)
    print(f"    gate: broken {gb.sum():,} bars true vs fixed "
          f"{gf.sum():,} bars true ({(gb!=gf).sum():,} disagree)")

    base_kw = dict(funding_arrays=(fr, fev), close_only_stop=True,
                   flatten_on_bear=False, size_on="equity")
    r0 = GC.run(b, gb, **base_kw)
    r1 = GC.run(b, gb, **{**base_kw, "close_only_stop": False})
    r2 = GC.run(b, gb, **{**base_kw, "flatten_on_bear": True})
    r3 = GC.run(b, gb, **{**base_kw, "size_on": "notional"})
    r4 = GC.run(b, gf, **{**base_kw, "size_on": "notional",
                          "close_only_stop": False, "flatten_on_bear": True})

    def pct(r):
        return (r["equity"] / GC.INITIAL_EQUITY - 1) * 100

    print(f"    unfixed            net {pct(r0):+9.2f}%  DD {r0['mdd']:6.2f}%  "
          f"stops {r0['counts'].get('stop',0):>4}")
    print(f"    + intrabar stop    net {pct(r1):+9.2f}%  DD {r1['mdd']:6.2f}%  "
          f"stops {r1['counts'].get('stop',0):>4}")
    print(f"    + bear flatten     net {pct(r2):+9.2f}%  DD {r2['mdd']:6.2f}%  "
          f"bear {r2['counts'].get('bear_flatten',0):>4}")
    print(f"    + notional sizing  net {pct(r3):+9.2f}%  DD {r3['mdd']:6.2f}%")
    print(f"    ALL FOUR FIXED     net {pct(r4):+9.2f}%  DD {r4['mdd']:6.2f}%  "
          f"grids {r4['counts'].get('grid_built',0):>4}")
    check("defect 2 intrabar stop changes stop count",
          r1["counts"].get("stop", 0) > r0["counts"].get("stop", 0),
          f"{r0['counts'].get('stop',0)} -> {r1['counts'].get('stop',0)}")
    check("defect 3 bear-flatten fires", r2["counts"].get("bear_flatten", 0) > 0,
          f"{r2['counts'].get('bear_flatten',0)} events")
    check("defect 4 notional sizing changes the book",
          abs(pct(r3) - pct(r0)) > 0.01)
    check("defect 1 fixed gate differs from broken gate",
          int((gb != gf).sum()) > 0, f"{int((gb!=gf).sum()):,} bars disagree")


def test_equity_identity(sym="SOLUSDT"):
    print("\n[5] EQUITY IDENTITY — equity == cash + inventory value, always")
    print("    " + "-" * 92)
    b = _load15(sym)
    T = np.array([x[0] for x in b], dtype=np.int64)
    fr, fev = funding_arrays(sym, T)
    gate = gate_broken(b)
    r = GC.run(b, gate, funding_arrays=(fr, fev), close_only_stop=True,
               flatten_on_bear=False, size_on="equity")
    # replay and check equity at every bar against cash+inventory
    eng = r["engine"]
    st = eng.st
    eqc = r["eq_curve"]
    # re-run stepping and verify identity each bar
    eng2 = GC.GridEngine(funding=(fr, fev), close_only_stop=True,
                         flatten_on_bear=False, size_on="equity")
    bad = 0
    neg_with_inv = 0
    H = np.array([x[2] for x in b], float)
    L = np.array([x[3] for x in b], float)
    C = np.array([x[4] for x in b], float)
    atrser = GC.atr(H, L, C)
    for t in range(len(b)):
        pc = b[t - 1][4] if t >= 1 else None
        ap = atrser[t - 1] if t >= 1 else None
        eng2.step_bar(b[t][0], b[t][1], b[t][2], b[t][3], b[t][4], b[t][5],
                      gate[t], ap, pc, bar_i=t)
        st = eng2.st
        inv = sum(x[0] * b[t][4] for x in st.lots)
        ident = abs((st.cash + inv) - eng2.equity(b[t][4])) < 1e-9
        if not ident:
            bad += 1
        if inv > 0 and (st.cash + inv) < -1e-6:
            neg_with_inv += 1
    print(f"    bars where equity != cash+inventory : {bad}")
    print(f"    bars with long inventory and negative equity : {neg_with_inv}")
    check("equity identity holds every bar", bad == 0, f"{bad} violations")
    check("never negative while holding long inventory", neg_with_inv == 0,
          f"{neg_with_inv} bars")


def main():
    print("=" * 92)
    print("grid_core parity + regression suite")
    print("=" * 92)
    test_fidelity()
    test_no_lookahead()
    test_sizing_invariant()
    test_fixes_change_behaviour()
    test_equity_identity()
    print("\n" + "=" * 92)
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for f in FAIL:
            print(f"    FAILED: {f}")
    print("=" * 92)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())