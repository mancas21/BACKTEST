"""Grid config sweep for $10 x 10x ($100 notional) Binance neutral futures grid.
Walk-forward: trailing-7d calibration -> next-7d test, maker fees (post-only limits).
Hard constraint: per-cell notional = 100/n >= 5 USDT (Binance min) -> n <= 20.
Usage: python grid_sweep.py
"""
import sys
sys.path.insert(0, r"C:\Users\Lenovo\AppData\Local\Temp\opencode")
from grid_binance_backtest import load, run_grid

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT"]
W = 7 * 288
EMBARGO = 12
MAKER = 0.0002
NOTIONAL = 100.0
MIN_ORDER = 5.0

def sym_interval(sym):
    bars = load(sym)
    return bars

print("sym grids width gtype | windows net$ PF fills hold% halt% | cell$ range%")
results = []
for sym in SYMS:
    bars = sym_interval(sym)
    n = len(bars)
    starts = list(range(0, n - W - EMBARGO - 500, W))
    closes = [b["c"] for b in bars]
    for ng in (8, 10, 12, 15, 20, 30, 60):
        cell = NOTIONAL / ng
        for wf in (0.5, 0.75, 1.0):
            for gt in ("arithmetic", "geometric"):
                agg_net = 0.0; gp = gl = 0.0; fills = 0; fees = 0.0
                inr = tot = 0; halts = 0; nw = 0
                for s in starts:
                    cal = bars[s:s + W]
                    tst = bars[s + W + EMBARGO:s + 2 * W + EMBARGO]
                    if len(tst) < 500:
                        continue
                    lo = min(b["l"] for b in cal); hi = max(b["h"] for b in cal)
                    mid = (lo + hi) / 2; w = (hi - lo) * wf
                    r = run_grid(tst, mid - w / 2, mid + w / 2, ng, gt, MAKER, 10)
                    agg_net += r["net"]; gp += r["gross_profit"]; gl += r["gross_loss"]
                    fills += r["fills"]; fees += r["fees"]
                    inr += int(round(r["bars_in_range_pct"] / 100 * r["bars"])); tot += r["bars"]
                    halts += 1 if r["halted"] else 0; nw += 1
                pf = gp / gl if gl > 1e-9 else None
                hold = inr / max(tot, 1) * 100
                results.append(dict(sym=sym, ng=ng, wf=wf, gt=gt, net=agg_net,
                                    pf=pf, fills=fills, hold=hold, nw=nw,
                                    halts=halts, fees=fees, cell=cell,
                                    ok=cell >= MIN_ORDER))
                print(f"{sym} n={ng} w={wf} {gt[:5]} | W={nw} net={agg_net:+.2f} "
                      f"PF={pf if pf is None else round(pf,3)} fills={fills} hold={hold:.0f}% "
                      f"halt={halts} fees={fees:.2f} cell=${cell:.2f} {'OK' if cell >= MIN_ORDER else 'MIN-ORDER-FAIL'}",
                      flush=True)

print("\n=== TOP executable (cell>=5) by net ===")
ok = sorted([r for r in results if r["ok"]], key=lambda r: -r["net"])[:10]
for r in ok:
    print(r)
print("\n=== TOP ignoring min-order (paper only) ===")
for r in sorted(results, key=lambda r: -r["net"])[:5]:
    print(r)
