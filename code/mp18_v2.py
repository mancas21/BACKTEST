#!/usr/bin/env python
"""mp18_v2.py — improved MP-18: market-neutral, short leg, funding filter."""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd
from itertools import product

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "code"))

PAIRS = ["ADAUSDT","AVAXUSDT","BNBUSDT","BTCUSDT","DOGEUSDT","ETHUSDT",
         "LINKUSDT","NEARUSDT","SOLUSDT","SUIUSDT","XRPUSDT"]

def load_1h(sym):
    p = os.path.join(DATA, "binance_klines_1h", f"{sym}_1h.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    d.columns = [c.strip().lower() for c in d.columns]
    d["ts"] = pd.to_datetime(d["open_ts"], unit="ms", utc=True)
    d = d.sort_values("ts").reset_index(drop=True)
    return d

def load_funding(sym):
    p = os.path.join(DATA, "binance_funding", f"{sym}_funding.json")
    if not os.path.exists(p):
        return None
    raw = json.load(open(p))
    rows = []
    for r in raw:
        t = r.get("t") or r.get("fundingTime")
        rate = r.get("r") or r.get("fundingRate")
        if rate is None:
            continue
        rows.append({"ts": pd.to_datetime(t, unit="ms", utc=True), "rate": float(rate)})
    return pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)

# Load data
prices = {}
funding = {}
for sym in PAIRS:
    df = load_1h(sym)
    if df is not None:
        prices[sym] = df
    fd = load_funding(sym)
    if fd is not None:
        funding[sym] = fd

all_ts = sorted(set().union(*[set(prices[s]["ts"]) for s in prices]))
close_matrix = pd.DataFrame(index=all_ts)
for sym in prices:
    s = prices[sym].set_index("ts")["close"]
    close_matrix[sym] = s.reindex(all_ts)

funding_matrix = pd.DataFrame(index=all_ts)
for sym in prices:
    if sym in funding:
        f = funding[sym].set_index("ts")["rate"]
        funding_matrix[sym] = f.reindex(all_ts, method="ffill")
    else:
        funding_matrix[sym] = np.nan

INIT = 10000.0
COST_BPS = 5.0
SLIP_BPS = 3.0
RT_COST = (COST_BPS + SLIP_BPS) / 10000.0  # per side

def mp18_v2_weights(close_matrix, funding_matrix, i, lookback=168, abs_gate=336,
                     top_n=2, bottom_n=2, use_funding_filter=False,
                     funding_threshold=0.0005):
    """Market-neutral: long top-N, short bottom-N by 168-bar ROC.
    Absolute gate: longs need 336-bar ROC > 0, shorts need 336-bar ROC < 0.
    Optional funding filter: skip longs with funding > threshold, shorts with funding < -threshold."""
    if i < abs_gate:
        return {}
    roc168 = {}
    roc336 = {}
    for sym in close_matrix.columns:
        c = close_matrix[sym].iloc[:i+1].dropna()
        if len(c) < abs_gate + 1:
            continue
        roc168[sym] = c.iloc[-1] / c.iloc[-1-lookback] - 1
        roc336[sym] = c.iloc[-1] / c.iloc[-1-abs_gate] - 1

    # Long candidates: positive 336-bar ROC
    long_candidates = [s for s in roc336 if roc336[s] > 0]
    # Short candidates: negative 336-bar ROC
    short_candidates = [s for s in roc336 if roc336[s] < 0]

    # Funding filter
    if use_funding_filter:
        fr = {}
        for sym in roc336:
            if sym in funding_matrix.columns:
                r = funding_matrix[sym].iloc[i]
                if pd.notna(r):
                    fr[sym] = r
        long_candidates = [s for s in long_candidates
                          if fr.get(s, 0) <= funding_threshold]
        short_candidates = [s for s in short_candidates
                           if fr.get(s, 0) >= -funding_threshold]

    if not long_candidates or not short_candidates:
        return {}

    # Rank and select
    long_ranked = sorted(long_candidates, key=lambda s: roc168[s], reverse=True)
    short_ranked = sorted(short_candidates, key=lambda s: roc168[s])  # most negative first

    longs = long_ranked[:top_n]
    shorts = short_ranked[:bottom_n]

    if not longs or not shorts:
        return {}

    w_long = 0.5 / len(longs)
    w_short = -0.5 / len(shorts)
    weights = {}
    for s in longs:
        weights[s] = w_long
    for s in shorts:
        weights[s] = w_short
    return weights

