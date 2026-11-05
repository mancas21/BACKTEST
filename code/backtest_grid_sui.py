#!/usr/bin/env python
"""backtest_grid_sui.py — neutral grid backtest for SUIUSDT 1m (dynamic center)."""
from __future__ import annotations
import os, sys, json, math
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
DATA = os.path.join(ROOT, "data")

SYMBOL = "SUIUSDT"
WIDTH = 0.12
N_GRIDS = 40
CAPITAL = 100.0
LEVERAGE = 3.0
TAKER_FEE = 0.0005
STOP_BUF = 0.03

def make_levels(center):
    lower = center * (1 - WIDTH)
    upper = center * (1 + WIDTH)
    lower_stop = lower * (1 - STOP_BUF)
    upper_stop = upper * (1 + STOP_BUF)
    ratio = (upper / lower) ** (1.0 / N_GRIDS)
    levels = [lower * (ratio ** i) for i in range(N_GRIDS + 1)]
    return lower, upper, lower_stop, upper_stop, levels, ratio

print("Loading SUIUSDT 1m data...")
df = pd.read_csv(os.path.join(DATA, "binance_klines_1m", f"{SYMBOL}_1m.csv"))
df.columns = [c.strip().lower() for c in df.columns]
df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
df = df.sort_values("ts").reset_index(drop=True)
print(f"Total bars: {len(df)}, range: {df['ts'].iloc[0]} to {df['ts'].iloc[-1]}")

days = 30
cutoff = df["ts"].max() - pd.Timedelta(days=days)
df = df[df["ts"] >= cutoff].reset_index(drop=True)
print(f"Backtest window: {days} days, {len(df)} bars")

cash = CAPITAL
positions = []
filled_buys = set()
filled_sells = set()

equity_curve = []
trade_log = []
n_fills = 0
n_stops = 0
n_tp = 0
n_rebuilds = 0
stopped = False
cooldown = 0
grid_center = None
grid_levels = None
lower_stop = None
upper_stop = None
qty_per_level = None

