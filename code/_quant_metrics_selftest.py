#!/usr/bin/env python3
"""
_quant_metrics_selftest.py — known-answer checks for quant_metrics additions.
Convention: VaR/CVaR are LOSS MAGNITUDES in PERCENT (positive = loss).

Test A (per-bar): r = [0.01, -0.02, 0.005, -0.05, 0.03, -0.01, 0.02, -0.015,
0.04, -0.005]; sorted: [-0.05, -0.02, -0.015, -0.01, -0.005, 0.005, 0.01,
0.02, 0.03, 0.04]. 5th percentile, linear interp: pos = 0.05*9 = 0.45 ->
-0.05 + 0.45*0.03 = -0.0365 -> VaR95 = 3.65%. CVaR95 = mean of obs <= that
= mean([-0.05]) = 5.0%. 1st percentile: pos = 0.09 -> -0.0473 -> VaR99 =
4.73%, CVaR99 = 5.0%.

Test B (scorecard daily aggregation): 30 days at 24 bars/day; daily returns
= 26 days +0.2%, then [-1%, -2%, -5%, -3%]. Sorted: [-5,-3,-2,-1, +0.2 x26].
n=30. 5th pct pos = 29*0.05 = 1.45 -> -3 + 0.45*1 = -2.55 -> VaR95 = 2.55%.
CVaR95 = mean([-5,-3]) = 4.0%. 1st pct pos = 0.29 -> -5 + 0.29*2 = -4.42 ->
VaR99 = 4.42%. CVaR99 = mean([-5]) = 5.0%. Bar returns are the exact 24th
root of each daily return, so daily compounding reproduces them exactly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import quant_metrics as qm


def main() -> int:
    fails = []

    r = [0.01, -0.02, 0.005, -0.05, 0.03, -0.01, 0.02, -0.015, 0.04, -0.005]
    vc = qm.historical_var_cvar(r, levels=(0.95, 0.99))
    for k, exp in {"var_95_pct": 3.65, "cvar_95_pct": 5.0,
                   "var_99_pct": 4.73, "cvar_99_pct": 5.0}.items():
        got = vc.get(k)
        if got is None or abs(got - exp) > 1e-9:
            fails.append(f"A/{k}: expected {exp}, got {got}")
        else:
            print(f"PASS A/{k} = {got}")

    short = qm.historical_var_cvar(r[:5])
    if short != {}:
        fails.append(f"A/short: should return {{}}, got {short}")
    else:
        print("PASS A/short-series guard returns empty dict")

    daily_rets = [0.002] * 26 + [-0.01, -0.02, -0.05, -0.03]
    bars = []
    eq = [100.0]
    for rd in daily_rets:
        rb = (1.0 + rd) ** (1.0 / 24.0) - 1.0
        for _ in range(24):
            eq.append(eq[-1] * (1.0 + rb))
    art = {
        "run_id": "selftest", "strategy": "selftest", "symbol": "TESTUSDT",
        "timeframe": "1h",
        "metrics": {"return_pct": 0.0, "max_dd_pct": 5.0},
        "equity_curve": eq,
    }
    card = qm.compute_artifact_scorecard(art)
    v = card.get("var_cvar") or {}
    if v.get("bars_per_day") != 24 or v.get("n_days") != 30:
        fails.append(f"B/aggregation: bars_per_day={v.get('bars_per_day')} n_days={v.get('n_days')}")
    else:
        print(f"PASS B/aggregation bars_per_day={v['bars_per_day']} n_days={v['n_days']}")
    for k, exp in {"var_95_pct": 2.55, "cvar_95_pct": 4.0,
                   "var_99_pct": 4.42, "cvar_99_pct": 5.0}.items():
        got = v.get(k)
        if got is None or abs(got - exp) > 1e-6:
            fails.append(f"B/{k}: expected {exp}, got {got}")
        else:
            print(f"PASS B/{k} = {got}")

    if fails:
        print("SELFTEST FAILED:")
        for f in fails:
            print("  " + f)
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
