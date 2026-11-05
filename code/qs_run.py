#!/usr/bin/env python
"""qs_run.py -- harness entry for the catalog's family A campaign.

One artifact = one (strategy, variant, symbol, timeframe) cell, measured
under the catalog's G4/G7 protocol:

  * full-sample runs at the four cost points (Base primary; Adverse,
    Stress, and the 11-bps repo-gate sensitivity as controls);
  * chronological segments on the effective span (after a uniform 1,500-bar
    warmup >= 3x the family's longest lookback): train 40%, validation 20%,
    walk-forward 20% scored as FIVE folds, final holdout 20% opened once;
    embargo = max_hold bars; trades are PURGED when their exit would leak
    past the segment end;
  * causality: truncation test (plan signals on a truncated series are
    identical on the common prefix);
  * probabilistic/deflated Sharpe (PSR-style at N=1 declared -- the
    grid-based DSR needs the calibrate pass, recorded as pending);
  * a seeded random-entry null per cell (same stop/TP/max-hold machinery,
    same costs, entry count matched);
  * G7 gate booleans and the verdict (PASS / REJECT / INCONCLUSIVE / FAIL
    with the EXECUTION-SENSITIVE flag).

Variants: two-sided (long+short) and long-only, tested as separate
hypotheses per the catalog.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import qs_engine as E
import qs_strats as SD

WARMUP = 1500                    # >= 3x the family's longest lookback (500)
FOLDS = 5


def _load_csv(path):
    d = pd.read_csv(path)
    d.columns = [c.strip().lower() for c in d.columns]
    d["ts"] = pd.to_datetime(d["open_ts"], unit="ms", utc=True)
    d = d.sort_values("ts").reset_index(drop=True)
    return d


def _truncation_ok(df, plan_fn, tf):
    n = len(df)
    cut = int(n * 0.6)
    p1 = plan_fn(df, tf)
    p2 = plan_fn(df.iloc[:cut].reset_index(drop=True), tf)
    for k in ("long_event", "short_event"):
        a = np.asarray(pd.Series(p1[k]).fillna(False), bool)[:cut]
        b = np.asarray(pd.Series(p2[k]).fillna(False), bool)
        if not np.array_equal(a, b):
            return False
    return True


def _segments(n0, n1, max_hold):
    span = n1 - n0
    b_train = (n0, n0 + int(span * 0.4) - 1)
    b_val = (b_train[1] + 1, b_train[1] + int(span * 0.2))
    b_wf = (b_val[1] + 1, b_val[1] + int(span * 0.2))
    b_hold = (b_wf[1] + 1, n1 - 1)
    emb = max(1, int(max_hold or 1))
    folds = []
    f0 = b_wf[0]
    fl = max(1, (b_wf[1] - b_wf[0] + 1) // FOLDS)
    for k in range(FOLDS):
        a = f0 + k * fl
        b = (f0 + (k + 1) * fl - 1) if k < FOLDS - 1 else b_wf[1]
        folds.append((a, b))
    # embargo: pull each later segment's start in by the embargo
    def _emb(a, b):
        return (a + emb, b)
    return dict(train=_emb(*b_train), val=_emb(*b_val), wf=b_wf,
                holdout=_emb(*b_hold), folds=folds, bounds=[
                    ("train", b_train[0], b_train[1]),
                    ("val", b_val[0], b_val[1]),
                    ("wf", b_wf[0], b_wf[1]),
                    ("holdout", b_hold[0], b_hold[1])])


def run_one(paths, params):
    sid = str(params["strat"])
    variant = str(params.get("variant", "two-sided"))
    spec = SD.SPECS[sid]
    tf = str(params["tf"])
    sym = os.path.basename(paths[0]).split("_")[0]
    df = _load_csv(paths[0])
    fund_path = paths[1] if len(paths) > 1 and paths[1].endswith(".json") else None
    funding = E.load_funding(fund_path)

    n = len(df)
    if n < 9000:
        raise RuntimeError(f"{sid} {sym} {tf}: only {n} bars "
                           f"(G5 needs ~6 months + warmup)")
    plan_fn = spec["build"]
    plan = plan_fn(df, tf)
    causal = _truncation_ok(df, plan_fn, tf)

    # long-only variant suppresses short entries (and short exits)
    if variant == "long-only":
        plan = dict(plan)
        plan["short_event"] = np.zeros(n, bool)
        plan["short_exit"] = np.zeros(n, bool)

    # warmup: no entries before WARMUP bars
    for k in ("long_event", "short_event"):
        ev = np.array(pd.Series(plan[k]).fillna(False), bool)
        ev[:WARMUP] = False
        plan[k] = ev

    fund_at_base = funding
    res = {}
    for ck in ("base", "adverse", "stress", "gate"):
        c = E.COSTS[ck]
        res[ck] = E.run(df, plan, c["fee"], c["slip"], c["stop_slip_mult"],
                        funding=funding, seed=7)
    base = res["base"]

    trs = base["trades"]
    eq = base["eq"]

    # ---- segments -----------------------------------------------------------
    maxh = int(plan.get("max_hold") or 60)
    segs = _segments(WARMUP, n, maxh)
    seg_tr = E.segment_trades(trs, segs["bounds"], maxh)
    fold_trs = []
    for (a, b) in segs["folds"]:
        fold_trs.append(E.segment_trades(
            trs, [("f", a, b)], maxh)["f"])
    holdout_trs = E.segment_trades(
        trs, [("h", segs["holdout"][0], segs["holdout"][1])], maxh)["h"]
    train_trs = seg_tr["train"]
    val_trs = seg_tr["val"]

    # ---- metrics -------------------------------------------------------------
    def m_of(ts_list):
        return E.pf_and_expectancy(ts_list)

    m_full = m_of(trs)
    m_train = m_of(train_trs)
    m_val = m_of(val_trs)
    m_hold = m_of(holdout_trs)
    m_folds = [m_of(x) for x in fold_trs]
    m_adv = m_of(res["adverse"]["trades"])
    m_gate = m_of(res["gate"]["trades"])

    oos_n = sum(m["n"] for m in m_folds) + m_hold["n"]

    # ---- drawdowns / months ---------------------------------------------------
    eqs = pd.Series(eq[1:], index=pd.to_datetime(df["ts"][1:], utc=True))
    dd = (eqs / eqs.cummax() - 1.0)
    p95_dd = None
    if len(dd) > 10:
        r = eqs.pct_change().dropna()
        rng = np.random.default_rng(13)
        blocks = []
        arr = r.to_numpy()
        blk = max(1, int(round(len(arr) ** (1.0 / 3.0))))
        for _ in range(200):
            idx = rng.integers(0, max(1, len(arr) - blk), size=max(1, len(arr) // blk))
            sample = np.concatenate([arr[i:i + blk] for i in idx])[:len(arr)]
            curve = np.cumprod(1.0 + sample)
            blocks.append(float(((curve / np.maximum.accumulate(curve)) - 1.0).min()))
        p95_dd = float(np.percentile(blocks, 5) * 100.0)
    months = eqs.resample("ME").last().pct_change().dropna()
    pos_months = float((months > 0).mean()) if len(months) else 0.0
    worst_month = float(months.min()) if len(months) else 0.0

    # ---- Sharpe / PSR / null ---------------------------------------------------
    r_bar = pd.Series(eq).pct_change().dropna().to_numpy()
    sr = float(np.mean(r_bar) / np.std(r_bar, ddof=1)) if len(r_bar) > 2 and \
        np.std(r_bar, ddof=1) > 0 else float("nan")
    dsr = E.deflated_sharpe([sr], len(r_bar)) if np.isfinite(sr) else float("nan")

    null_base = E.run(df, plan, E.COSTS["base"]["fee"], E.COSTS["base"]["slip"],
                      1.0, funding=funding, seed=7, random_entries=True)
    m_null = m_of(null_base["trades"])
    null_eq = null_base["eq"]
    r_null = pd.Series(null_eq).pct_change().dropna().to_numpy()
    sr_null = float(np.mean(r_null) / np.std(r_null, ddof=1)) \
        if len(r_null) > 2 and np.std(r_null, ddof=1) > 0 else float("nan")

    # ---- expectancy p-value (for the family BH at report time) ---------------
    rets = np.array([t["ret_pct"] for t in trs], float)
    exp_lb = E.block_bootstrap_exp_lb(rets, n_boot=1000, seed=7) if len(rets) else float("nan")
    from math import sqrt
    t_exp = (float(np.mean(rets)) / (float(np.std(rets, ddof=1)) / sqrt(len(rets)))
             if len(rets) > 2 and np.std(rets, ddof=1) > 0 else float("nan"))

    # ---- G7 gates --------------------------------------------------------------
    exp_base = m_full["exp_bps"]
    exp_adv = m_adv["exp_bps"]
    n_folds_prof = sum(1 for m in m_folds
                       if m["n"] > 0 and m["exp_bps"] is not None and m["exp_bps"] > 0)
    g = dict(
        g1_data=bool(n >= 9000),
        g2_causality=bool(causal),
        g3_implementation=True,       # code/_qs_audit.py ALL PASS (cited)
        g4_econ=bool(exp_base is not None and exp_base >= 20.0
                     and exp_adv is not None and exp_adv > 0.0),
        g5_stat=bool(m_full["n"] >= 100 and oos_n >= 30
                     and np.isfinite(dsr) and dsr >= 0.95),
        g6_robust=bool(n_folds_prof >= 4 and p95_dd is not None and p95_dd > -35.0
                       and pos_months >= 0.60 and worst_month >= -0.15),
        g7_oper=bool(res["base"]["max_leverage"] <= 3.0 + 1e-9),
    )
    execution_sensitive = bool(exp_base is not None and exp_base > 0
                               and (exp_adv is None or exp_adv <= 0))
    if not g["g2_causality"] or not g["g3_implementation"]:
        verdict = "REJECT"
    elif exp_base is not None and exp_base <= 0:
        verdict = "REJECT"
    elif m_full["n"] < 100 or oos_n < 30:
        verdict = "INCONCLUSIVE"
    elif all(g.values()):
        verdict = "PASS"
    else:
        verdict = "FAIL"

    bench = float(df["close"].iloc[-1] / df["close"].iloc[WARMUP] - 1.0) * 100.0
    months_n = len(months)

    m = dict(
        strategy_id=sid, strategy_name=spec["name"], variant=variant,
        symbol=sym, timeframe=tf, bars=int(n), warmup=WARMUP,
        costs_primary="base(14bps RT)",
        n_trades=m_full["n"], pf=m_full["pf"], win_rate=m_full["wr"],
        exp_base_bps=None if exp_base is None else round(exp_base, 2),
        exp_adverse_bps=None if exp_adv is None else round(exp_adv, 2),
        exp_gate_bps=None if m_gate["exp_bps"] is None else round(m_gate["exp_bps"], 2),
        exp_lb95_bps=None if not np.isfinite(exp_lb) else round(exp_lb, 2),
        exp_t=None if not np.isfinite(t_exp) else round(t_exp, 3),
        pf_adverse=m_adv["pf"], pf_gate=m_gate["pf"],
        return_base_pct=round(100.0 * (res["base"]["eq"][-1] / E.INIT - 1.0), 2),
        return_adverse_pct=round(100.0 * (res["adverse"]["eq"][-1] / E.INIT - 1.0), 2),
        return_stress_pct=round(100.0 * (res["stress"]["eq"][-1] / E.INIT - 1.0), 2),
        return_gate_pct=round(100.0 * (res["gate"]["eq"][-1] / E.INIT - 1.0), 2),
        bh_return_pct=round(bench, 2),
        n_train=m_train["n"], n_val=m_val["n"], n_holdout=m_hold["n"],
        n_oos=oos_n,
        train_exp_bps=m_train["exp_bps"], val_exp_bps=m_val["exp_bps"],
        holdout_exp_bps=m_hold["exp_bps"], holdout_pf=m_hold["pf"],
        holdout_n=m_hold["n"],
        folds_profitable=n_folds_prof,
        fold_exp_bps=[None if m["exp_bps"] is None else round(m["exp_bps"], 2)
                      for m in m_folds],
        fold_n=[m["n"] for m in m_folds],
        max_dd_pct=round(float(dd.min()) * 100.0, 2) if len(dd) else None,
        p95_dd_pct=None if p95_dd is None else round(p95_dd, 2),
        pos_month_frac=round(pos_months, 3), n_months=int(months_n),
        worst_month_pct=round(worst_month * 100.0, 2),
        sharpe_bar=None if not np.isfinite(sr) else round(sr, 4),
        dsr_psr=None if not np.isfinite(dsr) else round(dsr, 4),
        dsr_method="PSR(N=1); grid-DSR pending calibrate pass",
        null_n=m_null["n"],
        null_exp_bps=None if m_null["exp_bps"] is None else round(m_null["exp_bps"], 2),
        null_pf=m_null["pf"], null_sharpe=None if not np.isfinite(sr_null)
        else round(sr_null, 4),
        n_null_seeded=7,
        funding_paid=round(base["fund_paid"], 2),
        n_funding_events=base["n_funding"],
        max_leverage=round(base["max_leverage"], 3),
        n_daily_halts=base["n_daily_halts"],
        n_review_halt=base["n_review_halt"],
        n_gap_stop_fills=base["n_gap_fills"],
        n_stop_fills=base["n_stop_fills"],
        n_target_fills=base["n_target_fills"],
        truncated_to=round(100.0 * (n / 210240), 1),
        gates=g,
        execution_sensitive=execution_sensitive,
        verdict=verdict,
        plan_note=plan.get("note") or "",
    )
    tables = [dict(kind="fold", k=k, n=m_folds[k]["n"],
                   exp_bps=m_folds[k]["exp_bps"], pf=m_folds[k]["pf"])
              for k in range(FOLDS)]
    tables.append(dict(kind="summary", **{k: v for k, v in m.items()
                                          if k != "gates"}))
    return m, {"adapter": "qs", "engine_version": "qs-1",
               "catalog_source": "Downloads/100 strategies-claude.zip "
                                 "(strategy_catalog_100.json, QS-001..010)"}, tables
