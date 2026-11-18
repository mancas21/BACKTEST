#!/usr/bin/env python
"""_scalpma20_build_plan.py -- emit results/bt_plans/scalpma20.json.

DECLARED BEFORE ANY MARKET RUN (nothing here is tuned afterwards).

Grid: SOLUSDT, SUIUSDT, HYPEUSDT x {5m, 1m} x 20 ids = 120 screen jobs.
  * 5m: the full repo history (data/binance_klines_5m).
  * 1m: the window from 2026-05-01 (slice_from rides in the params, so it is
    part of run_id -- a declared window, not a silent cherry-pick; the same
    reason scalpwave declared its own 1m window).
  * LINKUSDT is a traded instrument but scalpwave found NO 1m/5m file for it
    in this repo: it is not in the grid, declared here instead of dropped
    silently. Add it the day the file exists.

Gates mirror the bt.py one standard battery exactly (pf > 1.2, n >= 30,
net > 0, thirds >= 2 of 3, OOS 70/30 pf > 1.2 and net > 0, best-5 concentration
<= 100 percent of net PnL, per-trade bootstrap CI low > 0). Every metric is
measured INSIDE each artifact; nothing is derived here.

MULTIPLE TESTING (declared): 120 screen cells x 7 gates on overlapping data.
A handful of passes is the EXPECTED outcome of noise. The report must (a)
count how many cells pass, (b) compare that count to what 120 coin flips at
the gate would give, (c) cite per-id artifacts only, never "the best of the
family". The neighborhood stage (one declared parameter, one step each side)
is the main filter: a survivor whose neighbors collapse is an isolated peak.

Neighborhood: sl_atr one step each side of the shipped default 1.2 (id 18's
declared default is 1.5, so its steps straddle 1.5). --set pins sl_atr for
the neighbors only; the center cell is the screen cell itself.

Walk-forward stage: NOT DECLARED (the signal rules have no fitted
parameters; the in-artifact frozen 70/30 split, thirds and best-5 carry the
stability evidence).

Stats: one scorecard job per cell, survivor-gated (needs=).
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYMS = ["SOLUSDT", "SUIUSDT", "HYPEUSDT"]
TFS = ["5m", "1m"]
SLICE_1M = "2026-05-01"
NB = {i: ("sl_atr", "1.0,1.4") for i in range(1, 21)}
NB[18] = ("sl_atr", "1.2,1.8")

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
                label = f"sm20_{sid:02d}_{sym}_{tf}"
                sets = [f"id={sid}"]
                if tf == "1m":
                    sets.append(f"slice_from={SLICE_1M}")
                jobs.append({"label": label, "role": "screen",
                             "strategy": "scalpma20", "tf": tf, "symbol": sym,
                             "set": sets})
                param, values = NB[sid]
                jobs.append({"label": f"{label}-nb", "role": "neighborhood",
                             "needs": label, "strategy": "scalpma20",
                             "tf": tf, "symbol": sym, "set": sets,
                             "param": param, "values": values})
                jobs.append({"label": f"{label}-stats", "role": "stats",
                             "needs": label})
    plan = {"name": "scalpma20-screen", "workers": 4, "gates": GATES,
            "jobs": jobs, "report": "results/bt_scalpma20_screen_report.md"}
    out = os.path.join(ROOT, "results", "bt_plans", "scalpma20.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1)
    c = lambda r: sum(1 for j in jobs if j["role"] == r)
    print(f"plan -> {out}")
    print(f"screen jobs: {c('screen')}   neighborhood jobs: {c('neighborhood')}   stats jobs: {c('stats')}")


if __name__ == "__main__":
    main()
