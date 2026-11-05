#!/usr/bin/env python
"""backtest_grid_sui_wf_v2.py — 7-day walk-forward neutral grid for SUIUSDT, aligned with user's setup."""
from __future__ import annotations
import os, sys, json, time
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
WINDOW_DAYS = 7

def make_levels(center):
    lower = center * (1 - WIDTH)
    upper = center * (1 + WIDTH)
    lower_stop = lower * (1 - STOP_BUF)
    upper_stop = upper * (1 + STOP_BUF)
    ratio = (upper / lower) ** (1.0 / N_GRIDS)
    levels = [lower * (ratio ** i) for i in range(N_GRIDS + 1)]
    return lower, upper, lower_stop, upper_stop, levels, ratio

# Load data
print("Loading SUIUSDT 1m data...")
df = pd.read_csv(os.path.join(DATA, "binance_klines_1m", f"{SYMBOL}_1m.csv"))
df.columns = [c.strip().lower() for c in df.columns]
df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
df = df.sort_values("ts").reset_index(drop=True)
print(f"Total bars: {len(df)}, range: {df['ts'].iloc[0]} to {df['ts'].iloc[-1]}")

# Find all 17:00 UTC bars
df["hour"] = df["ts"].dt.hour
df["minute"] = df["ts"].dt.minute
window_starts = df[(df["hour"] == 17) & (df["minute"] == 0)].index.tolist()
print(f"Found {len(window_starts)} 17:00 UTC bars")

# Limit to user's period: 9-Jun to 31-Oct 2026
target_start = pd.Timestamp("2026-06-09", tz="UTC")
start_idx = 0
for idx in window_starts:
    if df.iloc[idx]["ts"] >= target_start:
        start_idx = idx
        break
window_starts = [ws for ws in window_starts if ws >= start_idx]
print(f"Limited to {len(window_starts)} windows from {df.iloc[window_starts[0]]['ts']}")

BARS_PER_WINDOW = WINDOW_DAYS * 24 * 60
window_results = []
equity = CAPITAL
t0 = time.time()

for wi, start_idx in enumerate(window_starts):
    if start_idx + BARS_PER_WINDOW > len(df):
        print(f"  Window {wi}: not enough data, stopping")
        break
    if start_idx < 1:
        continue

    window = df.iloc[start_idx:start_idx + BARS_PER_WINDOW].reset_index(drop=True)
    center = float(window.iloc[0]["close"])  # close of 17:00 UTC bar
    
    lower, upper, lower_stop, upper_stop, levels, ratio = make_levels(center)
    cell_usdt = (equity if equity > 0 else CAPITAL) * LEVERAGE / N_GRIDS
    qty_per_level = cell_usdt / center

    w_min = window["low"].min()
    w_max = window["high"].max()

    # Simulate grid within window
    cash = equity
    positions = []
    filled_buys = set()
    filled_sells = set()
    n_fills = 0
    n_tp = 0
    n_stops = 0

    for idx in range(len(window)):
        bar = window.iloc[idx]
        o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])

        # Buy fills (below center)
        for i in range(N_GRIDS + 1):
            lvl = levels[i]
            if lvl >= center:
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
            lvl = levels[i]
            if lvl <= center:
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
            tp_lvl = levels[i + 1]
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
            tp_lvl = levels[i - 1]
            if l <= tp_lvl:
                qty = qty_per_level
                fill_px = tp_lvl * (1 + TAKER_FEE)
                cash -= qty * fill_px * (1 + TAKER_FEE)
                positions = [p for p in positions if not (p[0] == i and p[1] == -1)]
                filled_sells.discard(i)
                n_tp += 1
                n_fills += 1

    # End of window: close all positions at last close
    last_c = float(window.iloc[-1]["close"])
    for pos in positions:
        li, side, qty, entry_px = pos
        if side == 1:
            cash += qty * last_c * (1 - TAKER_FEE)
        else:
            cash -= qty * last_c * (1 + TAKER_FEE)
    n_open = len(positions)

    window_pnl = cash - equity
    window_ret = (cash / equity - 1) * 100 if equity > 0 else 0

    window_results.append({
        "window": wi,
        "start": str(window.iloc[0]["ts"]),
        "center": round(center, 6),
        "end_price": round(last_c, 6),
        "price_range": f"{w_min:.4f}-{w_max:.4f}",
        "n_fills": n_fills,
        "n_tp": n_tp,
        "n_open_closed": n_open,
        "equity_before": round(equity, 2),
        "equity_after": round(cash, 2),
        "pnl": round(window_pnl, 2),
        "ret_pct": round(window_ret, 2),
        "win": window_pnl > 0,
    })

    equity = cash

    if wi % 50 == 0:
        print(f"  Processed {wi}/{len(window_starts)} windows, equity=${equity:.2f}")

