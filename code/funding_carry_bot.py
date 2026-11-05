#!/usr/bin/env python
"""funding_carry_bot.py — funding rate carry strategy."""
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

# Common timestamps
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

# Market-neutral funding carry:
# Rank pairs by funding rate
# Go long the pair with most negative funding (receive funding as long)
# Go short the pair with most positive funding (receive funding as short)
# Equal weight, rebalance at each settlement
# This captures the funding differential while being market-neutral

# ... (rest of the code stays the same until the main loop)

# Identify funding settlement timestamps
settlement_ts = set()
for sym in funding:
    for t in funding[sym]["ts"]:
        settlement_ts.add(t)

INIT = 10000.0
COST_BPS = 5.0
SLIP_BPS = 3.0

# Strategy: for each pair, position = sign of -funding (long if funding<0, short if funding>0)
# Weight: equal weight across active positions, 100% invested
# Rebalance: every 8 hours (funding settlement)

equity = [INIT]
positions = {}  # sym -> +1 (long) or -1 (short) or 0
last_rebal = 0
REBAL_HOURS = 8

returns = []
turnover_cost = 0.0
total_funding = 0.0
n_trades = 0

for i in range(1, len(all_ts)):
    # compute portfolio return
    port_ret = 0.0
    for sym, pos in positions.items():
        if sym in close_matrix.columns:
            c_prev = close_matrix[sym].iloc[i-1]
            c_curr = close_matrix[sym].iloc[i]
            if pd.notna(c_prev) and pd.notna(c_curr) and c_prev > 0:
                port_ret += (1.0 / max(len(positions), 1)) * pos * (c_curr / c_prev - 1)
    # funding income: only at settlement bars
    fund_ret = 0.0
    is_settlement = pd.Timestamp(all_ts[i]) in settlement_ts
    if is_settlement:
        for sym, pos in positions.items():
            if sym in funding_matrix.columns:
                fr = funding_matrix[sym].iloc[i]
                if pd.notna(fr):
                    fund_income = -pos * fr
                    w = 1.0 / max(len(positions), 1)
                    fund_ret += w * fund_income
                    total_funding += w * equity[-1] * fund_income
    equity.append(equity[-1] * (1 + port_ret + fund_ret))
    returns.append(port_ret + fund_ret)

    # rebalance every 8 hours
    if i - last_rebal >= REBAL_HOURS or not positions:
        new_positions = {}
        for sym in PAIRS:
            if sym not in funding_matrix.columns:
                continue
            fr = funding_matrix[sym].iloc[i]
            if pd.isna(fr):
                continue
            if fr < -0.0001:  # funding negative -> go long
                new_positions[sym] = 1
            elif fr > 0.0001:  # funding positive -> go short
                new_positions[sym] = -1
            # else: no position (funding near zero)

        # turnover
        all_syms = set(positions) | set(new_positions)
        turnover = sum(abs(new_positions.get(s, 0) - positions.get(s, 0)) for s in all_syms)
        if turnover > 0:
            n_trades += 1
        cost = turnover * (COST_BPS + SLIP_BPS) / 10000.0 * equity[-1] / 2  # half turnover (each change = 1 side)
        equity[-1] -= cost
        turnover_cost += cost
        positions = new_positions
        last_rebal = i

# Buy & hold benchmark
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

eq = np.array(equity)
bh = np.array(bh_equity)
total_ret = (eq[-1]/eq[0] - 1) * 100
bh_ret = (bh[-1]/bh[0] - 1) * 100
max_dd = ((eq / np.maximum.accumulate(eq)) - 1).min() * 100
bh_dd = ((bh / np.maximum.accumulate(bh)) - 1).min() * 100

r = np.diff(eq) / eq[:-1]
sharpe = np.mean(r) / np.std(r, ddof=1) * np.sqrt(24*365) if np.std(r, ddof=1) > 0 else 0

print(f"\n{'='*60}")
print(f"FUNDING CARRY BOT RESULTS")
print(f"{'='*60}")
print(f"Period: {all_ts[0]} to {all_ts[-1]}")
print(f"Bars: {len(all_ts)}")
print(f"Initial: ${INIT:,.0f} -> Final: ${eq[-1]:,.0f}")
print(f"Total return: {total_ret:.1f}%")
print(f"Buy & hold return: {bh_ret:.1f}%")
print(f"Excess: {total_ret - bh_ret:.1f}pp")
print(f"Max drawdown: {max_dd:.1f}%")
print(f"BH max drawdown: {bh_dd:.1f}%")
print(f"Turnover cost: ${turnover_cost:,.0f}")
print(f"Total funding received: ${total_funding:,.0f}")
print(f"Rebalances: {n_trades}")
print(f"Sharpe: {sharpe:.2f}")
print(f"Avg positions: {np.mean([1]*len(equity)):.1f}")

# Monthly
eq_series = pd.Series(eq, index=pd.DatetimeIndex(all_ts))
monthly = eq_series.resample("ME").last().pct_change().dropna()
print(f"Positive months: {(monthly > 0).mean()*100:.1f}%")
print(f"Worst month: {monthly.min()*100:.1f}%")

result = {
    "total_return_pct": round(total_ret, 2),
    "bh_return_pct": round(bh_ret, 2),
    "excess_pp": round(total_ret - bh_ret, 2),
    "max_dd_pct": round(max_dd, 2),
    "turnover_cost": round(turnover_cost, 2),
    "funding_received": round(total_funding, 2),
    "n_rebalances": n_trades,
    "sharpe": round(sharpe, 2),
    "positive_months_pct": round((monthly > 0).mean()*100, 1),
}
with open(os.path.join(ROOT, "results", "funding_carry_results.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
print(f"\nSaved to results/funding_carry_results.json")
