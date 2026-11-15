#!/usr/bin/env python
"""_qs096_audit.py -- known-answer audit for QS-096 (CHoCH + ATR percentile filter).
Run BEFORE any real-data artifact.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import qs096_engine as E
import qs_d_strats as D

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


def _warmup(n=600):
    """Calm warmup so ATR percentile has >= 500 valid bars."""
    rows = []
    px = 100.0
    for i in range(n):
        px += 0.05 * (1 if i % 2 == 0 else -1)
        rows.append((px - 0.2, px + 0.3, px - 0.3, px))
    return rows


def frame(rows):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df["volume"] = 1000.0
    df["open_ts"] = np.arange(len(df)) * 3600000
    return df


def test_known_answers():
    # Build sawtooth downtrend -> CHoCH break as in D3 of _qs_d_audit.py
    rows = _warmup(600)
    px = 112.0
    for i in range(28):                     # 4 cycles of a 7-bar swing
        step = (0.8 if i % 7 == 0 else (-0.45 if i % 7 < 5 else 0.4))
        px += step
        rows.append((px - step, px + (0.5 if i % 7 == 0 else 0.2), px - 0.5, px))
    for i in range(3):                      # calm gap: last peak confirms
        rows.append((px + 0.1, px + 0.3, px - 0.2, px + 0.2))

    df_base = frame(rows)
    ph_conf, _pl = D._confirmed_pivots(df_base, 3)
    ph_last, _ = D._last_two(ph_conf)
    lvl = float(ph_last.iloc[-1])

    rows.append((lvl + 0.0, lvl + 1.4, lvl - 0.1, lvl + 1.2))   # break bar
    rows.append((lvl + 1.2, lvl + 1.3, lvl - 0.1, lvl + 0.3))   # retest touch
    rows.append((lvl + 0.3, lvl + 1.1, lvl + 0.2, lvl + 1.0))   # reclaim trigger bar

    df0 = frame(rows)

    # 1. Unconstrained filter [0, 100] should match #33
    plan_unconstrained = E.build_plan(df0, "1h", dict(pct_lo=0.0, pct_hi=100.0, variant="two_side"))
    check("1. Unconstrained [0, 100] produces #33 CHoCH long signal",
          plan_unconstrained["long_event"].sum() >= 1)

    # 2. Strict filter requiring extreme high volatility [98, 100] when volatility is ~95% should veto
    plan_veto_high = E.build_plan(df0, "1h", dict(pct_lo=98.0, pct_hi=100.0, variant="two_side"))
    check("2. Veto when ATR percentile is below pct_lo=98%",
          plan_veto_high["long_event"].sum() == 0,
          f"expected 0 events, got {plan_veto_high['long_event'].sum()}")

    # 3. Strict filter requiring low volatility [0, 5] when volatility is normal should veto
    plan_veto_low = E.build_plan(df0, "1h", dict(pct_lo=0.0, pct_hi=5.0, variant="two_side"))
    check("3. Veto when ATR percentile is above pct_hi=5%",
          plan_veto_low["long_event"].sum() == 0,
          f"expected 0 events, got {plan_veto_low['long_event'].sum()}")

    # 4. Long-only variant suppresses short entries
    plan_long_only = E.build_plan(df0, "1h", dict(pct_lo=0.0, pct_hi=100.0, variant="long"))
    check("4. Long-only variant suppresses short entries completely",
          plan_long_only["short_event"].sum() == 0)

    # 5. Full run_symbol execution sanity
    m = E.run_symbol_metrics(df0, "1h", dict(pct_lo=0.0, pct_hi=100.0, variant="two_side"), cost="gate")
    check("5. Execution produces metric dict with required gate fields",
          "profit_factor" in m and "return_pct" in m and "gate_all" in m)

    print(f"\nAUDIT COMPLETE: {PASS} PASS, {FAIL} FAIL")
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    test_known_answers()
