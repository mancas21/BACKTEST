#!/usr/bin/env python
"""pack50_engine.py -- harness runner for the fifty-strategy prompt pack.

One artifact = one numbered prompt on the symbol and timeframe the prompt names.
The artifact measures, inside itself:

    * the pack's own cost block (0.04/0.05% taker + 0.02/0.05% slippage),
    * the SAME strategy re-run at the repo gate cost (5.0 + 0.5 bps per side),
      so the cost sensitivity is measured rather than assembled by the reader,
    * the 70/30 in-sample / out-of-sample split the prompt asks for,
    * buy & hold over the same window,
    * perpetual funding actually charged at the settlement instants,
    * concentration and the gate verdicts (G1-G6).

Nothing is inferred from a previous run and no number is copied from the prompt
document; if a strategy cannot be run (S34, S49 need NVDA data) the adapter is
never called and the report says NO DATA.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import pack50_strats as S
from pack50_core import (Costs, Plan, _funding_cash, buy_and_hold,
                         buy_and_hold_pair, load_funding, load_tf, run_pair,
                         run_plan, split_metrics, summarise)

REPO_COSTS = Costs(fee_bps=5.0, slip_bps=0.5)


def _ctx_for(df: pd.DataFrame, strat: int) -> dict:
    """Cross-timeframe context. Only completed higher-timeframe bars are used."""
    if strat != 6:
        return {}
    d = df.copy()
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    g = (d.set_index("ts").resample("4h", label="left", closed="left")
          .agg({"close": "last"}).dropna())
    g["ema50"] = g["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    g["slope"] = g["ema50"] > g["ema50"].shift(1)
    # a 4h bar closing at T is only known at T; map it forward from T onward
    g = g.reset_index()
    g["ready"] = g["ts"] + pd.Timedelta(hours=4)
    right = g[["ready", "slope"]].dropna().sort_values("ready")
    left = pd.DataFrame({"ts": d["ts"].sort_values()})
    left["ts"] = left["ts"].dt.as_unit("us")
    right["ready"] = right["ready"].dt.as_unit("us")
    merged = pd.merge_asof(left, right, left_on="ts", right_on="ready",
                           direction="backward")
    slope = merged["slope"].fillna(False).to_numpy(bool)
    return {"ema50_4h_slope": slope}


def _turtle(df: pd.DataFrame, costs: Costs, funding, init=10000.0) -> dict:
    """S10: 20-day breakout, units every 0.5 ATR, stop 2 ATR from the last entry,
    exit on the 10-day low, four units maximum."""
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    o = df["open"].to_numpy(float)
    ts = (df["open_ts"] if "open_ts" in df else df["ts"].astype("int64") // 10**6).to_numpy(np.int64)
    a = S.atr(h, l, c, 14)
    hh20 = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy()
    ll10 = pd.Series(l).rolling(10, min_periods=10).min().shift(1).to_numpy()
    f_ts, f_rate = funding
    n = len(c)

    eq = init
    curve = np.full(n, init)
    units = []            # (qty, px)
    last_add_px = np.nan
    entry_ts = 0
    entry_i = -1
    rows = []
    fees = funding_paid = 0.0
    fee_in = 0.0
    pend_entry = False

    def _close_all(i, lvl, why):
        nonlocal eq, units, fees, funding_paid, entry_ts, entry_i
        tot_q = sum(q for q, _ in units)
        px = lvl
        gross = sum(q * (px - p) for q, p in units)
        fee = tot_q * px * costs.fee_bps / 1e4
        fcash, nf = _funding_cash(f_ts, f_rate, entry_ts, int(ts[i]), ts, c, tot_q, 1)
        avg = sum(q * p for q, p in units) / tot_q
        pnl_eq = gross - fee + fcash
        pnl = pnl_eq - fee_in
        eq += pnl_eq
        fees += fee
        funding_paid += -fcash
        rows.append(dict(entry_ts=entry_ts, exit_ts=int(ts[i]), side=1,
                         entry_px=avg, exit_px=px, qty=tot_q, pnl=pnl,
                         ret_pct=100.0 * pnl / max(eq - pnl_eq, 1e-9),
                         bars=i - entry_i, exit_reason=why, fees=fee + fee_in,
                         funding=fcash, n_funding=nf, equity_after=eq,
                         units=len(units)))
        units = []

    for i in range(n):
        if pend_entry and not units:
            px = o[i]
            q = (eq * 0.25) / px
            fee = q * px * costs.fee_bps / 1e4
            eq -= fee
            fees += fee
            units = [(q, px)]
            last_add_px = px
            entry_ts, entry_i = int(ts[i]), i
            fee_in = fee
            pend_entry = False

        if units:
            # add a unit every 0.5 ATR above the last entry, capped at four
            if len(units) < 4 and c[i] >= last_add_px + 0.5 * a[i]:
                px = c[i]
                q = (eq * 0.25) / px
                fee = q * px * costs.fee_bps / 1e4
                eq -= fee
                fees += fee
                fee_in += fee
                units.append((q, px))
                last_add_px = px
            stop = last_add_px - 2.0 * a[i]
            if l[i] <= stop:
                _close_all(i, stop, "stop")
            elif c[i] < ll10[i]:
                _close_all(i, o[i], "signal")
        elif c[i] > hh20[i]:
            pend_entry = True

        curve[i] = eq + sum(q * (c[i] - p) for q, p in units)

    if units:
        _close_all(n - 1, c[-1], "end_of_data")
        curve[-1] = eq

    tr = pd.DataFrame(rows)
    return {"trades": tr, "equity": curve, "fees": fees,
            "funding": funding_paid, "final_equity": eq}


def _gates(m: dict, tr: pd.DataFrame, years: dict) -> dict:
    good_years = sum(1 for v in years.values() if v > 0)
    tot_years = len(years)
    pf = m["profit_factor"]
    g1 = bool((pf is not None and pf > 1.2) or
              (m.get("pf_no_losses") and m["return_pct"] > 0))
    halves = [m["is_pf"], m["os_pf"]]
    g3 = bool(all((h is not None and h > 1.0) or
                  (h is None and m.get("pf_no_losses")) for h in halves))
    return {
        "g1_pf": g1,
        "g2_n": bool(m["n_trades"] >= 30),
        "g3_halves": g3,
        "g4_years": bool(tot_years > 0 and good_years >= (2.0 / 3.0) * tot_years),
        "g5_beats_bh": bool(m["return_pct"] > m["bh_return_pct"]),
        "g6_conc": bool(m["conc_net_without_top5_pct"] > 0),
        "green_years": int(good_years), "n_years": int(tot_years),
    }


def run_one(paths, params):
    strat = int(params["strat"])
    spec = S.SPECS[strat]
    if spec.get("no_data"):
        raise RuntimeError(f"S{strat} cannot be run: {spec['no_data']}")

    tf = spec["tf"]
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    fee, slip = S.costs_for(spec["sym"].split("+")[0], tf)
    costs = Costs(fee_bps=fee, slip_bps=slip)

    pair = "pair" in spec
    if pair:
        df_a = load_tf(klines[0], tf)
        df_b = load_tf(klines[1], tf)
        n = min(len(df_a), len(df_b))
        df_a, df_b = df_a.iloc[-n:].reset_index(drop=True), df_b.iloc[-n:].reset_index(drop=True)
        # align on the timestamp
        common = np.intersect1d(df_a["open_ts"].to_numpy(), df_b["open_ts"].to_numpy())
        df_a = df_a[df_a["open_ts"].isin(common)].reset_index(drop=True)
        df_b = df_b[df_b["open_ts"].isin(common)].reset_index(drop=True)
        fa = load_funding(fund[0]) if len(fund) > 0 else (np.array([], np.int64), np.array([], float))
        fb = load_funding(fund[1]) if len(fund) > 1 else (np.array([], np.int64), np.array([], float))
        if strat == 33:
            target, note = spec["pair"](df_a, df_b, fa, fb)
        else:
            target, note = spec["pair"](df_a, df_b)
        res = run_pair(df_a, df_b, target, costs, fa, fb)
        df = df_a
        bh = buy_and_hold_pair(df_a, df_b)
        plan_note = note
    elif spec["build"] is S.b10:
        df = load_tf(klines[0], tf)
        f = load_funding(fund[0]) if fund else (np.array([], np.int64), np.array([], float))
        res = _turtle(df, costs, f)
        bh = buy_and_hold(df)
        plan_note = "units every 0.5 ATR, stop 2 ATR from the last entry, 10-day low exit"
    else:
        df = load_tf(klines[0], tf)
        ctx = _ctx_for(df, strat)
        plan = spec["build"](df, ctx) if strat == 6 else spec["build"](df)
        f = load_funding(fund[0]) if fund else (np.array([], np.int64), np.array([], float))
        res = run_plan(df, plan, costs, f)
        bh = buy_and_hold(df)
        plan_note = plan.note if isinstance(plan, Plan) else ""

    tr = res["trades"]
    m = summarise(tr, res["equity"])
    split_ts = int(df["open_ts"].to_numpy()[int(len(df) * 0.7)])
    m.update(split_metrics(tr, split_ts))
    m.update(bh)
    m["funding_charged"] = bool(len(fund) > 0)
    m["strategy_id"] = strat
    m["strategy_name"] = spec["name"]
    m["symbol"] = spec["sym"]
    m["timeframe"] = tf
    m["fee_bps_per_side"] = fee
    m["slip_bps_per_side"] = slip
    m["cost_bp_roundtrip"] = 2.0 * (fee + slip)
    m["plan_note"] = plan_note
    m["bars"] = int(len(df))

    # measured repo-cost sensitivity on the SAME signals
    if pair:
        res2 = run_pair(df_a, df_b, target, REPO_COSTS,
                        load_funding(fund[0]) if len(fund) > 0 else None,
                        load_funding(fund[1]) if len(fund) > 1 else None)
    elif spec["build"] is S.b10:
        res2 = _turtle(df, REPO_COSTS, f)
    else:
        res2 = run_plan(df, plan, REPO_COSTS, f)
    m2 = summarise(res2["trades"], res2["equity"])
    m["repo_cost_ret_pct"] = m2["return_pct"]
    m["repo_cost_pf"] = m2["profit_factor"]
    m["repo_cost_n"] = m2["n_trades"]
    m["cost_swap_pp"] = m2["return_pct"] - m["return_pct"]

    # zero-cost control: the same signals with fees and slippage switched off.
    # This separates "the rule has no edge" from "the cost block ate the edge".
    zero = Costs(fee_bps=0.0, slip_bps=0.0)
    if pair:
        res0 = run_pair(df_a, df_b, target, zero,
                        load_funding(fund[0]) if len(fund) > 0 else None,
                        load_funding(fund[1]) if len(fund) > 1 else None)
    elif spec["build"] is S.b10:
        res0 = _turtle(df, zero, f)
    else:
        res0 = run_plan(df, plan, zero, f)
    m0 = summarise(res0["trades"], res0["equity"])
    m["zero_cost_ret_pct"] = m0["return_pct"]
    m["zero_cost_pf"] = m0["profit_factor"]
    m["zero_cost_win_rate"] = m0["win_rate"]
    m["gross_edge_exists"] = bool(m0["profit_factor"] is not None and m0["profit_factor"] > 1.2)

    # per-year PnL, from the trades themselves
    years = {}
    if len(tr):
        yr = pd.to_datetime(tr["entry_ts"], unit="ms", utc=True).dt.year
        for y, g in tr.groupby(yr):
            years[int(y)] = float(g["pnl"].sum())
    m["green_years_map"] = {str(k): v for k, v in sorted(years.items())}
    m.update(_gates(m, tr, years))

    tables = [{"year": y, "pnl": v} for y, v in sorted(years.items())]
    return m, {"adapter": "pack50", "engine_version": "pack50-1"}, tables
