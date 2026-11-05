#!/usr/bin/env python
"""mp18_deep.py — deepen MP-18 analysis: backtest with funding, variants, OOS."""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

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
    # normalize to DataFrame with ts, rate
    rows = []
    for r in raw:
        t = r.get("t") or r.get("fundingTime")
        rate = r.get("r") or r.get("fundingRate")
        if rate is None:
            continue
        rows.append({"ts": pd.to_datetime(t, unit="ms", utc=True), "rate": float(rate)})
    return pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)

# Load all data
prices = {}
for sym in PAIRS:
    df = load_1h(sym)
    if df is not None:
        prices[sym] = df
        print(f"{sym}: {len(df)} bars, {df['ts'].iloc[0]} to {df['ts'].iloc[-1]}")

# Common timestamp index
all_ts = sorted(set().union(*[set(prices[s]["ts"]) for s in prices]))
print(f"\nCommon bars: {len(all_ts)}")

# Build price matrix with NaN for missing (no ffill for returns calc)
close_matrix = pd.DataFrame(index=all_ts)
for sym in prices:
    s = prices[sym].set_index("ts")["close"]
    close_matrix[sym] = s.reindex(all_ts)  # NaN where missing

# Funding matrix
funding_matrix = pd.DataFrame(index=all_ts)
for sym in prices:
    fd = load_funding(sym)
    if fd is not None:
        f = fd.set_index("ts")["rate"]
        funding_matrix[sym] = f.reindex(all_ts, method="ffill")
    else:
        funding_matrix[sym] = 0.0

# MP-18 weight function
def mp18_weights(close_matrix, i, lookback=168, abs_gate=336, top_n=2):
    """Returns dict of {sym: weight} for bar i. Only considers pairs with data."""
    if i < abs_gate:
        return {}
    roc168 = {}
    roc336 = {}
    for sym in close_matrix.columns:
        c = close_matrix[sym].iloc[:i+1]
        # need at least abs_gate+1 non-NaN values
        valid = c.dropna()
        if len(valid) < abs_gate + 1:
            continue
        # use last valid price and price abs_gate bars ago (by position in valid series)
        roc168[sym] = valid.iloc[-1] / valid.iloc[-1-lookback] - 1
        roc336[sym] = valid.iloc[-1] / valid.iloc[-1-abs_gate] - 1
    # absolute gate: only positive 336-bar ROC
    candidates = [s for s in roc336 if roc336[s] > 0]
    if not candidates:
        return {}
    # rank by 168-bar ROC, pick top N
    ranked = sorted(candidates, key=lambda s: roc168[s], reverse=True)
    top = ranked[:top_n]
    w = 0.8 / top_n  # 80% invested, 20% cash
    return {s: w for s in top}

# Backtest
INIT = 10000.0
COST_BPS = 5.0  # per side
SLIP_BPS = 3.0  # per side
RT_COST = (COST_BPS + SLIP_BPS) * 2 / 10000.0  # round trip

equity = [INIT]
weights_prev = {}
rebal_every = 168  # weekly
last_rebal = 0

returns = []
turnover_cost = 0.0
total_funding = 0.0

for i in range(1, len(all_ts)):
    # compute portfolio return for this bar
    # weights from last rebalance
    port_ret = 0.0
    for sym, w in weights_prev.items():
        if sym in close_matrix.columns:
            c_prev = close_matrix[sym].iloc[i-1]
            c_curr = close_matrix[sym].iloc[i]
            if pd.notna(c_prev) and pd.notna(c_curr) and c_prev > 0:
                port_ret += w * (c_curr / c_prev - 1)
    # funding: charge funding on held positions
    fund_ret = 0.0
    for sym, w in weights_prev.items():
        if sym in funding_matrix.columns:
            fr = funding_matrix[sym].iloc[i]
            if pd.notna(fr):
                fund_ret -= w * fr
                total_funding += w * equity[-1] * (-fr)
    equity.append(equity[-1] * (1 + port_ret + fund_ret))
    returns.append(port_ret + fund_ret)

    # rebalance check
    if i - last_rebal >= rebal_every or not weights_prev:
        new_weights = mp18_weights(close_matrix, i)
        # compute turnover
        all_syms = set(weights_prev) | set(new_weights)
        turnover = sum(abs(new_weights.get(s, 0) - weights_prev.get(s, 0)) for s in all_syms)
        cost = turnover * (COST_BPS + SLIP_BPS) / 10000.0 * equity[-1]
        equity[-1] -= cost
        turnover_cost += cost
        weights_prev = new_weights
        last_rebal = i

