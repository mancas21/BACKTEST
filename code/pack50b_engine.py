#!/usr/bin/env python
"""pack50b_engine.py -- harness runner for the claude2 fifty-prompt pack.

One artifact = one numbered prompt on the symbol and timeframe the prompt names
(`crypto_strategy_prompts_50-claude2.md`, S01-S25 scalping, D01-D25 day trading).
The artifact measures, inside itself:

    * the pack's own cost block (0.05% fee + 0.02% slippage per side),
    * the SAME strategy re-run at the repo gate cost (5.0 + 0.5 bps per side),
    * the SAME strategy re-run with ZERO cost (the gross edge),
    * the 70/30 in-sample / out-of-sample split on entry time,
    * buy & hold over the same window,
    * perpetual funding charged at the settlement instants,
    * concentration and the gate verdicts (G1-G6).

Nothing is inferred from a previous run and no number is copied from the prompt
document; a prompt without its data on disk (S08, S23, D08, D18 need NVDA) is
never called and is reported NO DATA.

Sizing is full-equity compounding (the repo pack50 convention); the prompt
header's "1% of equity per trade" would rescale returns and drawdowns but not
profit factor, win rate, trade count or the cost share.

Data mapping (matches pack50_core.BASE_TF): 1m and 3m read the 1m taker files
(3m resampled), 5m reads 5m, 15m and 30m read the 15m taker files (30m
resampled), 1h reads 1h. SPXUSDT ("SPCX" in the prompts) exists only as PLAIN
1m/1h klines, so those files are used and resampled for its 5m/15m prompts;
the base timeframe is read from the file name and the resampler is identical
to pack50_core.load_tf's (pinned by the audit's parity check).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import pack50b_strats as SB
from pack50_core import (Costs, Plan, buy_and_hold, buy_and_hold_pair,
                         load_funding, load_tf, run_pair, run_plan,
                         split_metrics, summarise)

REPO_COSTS = Costs(fee_bps=5.0, slip_bps=0.5)


def _resample(d: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Identical recipe to pack50_core.load_tf's resample block."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last",
           "volume": "sum", "n_trades": "sum"}
    if d["taker_buy_base"].notna().any():
        agg["taker_buy_base"] = "sum"
    g = (d.set_index("ts").resample(rule, label="left", closed="left")
          .agg({k: v for k, v in agg.items() if k in d.columns})
          .dropna(subset=["open"]))
    g = g.reset_index()
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    g["open_ts"] = ((g["ts"] - epoch) // pd.Timedelta(milliseconds=1)).astype("int64")
    return g


def load_base_tf(path: str, tf: str) -> pd.DataFrame:
    """Load a kline file whose NATIVE timeframe is read from its file name
    (`<SYM>_<tf>.csv`) and resample to `tf` when finer."""
    base = os.path.basename(path).rsplit("_", 1)[1].split(".")[0]
    d = load_tf(path, base)          # native load; load_tf does not resample here
    if base == tf:
        return d
    from pack50_core import RULE
    return _resample(d, RULE[tf])


def _ctx_for(df: pd.DataFrame) -> dict:
    """S10's higher-timeframe filter: the 1h EMA50 slope, last CLOSED bar only."""
    d = df.copy()
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    g = (d.set_index("ts").resample("1h", label="left", closed="left")
          .agg({"close": "last"}).dropna())
    g["ema50"] = g["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    g["slope"] = g["ema50"] > g["ema50"].shift(1)
    g = g.reset_index()
    g["ready"] = g["ts"] + pd.Timedelta(hours=1)
    right = g[["ready", "slope"]].dropna().sort_values("ready")
    left = pd.DataFrame({"ts": d["ts"].sort_values()})
    left["ts"] = left["ts"].dt.as_unit("us")
    right["ready"] = right["ready"].dt.as_unit("us")
    merged = pd.merge_asof(left, right, left_on="ts", right_on="ready",
                           direction="backward")
    slope = merged["slope"].fillna(False).to_numpy(bool)
    return {"ema50_1h_slope": slope}


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
    spec = SB.SPECS[strat]
    if spec.get("no_data"):
        raise RuntimeError(f"prompt {SB.CODE[strat]} cannot be run: {spec['no_data']}")

    tf = spec["tf"]
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    fee, slip = SB.costs_for(spec["sym"].split("+")[0], tf)
    costs = Costs(fee_bps=fee, slip_bps=slip)

    pair = "pair" in spec
    if pair:
        df_a = load_base_tf(klines[0], tf)
        df_b = load_base_tf(klines[1], tf)
        n = min(len(df_a), len(df_b))
        df_a, df_b = df_a.iloc[-n:].reset_index(drop=True), df_b.iloc[-n:].reset_index(drop=True)
        common = np.intersect1d(df_a["open_ts"].to_numpy(), df_b["open_ts"].to_numpy())
        df_a = df_a[df_a["open_ts"].isin(common)].reset_index(drop=True)
        df_b = df_b[df_b["open_ts"].isin(common)].reset_index(drop=True)
        fa = load_funding(fund[0]) if len(fund) > 0 else (np.array([], np.int64), np.array([], float))
        fb = load_funding(fund[1]) if len(fund) > 1 else (np.array([], np.int64), np.array([], float))
        target, note = spec["pair"](df_a, df_b)
        res = run_pair(df_a, df_b, target, costs, fa, fb)
        df = df_a
        bh = buy_and_hold_pair(df_a, df_b)
        plan_note = note
    else:
        df = load_base_tf(klines[0], tf)
        f = load_funding(fund[0]) if fund else (np.array([], np.int64), np.array([], float))
        plan = spec["build"](df, _ctx_for(df)) if strat == 10 else spec["build"](df)
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
    m["prompt_code"] = SB.CODE[strat]
    m["symbol"] = spec["sym"]
    m["timeframe"] = tf
    m["fee_bps_per_side"] = fee
    m["slip_bps_per_side"] = slip
    m["cost_bp_roundtrip"] = 2.0 * (fee + slip)
    m["plan_note"] = plan_note
    m["bars"] = int(len(df))

    # repo-cost sensitivity on the SAME signals
    if pair:
        res2 = run_pair(df_a, df_b, target, REPO_COSTS, fa, fb)
    else:
        res2 = run_plan(df, plan, REPO_COSTS, f)
    m2 = summarise(res2["trades"], res2["equity"])
    m["repo_cost_ret_pct"] = m2["return_pct"]
    m["repo_cost_pf"] = m2["profit_factor"]
    m["repo_cost_n"] = m2["n_trades"]
    m["cost_swap_pp"] = m2["return_pct"] - m["return_pct"]

    # zero-cost control: separates "no edge" from "cost ate the edge"
    zero = Costs(fee_bps=0.0, slip_bps=0.0)
    if pair:
        res0 = run_pair(df_a, df_b, target, zero, fa, fb)
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
    return m, {"adapter": "pack50b", "engine_version": "pack50b-1"}, tables
