#!/usr/bin/env python
"""pack50c_engine.py -- harness runner for the Qwen fifty-prompt pack
(`Downloads/Qwen_50 strategies.txt`, numbered Q01-Q50).

One artifact = one numbered prompt on the symbol and timeframe the prompt
names. The measurement is the union of the pack50b protocol and the v2 gate
layer, so each artifact carries BOTH verdicts:

    * the pack's own cost block (5.0 fee + 2.0 slip bps per side, "2 ticks"
      read as 2 bps), and the SAME signals re-run at the repo gate cost,
      at twice the gate cost, at the measured breakeven, and with ZERO cost;
    * the v1 gates G1-G6 (pack semantics) and the v2 statistical gates
      (expectancy bootstrap LB, effective N, purged split, purged folds,
      exit-month buckets, top-5%/best-month/best-week concentration,
      beta-alpha t, cost share, P95 drawdown, MAE and the liquidation
      distance at the declared leverage);
    * perpetual funding charged at the settlement instants;
    * buy & hold over the same window, the 70/30 split on entry time.

Nothing is inferred from a previous run; a prompt without its data on disk
(eight NVDA prompts) is never called and is reported NO DATA.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import gate2 as G2
import pack50b_engine as PE
import pack50c_strats as SC
from pack50_core import Costs, Plan, buy_and_hold, load_funding, run_plan

REPO = Costs(fee_bps=5.0, slip_bps=0.5)
TWO_X = Costs(fee_bps=11.0, slip_bps=0.0)
INIT = 10000.0


def _bar_returns(curve):
    c = np.asarray(curve, float)
    return np.diff(c) / c[:-1]


def _expectancy_lb_chunked(ret_pct, n_boot=1000, seed=7, block=None, chunk=25):
    """Memory-bounded variant of gate2.block_bootstrap_mean for pathological
    trade counts (the Qwen pack's one-minute PSAR book traded nearly once per
    bar: a (reps x n) int64 index matrix reached gigabytes). Identical
    moving-block semantics with the draws issued in chunks; asserted equal to
    the unchunked version for small n in `_pack50c_audit.py`."""
    x = np.asarray(ret_pct, float) * 100.0
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return float("nan"), float("nan")
    if block is None:
        block = max(1, int(round(n ** (1.0 / 3.0))))
    block = min(block, n)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    means = np.empty(n_boot)
    for s in range(0, n_boot, chunk):
        e = min(s + chunk, n_boot)
        starts = rng.integers(0, n - block + 1, size=(e - s, nb))
        idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(e - s, -1)[:, :n]
        means[s:e] = x[idx].mean(axis=1)
    lb = float(np.percentile(means, 2.5))
    return lb, float(x.mean())


def _v1_gates(tr, df, bh_ret):
    n = len(tr)
    pnl = tr["pnl"].to_numpy(float)
    g = float(pnl[pnl > 0].sum())
    l = float(-pnl[pnl < 0].sum())
    pf = (g / l) if l > 0 else (float("inf") if g > 0 else 0.0)
    no_losses = bool(not np.isfinite(pf) and pnl.sum() > 0) if n else False
    split_ts = int(df["open_ts"].to_numpy()[int(len(df) * 0.7)])

    def _pf(x):
        if len(x) == 0:
            return None
        gg = float(x[x > 0].sum())
        ll = float(-x[x < 0].sum())
        return (gg / ll) if ll > 0 else (float("inf") if gg > 0 else 0.0)

    is_pf = _pf(tr[tr["entry_ts"] < split_ts]["pnl"].to_numpy(float))
    os_pf = _pf(tr[tr["entry_ts"] >= split_ts]["pnl"].to_numpy(float))
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
        "is_pf": None if is_pf is None or not np.isfinite(is_pf) else round(is_pf, 4),
        "os_pf": None if os_pf is None or not np.isfinite(os_pf) else round(os_pf, 4),
        "green_years": gy, "n_years": len(years),
        "years_map": {str(k): round(v, 2) for k, v in sorted(years.items())},
    }


def run_one(paths, params):
    strat = int(params["strat"])
    spec = SC.SPECS[strat]
    if spec.get("no_data"):
        raise RuntimeError(f"prompt {SC.CODE[strat]} cannot be run: {spec['no_data']}")

    tf = spec["tf"]
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    funding = load_funding(fund[0]) if fund else None
    df = PE.load_base_tf(klines[0], tf)
    plan = spec["build"](df)

    base_fee, base_slip = SC.costs_for(spec["sym"], tf)
    pack = Costs(fee_bps=base_fee, slip_bps=base_slip)
    res_pack = run_plan(df, plan, pack, funding)
    res = run_plan(df, plan, REPO, funding)
    tr = res["trades"]
    eq = res["equity"]
    if len(tr) == 0:
        raise RuntimeError(f"{SC.CODE[strat]} produced no trades at repo cost")
    r = tr["ret_pct"].to_numpy(float)
    e = tr["entry_ts"].to_numpy(np.int64)
    x = tr["exit_ts"].to_numpy(np.int64)

    sr_bar = _bar_returns(eq)
    mkt = df["close"].to_numpy(float)
    mkt_ret = np.diff(mkt) / mkt[:-1]
    # alpha is measured on DAILY returns (the reference layer's G5 basis):
    # bar-level bootstrap on a one-million-bar book allocates gigabytes, and
    # the daily basis is the statistically meaningful one for alpha vs market
    ts_idx = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    eq_d = pd.Series(eq, index=ts_idx).resample("1D").last().ffill()
    mk_d = pd.Series(mkt, index=ts_idx).resample("1D").last().ffill()
    strat_daily = eq_d.pct_change().dropna().to_numpy(float)
    mkt_daily = mk_d.pct_change().dropna().to_numpy(float)
    bh = buy_and_hold(df)

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
    zero = run_plan(df, plan, Costs(0.0, 0.0), funding)
    zero_pf = G2.profit_factor_pct(zero["trades"]["ret_pct"].to_numpy(float)) if len(zero["trades"]) else 0.0

    v1 = _v1_gates(tr, df, bh["bh_return_pct"])
    sr = float(np.mean(sr_bar) / np.std(sr_bar, ddof=1)) if len(sr_bar) > 2 else float("nan")

    m = {
        "strategy_id": strat, "prompt_code": SC.CODE[strat],
        "strategy_name": spec["name"], "symbol": spec["sym"], "timeframe": tf,
        "bars": int(len(df)),
        "pack_cost_bps_per_side": [base_fee, base_slip],
        "cost_bps_per_side": 5.5,
        "policy_hash": G2.policy_hash(),
        "n_trades": int(len(tr)),
        "plan_note": plan.note if isinstance(plan, Plan) else "",
        "funding_charged": bool(fund),
        "funding_paid": float(tr["funding"].sum()) if len(tr) else 0.0,
        # pack-cost headline
        "pack_ret_pct": float(100.0 * (res_pack["equity"][-1] / INIT - 1.0)),
        "pack_pf": round(G2.profit_factor_pct(res_pack["trades"]["ret_pct"].to_numpy(float)), 4)
        if len(res_pack["trades"]) else 0.0,
        # shared measurements (repo cost)
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
        "cost_share_strict_gross": round(cost_share, 4) if np.isfinite(cost_share) else None,
        "mae_median_pct": round(float(np.median(mae) * 100.0), 3),
        "mae_p95_pct": round(float(np.percentile(mae, 95) * 100.0), 3),
        "leverage_declared": leverage_declared,
        "liquidation_threshold_move_pct": round(liq_thresh * 100.0, 2),
        "liquidated_trades": liq_trades,
        "sr_per_bar": round(sr, 5),
        "n_bar_obs": int(len(sr_bar)),
        # v1 gates (pack semantics)
        "v1": v1,
        # v2 gates
        "split_pf_is": sp["pf_is"], "split_pf_oos": sp["pf_oos"],
        "split_n_oos": sp["n_oos"], "split_purged": sp["purged"],
        "folds_pf_gt1_frac": round(fold_frac, 4), "folds_purged_trades": int(purged_n),
        "buckets_green_frac": round(buckets["green_frac"], 4),
        "buckets_worst_pct": round(buckets["worst_pct"], 2) if np.isfinite(buckets["worst_pct"]) else None,
        "buckets_scored": buckets["n_buckets"],
        "conc_top5pct_net_pct": round(conc["net_without_pct"], 2),
        "net_without_best_month_pct": round(bm["net_without_pct"], 2),
        "net_without_best_week_pct": round(bw["net_without_pct"], 2),
        "alpha_t": round(alpha["t"], 3) if np.isfinite(alpha["t"]) else None,
        "alpha_basis": "daily",
        "p95_max_dd_pct": round(dd95, 2) if np.isfinite(dd95) else None,
        "longest_underwater_bars": ddst["longest_underwater_bars"],
        # v2 verdicts
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
    return m, {"adapter": "pack50c", "engine_version": "pack50c-1"}, []