def backtest_variant(close_matrix, funding_matrix, all_ts, params):
    """Run a single variant and return metrics."""
    lookback = params["lookback"]
    abs_gate = params["abs_gate"]
    top_n = params["top_n"]
    bottom_n = params["bottom_n"]
    use_ff = params["use_funding_filter"]
    rebal = params["rebal_hours"]

    # Build settlement_ts
    settlement_ts = set()
    for sym in funding:
        for t in funding[sym]["ts"]:
            settlement_ts.add(t)

    # Precompute settlement flags
    is_settle = np.array([pd.Timestamp(ts) in settlement_ts for ts in all_ts])

    equity = [INIT]
    positions = {}
    last_rebal = 0
    turnover_cost = 0.0
    total_funding = 0.0
    n_rebalances = 0

    for i in range(1, len(all_ts)):
        # portfolio return
        port_ret = 0.0
        n_pos = len(positions)
        if n_pos > 0:
            for sym, pos in positions.items():
                if sym in close_matrix.columns:
                    c_prev = close_matrix[sym].iloc[i-1]
                    c_curr = close_matrix[sym].iloc[i]
                    if pd.notna(c_prev) and pd.notna(c_curr) and c_prev > 0:
                        port_ret += abs(pos) / n_pos * pos * (c_curr / c_prev - 1) if False else (1.0/n_pos) * pos * (c_curr / c_prev - 1)

        # funding at settlement
        fund_ret = 0.0
        is_settlement = bool(is_settle[i])
        if is_settlement and n_pos > 0:
            for sym, pos in positions.items():
                if sym in funding_matrix.columns:
                    fr = funding_matrix[sym].iloc[i]
                    if pd.notna(fr):
                        # only count at settlement (every 8h). Approximate by checking hour
                        if all_ts[i].hour % 8 == 0 and all_ts[i].minute == 0:
                            fund_income = -pos * fr
                            w = 1.0 / n_pos
                            fund_ret += w * fund_income
                            total_funding += w * equity[-1] * fund_income

        equity.append(equity[-1] * (1 + port_ret + fund_ret))

        # rebalance
        if i - last_rebal >= rebal or not positions:
            new_weights = mp18_v2_weights(
                close_matrix, funding_matrix, i,
                lookback=lookback, abs_gate=abs_gate,
                top_n=top_n, bottom_n=bottom_n,
                use_funding_filter=use_ff)
            if not new_weights:
                last_rebal = i
                continue

            new_positions = {s: (1 if w > 0 else -1) for s, w in new_weights.items()}

            all_syms = set(positions) | set(new_positions)
            turnover = sum(abs(new_positions.get(s, 0) - positions.get(s, 0)) for s in all_syms)
            cost = turnover * RT_COST * equity[-1] / 2
            equity[-1] -= cost
            turnover_cost += cost
            if turnover > 0:
                n_rebalances += 1
            positions = new_positions
            last_rebal = i

    # metrics
    eq = np.array(equity)
    total_ret = (eq[-1]/eq[0] - 1) * 100
    max_dd = ((eq / np.maximum.accumulate(eq)) - 1).min() * 100
    r = np.diff(eq) / eq[:-1]
    sharpe = np.mean(r) / np.std(r, ddof=1) * np.sqrt(24*365) if np.std(r, ddof=1) > 0 else 0

    # walk-forward: 70/30 split
    split = int(len(eq) * 0.7)
    is_ret = (eq[split-1]/eq[0] - 1) * 100
    oos_ret = (eq[-1]/eq[split-1] - 1) * 100
    is_dd = ((eq[:split] / np.maximum.accumulate(eq[:split])) - 1).min() * 100
    oos_dd = ((eq[split:] / np.maximum.accumulate(eq[split:])) - 1).min() * 100

    # monthly
    eq_series = pd.Series(eq, index=pd.DatetimeIndex(all_ts))
    monthly = eq_series.resample("ME").last().pct_change().dropna()
    pos_months = (monthly > 0).mean() * 100

    return {
        "total_ret": round(total_ret, 1),
        "max_dd": round(max_dd, 1),
        "sharpe": round(sharpe, 2),
        "is_ret": round(is_ret, 1),
        "oos_ret": round(oos_ret, 1),
        "is_dd": round(is_dd, 1),
        "oos_dd": round(oos_dd, 1),
        "pos_months": round(pos_months, 1),
        "turnover_cost": round(turnover_cost, 0),
        "funding": round(total_funding, 0),
        "n_rebal": n_rebalances,
    }

# Variant grid - reduced to key variants
variants = []
for lookback in [168]:
    for top_n in [2]:
        for bottom_n in [2]:
            for use_ff in [False, True]:
                for rebal in [168, 336]:
                    variants.append({
                        "lookback": lookback,
                        "abs_gate": 336,
                        "top_n": top_n,
                        "bottom_n": bottom_n,
                        "use_funding_filter": use_ff,
                        "rebal_hours": rebal,
                    })
# Add a few more lookbacks
for lookback in [84, 336]:
    variants.append({
        "lookback": lookback,
        "abs_gate": max(lookback*2, 336),
        "top_n": 2,
        "bottom_n": 2,
        "use_funding_filter": False,
        "rebal_hours": 168,
    })

print(f"Testing {len(variants)} variants...")
results = []
for v in variants:
    try:
        m = backtest_variant(close_matrix, funding_matrix, all_ts, v)
        m["variant"] = f"LB{v['lookback']}_T{v['top_n']}_B{v['bottom_n']}_FF{v['use_funding_filter']}"
        results.append(m)
        print(f"  {m['variant']}: ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}%")
    except Exception as e:
        print(f"  ERROR: {e}")

# Sort by Sharpe
results.sort(key=lambda x: x["sharpe"], reverse=True)
print(f"\n{'='*80}")
print(f"TOP 10 VARIANTS BY SHARPE")
print(f"{'='*80}")
for r in results[:10]:
    print(f"  {r['variant']}: ret={r['total_ret']}% dd={r['max_dd']}% sharpe={r['sharpe']} is={r['is_ret']}% oos={r['oos_ret']}% pos_months={r['pos_months']}%")

# Best variant
best = results[0]
print(f"\nBEST: {best['variant']}")
print(f"  Total return: {best['total_ret']}%")
print(f"  Max DD: {best['max_dd']}%")
print(f"  Sharpe: {best['sharpe']}")
print(f"  IS return: {best['is_ret']}%  OOS return: {best['oos_ret']}%")
print(f"  Positive months: {best['pos_months']}%")

with open(os.path.join(ROOT, "results", "mp18_v2_results.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nSaved to results/mp18_v2_results.json")
