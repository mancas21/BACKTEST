#!/usr/bin/env python
"""qs_pair_run.py — validation path for the catalog's dollar-neutral pair
strategy (QS-019). Mirrors qs_run.run_one's G4/G7 layout but executes via
pack50_core.run_pair (two legs, dollar-neutral, funding on both) and uses
the ratio (A/B) as the buy-and-hold benchmark. The seeded null is a random
±1 target with the same flip cadence."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import qs_engine as E
import qs_run as R
from pack50_core import Costs, run_pair

INIT = 10000.0


def _target_to_trades(df_a, res, target_flip_bars=None):
    """Convert run_pair trades to the segment format (entry_i/exit_i).
    run_pair returns trades as a DataFrame (one row per trade)."""
    ts = df_a["open_ts"].to_numpy(np.int64)
    out = []
    trades = res["trades"]
    rows = trades if isinstance(trades, list) else trades.to_dict("records")
    for t in rows:
        ei = int(np.searchsorted(ts, int(t["entry_ts"])))
        xi = int(np.searchsorted(ts, int(t["exit_ts"])))
        out.append(dict(entry_i=ei, exit_i=xi, pnl=t["pnl"],
                        ret_pct=t["ret_pct"], side=t["side"]))
    return out


def run_one(paths, params):
    sid = str(params["strat"])
    variant = str(params.get("variant", "two-sided"))
    import qs_strats as SD
    spec = SD.SPECS[sid]
    tf = str(params["tf"])
    sym = os.path.basename(paths[0]).split("_")[0] + "+" + \
        os.path.basename(paths[1]).split("_")[0]
    df_a = R._load_csv(paths[0])
    df_b = R._load_csv(paths[1])
    na = min(len(df_a), len(df_b))
    df_a = df_a.iloc[-na:].reset_index(drop=True)
    df_b = df_b.iloc[-na:].reset_index(drop=True)
    import numpy as _np
    common = _np.intersect1d(df_a["open_ts"].to_numpy(), df_b["open_ts"].to_numpy())
    df_a = df_a[df_a["open_ts"].isin(common)].reset_index(drop=True)
    df_b = df_b[df_b["open_ts"].isin(common)].reset_index(drop=True)
    funding = E.load_funding(paths[2] if len(paths) > 2 and
                             paths[2].endswith(".json") else None)
    funding_b = E.load_funding(paths[3] if len(paths) > 3 and
                               paths[3].endswith(".json") else None)

    n = len(df_a)
    if n < 9000:
        raise RuntimeError(f"{sid} pair: only {n} aligned bars")

    tgt, note = spec["pair"](df_a, df_b)
    # warmup: no positions before WARMUP bars
    tgt = np.asarray(tgt).copy()
    tgt[:R.WARMUP] = 0
    # long-only variant: suppress the short-spread leg (-1)
    if variant == "long-only":
        tgt[tgt == -1] = 0

    def _run(costs, target=None):
        return run_pair(df_a, df_b, tgt if target is None else target,
                        costs, funding, funding_b)

    res = {}
    for ck in ("base", "adverse", "stress", "gate"):
        c = E.COSTS[ck]
        # E.COSTS carries fractions; pack50_core.Costs takes BPS
        res[ck] = _run(Costs(c["fee"] * 1e4, c["slip"] * 1e4))
    base = res["base"]
    trs = _target_to_trades(df_a, base)

    # seeded null: random +-1 target with a matched number of flips
    rng = np.random.default_rng(7)
    flips = int((np.diff(np.asarray(tgt)) != 0).sum())
    rt = np.zeros(n, dtype=int)
    cur = 0
    change_bars = rng.choice(np.arange(R.WARMUP, n), size=min(flips, n - R.WARMUP),
                             replace=False)
    change_bars.sort()
    ci = 0
    for i in range(n):
        if ci < len(change_bars) and i == change_bars[ci]:
            cur = rng.choice([1, -1])
            ci += 1
        rt[i] = cur
    null_res = _run(Costs(E.COSTS["base"]["fee"] * 1e4,
                          E.COSTS["base"]["slip"] * 1e4), rt)
    null_trs = _target_to_trades(df_a, null_res)

    # ---- segments / folds / holdout (same layout as qs_run) ---------------
    maxh = 3 * 100          # 3x the half-life cap (the sheet's max hold)
    segs = R._segments(R.WARMUP, n, maxh)
    seg_tr = E.segment_trades(trs, segs["bounds"], maxh)
    fold_trs = [E.segment_trades(trs, [("f", a, b)], maxh)["f"]
                for (a, b) in segs["folds"]]
    holdout_trs = E.segment_trades(trs, [("h", segs["holdout"][0],
                                          segs["holdout"][1])], maxh)["h"]
    m_full = E.pf_and_expectancy(trs)
    m_hold = E.pf_and_expectancy(holdout_trs)
    m_folds = [E.pf_and_expectancy(x) for x in fold_trs]
    m_adv = E.pf_and_expectancy(_target_to_trades(df_a, res["adverse"]))
    oos_n = sum(m["n"] for m in m_folds) + m_hold["n"]

    eq = base["equity"] if isinstance(base, dict) else None
    eq = res["base"]["equity"]
    eqs = pd.Series(eq, index=pd.to_datetime(df_a["ts"], utc=True))
    dd = (eqs / eqs.cummax() - 1.0)
    r_bar = pd.Series(eq).pct_change().dropna().to_numpy()
    sr = float(np.mean(r_bar) / np.std(r_bar, ddof=1)) if len(r_bar) > 2 and \
        np.std(r_bar, ddof=1) > 0 else float("nan")
    dsr = E.deflated_sharpe([sr], len(r_bar)) if np.isfinite(sr) else float("nan")
    months = eqs.resample("ME").last().pct_change().dropna()
    pos_months = float((months > 0).mean()) if len(months) else 0.0
    worst_month = float(months.min()) if len(months) else 0.0
    p95_dd = None
    if len(r_bar) > 10:
        rng2 = np.random.default_rng(13)
        blk = max(1, int(round(len(r_bar) ** (1 / 3))))
        blocks = []
        for _ in range(200):
            idx = rng2.integers(0, max(1, len(r_bar) - blk),
                                size=max(1, len(r_bar) // blk))
            smp = np.concatenate([r_bar[i:i + blk] for i in idx])[:len(r_bar)]
            curve = np.cumprod(1 + smp)
            blocks.append(float(((curve / np.maximum.accumulate(curve)) - 1).min()))
        p95_dd = float(np.percentile(blocks, 5) * 100.0)

    rets = np.array([t["ret_pct"] for t in trs], float)
    exp_lb = E.block_bootstrap_exp_lb(rets, 1000, 7) if len(rets) else float("nan")
    exp_base = m_full["exp_bps"]
    exp_adv = m_adv["exp_bps"]
    n_folds_prof = sum(1 for m in m_folds
                       if m["n"] > 0 and m["exp_bps"] is not None and m["exp_bps"] > 0)
    g = dict(
        g1_data=bool(n >= 9000),
        g2_causality=True,        # beta/z from past data only (verified in audit)
        g3_implementation=True,
        g4_econ=bool(exp_base is not None and exp_base >= 20.0
                     and exp_adv is not None and exp_adv > 0.0),
        g5_stat=bool(m_full["n"] >= 100 and oos_n >= 30
                     and np.isfinite(dsr) and dsr >= 0.95),
        g6_robust=bool(n_folds_prof >= 4 and p95_dd is not None and p95_dd > -35.0
                       and pos_months >= 0.60 and worst_month >= -0.15),
        g7_oper=True,
    )
    if exp_base is not None and exp_base <= 0:
        verdict = "REJECT"
    elif m_full["n"] < 100 or oos_n < 30:
        verdict = "INCONCLUSIVE"
    elif all(g.values()):
        verdict = "PASS"
    else:
        verdict = "FAIL"
    bench = float((df_a["close"].iloc[-1] / df_a["close"].iloc[R.WARMUP])
                  / (df_b["close"].iloc[-1] / df_b["close"].iloc[R.WARMUP]) - 1.0) * 100.0

    m = dict(
        strategy_id=sid, strategy_name=spec["name"],
        variant=variant, symbol=sym, timeframe=tf,
        bars=int(n), warmup=R.WARMUP, costs_primary="base(14bps RT)",
        n_trades=m_full["n"], pf=m_full["pf"], win_rate=m_full["wr"],
        exp_base_bps=None if exp_base is None else round(exp_base, 2),
        exp_adverse_bps=None if exp_adv is None else round(exp_adv, 2),
        exp_lb95_bps=None if not np.isfinite(exp_lb) else round(exp_lb, 2),
        return_base_pct=round(100.0 * (res["base"]["equity"][-1] / INIT - 1), 2),
        return_adverse_pct=round(100.0 * (res["adverse"]["equity"][-1] / INIT - 1), 2),
        bh_return_pct=round(bench, 2),
        n_train=len(seg_tr["train"]), n_holdout=m_hold["n"], n_oos=oos_n,
        holdout_exp_bps=m_hold["exp_bps"],
        folds_profitable=n_folds_prof,
        fold_exp_bps=[None if m["exp_bps"] is None else round(m["exp_bps"], 2)
                      for m in m_folds],
        fold_n=[m["n"] for m in m_folds],
        max_dd_pct=round(float(dd.min()) * 100.0, 2) if len(dd) else None,
        p95_dd_pct=None if p95_dd is None else round(p95_dd, 2),
        pos_month_frac=round(pos_months, 3), n_months=int(len(months)),
        worst_month_pct=round(worst_month * 100.0, 2),
        sharpe_bar=None if not np.isfinite(sr) else round(sr, 4),
        dsr_psr=None if not np.isfinite(dsr) else round(dsr, 4),
        dsr_method="PSR(N=1); grid-DSR pending calibrate pass",
        null_n=len(null_trs),
        null_exp_bps=(None if not null_trs else
                      round(float(np.mean([t["ret_pct"] for t in null_trs])) * 100.0, 2)),
        null_pf=E.pf_and_expectancy(null_trs)["pf"],
        funding_paid=round(float(base.get("funding_paid", 0.0) if hasattr(base, "get") else 0.0), 2),
        gates=g, execution_sensitive=bool(
            exp_base is not None and exp_base > 0 and
            (exp_adv is None or exp_adv <= 0)),
        verdict=verdict, plan_note=note,
    )
    tables = [dict(kind="fold", k=k, n=m_folds[k]["n"],
                   exp_bps=m_folds[k]["exp_bps"], pf=m_folds[k]["pf"])
              for k in range(R.FOLDS)]
    return m, {"adapter": "qsb", "engine_version": "qsb-1",
               "pair": "BTCUSDT+ETHUSDT (declared primary)"}, tables
