#!/usr/bin/env python
"""_pack20_build_plan.py -- emit results/bt_plans/pack20.json (2026-11-08).

Declared screen grid: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT x {1h, 15m} x
20 cards = one hundred and sixty screen jobs. Screen gates mirror the
bt.py one standard battery exactly (pf > 1.2, n >= 30, net > 0, thirds
>= 2 of 3, OOS 70/30 pf > 1.2 and net > 0, best-5 concentration <= 100
percent of net PnL, per-trade bootstrap CI low > 0) -- every metric is
measured inside each artifact by the wrapper, nothing is derived here.

Neighborhood: ONE declared parameter per card, one step each side of the
shipped default (the screen cell itself is the center point). Cards 18
(logreg) and 20 (gbm) are EXCLUDED: their wrapper functions ignore the
params dict entirely (`def logreg_walkforward(df, p=None): return
_walkforward(df, _LogReg)`), so no neighborhood exists to run -- declared
in the report, not a silent omission.

Walk-forward stage: NOT DECLARED. The pack has no parameter-frozen mode
and no window parameters; the in-artifact 70/30 split, thirds and yearly
PnL carry the stability evidence (pack50-series precedent, declared).

Stats: one scorecard job per cell, survivor-gated (needs=).
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
TFS = ["1h", "15m"]

# one declared neighborhood parameter per card: (param, "left,right" steps)
# around the shipped default (the screen cell is the center)
NEIGH = {
    1:  ("pen_atr", "0.05,0.15"),      # default 0.10
    2:  ("impulse_atr", "1.0,1.4"),    # 1.2
    3:  ("break_atr", "0.03,0.07"),    # 0.05
    4:  ("pen_atr", "0.03,0.07"),      # 0.05
    5:  ("pen_atr", "0.02,0.04"),      # 0.03
    6:  ("rr", "2.0,3.0"),             # 2.5
    7:  ("adx_in", "20,24"),           # 22
    8:  ("entry_n", "15,25"),          # 20
    9:  ("sig", "7,11"),               # 9
    10: ("buy", "8,12"),               # 10
    11: ("k", "1.8,2.2"),              # 2.0
    12: ("z_in", "1.8,2.2"),           # 2.0
    13: ("z_in", "1.8,2.2"),           # 2.0
    14: ("z_in", "1.8,2.2"),           # 2.0
    15: ("arm", "0.10,0.20"),          # 0.15
    16: ("kc_k", "1.3,1.7"),           # 1.5
    17: ("n", "72,120"),               # 96
    19: ("train", "480,720"),          # 600
    # 18 / 20: wrapper functions drop the params dict -> no neighborhood
}

GATES = {"screen": [
    ["profit_factor", ">", 1.2],
    ["n_trades", ">=", 30],
    ["return_pct", ">", 0.0],
    ["n_periods_green", ">=", 2],
    ["oos_profit_factor", ">", 1.2],
    ["oos_return_pct", ">", 0.0],
    ["best5_share_pct", "<=", 100.0],
    ["boot_ci_lo", ">", 0.0],
]}


def main() -> None:
    jobs = []
    for sid in range(1, 21):
        for sym in SYMS:
            for tf in TFS:
                label = f"p20_{sid:02d}_{sym}_{tf}"
                jobs.append({"label": label, "role": "screen",
                             "strategy": "pack20", "tf": tf, "symbol": sym,
                             "set": [f"id={sid}"]})
                if sid in NEIGH:
                    param, values = NEIGH[sid]
                    jobs.append({"label": f"{label}-nb", "role": "neighborhood",
                                 "needs": label, "strategy": "pack20",
                                 "tf": tf, "symbol": sym,
                                 "set": [f"id={sid}"],
                                 "param": param, "values": values})
                jobs.append({"label": f"{label}-stats", "role": "stats",
                             "needs": label})
    plan = {"name": "pack20-screen", "workers": 4, "gates": GATES,
            "jobs": jobs,
            "report": "results/bt_pack20_screen_report.md"}
    out = os.path.join(ROOT, "results", "bt_plans", "pack20.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1)
    n_screen = sum(1 for j in jobs if j["role"] == "screen")
    n_nb = sum(1 for j in jobs if j["role"] == "neighborhood")
    n_stats = sum(1 for j in jobs if j["role"] == "stats")
    print(f"plan -> {out}")
    print(f"screen jobs: {n_screen}   neighborhood jobs: {n_nb}   stats jobs: {n_stats}")


if __name__ == "__main__":
    main()
