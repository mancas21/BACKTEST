#!/usr/bin/env python
"""cand7_engine.py -- harness runner for the seven prespecified candidates of
`Downloads/strategy_candidates_v2-claude.md` (2026-10-27).

One artifact = one candidate.  The primary measurement is the candidate's own
declared protocol: 5.0 bps fee + 2.0 bps slippage per side, next-open fills,
stops from the fill, stop-first on ties, funding at the real settlement instants
with the declared entry-instant asymmetry, and the candidate's own sizing
(0.5% equity at the stop with a 3x notional cap for the directional books;
fixed gross exposure for the basket and pair books).

Inside the same artifact:
    * the repo gate cost (5.0 + 0.5 bps per side) and the old 22 bps preset
      (6.0 + 5.0) re-run on the same signals, plus a ZERO-cost control;
    * full-equity sizing as a control for the directional books;
    * the v1 gates G1-G6 and the v2 statistical layer of gate2.py
      (expectancy bootstrap LB, effective N, purged split and folds, monthly
      buckets, alpha t, top-5% / best-month / best-week concentration, cost
      share, P95 drawdown, breakeven by real re-runs);
    * buy & hold over the same window and the 70/30 split;
    * candidate-specific diagnostics (DST split for C3, same-bar stop/target
      count for C2, turnover and book kills for C4/C5, funding legs for C6,
      event counts and dispersion for every candidate).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import cand7_core as C
import cand7_strats as S
import gate2 as G2

INIT = 10000.0
BASE = C.Costs(5.0, 2.0)       # the candidate document's own block
REPO = C.Costs(5.0, 0.5)       # repo gate cost, 11 bps round trip
STRESS = C.Costs(6.0, 5.0)     # old 22 bps preset
ZERO = C.Costs(0.0, 0.0)


def _pf(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return None
    g = float(x[x > 0].sum())
    l = float(-x[x < 0].sum())
    if l <= 0:
        return None if g <= 0 else float("inf")
    return g / l


def _finite(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _bar_returns(curve):
    c = np.asarray(curve, float)
    return np.diff(c) / c[:-1]


def _years(tr):
    if len(tr) == 0:
        return {}
    y = pd.to_datetime(tr["entry_ts"], unit="ms", utc=True).dt.year
    g = tr.groupby(y)["pnl"].sum()
    return {int(k): float(v) for k, v in g.items()}


def _score(tr, curve, bar_ts, bh_ret, extra_split_ts=None):
    n = len(tr)
    pnl = tr["pnl"].to_numpy(float) if n else np.array([], float)
    ret = tr["ret_pct"].to_numpy(float) if n else np.array([], float)
    gross = float(pnl[pnl > 0].sum()) if n else 0.0
    loss = float(-pnl[pnl < 0].sum()) if n else 0.0
    pf = (gross / loss) if loss > 0 else (float("inf") if gross > 0 else 0.0)
    no_losses = bool(n and not np.isfinite(pf) and pnl.sum() > 0)
    split_ts = int(extra_split_ts) if extra_split_ts is not None else \
        int(bar_ts[int(len(bar_ts) * 0.7)])
    is_m = tr["entry_ts"].to_numpy(np.int64) < split_ts if n else np.array([], bool)
    is_pf = _pf(pnl[is_m]) if n else None
    os_pf = _pf(pnl[~is_m]) if n else None
    years = _years(tr)
    s = np.sort(pnl)[::-1] if n else np.array([])
    tot = float(pnl.sum()) if n else 0.0
    conc_share = float(100.0 * s[:5].sum() / tot) if n and tot != 0 else 0.0
    conc_net = float(100.0 * (tot - s[:5].sum()) / INIT) if n else 0.0
    wins = pnl[pnl > 0]
    losses = -pnl[pnl < 0]
    exp_r = float(wins.mean() / losses.mean()) if len(wins) and len(losses) and losses.mean() > 0 else 0.0
    eq = np.asarray(curve, float)
    peak = np.maximum.accumulate(eq)
    dd = float(-100.0 * ((eq - peak) / np.where(peak > 0, peak, 1.0)).min()) if len(eq) else 0.0
    return dict(
        n_trades=int(n),
        return_pct=float(100.0 * (eq[-1] / INIT - 1.0)) if len(eq) else 0.0,
        profit_factor=_finite(pf),
        pf_no_losses=no_losses,
        pf_pct=_finite(G2.profit_factor_pct(ret)),
        win_rate=float(100.0 * (pnl > 0).mean()) if n else 0.0,
        expectancy_R=_finite(exp_r),
        max_dd_pct=dd,
        is_pf=_finite(is_pf),
        os_pf=_finite(os_pf),
        n_is=int(is_m.sum()) if n else 0,
        n_oos=int((~is_m).sum()) if n else 0,
        conc_top5_share_pct=conc_share,
        conc_net_without_top5_pct=conc_net,
        funding_net_usdt=float(tr["funding"].sum()) if n else 0.0,   # + = received
        funding_net_pct=float(100.0 * tr["funding"].sum() / INIT) if n else 0.0,
        fees_paid=float(tr["fees"].sum()) if n else 0.0,
        avg_mae_pct=float(tr["mae_pct"].mean()) if n and "mae_pct" in tr else None,
        years={str(k): round(v, 4) for k, v in years.items()},
        green_years=int(sum(1 for v in years.values() if v > 0)),
        n_years=int(len(years)),
    )


def _v1(m):
    return {
        "g1_pf": bool((m["pf_pct"] is not None and np.isfinite(m["pf_pct"]) and
                       m["pf_pct"] > 1.2) or (m["pf_no_losses"] and m["return_pct"] > 0)),
        "g2_n": bool(m["n_trades"] >= 30),
        "g3_halves": bool(all((h is not None and np.isfinite(h) and h > 1.0) or
                              (h is None and m["pf_no_losses"])
                              for h in (m["is_pf"], m["os_pf"]))),
        "g4_years": bool(m["n_years"] > 0 and m["green_years"] >= (2.0 / 3.0) * m["n_years"]),
        "g5_beats_bh": bool(m["return_pct"] > m["bh_return_pct"]),
        "g6_conc": bool(m["conc_net_without_top5_pct"] > 0),
    }


def _v2(tr, curve, mkt_ret, breakeven, m):
    ret = tr["ret_pct"].to_numpy(float) if len(tr) else np.array([], float)
    e = tr["entry_ts"].to_numpy(np.int64) if len(tr) else np.array([], np.int64)
    x = tr["exit_ts"].to_numpy(np.int64) if len(tr) else np.array([], np.int64)
    lb, obs, blk = G2.expectancy_lb_bps(ret, n_boot=1000, seed=20261027) if len(ret) else (None, None, 0)
    eff_n = G2.effective_n(ret) if len(ret) else 0.0
    split = G2.purged_split(e, x, ret, 0.70, 30)
    folds, fold_frac, purged = G2.purged_folds(e, x, ret, 5, 10)
    buckets = G2.period_buckets(x, ret, "M", 5, -15.0, INIT, 6)
    ba = G2.beta_alpha_t(_bar_returns(curve), mkt_ret)
    tf = G2.top_frac_concentration(ret, 0.05, INIT)
    bm = G2.best_month_removal(e, ret, INIT)
    bw = G2.best_week_removal(x, ret, INIT)
    dd95 = G2.p95_max_dd(_bar_returns(curve))
    cost_share = None
    if len(tr):
        gp = float(tr.loc[tr["pnl"] > 0, "pnl"].sum())
        if gp > 0:
            cost_share = float(tr["fees"].sum() / gp)
    g8 = bool(m["profit_factor_stress"] is not None and
              np.isfinite(m["profit_factor_stress"]) and
              m["profit_factor_stress"] > 1.0 and
              cost_share is not None and cost_share <= 0.35)
    g6 = bool(tf["net_without_pct"] > 0 and bm["net_without_pct"] > 0
              and bw["net_without_pct"] > 0)
    gates = {
        "g1v2_exp_lb": bool(lb is not None and np.isfinite(lb) and lb > 0 and
                            m["pf_pct"] is not None and m["pf_pct"] > 1.2),
        "g2v2_n": bool(m["n_trades"] >= 100 and eff_n >= 50),
        "g3v2_split": bool(split["pass"] and fold_frac >= 0.70),
        "g4v2_buckets": bool(buckets["pass_floor"] and buckets["green_frac"] >= 0.60
                             and buckets["worst_pct"] >= -15.0),
        "g5v2_alpha": bool(np.isfinite(ba["t"]) and ba["t"] >= 2.0),
        "g6v2_conc": g6,
        "g8v2_cost": g8,
        "g9v2_dd": bool(dd95 is not None and np.isfinite(dd95) and dd95 <= 35.0),
    }
    detail = {
        "exp_lb_bps": _finite(lb), "exp_obs_bps": _finite(obs), "block": int(blk),
        "eff_n": float(eff_n),
        "split": split, "folds_frac": float(fold_frac), "folds": folds,
        "purged": int(purged),
        "buckets": {k: v for k, v in buckets.items() if k != "buckets"},
        "bucket_rows": buckets["buckets"],
        "beta": _finite(ba["beta"]), "alpha_bps_bar": _finite(ba["alpha_bps_per_bar"]),
        "alpha_t": _finite(ba["t"]),
        "conc5pct_share": float(tf["share_pct"]), "conc5pct_net": float(tf["net_without_pct"]),
        "best_month_net_pct": float(bm["net_without_pct"]),
        "best_week_net_pct": float(bw["net_without_pct"]),
        "cost_share": _finite(cost_share),
        "dd_p95": _finite(dd95),
        "breakeven_bps": _finite(breakeven),
    }
    return gates, detail


def _run(plan, costs, funding, sizing="declared"):
    kind = plan["kind"]
    if kind == "single":
        kw = dict(plan)
        for k in ("kind", "n_signals", "dst_dates", "df"):
            kw.pop(k, None)
        if sizing == "full":
            kw["risk_frac"] = None
            kw["size_frac"] = 1.0
        return C.sim_single(plan["df"], costs=costs, funding=funding,
                            init_equity=INIT, **kw)
    if kind == "pair":
        return C.sim_pair(plan["df_a"], plan["df_b"],
                          entry_at_open=plan["entry_at_open"],
                          exit_at_open=plan["exit_at_open"],
                          stop_at_close=plan["stop_at_close"],
                          entry_frac=plan["entry_frac"],
                          costs=costs,
                          fund_a=funding[0], fund_b=funding[1],
                          max_hold_bars=plan["max_hold_bars"],
                          spread_stop=plan["spread_stop"],
                          init_equity=INIT)
    if kind == "basket":
        return C.sim_basket(plan["dfs"], plan["target"], costs=costs,
                            fundings=funding, per_leg_stop=plan["per_leg_stop"],
                            book_stop=plan["book_stop"], init_equity=INIT)
    raise ValueError(kind)


def _benchmark(plan, klines):
    if plan["kind"] == "single":
        d = plan["df"]
        return float(100.0 * (d["close"].iloc[-1] / d["open"].iloc[0] - 1.0))
    if plan["kind"] == "pair":
        a, b = plan["df_a"], plan["df_b"]
        ra = a["close"].iloc[-1] / a["open"].iloc[0] - 1.0
        rb = b["close"].iloc[-1] / b["open"].iloc[0] - 1.0
        return float(100.0 * (0.5 * ra + 0.5 * rb))
    dfs = plan["dfs"]
    rs = [d["close"].iloc[-1] / d["open"].iloc[0] - 1.0 for d in dfs]
    return float(100.0 * np.mean(rs))


def _market_returns(plan):
    if plan["kind"] == "single":
        c = plan["df"]["close"].to_numpy(float)
    elif plan["kind"] == "pair":
        c = plan["df_b"]["close"].to_numpy(float)
    else:
        c = plan["dfs"][0]["close"].to_numpy(float)   # BTC is legs[0]
    return np.diff(c) / c[:-1]


def _bar_ts(plan):
    if plan["kind"] == "single":
        return plan["df"]["open_ts"].to_numpy(np.int64)
    if plan["kind"] == "pair":
        return plan["df_a"]["open_ts"].to_numpy(np.int64)
    return plan["dfs"][0]["open_ts"].to_numpy(np.int64)


def _us_dst(ts_ms):
    dt = pd.to_datetime(np.asarray(ts_ms, np.int64), unit="ms", utc=True)
    try:
        off = dt.tz_convert("America/New_York").strftime("%z")
        return np.array([o == "-0400" for o in off])
    except Exception:
        # fallback: approximate by month (Mar-Oct)
        mon = dt.month.to_numpy()
        return (mon >= 3) & (mon <= 10)


def run_one(paths, params):
    cand = int(params["cand"])
    spec = S.SPECS[cand]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    K, F = {}, {}
    for p in paths:
        b = os.path.basename(p)
        sym = b.split("_")[0]
        if b.endswith(".csv"):
            K[sym] = S.load_1h(sym, root)
        else:
            F[sym] = S.load_funding(sym, root)

    if cand in (1, 2, 3, 7):
        sym = spec["legs"][0]
        df = K[sym]
        plan = S.build_c1(df) if cand == 1 else S.build_c2(df) if cand == 2 \
            else S.build_c3(df) if cand == 3 else S.build_c7(df, root)
        plan["df"] = df
        funding = F[sym]
    elif cand in (4, 5):
        dfs = [K[s] for s in spec["legs"]]
        plan = S.build_c4(dfs) if cand == 4 else S.build_c5(dfs)
        funding = [F[s] for s in spec["legs"]]
    elif cand == 6:
        plan = S.build_c6(K["SOLUSDT"], K["BTCUSDT"], root)
        funding = (F["SOLUSDT"], F["BTCUSDT"])
    else:
        raise ValueError(cand)

    res = _run(plan, BASE, funding)
    tr, curve = res["trades"], res["equity"]
    bh = _benchmark(plan, K)
    m = _score(tr, curve, _bar_ts(plan), bh)
    m["bh_return_pct"] = bh

    # cost controls on the same signals
    res_repo = _run(plan, REPO, funding)
    res_stress = _run(plan, STRESS, funding)
    res_zero = _run(plan, ZERO, funding)
    m["return_repo_pct"] = float(100.0 * (res_repo["equity"][-1] / INIT - 1.0))
    m["profit_factor_repo"] = _finite(G2.profit_factor_pct(res_repo["trades"]["ret_pct"]))
    m["return_stress_pct"] = float(100.0 * (res_stress["equity"][-1] / INIT - 1.0))
    m["profit_factor_stress"] = _finite(G2.profit_factor_pct(res_stress["trades"]["ret_pct"]))
    m["return_zero_pct"] = float(100.0 * (res_zero["equity"][-1] / INIT - 1.0))
    m["profit_factor_zero"] = _finite(G2.profit_factor_pct(res_zero["trades"]["ret_pct"]))
    m["n_trades_repo"] = int(len(res_repo["trades"]))
    m["n_trades_zero"] = int(len(res_zero["trades"]))

    if plan["kind"] == "single":
        res_full = _run(plan, BASE, funding, sizing="full")
        m["return_fullsize_pct"] = float(100.0 * (res_full["equity"][-1] / INIT - 1.0))
        m["profit_factor_fullsize"] = _finite(G2.profit_factor_pct(res_full["trades"]["ret_pct"]))
        m["n_trades_fullsize"] = int(len(res_full["trades"]))
    else:
        m["return_fullsize_pct"] = None
        m["profit_factor_fullsize"] = None
        m["n_trades_fullsize"] = None

    # breakeven by real re-runs on total per-side cost
    def at_cost(t):
        return _run(plan, C.Costs(float(t), 0.0), funding)["trades"]
    be = None
    try:
        be, _ = G2.breakeven_side_cost(at_cost, lo=0.0, hi=100.0, iters=9)
    except Exception:
        be = None
    m["breakeven_bps"] = _finite(be)

    g1 = _v1(m)
    g2, det = _v2(tr, curve, _market_returns(plan), be, m)
    fails1 = [k.split("_")[0].upper() for k, v in g1.items() if not v]
    fails2 = [k[0:2].upper() + "v2" for k, v in g2.items() if not v]
    m.update({"gates_v1": g1, "fails_v1": fails1,
              "gates_v2": g2, "fails_v2": fails2,
              "n_fails_v1": len(fails1), "n_fails_v2": len(fails2),
              "gate2": det})
    m["declared"] = {
        "fee_bps": BASE.fee_bps, "slip_bps": BASE.slip_bps,
        "repo_fee_bps": REPO.fee_bps, "repo_slip_bps": REPO.slip_bps,
        "stress_fee_bps": STRESS.fee_bps, "stress_slip_bps": STRESS.slip_bps,
        "init_equity": INIT,
        "risk_frac": 0.005 if plan["kind"] == "single" else None,
        "max_leverage": 3.0 if plan["kind"] == "single" else 1.0,
    }
    m["declared"].update(S.DECLARED[cand])

    # candidate-specific diagnostics
    m["exit_reasons"] = ({str(k): int(v) for k, v in
                          tr["exit_reason"].value_counts().items()}
                         if len(tr) else {})
    if plan["kind"] == "single":
        m["n_signals"] = int(plan.get("n_signals", 0) or 0)
    elif plan["kind"] == "basket":
        m["n_signals"] = int(plan.get("n_trade", 0) or 0)
    else:
        m["n_signals"] = int(plan.get("n_signals", 0) or 0)
    if cand == 2:
        m["same_bar_stop_target"] = int(res.get("same_bar_stop_target", 0))
    if cand == 3:
        dst = _us_dst(tr["entry_ts"].to_numpy(np.int64)) if len(tr) else np.array([], bool)
        p = tr["pnl"].to_numpy(float) if len(tr) else np.array([], float)
        r = tr["ret_pct"].to_numpy(float) if len(tr) else np.array([], float)
        m["dst_n"] = int(dst.sum())
        m["non_dst_n"] = int((~dst).sum())
        m["dst_pf"] = _finite(G2.profit_factor_pct(r[dst]))
        m["non_dst_pf"] = _finite(G2.profit_factor_pct(r[~dst]))
        m["dst_return_pct"] = float(100.0 * p[dst].sum() / INIT)
        m["non_dst_return_pct"] = float(100.0 * p[~dst].sum() / INIT)
    if cand in (4, 5):
        days = len(_bar_ts(plan)) / 24.0
        m["turnover_per_day_pct"] = float(100.0 * res["turnover_units"] / max(days, 1e-9))
        m["book_kill_fired"] = int(res.get("book_kill_fired", 0))
        m["median_dispersion"] = _finite(plan.get("median_dispersion"))
        m["n_rebal"] = int(plan.get("n_rebal", 0))
        m["n_rebal_skipped"] = int(plan.get("n_rebal", 0)) - int(plan.get("n_trade", 0))
        m["funding_gross_paid_usdt"] = float(res.get("funding_gross_paid", 0.0))
        m["funding_gross_received_usdt"] = float(res.get("funding_gross_received", 0.0))
        m["gross_exposure"] = float(plan.get("gross", 0.0))
    if cand == 6:
        m["frac_abs_d_ge_25bps"] = float(plan.get("frac_abs_d_ge_25bps", 0.0))
        m["frac_d_le_neg25_bps"] = float(plan.get("frac_d_le_neg25_bps", 0.0))
        m["frac_d_ge_pos25_bps"] = float(plan.get("frac_d_ge_pos25_bps", 0.0))
        m["n_entry_long"] = int(plan.get("n_entry_long", 0))
        m["n_entry_short"] = int(plan.get("n_entry_short", 0))
        m["funding_sol"] = float(tr["funding_a"].sum()) if len(tr) else 0.0
        m["funding_btc"] = float(tr["funding_b"].sum()) if len(tr) else 0.0
    if cand == 7:
        m["funding_net_label"] = "short book receives when funding is positive"

    tables = {
        "cost_sensitivity": [
            {"cost": "declared_5.0_2.0", "return_pct": m["return_pct"],
             "pf": m["profit_factor"]},
            {"cost": "repo_5.0_0.5", "return_pct": m["return_repo_pct"],
             "pf": m["profit_factor_repo"]},
            {"cost": "stress_6.0_5.0", "return_pct": m["return_stress_pct"],
             "pf": m["profit_factor_stress"]},
            {"cost": "zero", "return_pct": m["return_zero_pct"],
             "pf": m["profit_factor_zero"]},
        ],
        "yearly_pnl": m["years"],
        "trades": tr.to_dict(orient="records") if len(tr) <= 2000 else [],
    }
    prov = {"adapter": "cand7", "engine_version": "cand7-1",
            "candidate": spec["code"], "candidate_name": spec["name"],
            "sizing": "0.5pct_risk_3x" if plan["kind"] == "single" else "fixed_gross",
            "cost_bps_per_side": [BASE.fee_bps, BASE.slip_bps],
            "funding_convention": "settlements in [entry,exit); at entry charged only if paying"}
    return m, prov, tables
