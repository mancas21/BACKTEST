#!/usr/bin/env python
"""Known-answer audit for the author engine `code/claude_bot_1/engine_core.py`.

The engine is imported UNMODIFIED; costs are pinned to the author's shipped
values (TAKER_FEE 5 bps, SLIPPAGE_BPS 3 bps) at the start of every test.
Every expected figure below is hand-computed in the comments. ALL PASS is
required before any real-data artifact of this suite is reported.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mps20_engine as M  # noqa: E402

ec, sg = M.load_author_modules()
FEE, SLIP = 0.0005, 0.0003
EQ0 = 100_000.0
TOL = 1e-4

FAILS = []


def flat(n: int) -> pd.DataFrame:
    return pd.DataFrame({"open": [100.0] * n, "high": [100.0] * n,
                         "low": [100.0] * n, "close": [100.0] * n,
                         "volume": [0.0] * n})


def ind_atr(df: pd.DataFrame, atr: float) -> pd.DataFrame:
    return pd.DataFrame({"atr14": [atr] * len(df)}, index=df.index)


def cfg(id_: str, sig, mode="discrete", **kw) -> ec.StrategyConfig:
    base = dict(id=id_, name=id_, archetype="audit", mode=mode, signal_fn=sig if mode == "discrete" else None,
                weight_fn=sig if mode == "weight" else None,
                max_concurrent_legs=5, risk_per_trade=0.01,
                portfolio_heat_cap=0.05, atr_stop_mult=2.0, max_gross_leverage=1.0)
    base.update(kw)
    return ec.StrategyConfig(**base)


def check(name: str, got, want, tol: float = TOL):
    ok = got is not None and want is not None and abs(got - want) <= tol * max(1.0, abs(want))
    line = f"{'PASS' if ok else 'FAIL'}  {name:<48} got={got!r} want={want!r}"
    print(line)
    if not ok:
        FAILS.append(name)


def test_t1_stop_and_fees():
    """5 bars, 1 pair. t0 enter long at close 100 (+3bps slip = 100.03),
    fee 100.03*500*5bps = 25.0075 -> cash 99974.9925, unrealized -15.0
    -> equity[0] = 99959.9925. Stop = 100.03 - 2*1.0 = 98.03.
    t1: low 98.0 touches -> exit AT STOP 98.03 (no slip on stops):
    pnl = 500*(98.03-100.03) = -1000; exit fee 98.03*500*5bps = 24.5075;
    trade record = -1024.5075; equity[1] = 98950.485."""
    M.set_costs(ec, FEE, SLIP)
    bars = 5
    df = flat(bars)
    df.loc[1, "low"] = 98.0
    sigs = {"entered": {}}

    def sig(data, indicators, t, state, open_legs):
        if t == 0:
            sigs["entered"][0] = True
            return {"entries": {"TEST": {"action": "enter_long"}}}
        return {}

    n = len(df)
    idx = pd.RangeIndex(n)
    df.index = idx
    ind = {"TEST": ind_atr(df, 1.0)}
    cfga = cfg("T1", sig)
    res = ec.run_discrete_backtest(cfga, {"TEST": df}, ind)
    eq = res.equity_curve
    check("T1 equity[0] after entry (fee+slip mark)", eq.iat[0], 99959.9925)
    check("T1 equity[1] after stop", eq.iat[1], 98950.485)
    check("T1 equity final", eq.iat[-1], 98950.485)
    tr = res.trades[0]
    check("T1 trade record pnl (net of exit fee only)", tr.pnl, -1024.5075)
    check("T1 entry price w/ slippage", tr.entry_price, 100.03)
    check("T1 exit price = stop, no slip", tr.exit_price, 98.03)
    check("T1 size reconstruction (runner's _size_of)", M._size_of(tr, cfga, ind), 500.0)
    check("T1 reason == stop", 0 if tr.reason == "stop" else 1, 0)
    check("T1 n trades", float(len(res.trades)), 1.0)


def test_t2_sizing_heatcap():
    """6 pairs signalled long at t0; risk 1% each; heat cap 5% -> 4 legs=4000,
    5th leg: 4000+1000=5000 > 5000? no (equal) -> allowed; 6th: 6000 > 5000
    -> skipped, and a skipped entry charges NO fee.
    equity[0] = 100000 - 5*(25.0075) - 5*15.0 = 99799.9625."""
    M.set_costs(ec, FEE, SLIP)
    df = flat(3)
    data, ind = {}, {}
    for i in range(1, 7):
        p = f"T{i}"
        data[p] = df.copy()
        ind[p] = ind_atr(df, 1.0)

    def sig(data, indicators, t, state, open_legs):
        if t == 0:
            return {"entries": {p: {"action": "enter_long"} for p in data}}
        return {}

    res = ec.run_discrete_backtest(cfg("T2", sig), data, ind)
    eq = res.equity_curve
    # leg count is fingerprinted through equity: 5 admitted legs -> fees 5*25.0075
    # and slip marks 5*15.0 -> 99799.9625; 6 legs would be 99759.9550 (6th entry
    # violates the heat cap, and a skipped entry must charge NO fee).
    check("T2 equity[0] == 5 capped legs marked", eq.iat[0], 99799.9625)
    six_leg_print = abs(eq.iat[0] - 99759.9550) < 1e-6
    check("T2 not the 6-leg fingerprint", 1.0 if six_leg_print else 0.0, 0.0)


def test_t3_signal_exit_fees():
    """t0 enter long @100.03 (fee 25.0075); t2 signal exit at close 102:
    pnl_raw = 500*(102-100.03) = 985; exit fee 102*500*5bps = 25.5;
    trade record = 959.5; equity[2] = 99974.9925 + 985 - 25.5 = 100934.4925.
    STRICT pnl (both fees) = 959.5 - 25.0075 = 934.4925."""
    M.set_costs(ec, FEE, SLIP)
    df = flat(4)
    for t in range(4):
        df.loc[t, "close"] = [100.0, 101.0, 102.0, 102.0][t]
        df.loc[t, "open"] = df.loc[t, "close"]
        df.loc[t, "high"] = df.loc[t, "close"]
        df.loc[t, "low"] = df.loc[t, "close"]

    def sig(data, indicators, t, state, open_legs):
        if t == 0:
            return {"entries": {"TEST": {"action": "enter_long"}}}
        if t == 2 and "TEST" in open_legs:
            return {"exits": {"TEST": True}}
        return {}

    cfgt = cfg("T3", sig)
    ind = {"TEST": ind_atr(df, 1.0)}
    res = ec.run_discrete_backtest(cfgt, {"TEST": df}, ind)
    eq = res.equity_curve
    tr = res.trades[0]
    size_rec = M._size_of(tr, cfgt, ind)
    check("T3 equity[2] after signal exit", eq.iat[2], 100934.4925)
    check("T3 trade record pnl (net of exit fee)", tr.pnl, 959.5)
    check("T3 size reconstruction matches 500", size_rec, 500.0)
    check("T3 strict pnl (both fees; runner's formula on this trade)",
          tr.pnl - abs(tr.entry_price * size_rec) * FEE, 934.4925)
    check("T3 reason == signal", 0 if tr.reason == "signal" else 1, 0)


def test_t4_weight_accounting():
    """2 pairs A(10->11), B(20->20). weight_fn targets .50/.50 at t0 only.
    port=100000: units A=5000, B=2500; fees+slip 40 each -> cash = -80.
    eq[0] = -80 + 50000 + 50000 = 99920; eq[1] = -80 + 55000 + 50000 = 104920."""
    M.set_costs(ec, FEE, SLIP)
    idx = pd.RangeIndex(2)
    a = pd.DataFrame({"open": [10.0, 11.0], "high": [10.0, 11.0], "low": [10.0, 11.0],
                      "close": [10.0, 11.0], "volume": [0.0, 0.0]}, index=idx)
    b = pd.DataFrame({"open": [20.0, 20.0], "high": [20.0, 20.0], "low": [20.0, 20.0],
                      "close": [20.0, 20.0], "volume": [0.0, 0.0]}, index=idx)

    def wf(data, indicators, t, state):
        return {"A": 0.5, "B": 0.5} if t == 0 else None

    res = ec.run_weight_backtest(cfg("T4", wf, mode="weight"), {"A": a, "B": b}, {})
    eq = res.equity_curve
    check("T4 eq[0] with fees+slip on both fills", eq.iat[0], 99920.0)
    check("T4 eq[1] mark-to-market", eq.iat[1], 104920.0)

    def wf_cap(data, indicators, t, state):
        return {"A": 1.2, "B": -0.4} if t == 0 else None  # gross 1.6 -> scaled .625

    res2 = ec.run_weight_backtest(cfg("T4b", wf_cap, mode="weight"), {"A": a, "B": b}, {})
    eq2 = res2.equity_curve
    check("T4b gross cap scales weights (eq[0])", eq2.iat[0], 99920.0)
    check("T4b short side -25% marked at t1", eq2.iat[1], 107420.0)


def test_t5_benchmark():
    """Equal-weight units (5000 A, 2500 B), no fees: t1 = 55000+50000=105000."""
    M.set_costs(ec, FEE, SLIP)
    idx = pd.RangeIndex(2)
    a = pd.DataFrame({"open": [10, 11], "high": [10, 11], "low": [10, 11],
                      "close": [10.0, 11.0], "volume": [0, 0]}, index=idx)
    b = pd.DataFrame({"open": [20, 20], "high": [20, 20], "low": [20, 20],
                      "close": [20.0, 20.0], "volume": [0, 0]}, index=idx)
    bm = ec.build_benchmark({"A": a, "B": b})
    check("T5 benchmark is fee-free equal weight", bm.iat[1], 105000.0)


def test_t6_metrics_zero_pnl_is_loss():
    """compute_metrics counts pnl==0 as a LOSS (engine's own convention):
    pnls [5, 0, -2] -> wins {5}, losses {0, -2} -> PF = 5/2 = 2.5,
    win_rate = 1/3."""
    idx = pd.RangeIndex(4)
    eqv = pd.Series([100000.0, 100000.0, 100000.0, 100000.0], index=idx)
    benv = pd.Series([100000.0] * 4, index=idx)
    trades = [
        ec.Trade("X", 1, 0, 1, 100.0, 105.0, 5.0, 1.0, "signal"),
        ec.Trade("X", 1, 1, 2, 105.0, 105.0, 0.0, 1.0, "signal"),
        ec.Trade("X", 1, 2, 3, 105.0, 103.0, -2.0, 1.0, "signal"),
    ]
    res = ec.BacktestResult("T6", "discrete", eqv, trades)
    m = ec.compute_metrics(res, benv)
    check("T6 profit_factor (0 treated as loss)", m["profit_factor"], 2.5)
    check("T6 win_rate = 1/3", m["win_rate_pct"], 100.0 / 3.0)
    check("T6 n trades", float(m["total_trades"]), 3.0)


def test_t7_engine_costs_are_module_state():
    """Fees flow through module constants; overriding changes fills (documented
    mechanism used by the adapter for cost knobs)."""
    M.set_costs(ec, 0.0, 0.0)
    df = flat(4)
    for t in range(4):
        df.loc[t, "close"] = [100.0, 101.0, 102.0, 102.0][t]
        df.loc[t, "high"] = df.loc[t, "close"]
        df.loc[t, "low"] = df.loc[t, "close"]

    def sig(data, indicators, t, state, open_legs):
        if t == 0:
            return {"entries": {"TEST": {"action": "enter_long"}}}
        if t == 2 and "TEST" in open_legs:
            return {"exits": {"TEST": True}}
        return {}

    res = ec.run_discrete_backtest(cfg("T7", sig), {"TEST": df}, {"TEST": ind_atr(df, 1.0)})
    eq = res.equity_curve
    check("T7 zero-cost control: entry price = close (no slip)", res.trades[0].entry_price, 100.0)
    # zero slip -> entry at close exactly; pnl = 500*(102-100) = 1000; equity = 101000
    check("T7 zero-cost control: equity[2] = 101000", eq.iat[2], 101000.0)
    check("T7 zero-cost control: trade pnl = raw 1000", res.trades[0].pnl, 1000.0)


def main() -> int:
    tests = [
        ("T1 stop fill + fee accounting", test_t1_stop_and_fees),
        ("T2 sizing / heat cap / skipped entry", test_t2_sizing_heatcap),
        ("T3 signal exit + strict fees", test_t3_signal_exit_fees),
        ("T4 weight accounting + gross cap", test_t4_weight_accounting),
        ("T5 benchmark", test_t5_benchmark),
        ("T6 metrics conventions", test_t6_metrics_zero_pnl_is_loss),
        ("T7 cost knobs via module state", test_t7_engine_costs_are_module_state),
    ]
    for name, fn in tests:
        print(f"--- {name} ---")
        try:
            fn()
        except Exception as e:
            print(f"FAIL  {name}  raised {type(e).__name__}: {e}")
            FAILS.append(name)
        M.set_costs(ec, FEE, SLIP)
    n_pass = len(tests) - len([f for f in FAILS])
    print(f"\nRESULT: {n_pass}/{len(tests)} test groups passed" if not FAILS
          else f"\nRESULT: FAILURES: {FAILS}")
    return 0 if not FAILS else 2


if __name__ == "__main__":
    sys.exit(main())