total_ret = (equity / CAPITAL - 1) * 100
wins = sum(1 for w in window_results if w["win"])
losses = len(window_results) - wins
gross_profit = sum(w["pnl"] for w in window_results if w["pnl"] > 0)
gross_loss = abs(sum(w["pnl"] for w in window_results if w["pnl"] < 0))
pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

print(f"\n{'='*70}")
print(f"WALK-FORWARD GRID RESULTS — {SYMBOL}, {WINDOW_DAYS}-day windows, {len(window_results)} windows")
print(f"{'='*70}")
print(f"  Period: {window_results[0]['start'][:10]} → {window_results[-1]['start'][:10]}")
print(f"  Total return:    {total_ret:+.2f}%")
print(f"  Final equity:    ${equity:.2f}")
print(f"  Win rate:        {wins}/{len(window_results)} = {wins/len(window_results)*100:.1f}%")
print(f"  Profit factor:   {pf:.2f}")
print(f"  Gross profit:    ${gross_profit:.2f}")
print(f"  Gross loss:      ${gross_loss:.2f}")
print(f"  Avg fills/window: {np.mean([w['n_fills'] for w in window_results]):.0f}")
print(f"  Total fills:     {sum(w['n_fills'] for w in window_results)}")
print(f"  Avg open closed: {np.mean([w['n_open_closed'] for w in window_results]):.1f}")
print(f"  Runtime: {time.time()-t0:.0f}s")

# Save
out = {
    "symbol": SYMBOL, "window_days": WINDOW_DAYS, "n_windows": len(window_results),
    "period": f"{window_results[0]['start'][:10]} → {window_results[-1]['start'][:10]}",
    "total_ret_pct": round(total_ret, 2), "final_equity": round(equity, 2),
    "win_rate": round(wins/len(window_results)*100, 1), "profit_factor": round(pf, 2),
    "gross_profit": round(gross_profit, 2), "gross_loss": round(gross_loss, 2),
    "total_fills": sum(w['n_fills'] for w in window_results),
    "windows": window_results[:20],
}
with open(os.path.join(ROOT, "results", "grid_sui_wf.json"), "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to results/grid_sui_wf.json")

# Print first 10 and last 5 windows
print(f"\nFirst 10 windows:")
for w in window_results[:10]:
    print(f"  W{w['window']:>3} {w['start'][:10]} center={w['center']:.4f} end={w['end_price']:.4f} fills={w['n_fills']:>4} tp={w['n_tp']:>3} open={w['n_open_closed']:>2} pnl={w['pnl']:>+8.2f} {'WIN' if w['win'] else 'LOSS'}")
print(f"\nLast 5 windows:")
for w in window_results[-5:]:
    print(f"  W{w['window']:>3} {w['start'][:10]} center={w['center']:.4f} end={w['end_price']:.4f} fills={w['n_fills']:>4} tp={w['n_tp']:>3} open={w['n_open_closed']:>2} pnl={w['pnl']:>+8.2f} {'WIN' if w['win'] else 'LOSS'}")
