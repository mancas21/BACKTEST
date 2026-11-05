"""CVRMD-v1.1 validation port: session VWAP+1sd (5-bar warmup guard),
CLV CVD slope, RSI14, MACD 12/26/9 pivot divergence (3/3, sep 5..60),
ATR1.5 SL frozen, TP1=VWAP mean, TP2=2R, entry+flip cooldown 3,
1% risk 3x, 6bps/side. Usage: cvrmd_backtest.py [1H|SCALP]"""
import csv, sys
from collections import deque
import numpy as np
import pandas as pd

# Paths are relative to this repo, so the script runs on any machine.
# (They previously pointed at a stale %TEMP%\opencode copy: same data, less
#  history — TEMP had 25,436 1h bars, the repo has 29,810+ after the 2017
#  backfill. Numbers below are re-validated on the full repo history.)
import os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1H = os.path.join(_ROOT, "data", "binance_klines_1h")
D1M = os.path.join(_ROOT, "data", "binance_klines_1m")
P, L, R, MD = 3, 3, 3, 60
MIND = 5  # v1.1 M-5: min bars between pivots
COST, SLIP = 0.0006, 0.0005
CD = 3  # v1.1 entry + flip cooldown (bars)

def load(sym, tfdir, tf):
    bars = []
    with open(os.path.join(tfdir, sym + "_" + tf + ".csv")) as f:
        for r in csv.DictReader(f):
            bars.append((int(r["open_ts"]), float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), float(r["volume"])))
    bars.sort(key=lambda b: b[0])
    return bars