# Buy & hold benchmark (equal weight all pairs)
bh_equity = [INIT]
for i in range(1, len(all_ts)):
    bh_ret = 0.0
    n = len(PAIRS)
    for sym in PAIRS:
        if sym in close_matrix.columns:
            c_prev = close_matrix[sym].iloc[i-1]
            c_curr = close_matrix[sym].iloc[i]
            if pd.notna(c_prev) and pd.notna(c_curr) and c_prev > 0:
                bh_ret += (1.0/n) * (c_curr / c_prev - 1)
    bh_equity.append(bh_equity[-1] * (1 + bh_ret))

# Metrics
eq = np.array(equity)
bh = np.array(bh_equity)
total_ret = (eq[-1]/eq[0] - 1) * 100
bh_ret = (bh[-1]/bh[0] - 1) * 100
max_dd = ((eq / np.maximum.accumulate(eq)) - 1).min() * 100
bh_dd = ((bh / np.maximum.accumulate(bh)) - 1).min() * 100

print(f"\n{'='*60}")
print(f"MP-18 BACKTEST RESULTS")
print(f"{'='*60}")
print(f"Period: {all_ts[0]} to {all_ts[-1]}")
print(f"Bars: {len(all_ts)}")
print(f"Initial equity: ${INIT:,.0f}")
print(f"Final equity: ${eq[-1]:,.0f}")
print(f"Total return: {total_ret:.1f}%")
print(f"Buy & hold return: {bh_ret:.1f}%")
print(f"Excess: {total_ret - bh_ret:.1f}pp")
print(f"Max drawdown: {max_dd:.1f}%")
print(f"BH max drawdown: {bh_dd:.1f}%")
print(f"Total turnover cost: ${turnover_cost:,.0f}")
print(f"Total funding paid: ${total_funding:,.0f}")
print(f"Final weights: {weights_prev}")

# Monthly returns
eq_series = pd.Series(eq, index=pd.DatetimeIndex(all_ts))
monthly = eq_series.resample("ME").last().pct_change().dropna()
print(f"\nMonths: {len(monthly)}")
print(f"Positive months: {(monthly > 0).mean()*100:.1f}%")
print(f"Worst month: {monthly.min()*100:.1f}%")
print(f"Best month: {monthly.max()*100:.1f}%")

# Sharpe
r = np.diff(eq) / eq[:-1]
sharpe = np.mean(r) / np.std(r, ddof=1) * np.sqrt(24*365) if np.std(r, ddof=1) > 0 else 0
print(f"Sharpe (annualized, hourly): {sharpe:.2f}")

# Save results
result = {
    "total_return_pct": round(total_ret, 2),
    "bh_return_pct": round(bh_ret, 2),
    "excess_pp": round(total_ret - bh_ret, 2),
    "max_dd_pct": round(max_dd, 2),
    "bh_max_dd_pct": round(bh_dd, 2),
    "turnover_cost": round(turnover_cost, 2),
    "funding_paid": round(total_funding, 2),
    "sharpe": round(sharpe, 2),
    "positive_months_pct": round((monthly > 0).mean()*100, 1),
    "worst_month_pct": round(monthly.min()*100, 2),
    "n_bars": len(all_ts),
    "n_pairs": len(PAIRS),
    "final_weights": weights_prev,
}
with open(os.path.join(ROOT, "results", "mp18_deep_results.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
print(f"\nSaved to results/mp18_deep_results.json")
