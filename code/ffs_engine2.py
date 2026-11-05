"""Engine run with corrected exit designs (strict, single position)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from ffs_engine import load5, COST

def engine2(b, sigMult=2.0, sigLen=288, volMult=3.0, flushBars=5, undercut=0.05,
            waitBars=10, cooldown=3, tp_mode="pct", tpPct=1.0, slPct=1.0,
            maxHold=60, riskPct=1.0, maxLev=3.0, allowLong=False,
            return_state=False):
    O = b.open.to_numpy(); H = b.high.to_numpy(); Lo = b.low.to_numpy()
    C = b.close.to_numpy(); V = b.volume.to_numpy(); T = b.open_ts.to_numpy()
    N = len(b)
    rN = np.zeros(N)
    rN[flushBars:] = C[flushBars:] / C[:-flushBars] - 1.0
    sig = pd.Series(rN).rolling(sigLen).std().to_numpy()
    vmed = pd.Series(V).rolling(sigLen).median().to_numpy()
    hi5 = pd.Series(H).rolling(flushBars).max().to_numpy()
    lo5 = pd.Series(Lo).rolling(flushBars).min().to_numpy()
    eq = 10000.0; peak = eq; mdd = 0.0
    trades = []
    pos = 0; pendPx = 0.0; pendBar = 0; lastSetup = -100000
    ep = sl = tp = legv = 0.0; qty = 0.0; ebar = 0
    for i in range(sigLen + flushBars, N):
        o, h_, l_, c_ = O[i], H[i], Lo[i], C[i]
        okS = sig[i] == sig[i] and sig[i] > 0
        volOK = vmed[i] == vmed[i] and V[i] >= volMult * vmed[i]
        upF = okS and volOK and rN[i] >= sigMult * sig[i]
        dnF = okS and volOK and rN[i] <= -sigMult * sig[i]
        if pos == 1:
            if h_ >= pendPx:
                ep = pendPx; pos = 2; ebar = i
                sl = ep * (1 + slPct / 100)
                tp = ep * (1 - tpPct / 100) if tp_mode == "pct" else ep - (hi5[i] - lo5[i]) * tpPct / 100
                legv = (hi5[i] - lo5[i]) / ep
                qty = min(eq * riskPct / 100 / (ep * slPct / 100), eq * maxLev / ep)
                eq -= qty * ep * COST
            elif i - pendBar > waitBars:
                pos = 0
        elif pos == -1:
            if l_ <= pendPx:
                ep = pendPx; pos = -2; ebar = i
                sl = ep * (1 - slPct / 100)
                tp = ep * (1 + tpPct / 100)
                qty = min(eq * riskPct / 100 / (ep * slPct / 100), eq * maxLev / ep)
                eq -= qty * ep * COST
            elif i - pendBar > waitBars:
                pos = 0
        if pos == 2:
            xp = None
            if i > ebar:
                if h_ >= sl:
                    xp = sl * (1 + 0.0005)
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
        ce = eq
        if pos == 2:
            ce = eq + qty * (ep - c_)
        elif pos == -2:
            ce = eq + qty * (c_ - ep)
        if ce > peak: peak = ce
        dd = (peak - ce) / max(peak, 1e-9)
        if dd > mdd: mdd = dd
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
    if return_state:
        st = dict(pos=pos, pendPx=pendPx, pendBar=pendBar, ep=ep, sl=sl, tp=tp,
                  qty=qty, legv=legv, ebar=ebar, lastSetup=lastSetup,
                  last_ts=int(T[N - 1]), last_close=float(C[N - 1]))
        return eq, pf, wr, len(trades), mdd * 100, trades, st
    return eq, pf, wr, len(trades), mdd * 100, trades

VARIANTS = [
    ("TP1.0/SL1.0", dict(tp_mode="pct", tpPct=1.0, slPct=1.0)),
    ("TP1.5/SL1.0", dict(tp_mode="pct", tpPct=1.5, slPct=1.0)),
    ("leg50/SL1.0", dict(tp_mode="leg", tpPct=50, slPct=1.0)),
    ("leg60/SL1.0", dict(tp_mode="leg", tpPct=60, slPct=1.0)),
]
for sym in ["SUIUSDT", "HYPEUSDT", "SPXUSDT"]:
    b = load5(sym)
    print(f"=== {sym} ===")
    for name, kw in VARIANTS:
        eq, pf, wr, n, mdd, tr = engine2(b, **kw)
        mid = len(tr) // 2
        e1 = 10000.0
        for t in tr[:mid]:
            e1 += t[1]
        e2 = 10000.0
        for t in tr[mid:]:
            e2 += t[1]
        print(f"  {name}: net {(eq-10000)/100:+.2f}% PF {pf:.2f} WR {wr:.0f}% n={n} DD {mdd:.1f}% | H1 {(e1-10000)/100:+.1f}% H2 {(e2-10000)/100:+.1f}%", flush=True)