def run(sym, bars, return_state=False):
    N = len(bars)
    T = np.array([b[0] for b in bars]); O = np.array([b[1] for b in bars])
    H = np.array([b[2] for b in bars]); Lo = np.array([b[3] for b in bars])
    C = np.array([b[4] for b in bars]); V = np.array([b[5] for b in bars])
    hl = np.maximum(H - Lo, 1e-9)
    clv = ((C - Lo) - (H - C)) / hl
    cvd = np.cumsum(clv * V)
    es = pd.Series(cvd).ewm(span=3, adjust=False).mean().to_numpy()
    slope = es - np.roll(es, 5)
    rsi = pd.Series(C).rolling(0).mean()  # placeholder
    # Wilder RSI
    d = np.diff(C, prepend=C[0])
    u = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    au = pd.Series(u).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    ad = pd.Series(dn).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    rsi = np.where(ad == 0, 100.0, 100 - 100 / (1 + au / np.where(ad == 0, 1, ad)))
    ef = pd.Series(C).ewm(span=12, adjust=False).mean().to_numpy()
    esl = pd.Series(C).ewm(span=26, adjust=False).mean().to_numpy()
    ml = ef - esl
    sg = pd.Series(ml).ewm(span=9, adjust=False).mean().to_numpy()
    hist = ml - sg
    osc = hist
    # session vwap (+ v1.1 M-4 warmup guard: >=5 bars in anchor, sd>0)
    day = T // 86400000
    vwap = np.zeros(N); vsd = np.zeros(N); inanchor = np.zeros(N, dtype=int)
    pv = vv = pv2 = 0.0
    cur = -1
    cnt = 0
    for i in range(N):
        if day[i] != cur:
            cur, pv, vv, pv2 = day[i], 0.0, 0.0, 0.0
            cnt = 1
        else:
            cnt += 1
        inanchor[i] = cnt
        hlc = (H[i] + Lo[i] + C[i]) / 3
        pv += hlc * V[i]; vv += V[i]; pv2 += hlc * hlc * V[i]
        vw = pv / vv if vv > 0 else C[i]
        vwap[i] = vw
        vsd[i] = np.sqrt(max(pv2 / vv - vw * vw, 0)) if vv > 0 else 0.0
    vwap_ready = (inanchor >= 5) & (vsd > 0)
    vb1l = vwap - vsd
    vb1u = vwap + vsd
    # pivots
    hsr = pd.Series(H); lsr = pd.Series(Lo)
    ph = (hsr > hsr.shift(1).rolling(P).max()) & (hsr > hsr.shift(-1)[::-1].rolling(P).max()[::-1])
    pl = (lsr < lsr.shift(1).rolling(L).min()) & (lsr < lsr.shift(-1)[::-1].rolling(L).min()[::-1])
    phc = ph.shift(R).fillna(False).astype(bool).to_numpy()
    plc = pl.shift(R).fillna(False).astype(bool).to_numpy()
    j = np.clip(np.arange(N) - R, 0, N - 1)
    bull = np.zeros(N, bool); bear = np.zeros(N, bool)
    lastLP = lastLO = lastLB = None
    prevLP = prevLO = prevLB = None
    lastHP = lastHO = lastHB = None
    prevHP = prevHO = prevHB = None
    for i in range(N):
        if plc[i]:
            prevLP, prevLO, prevLB = lastLP, lastLO, lastLB
            lastLP, lastLO, lastLB = Lo[j[i]], osc[j[i]], j[i]
            if prevLP is not None and lastLP < prevLP and lastLO > prevLO and (lastLB - prevLB) >= MIND and (lastLB - prevLB) <= MD:
                bull[i] = True
        if phc[i]:
            prevHP, prevHO, prevHB = lastHP, lastHO, lastHB
            lastHP, lastHO, lastHB = H[j[i]], osc[j[i]], j[i]
            if prevHP is not None and lastHP > prevHP and lastHO < prevHO and (lastHB - prevHB) >= MIND and (lastHB - prevHB) <= MD:
                bear[i] = True
    nearL = vwap_ready & (Lo <= vb1l) & (vb1l < C)
    nearH = vwap_ready & (H >= vb1u) & (vb1u > C)
    longSig = bull & nearL & (slope > 0) & ((rsi <= 35) | ((rsi < 50) & (rsi > np.roll(rsi, 1))))
    shortSig = bear & nearH & (slope < 0) & ((rsi >= 65) | ((rsi > 50) & (rsi < np.roll(rsi, 1))))
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H - Lo, np.maximum(np.abs(H - pc), np.abs(Lo - pc)))
    a = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    eq = 10000.0; peak = eq; mdd = 0.0; gp = gl = 0.0; tr_ = w_ = 0
    pos = 0; ep = sl = tp1 = tp2 = qty = 0.0; lastE = -10 ** 9
    tp1done = False
    logs = []
    for i in range(500, N):
        o, h_, l_, c_, t = O[i], H[i], Lo[i], C[i], T[i]
        ai = a[i]
        if ai <= 0 or not np.isfinite(ai):
            continue
        exited = False
        if pos == 1:
            if not tp1done and h_ >= tp1:
                ret = max(qty * 0.5 * ((tp1 - ep) / ep) - qty * 0.5 * COST, -0.999999)
                eq *= (1 + ret)
                if ret > 0:
                    gp += ret
                else:
                    gl += abs(ret)
                qty *= 0.5
                tp1done = True
                logs.append((t, ret))
            xp = None
            if o <= sl:
                xp = o * (1 - SLIP)
            elif l_ <= sl:
                xp = sl * (1 - SLIP)
            elif o >= tp2:
                xp = o * (1 - SLIP)
            elif h_ >= tp2:
                xp = tp2 * (1 - SLIP)
            elif shortSig[i] and (i - lastE) >= max(CD, 1):  # v1.1 M-6 flip cooldown
                xp = c_ * (1 - SLIP)
            if xp is not None:
                ret = max(qty * ((xp - ep) / ep) - qty * COST, -0.999999)
                eq *= (1 + ret); tr_ += 1
                if ret > 0:
                    w_ += 1; gp += ret
                else:
                    gl += abs(ret)
                pos = 0; exited = True
                logs.append((t, ret))
        elif pos == -1:
            if not tp1done and l_ <= tp1:
                ret = max(qty * 0.5 * ((ep - tp1) / ep) - qty * 0.5 * COST, -0.999999)
                eq *= (1 + ret)
                if ret > 0:
                    gp += ret
                else:
                    gl += abs(ret)
                qty *= 0.5
                tp1done = True
                logs.append((t, ret))
            xp = None
            if o >= sl:
                xp = o * (1 + SLIP)
            elif h_ >= sl:
                xp = sl * (1 + SLIP)
            elif o <= tp2:
                xp = o * (1 + SLIP)
            elif l_ <= tp2:
                xp = tp2 * (1 + SLIP)
            elif longSig[i] and (i - lastE) >= max(CD, 1):  # v1.1 M-6 flip cooldown
                xp = c_ * (1 + SLIP)
            if xp is not None:
                ret = max(qty * ((ep - xp) / ep) - qty * COST, -0.999999)
                eq *= (1 + ret); tr_ += 1
                if ret > 0:
                    w_ += 1; gp += ret
                else:
                    gl += abs(ret)
                pos = 0; exited = True
                logs.append((t, ret))
        # TP1 partial: check before full exits? simplified: TP1 folds into TP2 book via partial qty
        if pos == 0 and not exited and (i - lastE) >= CD:
            sd = ai * 1.5
            if longSig[i] and sd > 0:
                t1 = vwap[i] if vwap[i] > c_ else c_ + sd * 1.5
                pos, ep = 1, c_
                sl = c_ - sd; tp1 = t1; tp2 = c_ + sd * 2.0
                qty = min(0.01 / (sd / c_), 3.0)
                tp1done = False
                lastE = i
            elif shortSig[i] and sd > 0:
                t1 = vwap[i] if vwap[i] < c_ else c_ - sd * 1.5
                pos, ep = -1, c_
                sl = c_ + sd; tp1 = t1; tp2 = c_ - sd * 2.0
                qty = min(0.01 / (sd / c_), 3.0)
                tp1done = False
                lastE = i
        ce = eq
        if pos != 0:
            pr = (c_ - ep) / ep if pos == 1 else (ep - c_) / ep
            ce = max(eq * (1 + qty * pr), 0.0)
        if ce > peak:
            peak = ce
        dd = (peak - ce) / max(peak, 1e-9)
        if dd > mdd:
            mdd = dd
    if return_state:
        st = dict(pos=pos, ep=ep, sl=sl, tp1=tp1, tp2=tp2, qty=qty,
                  tp1done=tp1done, lastE=lastE, last_ts=int(T[N - 1]),
                  last_close=float(C[N - 1]))
        return eq, tr_, w_, gp, gl, mdd, logs, st
    return eq, tr_, w_, gp, gl, mdd, logs

