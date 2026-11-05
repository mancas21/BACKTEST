"""BOT-Strat (Breakout Targets) validation port.
Ranges: pivots 49/49 + crossunder(WMA99, EMA99) of |close-open|.
Breakout: close beyond box; entry NEXT open; SL = signal extreme -/+ ATR14*5;
TP 0.5/1.0/1.5R sliced 33/33/34%; 10% equity; reversal allowed (pyramiding 0);
commission 6bps/side + slip (conservative vs script 0.04%+1tick).
Usage: python botstrat_backtest.py
"""
import sys
import os
import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1H = os.path.join(_ROOT, "data", "binance_klines_1h")
LEN, LH = 99, 49
SLM = 5.0
TPM = (0.5, 1.0, 1.5)
PCTS = (0.33, 0.33, 0.34)
COST, SLIP = 0.0006, 0.0005

def load(sym):
    import csv, os
    bars = []
    with open(os.path.join(D1H, sym + "_1h.csv")) as f:
        for r in csv.DictReader(f):
            bars.append((int(r["open_ts"]), float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), float(r["volume"])))
    bars.sort(key=lambda b: b[0])
    return bars

def wma(s, n):
    w = np.arange(1, n + 1, dtype=float)
    return pd.Series(s).rolling(n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True).to_numpy()

