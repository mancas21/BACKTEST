"""Exact-engine simulation of FFS-v1 Pine logic (single position, TTL,
cooldown, TP/SL, timeout). 5m. Recommended symbols first, then all.
Split into H1/H2 for stability check.
"""
import numpy as np
import pandas as pd
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1M = os.path.join(_ROOT, "data", "binance_klines_1m")
COST = 0.0004  # commission per side (Pine 0.04%)

def load5(sym):
    import pandas as pd
    d = pd.read_csv(os.path.join(D1M, sym + "_1m.csv")).sort_values("open_ts").reset_index(drop=True)
    g = d.index // 5
    return d.groupby(g).agg(open_ts=("open_ts", "first"), open=("open", "first"),
                            high=("high", "max"), low=("low", "min"),
                            close=("close", "last"), volume=("volume", "sum")).reset_index(drop=True)

def engine(b, sigMult=2.0, sigLen=288, volMult=3.0, flushBars=5, undercut=0.05,
           waitBars=10, cooldown=3, tpPct=0.5, slPct=0.8, maxHold=60,
           riskPct=1.0, maxLev=3.0, allowLong=False):
    O = b.open.to_numpy(); H = b.high.to_numpy(); Lo = b.low.to_numpy()
    C = b.close.to_numpy(); V = b.volume.to_numpy(); T = b.open_ts.to_numpy()
    N = len(b)
    rN = np.zeros(N)
    rN[flushBars:] = C[flushBars:] / C[:-flushBars] - 1.0
    sig = pd.Series(rN).rolling(sigLen).std().to_numpy()
    vmed = pd.Series(V).rolling(sigLen).median().to_numpy()
    hi5 = pd.Series(H).rolling(flushBars).max().to_numpy()
    lo5 = pd.Series(Lo).rolling(flushBars).min().to_numpy()
    eq = 10000.0
    peak = eq; mdd = 0.0
    trades = []          # (ts, pnl, side)
    pos = 0              # 0 flat, 1 pending short, -1 pending long, 2 short pos, -2 long pos
    pendPx = 0.0; pendBar = 0; lastSetup = -100000
    ep = sl = tp = 0.0; qty = 0.0; ebar = 0
    for i in range(sigLen + flushBars, N):
        o, h_, l_, c_ = O[i], H[i], Lo[i], C[i]
        okS = sig[i] == sig[i] and sig[i] > 0
        volOK = vmed[i] == vmed[i] and V[i] >= volMult * vmed[i]
        upF = okS and volOK and rN[i] >= sigMult * sig[i]
        dnF = okS and volOK and rN[i] <= -sigMult * sig[i]
        # pending fill checks (intrabar)
        if pos == 1:
            if h_ >= pendPx:   # short limit filled
                ep = pendPx; pos = 2; ebar = i
                sl = ep * (1 + slPct / 100); tp = ep * (1 - tpPct / 100)
                qty = min(eq * riskPct / 100 / (ep * slPct / 100), eq * maxLev / ep)
                eq -= qty * ep * COST
            elif i - pendBar > waitBars:
                pos = 0
        elif pos == -1:
            if l_ <= pendPx:
                ep = pendPx; pos = -2; ebar = i
                sl = ep * (1 - slPct / 100); tp = ep * (1 + tpPct / 100)
                qty = min(eq * riskPct / 100 / (ep * slPct / 100), eq * maxLev / ep)
                eq -= qty * ep * COST
            elif i - pendBar > waitBars:
                pos = 0
        # position exits (Pine: exit orders active from the bar AFTER the fill)
        if pos == 2:
            xp = None
            if i > ebar:
                if h_ >= sl:
                    xp = sl * (1 + 0.0005)   # stop slippage
                elif l_ <= tp:
                    xp = tp
                elif i - ebar >= maxHold:
                    xp = c_
            if xp is not None:
                pnl = qty * (ep - xp) - qty * xp * COST
                eq += pnl
                trades.append((T[i], pnl, "S"))
                pos = 0
        elif pos == -2:
            xp = None
            if i > ebar:
                if l_ <= sl:
                    xp = sl * (1 - 0.0005)
                elif h_ >= tp:
                    xp = tp
                elif i - ebar >= maxHold:
                    xp = c_
            if xp is not None:
                pnl = qty * (xp - ep) - qty * xp * COST
                eq += pnl
                trades.append((T[i], pnl, "L"))
                pos = 0
        # MTM dd
        ce = eq
        if pos == 2:
            ce = eq + qty * (ep - c_)
        elif pos == -2:
            ce = eq + qty * (c_ - ep)
        if ce > peak: peak = ce
        dd = (peak - ce) / max(peak, 1e-9)
        if dd > mdd: mdd = dd
        # new setup
        if pos == 0 and (i - lastSetup) > cooldown:
            if upF and hi5[i] * (1 + undercut / 100) > c_:
                pendPx = hi5[i] * (1 + undercut / 100)
                pendBar = i; pos = 1; lastSetup = i
            elif allowLong and dnF and lo5[i] * (1 - undercut / 100) < c_:
                pendPx = lo5[i] * (1 - undercut / 100)
                pendBar = i; pos = -1; lastSetup = i
    wins = [t for t in trades if t[1] > 0]
    gp = sum(t[1] for t in trades if t[1] > 0)
    gl = -sum(t[1] for t in trades if t[1] <= 0)
    pf = gp / gl if gl > 0 else float("inf") if gp > 0 else 0.0
    wr = len(wins) / max(len(trades), 1) * 100
    n = len(trades)
    return eq, pf, wr, n, mdd * 100, trades

print("=== FFS-v1 exact engine, 5m, SHORT only, 94 days ===")
for sym in ["HYPEUSDT", "SUIUSDT", "SPXUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]:
    b = load5(sym)
    eq, pf, wr, n, mdd, trades = engine(b)
    # split
    if trades:
        mid = len(trades) // 2
        e1 = 10000.0
        for t in trades[:mid]:
            e1 += t[1]
        e2 = 10000.0
        for t in trades[mid:]:
            e2 += t[1]
        s = f"H1 {(e1-10000)/100:+.2f}% H2 {(e2-10000)/100:+.2f}%"
    else:
        s = ""
    print(f"{sym}: net {(eq-10000)/100:+.2f}% PF {pf:.2f} WR {wr:.0f}% n={n} DD {mdd:.1f}% | {s}", flush=True)
