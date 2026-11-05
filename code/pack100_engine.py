#!/usr/bin/env python
"""pack100_engine.py -- harness runner for the Sonnet 100-prompt pack
(`Downloads/strategy_prompts_100-sonnet-claude.md`, numbered 01..100).

One artifact = one (prompt, timeframe) cell. The measurement machinery is the
pack50d protocol IMPORTED, not copied: _v1_gates / _bar_returns /
_expectancy_lb_chunked / _ctx_1h come from pack50d_engine by identity, the
execution core is pack50_core.run_plan / run_pair, the statistical layer is
gate2. Differences from pack50d, all declared:
  * the pack declares NO cost block, so the primary headline IS the repo gate
    (5.0 fee + 0.5 slip bps per side); 2x, breakeven and zero-cost controls
    are measured inside every artifact;
  * prompts expand one spec per timeframe (sid "A01-5m"); the pack template
    itself says the timeframes run separately;
  * multi-leg prompts (51, 89: BTC aux leg; 99, 100: ratio pairs) hash every
    leg into the artifact inputs;
  * ctx prompts (90, 91) map fully-closed 1h context onto the fine book
    (the pack50b convention, via pack50d_engine._ctx_1h);
  * NO DATA prompts (NVDA legs, OI, long/short ratio, JUP funding) are never
    called and never estimated.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import gate2 as G2
import pack100_strats2 as SD
import pack50b_engine as PE
from pack50_core import Costs, Plan, buy_and_hold, buy_and_hold_pair, \
    load_funding, run_pair, run_plan
from pack50d_engine import (_bar_returns, _ctx_1h, _expectancy_lb_chunked,
                            _v1_gates)

REPO = Costs(fee_bps=5.0, slip_bps=0.5)
TWO_X = Costs(fee_bps=11.0, slip_bps=0.0)
INIT = 10000.0


def _ctx_for(df, sid):
    m = _ctx_1h(df)
    h1 = m["high"].to_numpy(float)
    l1 = m["low"].to_numpy(float)
    c1 = m["close"].to_numpy(float)
    if sid.startswith("H90"):
        import pack100_strats as P1
        e50 = pd.Series(P1.ema(c1, 50))
        e200 = pd.Series(P1.ema(c1, 200))
        up = (e50 > e200).to_numpy(float)
        return {"ema_up_1h": up}
    if sid.startswith("H91"):
        hh = pd.Series(h1).rolling(20).max().shift(1).to_numpy()
        ll = pd.Series(l1).rolling(20).min().shift(1).to_numpy()
        return {"don_hi_1h": hh, "don_lo_1h": ll}
    return {}


def run_one(paths, params):
    sid = str(params["strat"])
    spec = SD.SPECS[sid]
    if spec.get("no_data"):
        raise RuntimeError(f"prompt {sid} cannot be run: {spec['no_data']}")

    tf = spec["tf"]
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    funding = load_funding(fund[0]) if fund else None
    is_pair = "pair" in spec
    df = PE.load_base_tf(klines[0], tf)
    df_a = df
    pair_note = None
    if is_pair or "build2" in spec:
        df_b = PE.load_base_tf(klines[1], tf)
        na = min(len(df_a), len(df_b))
        df_a = df_a.iloc[-na:].reset_index(drop=True)
        df_b = df_b.iloc[-na:].reset_index(drop=True)
        common = np.intersect1d(df_a["open_ts"].to_numpy(), df_b["open_ts"].to_numpy())
        df_a = df_a[df_a["open_ts"].isin(common)].reset_index(drop=True)
        df_b = df_b[df_b["open_ts"].isin(common)].reset_index(drop=True)

    if is_pair:
        def _pair_run(costs):
            tgt, note = spec["pair"](df_a, df_b)
            return run_pair(df_a, df_b, tgt, costs, funding,
                            load_funding(fund[1]) if len(fund) > 1 else None), \
                tgt, note
        res, _tgt, pair_note = _pair_run(REPO)
        plan = None
    elif "build2" in spec:
        plan = spec["build2"](df, df_b)
        res = run_plan(df, plan, REPO, funding)
    elif spec.get("ctx"):
        plan = spec["build"](df, _ctx_for(df, sid))
        res = run_plan(df, plan, REPO, funding)
    else:
        plan = spec["build"](df)
        res = run_plan(df, plan, REPO, funding)

    tr = res["trades"]
    eq = res["equity"]
    if len(tr) == 0:
        raise RuntimeError(f"{sid} produced no trades at repo cost")
    r = tr["ret_pct"].to_numpy(float)
    e = tr["entry_ts"].to_numpy(np.int64)
    x = tr["exit_ts"].to_numpy(np.int64)

    sr_bar = _bar_returns(eq)
    mkt = (df_a["close"].to_numpy(float) / df_b["close"].to_numpy(float)) \
        if is_pair else df["close"].to_numpy(float)
    book_df = df_a if is_pair else df
    ts_idx = pd.to_datetime(book_df["open_ts"], unit="ms", utc=True)
    eq_d = pd.Series(eq, index=ts_idx).resample("1D").last().ffill()
    mk_d = pd.Series(mkt, index=ts_idx).resample("1D").last().ffill()
    strat_daily = eq_d.pct_change().dropna().to_numpy(float)
    mkt_daily = mk_d.pct_change().dropna().to_numpy(float)

    lb, exp_bps, blk = (None, None, None)
    if len(r) > 100_000:
        lb, exp_bps = _expectancy_lb_chunked(r, n_boot=1000, seed=7)
        lb_method = "chunked_moving_block"
    else:
        lb, exp_bps, blk = G2.expectancy_lb_bps(r, n_boot=1000, seed=7)
        lb_method = "moving_block"
    eff = G2.effective_n(r)
    sp = G2.purged_split(e, x, r)
    folds, fold_frac, purged_n = G2.purged_folds(e, x, r)
    buckets = G2.period_buckets(x, r, freq="M", min_bucket_trades=5)
    alpha = G2.beta_alpha_t(strat_daily, mkt_daily, n_boot=1000, seed=11)
    conc = G2.top_frac_concentration(r, frac=0.05)
    bm = G2.best_month_removal(e, r)
    bw = G2.best_week_removal(x, r)
    dd95 = G2.p95_max_dd(sr_bar, n_boot=500, seed=13)
    ddst = G2.drawdown_stats(eq)
    pf_pct = G2.profit_factor_pct(r)

    mae_df = df_a if is_pair else df
    h = mae_df["high"].to_numpy(float)
    l = mae_df["low"].to_numpy(float)
    bar_ts = mae_df["open_ts"].to_numpy(np.int64)
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

    gross = tr["pnl"].to_numpy(float) + tr["fees"].to_numpy(float) \
        - tr["funding"].to_numpy(float)
    strict_gross = float(gross[gross > 0].sum())
    fees_total = float(tr["fees"].sum())
    cost_share = float(fees_total / strict_gross) if strict_gross > 0 else float("inf")

    base_fee, base_slip = SD.costs_for(spec["sym"], tf)
    pack = Costs(fee_bps=base_fee, slip_bps=base_slip)
    if is_pair:
        res_pack, _, _ = _pair_run(pack)
        bh = buy_and_hold_pair(df_a, df_b)
    else:
        res_pack = run_plan(df, plan, pack, funding)
        bh = buy_and_hold(df)

    def _run_at(costs):
        if is_pair:
            return _pair_run(costs)[0]
        return run_plan(df, plan, costs, funding)

    def _pf_at(costs):
        t2 = _run_at(costs)["trades"]
        return G2.profit_factor_pct(t2["ret_pct"].to_numpy(float)) if len(t2) else 0.0

    pf_2x = _pf_at(TWO_X)
    be, _ = G2.breakeven_side_cost(
        lambda t: _run_at(Costs(fee_bps=t, slip_bps=0.0))["trades"],
        lo=0.0, hi=100.0, iters=8)
    zero = _run_at(Costs(0.0, 0.0))
    zero_pf = G2.profit_factor_pct(zero["trades"]["ret_pct"].to_numpy(float)) \
        if len(zero["trades"]) else 0.0

    v1 = _v1_gates(tr, book_df, bh["bh_return_pct"])
    sr = float(np.mean(sr_bar) / np.std(sr_bar, ddof=1)) if len(sr_bar) > 2 \
        else float("nan")

    plan_note = (pair_note if is_pair else
                 (plan.note if isinstance(plan, Plan) else ""))
    m = {
        "strategy_id": sid, "prompt_code": SD.CODE.get(sid, sid),
        "prompt_num": spec["num"], "strategy_name": spec["name"],
        "symbol": spec["sym"], "timeframe": tf,
        "bars": int(len(df)),
        "pack_cost_bps_per_side": [base_fee, base_slip],
        "cost_bps_per_side": 5.5,
        "policy_hash": G2.policy_hash(),
        "n_trades": int(len(tr)),
        "funding_charged": bool(fund),
        "funding_paid": float(tr["funding"].sum()) if len(tr) else 0.0,
        "pack_ret_pct": float(100.0 * (res_pack["equity"][-1] / INIT - 1.0)),
        "pack_pf": round(G2.profit_factor_pct(
            res_pack["trades"]["ret_pct"].to_numpy(float)), 4)
        if len(res_pack["trades"]) else 0.0,
        "pf_pct": round(pf_pct, 4) if np.isfinite(pf_pct) else None,
        "return_pct": float(100.0 * (eq[-1] / INIT - 1.0)),
        "max_dd_pct": round(ddst["max_dd_pct"], 2),
        "bh_return_pct": bh["bh_return_pct"],
        "zero_cost_pf": round(zero_pf, 4) if np.isfinite(zero_pf) else None,
        "expectancy_lb_method": lb_method,
        "expectancy_bps": round(exp_bps, 3),
        "expectancy_lb95_bps": round(lb, 3) if np.isfinite(lb) else None,
        "effective_n": round(eff, 1),
        "pf_at_2x_cost": round(pf_2x, 4) if np.isfinite(pf_2x) else None,
        "breakeven_side_cost_bps": round(be, 2) if np.isfinite(be) else None,
        "cost_share_strict_gross": round(cost_share, 4)
        if np.isfinite(cost_share) else None,
        "mae_median_pct": round(float(np.median(mae) * 100.0), 3),
        "mae_p95_pct": round(float(np.percentile(mae, 95) * 100.0), 3),
        "leverage_declared": leverage_declared,
        "liquidation_threshold_move_pct": round(liq_thresh * 100.0, 2),
        "liquidated_trades": liq_trades,
        "sr_per_bar": round(sr, 5),
        "n_bar_obs": int(len(sr_bar)),
        "v1": v1,
        "split_pf_is": sp["pf_is"], "split_pf_oos": sp["pf_oos"],
        "split_n_oos": sp["n_oos"], "split_purged": sp["purged"],
        "folds_pf_gt1_frac": round(fold_frac, 4),
        "folds_purged_trades": int(purged_n),
        "buckets_green_frac": round(buckets["green_frac"], 4),
        "buckets_worst_pct": round(buckets["worst_pct"], 2)
        if np.isfinite(buckets["worst_pct"]) else None,
        "buckets_scored": buckets["n_buckets"],
        "alpha_t": round(alpha["t"], 3) if np.isfinite(alpha["t"]) else None,
        "alpha_bps_per_bar": round(alpha["alpha_bps_per_bar"], 3)
        if np.isfinite(alpha["alpha_bps_per_bar"]) else None,
        "conc_top5pct_net_pct": round(conc["net_without_pct"], 2),
        "net_without_best_month_pct": round(bm["net_without_pct"], 2),
        "net_without_best_week_pct": round(bw["net_without_pct"], 2),
        "alpha_t": round(alpha["t"], 3) if np.isfinite(alpha["t"]) else None,
        "alpha_basis": "daily", "is_pair": is_pair,
        "p95_max_dd_pct": round(dd95, 2) if np.isfinite(dd95) else None,
        "longest_underwater_bars": ddst["longest_underwater_bars"],
        # v2 verdicts (pack50d's frozen definitions, verbatim)
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
    m["v1_pass"] = bool(all(v1[k] for k in
                            ("g1_pf", "g2_n", "g3_halves", "g4_years",
                             "g5_beats_bh", "g6_conc")))
    m["v2_pass"] = bool(all(m[k] for k in
                            ("g1v2_lb_pos", "g2v2_n", "g3v2_split_folds",
                             "g4v2_buckets", "g5v2_alpha_t", "g6v2_conc",
                             "g8_cost", "g9v2_dd")))
    return m, {"adapter": "pack100", "engine_version": "pack100-1",
               "pack_source": "Downloads/strategy_prompts_100-sonnet-claude.md"}, []