def run(sym, bars, return_state=False):
    N = len(bars)
    T = np.array([b[0] for b in bars]); O = np.array([b[1] for b in bars])
    H = np.array([b[2] for b in bars]); Lo = np.array([b[3] for b in bars])
    C = np.array([b[4] for b in bars])
    body = np.abs(C - O)
    v1 = wma(body, LEN)
    v2 = pd.Series(body).ewm(span=LEN, adjust=False).mean().to_numpy()
    cross = np.zeros(N, bool)
    cross[1:] = (v1[:-1] >= v2[:-1]) & (v1[1:] < v2[1:])
    P = LH
    hsr = pd.Series(H); lsr = pd.Series(Lo)
    ph = (hsr > hsr.shift(1).rolling(P).max()) & (hsr > hsr.shift(-1)[::-1].rolling(P).max()[::-1])
    pl = (lsr < lsr.shift(1).rolling(P).min()) & (lsr < lsr.shift(-1)[::-1].rolling(P).min()[::-1])
    phc = ph.shift(P).fillna(False).astype(bool).to_numpy()
    plc = pl.shift(P).fillna(False).astype(bool).to_numpy()
    j = np.clip(np.arange(N) - P, 0, N - 1)
    # confirmed pivot level/bar series
    phLvl = np.where(phc, H[j], np.nan)
    phBar = np.where(phc, j.astype(float), np.nan)
    plLvl = np.where(plc, Lo[j], np.nan)
    plBar = np.where(plc, j.astype(float), np.nan)
    lastPH = pd.Series(phLvl).ffill().to_numpy()
    lastPHB = pd.Series(phBar).ffill().fillna(-1).to_numpy()
    lastPL = pd.Series(plLvl).ffill().to_numpy()
    lastPLB = pd.Series(plBar).ffill().fillna(-1).to_numpy()
    # ATR14 + vola
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H - Lo, np.maximum(np.abs(H - pc), np.abs(Lo - pc)))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    # boxes: list of [left, top, bottom] in creation order
    boxes = []
    sig = np.zeros(N, dtype=int)  # +1 long, -1 short at signal bar
    sigPx = np.zeros(N)           # signal close
    sigSL = np.zeros(N)
    for i in range(max(LEN + P + 5, 500), N):
        # range trigger
        if cross[i] and lastPHB[i] >= 0 and lastPLB[i] >= 0:
            if lastPHB[i] > lastPLB[i]:
                h = lastPH[i]; sIdx = int(lastPHB[i])
                dist = i - sIdx
                l = Lo[sIdx + 1:i + 1].min() if dist > 0 else np.nan
            else:
                l = lastPL[i]; sIdx = int(lastPLB[i])
                dist = i - sIdx
                h = H[sIdx + 1:i + 1].max() if dist > 0 else np.nan
            lastRight = boxes[-1][3] if boxes else -1
            if np.isfinite(h) and np.isfinite(l) and C[i] <= h and C[i] >= l and sIdx > lastRight:
                boxes.append([sIdx, h, l, i])
        # breakout scan oldest first
        rm = []
        for bi, (lft, top, bot, rgt) in enumerate(boxes):
            if C[i] > top:
                sig[i] = 1; sigPx[i] = C[i]; sigSL[i] = Lo[i] - atr[i] * SLM
                rm.append(bi)
                break
            elif C[i] < bot:
                sig[i] = -1; sigPx[i] = C[i]; sigSL[i] = H[i] + atr[i] * SLM
                rm.append(bi)
                break
            else:
                boxes[bi][3] = i
        for bi in rm:
            boxes.pop(bi)
    # trade engine: entry next open, reversal allowed, partial TPs
    eq = 10000.0; peak = eq; mdd = 0.0; gp = gl = 0.0; tr_ = w_ = 0
    pos = 0; ep = sl = 0.0; tps = []; qty = 0.0; rem = 0.0; tpnl = 0.0
    logs = []
    closes = []  # (open_ts, side, ret_total)
    pending = 0  # signal side to enter at next open, with stored levels
    pSL = pTPs = None; pSigPx = 0.0
    for i in range(max(LEN + P + 5, 500), N):
        o, h_, l_, c_, t = O[i], H[i], Lo[i], C[i], T[i]
        # execute pending entry at open
        if pending != 0:
            if pos != 0:
                # reversal: close current at open
                pr = (o - ep) / ep if pos == 1 else (ep - o) / ep
                ret = max(rem * pr - rem * COST, -0.999999)
                eq *= (1 + ret); tpnl += ret; tr_ += 1; closes.append((t, pos, tpnl))
                if tpnl > 0: w_ += 1
                if ret > 0: gp += ret
                else: gl += abs(ret)
                logs.append((t, ret))
                pos = 0
            risk = abs(pSigPx - pSL)
            if risk > 0:
                pos = pending; ep = o; sl = pSL if pending == 1 else pSL
                if pending == 1:
                    sl = pSL; tps = [(pSigPx + risk * m, p) for m, p in zip(TPM, PCTS)]
                else:
                    sl = pSL; tps = [(pSigPx - risk * m, p) for m, p in zip(TPM, PCTS)]
                qty = rem = 0.10
                tpnl = 0.0
                eq -= rem * COST
            pending = 0
        # opposite signal while in position -> schedule reversal
        if sig[i] != 0 and pos != 0 and sig[i] != pos:
            pending = sig[i]; pSL = sigSL[i]; pSigPx = sigPx[i]
        elif sig[i] != 0 and pos == 0 and pending == 0:
            pending = sig[i]; pSL = sigSL[i]; pSigPx = sigPx[i]
        # manage open position (conservative: stop first, then TPs in order)
        if pos == 1:
            if o <= sl:
                xp = o * (1 - SLIP)
                ret = max(rem * ((xp - ep) / ep) - rem * COST, -0.999999)
                eq *= (1 + ret); tpnl += ret; tr_ += 1; closes.append((t, pos, tpnl))
                if tpnl > 0: w_ += 1
                if ret > 0: gp += ret
                else: gl += abs(ret)
                logs.append((t, ret)); pos = 0
            elif l_ <= sl:
                xp = sl * (1 - SLIP)
                ret = max(rem * ((xp - ep) / ep) - rem * COST, -0.999999)
                eq *= (1 + ret); tpnl += ret; tr_ += 1; closes.append((t, pos, tpnl))
                if tpnl > 0: w_ += 1
                if ret > 0: gp += ret
                else: gl += abs(ret)
                logs.append((t, ret)); pos = 0
            else:
                for lvl, pc_ in tps:
                    if pc_ > 0 and (o >= lvl or h_ >= lvl):
                        fxp = o * (1 - SLIP) if o >= lvl else lvl * (1 - SLIP)
                        ret = max(rem * pc_ * ((fxp - ep) / ep) - rem * pc_ * COST, -0.999999)
                        eq *= (1 + ret); tpnl += ret
                        if ret > 0: gp += ret
                        else: gl += abs(ret)
                        logs.append((t, ret))
                        rem *= (1 - pc_)
                tps = [(lv, 0.0) for lv, pc_ in tps]
                if rem < 1e-9:
                    tr_ += 1; closes.append((t, pos, tpnl))
                    if tpnl > 0: w_ += 1
                    pos = 0
        elif pos == -1:
            if o >= sl:
                xp = o * (1 + SLIP)
                ret = max(rem * ((ep - xp) / ep) - rem * COST, -0.999999)
                eq *= (1 + ret); tpnl += ret; tr_ += 1; closes.append((t, pos, tpnl))
                if tpnl > 0: w_ += 1
                if ret > 0: gp += ret
                else: gl += abs(ret)
                logs.append((t, ret)); pos = 0
            elif h_ >= sl:
                xp = sl * (1 + SLIP)
                ret = max(rem * ((ep - xp) / ep) - rem * COST, -0.999999)
                eq *= (1 + ret); tpnl += ret; tr_ += 1; closes.append((t, pos, tpnl))
                if tpnl > 0: w_ += 1
                if ret > 0: gp += ret
                else: gl += abs(ret)
                logs.append((t, ret)); pos = 0
            else:
                for lvl, pc_ in tps:
                    if pc_ > 0 and (o <= lvl or l_ <= lvl):
                        fxp = o * (1 + SLIP) if o <= lvl else lvl * (1 + SLIP)
                        ret = max(rem * pc_ * ((ep - fxp) / ep) - rem * pc_ * COST, -0.999999)
                        eq *= (1 + ret); tpnl += ret
                        if ret > 0: gp += ret
                        else: gl += abs(ret)
                        logs.append((t, ret))
                        rem *= (1 - pc_)
                tps = [(lv, 0.0) for lv, pc_ in tps]
                if rem < 1e-9:
                    tr_ += 1; closes.append((t, pos, tpnl))
                    if tpnl > 0: w_ += 1
                    pos = 0
        ce = eq
        if ce > peak: peak = ce
        dd = (peak - ce) / max(peak, 1e-9)
        if dd > mdd: mdd = dd
    if return_state:
        st = dict(pos=pos, ep=ep, sl=sl, tps=[(float(l), float(p)) for l, p in tps],
                  qty=qty, rem=rem, tpnl=tpnl, pending=pending, pSL=pSL,
                  pSigPx=pSigPx, last_ts=int(T[N - 1]), last_close=float(C[N - 1]))
        return eq, tr_, w_, gp, gl, mdd, logs, closes, st
    return eq, tr_, w_, gp, gl, mdd, logs, closes

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
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "HYPEUSDT", "SPXUSDT"]
    for s in syms:
        try:
            eq, tr_, w_, gp, gl, mdd, logs, closes = run(s, load(s))
            rep(s + " 1H BOT", eq, tr_, w_, gp, gl, mdd, logs)
        except FileNotFoundError as e:
            print(s, "no data", flush=True)
