#!/usr/bin/env python
"""Quick grid test with fixed center on a specific window."""
import os, sys, json
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
DATA = os.path.join(ROOT, "data")

SYMBOL = "SUIUSDT"
CENTER = 0.8962
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
    return lower, upper, lower_stop, upper_stop, levels

lower, upper, lower_stop, upper_stop, levels = make_levels(CENTER)
cell_usdt = CAPITAL * LEVERAGE / N_GRIDS
qty_per_level = cell_usdt / CENTER

df = pd.read_csv(os.path.join(DATA, "binance_klines_1m", f"{SYMBOL}_1m.csv"))
df.columns = [c.strip().lower() for c in df.columns]
df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
df = df.sort_values("ts").reset_index(drop=True)

# Test window: 2026-02-16 to 2026-03-18
start = pd.Timestamp("2026-02-16", tz="UTC")
end = pd.Timestamp("2026-03-18", tz="UTC")
df = df[(df["ts"] >= start) & (df["ts"] < end)].reset_index(drop=True)
print(f"Window: {df['ts'].iloc[0]} to {df['ts'].iloc[-1]}, {len(df)} bars")
print(f"Price range: {df['low'].min():.4f} - {df['high'].max():.4f}, mean: {df['close'].mean():.4f}")

cash = CAPITAL
positions = []
filled_buys = set()
filled_sells = set()
equity_curve = []
n_fills = 0; n_tp = 0; n_stops = 0

for idx in range(len(df)):
    bar = df.iloc[idx]
    o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])

    if c <= lower_stop or c >= upper_stop:
        for pos in positions:
            li, side, qty, entry_px = pos
            if side == 1:
                cash += qty * c * (1 - TAKER_FEE)
            else:
                cash -= qty * c * (1 + TAKER_FEE)
        positions = []; filled_buys.clear(); filled_sells.clear()
        n_stops += 1
        equity_curve.append(cash)
        continue

    for i in range(N_GRIDS + 1):
        lvl = levels[i]
        if lvl >= CENTER: continue
        if l <= lvl and i not in filled_buys:
            fill_px = lvl * (1 + TAKER_FEE)
            cost = qty_per_level * fill_px * (1 + TAKER_FEE)
            if cash >= cost:
                cash -= cost
                positions.append((i, 1, qty_per_level, fill_px))
                filled_buys.add(i); n_fills += 1

    for i in range(N_GRIDS + 1):
        lvl = levels[i]
        if lvl <= CENTER: continue
        if h >= lvl and i not in filled_sells:
            fill_px = lvl * (1 - TAKER_FEE)
            cash += qty_per_level * fill_px * (1 - TAKER_FEE)
            positions.append((i, -1, qty_per_level, fill_px))
            filled_sells.add(i); n_fills += 1

    for i in list(filled_buys):
        if i + 1 > N_GRIDS: continue
        tp_lvl = levels[i + 1]
        if h >= tp_lvl:
            qty = qty_per_level
            fill_px = tp_lvl * (1 - TAKER_FEE)
            cash += qty * fill_px * (1 - TAKER_FEE)
            positions = [p for p in positions if not (p[0] == i and p[1] == 1)]
            filled_buys.discard(i); n_tp += 1; n_fills += 1

    for i in list(filled_sells):
        if i - 1 < 0: continue
        tp_lvl = levels[i - 1]
        if l <= tp_lvl:
            qty = qty_per_level
            fill_px = tp_lvl * (1 + TAKER_FEE)
            cash -= qty * fill_px * (1 + TAKER_FEE)
            positions = [p for p in positions if not (p[0] == i and p[1] == -1)]
            filled_sells.discard(i); n_tp += 1; n_fills += 1

    mtm = cash
    for pos in positions:
        li, side, qty, entry_px = pos
        mtm += qty * c if side == 1 else qty * (2 * entry_px - c)
    equity_curve.append(mtm)

eq = np.array(equity_curve)
total_ret = (eq[-1] / CAPITAL - 1) * 100
max_dd = ((eq / np.maximum.accumulate(eq)) - 1).min() * 100

print(f"\n{'='*50}")
print(f"FIXED CENTER {CENTER} — {len(df)} bars")
print(f"{'='*50}")
print(f"  Total return:  {total_ret:+.2f}%")
print(f"  Final equity:  ${eq[-1]:.2f}")
print(f"  Max drawdown:  {max_dd:.2f}%")
print(f"  Total fills:   {n_fills}")
print(f"  TP fills:      {n_tp}")
print(f"  Stops hit:     {n_stops}")
print(f"  Open positions: {len(positions)}")
print(f"  Min equity:    ${eq.min():.2f}")
print(f"  Max equity:    ${eq.max():.2f}")