for idx in range(len(df)):
    bar = df.iloc[idx]
    o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
    ts = bar["ts"]

    if cooldown > 0:
        cooldown -= 1
        mtm = cash
        for pos in positions:
            li, side, qty, entry_px = pos
            mtm += qty * c if side == 1 else qty * (2 * entry_px - c)
        equity_curve.append(mtm)
        continue

    if stopped:
        equity_curve.append(cash)
        continue

    if grid_center is None:
        grid_center = c
        lower, upper, lower_stop, upper_stop, grid_levels, ratio = make_levels(grid_center)
        cell_usdt = CAPITAL * LEVERAGE / N_GRIDS
        qty_per_level = cell_usdt / grid_center

    if c <= lower_stop or c >= upper_stop:
        for pos in positions:
            li, side, qty, entry_px = pos
            if side == 1:
                cash += qty * c * (1 - TAKER_FEE)
            else:
                cash -= qty * c * (1 + TAKER_FEE)
        positions = []
        filled_buys.clear()
        filled_sells.clear()
        n_stops += 1
        stopped = True
        trade_log.append({"ts": str(ts), "type": "STOP", "price": c})
        equity_curve.append(cash)
        continue

    if c > grid_center * 1.06 or c < grid_center * 0.94:
        for pos in positions:
            li, side, qty, entry_px = pos
            if side == 1:
                cash += qty * c * (1 - TAKER_FEE)
            else:
                cash -= qty * c * (1 + TAKER_FEE)
        positions = []
        filled_buys.clear()
        filled_sells.clear()
        grid_center = c
        lower, upper, lower_stop, upper_stop, grid_levels, ratio = make_levels(grid_center)
        cell_usdt = (cash if cash > 0 else CAPITAL) * LEVERAGE / N_GRIDS
        qty_per_level = cell_usdt / grid_center
        n_rebuilds += 1
        trade_log.append({"ts": str(ts), "type": "REBUILD", "price": c})
        equity_curve.append(cash)
        continue

    # Buy fills (below center)
    for i in range(N_GRIDS + 1):
        lvl = grid_levels[i]
        if lvl >= grid_center:
            continue
        if l <= lvl and i not in filled_buys:
            fill_px = lvl * (1 + TAKER_FEE)
            cost = qty_per_level * fill_px * (1 + TAKER_FEE)
            if cash >= cost:
                cash -= cost
                positions.append((i, 1, qty_per_level, fill_px))
                filled_buys.add(i)
                n_fills += 1

    # Sell fills (above center)
    for i in range(N_GRIDS + 1):
        lvl = grid_levels[i]
        if lvl <= grid_center:
            continue
        if h >= lvl and i not in filled_sells:
            fill_px = lvl * (1 - TAKER_FEE)
            cash += qty_per_level * fill_px * (1 - TAKER_FEE)
            positions.append((i, -1, qty_per_level, fill_px))
            filled_sells.add(i)
            n_fills += 1

    # Long TP
    for i in list(filled_buys):
        if i + 1 > N_GRIDS:
            continue
        tp_lvl = grid_levels[i + 1]
        if h >= tp_lvl:
            qty = qty_per_level
            fill_px = tp_lvl * (1 - TAKER_FEE)
            cash += qty * fill_px * (1 - TAKER_FEE)
            positions = [p for p in positions if not (p[0] == i and p[1] == 1)]
            filled_buys.discard(i)
            n_tp += 1
            n_fills += 1

    # Short TP
    for i in list(filled_sells):
        if i - 1 < 0:
            continue
        tp_lvl = grid_levels[i - 1]
        if l <= tp_lvl:
            qty = qty_per_level
            fill_px = tp_lvl * (1 + TAKER_FEE)
            cash -= qty * fill_px * (1 + TAKER_FEE)
            positions = [p for p in positions if not (p[0] == i and p[1] == -1)]
            filled_sells.discard(i)
            n_tp += 1
            n_fills += 1

    mtm = cash
    for pos in positions:
        li, side, qty, entry_px = pos
        mtm += qty * c if side == 1 else qty * (2 * entry_px - c)
    equity_curve.append(mtm)

eq = np.array(equity_curve)
total_ret = (eq[-1] / CAPITAL - 1) * 100
max_dd = ((eq / np.maximum.accumulate(eq)) - 1).min() * 100

print(f"\n{'='*60}")
print(f"GRID BACKTEST RESULTS — {SYMBOL} 1m, {days} days (dynamic center)")
print(f"{'='*60}")
print(f"  Total return:  {total_ret:+.2f}%")
print(f"  Final equity:  ${eq[-1]:.2f}")
print(f"  Max drawdown:  {max_dd:.2f}%")
print(f"  Total fills:   {n_fills}")
print(f"  TP fills:      {n_tp}")
print(f"  Stops hit:     {n_stops}")
print(f"  Rebuilds:      {n_rebuilds}")
print(f"  Open positions: {len(positions)}")
print(f"  Cash:          ${cash:.2f}")
print(f"  Min equity:    ${eq.min():.2f}")
print(f"  Max equity:    ${eq.max():.2f}")

out = {
    "symbol": SYMBOL, "days": days, "bars": len(df),
    "total_ret_pct": round(total_ret, 2), "final_equity": round(float(eq[-1]), 2),
    "max_dd_pct": round(max_dd, 2), "n_fills": n_fills, "n_tp": n_tp,
    "n_stops": n_stops, "n_rebuilds": n_rebuilds, "open_positions": len(positions),
    "min_equity": round(float(eq.min()), 2), "max_equity": round(float(eq.max()), 2),
}
with open(os.path.join(ROOT, "results", "grid_sui_backtest.json"), "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to results/grid_sui_backtest.json")