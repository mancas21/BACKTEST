#!/usr/bin/env python
"""gatecal_engine.py -- the calibration of the gate set itself (audit C1).

THE QUESTION
    How often does a book with NO edge clear the gates, and how much edge is
    needed before it usually does? The v1 gate set (G1-G6) was adopted by
    convention; its false-positive rate was never measured. This engine
    measures it.

THE NULL
    Random entries on REAL Binance prices (BTCUSDT 1h taker): at every bar a
    coin-flip side fires with probability p = n_target / bars, filled at the
    next open by the SAME audited execution core the pack engines use
    (pack50_core.run_plan: next-open fills, intrabar 2x-ATR stop, time stop at
    the next open, funding charged at the settlement instants). A null has no
    edge by construction, so any gate pass is a false positive.

THE PLANTED EDGE
    The same trials are re-scored with a fixed per-trade drift added to every
    per-trade return: ret' = (1+ret)(1+d)-1, d in {0, 5, 10, 20} bps, and the
    equity is rebuilt by compounding the adjusted returns. The pass rate as a
    function of d is the gate set's POWER curve (the positive control).

DESIGN
    n_target in {30, 100, 300} x d in {0, 5, 10, 20} bps x 400 trials, each
    trial a distinct seeded generator (numpy default_rng seeded from a list,
    so the artifact reproduces bit-for-bit). Gates are scored with the v1
    semantics (the pack50 `_gates` booleans) AND the v2 statistical gates
    (G1v2 expectancy LB, G3v2 purged folds, G4v2 monthly buckets, G6v2 top-5%
    concentration) so the two gate sets' false-positive rates and power are
    directly comparable. G9v2 (P95 drawdown) is scored on the raw mark-to-
    market curves of the d=0 cells only; a per-trade drift added post hoc
    does not change the price path, so re-scoring drawdown on adjusted
    equity would overstate the effect (declared reading).

    Costs are the repo gate block (5.0 + 0.5 bps per side). All six v1 gates
    and the v2 set are evaluated per trial; the artifact records per-cell
    pass rates for every gate and for the all-gate conjunction.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import gate2 as G2
from pack50_core import (Costs, Plan, atr, buy_and_hold, load_funding, load_tf,
                         run_plan)

REPO = Costs(fee_bps=5.0, slip_bps=0.5)
HOLDS = [2, 4, 8, 16, 32, 72]
N_TARGETS = [30, 100, 300]
DELTAS_BPS = [0.0, 5.0, 10.0, 20.0]
N_TRIALS = 400
INIT = 10000.0


def _null_plan(df, rng, p, a):
    n = len(df)
    fire = rng.random(n) < p
    side = rng.integers(0, 2, size=n) * 2 - 1
    c = df["close"].to_numpy(float)
    le = fire & (side == 1)
    se = fire & (side == -1)
    hold = int(rng.choice(HOLDS))
    return Plan(le, se, np.zeros(n, bool), np.zeros(n, bool),
                stop_long=c - 2 * a, stop_short=c + 2 * a, time_stop=hold)


def _v1_gate_booleans(tr, split_ts, bh_ret):
    """The pack50 `_gates` semantics, on the trades of one trial."""
    n = len(tr)
    pnl = tr["pnl"].to_numpy(float)
    g = float(pnl[pnl > 0].sum())
    l = float(-pnl[pnl < 0].sum())
    pf = (g / l) if l > 0 else (float("inf") if g > 0 else 0.0)
    no_losses = bool(not np.isfinite(pf) and pnl.sum() > 0) if n else False
    if n:
        ins = tr[tr["entry_ts"] < split_ts]["pnl"].to_numpy(float)
        oos = tr[tr["entry_ts"] >= split_ts]["pnl"].to_numpy(float)

        def _pf(x):
            gg = float(x[x > 0].sum())
            ll = float(-x[x < 0].sum())
            if len(x) == 0:
                return None
            return (gg / ll) if ll > 0 else (float("inf") if gg > 0 else 0.0)

        is_pf, os_pf = _pf(ins), _pf(oos)
    else:
        is_pf = os_pf = None
    yr = pd.to_datetime(tr["entry_ts"], unit="ms", utc=True).dt.year if n else pd.Series([], dtype=int)
    years = {int(y): float(v) for y, v in (tr.assign(y=yr).groupby("y")["pnl"].sum().items() if n else {})}
    gy = sum(1 for v in years.values() if v > 0)
    s = np.sort(pnl)[::-1] if n else np.array([])
    tot = float(pnl.sum()) if n else 0.0
    conc_net = float(100.0 * (tot - s[:5].sum()) / INIT) if n else 0.0
    ret_pct = float(100.0 * (tr["equity_after"].iloc[-1] / INIT - 1.0)) if n else 0.0
    return {
        "g1_pf": bool((np.isfinite(pf) and pf > 1.2) or (no_losses and ret_pct > 0)),
        "g2_n": bool(n >= 30),
        "g3_halves": bool(all((h is not None and np.isfinite(h) and h > 1.0) or
                              (h is None and no_losses) for h in (is_pf, os_pf))),
        "g4_years": bool(len(years) > 0 and gy >= (2.0 / 3.0) * len(years)),
        "g5_beats_bh": bool(ret_pct > bh_ret),
        "g6_conc": bool(conc_net > 0),
    }


def _v2_gate_booleans(tr):
    """The v2 statistical gates on one trial's adjusted trades (policy-aligned
    with _gates_v2.POLICY: purged split AND folds, exit-month buckets with a
    six-scored-bucket floor, top-5% and best-week and best-month removal)."""
    r = tr["ret_pct"].to_numpy(float)
    e = tr["entry_ts"].to_numpy(np.int64)
    x = tr["exit_ts"].to_numpy(np.int64)
    lb, _, _ = G2.expectancy_lb_bps(r, n_boot=300, seed=17)
    sp = G2.purged_split(e, x, r, frac=0.70, min_oos=30)
    folds, frac, _ = G2.purged_folds(e, x, r, n_folds=5, min_fold_trades=10)
    b = G2.period_buckets(x, r, freq="M", min_bucket_trades=5)
    conc = G2.top_frac_concentration(r, frac=0.05)
    bm = G2.best_month_removal(e, r)
    bw = G2.best_week_removal(x, r)
    en = G2.effective_n(r)
    return {
        "g1v2_lb": bool(np.isfinite(lb) and lb > 0),
        "g3v2_split_folds": bool(sp["pass"] and frac >= 0.70),
        "g4v2_buckets": bool(b["pass_floor"] and b["n_buckets"] >= 6
                             and b["green_frac"] >= 0.60
                             and b["worst_pct"] > -15.0),
        "g6v2_conc": bool(conc["net_without_pct"] > 0 and bm["net_without_pct"] > 0
                          and bw["net_without_pct"] > 0),
        "g2v2_eff_n": bool(len(r) >= 30 and en >= 50),
    }


def run_one(paths, params):
    seed0 = int(params.get("seed", 20261027))
    n_trials = int(params.get("n_trials", N_TRIALS))
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    df = load_tf(klines[0], "1h")
    f = load_funding(fund[0]) if fund else None
    n = len(df)
    a = atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
            df["close"].to_numpy(float), 14)
    bh = buy_and_hold(df)["bh_return_pct"]
    split_ts = int(df["open_ts"].to_numpy()[int(n * 0.7)])

    cells = {}
    for n_target in N_TARGETS:
        p = n_target / n
        for delta in DELTAS_BPS:
            key = f"n{n_target}_d{int(delta)}"
            rates_v1 = {g: 0 for g in ("g1_pf", "g2_n", "g3_halves", "g4_years",
                                       "g5_beats_bh", "g6_conc")}
            rates_v2 = {g: 0 for g in ("g1v2_lb", "g3v2_split_folds", "g4v2_buckets",
                                       "g6v2_conc", "g2v2_eff_n")}
            all6 = 0
            allv2 = 0
            done = 0
            for trial in range(n_trials):
                rng = np.random.default_rng([seed0, n_target, int(delta * 10), trial])
                plan = _null_plan(df, rng, p, a)
                res = run_plan(df, plan, REPO, f)
                tr = res["trades"]
                if len(tr) == 0:
                    continue
                if delta > 0.0:
                    eqb = (tr["equity_after"] - tr["pnl"]).to_numpy(float)
                    adj = (1.0 + tr["ret_pct"].to_numpy(float) / 100.0) * (1.0 + delta / 1e4) - 1.0
                    pnl2 = eqb * adj
                    tr = tr.assign(pnl=pnl2, ret_pct=adj * 100.0,
                                   equity_after=eqb + pnl2)
                g1 = _v1_gate_booleans(tr, split_ts, bh)
                for k, v in g1.items():
                    rates_v1[k] += int(v)
                all6 += int(all(g1.values()))
                g2b = _v2_gate_booleans(tr)
                for k, v in g2b.items():
                    rates_v2[k] += int(v)
                allv2 += int(all(g2b.values()))
                done += 1
            cells[key] = {
                "n_target": n_target, "delta_bps": delta, "trials": done,
                "avg_trades": 0.0,
                "v1_pass_rates": {k: round(v / max(done, 1), 4) for k, v in rates_v1.items()},
                "v1_all_six": round(all6 / max(done, 1), 4),
                "v2_pass_rates": {k: round(v / max(done, 1), 4) for k, v in rates_v2.items()},
                "v2_all": round(allv2 / max(done, 1), 4),
            }

    # average realized trade count per cell (from the d=0 runs, re-derived cheaply
    # is not possible post hoc; record from a fixed reference seed per n)
    for n_target in N_TARGETS:
        rng = np.random.default_rng([seed0, n_target, 0, 0])
        plan = _null_plan(df, rng, n_target / n, a)
        res = run_plan(df, plan, REPO, f)
        cells[f"n{n_target}_d0"]["avg_trades"] = float(len(res["trades"]))

    # G9v2 null distribution: P95 drawdown on the raw mark-to-market curves
    dd95 = []
    for trial in range(100):
        rng = np.random.default_rng([seed0, 100, 0, trial])
        plan = _null_plan(df, rng, 100 / n, a)
        res = run_plan(df, plan, REPO, f)
        r = np.diff(res["equity"]) / res["equity"][:-1]
        dd95.append(G2.p95_max_dd(r, n_boot=300, seed=trial))
    dd95 = np.array(dd95, float)

    # ── cross-check: the reference layer `_gates_v2.py` (the second audit-fix
    # implementation) on the SAME real market, its own null generator. Its
    # rates are recorded side by side with this engine's so the two
    # implementations' agreement is a measurement, not an assertion.
    xref = {"note": "reference layer _gates_v2.null_calibration, same real BTCUSDT 1h bars"}
    try:
        import _gates_v2 as GV
        dfx = df.set_index("ts")
        ctxx = GV.GateContext(benchmark_close=dfx["close"], max_leverage=1.0, n_trials=1)
        holds = list(range(2, 25))
        for edge in (0, 20):
            rr = GV.null_calibration(dfx, 100, holds, ctxx, n_sims=200,
                                     seed=seed0, reps=400, edge_bps=float(edge))
            xref[f"edge{edge}"] = {
                "joint": rr["pass_rate_joint"],
                "joint_ex_g7": rr["pass_rate_joint_ex_G7"],
                "upper95": rr["upper95_joint"],
                "by_gate": {k: round(v, 4) for k, v in rr["pass_rate_by_gate"].items()},
            }
    except Exception as e:      # the cross-check must never kill the artifact
        xref["error"] = f"{type(e).__name__}: {e}"

    m = {
        "purpose": "empirical false-positive rate and power of the v1 (G1-G6) and v2 gate sets",
        "null": "random 50/50 entries on real BTCUSDT 1h bars, next-open fills, 2xATR stop, time stop, funding charged",
        "data": "BTCUSDT 1h taker + funding",
        "cost_bps_per_side": 5.5,
        "policy_hash": G2.policy_hash(),
        "reference_layer_cross_check": xref,
        "seed": seed0,
        "n_trials_per_cell": n_trials,
        "n_targets": N_TARGETS,
        "deltas_bps": DELTAS_BPS,
        "bars": int(n),
        "bh_return_pct": bh,
        "cells": cells,
        "g9v2_null_p95_dd_median": float(np.median(dd95)),
        "g9v2_null_p95_dd_p90": float(np.percentile(dd95, 90)),
        "versions": {"python": sys.version.split()[0], "numpy": np.__version__,
                     "pandas": pd.__version__},
        "pre_registered": False,
    }
    return m, {"adapter": "gatecal", "engine_version": "gatecal-1"}, []
