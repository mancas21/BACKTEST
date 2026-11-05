"""Trace the SOL grid run to find why equity collapses. Diagnostic only."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cvrmd_port as P
import grid_audit as G

bars = G.load15("SOLUSDT")
gate = G.htf_filter(bars)[0]
print(f"bars {len(bars):,}  gate TRUE {gate.sum():,}")

# replicate the loop with tracing
n = len(bars)
T = np.array([b[0] for b in bars], dtype=np.int64)
H = np.array([b[2] for b in bars])
L = np.array([b[3] for b in bars])
C = np.array([b[4] for b in bars])
tr = np.maximum.reduce([H - L, np.abs(H - G.shift(C, 1)), np.abs(L - G.shift(C, 1))])
atr = P.atr(H, L, C, 20)

INIT = G.INIT
cash = INIT
lots = []
state = "idle"
cooldown = 0
bars_since = 0
grid_px = [0.0] * 5
grid_qty = [0.0] * 5
ent = [None] * 5
cov = [None] * 5
step = stop_px = center = half = 0.0
fill = cover = 0
first_liq = None
first_loss = None

def qn():
    return sum(l[0] for l in lots)

def be(px):
    return cash + sum(l[0] * (px - l[1]) for l in lots)

for t in range(n):
    bars_since += 1
    if state == "cooldown":
        cooldown -= 1
        if cooldown <= 0:
            state = "idle"
        continue
    if bars_since < G.WARMUP_BARS:
        continue
    ap = atr[t - 1] if t >= 1 else np.nan
    if np.isnan(ap) or ap <= 0:
        continue
    cp = C[t - 1]
    cn = C[t]
    bull = bool(gate[t])
    if state == "idle":
        if not bull:
            continue
        half = ap * G.ATR_MULT
        step = half / 5
        pf = be(cp)
        grid_px = [cp - step * (i + 1) for i in range(5)]
        grid_qty = [G.EQUITY_PCT * pf / p for p in grid_px]
        center = cp
        stop_px = grid_px[-1] - ap * G.STOP_ATR_MULT
        state = "working"
        for i in range(5):
            if grid_px[i] < cn:
                ent[i] = grid_px[i]
        if first_loss is None:
            print(f"t={t} first grid: px={cp:.2f} step={step:.3f} "
                  f"stop={stop_px:.2f} ({100*(cp-stop_px)/cp:.2f}% below) "
                  f"notional={sum(grid_qty)*0:.0f}")
            print(f"     levels {[round(x,2) for x in grid_px]}")
            print(f"     qtys  {[round(x,3) for x in grid_qty]}")
            print(f"     total notional ${sum(grid_qty[i]*grid_px[i] for i in range(5)):,.0f}"
                  f"  equity ${pf:,.0f}")
            print(f"     rest levels below close: "
                  f"{[i for i in range(5) if grid_px[i] < cn]}")
        continue
    for i in range(5):
        if ent[i] is None:
            continue
        if L[t] < ent[i]:
            q = grid_qty[i]
            px = ent[i] * (1 + G.MAKER_SLIP)
            f = q * px * G.MAKER_FEE
            cash -= q * px + f
            lots.append([q, px, i, f])
            ent[i] = None
            cov[i] = ent[i] + step if False else grid_px[i] + step
            fill += 1
    for i in range(5):
        if cov[i] is None:
            continue
        if H[t] < cov[i]:
            continue
        for lot in list(lots):
            if lot[2] != i:
                continue
            q = lot[0]
            px = cov[i] * (1 - G.MAKER_SLIP)
            cash += q * px
            f = q * px * G.MAKER_FEE
            cash -= f
            lot[0] -= q
            if lot[0] <= 1e-12:
                lots.remove(lot)
            cover += 1
            break
        cov[i] = None
    if cn <= stop_px:
        if lots:
            for lot in list(lots):
                px = cn * (1 - 0.0005)
                cash += lot[0] * px
                f = lot[0] * px * G.TAKER_FEE
                cash -= f
                lot[0] = 0.0
            lots.clear()
        state = "cooldown"
        cooldown = G.COOLDOWN_BARS
    else:
        for i in range(5):
            if ent[i] is None and cov[i] is None:
                if bull and grid_px[i] < cn:
                    ent[i] = grid_px[i]
        if cn > center + half * G.REBUILD_DRIFT:
            if lots:
                for lot in list(lots):
                    px = cn * (1 - 0.0005)
                    cash += lot[0] * px
                    f = lot[0] * px * G.TAKER_FEE
                    cash -= f
                    lot[0] = 0.0
                lots.clear()
            state = "idle"
        elif (not bull) and not lots:
            state = "idle"
    eq = be(C[t])
    notional = qn() * C[t]
    if first_loss is None and eq < INIT * 0.9:
        first_loss = (t, eq, notional, state, len(lots), fill, cover)
        print(f"\nt={t} FIRST 10% EQUITY LOSS")
        print(f"   close={cn:.2f} stop={stop_px:.2f} state={state} lots={len(lots)}")
        print(f"   equity=${eq:,.2f} notional=${notional:,.2f} "
              f"lev={notional/eq if eq>0 else 0:.2f}x")
        print(f"   maint margin 0.5% of notional = ${0.005*notional:,.2f}")
        print(f"   fills={fill} covers={cover}")
        for lot in lots:
            print(f"   lot lvl={lot[2]} qty={lot[0]:.3f} entry={lot[1]:.2f} "
                  f"pnl=${lot[0]*(cn-lot[1]):,.2f}")
    if notional > 0 and eq <= 0.005 * notional:
        first_liq = (t, eq, notional, len(lots))
        print(f"\nt={t} LIQUIDATION eq=${eq:,.2f} notional=${notional:,.2f} "
              f"lots={len(lots)}")
        print(f"   maint threshold ${0.005*notional:,.2f}")
        for lot in lots:
            print(f"   lot lvl={lot[2]} qty={lot[0]:.3f} entry={lot[1]:.2f} "
                  f"unreal=${lot[0]*(cn-lot[1]):,.2f} "
                  f"({100*(cn-lot[1])/lot[1]:+.2f}%)")
        print(f"   close={cn:.2f} stop={stop_px:.2f} grid_px={[round(x,2) for x in grid_px]}")
        break

print(f"\ntotals: fills={fill} covers={cover} first_loss={first_loss} first_liq={first_liq}")