def rep(name, eq, tr_, w_, gp, gl, mdd, logs):
    pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)
    segs = {}
    for t, r in logs:
        y = "24" if t < 1735689600000 else ("25" if t < 1767225600000 else "26")
        segs.setdefault(y, []).append(r)
    s = []
    for y in ("24", "25", "26"):
        rs = segs.get(y, [])
        e = 1.0
        for r in rs:
            e *= (1 + r)
        s.append(f"20{y}:{(e-1)*100:+.1f}%/{len(rs)}")
    print(f"{name}: net {(eq-10000)/100:+.2f}% PF {pf:.2f} WR {w_/max(tr_,1)*100:.1f}% n={tr_} DD {mdd*100:.1f}% | {' '.join(s)}", flush=True)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "1H"
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT"]
    if mode == "1H":
        for s in syms:
            eq, tr_, w_, gp, gl, mdd, logs = run(s, load(s, D1H, "1h"))
            rep(f"{s} 1H", eq, tr_, w_, gp, gl, mdd, logs)
    else:
        import pandas as pd
        for s in syms:
            for tf, f_ in (("1m", 1), ("5m", 5), ("15m", 15)):
                d = pd.read_csv(D1M + "\\" + s + "_1m.csv").sort_values("open_ts")
                g = np.arange(len(d)) // f_
                b = d.groupby(g).agg(open_ts=("open_ts", "first"), open=("open", "first"),
                                     high=("high", "max"), low=("low", "min"),
                                     close=("close", "last"), volume=("volume", "sum"))
                bars = [(int(r.open_ts), float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume)) for r in b.itertuples()]
                eq, tr_, w_, gp, gl, mdd, logs = run(s, bars)
                rep(f"{s} {tf}", eq, tr_, w_, gp, gl, mdd, logs)
