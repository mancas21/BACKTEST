#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_emaadx_audit.py — known-answer audit for emaadx_engine.py.

MUST pass ALL before any real-data run (repo porting protocol step 2).
Every case is hand-computed arithmetic, a pandas holy-reference, a dual-engine
DMI recomputation, or a crafted playthrough whose fills are re-derived
independently of the engine's simulation loop:
  A  long entry at the signal-bar close, TP fills at the exact anchored stop
  B  a spanning bar (SL and TP both reached) resolves STOP-FIRST
  C  fee recomputation per trade + money conservation at zero-tolerance
  D  reversal behaviour (use_tp=False, entry held into the crossdown),
     fill = close*(1 +/- slip), fees on the whole order quantity
  E  the Pine trap: a SECOND cross_up while still long re-sets the brackets
     (proven by the later SL exit price equal to the re-set bar's anchor)
Writes results/emaadx_audit_known_answers.txt; exit 0 = all pass.
"""

import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import emaadx_engine as E

OUT = os.path.join(ROOT, "results", "emaadx_audit_known_answers.txt")
lines = []
P = dict(E.PINE)
FEER, SLIPR = 0.0006, 0.0005           # repo6x5 for the money cases


def ok(name, cond, detail=""):
    lines.append("[PASS] %s  %s" % (name, detail) if cond
                 else "[FAIL] %s  %s" % (name, detail))
    return bool(cond)


def mk(deltas, base=100.0):
    """OHLC from a close-path; honest fixed-width wicks."""
    c = base + np.cumsum(np.asarray(deltas, float))
    o = np.concatenate([[base], c[:-1]])
    h = np.maximum(o, c) + 0.4
    l = np.minimum(o, c) - 0.4
    return o, h, l, c


def sigbars(o, h, l, c):
    """Long/short condition rederived from the engine's own primitives."""
    ef, es = E.ema(c, 20), E.ema(c, 50)
    pP, pM, axx = E.dmi_pine(h, l, c, 14, 14)
    ts = (~np.isnan(axx)) & (axx >= 25.0)
    bull = pP > pM
    bear = pM > pP
    lc = E.cross_over(ef, es) & ts & bull
    sc = E.cross_under(ef, es) & ts & bear
    lc[:60] = False
    sc[:60] = False
    return lc, sc


def money_rows(trades, fee_rate):
    """Every row's pnl must recompute from its own columns."""
    for t in trades:
        side = 1.0 if t["side"] == "L" else -1.0
        expect = side * t["qty"] * (t["exit"] - t["entry"]) \
            - t["entry_fee"] - t["exit_fee"]
        if not np.isclose(expect, t["pnl"], atol=1e-6):
            return False
        if not np.isclose(t["entry_fee"], t["qty"] * t["entry"] * fee_rate,
                          atol=1e-9):
            return False
        if not np.isclose(t["exit_fee"], t["qty"] * t["exit"] * fee_rate,
                          atol=1e-9):
            return False
    return True


# ---------------------------------------------------------------- 1. ema
x = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
# alpha=2/(3+1)=0.5, seeded with x0: e0=0, e1=0, e2=0.5*1+0.5*0=0.5; head gated
e = E.ema(x, 3)
ok("ema known answer x=[0,0,1,0,0] n=3 -> e2=0.5, head gated",
   bool(np.isnan(e[0]) and np.isnan(e[1]) and np.isclose(e[2], 0.5)),
   "e=" + str(e))
dfe = pd.Series(x).ewm(span=3, adjust=False, min_periods=3).mean().to_numpy()
ok("ema equals pandas ewm(span, adjust=False, min_periods)",
   bool(np.allclose(e, dfe, equal_nan=True)))
rise = np.linspace(100, 200, 220)
ef = E.ema(rise, 20); es = E.ema(rise, 50)
ok("ema monotone rise -> ef above es, zero crossovers after warmup",
   not bool(E.cross_over(ef, es).any()) and not bool(E.cross_under(ef, es).any()))

# ---------------------------------------------------------------- 2. cross
a = np.array([1.0, 2.0, 2.1, 2.2]); b = np.array([2.0, 2.0, 2.05, 2.2])
ok("cross_over fires exactly where designed (index 2 only)",
   list(E.cross_over(a, b)) == [False, False, True, False])
ok("cross_under mirrored (no cross in this path)",
   list(E.cross_under(a, b)) == [False, False, False, False])
nan_a = np.array([np.nan, np.nan, 2.0]); nan_b = np.array([np.nan, np.nan, 1.0])
ok("na PREV bar cannot cross", not bool(E.cross_over(nan_a, nan_b).any()),
   "prev na -> falsy, like Pine crossover on warmup")

# ---------------------------------------------------------------- 3. rma / atr / dmi
z = np.arange(1, 51, dtype=float)
r = E.rma(z, 14)
ok("rma seed = SMA of first n", bool(np.isclose(r[13], z[:14].mean())))
ok("rma recursion", bool(np.isclose(r[14], (r[13] * 13 + z[14]) / 14)))
zz = z.copy(); zz[:13] = np.nan
rr = E.rma(zz, 10)
ok("rma leading-na: seed = mean of first 10 valid values",
   bool(np.isclose(rr[22], zz[13:23].mean())), "rr22=%.10f" % rr[22])
h60 = np.full(80, 10.0); l60 = h60.copy(); c60 = h60.copy()
ok("atr flat -> 0", bool(np.nanmax(np.abs(E.atr_pine(h60, l60, c60, 14))) < 1e-12))

hh = np.arange(1.0, 121.0) + 100.0; ll = hh - 0.5; cc = hh
dP, dM, ax = E.dmi_pine(hh, ll, cc, 14, 14)
ok("dmi uptrend: diPlus dominates late",
   bool(np.nanmean(dP[-40:]) > np.nanmean(dM[-40:])))
ok("dmi uptrend: adx >= 40 late", bool(np.nanmean(ax[-40:]) >= 40.0))


def rma_ref(x, n):
    out = [np.nan] * len(x); buf = []; prev = None; seeded = False
    for i, xi in enumerate(np.asarray(x, float)):
        if not seeded:
            if not np.isnan(xi):
                buf.append(xi)
                if len(buf) == n:
                    prev = sum(buf) / n; out[i] = prev; seeded = True
        else:
            if np.isnan(xi):
                out[i] = prev
            else:
                prev = (prev * (n - 1) + xi) / n; out[i] = prev
    return np.array(out, float)


def dmi_ref(h, l, c, dl, sm):
    up = np.full(len(h), np.nan); dn = np.full(len(h), np.nan)
    up[1:] = h[1:] - h[:-1]; dn[1:] = -(l[1:] - l[:-1])
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pdm[0] = np.nan; mdm[0] = np.nan
    trur = np.asarray(rma_ref(E.true_range(h, l, c), dl), float)
    plus = E.fixnan(100.0 * np.asarray(rma_ref(pdm, dl), float) / trur)
    minus = E.fixnan(100.0 * np.asarray(rma_ref(mdm, dl), float) / trur)
    s = plus + minus
    denom = np.where(s == 0, 1.0, s)
    return plus, minus, 100.0 * rma_ref(np.abs(plus - minus) / denom, sm)


rng = np.random.default_rng(11)
h2 = 100.0 + np.cumsum(rng.normal(0, 0.4, 500))
l2 = h2 - rng.uniform(0.1, 1.0, 500)
c2 = h2 - rng.uniform(0.0, 0.5, 500)
dP2, dM2, ax2 = E.dmi_pine(h2, l2, c2, 14, 14)
dP3, dM3, ax3 = dmi_ref(h2, l2, c2, 14, 14)
ok("dmi dual-engine agreement, 500 random bars",
   bool(np.allclose(dP2[30:], dP3[30:], equal_nan=True))
   and bool(np.allclose(dM2[30:], dM3[30:], equal_nan=True))
   and bool(np.allclose(ax2[30:], ax3[30:], equal_nan=True)))

# ---------------------------------------------------------------- playthrough A
flat = np.sin(np.arange(110) * 0.7) * 0.05
oA, hA, lA, cA = mk(np.concatenate([flat, [-1.2] * 40, [2.2] * 80, [-1.8] * 140]))
tA = np.arange(len(cA)) * 3600_000 + 1577880000000
resA = E.simulate(dict(o=oA, h=hA, l=lA, c=cA, t=tA), P, 0.0, 0.0)
trA = resA["trades"]
ok("playthrough A trades", len(trA) >= 2, "n=" + str(len(trA)))

lcA, scA = sigbars(oA, hA, lA, cA)
ks = np.where(lcA)[0]
ok("A: reference derives the long-signal bar(s)",
   len(ks) == 1 and trA[0]["entry_bar"] == int(ks[0]),
   "ref=%s engine=%s" % (list(ks), trA[0]["entry_bar"] if trA else -1))
kA = int(ks[0])
ok("A: entry fills at the SIGNAL bar close (process_orders_on_close)",
   bool(np.isclose(trA[0]["entry"], cA[kA] * (1 + 0.0))),
   "fill=%.6f close=%.6f" % (trA[0]["entry"], cA[kA]))
AA = E.atr_pine(hA, lA, cA, 14)
ok("A: ALL-IN sizing (qty = equity/fill at entry)",
   bool(np.isclose(trA[0]["qty"] * trA["entry"] if False else
                   trA[0]["qty"] * trA[0]["entry"], 10000.0, atol=1e-6)),
   "qty*entry=%.4f" % (trA[0]["qty"] * trA[0]["entry"]))
tps = [t for t in trA if t["why"] == "TP"]
ok("A: TP fills at the exact anchored limit (entry + 4*ATR(signal bar))",
   len(tps) >= 1 and bool(np.isclose(tps[0]["exit"], cA[kA] + 4.0 * AA[kA])),
   "exit=%.6f anchor=%.6f" % (tps[0]["exit"], cA[kA] + 4.0 * AA[kA]) if tps else "none")
ok("A: every trade pnl recomputes from its own columns",
   money_rows(trA, 0.0))
if resA["n_open"] == 0:
    ok("A: equity identity INIT + sum(pnl) == final (flat end)",
       bool(np.isclose(resA["eq"][-1], 10000.0 + sum(t["pnl"] for t in trA),
                       atol=1e-6)),
       "eq=%.4f expected=%.4f" % (resA["eq"][-1],
                                  10000.0 + sum(t["pnl"] for t in trA)))
else:
    ok("A: open trade excluded from closed stats", resA["n_open"] == 1)

# ---------------------------------------------------------------- playthrough B
kB = kA
slB = cA[kB] - 2.0 * AA[kB]; tpB = cA[kB] + 4.0 * AA[kB]
oB, hB, lB, cB = mk(np.concatenate([flat, [-1.2] * 40, [2.2] * 80, [0.0] * 30]))
hB[kB + 1] = tpB + 5.0                      # one bar SPANS SL and TP
lB[kB + 1] = slB - 5.0
tB = np.arange(len(cB)) * 3600_000 + 1577880000000
resB = E.simulate(dict(o=oB, h=hB, l=lB, c=cB, t=tB), P, 0.0, 0.0)
spans = [t for t in resB["trades"] if t["why"] == "SL" and t["exit_bar"] == kB + 1]
ok("B: spanning bar resolves STOP FIRST, at the stop price",
   len(spans) == 1 and bool(np.isclose(spans[0]["exit"], slB)),
   "exit=%s sl=%.6f" % (spans[0]["exit"] if spans else "none", slB))

# ---------------------------------------------------------------- playthrough C
resC = E.simulate(dict(o=oA, h=hA, l=lA, c=cA, t=tA), P, FEER, SLIPR)
trC = resC["trades"]
ok("C: fees at repo6x5 — every row's entry/exit fee and pnl recompute",
   len(trC) >= 2 and money_rows(trC, FEER), "n=" + str(len(trC)))
if resC["n_open"] == 0:
    ok("C: equity identity with fees (flat end)",
       bool(np.isclose(resC["eq"][-1], 10000.0 + sum(t["pnl"] for t in trC),
                       atol=1e-6)))
else:
    ok("C: open trade excluded from closed stats", resC["n_open"] == 1)

# ---------------------------------------------------------------- playthrough D
PD = dict(P); PD["use_tp"] = False
oD, hD, lD, cD = mk(np.concatenate([flat, [-1.2] * 40, [2.2] * 80, [0.0] * 22,
                                    [-1.8] * 55, [2.8] * 60]))
tD = np.arange(len(cD)) * 3600_000 + 1577880000000
resD = E.simulate(dict(o=oD, h=hD, l=lD, c=cD, t=tD), PD, FEER, SLIPR)
trD = resD["trades"]
revs = [t for t in trD if t["why"] == "reverse"]
ok("D: reversal exists (long held into the crossdown)", len(revs) >= 1,
   "n_rev=%d" % len(revs))
rb = revs[0]["exit_bar"] if revs else -1
# a SELL-side signal closes the old LONG: fill = close*(1-slip) (one order,
# one price, both legs)
ok("D: reversal single fill at close*(1-slip) — old exit and new entry same price",
   rb >= 0 and bool(np.isclose(revs[0]["exit"], cD[rb] * (1.0 - SLIPR))),
   "exit=%.6f close*(1-slip)=%.6f" % (revs[0]["exit"] if revs else -1,
                                      cD[rb] * (1.0 - SLIPR)))
idx0 = trD.index(revs[0]) if revs else -1
nextrow = trD[idx0 + 1] if revs and idx0 + 1 < len(trD) else None
ok("D: next trade's entry == the reversal fill (one order, both legs)",
   nextrow is not None and bool(np.isclose(revs[0]["exit"], nextrow["entry"])),
   "rev_exit=%s next_entry=%s" % (revs[0]["exit"] if revs else "-",
                                  nextrow["entry"] if nextrow else "-"))
ok("D: fee recomputation on every row (repo6x5)", money_rows(trD, FEER))
ok("D: whole-order fee split (old leg's exit fee + new leg's entry fee share one fill)",
   rb >= 0 and bool(np.isclose(revs[0]["exit_fee"],
                               revs[0]["qty"] * revs[0]["exit"] * FEER,
                               atol=1e-9)))
ok("D: open trade at series end excluded from closed stats", resD["n_open"] == 1)

# ---------------------------------------------------------------- playthrough E
# The Pine trap: on a duplicate same-direction signal while pyramiding=0
# REJECTS the entry, the strategy's `var` assignments still run and RE-SET the
# brackets from the duplicate bar. To hold a long across a crossunder we run
# with allow_short=False (a genuine Pine "Direccion" input): the crossunder is
# then mechanically inert, the long survives, and any later cross_up while
# positioned MUST take the re-set branch. Proof: the eventual SL exit price
# equals the re-set bar's anchor, NOT the entry bar's.
PE = dict(P); PE["use_tp"] = False; PE["allow_short"] = False
oE, hE, lE, cE = mk(np.concatenate([flat, [-1.2] * 40, [2.2] * 80,
                                    [-0.8] * 45, [3.5] * 8, [1.2] * 20,
                                    [0.0] * 6, [-1.6] * 70]))
tE = np.arange(len(cE)) * 3600_000 + 1577880000000
resE = E.simulate(dict(o=oE, h=hE, l=lE, c=cE, t=tE), PE, 0.0, 0.0)
trE = resE["trades"]
lcE, scE = sigbars(oE, hE, lE, cE)
ksE = list(np.where(lcE)[0])
ok("E: at least two cross_up signals (duplicate while long occurs)",
   len(ksE) >= 2, "long_cond bars=%s" % ksE)
slsE = [t for t in trE if t["why"] == "SL"]
if len(ksE) >= 2 and slsE:
    k1, k2 = int(ksE[0]), None
    sl_exit = slsE[0]
    k2 = int(max(x for x in ksE if x < sl_exit["exit_bar"]))
    AE = E.atr_pine(hE, lE, cE, 14)
    anchor1 = cE[k1] - 2.0 * AE[k1]
    anchor2 = cE[k2] - 2.0 * AE[k2]
    ok("E: re-set used (two distinct signal bars before the exit)",
       k1 != k2, "k1=%d k2=%d" % (k1, k2))
    ok("E: SL exit == RE-SET bar anchor (var-block reran on the dup signal)",
       bool(np.isclose(sl_exit["exit"], anchor2)),
       "exit=%.4f reset_anchor=%.4f entry_anchor=%.4f (entry anchor would be the bug)"
       % (sl_exit["exit"], anchor2, anchor1))
    ok("E: qty unchanged by the duplicate signal (pyramiding=0)",
       not any(t["entry_bar"] == k2 for t in trE if t is not sl_exit))
else:
    ok("E: SL exit + >=2 signals present", False,
       "ks=%s sls=%d" % (ksE, len(slsE)))
if resE["n_open"] == 0:
    ok("E: equity identity (flat end)",
       bool(np.isclose(resE["eq"][-1], 10000.0 + sum(t["pnl"] for t in trE),
                       atol=1e-6)))
else:
    ok("E: open trade excluded from closed stats", resE["n_open"] == 1)

# ---------------------------------------------------------------- no-lookahead
cut = 150
full = E.simulate(dict(o=oA, h=hA, l=lA, c=cA, t=tA), P, FEER, SLIPR)
part = E.simulate({k: v[:cut] for k, v in
                   dict(o=oA, h=hA, l=lA, c=cA, t=tA).items()}, P, FEER, SLIPR)
ok("truncation parity (no-lookahead)",
   bool(np.allclose(full["eq"][:cut - 1], part["eq"][:cut - 1], atol=1e-12)))

# ---------------------------------------------------------------- write
n_fail = sum(1 for ln in lines if ln.startswith("[FAIL]"))
n_pass = sum(1 for ln in lines if ln.startswith("[PASS]"))
with open(OUT, "w", encoding="utf-8") as f:
    f.write("emaadx_engine audit — known answers\n")
    f.write("Pine: deepseek_pinescript_20261022_c2f363.txt "
            "(EMA Cross + ADX [Quant], Pine v6)\n")
    f.write("engine: code/emaadx_engine.py\n\n")
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
print("\n%d pass / %d fail  (wrote %s)" % (n_pass, n_fail, OUT))
sys.exit(0 if n_fail == 0 else 1)
