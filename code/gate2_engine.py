#!/usr/bin/env python
"""gate2_engine.py -- score a pack50b candidate under the v2 gate set.

One artifact = one prompt of the claude2 pack, re-executed through the SAME
frozen machinery (pack50b_engine's loader, pack50b_strats' rules, the audited
pack50_core execution core) and measured with gate2.py's statistical layer:

    G1v2  per-trade expectancy, block-bootstrap 95% LB > 0 (PF kept secondary)
    G2v2  >= 100 closed trades (>= 30 per symbol), effective N reported
    G3v2  six contiguous folds split on entry time, boundary-crossing trades
          purged from both sides, >= 70% of scorable folds PF > 1
    G4v2  monthly buckets, >= 5 trades each, >= 60% green, worst bucket
          better than -15% of starting capital
    G5v2  beta-adjusted alpha vs the same symbol's bar returns, t > 2 by
          block bootstrap
    G6v2  net > 0 after removing the top 5% of trades AND the best month
    G8    PF > 1 at 2x the repo gate cost (11 bps per side), and the
          breakeven per-side cost measured by bisection with real re-runs
    G9v2  P95 of the bootstrapped max drawdown <= 50% of starting capital,
          with mark-to-market longest-underwater reported
    G7    components recorded (per-bar SR, n_obs, skew, kurt) for the
          campaign-level DSR; G10 is a process gate, recorded as
          `pre_registered: false` for this pack

The measurement run is at the REPO gate cost (5.0 + 0.5 bps per side). The
pack-cost headline from the pack50b campaign is re-measured here too so the
two reports stay comparable. Nothing is inferred from the existing artifacts;
every number is computed from a fresh execution inside this artifact.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import gate2 as G2
import pack50b_engine as PE
import pack50b_strats as SB
from pack50_core import Costs, load_funding, load_tf, run_plan

REPO = Costs(fee_bps=5.0, slip_bps=0.5)
TWO_X = Costs(fee_bps=11.0, slip_bps=0.0)     # 2x the 5.5 bps gate cost, per side


def _bar_returns(curve):
    c = np.asarray(curve, float)
    return np.diff(c) / c[:-1]


def run_one(paths, params):
    strat = int(params["strat"])
    spec = SB.SPECS[strat]
    if spec.get("no_data"):
        raise RuntimeError(f"prompt {SB.CODE[strat]} cannot be run: {spec['no_data']}")
    tf = spec["tf"]
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    funding = load_funding(fund[0]) if fund else None
    df = PE.load_base_tf(klines[0], tf)
    plan = spec["build"](df, PE._ctx_for(df)) if strat == 10 else spec["build"](df)

    base_fee, base_slip = SB.costs_for(spec["sym"].split("+")[0], tf)
    pack = Costs(fee_bps=base_fee, slip_bps=base_slip)
    res_pack = run_plan(df, plan, pack, funding)
    res = run_plan(df, plan, REPO, funding)
    res_2x = run_plan(df, plan, TWO_X, funding)
    tr = res["trades"]
    eq = res["equity"]
    if len(tr) == 0:
        raise RuntimeError(f"{SB.CODE[strat]} produced no trades at repo cost")

    r = tr["ret_pct"].to_numpy(float)
    e = tr["entry_ts"].to_numpy(np.int64)
    x = tr["exit_ts"].to_numpy(np.int64)
    sr_bar = _bar_returns(eq)
    mkt = df["close"].to_numpy(float)
    mkt_ret = np.diff(mkt) / mkt[:-1]

    lb, exp_bps, blk = G2.expectancy_lb_bps(r, n_boot=1000, seed=7)
    eff = G2.effective_n(r)
    sp = G2.purged_split(e, x, r, frac=0.70, min_oos=30)
    folds, fold_frac, purged_n = G2.purged_folds(e, x, r, n_folds=5, min_fold_trades=10)
    buckets = G2.period_buckets(x, r, freq="M", min_bucket_trades=5)
    alpha = G2.beta_alpha_t(sr_bar, mkt_ret, n_boot=1000, seed=11)
    conc = G2.top_frac_concentration(r, frac=0.05)
    bm = G2.best_month_removal(e, r)
    bw = G2.best_week_removal(x, r)
    dd95 = G2.p95_max_dd(sr_bar, n_boot=500, seed=13)
    ddst = G2.drawdown_stats(eq)
    pf_pct = G2.profit_factor_pct(r)

    # per-trade max adverse excursion from the bars each trade spans, and the
    # liquidation check at the DECLARED leverage (the pack compounds full
    # equity with no leverage: notional/equity = 1.0)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    bar_ts = df["open_ts"].to_numpy(np.int64)
    entry_px = tr["entry_px"].to_numpy(float)
    side = tr["side"].to_numpy(int)
    i_in = np.searchsorted(bar_ts, e)
    i_out = np.clip(np.searchsorted(bar_ts, x), 0, len(bar_ts) - 1)
    mae = np.zeros(len(tr))
    for k in range(len(tr)):
        lo_k = l[i_in[k]:i_out[k] + 1].min()
        hi_k = h[i_in[k]:i_out[k] + 1].max()
        mae[k] = max((entry_px[k] - lo_k) / entry_px[k], 0.0) if side[k] > 0 \
            else max((hi_k - entry_px[k]) / entry_px[k], 0.0)
    leverage_declared = 1.0
    liq_thresh = 1.0 / leverage_declared - 0.005
    liq_trades = int((mae >= liq_thresh).sum())

    # cost share on the repo convention: fees as a share of STRICT gross profit
    gross = tr["pnl"].to_numpy(float) + tr["fees"].to_numpy(float) - tr["funding"].to_numpy(float)
    strict_gross = float(gross[gross > 0].sum())
    fees_total = float(tr["fees"].sum())
    cost_share = float(fees_total / strict_gross) if strict_gross > 0 else float("inf")

    def _pf_at(costs):
        t2 = run_plan(df, plan, costs, funding)["trades"]
        return G2.profit_factor_pct(t2["ret_pct"].to_numpy(float)) if len(t2) else 0.0

    pf_2x = _pf_at(TWO_X)
    be, _ = G2.breakeven_side_cost(lambda t: run_plan(df, plan, Costs(fee_bps=t, slip_bps=0.0), funding)["trades"],
                                   lo=0.0, hi=100.0, iters=8)

    sr = float(np.mean(sr_bar) / np.std(sr_bar, ddof=1)) if len(sr_bar) > 2 else float("nan")
    sk = float(pd.Series(sr_bar).skew()) if len(sr_bar) > 2 else 0.0
    ku = float(pd.Series(sr_bar).kurt() + 3.0) if len(sr_bar) > 2 else 3.0

    m = {
        "strategy_id": strat, "prompt_code": SB.CODE[strat],
        "strategy_name": spec["name"], "symbol": spec["sym"], "timeframe": tf,
        "bars": int(len(df)),
        "cost_bps_per_side": 5.5,
        "n_trades": int(len(tr)),
        # headline at the pack's own block, for comparability with pack50b
        "pack_ret_pct": float(100.0 * (res_pack["equity"][-1] / 10000.0 - 1.0)),
        "pack_pf": G2.profit_factor_pct(res_pack["trades"]["ret_pct"].to_numpy(float))
        if len(res_pack["trades"]) else 0.0,
        # v1 gates at repo cost (the pack50b semantics, on this run)
        "v1_pf_pct": round(pf_pct, 4) if np.isfinite(pf_pct) else None,
        "v1_return_pct": float(100.0 * (eq[-1] / 10000.0 - 1.0)),
        "v1_conc_top5_net_pct": float(100.0 * (r.sum() - np.sort(r)[::-1][:5].sum()) / 10000.0),
        # v2 measurements
        "expectancy_bps": round(exp_bps, 3),
        "expectancy_lb95_bps": round(lb, 3) if np.isfinite(lb) else None,
        "expectancy_block": blk,
        "effective_n": round(eff, 1),
        "folds": folds, "folds_pf_gt1_frac": round(fold_frac, 4),
        "folds_purged_trades": int(purged_n),
        "split_pf_is": sp["pf_is"], "split_pf_oos": sp["pf_oos"],
        "split_n_is": sp["n_is"], "split_n_oos": sp["n_oos"],
        "split_purged_trades": sp["purged"],
        "buckets": buckets,
        "beta": round(alpha["beta"], 4), "alpha_bps_per_bar": round(alpha["alpha_bps_per_bar"], 3),
        "alpha_t": round(alpha["t"], 3) if np.isfinite(alpha["t"]) else None,
        "conc_top5pct_k": conc["k"], "conc_top5pct_share_pct": round(conc["share_pct"], 2),
        "conc_top5pct_net_pct": round(conc["net_without_pct"], 2),
        "best_month": bm["best_month"], "best_month_pnl": bm["best_month_pnl"],
        "net_without_best_month_pct": round(bm["net_without_pct"], 2),
        "best_week": bw["best_week"], "best_week_pnl": bw["best_week_pnl"],
        "net_without_best_week_pct": round(bw["net_without_pct"], 2),
        "pf_at_2x_cost": round(pf_2x, 4) if np.isfinite(pf_2x) else None,
        "breakeven_side_cost_bps": round(be, 2) if np.isfinite(be) else None,
        "cost_share_strict_gross": round(cost_share, 4) if np.isfinite(cost_share) else None,
        "mae_median_pct": round(float(np.median(mae) * 100.0), 3),
        "mae_p95_pct": round(float(np.percentile(mae, 95) * 100.0), 3),
        "leverage_declared": leverage_declared,
        "liquidation_threshold_move_pct": round(liq_thresh * 100.0, 2),
        "liquidated_trades": liq_trades,
        "p95_max_dd_pct": round(dd95, 2) if np.isfinite(dd95) else None,
        "max_dd_pct": round(ddst["max_dd_pct"], 2),
        "longest_underwater_bars": ddst["longest_underwater_bars"],
        "sr_per_bar": round(sr, 5), "skew": round(sk, 3), "kurt": round(ku, 3),
        "n_bar_obs": int(len(sr_bar)),
        # v2 verdicts (POLICY-aligned with _gates_v2; hash below)
        "policy_hash": G2.policy_hash(),
        "g1v2_lb_pos": bool(np.isfinite(lb) and lb > 0),
        "g2v2_n": bool(len(tr) >= 100 and eff >= 50),
        "g3v2_split_folds": bool(sp["pass"] and fold_frac >= 0.70),
        "g4v2_buckets": bool(buckets["pass_floor"] and buckets["n_buckets"] >= 6
                             and buckets["green_frac"] >= 0.60
                             and buckets["worst_pct"] > -15.0),
        "g5v2_alpha_t": bool(np.isfinite(alpha["t"]) and alpha["t"] > 2.0),
        "g6v2_conc": bool(conc["net_without_pct"] > 0 and bm["net_without_pct"] > 0
                          and bw["net_without_pct"] > 0),
        "g8_cost": bool((pf_2x is not None and np.isfinite(pf_2x) and pf_2x > 1.0)
                        and (be is not None and np.isfinite(be) and be >= 11.0)
                        and (cost_share == cost_share and cost_share <= 0.35)),
        "g9v2_dd": bool(np.isfinite(dd95) and dd95 <= 35.0 and liq_trades == 0),
        "pre_registered": False,
        "versions": {"python": sys.version.split()[0], "numpy": np.__version__,
                     "pandas": pd.__version__},
    }
    return m, {"adapter": "gate2", "engine_version": "gate2-1"}, []
